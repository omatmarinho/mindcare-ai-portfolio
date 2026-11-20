"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { combine, isISODate } from "@/lib/dates";
import type { Appointment, AvailabilitySlot, FormState } from "@/lib/types";

function text(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

function appointmentFields(formData: FormData) {
  const values = {
    patient_id: text(formData, "patient_id"),
    date: text(formData, "date"),
    time: text(formData, "time"),
    duration: text(formData, "duration") || "50",
    modality: text(formData, "modality") || "presencial",
  };
  const errors: Record<string, string> = {};
  if (!isISODate(values.date)) errors.date = "Informe a data.";
  if (!/^\d{2}:\d{2}$/.test(values.time)) errors.time = "Informe o horário.";
  return { values, errors };
}

export async function createAppointmentAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const { values, errors } = appointmentFields(formData);
  if (!values.patient_id) errors.patient_id = "Escolha o paciente.";
  if (Object.keys(errors).length) return { fieldErrors: errors, values };

  const result = await apiFetch<Appointment>("/appointments", {
    method: "POST",
    json: {
      patient_id: Number(values.patient_id),
      starts_at: combine(values.date, values.time),
      duration_minutes: Number(values.duration),
      modality: values.modality,
    },
  });
  if (!result.ok) return { error: result.error, fieldErrors: result.fieldErrors, values };

  revalidatePath("/agenda");
  redirect(`/agenda/consultas/${result.data.id}`);
}

export async function updateAppointmentAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = Number(formData.get("id"));
  const { values, errors } = appointmentFields(formData);
  if (Object.keys(errors).length) return { fieldErrors: errors, values };

  const result = await apiFetch<Appointment>(`/appointments/${id}`, {
    method: "PUT",
    json: {
      starts_at: combine(values.date, values.time),
      duration_minutes: Number(values.duration),
      modality: values.modality,
    },
  });
  if (!result.ok) return { error: result.error, fieldErrors: result.fieldErrors, values };

  revalidatePath(`/agenda/consultas/${id}`);
  return { success: "Consulta remarcada." };
}

export async function setAppointmentStatusAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = Number(formData.get("id"));
  const result = await apiFetch<Appointment>(`/appointments/${id}/status`, {
    method: "POST",
    json: { status: text(formData, "status") },
  });
  if (!result.ok) return { error: result.error };
  revalidatePath(`/agenda/consultas/${id}`);
  revalidatePath("/agenda");
  revalidatePath("/");
  return { success: "Status atualizado." };
}

export async function saveAvailabilityAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const slots: Omit<AvailabilitySlot, "id">[] = [];
  for (let weekday = 0; weekday < 7; weekday++) {
    for (let i = 0; i < 2; i++) {
      const start = text(formData, `start_${weekday}_${i}`);
      const end = text(formData, `end_${weekday}_${i}`);
      if (!start && !end) continue;
      if (!start || !end) return { error: "Preencha início e fim de cada horário (ou deixe os dois vazios)." };
      slots.push({ weekday, start_time: start, end_time: end });
    }
  }

  const result = await apiFetch<AvailabilitySlot[]>("/agenda/availability", { method: "PUT", json: { slots } });
  if (!result.ok) return { error: result.error };
  revalidatePath("/agenda/disponibilidade");
  return { success: "Horários de atendimento salvos." };
}
