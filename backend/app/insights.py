"""
Indicadores do consultório (gráficos e listas do painel).

Tudo é calculado só com dados do próprio psicólogo (filtro por user_id) e
devolve apenas contagens, datas e nomes: nenhum conteúdo clínico.
As somas por mês são feitas em Python para funcionar igual no Postgres e no
SQLite dos testes; o volume por psicólogo é pequeno.
"""
from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import Appointment, Patient
from app.schemas import AttendanceCounts, InactivePatient, MonthPoint
from app.timeutils import as_utc, local_date, local_tz, to_utc

ACTIVE_STATUSES = ("scheduled", "completed", "no_show")


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def last_months(today: date, count: int) -> list[str]:
    """Os `count` últimos meses, do mais antigo ao atual: ["2026-06", ..., "2026-11"]."""
    year, month = today.year, today.month
    keys = []
    for _ in range(count):
        keys.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(keys))


def month_series(db: Session, user_id: int, today: date, months: int = 6,
                 patient_id: int | None = None) -> list[MonthPoint]:
    """Sessões realizadas e faltas por mês (horário local)."""
    keys = last_months(today, months)
    first_day = date.fromisoformat(f"{keys[0]}-01")
    since, _ = day_bounds(first_day)
    query = db.query(Appointment.status, Appointment.starts_at).filter(
        Appointment.user_id == user_id,
        Appointment.status.in_(("completed", "no_show")),
        Appointment.starts_at >= since,
    )
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)

    completed, no_show = Counter(), Counter()
    for status, starts_at in query:
        (completed if status == "completed" else no_show)[month_key(local_date(starts_at))] += 1
    return [MonthPoint(month=k, completed=completed[k], no_show=no_show[k]) for k in keys]


def attendance(db: Session, user_id: int, since: datetime, until: datetime,
               patient_id: int | None = None) -> AttendanceCounts:
    """Consultas que já aconteceram no período, por situação."""
    query = db.query(Appointment.status, func.count(Appointment.id)).filter(
        Appointment.user_id == user_id,
        Appointment.starts_at >= since,
        Appointment.starts_at < until,
    )
    if patient_id is not None:
        query = query.filter(Appointment.patient_id == patient_id)
    counts = dict(query.group_by(Appointment.status).all())
    return AttendanceCounts(
        completed=counts.get("completed", 0),
        no_show=counts.get("no_show", 0),
        cancelled=counts.get("cancelled", 0),
        scheduled=counts.get("scheduled", 0),  # já passaram mas ninguém marcou o resultado
    )


def weekday_load(db: Session, user_id: int, since: datetime, until: datetime) -> list[int]:
    """Consultas (não canceladas) por dia da semana: índice 0 = segunda ... 6 = domingo."""
    rows = db.query(Appointment.starts_at).filter(
        Appointment.user_id == user_id,
        Appointment.status.in_(ACTIVE_STATUSES),
        Appointment.starts_at >= since,
        Appointment.starts_at < until,
    )
    load = [0] * 7
    for (starts_at,) in rows:
        load[local_date(starts_at).weekday()] += 1
    return load


def inactive_patients(db: Session, user_id: int, now: datetime, days: int = 30, limit: int = 5) -> list[InactivePatient]:
    """Pacientes ativos sem consulta nos últimos `days` dias e sem nada marcado à frente.

    Ajuda o psicólogo a lembrar de quem "sumiu". Ordena pelo mais tempo sem vir.
    """
    last = dict(
        db.query(Appointment.patient_id, func.max(Appointment.starts_at))
        .filter(Appointment.user_id == user_id, Appointment.status.in_(ACTIVE_STATUSES))
        .group_by(Appointment.patient_id)
        .all()
    )
    cutoff = now - timedelta(days=days)
    patients = db.query(Patient.id, Patient.full_name, Patient.created_at).filter(
        Patient.user_id == user_id, Patient.archived_at.is_(None)
    )
    result = []
    for patient_id, name, created_at in patients:
        last_at = last.get(patient_id)
        if last_at is not None:
            if as_utc(last_at) >= cutoff:
                continue  # veio recentemente ou tem consulta marcada à frente
            result.append(InactivePatient(id=patient_id, full_name=name, last_session=local_date(last_at)))
        elif created_at is not None and as_utc(created_at) < cutoff:
            result.append(InactivePatient(id=patient_id, full_name=name, last_session=None))
    # Sem nenhuma sessão primeiro; depois quem está há mais tempo sem vir
    result.sort(key=lambda p: (p.last_session is not None, p.last_session or date.min))
    return result[:limit]


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """Início e fim (UTC) de um dia no horário local."""
    start = to_utc(datetime.combine(day, datetime.min.time(), tzinfo=local_tz()))
    return start, start + timedelta(days=1)
