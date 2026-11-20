"""
Horários livres de um psicólogo.

Livre = dentro dos horários de atendimento, sem consulta ativa (agendada/realizada)
e não antes de `not_before`.
"""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.database.models import Appointment, AvailabilitySlot
from app.timeutils import as_utc, local_tz, to_utc

ACTIVE_STATUSES = ("scheduled", "completed")


def busy_intervals(db: Session, user_id: int, start: datetime, end: datetime) -> list[tuple[datetime, datetime]]:
    rows = db.query(Appointment.starts_at, Appointment.ends_at).filter(
        Appointment.user_id == user_id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.starts_at < end,
        Appointment.ends_at > start,
    )
    return [(as_utc(s), as_utc(e)) for s, e in rows]


def free_slots(db: Session, user_id: int, target: date, duration: int, not_before: datetime) -> list[tuple[datetime, datetime]]:
    """Horários livres de um dia (horário local), cada um com `duration` minutos."""
    tz = local_tz()
    slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.user_id == user_id,
        AvailabilitySlot.weekday == target.weekday()
    ).order_by(AvailabilitySlot.start_time).all()
    if not slots:
        return []

    day_start = to_utc(datetime.combine(target, datetime.min.time(), tzinfo=tz))
    busy = busy_intervals(db, user_id, day_start, day_start + timedelta(days=1))

    length = timedelta(minutes=duration)
    result = []
    for slot in slots:
        cursor = to_utc(datetime.combine(target, slot.start_time, tzinfo=tz))
        limit = to_utc(datetime.combine(target, slot.end_time, tzinfo=tz))
        while cursor + length <= limit:
            end = cursor + length
            clashes = [e for s, e in busy if s < end and e > cursor]
            if clashes:
                cursor = max(clashes)  # pula para o fim do que ocupa o horário
                continue
            if cursor >= not_before:
                result.append((cursor.astimezone(tz), end.astimezone(tz)))
            cursor = end
    return result
