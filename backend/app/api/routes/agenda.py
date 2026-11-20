"""
Agenda: horários de atendimento, consultas e horários livres.

Regras:
- Cada psicólogo só vê e altera a própria agenda (isolamento por user_id).
- Duas consultas ativas (agendada/realizada) do mesmo psicólogo não podem
  se sobrepor.
- Consultas não são apagadas: são CANCELADAS (o histórico fica).
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app import audit, scheduling
from app.api.deps import get_current_user
from app.database import crud
from app.database.database import get_db
from app.database.models import Appointment, AvailabilitySlot, Patient, User
from app.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    AvailabilityReplace,
    AvailabilitySlotOut,
    FreeSlot,
)
from app.timeutils import as_utc, local_tz, now_utc, to_utc

router = APIRouter(tags=["Agenda"], dependencies=[Depends(get_current_user)])

ACTIVE_STATUSES = ("scheduled", "completed")
MAX_RANGE_DAYS = 62


# ---------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------

def _owned_appointment(db: Session, request: Request, user: User, appointment_id: int) -> Appointment:
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.user_id == user.id
    ).first()
    if appointment is None:
        audit.record(db, request, audit.APPOINTMENT_ACCESS_DENIED, user_id=user.id,
                     resource_type=audit.RESOURCE_APPOINTMENT, resource_id=appointment_id,
                     details={"method": request.method})
        raise HTTPException(status_code=404, detail="Consulta não encontrada")
    return appointment


def _active_patient(db: Session, user: User, patient_id: int) -> Patient:
    patient = crud.get_patient(db, owner_id=user.id, patient_id=patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Paciente não encontrado")
    if patient.archived_at is not None:
        raise HTTPException(status_code=409, detail="Paciente arquivado. Restaure-o para agendar.")
    return patient


def _has_overlap(db: Session, user: User, starts_at: datetime, ends_at: datetime, ignore_id: int | None = None) -> bool:
    query = db.query(Appointment).filter(
        Appointment.user_id == user.id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
    )
    if ignore_id is not None:
        query = query.filter(Appointment.id != ignore_id)
    return query.first() is not None


def _check_overlap(db: Session, user: User, starts_at: datetime, ends_at: datetime, ignore_id: int | None = None):
    if _has_overlap(db, user, starts_at, ends_at, ignore_id):
        raise HTTPException(status_code=409, detail="Já existe uma consulta nesse horário.")


def _response(db: Session, appointment: Appointment) -> AppointmentResponse:
    patient = db.get(Patient, appointment.patient_id)
    return AppointmentResponse(
        id=appointment.id,
        patient_id=appointment.patient_id,
        patient_name=patient.full_name if patient else None,
        starts_at=as_utc(appointment.starts_at),
        ends_at=as_utc(appointment.ends_at),
        status=appointment.status,
        modality=appointment.modality,
    )


def _audit_appointment(db, request, action, user, appointment_id, details=None):
    audit.record(db, request, action, user_id=user.id,
                 resource_type=audit.RESOURCE_APPOINTMENT, resource_id=appointment_id, details=details)


# ---------------------------------------------------------------------
# Horários de atendimento (disponibilidade)
# ---------------------------------------------------------------------

@router.get("/agenda/availability", response_model=list[AvailabilitySlotOut])
def get_availability(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(AvailabilitySlot)
        .filter(AvailabilitySlot.user_id == current_user.id)
        .order_by(AvailabilitySlot.weekday, AvailabilitySlot.start_time)
        .all()
    )


@router.put("/agenda/availability", response_model=list[AvailabilitySlotOut])
def replace_availability(
    request: Request,
    data: AvailabilityReplace,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Substitui todos os horários de atendimento de uma vez."""
    for slot in data.slots:
        if slot.end_time <= slot.start_time:
            raise HTTPException(status_code=422, detail="O fim de cada horário deve ser depois do início.")

    # Sem sobreposição dentro do mesmo dia da semana
    by_day: dict[int, list] = {}
    for slot in sorted(data.slots, key=lambda s: (s.weekday, s.start_time)):
        previous = by_day.setdefault(slot.weekday, [])
        if previous and slot.start_time < previous[-1].end_time:
            raise HTTPException(status_code=422, detail="Há horários sobrepostos no mesmo dia.")
        previous.append(slot)

    db.query(AvailabilitySlot).filter(AvailabilitySlot.user_id == current_user.id).delete()
    for slot in data.slots:
        db.add(AvailabilitySlot(user_id=current_user.id, **slot.model_dump()))
    db.commit()

    audit.record(db, request, audit.AVAILABILITY_UPDATE, user_id=current_user.id,
                 details={"slots": len(data.slots)})
    return get_availability(db, current_user)


