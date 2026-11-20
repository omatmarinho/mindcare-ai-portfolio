"""Agenda: disponibilidade, consultas, sobreposição, status e cobrança automática."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest


SP = ZoneInfo("America/Sao_Paulo")


def _future_day(days=7) -> date:
    return (datetime.now(SP) + timedelta(days=days)).date()


def _at(day: date, hour: int, minute: int = 0) -> str:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SP).isoformat()


@pytest.fixture
def patient(client, auth_a):
    return client.post(
        "/patients", json={"full_name": "Paciente Agenda"}, headers=auth_a
    ).json()


def _book(client, headers, patient_id, starts_at, duration=50, **extra):
    return client.post("/appointments", json={
        "patient_id": patient_id, "starts_at": starts_at, "duration_minutes": duration, **extra,
    }, headers=headers)


# ---------- Consultas ----------

def test_create_appointment(client, auth_a, patient):
    day = _future_day()
    response = _book(client, auth_a, patient["id"], _at(day, 14))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["patient_name"] == "Paciente Agenda"
    # 14:00 em São Paulo (UTC-3) = 17:00 UTC
    assert datetime.fromisoformat(body["starts_at"]).astimezone(ZoneInfo("UTC")).hour == 17


def test_overlapping_appointments_are_rejected(client, auth_a, patient):
    day = _future_day()
    assert _book(client, auth_a, patient["id"], _at(day, 14)).status_code == 201
    assert _book(client, auth_a, patient["id"], _at(day, 14, 30)).status_code == 409
    # Logo depois do fim (14:50) pode
    assert _book(client, auth_a, patient["id"], _at(day, 14, 50)).status_code == 201


def test_cancelled_slot_can_be_reused(client, auth_a, patient):
    day = _future_day()
    first = _book(client, auth_a, patient["id"], _at(day, 9)).json()
    client.post(f"/appointments/{first['id']}/status", json={"status": "cancelled"}, headers=auth_a)
    assert _book(client, auth_a, patient["id"], _at(day, 9)).status_code == 201


def test_list_appointments_in_range(client, auth_a, patient):
    day = _future_day()
    _book(client, auth_a, patient["id"], _at(day, 10))
    _book(client, auth_a, patient["id"], _at(day + timedelta(days=30), 10))

    start = _at(day, 0)
    end = _at(day + timedelta(days=1), 0)
    listed = client.get("/appointments", params={"start": start, "end": end}, headers=auth_a).json()
    assert len(listed) == 1


def test_range_limit(client, auth_a):
    day = _future_day()
    params = {"start": _at(day, 0), "end": _at(day + timedelta(days=90), 0)}
    assert client.get("/appointments", params=params, headers=auth_a).status_code == 422


def test_reschedule_only_scheduled(client, auth_a, patient):
    day = _future_day()
    appt = _book(client, auth_a, patient["id"], _at(day, 10)).json()
    moved = client.put(f"/appointments/{appt['id']}", json={
        "starts_at": _at(day, 16), "duration_minutes": 60, "modality": "online",
    }, headers=auth_a)
    assert moved.status_code == 200
    assert moved.json()["modality"] == "online"

    client.post(f"/appointments/{appt['id']}/status", json={"status": "completed"}, headers=auth_a)
    again = client.put(f"/appointments/{appt['id']}", json={
        "starts_at": _at(day, 17), "duration_minutes": 50, "modality": "online",
    }, headers=auth_a)
    assert again.status_code == 409


def test_archived_patient_cannot_be_booked(client, auth_a, patient):
    client.delete(f"/patients/{patient['id']}", headers=auth_a)
    assert _book(client, auth_a, patient["id"], _at(_future_day(), 10)).status_code == 409


# ---------- Status ----------









# ---------- Disponibilidade e horários livres ----------

def test_availability_and_free_slots(client, auth_a, patient):
    day = _future_day()
    client.put("/agenda/availability", json={"slots": [
        {"weekday": day.weekday(), "start_time": "08:00", "end_time": "12:00"},
    ]}, headers=auth_a)

    _book(client, auth_a, patient["id"], _at(day, 8, 50))  # ocupa 08:50-09:40

    slots = client.get("/agenda/free-slots", params={"day": str(day), "duration": 50}, headers=auth_a).json()
    starts = [datetime.fromisoformat(s["starts_at"]).astimezone(SP).strftime("%H:%M") for s in slots]
    assert starts == ["08:00", "09:40", "10:30"]  # 08:50 ocupado; 11:20 não cabe até 12:00


def test_free_slots_resume_right_after_appointment(client, auth_a, patient):
    """Consulta 09:00-09:50: o próximo horário livre é 09:50, não 10:30."""
    day = _future_day(8)
    client.put("/agenda/availability", json={"slots": [
        {"weekday": day.weekday(), "start_time": "08:00", "end_time": "12:00"},
    ]}, headers=auth_a)
    _book(client, auth_a, patient["id"], _at(day, 9))

    slots = client.get("/agenda/free-slots", params={"day": str(day), "duration": 50}, headers=auth_a).json()
    starts = [datetime.fromisoformat(s["starts_at"]).astimezone(SP).strftime("%H:%M") for s in slots]
    assert starts == ["08:00", "09:50", "10:40"]


def test_availability_rejects_overlap(client, auth_a):
    response = client.put("/agenda/availability", json={"slots": [
        {"weekday": 0, "start_time": "08:00", "end_time": "12:00"},
        {"weekday": 0, "start_time": "11:00", "end_time": "13:00"},
    ]}, headers=auth_a)
    assert response.status_code == 422


def test_availability_replace_is_per_user(client, auth_a, auth_b):
    client.put("/agenda/availability", json={"slots": [
        {"weekday": 1, "start_time": "08:00", "end_time": "12:00"}]}, headers=auth_a)
    assert client.get("/agenda/availability", headers=auth_b).json() == []
    assert len(client.get("/agenda/availability", headers=auth_a).json()) == 1


# ---------- Isolamento ----------

def test_other_user_cannot_touch_appointments(client, auth_a, auth_b, patient):
    day = _future_day()
    appt = _book(client, auth_a, patient["id"], _at(day, 10)).json()

    assert client.get(f"/appointments/{appt['id']}", headers=auth_b).status_code == 404
    assert client.post(f"/appointments/{appt['id']}/status", json={"status": "cancelled"},
                       headers=auth_b).status_code == 404
    assert _book(client, auth_b, patient["id"], _at(day, 15)).status_code == 404
    listed = client.get("/appointments", params={"start": _at(day, 0), "end": _at(day + timedelta(days=1), 0)},
                        headers=auth_b).json()
    assert listed == []


def test_overlap_check_is_per_user(client, auth_a, auth_b, patient):
    day = _future_day()
    _book(client, auth_a, patient["id"], _at(day, 10))
    other_patient = client.post("/patients", json={"full_name": "Do B"}, headers=auth_b).json()
    assert _book(client, auth_b, other_patient["id"], _at(day, 10)).status_code == 201


# ---------- Sessões recorrentes ----------


















