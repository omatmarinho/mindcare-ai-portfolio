"""
Trilha de auditoria.

Uso nas rotas:
    audit.record(db, request, "patient.read", user_id=..., resource_id=...)

REGRA: nunca coloque dados pessoais ou clínicos em "details" (nomes,
e-mails, conteúdo de registros, senhas, tokens). Guarde apenas IDs e
informações técnicas. O log precisa ser seguro de ler.
"""
from fastapi import Request
from sqlalchemy.orm import Session

from app.database.models import AuditLog

# Ações registradas
LOGIN_SUCCESS = "auth.login_success"
LOGIN_FAILED = "auth.login_failed"
LOGIN_BLOCKED_UNVERIFIED = "auth.login_blocked_unverified"
REGISTER = "auth.register"
REGISTER_EXISTING_EMAIL = "auth.register_existing_email"
PASSWORD_RESET_REQUESTED = "auth.password_reset_requested"
PASSWORD_RESET_COMPLETED = "auth.password_reset_completed"
PASSWORD_RESET_INVALID_TOKEN = "auth.password_reset_invalid_token"
EMAIL_VERIFIED = "auth.email_verified"
TOKEN_REFRESH = "auth.token_refresh"
TOKEN_REUSE_DETECTED = "auth.token_reuse_detected"
LOGOUT = "auth.logout"
AUDIT_LOG_VIEW = "audit.view"

PATIENT_CREATE = "patient.create"
PATIENT_LIST = "patient.list"
PATIENT_READ = "patient.read"
PATIENT_UPDATE = "patient.update"
PATIENT_ARCHIVE = "patient.archive"
PATIENT_RESTORE = "patient.restore"
PATIENT_ACCESS_DENIED = "patient.access_denied"
PATIENT_EXPORT = "patient.export"
PATIENT_OVERVIEW = "patient.overview"

PATIENT_AI_CONSENT_GIVEN = "patient.ai_consent_given"
PATIENT_AI_CONSENT_REVOKED = "patient.ai_consent_revoked"

NOTE_CREATE = "note.create"
NOTE_LIST = "note.list"
NOTE_READ = "note.read"
NOTE_UPDATE = "note.update"
NOTE_APPROVE = "note.approve"
NOTE_ACCESS_DENIED = "note.access_denied"

NOTE_RETRY = "note.retry"

AVAILABILITY_UPDATE = "agenda.availability_update"
APPOINTMENT_CREATE = "appointment.create"
APPOINTMENT_UPDATE = "appointment.update"
APPOINTMENT_STATUS = "appointment.status"
APPOINTMENT_LIST = "appointment.list"
APPOINTMENT_ACCESS_DENIED = "appointment.access_denied"


DASHBOARD_VIEW = "dashboard.view"
DEMO_SESSION_START = "demo.session_start"

RESOURCE_PATIENT = "patient"
RESOURCE_NOTE = "clinical_note"
RESOURCE_APPOINTMENT = "appointment"


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def record(
    db: Session,
    request: Request,
    action: str,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Grava um evento de auditoria e confirma a transação."""
    user_agent = request.headers.get("user-agent")

    db.add(AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=_client_ip(request),
        user_agent=user_agent[:255] if user_agent else None,
        details=details,
    ))
    db.commit()


def record_system(
    db: Session,
    action: str,
    user_id: int | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Evento gerado por uma rotina automática (sem requisição, sem IP)."""
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=None,
        user_agent="mindcare-rotina",
        details=details,
    ))
    db.commit()