@router.get("/agenda/free-slots", response_model=list[FreeSlot])
def free_slots(
    day: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Data no formato AAAA-MM-DD"),
    duration: int = Query(default=50, ge=10, le=480),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Horários livres de um dia: disponibilidade - consultas ativas - pedidos on-line pendentes - passado."""
    try:
        target = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Data inválida.")
    return [
        FreeSlot(starts_at=s, ends_at=e)
        for s, e in scheduling.free_slots(db, current_user.id, target, duration, not_before=now_utc())
    ]


# ---------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------

@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(
    request: Request,
    start: datetime,
    end: datetime,
    patient_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start_utc, end_utc = to_utc(start), to_utc(end)
    if end_utc <= start_utc or end_utc - start_utc > timedelta(days=MAX_RANGE_DAYS):
        raise HTTPException(status_code=422, detail=f"Intervalo inválido (máximo de {MAX_RANGE_DAYS} dias).")

    query = db.query(Appointment).filter(
        Appointment.user_id == current_user.id,
        Appointment.starts_at < end_utc,
        Appointment.ends_at > start_utc,
    )
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)
    appointments = query.order_by(Appointment.starts_at).all()

    audit.record(db, request, audit.APPOINTMENT_LIST, user_id=current_user.id,
                 resource_type=audit.RESOURCE_APPOINTMENT, details={"count": len(appointments)})
    return [_response(db, a) for a in appointments]


@router.post("/appointments", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    request: Request,
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = _active_patient(db, current_user, data.patient_id)
    starts_at = to_utc(data.starts_at)
    ends_at = starts_at + timedelta(minutes=data.duration_minutes)
    _check_overlap(db, current_user, starts_at, ends_at)

    appointment = Appointment(
        user_id=current_user.id,
        patient_id=patient.id,
        starts_at=starts_at,
        ends_at=ends_at,
        status="scheduled",
        modality=data.modality,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    _audit_appointment(db, request, audit.APPOINTMENT_CREATE, current_user, appointment.id,
                       details={"patient_id": patient.id})
    return _response(db, appointment)


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def read_appointment(
    request: Request,
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return _response(db, _owned_appointment(db, request, current_user, appointment_id))


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    request: Request,
    appointment_id: int,
    data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remarca ou altera uma consulta ainda agendada."""
    appointment = _owned_appointment(db, request, current_user, appointment_id)
    if appointment.status != "scheduled":
        raise HTTPException(status_code=409, detail="Só é possível alterar consultas agendadas.")

    starts_at = to_utc(data.starts_at)
    ends_at = starts_at + timedelta(minutes=data.duration_minutes)
    _check_overlap(db, current_user, starts_at, ends_at, ignore_id=appointment.id)

    appointment.starts_at = starts_at
    appointment.ends_at = ends_at
    appointment.modality = data.modality
    appointment.updated_at = now_utc()
    db.commit()
    db.refresh(appointment)

    _audit_appointment(db, request, audit.APPOINTMENT_UPDATE, current_user, appointment.id)
    return _response(db, appointment)


@router.post("/appointments/{appointment_id}/status", response_model=AppointmentResponse)
def change_status(
    request: Request,
    appointment_id: int,
    data: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = _owned_appointment(db, request, current_user, appointment_id)
    previous = appointment.status
    if previous == data.status:
        return _response(db, appointment)

    if data.status == "scheduled":
        _check_overlap(db, current_user, as_utc(appointment.starts_at), as_utc(appointment.ends_at),
                       ignore_id=appointment.id)

    appointment.status = data.status
    appointment.updated_at = now_utc()

    db.commit()
    db.refresh(appointment)

    _audit_appointment(db, request, audit.APPOINTMENT_STATUS, current_user, appointment.id,
                       details={"from": previous, "to": data.status})
    return _response(db, appointment)
