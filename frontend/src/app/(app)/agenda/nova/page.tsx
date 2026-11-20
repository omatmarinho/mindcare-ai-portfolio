import { connection } from "next/server";
import Link from "next/link";

import { NewAppointmentForm } from "@/components/agenda-forms";
import { ClockIcon } from "@/components/icons";
import { Card, PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { formatDate, formatTime, isISODate, todayISO } from "@/lib/dates";
import type { FreeSlot, Patient } from "@/lib/types";
import { buttonClasses, inputClasses } from "@/lib/ui-classes";

export default async function NewAppointmentPage({ searchParams }: PageProps<"/agenda/nova">) {
  await connection(); // "hoje" depende do momento do pedido
  const { dia, hora, paciente } = await searchParams;
  const day = isISODate(dia) ? dia : todayISO();
  const time = typeof hora === "string" && /^\d{2}:\d{2}$/.test(hora) ? hora : undefined;
  const patientId = typeof paciente === "string" ? paciente : undefined;

  const [patients, free] = await Promise.all([
    apiFetch<Patient[]>("/patients"),
    apiFetch<FreeSlot[]>(`/agenda/free-slots?day=${day}&duration=50`),
  ]);

  const query = (extra: Record<string, string>) =>
    new URLSearchParams({ dia: day, ...(patientId ? { paciente: patientId } : {}), ...extra }).toString();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Nova consulta" back={{ href: `/agenda?semana=${day}`, label: "Agenda" }}
        subtitle="Escolha um horário livre ao lado ou digite o horário no formulário." />

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <Card>
          {patients.ok && patients.data.length === 0 ? (
            <Alert kind="info">
              Cadastre um paciente antes de agendar. <Link href="/pacientes/novo" className="font-medium underline">Novo paciente</Link>
            </Alert>
          ) : (
            <NewAppointmentForm
              key={`${day}-${time}`}
              patients={patients.ok ? patients.data : []}
              defaultDate={day}
              defaultTime={time}
              defaultPatientId={patientId}
            />
          )}
        </Card>

        <Card title={<span className="flex items-center gap-2"><ClockIcon className="h-4 w-4 text-brand-600" /> Horários livres</span>}
          description={formatDate(day)}>
          <form className="mb-4 flex gap-2">
            <input type="date" name="dia" defaultValue={day} aria-label="Ver outro dia" className={`${inputClasses} border-gray-300 py-1.5`} />
            {patientId && <input type="hidden" name="paciente" value={patientId} />}
            <button type="submit" className={buttonClasses("secondary", "sm")}>Ver</button>
          </form>
          {free.ok && free.data.length > 0 ? (
            <div className="grid grid-cols-3 gap-2">
              {free.data.map((slot) => {
                const label = formatTime(slot.starts_at);
                const selected = time === label;
                return (
                  <Link key={slot.starts_at} href={`/agenda/nova?${query({ hora: label })}`}
                    aria-current={selected ? "true" : undefined}
                    className={`rounded-lg border py-1.5 text-center text-sm transition ${
                      selected ? "border-brand-600 bg-brand-600 font-medium text-white" : "border-gray-200 text-gray-700 hover:border-brand-300 hover:bg-brand-50"
                    }`}>
                    {label}
                  </Link>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              Nenhum horário livre neste dia. Confira seus{" "}
              <Link href="/agenda/disponibilidade" className="font-medium text-brand-700 underline">horários de atendimento</Link>.
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}
