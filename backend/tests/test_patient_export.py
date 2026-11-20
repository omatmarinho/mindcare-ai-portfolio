"""Exportação dos dados do paciente (LGPD: acesso e portabilidade)."""
from datetime import date

import pytest
from cryptography.fernet import Fernet

from app import audit
from app.ai import summarizer
from app.database.models import AuditLog
from tests.test_notes import FAKE_SUMMARY


@pytest.fixture
def ai(monkeypatch):
    monkeypatch.setenv("NOTES_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(summarizer, "summarize", lambda text: FAKE_SUMMARY)


@pytest.fixture
def patient(client, auth_a):
    p = client.post("/patients", json={"full_name": "Paciente Exporta", "email": "exporta@exemplo.com"},
                   headers=auth_a).json()
    client.post(f"/patients/{p['id']}/ai-consent", headers=auth_a)
    return p


def test_export_contains_everything_about_the_patient(client, db_session, auth_a, patient, ai):
    client.post("/appointments", json={"patient_id": patient["id"], "starts_at": "2026-12-01T10:00:00-03:00"},
                headers=auth_a)
    client.post(f"/patients/{patient['id']}/notes/text", json={"text": "Relato ficticio da sessao."},
                headers=auth_a)

    response = client.get(f"/patients/{patient['id']}/export", headers=auth_a)
    assert response.status_code == 200
    body = response.json()

    assert body["patient"]["full_name"] == "Paciente Exporta"
    assert body["patient"]["ai_consent_at"] is not None
    assert len(body["appointments"]) == 1
    # Registro clínico vem descriptografado
    assert body["clinical_notes"][0]["transcript"] == "Relato ficticio da sessao."
    assert body["clinical_notes"][0]["summary"]["resumo"] == FAKE_SUMMARY.resumo
    assert "LGPD" in body["notice"]

    logged = db_session.query(AuditLog).filter(AuditLog.action == audit.PATIENT_EXPORT).one()
    assert logged.resource_id == patient["id"]


def test_export_does_not_mix_other_patients(client, auth_a, patient, ai):
    other = client.post("/patients", json={"full_name": "Outro Paciente"}, headers=auth_a).json()
    client.post("/appointments", json={"patient_id": other["id"], "starts_at": "2026-12-02T10:00:00-03:00"},
                headers=auth_a)
    body = client.get(f"/patients/{patient['id']}/export", headers=auth_a).json()
    assert body["appointments"] == []


def test_other_user_cannot_export(client, auth_b, patient):
    assert client.get(f"/patients/{patient['id']}/export", headers=auth_b).status_code == 404


def test_archived_patient_can_still_be_exported(client, auth_a, patient):
    client.delete(f"/patients/{patient['id']}", headers=auth_a)
    assert client.get(f"/patients/{patient['id']}/export", headers=auth_a).status_code == 200
