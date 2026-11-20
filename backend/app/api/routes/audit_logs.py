from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import get_current_user
from app.database.database import get_db
from app.database.models import AuditLog, User
from app.schemas import AuditLogResponse

router = APIRouter(
    prefix="/audit-logs",
    tags=["Auditoria"],
    dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[AuditLogResponse])
def list_my_audit_logs(
    request: Request,
    patient_id: int | None = Query(default=None, description="Filtra pelo histórico de um paciente"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Histórico de ações do PRÓPRIO psicólogo, do mais recente ao mais antigo.
    Com patient_id: tudo o que foi feito com aquele paciente.
    Nunca mostra ações de outras contas.
    """
    query = db.query(AuditLog).filter(AuditLog.user_id == current_user.id)

    if patient_id is not None:
        query = query.filter(
            AuditLog.resource_type == audit.RESOURCE_PATIENT,
            AuditLog.resource_id == patient_id
        )

    logs = (
        query.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Consultar a auditoria também é registrado (depois da leitura,
    # para o próprio registro não aparecer na resposta)
    audit.record(
        db, request, audit.AUDIT_LOG_VIEW,
        user_id=current_user.id,
        resource_type=audit.RESOURCE_PATIENT if patient_id is not None else None,
        resource_id=patient_id,
    )
    return logs
