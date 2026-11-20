"""Visão geral do paciente: frequência e histórico (sem conteúdo clínico)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

SP = ZoneInfo("America/Sao_Paulo")


def _at(days: int, hour: int = 10) -> str:
    day = (datetime.now(SP) + timedelta(days=days)).date()
    return datetime(day.year, day.month, day.day, hour, tzinfo=SP).isoformat()


def _book(client, headers, patient_id, days, status=None):
    appt = client.post("/appointments", json={"patient_id": patient_id, "starts_at": _at(days)}, headers=headers).json()
    if status:
        client.post(f"/appointments/{appt['id']}/status", json={"status": status}, headers=headers)
    return appt


def test_overview_counts_and_history(client, auth_a):
    patient = client.post("/patients", json={"full_name": "Paciente Visão"},
                          headers=auth_a).json()
    _book(client, auth_a, patient["id"], -21, "completed")
    _book(client, auth_a, patient["id"], -14, "no_show")
    last = _book(client, auth_a, patient["id"], -7, "completed")
    nxt = _book(client, auth_a, patient["id"], 7)

    body = client.get(f"/patients/{patient['id']}/overview", headers=auth_a).json()
    assert body["sessions_completed"] == 2 and body["sessions_no_show"] == 1
    assert body["first_session"] == _at(-21)[:10] and body["last_session"] == _at(-7)[:10]
    assert body["next_appointment"]["id"] == nxt["id"]
    assert sum(m["completed"] for m in body["months"]) == 2
    assert [a["id"] for a in body["recent"]][0] == last["id"]  # mais recente primeiro
    assert len(body["months"]) == 6
    assert body["notes_count"] == 0


def test_overview_of_new_patient_is_empty(client, auth_a):
    patient = client.post("/patients", json={"full_name": "Paciente Novo"}, headers=auth_a).json()
    body = client.get(f"/patients/{patient['id']}/overview", headers=auth_a).json()
    assert body["sessions_completed"] == 0 and body["next_appointment"] is None and body["recent"] == []
    assert body["first_session"] is None


def test_overview_is_private(client, auth_a, auth_b):
    patient = client.post("/patients", json={"full_name": "Paciente Privado"}, headers=auth_a).json()
    assert client.get(f"/patients/{patient['id']}/overview", headers=auth_b).status_code == 404
    assert client.get("/patients/999999/overview", headers=auth_a).status_code == 404
