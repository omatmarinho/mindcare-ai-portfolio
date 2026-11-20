import Link from "next/link";
import { notFound } from "next/navigation";

import { RescheduleForm, StatusButtons } from "@/components/agenda-forms";
import { ChevronRightIcon } from "@/components/icons";
import { NewNoteTabs } from "@/components/note-forms";
import { Badge, Card, PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { APPOINTMENT_STATUS_LABELS, APPOINTMENT_STATUS_STYLES } from "@/lib/agenda";
import { apiFetch } from "@/lib/api";
import { formatDayLabel, formatTime, localDateOf } from "@/lib/dates";
import { formatDateTime } from "@/lib/format";
import { STATUS_LABELS, STATUS_STYLES } from "@/lib/notes";
import type { Appointment, NoteListItem, Patient } from "@/lib/types";

export default async function AppointmentPage({ params }: PageProps<"/agenda/consultas/[id]">) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  const result = await apiFetch<Appointment>(`/appointments/${id}`);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok) return <Alert kind="error">{result.error}</Alert>;
  const appt = result.data;

  const [patient, notes] = await Promise.all([
    apiFetch<Patient>(`/patients/${appt.patient_id}`),
    apiFetch<NoteListItem[]>(`/patients/${appt.patient_id}/notes`),
  ]);
  const day = localDateOf(appt.starts_at);
  const duration = Math.round((new Date(appt.ends_at).getTime() - new Date(appt.starts_at).getTime()) / 60000);
  const linkedNotes = notes.ok ? notes.data.filter((n) => n.appointment_id === appt.id) : [];
  const canWriteNotes = patient.ok && patient.data.ai_consent_at && !patient.data.archived_at;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        back={{ href: `/agenda?semana=${day}`, label: "Agenda" }}
        title={<>Consulta com <Link href={`/pacientes/${appt.patient_id}`} className="text-brand-700 hover:underline">{appt.patient_name}</Link></>}
        subtitle={
          <span className="capitalize-first">
            {formatDayLabel(day)} · {formatTime(appt.starts_at)} às {formatTime(appt.ends_at)} ·{" "}
            {appt.modality === "online" ? "on-line" : "presencial"}
          </span>
        }
        actions={<Badge className={`px-3 py-1 text-sm ${APPOINTMENT_STATUS_STYLES[appt.status]}`}>{APPOINTMENT_STATUS_LABELS[appt.status]}</Badge>}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <Card title="Registro desta sessão"
            description="Grave ou digite: a IA organiza e você revisa antes de aprovar.">
            {linkedNotes.length > 0 && (
              <ul className="-mx-2 mb-4 flex flex-col">
                {linkedNotes.map((n) => (
                  <li key={n.id}>
                    <Link href={`/registros/${n.id}`} className="group flex items-center justify-between gap-3 rounded-lg px-2 py-2 text-sm hover:bg-gray-50">
                      <span className="font-medium text-gray-800">Registro de {formatDateTime(n.created_at)}</span>
                      <span className="flex items-center gap-2">
                        <Badge className={STATUS_STYLES[n.status]}>{STATUS_LABELS[n.status]}</Badge>
                        <ChevronRightIcon className="h-4 w-4 text-gray-300 group-hover:text-brand-500" />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
            {canWriteNotes ? (
              <NewNoteTabs patientId={appt.patient_id} appointmentId={appt.id} />
            ) : (
              <Alert kind="info">
                Para usar a IA, registre o consentimento do paciente na{" "}
                <Link href={`/pacientes/${appt.patient_id}`} className="font-medium underline">ficha do paciente</Link>.
              </Alert>
            )}
          </Card>
        </div>

        <div className="flex flex-col gap-6">
          <Card title="Situação da consulta">
            <StatusButtons id={appt.id} current={appt.status} />
          </Card>

          {appt.status === "scheduled" && (
            <Card title="Remarcar ou alterar">
              <RescheduleForm id={appt.id} date={day} time={formatTime(appt.starts_at)} duration={String(duration)}
                modality={appt.modality} />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
