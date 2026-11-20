
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func

from app.database.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Psicólogo responsável pelo paciente.
    # RESTRICT: o banco recusa apagar um psicólogo que ainda tem pacientes.
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )

    # NULL = ativo; preenchido = arquivado (os dados são mantidos)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Consentimento do paciente para uso de IA nos registros (NULL = sem consentimento)
    ai_consent_at = Column(DateTime(timezone=True), nullable=True)

    phone = Column(String(20), nullable=True)



class AvailabilitySlot(Base):
    """Horário semanal de atendimento (ex.: segunda, 08:00 às 12:00)."""
    __tablename__ = "availability_slots"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_availability_weekday"),
        CheckConstraint("end_time > start_time", name="ck_availability_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="availability_slots_user_id_fkey"),
        nullable=False,
        index=True
    )
    weekday = Column(SmallInteger, nullable=False)  # 0 = segunda ... 6 = domingo
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)


class Appointment(Base):
    """Consulta agendada. Horários guardados em UTC (com fuso)."""
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="ck_appointments_order"),
        Index("ix_appointments_user_starts", "user_id", "starts_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", name="appointments_user_id_fkey"),
        nullable=False
    )
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT", name="appointments_patient_id_fkey"),
        nullable=False,
        index=True
    )
    starts_at = Column(DateTime(timezone=True), nullable=False)
    ends_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(20), nullable=False)      # scheduled, completed, cancelled, no_show
    modality = Column(String(20), nullable=False)    # presencial, online
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class ClinicalNote(Base):
    """
    Registro de sessão (transcrição + resumo gerado por IA).
    O conteúdo fica CRIPTOGRAFADO no banco (ver app/crypto.py).
    Ciclo: processing -> pending_review -> approved (ou failed).
    """
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT", name="clinical_notes_patient_id_fkey"),
        nullable=False,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", name="clinical_notes_user_id_fkey"),
        nullable=False,
        index=True
    )
    # Consulta à qual o registro pertence (opcional)
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id", ondelete="RESTRICT", name="clinical_notes_appointment_id_fkey"),
        nullable=True,
        index=True
    )
    source = Column(String(10), nullable=False)   # "audio" ou "text"
    status = Column(String(20), nullable=False)
    transcript_encrypted = Column(Text, nullable=True)
    summary_encrypted = Column(Text, nullable=True)
    error_message = Column(String(255), nullable=True)  # mensagem genérica, sem conteúdo clínico
    transcription_model = Column(String(100), nullable=True)
    ai_model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Vai dentro de cada JWT. Aumentar este número invalida todos os
    # tokens antigos do usuário (ex.: ao redefinir a senha).
    token_version = Column(Integer, nullable=False, default=0, server_default="0")

    # NULL = e-mail ainda não confirmado
    email_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Conta de demonstração (portfólio): criada com dados fictícios e apagada
    # automaticamente depois deste horário. NULL = conta normal.
    demo_expires_at = Column(DateTime(timezone=True), nullable=True, index=True)



class UserToken(Base):
    """Token de uso único enviado por e-mail (recuperar senha, confirmar e-mail)."""
    __tablename__ = "user_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="user_tokens_user_id_fkey"),
        nullable=False,
        index=True
    )
    purpose = Column(String(32), nullable=False)

    # Só o hash SHA-256 é guardado; o token em si só existe no e-mail
    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    """
    Cada refresh token emitido (uso único). Só o hash do seu "jti" é guardado.
    Um token já usado que aparece de novo indica roubo: todas as sessões do
    usuário são encerradas (ver crud.use_refresh_token).
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE", name="refresh_tokens_user_id_fkey"),
        nullable=False,
        index=True
    )
    jti_hash = Column(String(64), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """
    Trilha de auditoria: quem fez o quê, quando e de onde.
    Somente inserção (no PostgreSQL um gatilho recusa UPDATE/DELETE).
    Guarda apenas IDs, nunca dados pessoais ou clínicos.
    """
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    # BigInteger no PostgreSQL (muitos registros); Integer no SQLite dos testes
    id = Column(BigInteger().with_variant(Integer(), "sqlite"), primary_key=True)
    occurred_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Sem ForeignKey de propósito: o histórico sobrevive a qualquer exclusão
    user_id = Column(Integer, nullable=True, index=True)

    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=True)
