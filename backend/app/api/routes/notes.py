"""
Registros de sessão com IA.

Fluxo:
1. O psicólogo registra o CONSENTIMENTO do paciente para uso de IA.
2. Envia um áudio (sessão/ditado) ou um texto.
3. A API responde na hora (202) e processa em segundo plano:
   transcrição local (Whisper) -> resumo local (Ollama) -> criptografia.
4. O registro fica "pending_review": o psicólogo revisa, edita e APROVA.
5. Registro aprovado fica travado (não pode mais ser editado).
"""
import os
import tempfile
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app import audit, crypto
from app.ai import pipeline
from app.api.deps import get_current_user
from app.database import crud
from app.database.database import get_db, get_session_factory
from app.database.models import Appointment, ClinicalNote, Patient, User
from app.schemas import (
    NoteDetail,
    NoteListItem,
    NoteSummary,
    NoteTextCreate,
    NoteUpdate,
    PatientResponse,
)

router = APIRouter(
    tags=["Registros de sessão (IA)"],
    dependencies=[Depends(get_current_user)]
)

MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_MB", "100")) * 1024 * 1024
ALLOWED_AUDIO_PREFIXES = ("audio/", "video/webm", "video/mp4")
CHUNK = 1024 * 1024


# ---------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------

def _owned_patient(db: Session, request: Request, user: User, patient_id: int) -> Patient:
    patient = crud.get_patient(db, owner_id=user.id, patient_id=patient_id)
    if patient is None:
        audit.record(
            db, request, audit.PATIENT_ACCESS_DENIED, user_id=user.id,
            resource_type=audit.RESOURCE_PATIENT, resource_id=patient_id,
            details={"method": request.method},
        )
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    return patient


def _owned_note(db: Session, request: Request, user: User, note_id: int) -> ClinicalNote:
    note = db.query(ClinicalNote).filter(
        ClinicalNote.id == note_id,
        ClinicalNote.user_id == user.id
    ).first()
    if note is None:
        audit.record(
            db, request, audit.NOTE_ACCESS_DENIED, user_id=user.id,
            resource_type=audit.RESOURCE_NOTE, resource_id=note_id,
            details={"method": request.method},
        )
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return note


def _require_ai_allowed(patient: Patient) -> None:
    if patient.archived_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Paciente arquivado. Restaure-o antes de criar registros."
        )
    if patient.ai_consent_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registre o consentimento do paciente para uso de IA antes de enviar registros."
        )
    try:
        crypto.encrypt_text("")  # falha cedo se a chave de criptografia não existir
    except crypto.EncryptionKeyMissing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registros com IA indisponíveis: criptografia não configurada no servidor."
        )


def _check_appointment(db: Session, user: User, patient: Patient, appointment_id: int | None) -> None:
    """O registro só pode ser ligado a uma consulta do mesmo psicólogo e paciente."""
    if appointment_id is None:
        return
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.user_id == user.id,
        Appointment.patient_id == patient.id,
    ).first()
    if appointment is None:
        raise HTTPException(status_code=404, detail="Consulta não encontrada para este paciente")


