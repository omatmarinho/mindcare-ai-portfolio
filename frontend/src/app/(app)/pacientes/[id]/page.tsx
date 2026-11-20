import Link from "next/link";
import { notFound } from "next/navigation";

import { archivePatientAction, restorePatientAction } from "@/actions/patients";
import { Avatar } from "@/components/avatar";
import { Ring, SessionBars } from "@/components/charts";
import { CalendarIcon, ChevronLeftIcon, ChevronRightIcon, ClockIcon, DownloadIcon, NoteIcon } from "@/components/icons";
import { NotesSection } from "@/components/notes-section";
import { Badge, Card } from "@/components/page";
import { EditPatientForm } from "@/components/patient-forms";
import { Alert, ConfirmSubmit, SubmitButton } from "@/components/ui";
import { APPOINTMENT_STATUS_LABELS, APPOINTMENT_STATUS_STYLES } from "@/lib/agenda";
import { apiFetch } from "@/lib/api";
import { formatDate, formatDayLabel, formatTime, localDateOf } from "@/lib/dates";
import { ACTION_LABELS, formatDateTime } from "@/lib/format";
import type { AuditLog, Patient, PatientOverview } from "@/lib/types";
import { buttonClasses } from "@/lib/ui-classes";

// Cor do ponto na linha do tempo, por situação da consulta
const TIMELINE_DOT: Record<string, string> = {
  completed: "bg-emerald-500",
  no_show: "bg-accent-500",
  cancelled: "bg-gray-300",
  scheduled: "bg-brand-400",
};

