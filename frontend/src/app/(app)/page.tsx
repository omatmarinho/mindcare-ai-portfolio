import Link from "next/link";

import { Avatar } from "@/components/avatar";
import { Donut, MonthCalendar, Ring, SessionBars, WeekdayBars } from "@/components/charts";
import {
  AlertIcon, CalendarIcon, ChevronRightIcon, ClockIcon, MicIcon, NoteIcon, PlusIcon, ShieldIcon, UsersIcon,
} from "@/components/icons";
import { Card, EmptyState, PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { APPOINTMENT_STATUS_LABELS, APPOINTMENT_STATUS_STYLES } from "@/lib/agenda";
import { apiFetch } from "@/lib/api";
import { addMonths, formatDate, formatMonth, formatTime, localDateOf, startOfDay } from "@/lib/dates";
import { formatDateTime } from "@/lib/format";
import type { Appointment, DashboardNote, DashboardSummary } from "@/lib/types";
import { buttonClasses } from "@/lib/ui-classes";

function greeting() {
  const hour = Number(new Intl.DateTimeFormat("pt-BR", { hour: "numeric", hour12: false, timeZone: "America/Sao_Paulo" }).format(new Date()));
  return hour < 12 ? "Bom dia" : hour < 18 ? "Boa tarde" : "Boa noite";
}

function longDate(iso: string) {
  const text = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
    .format(new Date(`${iso}T12:00:00Z`));
  return text.charAt(0).toUpperCase() + text.slice(1); // "Quinta-feira, 19 de novembro"
}

const WEEKDAY_LABEL = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "short", timeZone: "UTC" });
const dayHeading = (iso: string) => {
  const text = WEEKDAY_LABEL.format(new Date(`${iso}T12:00:00Z`));
  return text.charAt(0).toUpperCase() + text.slice(1);
};

/** Variação percentual entre dois valores ("+12%", "−5%"); null quando não há base de comparação. */
function delta(current: number, previous: number) {
  if (!previous) return null;
  const pct = Math.round(((current - previous) / previous) * 100);
  return { pct, text: `${pct > 0 ? "+" : pct < 0 ? "−" : ""}${Math.abs(pct)}%` };
}