def _new_note(
    db: Session, patient: Patient, user: User, source: str, appointment_id: int | None = None
) -> ClinicalNote:
    note = ClinicalNote(
        patient_id=patient.id,
        user_id=user.id,
        appointment_id=appointment_id,
        source=source,
        status=pipeline.STATUS_PROCESSING,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def _detail(note: ClinicalNote) -> NoteDetail:
    data = NoteListItem.model_validate(note).model_dump()
    return NoteDetail(
        **data,
        transcript=crypto.decrypt_text(note.transcript_encrypted) if note.transcript_encrypted else None,
        summary=NoteSummary(**crypto.decrypt_json(note.summary_encrypted)) if note.summary_encrypted else None,
        transcription_model=note.transcription_model,
        ai_model=note.ai_model,
    )


def _audit_note(db, request, action, user, note_id, details=None):
    audit.record(
        db, request, action, user_id=user.id,
        resource_type=audit.RESOURCE_NOTE, resource_id=note_id, details=details,
    )


# ---------------------------------------------------------------------
# Consentimento
# ---------------------------------------------------------------------

@router.post("/patients/{patient_id}/ai-consent", response_model=PatientResponse)
def give_ai_consent(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra que o paciente consentiu com o uso de IA nos seus registros."""
    patient = _owned_patient(db, request, current_user, patient_id)
    if patient.ai_consent_at is None:
        patient.ai_consent_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(patient)
    audit.record(
        db, request, audit.PATIENT_AI_CONSENT_GIVEN, user_id=current_user.id,
        resource_type=audit.RESOURCE_PATIENT, resource_id=patient.id,
    )
    return patient


@router.delete("/patients/{patient_id}/ai-consent", response_model=PatientResponse)
def revoke_ai_consent(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revoga o consentimento: novos envios para a IA passam a ser recusados."""
    patient = _owned_patient(db, request, current_user, patient_id)
    patient.ai_consent_at = None
    db.commit()
    db.refresh(patient)
    audit.record(
        db, request, audit.PATIENT_AI_CONSENT_REVOKED, user_id=current_user.id,
        resource_type=audit.RESOURCE_PATIENT, resource_id=patient.id,
    )
    return patient


# ---------------------------------------------------------------------
# Envio (áudio ou texto)
# ---------------------------------------------------------------------

@router.post(
    "/patients/{patient_id}/notes/audio",
    response_model=NoteListItem,
    status_code=status.HTTP_202_ACCEPTED
)
def create_note_from_audio(
    request: Request,
    patient_id: int,
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    appointment_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
    current_user: User = Depends(get_current_user)
):
    patient = _owned_patient(db, request, current_user, patient_id)
    _require_ai_allowed(patient)
    _check_appointment(db, current_user, patient, appointment_id)

    content_type = (audio.content_type or "").lower()
    if not content_type.startswith(ALLOWED_AUDIO_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Envie um arquivo de áudio (mp3, m4a, wav, ogg, webm...)."
        )

    # Grava o upload em um arquivo temporário, em partes, respeitando o limite
    # Só a extensão, e só letras/números (o nome do arquivo vem do usuário)
    extension = os.path.splitext(audio.filename or "")[1][1:10]
    suffix = "." + extension if extension.isalnum() else ""
    fd, temp_path = tempfile.mkstemp(prefix="mindcare-audio-", suffix=suffix)
    size = 0
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := audio.file.read(CHUNK):
                size += len(chunk)
                if size > MAX_AUDIO_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=f"Áudio maior que {MAX_AUDIO_BYTES // (1024 * 1024)} MB."
                    )
                out.write(chunk)
    except BaseException:
        os.remove(temp_path)
        raise

    if size == 0:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail="Arquivo de áudio vazio.")

    note = _new_note(db, patient, current_user, "audio", appointment_id)
    _audit_note(db, request, audit.NOTE_CREATE, current_user, note.id,
                details={"source": "audio", "patient_id": patient.id, "bytes": size})

    # O pipeline apaga o arquivo temporário ao terminar
    background_tasks.add_task(
        pipeline.process_note, session_factory, note.id, audio_path=temp_path
    )
    return note


@router.post(
    "/patients/{patient_id}/notes/text",
    response_model=NoteListItem,
    status_code=status.HTTP_202_ACCEPTED
)
def create_note_from_text(
    request: Request,
    patient_id: int,
    data: NoteTextCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
    current_user: User = Depends(get_current_user)
):
    patient = _owned_patient(db, request, current_user, patient_id)
    _require_ai_allowed(patient)
    _check_appointment(db, current_user, patient, data.appointment_id)

    note = _new_note(db, patient, current_user, "text", data.appointment_id)
    _audit_note(db, request, audit.NOTE_CREATE, current_user, note.id,
                details={"source": "text", "patient_id": patient.id})

    background_tasks.add_task(
        pipeline.process_note, session_factory, note.id, text=data.text
    )
    return note


