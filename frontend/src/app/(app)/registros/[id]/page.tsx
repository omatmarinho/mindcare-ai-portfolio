import Link from "next/link";
import { notFound } from "next/navigation";

import { CalendarIcon, CheckIcon } from "@/components/icons";
import { AutoRefresh, RetryNoteForm, ReviewNoteForm } from "@/components/note-forms";
import { Badge, Card, PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { STATUS_LABELS, STATUS_STYLES } from "@/lib/notes";
import type { NoteDetail, Patient } from "@/lib/types";

function ReadOnlyList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="mb-1.5 text-sm font-semibold text-gray-800">{title}</h3>
      <ul className="flex flex-col gap-1 text-sm text-gray-700">
        {items.map((item, i) => (
          <li key={i} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-400" />{item}</li>
        ))}
      </ul>
    </div>
  );
}

export default async function NotePage({ params }: PageProps<"/registros/[id]">) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  const result = await apiFetch<NoteDetail>(`/notes/${id}`);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok) return <Alert kind="error">{result.error}</Alert>;
  const note = result.data;
  const patient = await apiFetch<Patient>(`/patients/${note.patient_id}`);
  const patientName = patient.ok ? patient.data.full_name : "Paciente";

  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <PageHeader
        back={{ href: `/pacientes/${note.patient_id}`, label: patientName }}
        title="Registro de sessão"
        subtitle={
          <>
            {formatDateTime(note.created_at)} · a partir de {note.source === "audio" ? "áudio" : "texto"}
            {note.ai_model && ` · ${note.ai_model}${note.transcription_model ? ` + ${note.transcription_model}` : ""}`}
          </>
        }
        actions={<Badge className={`px-3 py-1 text-sm ${STATUS_STYLES[note.status]}`}>{STATUS_LABELS[note.status]}</Badge>}
      />

      {note.appointment_id && (
        <Link href={`/agenda/consultas/${note.appointment_id}`}
          className="flex w-fit items-center gap-2 text-sm text-brand-700 hover:underline">
          <CalendarIcon className="h-4 w-4" /> Ver a consulta desta sessão
        </Link>
      )}

      {note.status === "processing" && (
        <Card>
          <AutoRefresh />
          <div className="flex items-center gap-4">
            <span className="h-8 w-8 animate-spin rounded-full border-[3px] border-brand-200 border-t-brand-600" aria-hidden="true" />
            <div>
              <p className="font-medium text-gray-900">A IA está processando este registro</p>
              <p className="text-sm text-gray-500">Pode levar alguns minutos. Esta página se atualiza sozinha.</p>
            </div>
          </div>
        </Card>
      )}

      {note.status === "failed" && (
        <Card>
          <div className="flex flex-col gap-3">
            <Alert kind="error">{note.error_message ?? "Falha no processamento."}</Alert>
            {note.transcript ? (
              <RetryNoteForm noteId={note.id} />
            ) : (
              <p className="text-sm text-gray-600">Não há transcrição guardada: envie o áudio ou o texto novamente.</p>
            )}
          </div>
        </Card>
      )}

      {note.status === "pending_review" && (
        <>
          <Alert kind="info">
            Este conteúdo foi gerado por IA e é um <strong>rascunho</strong>. Revise e corrija o que for preciso.
            Ao aprovar, o registro fica definitivo e não pode mais ser alterado.
          </Alert>
          <Card>
            <ReviewNoteForm note={note} />
          </Card>
        </>
      )}

      {(note.status === "approved" || note.status === "failed") && (note.summary || note.transcript) && (
        <Card>
          <div className="flex flex-col gap-5">
            {note.status === "approved" && (
              <p className="flex items-center gap-2 text-sm font-medium text-emerald-700">
                <CheckIcon className="h-4 w-4" /> Aprovado em {formatDateTime(note.approved_at)}
              </p>
            )}
            {note.summary && (
              <>
                <div>
                  <h3 className="mb-1.5 text-sm font-semibold text-gray-800">Resumo</h3>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-700">{note.summary.resumo}</p>
                </div>
                <ReadOnlyList title="Tópicos discutidos" items={note.summary.topicos} />
                <ReadOnlyList title="Pontos de acompanhamento" items={note.summary.pontos_de_acompanhamento} />
                <ReadOnlyList title="Trechos para revisão" items={note.summary.trechos_para_revisao} />
              </>
            )}
            {note.transcript && (
              <details className="rounded-lg border border-gray-200">
                <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50">
                  Transcrição completa
                </summary>
                <p className="whitespace-pre-wrap border-t border-gray-200 p-4 text-sm leading-relaxed text-gray-700">{note.transcript}</p>
              </details>
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
