import Link from "next/link";

import { revokeConsentAction } from "@/actions/notes";
import { ChevronRightIcon, MicIcon, NoteIcon } from "@/components/icons";
import { NewNoteTabs, ConsentForm } from "@/components/note-forms";
import { Badge, Card } from "@/components/page";
import { ConfirmSubmit } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { STATUS_LABELS, STATUS_STYLES } from "@/lib/notes";
import type { NoteListItem, Patient } from "@/lib/types";

// Seção "Registros de sessão" da ficha do paciente (componente de servidor)
export async function NotesSection({ patient }: { patient: Patient }) {
  const notes = await apiFetch<NoteListItem[]>(`/patients/${patient.id}/notes`);
  const list = notes.ok ? [...notes.data].reverse() : []; // mais recentes primeiro

  return (
    <>
      <Card title="Novo registro de sessão"
        description="A IA transcreve e organiza; você revisa e aprova. A IA não faz diagnósticos nem sugere tratamentos.">
        {!patient.ai_consent_at ? (
          <ConsentForm patientId={patient.id} />
        ) : patient.archived_at ? (
          <p className="text-sm text-gray-500">Restaure o paciente para criar novos registros.</p>
        ) : (
          <div className="flex flex-col gap-5">
            <NewNoteTabs patientId={patient.id} />
            <form action={revokeConsentAction}
              className="flex flex-wrap items-center gap-3 border-t border-gray-100 pt-4 text-xs text-gray-500">
              <input type="hidden" name="patient_id" value={patient.id} />
              <span>Consentimento para IA registrado em {formatDateTime(patient.ai_consent_at)}.</span>
              <ConfirmSubmit question="Revogar o consentimento?" confirmText="Revogar" pendingText="Revogando…"
                variant="ghost" size="sm">
                Revogar
              </ConfirmSubmit>
            </form>
          </div>
        )}
      </Card>

      <Card title="Histórico de registros">
        {list.length > 0 ? (
          <ul className="-mx-2 flex flex-col">
            {list.map((note) => (
              <li key={note.id}>
                <Link href={`/registros/${note.id}`}
                  className="group flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm hover:bg-gray-50">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-gray-100 text-gray-500">
                    {note.source === "audio" ? <MicIcon className="h-4 w-4" /> : <NoteIcon className="h-4 w-4" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium text-gray-800">Registro de {formatDateTime(note.created_at)}</span>
                    <span className="block text-xs text-gray-500">{note.source === "audio" ? "A partir de áudio" : "A partir de texto"}</span>
                  </span>
                  <Badge className={STATUS_STYLES[note.status]}>{STATUS_LABELS[note.status]}</Badge>
                  <ChevronRightIcon className="h-4 w-4 text-gray-300 group-hover:text-brand-500" />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-500">Nenhum registro ainda.</p>
        )}
      </Card>
    </>
  );
}
