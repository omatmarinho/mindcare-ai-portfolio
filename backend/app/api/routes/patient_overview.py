"""
Visão geral de um paciente: frequência e histórico de consultas.

Só números, datas e situações das consultas: nenhum conteúdo clínico (os
registros são contados, não lidos). Cada acesso fica na auditoria.
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import audit, insights
from app.api.deps import get_current_user
from app.api.routes.agenda import _response as appointment_response
from app.database import crud
from app.database.database import get_db
from app.database.models import Appointment, ClinicalNote, User
from app.schemas import PatientOverview
from app.timeutils import local_date, local_tz, now_utc

router = APIRouter(tags=["Pacientes"], dependencies=[Depends(get_current_user)])

RECENT_LIMIT = 10


@router.get("/patients/{patient_id}/overview", response_model=PatientOverview)
def patient_overview(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = crud.get_patient(db, owner_id=current_user.id, patient_id=patient_id)
    if patient is None:
        audit.record(db, request, audit.PATIENT_ACCESS_DENIED, user_id=current_user.id,
                     resource_type=audit.RESOURCE_PATIENT, resource_id=patient_id,
                     details={"method": request.method})
        raise HTTPException(status_code=404, detail="Paciente não encontrado")

    now = now_utc()
    base = db.query(Appointment).filter(
        Appointment.user_id == current_user.id, Appointment.patient_id == patient.id
    )
    counts = dict(
        db.query(Appointment.status, func.count(Appointment.id))
        .filter(Appointment.user_id == current_user.id, Appointment.patient_id == patient.id)
        .group_by(Appointment.status).all()
    )
    attended = base.filter(Appointment.status == "completed")
    first = attended.order_by(Appointment.starts_at).first()
    last = attended.order_by(Appointment.starts_at.desc()).first()
    upcoming = base.filter(Appointment.status == "scheduled", Appointment.starts_at >= now) \
        .order_by(Appointment.starts_at).first()
    recent = base.filter(Appointment.starts_at < now).order_by(Appointment.starts_at.desc()).limit(RECENT_LIMIT).all()

    today = now.astimezone(local_tz()).date()
    notes_count = db.query(func.count(ClinicalNote.id)).filter(
        ClinicalNote.user_id == current_user.id, ClinicalNote.patient_id == patient.id
    ).scalar()

    audit.record(db, request, audit.PATIENT_OVERVIEW, user_id=current_user.id,
                 resource_type=audit.RESOURCE_PATIENT, resource_id=patient.id)

    def day(appt: Appointment | None) -> date | None:
        return local_date(appt.starts_at) if appt else None

    return PatientOverview(
        sessions_completed=counts.get("completed", 0),
        sessions_no_show=counts.get("no_show", 0),
        sessions_cancelled=counts.get("cancelled", 0),
        first_session=day(first),
        last_session=day(last),
        next_appointment=appointment_response(db, upcoming) if upcoming else None,
        notes_count=notes_count,
        months=insights.month_series(db, current_user.id, today, patient_id=patient.id),
        recent=[appointment_response(db, a) for a in recent],
    )
