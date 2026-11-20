import re
from datetime import date, datetime, time
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------
# Tipos reutilizáveis com as regras de validação
# ---------------------------------------------------------------------

# Nome: remove espaços nas pontas; não pode ficar vazio; cabe na coluna (150)
FullName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]


def _normalize_email(value: str) -> str:
    # E-mails não diferenciam maiúsculas na prática: "Ana@X.com" == "ana@x.com"
    value = value.strip().lower()
    if len(value) > 150:  # tamanho da coluna no banco
        raise ValueError("O e-mail deve ter no máximo 150 caracteres.")
    return value


Email = Annotated[EmailStr, AfterValidator(_normalize_email)]

# Senha: mínimo de 8 caracteres; máximo de 128 para impedir que senhas
# gigantes sobrecarreguem o Argon2 (que é lento de propósito)
Password = Annotated[str, Field(min_length=8, max_length=128)]


# ---------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------

Cents = Annotated[int, Field(ge=0, le=100_000_000)]  # até R$ 1.000.000,00


def normalize_phone(value: str | None) -> str | None:
    """Celular em formato internacional: "(11) 98888-7777" -> "+5511988887777"."""
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if len(digits) in (10, 11):  # DDD + número, sem o código do país: Brasil
        digits = "55" + digits
    if not 12 <= len(digits) <= 15:
        raise ValueError("Telefone inválido. Use DDD + número, ex.: (11) 98888-7777.")
    return "+" + digits


class PatientCreate(BaseModel):
    full_name: FullName
    email: Email | None = None
    phone: Annotated[str, StringConstraints(max_length=30)] | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, value):
        return normalize_phone(value)



class PatientResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr | None = None
    archived_at: datetime | None = None
    ai_consent_at: datetime | None = None
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------
# Usuários (psicólogos)
# ---------------------------------------------------------------------

class UserCreate(BaseModel):
    full_name: FullName
    email: Email
    password: Password


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    is_active: bool
    email_verified_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------
# Recuperação de senha e verificação de e-mail
# ---------------------------------------------------------------------

class PasswordResetRequest(BaseModel):
    email: Email


class PasswordResetConfirm(BaseModel):
    token: Annotated[str, Field(min_length=1, max_length=200)]
    new_password: Password


class EmailVerificationRequest(BaseModel):
    email: Email


class EmailVerificationConfirm(BaseModel):
    token: Annotated[str, Field(min_length=1, max_length=200)]


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------
# Registros de sessão (IA)
# ---------------------------------------------------------------------

ShortItem = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)]


class NoteSummary(BaseModel):
    """Resumo estruturado (gerado pela IA e editável pelo psicólogo)."""
    resumo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] = ""
    topicos: list[ShortItem] = Field(default_factory=list, max_length=30)
    pontos_de_acompanhamento: list[ShortItem] = Field(default_factory=list, max_length=30)
    trechos_para_revisao: list[ShortItem] = Field(default_factory=list, max_length=30)


class NoteTextCreate(BaseModel):
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50000)]
    appointment_id: int | None = None


class NoteUpdate(BaseModel):
    transcript: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200000)]
    summary: NoteSummary


class NoteListItem(BaseModel):
    """Item da lista: sem conteúdo clínico (só metadados)."""
    id: int
    patient_id: int
    appointment_id: int | None = None
    source: str
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    approved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NoteDetail(NoteListItem):
    """Registro completo, já descriptografado."""
    transcript: str | None = None
    summary: NoteSummary | None = None
    transcription_model: str | None = None
    ai_model: str | None = None


# ---------------------------------------------------------------------
# Agenda
# ---------------------------------------------------------------------

AppointmentStatus = Literal["scheduled", "completed", "cancelled", "no_show"]
Modality = Literal["presencial", "online"]


class AvailabilitySlotIn(BaseModel):
    weekday: Annotated[int, Field(ge=0, le=6)]  # 0 = segunda ... 6 = domingo
    start_time: time
    end_time: time