# ---------------------------------------------------------------------
# Consulta, revisão e aprovação
# ---------------------------------------------------------------------

@router.get("/patients/{patient_id}/notes", response_model=list[NoteListItem])
def list_notes(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = _owned_patient(db, request, current_user, patient_id)
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.patient_id == patient.id, ClinicalNote.user_id == current_user.id)
        .order_by(ClinicalNote.created_at.desc(), ClinicalNote.id.desc())
        .all()
    )
    for note in notes:
        pipeline.expire_if_stale(db, note)
    audit.record(
        db, request, audit.NOTE_LIST, user_id=current_user.id,
        resource_type=audit.RESOURCE_PATIENT, resource_id=patient.id,
        details={"count": len(notes)},
    )
    return notes


@router.get("/notes/{note_id}", response_model=NoteDetail)
def read_note(
    request: Request,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    note = _owned_note(db, request, current_user, note_id)
    pipeline.expire_if_stale(db, note)
    _audit_note(db, request, audit.NOTE_READ, current_user, note.id)
    return _detail(note)


@router.post("/notes/{note_id}/retry", response_model=NoteListItem, status_code=status.HTTP_202_ACCEPTED)
def retry_note(
    request: Request,
    note_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
    current_user: User = Depends(get_current_user)
):
    """
    Reprocessa um registro que falhou, gerando o resumo de novo a partir
    da transcrição guardada. Se a falha foi antes da transcrição, o áudio
    já não existe (nunca guardamos áudio): é preciso enviar de novo.
    """
    note = _owned_note(db, request, current_user, note_id)
    pipeline.expire_if_stale(db, note)

    if note.status != pipeline.STATUS_FAILED:
        raise HTTPException(status_code=409, detail="Só é possível reprocessar registros que falharam.")
    if not note.transcript_encrypted:
        raise HTTPException(
            status_code=409,
            detail="Não há transcrição guardada para reprocessar (o áudio não é armazenado). Envie novamente."
        )
    patient = db.get(Patient, note.patient_id)
    _require_ai_allowed(patient)

    text = crypto.decrypt_text(note.transcript_encrypted)
    note.status = pipeline.STATUS_PROCESSING
    note.error_message = None
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)

    _audit_note(db, request, audit.NOTE_RETRY, current_user, note.id)
    background_tasks.add_task(pipeline.process_note, session_factory, note.id, text=text)
    return note


@router.put("/notes/{note_id}", response_model=NoteDetail)
def update_note(
    request: Request,
    note_id: int,
    data: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revisão humana: o psicólogo corrige a transcrição e o resumo."""
    note = _owned_note(db, request, current_user, note_id)

    if note.status != pipeline.STATUS_PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Só é possível editar registros aguardando revisão."
        )

    note.transcript_encrypted = crypto.encrypt_text(data.transcript)
    note.summary_encrypted = crypto.encrypt_json(data.summary.model_dump())
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)

    _audit_note(db, request, audit.NOTE_UPDATE, current_user, note.id)
    return _detail(note)


@router.post("/notes/{note_id}/approve", response_model=NoteDetail)
def approve_note(
    request: Request,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aprovação: o conteúdo passa a valer como registro e fica travado."""
    note = _owned_note(db, request, current_user, note_id)

    if note.status != pipeline.STATUS_PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Só é possível aprovar registros aguardando revisão."
        )

    now = datetime.now(timezone.utc)
    note.status = pipeline.STATUS_APPROVED
    note.approved_at = now
    note.updated_at = now
    db.commit()
    db.refresh(note)

    _audit_note(db, request, audit.NOTE_APPROVE, current_user, note.id)
    return _detail(note)
