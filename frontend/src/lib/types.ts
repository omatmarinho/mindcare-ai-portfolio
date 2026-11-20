// Formatos devolvidos pela API FastAPI (espelham os schemas do backend)

export type User = {
  id: number;
  full_name: string;
  email: string;
  is_active: boolean;
  email_verified_at: string | null;
};

export type Patient = {
  id: number;
  full_name: string;
  email: string | null;
  archived_at: string | null;
  ai_consent_at: string | null;
  phone: string | null;
};

export type AppointmentStatus = "scheduled" | "completed" | "cancelled" | "no_show";

export type PatientOverview = {
  sessions_completed: number;
  sessions_no_show: number;
  sessions_cancelled: number;
  first_session: string | null;
  last_session: string | null;
  next_appointment: Appointment | null;
  notes_count: number;
  months: MonthPoint[];
  recent: Appointment[];
};

export type Appointment = {
  id: number;
  patient_id: number;
  patient_name: string | null;
  starts_at: string;
  ends_at: string;
  status: AppointmentStatus;
  modality: "presencial" | "online";
};

export type AvailabilitySlot = { id: number; weekday: number; start_time: string; end_time: string };
export type FreeSlot = { starts_at: string; ends_at: string };

export type NoteStatus = "processing" | "pending_review" | "approved" | "failed";

export type NoteSummary = {
  resumo: string;
  topicos: string[];
  pontos_de_acompanhamento: string[];
  trechos_para_revisao: string[];
};

export type NoteListItem = {
  id: number;
  patient_id: number;
  appointment_id: number | null;
  source: "audio" | "text";
  status: NoteStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
  approved_at: string | null;
};

export type NoteDetail = NoteListItem & {
  transcript: string | null;
  summary: NoteSummary | null;
  transcription_model: string | null;
  ai_model: string | null;
};

export type AuditLog = {
  id: number;
  occurred_at: string;
  action: string;
  resource_type: string | null;
  resource_id: number | null;
  ip_address: string | null;
  user_agent: string | null;
  details: Record<string, unknown> | null;
};

export type Message = { message: string };

/** Estado devolvido pelas Server Actions para os formulários. */
export type FormState = {
  error?: string;
  success?: string;
  fieldErrors?: Record<string, string>;
  values?: Record<string, string>;
};

export type DashboardNote = {
  id: number;
  patient_id: number;
  patient_name: string;
  status: string;
  created_at: string;
};

export type MonthPoint = { month: string; completed: number; no_show: number };
export type AttendanceCounts = { completed: number; no_show: number; cancelled: number; scheduled: number };
export type InactivePatient = { id: number; full_name: string; last_session: string | null };

export type DashboardInsights = {
  months: MonthPoint[];
  attendance_30d: AttendanceCounts;
  weekday_load: number[];
  active_patients: number;
  new_patients_month: number;
  upcoming: Appointment[];
  inactive_patients: InactivePatient[];
};

export type DashboardSummary = {
  date: string;
  appointments_today: Appointment[];
  notes_to_review: DashboardNote[];
  notes_failed: DashboardNote[];
  insights: DashboardInsights;
};