class AvailabilitySlotOut(AvailabilitySlotIn):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AvailabilityReplace(BaseModel):
    slots: list[AvailabilitySlotIn] = Field(default_factory=list, max_length=50)


class AppointmentCreate(BaseModel):
    patient_id: int
    starts_at: datetime  # com fuso, ex.: 2026-11-20T14:00:00-03:00
    duration_minutes: Annotated[int, Field(ge=10, le=480)] = 50
    modality: Modality = "presencial"


RepeatFrequency = Literal["weekly", "biweekly"]
MAX_SERIES_OCCURRENCES = 52


class AppointmentUpdate(BaseModel):
    starts_at: datetime
    duration_minutes: Annotated[int, Field(ge=10, le=480)]
    modality: Modality


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: str | None = None
    starts_at: datetime
    ends_at: datetime
    status: str
    modality: str

    model_config = ConfigDict(from_attributes=True)


class FreeSlot(BaseModel):
    starts_at: datetime
    ends_at: datetime


# ---------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------

class AuditLogResponse(BaseModel):
    id: int
    occurred_at: datetime
    action: str
    resource_type: str | None = None
    resource_id: int | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    details: dict | None = None

    model_config = ConfigDict(from_attributes=True)


# Resposta devolvida pela rota de login (padrão OAuth2)
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None
    expires_in: int | None = None  # validade do access_token, em segundos


class RefreshRequest(BaseModel):
    refresh_token: Annotated[str, Field(min_length=1, max_length=2000)]


# ---------------------------------------------------------------------
# Resumo do dia (tela inicial)
# ---------------------------------------------------------------------

class DashboardNote(BaseModel):
    id: int
    patient_id: int
    patient_name: str
    status: str
    created_at: datetime


class MonthPoint(BaseModel):
    month: str  # "2026-11"
    completed: int  # sessões realizadas no mês
    no_show: int    # faltas no mês


class AttendanceCounts(BaseModel):
    completed: int
    no_show: int
    cancelled: int
    scheduled: int  # já passaram, mas o resultado não foi marcado


class InactivePatient(BaseModel):
    id: int
    full_name: str
    last_session: date | None  # None = nunca teve sessão


class DashboardInsights(BaseModel):
    months: list[MonthPoint]                 # sessões dos últimos 6 meses
    attendance_30d: AttendanceCounts         # consultas dos últimos 30 dias
    weekday_load: list[int]                  # últimas 8 semanas, 0 = segunda
    active_patients: int
    new_patients_month: int
    upcoming: list[AppointmentResponse]      # próximos 7 dias (sem hoje)
    inactive_patients: list[InactivePatient]


class DashboardSummary(BaseModel):
    date: date
    appointments_today: list[AppointmentResponse]
    notes_to_review: list[DashboardNote]
    notes_failed: list[DashboardNote]
    insights: DashboardInsights


# ---------------------------------------------------------------------
# Exportação dos dados de um paciente (LGPD: acesso e portabilidade)
# ---------------------------------------------------------------------

class PatientExportProfile(PatientResponse):
    created_at: datetime | None = None


class PatientExport(BaseModel):
    format_version: int = 1
    exported_at: datetime
    exported_by: str
    notice: str
    patient: PatientExportProfile
    appointments: list[AppointmentResponse]
    clinical_notes: list[NoteDetail]


class PatientOverview(BaseModel):
    """Números de um paciente (sem conteúdo clínico)."""
    sessions_completed: int
    sessions_no_show: int
    sessions_cancelled: int
    first_session: date | None
    last_session: date | None
    next_appointment: AppointmentResponse | None
    notes_count: int
    months: list[MonthPoint]                  # sessões do paciente nos últimos 6 meses
    recent: list[AppointmentResponse]         # últimas consultas (mais recentes primeiro)
