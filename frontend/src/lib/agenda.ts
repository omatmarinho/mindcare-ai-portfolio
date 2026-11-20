import type { AppointmentStatus } from "./types";

export const APPOINTMENT_STATUS_LABELS: Record<AppointmentStatus, string> = {
  scheduled: "Agendada",
  completed: "Realizada",
  cancelled: "Cancelada",
  no_show: "Faltou",
};

export const APPOINTMENT_STATUS_STYLES: Record<AppointmentStatus, string> = {
  scheduled: "border-brand-200 bg-brand-50 text-brand-800",
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  cancelled: "border-gray-200 bg-gray-50 text-gray-500 line-through",
  no_show: "border-accent-300 bg-accent-50 text-accent-700",
};
