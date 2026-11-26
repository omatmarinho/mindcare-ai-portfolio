"""
Processamento de um registro de sessão em segundo plano:
    (áudio) -> transcrição -> resumo -> criptografia -> "pending_review"

Roda DEPOIS que a API já respondeu (a transcrição pode levar minutos).
Por isso abre a sua própria sessão de banco.

Privacidade:
- o arquivo de áudio temporário é SEMPRE apagado no final, com ou sem erro;
- os logs registram apenas o id do registro e o tipo de erro, nunca o conteúdo.
"""
import logging
import os
import threading
from datetime import datetime, timedelta, timezone

from app import crypto
from app.ai import demo, summarizer, transcription
from app.database.models import ClinicalNote

logger = logging.getLogger("psinara.ai")

STATUS_PROCESSING = "processing"
STATUS_PENDING_REVIEW = "pending_review"
STATUS_APPROVED = "approved"
STATUS_FAILED = "failed"


class NoSpeechError(ValueError):
    pass


# Só estas mensagens (escritas por nós, sem conteúdo clínico) chegam ao usuário
_SAFE_ERRORS = (NoSpeechError, summarizer.SummarizationError, crypto.EncryptionKeyMissing)

# "Fila" simples: processa UM registro por vez. Whisper e o modelo de
# linguagem usam muita CPU e memória; rodar vários ao mesmo tempo deixaria
# todos lentos e poderia esgotar a memória do servidor. Os demais esperam.
_PROCESSING_SLOT = threading.Semaphore(int(os.getenv("AI_MAX_CONCURRENT", "1")))

# Um registro "processando" há mais tempo que isso foi interrompido
# (ex.: o servidor reiniciou no meio do processamento)
STALE_AFTER = timedelta(minutes=int(os.getenv("AI_STALE_MINUTES", "60")))
STALE_MESSAGE = "O processamento foi interrompido. Use \"Reprocessar\" ou envie novamente."


def expire_if_stale(db, note: ClinicalNote) -> bool:
    """Marca como falho um registro preso em 'processing'. Devolve True se mudou."""
    if note.status != STATUS_PROCESSING:
        return False
    created = note.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created < STALE_AFTER:
        return False
    note.status = STATUS_FAILED
    note.error_message = STALE_MESSAGE
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    return True


def process_note(
    session_factory,
    note_id: int,
    audio_path: str | None = None,
    text: str | None = None,
) -> None:
    with _PROCESSING_SLOT:
        _process(session_factory, note_id, audio_path, text)


def _process(session_factory, note_id: int, audio_path: str | None, text: str | None) -> None:
    db = session_factory()
    try:
        note = db.get(ClinicalNote, note_id)
        if note is None:
            return

        try:
            if audio_path is not None:
                if demo.enabled():
                    note.transcription_model = "demo (transcrição de exemplo)"
                    text = demo.transcribe(audio_path)
                else:
                    note.transcription_model = f"faster-whisper:{transcription.model_name()}"
                    text = transcription.transcribe(audio_path)

            if not text or not text.strip():
                raise NoSpeechError("Nenhuma fala foi reconhecida no áudio.")

            summary = demo.summarize(text) if demo.enabled() else summarizer.summarize(text)

            note.transcript_encrypted = crypto.encrypt_text(text)
            note.summary_encrypted = crypto.encrypt_json(summary.model_dump())
            note.ai_model = "demo (regras simples)" if demo.enabled() else f"ollama:{summarizer.model_name()}"
            note.status = STATUS_PENDING_REVIEW
            note.error_message = None

        except Exception as exc:  # noqa: BLE001 - qualquer falha vira "failed"
            logger.warning("Falha ao processar registro %s: %s", note_id, type(exc).__name__)
            note.status = STATUS_FAILED
            note.error_message = (
                str(exc)[:255] if isinstance(exc, _SAFE_ERRORS)
                else "Falha no processamento. Tente novamente."
            )
            # Mesmo com falha no resumo, guarda a transcrição (criptografada)
            # para o psicólogo não perder o trabalho
            if text and text.strip() and note.transcript_encrypted is None:
                try:
                    note.transcript_encrypted = crypto.encrypt_text(text)
                except crypto.EncryptionKeyMissing:
                    pass

        note.updated_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)  # o áudio nunca é guardado
