"""
Registros de sessão com IA.

A IA real (Whisper e Ollama) é substituída por versões falsas: os testes
verificam as REGRAS (consentimento, isolamento, criptografia, revisão,
aprovação), não a qualidade da IA.
"""
import io
import os

import pytest
from cryptography.fernet import Fernet

from app import audit
from app.ai import pipeline, summarizer, transcription
from app.database.models import AuditLog, ClinicalNote

FAKE_TRANSCRIPT = "Paciente ficticio relatou semana tranquila e falou sobre o trabalho."
FAKE_SUMMARY = summarizer.SessionSummary(
    resumo="Sessao sobre rotina de trabalho.",
    topicos=["trabalho", "rotina"],
    pontos_de_acompanhamento=["retomar tema do trabalho"],
    trechos_para_revisao=[],
)


@pytest.fixture(autouse=True)
def fake_ai(monkeypatch):
    """Chave de criptografia de teste + IA falsa que registra o que recebeu."""
    monkeypatch.setenv("NOTES_ENCRYPTION_KEY", Fernet.generate_key().decode())
    calls = {"transcribe": [], "summarize": []}

    def fake_transcribe(path):
        calls["transcribe"].append(path)
        assert os.path.exists(path)  # o arquivo existe durante a transcrição
        return FAKE_TRANSCRIPT

    def fake_summarize(text):
        calls["summarize"].append(text)
        return FAKE_SUMMARY

    monkeypatch.setattr(transcription, "transcribe", fake_transcribe)
    monkeypatch.setattr(summarizer, "summarize", fake_summarize)
    return calls


@pytest.fixture
def patient(client, auth_a):
    return client.post("/patients", json={"full_name": "Paciente Ficticio"}, headers=auth_a).json()


@pytest.fixture
def consented_patient(client, auth_a, patient):
    response = client.post(f"/patients/{patient['id']}/ai-consent", headers=auth_a)
    assert response.status_code == 200
    return response.json()


def _upload(client, headers, patient_id, content=b"RIFF....fake-audio", content_type="audio/wav"):
    return client.post(
        f"/patients/{patient_id}/notes/audio",
        files={"audio": ("sessao.wav", io.BytesIO(content), content_type)},
        headers=headers,
    )


# ---------- Consentimento ----------

def test_ai_requires_patient_consent(client, auth_a, patient, fake_ai):
    response = client.post(f"/patients/{patient['id']}/notes/text", json={"text": "abc"}, headers=auth_a)
    assert response.status_code == 409
    assert "consentimento" in response.json()["detail"]
    assert _upload(client, auth_a, patient["id"]).status_code == 409
    assert fake_ai["summarize"] == []  # nada foi enviado à IA


def test_consent_can_be_given_and_revoked(client, auth_a, patient):
    given = client.post(f"/patients/{patient['id']}/ai-consent", headers=auth_a).json()
    assert given["ai_consent_at"] is not None

    revoked = client.delete(f"/patients/{patient['id']}/ai-consent", headers=auth_a).json()
    assert revoked["ai_consent_at"] is None

    response = client.post(f"/patients/{patient['id']}/notes/text", json={"text": "abc"}, headers=auth_a)
    assert response.status_code == 409


def test_archived_patient_cannot_receive_notes(client, auth_a, consented_patient):
    client.delete(f"/patients/{consented_patient['id']}", headers=auth_a)
    response = client.post(f"/patients/{consented_patient['id']}/notes/text", json={"text": "abc"}, headers=auth_a)
    assert response.status_code == 409


# ---------- Fluxo completo ----------

def test_audio_flow_transcribes_summarizes_and_deletes_audio(client, auth_a, consented_patient, fake_ai):
    response = _upload(client, auth_a, consented_patient["id"])
    assert response.status_code == 202
    assert response.json()["status"] == "processing"
    note_id = response.json()["id"]

    # A tarefa em segundo plano já rodou (o TestClient espera por ela)
    detail = client.get(f"/notes/{note_id}", headers=auth_a).json()
    assert detail["status"] == "pending_review"
    assert detail["transcript"] == FAKE_TRANSCRIPT
    assert detail["summary"]["topicos"] == ["trabalho", "rotina"]
    assert detail["ai_model"].startswith("ollama:")
    assert detail["transcription_model"].startswith("faster-whisper:")

    # O áudio temporário foi apagado
    [audio_path] = fake_ai["transcribe"]
    assert not os.path.exists(audio_path)


def test_text_flow_skips_transcription(client, auth_a, consented_patient, fake_ai):
    response = client.post(
        f"/patients/{consented_patient['id']}/notes/text",
        json={"text": "Anotacao ditada pelo psicologo."},
        headers=auth_a,
    )
    assert response.status_code == 202
    assert fake_ai["transcribe"] == []
    assert fake_ai["summarize"] == ["Anotacao ditada pelo psicologo."]


