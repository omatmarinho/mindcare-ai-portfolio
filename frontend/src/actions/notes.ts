"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { apiFetch } from "@/lib/api";
import type { FormState, NoteDetail, NoteListItem, Patient } from "@/lib/types";

const MAX_AUDIO_BYTES = 100 * 1024 * 1024;

function patientId(formData: FormData) {
  return Number(formData.get("patient_id"));
}

function appointmentId(formData: FormData): number | null {
  const value = Number(formData.get("appointment_id"));
  return Number.isInteger(value) && value > 0 ? value : null;
}

export async function retryNoteAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const noteId = Number(formData.get("note_id"));
  const result = await apiFetch<NoteListItem>(`/notes/${noteId}/retry`, { method: "POST" });
  if (!result.ok) return { error: result.error };
  revalidatePath(`/registros/${noteId}`);
  redirect(`/registros/${noteId}`);
}

export async function giveConsentAction(_prev: FormState, formData: FormData): Promise<FormState> {
  if (formData.get("confirm") !== "on") {
    return { error: "Marque a confirmação de que o paciente consentiu." };
  }
  const id = patientId(formData);
  const result = await apiFetch<Patient>(`/patients/${id}/ai-consent`, { method: "POST" });
  if (!result.ok) return { error: result.error };
  revalidatePath(`/pacientes/${id}`);
  return { success: "Consentimento registrado." };
}

export async function revokeConsentAction(formData: FormData) {
  const id = patientId(formData);
  await apiFetch<Patient>(`/patients/${id}/ai-consent`, { method: "DELETE" });
  revalidatePath(`/pacientes/${id}`);
}

export async function createTextNoteAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = patientId(formData);
  const text = String(formData.get("text") ?? "").trim();
  if (!text) return { fieldErrors: { text: "Escreva ou cole o texto da sessão." } };

  const result = await apiFetch<NoteListItem>(`/patients/${id}/notes/text`, {
    method: "POST",
    json: { text, appointment_id: appointmentId(formData) },
  });
  if (!result.ok) return { error: result.error, values: { text } };
  redirect(`/registros/${result.data.id}`);
}

export async function createAudioNoteAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const id = patientId(formData);
  const audio = formData.get("audio");

  if (!(audio instanceof File) || audio.size === 0) {
    return { fieldErrors: { audio: "Escolha um arquivo de áudio." } };
  }
  if (audio.size > MAX_AUDIO_BYTES) {
    return { fieldErrors: { audio: "O arquivo passa de 100 MB." } };
  }

  const upload = new FormData();
  upload.append("audio", audio, audio.name);
  const appointment = appointmentId(formData);
  if (appointment) upload.append("appointment_id", String(appointment));
  const result = await apiFetch<NoteListItem>(`/patients/${id}/notes/audio`, { method: "POST", multipart: upload });
  if (!result.ok) return { error: result.error };
  redirect(`/registros/${result.data.id}`);
}

/** Uma linha por item; ignora linhas vazias. */
function lines(formData: FormData, name: string) {
  return String(formData.get(name) ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export async function updateNoteAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const noteId = Number(formData.get("note_id"));
  const payload = {
    transcript: String(formData.get("transcript") ?? "").trim(),
    summary: {
      resumo: String(formData.get("resumo") ?? "").trim(),
      topicos: lines(formData, "topicos"),
      pontos_de_acompanhamento: lines(formData, "pontos_de_acompanhamento"),
      trechos_para_revisao: lines(formData, "trechos_para_revisao"),
    },
  };

  const result = await apiFetch<NoteDetail>(`/notes/${noteId}`, { method: "PUT", json: payload });
  if (!result.ok) return { error: result.error, fieldErrors: result.fieldErrors };

  // "Salvar e aprovar": aprova só depois de salvar, para nenhuma edição se perder
  if (formData.get("intent") === "approve") {
    const approved = await apiFetch<NoteDetail>(`/notes/${noteId}/approve`, { method: "POST" });
    if (!approved.ok) return { error: approved.error };
    revalidatePath(`/registros/${noteId}`);
    redirect(`/registros/${noteId}`);
  }

  revalidatePath(`/registros/${noteId}`);
  return { success: "Rascunho salvo." };
}