function Stat({ icon, label, value, detail, tone = "default" }: {
  icon: React.ReactNode; label: string; value: React.ReactNode; detail?: React.ReactNode; tone?: "default" | "attention";
}) {
  return (
    <div className="card flex items-start gap-3 p-4">
      <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${tone === "attention" ? "bg-accent-100 text-accent-700" : "bg-brand-50 text-brand-600"}`}>
        {icon}
      </span>
      <div className="min-w-0">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="mt-0.5 truncate text-lg font-semibold tabular-nums text-gray-900">{value}</p>
        {detail && <p className="truncate text-xs text-gray-500">{detail}</p>}
      </div>
    </div>
  );
}

export default async function PatientPage({ params }: PageProps<"/pacientes/[id]">) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();

  const result = await apiFetch<Patient>(`/patients/${id}`);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok) return <Alert kind="error">{result.error}</Alert>;

  const patient = result.data;
  const [history, overview] = await Promise.all([
    apiFetch<AuditLog[]>(`/audit-logs?patient_id=${patient.id}&limit=8`),
    apiFetch<PatientOverview>(`/patients/${patient.id}/overview`),
  ]);
  const o = overview.ok ? overview.data : null;
  const decided = o ? o.sessions_completed + o.sessions_no_show : 0;
  const rate = o && decided ? Math.round((o.sessions_completed / decided) * 100) : null;
  const next = o?.next_appointment;

  return (
    <div className="flex flex-col gap-6">
      <Link href={patient.archived_at ? "/pacientes?arquivados=1" : "/pacientes"}
        className="inline-flex w-fit items-center gap-1 text-sm text-gray-500 hover:text-brand-700">
        <ChevronLeftIcon className="h-4 w-4" /> Pacientes
      </Link>

      {/* Cabeçalho do paciente */}
      <section className="card relative overflow-hidden p-5 sm:p-6">
        <div className="pointer-events-none absolute -right-10 -top-24 h-48 w-48 rounded-full bg-brand-50/70" aria-hidden="true" />
        <div className="relative flex flex-wrap items-center justify-between gap-5">
          <div className="flex min-w-0 items-center gap-4">
            <Avatar name={patient.full_name} size="lg" />
            <div className="min-w-0">
              <h1 className="text-balance text-2xl font-semibold tracking-tight text-gray-900">{patient.full_name}</h1>
              <p className="mt-0.5 truncate text-sm text-gray-500">{patient.email ?? "Sem e-mail cadastrado"}</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {patient.archived_at
                  ? <Badge className="border-gray-200 bg-gray-50 text-gray-600">Arquivado</Badge>
                  : <Badge className="border-emerald-200 bg-emerald-50 text-emerald-800">Ativo</Badge>}
                <Badge className={patient.ai_consent_at ? "border-brand-200 bg-brand-50 text-brand-800" : "border-accent-300 bg-accent-50 text-accent-700"}>
                  {patient.ai_consent_at ? "IA autorizada" : "Sem consentimento para IA"}
                </Badge>
                {o?.first_session && <Badge className="border-gray-200 bg-white text-gray-600">Em atendimento desde {formatDate(o.first_session)}</Badge>}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {!patient.archived_at && (
              <Link href={`/agenda/nova?paciente=${patient.id}`} className={buttonClasses("primary")}>
                <CalendarIcon className="h-4 w-4" /> Agendar consulta
              </Link>
            )}
            <form action={patient.archived_at ? restorePatientAction : archivePatientAction}>
              <input type="hidden" name="id" value={patient.id} />
              {patient.archived_at ? (
                <SubmitButton variant="secondary" pendingText="Restaurando…">Restaurar paciente</SubmitButton>
              ) : (
                <ConfirmSubmit question="Arquivar este paciente?" confirmText="Arquivar" pendingText="Arquivando…"
                  variant="secondary">
                  Arquivar
                </ConfirmSubmit>
              )}
            </form>
          </div>
        </div>
      </section>

      {patient.archived_at && (
        <Alert kind="info">
          Paciente arquivado em {formatDateTime(patient.archived_at)}. Os dados continuam guardados
          (Resolução CFP nº 001/2009) e podem ser restaurados.
        </Alert>
      )}

      {/* Números do paciente */}
      {o && (
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <div className="card flex items-center justify-between gap-3 p-4">
            <div className="min-w-0">
              <p className="text-xs text-gray-500">Frequência</p>
              <p className="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">{rate === null ? "—" : `${rate}%`}</p>
              <p className="truncate text-xs text-gray-500">{o.sessions_completed} sessões · {o.sessions_no_show} falta{o.sessions_no_show === 1 ? "" : "s"}</p>
            </div>
            <Ring value={o.sessions_completed} total={decided} center={rate === null ? "—" : `${rate}%`} size={64} />
          </div>
          <Stat icon={<ClockIcon />} label="Próxima sessão"
            value={next ? <Link href={`/agenda/consultas/${next.id}`} className="hover:text-brand-700 hover:underline">
              <span className="capitalize-first">{formatDayLabel(localDateOf(next.starts_at))}</span></Link> : "Nada marcado"}
            detail={next ? `às ${formatTime(next.starts_at)}` : o.last_session ? `Última em ${formatDate(o.last_session)}` : undefined} />
          <Stat icon={<CalendarIcon />} label="Canceladas" value={o.sessions_cancelled}
            detail={o.first_session ? `Desde ${formatDate(o.first_session)}` : "Ainda sem sessões"} />
          <Stat icon={<NoteIcon />} label="Registros de sessão" value={o.notes_count}
            detail={patient.ai_consent_at ? "Com apoio da IA" : "Sem IA (falta consentimento)"} />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <NotesSection patient={patient} />

          {o && (
            <Card title="Histórico de consultas" description="As últimas consultas, da mais recente para a mais antiga."
              actions={<Link href={`/agenda/nova?paciente=${patient.id}`} className={buttonClasses("ghost", "sm")}>Agendar</Link>}>
              {o.recent.length === 0 ? (
                <p className="text-sm text-gray-500">Nenhuma consulta realizada ainda.</p>
              ) : (
                <ol className="relative ml-1.5 border-l border-gray-200">
                  {o.recent.map((a) => (
                    <li key={a.id} className="relative pb-3 pl-5 last:pb-0">
                      <span className={`absolute -left-[5px] top-3 h-2.5 w-2.5 rounded-full ring-4 ring-white ${TIMELINE_DOT[a.status]}`} aria-hidden="true" />
                      <Link href={`/agenda/consultas/${a.id}`} className="group flex items-center justify-between gap-3 rounded-lg px-2 py-2 hover:bg-gray-50">
                        <span className="min-w-0">
                          <span className="block text-sm font-medium text-gray-800">
                            <span className="capitalize-first">{formatDayLabel(localDateOf(a.starts_at))}</span> · {formatTime(a.starts_at)}
                          </span>
                          <span className="block text-xs text-gray-500">
                            {a.modality === "online" ? "On-line" : "Presencial"}
                          </span>
                        </span>
                        <span className="flex items-center gap-2">
                          <Badge className={APPOINTMENT_STATUS_STYLES[a.status]}>{APPOINTMENT_STATUS_LABELS[a.status]}</Badge>
                          <ChevronRightIcon className="h-4 w-4 text-gray-300 group-hover:text-brand-500" />
                        </span>
                      </Link>
                    </li>
                  ))}
                </ol>
              )}
            </Card>
          )}
        </div>

        <div className="flex flex-col gap-6">
          {o && o.months.some((m) => m.completed || m.no_show) && (
            <Card title="Sessões por mês" description="Realizadas e faltas nos últimos 6 meses">
              <SessionBars months={o.months} />
            </Card>
          )}

          <Card title="Dados cadastrais">
            <EditPatientForm patient={patient} />
          </Card>

          <Card title="Exportar dados"
            description="Tudo o que o MindCare guarda sobre este paciente, em JSON. Para pedidos de acesso ou portabilidade (LGPD, art. 18). Contém dados sensíveis: guarde em local seguro.">
            <a href={`/pacientes/${patient.id}/exportar`} download className={buttonClasses("secondary", "sm")}>
              <DownloadIcon className="h-4 w-4" /> Baixar dados (JSON)
            </a>
          </Card>

          <Card title="Acessos recentes" description="Quem abriu ou alterou os dados deste paciente.">
            {history.ok && history.data.length > 0 ? (
              <ul className="flex flex-col text-sm">
                {history.data.map((log) => (
                  <li key={log.id} className="flex flex-wrap justify-between gap-x-3 gap-y-0.5 border-b border-gray-100 py-2 last:border-0">
                    <span className="text-gray-700">{ACTION_LABELS[log.action] ?? log.action}</span>
                    <span className="text-xs text-gray-400">{formatDateTime(log.occurred_at)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">Sem registros.</p>
            )}
            <Link href="/auditoria" className="mt-3 inline-block text-sm font-medium text-brand-700 hover:underline">Ver histórico completo</Link>
          </Card>
        </div>
      </div>
    </div>
  );
}