def test_content_is_encrypted_in_database(client, db_session, auth_a, consented_patient):
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]
    note = db_session.get(ClinicalNote, note_id)
    db_session.refresh(note)

    assert note.transcript_encrypted and note.summary_encrypted
    assert "trabalho" not in note.transcript_encrypted
    assert "trabalho" not in note.summary_encrypted


def test_review_edit_then_approve_locks_note(client, auth_a, consented_patient):
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]

    edited = client.put(f"/notes/{note_id}", json={
        "transcript": "Transcricao corrigida pelo psicologo.",
        "summary": {"resumo": "Resumo revisado.", "topicos": ["trabalho"],
                    "pontos_de_acompanhamento": [], "trechos_para_revisao": []},
    }, headers=auth_a)
    assert edited.status_code == 200
    assert edited.json()["transcript"] == "Transcricao corrigida pelo psicologo."

    approved = client.post(f"/notes/{note_id}/approve", headers=auth_a)
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert approved.json()["approved_at"] is not None

    # Aprovado = travado
    again = client.put(f"/notes/{note_id}", json={
        "transcript": "Tentativa de alterar depois.",
        "summary": {"resumo": "x"},
    }, headers=auth_a)
    assert again.status_code == 409
    assert client.post(f"/notes/{note_id}/approve", headers=auth_a).status_code == 409


def test_failure_is_reported_without_losing_transcript(client, auth_a, consented_patient, monkeypatch):
    def broken_summarize(text):
        raise summarizer.SummarizationError("Falha ao comunicar com o modelo de IA local.")

    monkeypatch.setattr(summarizer, "summarize", broken_summarize)
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]

    detail = client.get(f"/notes/{note_id}", headers=auth_a).json()
    assert detail["status"] == "failed"
    assert detail["error_message"] == "Falha ao comunicar com o modelo de IA local."
    assert detail["transcript"] == FAKE_TRANSCRIPT  # a transcrição não se perdeu
    assert client.post(f"/notes/{note_id}/approve", headers=auth_a).status_code == 409


def test_unexpected_error_message_is_generic(client, auth_a, consented_patient, monkeypatch):
    def exploding_transcribe(path):
        raise RuntimeError("detalhe interno que poderia conter conteudo sensivel")

    monkeypatch.setattr(transcription, "transcribe", exploding_transcribe)
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]

    detail = client.get(f"/notes/{note_id}", headers=auth_a).json()
    assert detail["status"] == "failed"
    assert "sensivel" not in detail["error_message"]


def test_missing_encryption_key_blocks_ai(client, auth_a, consented_patient, monkeypatch, fake_ai):
    monkeypatch.delenv("NOTES_ENCRYPTION_KEY")
    response = client.post(f"/patients/{consented_patient['id']}/notes/text", json={"text": "abc"}, headers=auth_a)
    assert response.status_code == 503
    assert fake_ai["summarize"] == []


# ---------- Upload ----------

def test_rejects_non_audio_files(client, auth_a, consented_patient):
    response = _upload(client, auth_a, consented_patient["id"], content_type="application/pdf")
    assert response.status_code == 415


def test_rejects_empty_audio(client, auth_a, consented_patient):
    assert _upload(client, auth_a, consented_patient["id"], content=b"").status_code == 400


def test_rejects_audio_over_limit(client, auth_a, consented_patient, monkeypatch):
    from app.api.routes import notes as notes_routes
    monkeypatch.setattr(notes_routes, "MAX_AUDIO_BYTES", 10)
    response = _upload(client, auth_a, consented_patient["id"], content=b"x" * 11)
    assert response.status_code == 413


# ---------- Isolamento e auditoria ----------

def test_other_user_cannot_access_notes(client, auth_a, auth_b, consented_patient):
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]

    assert client.get(f"/notes/{note_id}", headers=auth_b).status_code == 404
    assert client.put(f"/notes/{note_id}", json={"transcript": "x", "summary": {}}, headers=auth_b).status_code == 404
    assert client.post(f"/notes/{note_id}/approve", headers=auth_b).status_code == 404
    assert client.get(f"/patients/{consented_patient['id']}/notes", headers=auth_b).status_code == 404
    assert client.post(f"/patients/{consented_patient['id']}/ai-consent", headers=auth_b).status_code == 404
    assert _upload(client, auth_b, consented_patient["id"]).status_code == 404


def test_list_has_metadata_only(client, auth_a, consented_patient):
    _upload(client, auth_a, consented_patient["id"])
    [item] = client.get(f"/patients/{consented_patient['id']}/notes", headers=auth_a).json()
    assert "transcript" not in item and "summary" not in item
    assert item["status"] == "pending_review"


