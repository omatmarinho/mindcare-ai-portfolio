"""Trilha de auditoria: o que é registrado e o que NUNCA pode ser registrado."""
import json

from app import audit
from app.database.models import AuditLog
from tests.conftest import TEST_PASSWORD

PATIENT_NAME = "Maria Ficticia da Silva"
PATIENT_EMAIL = "maria.ficticia@exemplo.com"


def _actions(db_session):
    return [log.action for log in db_session.query(AuditLog).order_by(AuditLog.id)]


def _logs(db_session, action):
    return db_session.query(AuditLog).filter(AuditLog.action == action).all()


def _create_patient(client, headers):
    return client.post(
        "/patients",
        json={"full_name": PATIENT_NAME, "email": PATIENT_EMAIL},
        headers=headers,
    ).json()


# ---------- Autenticação ----------

def test_successful_login_is_recorded(client, db_session, user_a, auth_a):
    log = _logs(db_session, audit.LOGIN_SUCCESS)[-1]
    assert log.user_id == user_a.id
    assert log.ip_address  # de onde veio
    assert log.occurred_at is not None


def test_failed_login_is_recorded_without_typed_email(client, db_session, user_a):
    client.post("/auth/login", data={"username": user_a.email, "password": "SenhaErrada123!"})

    log = _logs(db_session, audit.LOGIN_FAILED)[-1]
    assert log.user_id is None
    assert user_a.email not in json.dumps(log.details or {})


def test_password_reset_is_recorded(client, db_session, user_a, outbox):
    client.post("/auth/password-reset/request", json={"email": user_a.email})
    assert _logs(db_session, audit.PASSWORD_RESET_REQUESTED)[-1].user_id == user_a.id


# ---------- Pacientes ----------

def test_every_patient_operation_is_recorded(client, db_session, user_a, auth_a):
    patient = _create_patient(client, auth_a)
    pid = patient["id"]

    client.get("/patients", headers=auth_a)
    client.get(f"/patients/{pid}", headers=auth_a)
    client.put(f"/patients/{pid}", json={"full_name": "Novo Nome"}, headers=auth_a)
    client.delete(f"/patients/{pid}", headers=auth_a)
    client.post(f"/patients/{pid}/restore", headers=auth_a)

    patient_actions = [a for a in _actions(db_session) if a.startswith("patient.")]
    assert patient_actions == [
        audit.PATIENT_CREATE,
        audit.PATIENT_LIST,
        audit.PATIENT_READ,
        audit.PATIENT_UPDATE,
        audit.PATIENT_ARCHIVE,
        audit.PATIENT_RESTORE,
    ]

    for log in db_session.query(AuditLog).filter(AuditLog.action.like("patient.%")):
        assert log.user_id == user_a.id
        assert log.resource_type == "patient"
        if log.action != audit.PATIENT_LIST:
            assert log.resource_id == pid


def test_cross_account_attempt_is_recorded(client, db_session, user_b, auth_a, auth_b):
    patient = _create_patient(client, auth_a)

    client.get(f"/patients/{patient['id']}", headers=auth_b)

    log = _logs(db_session, audit.PATIENT_ACCESS_DENIED)[-1]
    assert log.user_id == user_b.id
    assert log.resource_id == patient["id"]


def test_update_records_field_names_not_values(client, db_session, auth_a):
    patient = _create_patient(client, auth_a)
    client.put(
        f"/patients/{patient['id']}",
        json={"full_name": "Nome Secreto Novo", "email": "secreto@exemplo.com"},
        headers=auth_a,
    )
    log = _logs(db_session, audit.PATIENT_UPDATE)[-1]
    assert log.details == {"fields": ["email", "full_name"]}


def test_audit_log_never_contains_personal_data(client, db_session, user_a, auth_a, outbox):
    """Varre TODOS os registros procurando dados pessoais ou segredos."""
    patient = _create_patient(client, auth_a)
    client.get(f"/patients/{patient['id']}", headers=auth_a)
    client.put(
        f"/patients/{patient['id']}",
        json={"full_name": PATIENT_NAME + " Editado", "email": PATIENT_EMAIL},
        headers=auth_a,
    )
    client.post("/auth/login", data={"username": user_a.email, "password": "SenhaErrada123!"})
    client.post("/auth/password-reset/request", json={"email": user_a.email})

    forbidden = [PATIENT_NAME, PATIENT_EMAIL, user_a.email, TEST_PASSWORD, "SenhaErrada123!"]
    for log in db_session.query(AuditLog).all():
        dump = json.dumps({
            "action": log.action, "details": log.details,
            "resource_type": log.resource_type, "user_agent": log.user_agent,
        })
        for value in forbidden:
            assert value not in dump, f"'{value}' vazou no log {log.action}"


def test_user_agent_is_truncated(client, db_session, user_a):
    client.post(
        "/auth/login",
        data={"username": user_a.email, "password": TEST_PASSWORD},
        headers={"User-Agent": "x" * 1000},
    )
    log = _logs(db_session, audit.LOGIN_SUCCESS)[-1]
    assert len(log.user_agent) == 255