// Tela inicial: o que o psicólogo precisa ver ao abrir o MindCare
export default async function HomePage() {
  const result = await apiFetch<DashboardSummary>("/dashboard");
  if (!result.ok) return <Alert kind="error">{result.error}</Alert>;
  const d = result.data;
  const ins = d.insights;

  // Consultas do mês, para marcar os dias no calendário
  const month = d.date.slice(0, 7);
  const monthParams = new URLSearchParams({ start: startOfDay(`${month}-01`), end: startOfDay(`${addMonths(month, 1)}-01`) });
  const monthAppts = await apiFetch<Appointment[]>(`/appointments?${monthParams}`);
  const busyDays = new Map<string, number>();
  for (const appt of monthAppts.ok ? monthAppts.data : []) {
    if (appt.status === "cancelled") continue;
    const day = localDateOf(appt.starts_at);
    busyDays.set(day, (busyDays.get(day) ?? 0) + 1);
  }
  const monthTotal = [...busyDays.values()].reduce((a, b) => a + b, 0);

  const today = d.appointments_today.filter((a) => a.status !== "cancelled");
  const done = today.filter((a) => a.status === "completed" || a.status === "no_show").length;
  const nextToday = d.appointments_today.find((a) => a.status === "scheduled");

  const [prevMonth, thisMonth] = ins.months.slice(-2);
  const sessionsDelta = delta(thisMonth.completed, prevMonth.completed);
  const sixMonthsTotal = ins.months.reduce((sum, m) => sum + m.completed, 0);
  const toReview = d.notes_to_review.length;

  const att = ins.attendance_30d;
  const decided = att.completed + att.no_show;
  const attendanceRate = decided ? Math.round((att.completed / decided) * 100) : null;

  // Próximas sessões agrupadas por dia
  const upcomingByDay = new Map<string, Appointment[]>();
  for (const appt of ins.upcoming) {
    const day = localDateOf(appt.starts_at);
    upcomingByDay.set(day, [...(upcomingByDay.get(day) ?? []), appt]);
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={`${greeting()}!`}
        subtitle={`${longDate(d.date)} · ${today.length ? `${today.length} consulta${today.length > 1 ? "s" : ""} hoje` : "agenda livre hoje"}`}
        actions={
          <Link href="/agenda/nova" className={buttonClasses("primary")}>
            <PlusIcon className="h-4 w-4" /> Nova consulta
          </Link>
        }
      />

      {/* Atalhos */}
      <nav aria-label="Atalhos" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Shortcut href="/agenda/nova" icon={<CalendarIcon />} title="Agendar sessão" text="Escolha um horário livre" />
        <Shortcut href="/pacientes/novo" icon={<UsersIcon />} title="Novo paciente" text="Cadastro em 1 minuto" />
        <Shortcut href={nextToday ? `/agenda/consultas/${nextToday.id}` : "/pacientes"} icon={<MicIcon />}
          title="Registrar sessão" text={nextToday ? `Próxima: ${formatTime(nextToday.starts_at)}` : "Grave ou digite"} />
        <Shortcut href="/auditoria" icon={<ShieldIcon />} title="Histórico de acessos" text="Trilha de auditoria (LGPD)" />
      </nav>

      {/* Números principais */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Link href="/agenda" className="card flex items-center justify-between gap-4 border-brand-200 bg-brand-50 p-5 transition hover:border-brand-300">
          <div className="min-w-0">
            <p className="text-sm font-medium text-brand-800">Consultas hoje</p>
            <p className="mt-1 text-3xl font-semibold tracking-tight text-gray-900 tabular-nums">{today.length}</p>
            <p className="mt-0.5 text-xs text-gray-500">{today.length ? `${done} atendida${done === 1 ? "" : "s"}` : "Agenda livre"}</p>
          </div>
          <Ring value={done} total={today.length} center={`${done}/${today.length}`} />
        </Link>
        <Kpi icon={<UsersIcon />} label="Pacientes ativos" value={String(ins.active_patients)} href="/pacientes"
          detail={ins.new_patients_month ? <span className="text-emerald-700">+{ins.new_patients_month} novo{ins.new_patients_month > 1 ? "s" : ""} este mês</span> : "Nenhum novo este mês"} />
        <Kpi icon={<CalendarIcon />} label="Sessões no mês" value={String(thisMonth.completed)} href="/agenda"
          detail={sessionsDelta
            ? <span className={sessionsDelta.pct >= 0 ? "text-emerald-700" : "text-red-700"}>{sessionsDelta.text} em relação a {formatMonth(prevMonth.month).split(" ")[0]}</span>
            : <span className="capitalize-first">{formatMonth(month)}</span>} />
        <Kpi icon={<AlertIcon />} label="Registros a revisar"
          value={toReview ? String(toReview) : "Nenhum"}
          detail={toReview ? "Rascunhos da IA esperando você" : "Tudo revisado"}
          href={toReview ? `/registros/${d.notes_to_review[0].id}` : "/pacientes"} attention={toReview > 0} />
      </div>

      {/* Sessões + comparecimento */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Sessões dos últimos 6 meses" className="lg:col-span-2"
          description={`${sixMonthsTotal} sessões realizadas no período`}
          actions={<Link href="/agenda" className={buttonClasses("ghost", "sm")}>Ver agenda</Link>}>
          <SessionBars months={ins.months} />
        </Card>

        <Card title="Comparecimento" description="Consultas dos últimos 30 dias">
          <div className="flex flex-col items-center gap-5">
            <Donut
              center={attendanceRate === null ? "—" : `${attendanceRate}%`}
              caption={attendanceRate === null ? "sem dados" : "compareceram"}
              segments={[
                { value: att.completed, className: "stroke-brand-600", label: "Realizadas" },
                { value: att.no_show, className: "stroke-accent-500", label: "Faltas" },
                { value: att.cancelled, className: "stroke-gray-300", label: "Canceladas" },
              ]}
            />
            <dl className="grid w-full grid-cols-3 gap-2 text-center">
              <Legend color="bg-brand-600" label="Realizadas" value={att.completed} />
              <Legend color="bg-accent-500" label="Faltas" value={att.no_show} />
              <Legend color="bg-gray-300" label="Canceladas" value={att.cancelled} />
            </dl>
            {att.scheduled > 0 && (
              <p className="w-full rounded-lg bg-accent-50 px-3 py-2 text-xs text-accent-700">
                {att.scheduled === 1 ? "1 consulta já passou" : `${att.scheduled} consultas já passaram`} sem resultado marcado.{" "}
                <Link href="/agenda" className="font-medium underline">Atualizar na agenda</Link>
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* Hoje + calendário */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Consultas de hoje" className="lg:col-span-2"
          actions={<Link href="/agenda" className={buttonClasses("ghost", "sm")}>Ver agenda</Link>}>
          {d.appointments_today.length === 0 ? (
            <EmptyState icon={<CalendarIcon />} title="Agenda livre hoje"
              text="Nenhuma consulta marcada para hoje."
              action={<Link href="/agenda/nova" className={buttonClasses("secondary", "sm")}>Agendar consulta</Link>} />
          ) : (
            <ul className="flex flex-col gap-2">
              {d.appointments_today.map((appt) => <AppointmentRow key={appt.id} appt={appt} />)}
            </ul>
          )}
        </Card>

        <Card title={<span className="capitalize-first">{formatMonth(month)}</span>}
          description={monthTotal ? `${monthTotal} consulta${monthTotal > 1 ? "s" : ""} no mês` : "Nenhuma consulta no mês"}>
          <MonthCalendar month={month} today={d.date} busyDays={busyDays} />
        </Card>
      </div>

      {/* Semana, movimento e acompanhamento */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card title="Próximos 7 dias" description={ins.upcoming.length ? `${ins.upcoming.length} sessões marcadas` : undefined}>
          {ins.upcoming.length === 0 ? (
            <p className="text-sm text-gray-500">Nenhuma sessão marcada para os próximos dias.</p>
          ) : (
            <div className="flex flex-col gap-4">
              {[...upcomingByDay.entries()].map(([day, appts]) => (
                <div key={day}>
                  <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-gray-400">{dayHeading(day)}</p>
                  <ul className="flex flex-col">
                    {appts.map((a) => (
                      <li key={a.id}>
                        <Link href={`/agenda/consultas/${a.id}`} className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-gray-50">
                          <Avatar name={a.patient_name ?? "?"} size="sm" />
                          <span className="min-w-0 flex-1 truncate text-sm text-gray-800">{a.patient_name}</span>
                          <span className="text-xs tabular-nums text-gray-500">{formatTime(a.starts_at)}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card title="Movimento da semana" description="Sessões por dia nas últimas 8 semanas">
          {ins.weekday_load.some(Boolean) ? (
            <WeekdayBars load={ins.weekday_load} />
          ) : (
            <p className="text-sm text-gray-500">Os dias mais movimentados aparecem aqui depois das primeiras sessões.</p>
          )}
        </Card>

        <div className="flex flex-col gap-6">
          <Card title="Registros para revisar" description="Rascunhos da IA esperando sua aprovação.">
            <NotesList notes={d.notes_to_review} empty="Tudo revisado. Nenhum registro pendente." />
          </Card>
          {d.notes_failed.length > 0 && (
            <Card title={<span className="flex items-center gap-2 text-red-700"><AlertIcon className="h-4 w-4" /> Registros com falha</span>}
              description="Abra o registro para tentar processar de novo.">
              <NotesList notes={d.notes_failed} empty="" />
            </Card>
          )}
          <Card title="Sem sessão há mais de 30 dias" description="Que tal entrar em contato?">
            {ins.inactive_patients.length === 0 ? (
              <p className="text-sm text-gray-500">Todos os pacientes ativos vieram recentemente ou têm sessão marcada.</p>
            ) : (
              <ul className="-mx-2 flex flex-col">
                {ins.inactive_patients.map((p) => (
                  <li key={p.id}>
                    <Link href={`/pacientes/${p.id}`} className="flex items-center gap-3 rounded-lg px-2 py-2 hover:bg-gray-50">
                      <Avatar name={p.full_name} size="sm" />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-gray-800">{p.full_name}</span>
                        <span className="block text-xs text-gray-500">
                          {p.last_session ? `Última sessão em ${formatDate(p.last_session)}` : "Nenhuma sessão ainda"}
                        </span>
                      </span>
                      <ChevronRightIcon className="h-4 w-4 text-gray-300" />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function Shortcut({ href, icon, title, text }: { href: string; icon: React.ReactNode; title: string; text: string }) {
  return (
    <Link href={href} className="card group flex flex-col items-start gap-2.5 p-4 transition hover:border-brand-300 hover:bg-brand-50/40 sm:flex-row sm:items-center sm:gap-3">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-600 text-white shadow-sm shadow-brand-900/10 transition group-hover:bg-brand-700 sm:h-11 sm:w-11">
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-sm font-semibold leading-snug text-gray-900 sm:truncate">{title}</span>
        <span className="block text-xs text-gray-500 sm:truncate">{text}</span>
      </span>
    </Link>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <div className="rounded-lg bg-gray-50 px-2 py-2">
      <dt className="flex items-center justify-center gap-1.5 text-[11px] text-gray-500"><span className={`h-2 w-2 rounded-full ${color}`} />{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">{value}</dd>
    </div>
  );
}

function AppointmentRow({ appt }: { appt: Appointment }) {
  return (
    <li>
      <Link href={`/agenda/consultas/${appt.id}`}
        className="group flex items-center gap-3 rounded-xl bg-gray-50 px-3 py-3 transition hover:bg-brand-50 sm:gap-4 sm:px-4">
        <div className="w-14 shrink-0 rounded-lg bg-white px-2 py-1.5 text-center tabular-nums shadow-[0_1px_2px_rgba(29,36,32,0.06)] sm:w-16">
          <p className="text-sm font-semibold text-gray-900">{formatTime(appt.starts_at)}</p>
          <p className="text-[11px] text-gray-500">{formatTime(appt.ends_at)}</p>
        </div>
        <Avatar name={appt.patient_name ?? "?"} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium text-gray-800">{appt.patient_name}</p>
          <p className="flex items-center gap-1 truncate text-xs text-gray-500">
            <ClockIcon className="h-3 w-3" />
            {appt.modality === "online" ? "On-line" : "Presencial"}
            <span className="sm:hidden"> · {APPOINTMENT_STATUS_LABELS[appt.status]}</span>
          </p>
        </div>
        <span className={`hidden whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs sm:inline-flex ${APPOINTMENT_STATUS_STYLES[appt.status]}`}>
          {APPOINTMENT_STATUS_LABELS[appt.status]}
        </span>
        <ChevronRightIcon className="h-4 w-4 text-gray-300 group-hover:text-brand-500" />
      </Link>
    </li>
  );
}

function Kpi({ icon, label, value, detail, href, attention = false }: {
  icon: React.ReactNode; label: string; value: string; detail?: React.ReactNode; href?: string; attention?: boolean;
}) {
  const body = (
    <div className={`card flex h-full items-start justify-between gap-4 p-5 transition ${href ? "hover:border-brand-300" : ""}`}>
      <div className="min-w-0">
        <p className="text-sm text-gray-500">{label}</p>
        <p className={`mt-1 text-3xl font-semibold tracking-tight tabular-nums ${attention ? "text-accent-700" : "text-gray-900"}`}>{value}</p>
        {detail && <p className="mt-0.5 text-xs text-gray-500">{detail}</p>}
      </div>
      <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-full ${attention ? "bg-accent-100 text-accent-700" : "bg-brand-50 text-brand-600"}`}>
        {icon}
      </span>
    </div>
  );
  return href ? <Link href={href} className="block">{body}</Link> : body;
}

function NotesList({ notes, empty }: { notes: DashboardNote[]; empty: string }) {
  if (notes.length === 0) return <p className="text-sm text-gray-500">{empty}</p>;
  return (
    <ul className="-mx-2 flex flex-col">
      {notes.map((note) => (
        <li key={note.id}>
          <Link href={`/registros/${note.id}`} className="flex items-center justify-between gap-3 rounded-lg px-2 py-2.5 text-sm hover:bg-gray-50">
            <span className="flex min-w-0 items-center gap-2">
              <NoteIcon className="h-4 w-4 shrink-0 text-gray-400" />
              <span className="truncate font-medium text-gray-800">{note.patient_name}</span>
            </span>
            <span className="shrink-0 text-xs text-gray-500">{formatDateTime(note.created_at)}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
