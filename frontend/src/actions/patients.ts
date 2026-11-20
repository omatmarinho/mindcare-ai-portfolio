"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiFetch } from "@/lib/api";
import type { FormState, Patient } from "@/lib/types";

function patientPayload(formData: FormData) {
  const full_name = String(formData.get("full_name") ?? "").trim();
  const email = String(formData.get("email") ?? "").trim();
  const phone = String(formData.get("phone") ?? "").trim();
  return {
    payload: { full_name, email: email || null, phone: phone || null },
    values: { full_name, email, phone },
  };
}

export async function createPatientAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const { payload, values } = patientPayload(formData);
  const result = await apiFetch<Patient>("/patients", { method: "POST", json: payload });

  if (!result.ok) {
    return { error: result.error, fieldErrors: result.fieldErrors, values };
  }
  revalidatePath("/pacientes");
  redirect(`/pacientes/${result.data.id}`);
}

export async function updatePatientAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = Number(formData.get("id"));
  const { payload, values } = patientPayload(formData);
  const result = await apiFetch<Patient>(`/patients/${id}`, { method: "PUT", json: payload });

  if (!result.ok) {
    return { error: result.error, fieldErrors: result.fieldErrors, values };
  }
  revalidatePath(`/pacientes/${id}`);
  return { success: "Dados atualizados." };
}

export async function archivePatientAction(formData: FormData) {
  const id = Number(formData.get("id"));
  await apiFetch<Patient>(`/patients/${id}`, { method: "DELETE" });
  revalidatePath("/pacientes");
  redirect(`/pacientes/${id}`);
}

export async function restorePatientAction(formData: FormData) {
  const id = Number(formData.get("id"));
  await apiFetch<Patient>(`/patients/${id}/restore`, { method: "POST" });
  revalidatePath("/pacientes");
  redirect(`/pacientes/${id}`);
}
