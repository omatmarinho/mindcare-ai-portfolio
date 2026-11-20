import type { NoteStatus } from "./types";

export const STATUS_LABELS: Record<NoteStatus, string> = {
  processing: "Processando",
  pending_review: "Aguardando sua revisão",
  approved: "Aprovado",
  failed: "Falhou",
};

export const STATUS_STYLES: Record<NoteStatus, string> = {
  processing: "bg-sky-50 text-sky-800 border-sky-200",
  pending_review: "bg-accent-50 text-accent-700 border-accent-300",
  approved: "bg-emerald-50 text-emerald-800 border-emerald-200",
  failed: "bg-red-50 text-red-800 border-red-200",
};