def test_note_actions_are_audited_without_content(client, db_session, auth_a, consented_patient):
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]
    client.get(f"/notes/{note_id}", headers=auth_a)
    client.post(f"/notes/{note_id}/approve", headers=auth_a)

    actions = [log.action for log in db_session.query(AuditLog).order_by(AuditLog.id)]
    for expected in (audit.PATIENT_AI_CONSENT_GIVEN, audit.NOTE_CREATE, audit.NOTE_READ, audit.NOTE_APPROVE):
        assert expected in actions

    for log in db_session.query(AuditLog).all():
        assert "trabalho" not in str(log.details or "")
        assert FAKE_TRANSCRIPT not in str(log.details or "")


def test_summary_prompt_forbids_diagnosis():
    """Garante que as regras de limite da IA continuam no prompt."""
    prompt = summarizer.SYSTEM_PROMPT
    assert "NÃO faça diagnósticos" in prompt
    assert "NÃO sugira tratamentos" in prompt
    assert "Nunca invente" in prompt


def test_pipeline_ignores_unknown_note(session_factory):
    pipeline.process_note(session_factory, 999999, text="abc")  # não lança erro


# ---------- Melhorias: reprocessar, registros presos, vínculo com consulta ----------

def test_retry_failed_note_from_saved_transcript(client, auth_a, consented_patient, monkeypatch, fake_ai):
    def broken(text):
        raise summarizer.SummarizationError("Falha ao comunicar com o modelo de IA local.")

    monkeypatch.setattr(summarizer, "summarize", broken)
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]
    assert client.get(f"/notes/{note_id}", headers=auth_a).json()["status"] == "failed"

    # IA volta a funcionar: reprocessa sem precisar do áudio
    monkeypatch.setattr(summarizer, "summarize", lambda text: FAKE_SUMMARY)
    response = client.post(f"/notes/{note_id}/retry", headers=auth_a)
    assert response.status_code == 202

    detail = client.get(f"/notes/{note_id}", headers=auth_a).json()
    assert detail["status"] == "pending_review"
    assert detail["transcript"] == FAKE_TRANSCRIPT


def test_retry_without_transcript_asks_for_new_upload(client, auth_a, consented_patient, monkeypatch):
    def broken_transcribe(path):
        raise RuntimeError("falha")

    monkeypatch.setattr(transcription, "transcribe", broken_transcribe)
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]
    response = client.post(f"/notes/{note_id}/retry", headers=auth_a)
    assert response.status_code == 409
    assert "Envie novamente" in response.json()["detail"]


def test_retry_only_for_failed(client, auth_a, consented_patient):
    note_id = _upload(client, auth_a, consented_patient["id"]).json()["id"]
    assert client.post(f"/notes/{note_id}/retry", headers=auth_a).status_code == 409


def test_stuck_processing_note_becomes_failed(client, db_session, auth_a, user_a, consented_patient):
    from datetime import datetime, timedelta, timezone
    stuck = ClinicalNote(
        patient_id=consented_patient["id"], user_id=user_a.id, source="audio",
        status="processing", created_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    db_session.add(stuck)
    db_session.commit()

    detail = client.get(f"/notes/{stuck.id}", headers=auth_a).json()
    assert detail["status"] == "failed"
    assert "interrompido" in detail["error_message"]


def test_note_linked_to_appointment(client, auth_a, consented_patient):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    starts = (datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=3)).replace(
        hour=10, minute=0, second=0, microsecond=0)
    appt = client.post("/appointments", json={
        "patient_id": consented_patient["id"], "starts_at": starts.isoformat()}, headers=auth_a).json()

    note = client.post(f"/patients/{consented_patient['id']}/notes/text",
                       json={"text": "Anotacao", "appointment_id": appt["id"]}, headers=auth_a).json()
    assert note["appointment_id"] == appt["id"]

    audio_note = client.post(
        f"/patients/{consented_patient['id']}/notes/audio",
        files={"audio": ("s.wav", io.BytesIO(b"abc"), "audio/wav")},
        data={"appointment_id": str(appt["id"])},
        headers=auth_a,
    ).json()
    assert audio_note["appointment_id"] == appt["id"]


def test_note_cannot_link_appointment_of_other_patient(client, auth_a, consented_patient):
    other = client.post("/patients", json={"full_name": "Outro"}, headers=auth_a).json()
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    starts = (datetime.now(ZoneInfo("America/Sao_Paulo")) + timedelta(days=4)).replace(
        hour=11, minute=0, second=0, microsecond=0)
    appt = client.post("/appointments", json={"patient_id": other["id"], "starts_at": starts.isoformat()},
                       headers=auth_a).json()
    response = client.post(f"/patients/{consented_patient['id']}/notes/text",
                           json={"text": "x", "appointment_id": appt["id"]}, headers=auth_a)
    assert response.status_code == 404
