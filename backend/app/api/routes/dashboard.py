"""
Resumo do dia: o que o psicólogo precisa ver ao abrir o MindCare.

- Consultas de hoje (horário local), menos as canceladas.
- Registros com IA esperando revisão, e os que falharam.
- Indicadores para os gráficos: sessões de 6 meses, comparecimento em 30 dias,
  movimento por dia da semana, próximas sessões e pacientes sem vir há 30 dias.

Só contagens, horários e nomes: nenhum conteúdo clínico é devolvido aqui.
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import audit, insights
from app.api.deps import get_current_user
from app.api.routes.agenda import _response as appointment_response
from app.database.database import get_db
from app.database.models import Appointment, ClinicalNote, Patient, User
from app.schemas import DashboardInsights, DashboardNote, DashboardSummary
from app.timeutils import local_tz, now_utc, to_utc

router = APIRouter(prefix="/dashboard", tags=["Resumo do dia"], dependencies=[Depends(get_current_user)])

NOTES_LIMIT = 20
UPCOMING_LIMIT = 15


def _notes(db: Session, user: User, status: str) -> list[DashboardNote]:
    rows = (
        db.query(ClinicalNote.id, ClinicalNote.patient_id, Patient.full_name,
                 ClinicalNote.status, ClinicalNote.created_at)
        .join(Patient, Patient.id == ClinicalNote.patient_id)
        .filter(ClinicalNote.user_id == user.id, ClinicalNote.status == status)
        .order_by(ClinicalNote.created_at)
        .limit(NOTES_LIMIT)
        .all()
    )
    return [
        DashboardNote(id=r[0], patient_id=r[1], patient_name=r[2], status=r[3], created_at=r[4])
        for r in rows
    ]


@router.get("", response_model=DashboardSummary)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tz = local_tz()
    today = now_utc().astimezone(tz).date()
    day_start = to_utc(datetime.combine(today, datetime.min.time(), tzinfo=tz))
    day_end = day_start + timedelta(days=1)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.user_id == current_user.id,
            Appointment.starts_at >= day_start,
            Appointment.starts_at < day_end,
            Appointment.status != "cancelled",
        )
        .order_by(Appointment.starts_at)
        .all()
    )

    month_start = today.replace(day=1)
    now = now_utc()
    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.user_id == current_user.id,
            Appointment.starts_at >= day_end,
            Appointment.starts_at < day_end + timedelta(days=7),
            Appointment.status == "scheduled",
        )
        .order_by(Appointment.starts_at)
        .limit(UPCOMING_LIMIT)
        .all()
    )
    active_patients = db.query(func.count(Patient.id)).filter(
        Patient.user_id == current_user.id, Patient.archived_at.is_(None)
    ).scalar()
    month_start_utc, _ = insights.day_bounds(month_start)
    new_patients = db.query(func.count(Patient.id)).filter(
        Patient.user_id == current_user.id, Patient.created_at >= month_start_utc
    ).scalar()
    panel = DashboardInsights(
        months=insights.month_series(db, current_user.id, today),
        attendance_30d=insights.attendance(db, current_user.id, now - timedelta(days=30), now),
        weekday_load=insights.weekday_load(db, current_user.id, now - timedelta(weeks=8), now),
        active_patients=active_patients,
        new_patients_month=new_patients,
        upcoming=[appointment_response(db, a) for a in upcoming],
        inactive_patients=insights.inactive_patients(db, current_user.id, now),
    )

    audit.record(db, request, audit.DASHBOARD_VIEW, user_id=current_user.id)

    return DashboardSummary(
        date=today,
        appointments_today=[appointment_response(db, a) for a in appointments],
        notes_to_review=_notes(db, current_user, "pending_review"),
        notes_failed=_notes(db, current_user, "failed"),
        insights=panel,
    )
