"""
Modo demonstração (portfólio).

Cada visitante ganha uma conta PRÓPRIA e temporária, já com pacientes, agenda e
registros FICTÍCIOS. Ninguém vê o que outro visitante escreveu, e a conta é
apagada por inteiro depois de DEMO_TTL_HOURS (padrão: 24 h).

Liga com DEMO_MODE=true. Com ele ligado, cadastro e recuperação de senha ficam
fechados (não há e-mail de verdade na demonstração).
"""
import os
import secrets
import unicodedata
from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from app import crypto
from app.ai import demo as demo_ai
from app.database.models import (
    Appointment,
    AuditLog,
    AvailabilitySlot,
    ClinicalNote,
    Patient,
    RefreshToken,
    User,
    UserToken,
)
from app.security import hash_password
from app.timeutils import local_tz, now_utc, to_utc

# Nomes claramente fictícios. Nenhum dado real é usado na demonstração.
PATIENTS = [
    ("Ana Fictícia Souza", True),
    ("Bruno Exemplo Lima", True),
    ("Carla Teste Ribeiro", True),
    ("Diego Modelo Alves", False),  # sem consentimento para IA: mostra o bloqueio
    ("Elisa Demo Castro", True),
    ("Fábio Simulado Rocha", True),
    ("Gabriela Ficção Mendes", True),
    ("Henrique Teste Nunes", True),
    ("Isabela Exemplo Prado", True),
    ("João Demo Farias", True),
]

# (dia da semana, hora) fixos por paciente: 0 = segunda
SLOTS = [(0, 9), (0, 14), (1, 10), (2, 15), (3, 9), (4, 11), (1, 16), (2, 10), (3, 14), (4, 15)]

APPROVED_TEXT = (
    "Paciente contou que conseguiu manter a rotina de sono combinada. "
    "Falou sobre a pressão no trabalho com o novo projeto e sobre a vontade de pedir ajuda à equipe. "
    "Combinamos que ele vai observar em quais situações sente mais cansaço. "
    "Na próxima sessão vamos retomar o tema das expectativas no trabalho."
)


def enabled() -> bool:
    return os.getenv("DEMO_MODE", "false").lower() in ("1", "true", "yes")


def ttl() -> timedelta:
    return timedelta(hours=int(os.getenv("DEMO_TTL_HOURS", "24")))


def max_active() -> int:
    return int(os.getenv("DEMO_MAX_ACTIVE", "300"))


def delete_user_data(db: Session, user_id: int) -> None:
    """Apaga TUDO de uma conta de demonstração (na ordem das chaves estrangeiras)."""
    for model in (ClinicalNote, Appointment, Patient, AvailabilitySlot, UserToken, RefreshToken):
        db.query(model).filter(model.user_id == user_id).delete(synchronize_session=False)
    # A auditoria guarda IP e navegador do visitante: some junto com a conta. No PostgreSQL
    # a tabela é imutável (gatilho) e fica, como em produção.
    if db.get_bind().dialect.name != "postgresql":
        db.query(AuditLog).filter(AuditLog.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)


def purge_expired(db: Session) -> int:
    expired = [uid for (uid,) in db.query(User.id).filter(
        User.demo_expires_at.isnot(None), User.demo_expires_at < now_utc()
    )]
    for uid in expired:
        delete_user_data(db, uid)
    db.commit()
    return len(expired)


def active_count(db: Session) -> int:
    return db.query(User).filter(User.demo_expires_at.isnot(None)).count()


def _at(day, hour: int) -> datetime:
    return to_utc(datetime.combine(day, time(hour, 0), tzinfo=local_tz()))


def _note(user: User, patient: Patient, appointment: Appointment | None, text: str, status: str) -> ClinicalNote:
    now = now_utc()
    return ClinicalNote(
        user_id=user.id, patient_id=patient.id, appointment_id=appointment.id if appointment else None,
        source="text", status=status,
        transcript_encrypted=crypto.encrypt_text(text),
        summary_encrypted=crypto.encrypt_json(demo_ai.summarize(text).model_dump()),
        transcription_model=None, ai_model="demo (regras simples)",
        created_at=now, updated_at=now, approved_at=now if status == "approved" else None,
    )


def create_demo_user(db: Session) -> User:
    now = now_utc()
    user = User(
        full_name="Psicóloga Demonstração",
        # Nenhum e-mail é enviado na demonstração (cadastro e recuperação de senha fechados)
        email=f"demo-{secrets.token_hex(8)}@exemplo.com",
        # Senha aleatória que ninguém conhece: a conta só é acessada pelo botão da demonstração
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        email_verified_at=now,
        demo_expires_at=now + ttl(),
    )
    db.add(user)
    db.flush()

    # Horários de atendimento: segunda a sexta, 08-12 e 13-18
    for weekday in range(5):
        db.add(AvailabilitySlot(user_id=user.id, weekday=weekday, start_time=time(8), end_time=time(12)))
        db.add(AvailabilitySlot(user_id=user.id, weekday=weekday, start_time=time(13), end_time=time(18)))

    patients = []
    for index, (name, consent) in enumerate(PATIENTS):
        first = unicodedata.normalize("NFKD", name.split()[0].lower()).encode("ascii", "ignore").decode()
        patient = Patient(
            user_id=user.id, full_name=name, email=f"{first}@exemplo.com",
            ai_consent_at=now - timedelta(days=200 - index * 12) if consent else None,
            created_at=now - timedelta(days=200 - index * 12),
        )
        db.add(patient)
        patients.append(patient)
    db.flush()

    # 6 meses para trás e 2 semanas para a frente, uma sessão semanal por paciente
    today = now.astimezone(local_tz()).date()
    monday = today - timedelta(days=today.weekday())
    last_by_patient: dict[int, Appointment] = {}
    for index, patient in enumerate(patients):
        weekday, hour = SLOTS[index]
        for week in range(-26, 3):
            day = monday + timedelta(weeks=week, days=weekday)
            starts = _at(day, hour)
            if starts < patient.created_at:
                continue  # antes do cadastro do paciente
            if starts > now:
                status = "scheduled"
            elif (week + index) % 7 == 0:
                status = "no_show"
            elif (week * 3 + index) % 11 == 0:
                status = "cancelled"
            else:
                status = "completed"
            appointment = Appointment(
                user_id=user.id, patient_id=patient.id, starts_at=starts,
                ends_at=starts + timedelta(minutes=50), status=status,
                modality="online" if index % 3 == 2 else "presencial",
            )
            db.add(appointment)
            if status == "completed":
                last_by_patient[patient.id] = appointment
    db.flush()

    # Registros: um aprovado e um esperando revisão (para o visitante aprovar)
    db.add(_note(user, patients[1], last_by_patient.get(patients[1].id), APPROVED_TEXT, "approved"))
    db.add(_note(user, patients[0], last_by_patient.get(patients[0].id), demo_ai.SAMPLE_TRANSCRIPT, "pending_review"))
    db.commit()
    db.refresh(user)
    return user
