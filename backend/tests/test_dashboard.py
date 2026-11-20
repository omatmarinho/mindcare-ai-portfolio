"""Resumo do dia: consultas de hoje, registros a revisar e indicadores."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from cryptography.fernet import Fernet

from app.ai import summarizer
from tests.test_notes import FAKE_SUMMARY

SP = ZoneInfo("America/Sao_Paulo")


def _today():
    return datetime.now(SP).date()


def _at(day, hour):
    return datetime(day.year, day.month, day.day, hour, tzinfo=SP).isoformat()


@pytest.fixture
def ai(monkeypatch):
    monkeypatch.setenv("NOTES_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(summarizer, "summarize", lambda text: FAKE_SUMMARY)


@pytest.fixture
def patient(client, auth_a):
    p = client.post("/patients", json={"full_name": "Paciente Resumo"},
                    headers=auth_a).json()
    client.post(f"/patients/{p['id']}/ai-consent", headers=auth_a)
    return p


def _book(client, headers, patient_id, starts_at):
    return client.post("/appointments", json={"patient_id": patient_id, "starts_at": starts_at},
                       headers=headers).json()


def test_dashboard_summarizes_the_day(client, auth_a, patient, ai):
    today = _today()
    first = _book(client, auth_a, patient["id"], _at(today, 9))
    _book(client, auth_a, patient["id"], _at(today, 15))
    cancelled = _book(client, auth_a, patient["id"], _at(today, 11))
    client.post(f"/appointments/{cancelled['id']}/status", json={"status": "cancelled"}, headers=auth_a)
    _book(client, auth_a, patient["id"], _at(today + timedelta(days=1), 9))  # amanhã: fora

    # Registro com IA esperando revisão
    client.post(f"/patients/{patient['id']}/notes/text", json={"text": "Anotacao ficticia."}, headers=auth_a)

    body = client.get("/dashboard", headers=auth_a).json()

    assert body["date"] == str(today)
    starts = [datetime.fromisoformat(a["starts_at"]).astimezone(SP).hour for a in body["appointments_today"]]
    assert starts == [9, 15]
    assert body["appointments_today"][0]["id"] == first["id"]
    assert body["appointments_today"][0]["patient_name"] == "Paciente Resumo"

    assert [n["patient_name"] for n in body["notes_to_review"]] == ["Paciente Resumo"]
    assert body["notes_failed"] == []


def test_dashboard_has_no_clinical_content(client, auth_a, patient, ai):
    client.post(f"/patients/{patient['id']}/notes/text", json={"text": "Conteudo sigiloso."}, headers=auth_a)
    text = client.get("/dashboard", headers=auth_a).text
    assert "sigiloso" not in text and FAKE_SUMMARY.resumo not in text


def test_dashboard_is_per_user(client, auth_a, auth_b, patient, ai):
    _book(client, auth_a, patient["id"], _at(_today(), 10))
    client.post(f"/patients/{patient['id']}/notes/text", json={"text": "Anotacao."}, headers=auth_a)

    body_b = client.get("/dashboard", headers=auth_b).json()
    assert body_b["appointments_today"] == [] and body_b["notes_to_review"] == []


def test_dashboard_requires_login(client):
    assert client.get("/dashboard").status_code == 401


# ---------- Indicadores do painel ----------

def _insights(client, headers):
    return client.get("/dashboard", headers=headers).json()["insights"]


def _status(client, headers, appointment_id, status):
    client.post(f"/appointments/{appointment_id}/status", json={"status": status}, headers=headers)


def test_insights_sessions_per_month(client, auth_a, patient):
    today = _today()
    done = _book(client, auth_a, patient["id"], _at(today - timedelta(days=1), 9))
    missed = _book(client, auth_a, patient["id"], _at(today - timedelta(days=1), 11))
    _status(client, auth_a, done["id"], "completed")
    _status(client, auth_a, missed["id"], "no_show")

    months = _insights(client, auth_a)["months"]
    assert len(months) == 6
    yesterday = today - timedelta(days=1)
    point = [m for m in months if m["month"] == yesterday.strftime("%Y-%m")][0]
    assert point["completed"] == 1 and point["no_show"] == 1
    assert sum(m["completed"] for m in months) == 1


def test_insights_attendance_and_weekday(client, auth_a, patient):
    today = _today()
    done = _book(client, auth_a, patient["id"], _at(today - timedelta(days=3), 9))
    missed = _book(client, auth_a, patient["id"], _at(today - timedelta(days=10), 9))
    _status(client, auth_a, done["id"], "completed")
    _status(client, auth_a, missed["id"], "no_show")

    data = _insights(client, auth_a)
    assert data["attendance_30d"]["completed"] == 1
    assert data["attendance_30d"]["no_show"] == 1
    assert sum(data["weekday_load"]) == 2
    assert data["weekday_load"][(today - timedelta(days=3)).weekday()] >= 1


def test_insights_upcoming_skips_today(client, auth_a, patient):
    today = _today()
    _book(client, auth_a, patient["id"], _at(today + timedelta(days=2), 15))
    _book(client, auth_a, patient["id"], _at(today + timedelta(days=9), 15))  # fora dos 7 dias
    upcoming = _insights(client, auth_a)["upcoming"]
    assert len(upcoming) == 1 and upcoming[0]["patient_name"] == "Paciente Resumo"


def test_insights_inactive_patients(client, auth_a, patient):
    today = _today()
    # Paciente que veio há 40 dias e não tem nada marcado
    gone = client.post("/patients", json={"full_name": "Paciente Sumido"}, headers=auth_a).json()
    old = _book(client, auth_a, gone["id"], _at(today - timedelta(days=40), 10))
    _status(client, auth_a, old["id"], "completed")
    # O paciente da fixture tem sessão marcada à frente: não aparece
    _book(client, auth_a, patient["id"], _at(today + timedelta(days=3), 10))

    data = _insights(client, auth_a)
    names = [p["full_name"] for p in data["inactive_patients"]]
    assert names == ["Paciente Sumido"]
    assert data["inactive_patients"][0]["last_session"] == str(today - timedelta(days=40))
    assert data["active_patients"] == 2
    assert data["new_patients_month"] == 2


def test_insights_are_per_user(client, auth_a, auth_b, patient):
    _book(client, auth_a, patient["id"], _at(_today() + timedelta(days=2), 15))
    other = _insights(client, auth_b)
    assert other["upcoming"] == [] and other["active_patients"] == 0 and other["inactive_patients"] == []
