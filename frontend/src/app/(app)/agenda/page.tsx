import { connection } from "next/server";
import Link from "next/link";

import { Ring } from "@/components/charts";
import { CalendarIcon, CheckIcon, ChevronLeftIcon, ChevronRightIcon, ClockIcon, PlusIcon } from "@/components/icons";
import { PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { APPOINTMENT_STATUS_LABELS } from "@/lib/agenda";
import { apiFetch } from "@/lib/api";
import { addDays, formatDate, formatDayLabel, formatTime, isISODate, localDateOf, mondayOf, startOfDay, todayISO } from "@/lib/dates";
import type { Appointment, AppointmentStatus, AvailabilitySlot } from "@/lib/types";
import { buttonClasses } from "@/lib/ui-classes";

// Cor de cada consulta, por status
const STATUS_BAR: Record<AppointmentStatus, string> = {
  scheduled: "border-l-brand-500 bg-brand-50 text-brand-900",
  completed: "border-l-emerald-500 bg-emerald-50 text-emerald-900",
  no_show: "border-l-accent-500 bg-accent-50 text-accent-700",
  cancelled: "border-l-gray-300 bg-gray-50 text-gray-400 line-through",
};
const LEGEND: { status: AppointmentStatus; dot: string }[] = [
  { status: "scheduled", dot: "bg-brand-500" },
  { status: "completed", dot: "bg-emerald-500" },
  { status: "no_show", dot: "bg-accent-500" },
  { status: "cancelled", dot: "bg-gray-300" },
];

const HOUR_PX = 56;
const WEEKDAY_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

/** "14:30" -> 870 (minutos desde meia-noite). */
const toMinutes = (hhmm: string) => {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + m;
};

function nowMinutesInBrazil() {
  const parts = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Sao_Paulo" })
    .format(new Date());
  return toMinutes(parts);
}

export default async function AgendaPage({ searchParams }: PageProps<"/agenda">) {
  await connection(); // "hoje" depende do momento do pedido
  const { semana } = await searchParams;
  const today = todayISO();
  const monday = mondayOf(isISODate(semana) ? semana : today);
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i));
  const isCurrentWeek = days.includes(today);

  const params = new URLSearchParams({ start: startOfDay(monday), end: startOfDay(addDays(monday, 7)) });
  const [result, availability] = await Promise.all([
    apiFetch<Appointment[]>(`/appointments?${params}`),
    apiFetch<AvailabilitySlot[]>("/agenda/availability"),
  ]);
  const appointments = result.ok ? result.data : [];
  const slots = availability.ok ? availability.data : [];

  const byDay = new Map<string, Appointment[]>();
  for (const appt of appointments) {
    const day = localDateOf(appt.starts_at);
    byDay.set(day, [...(byDay.get(day) ?? []), appt]);
  }

  // Números da semana
  const active = appointments.filter((a) => a.status !== "cancelled");
  const bookedMinutes = active.reduce((sum, a) => sum + (new Date(a.ends_at).getTime() - new Date(a.starts_at).getTime()) / 60000, 0);
  const openMinutes = slots.reduce((sum, s) => sum + toMinutes(s.end_time.slice(0, 5)) - toMinutes(s.start_time.slice(0, 5)), 0);
  const occupancy = openMinutes ? Math.min(100, Math.round((bookedMinutes / openMinutes) * 100)) : null;
  const online = active.filter((a) => a.modality === "online").length;
  const done = appointments.filter((a) => a.status === "completed").length;
  const missed = appointments.filter((a) => a.status === "no_show").length;

  // Faixa de horas da grade: expediente + consultas, com folga de 1 hora
  const starts = [...slots.map((s) => toMinutes(s.start_time.slice(0, 5))), ...appointments.map((a) => toMinutes(formatTime(a.starts_at)))];
  const ends = [...slots.map((s) => toMinutes(s.end_time.slice(0, 5))), ...appointments.map((a) => toMinutes(formatTime(a.ends_at)))];
  const firstHour = Math.max(0, Math.floor((starts.length ? Math.min(...starts) : 8 * 60) / 60) - 1);
  const lastHour = Math.min(24, Math.ceil((ends.length ? Math.max(...ends) : 19 * 60) / 60));
  const hours = Array.from({ length: lastHour - firstHour }, (_, i) => firstHour + i);
  const gridHeight = hours.length * HOUR_PX;
  const y = (minutes: number) => ((minutes - firstHour * 60) / 60) * HOUR_PX;
  const nowY = isCurrentWeek ? y(nowMinutesInBrazil()) : null;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Agenda"
        subtitle={`${formatDate(monday)} a ${formatDate(addDays(monday, 6))}`}
        actions={
          <>
            <Link href="/agenda/disponibilidade" className={buttonClasses("secondary")}>
              <ClockIcon className="h-4 w-4" /> Horários de atendimento
            </Link>
            <Link href="/agenda/nova" className={buttonClasses("primary")}>
              <PlusIcon className="h-4 w-4" /> Nova consulta
            </Link>
          </>
        }
      />

      {/* Números da semana */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <WeekStat icon={<CalendarIcon />} label="Sessões na semana" value={String(active.length)}
          detail={online ? `${online} on-line` : "Todas presenciais"} />
        <WeekStat icon={<ClockIcon />} label="Horas agendadas" value={`${Math.floor(bookedMinutes / 60)}h${bookedMinutes % 60 ? ` ${Math.round(bookedMinutes % 60)}min` : ""}`}
          detail={openMinutes ? `de ${Math.round(openMinutes / 60)}h de atendimento` : "Defina seus horários"} />
        <div className="card flex items-center justify-between gap-3 p-4">
          <div className="min-w-0">
            <p className="text-xs text-gray-500">Ocupação</p>
            <p className="mt-0.5 text-lg font-semibold tabular-nums text-gray-900">{occupancy === null ? "—" : `${occupancy}%`}</p>
            <p className="truncate text-xs text-gray-500">{occupancy === null ? "Sem horários definidos" : "dos horários de atendimento"}</p>
          </div>
          <Ring value={occupancy ?? 0} total={100} center={occupancy === null ? "—" : `${occupancy}%`} size={64} />
        </div>
        <WeekStat icon={<CheckIcon />} label="Realizadas" value={String(done)}
          detail={missed ? `${missed} falta${missed > 1 ? "s" : ""}` : "Nenhuma falta"} />
      </div>

      {/* Navegação e legenda */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex overflow-hidden rounded-lg border border-gray-300 bg-white">
          <Link href={`/agenda?semana=${addDays(monday, -7)}`} aria-label="Semana anterior" className="px-2.5 py-2 text-gray-600 hover:bg-gray-50">
            <ChevronLeftIcon className="h-4 w-4" />
          </Link>
          <Link href="/agenda" className={`border-x border-gray-300 px-3 py-2 text-sm ${isCurrentWeek ? "font-medium text-brand-700" : "text-gray-700 hover:bg-gray-50"}`}>
            Hoje
          </Link>
          <Link href={`/agenda?semana=${addDays(monday, 7)}`} aria-label="Próxima semana" className="px-2.5 py-2 text-gray-600 hover:bg-gray-50">
            <ChevronRightIcon className="h-4 w-4" />
          </Link>
        </div>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
          {LEGEND.map((l) => (
            <li key={l.status} className="flex items-center gap-1.5"><span className={`h-2.5 w-2.5 rounded-full ${l.dot}`} />{APPOINTMENT_STATUS_LABELS[l.status]}</li>
          ))}
          {slots.length > 0 && (
            <li className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-sm border border-gray-300 bg-[repeating-linear-gradient(45deg,#e4e6df,#e4e6df_2px,#fff_2px,#fff_4px)]" />Fora do expediente</li>
          )}
        </ul>
      </div>

      {!result.ok && <Alert kind="error">{result.error}</Alert>}

      {/* Grade semanal por horário (computador) */}
      <section className="card hidden overflow-hidden md:block" aria-label="Semana em grade de horários">
        <div className="grid grid-cols-[3.5rem_repeat(7,minmax(0,1fr))] border-b border-gray-100">
          <div />
          {days.map((day, i) => {
            const isToday = day === today;
            const count = (byDay.get(day) ?? []).filter((a) => a.status !== "cancelled").length;
            return (
              <div key={day} className="flex items-center justify-between gap-1 border-l border-gray-100 px-2 py-2.5">
                <div className="flex items-center gap-2">
                  <span className={`grid h-8 w-8 place-items-center rounded-full text-sm font-semibold tabular-nums ${isToday ? "bg-brand-600 text-white" : "text-gray-800"}`}>
                    {Number(day.slice(8))}
                  </span>
                  <span className="leading-tight">
                    <span className={`block text-xs font-medium ${isToday ? "text-brand-700" : "text-gray-500"}`}>{WEEKDAY_SHORT[i]}</span>
                    <span className="block text-[11px] text-gray-400">{count ? `${count} sess${count > 1 ? "ões" : "ão"}` : "livre"}</span>
                  </span>
                </div>
                <Link href={`/agenda/nova?dia=${day}`} aria-label={`Agendar em ${formatDate(day)}`}
                  className="grid h-7 w-7 place-items-center rounded-md text-gray-400 hover:bg-brand-50 hover:text-brand-700">
                  <PlusIcon className="h-4 w-4" />
                </Link>
              </div>
            );
          })}
        </div>

        <div className="relative grid grid-cols-[3.5rem_repeat(7,minmax(0,1fr))]" style={{ height: gridHeight }}>
          {/* Horas */}
          <div className="relative">
            {hours.map((h) => (
              <span key={h} className="absolute right-2 -translate-y-1/2 text-[11px] tabular-nums text-gray-400" style={{ top: y(h * 60) }}>
                {h > firstHour ? `${String(h).padStart(2, "0")}:00` : ""}
              </span>
            ))}
          </div>

          {days.map((day, i) => {
            const daySlots = slots.filter((s) => s.weekday === i);
            const appts = byDay.get(day) ?? [];
            const isToday = day === today;
            return (
              <div key={day} className={`relative border-l border-gray-100 ${day < today ? "bg-gray-50/40" : ""}`}>
                {/* Fora do expediente (listrado) e horários de atendimento (branco) */}
                {slots.length > 0 && (
                  <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,#f6f7f3,#f6f7f3_4px,#fbfbf9_4px,#fbfbf9_8px)]" aria-hidden="true" />
                )}
                {daySlots.map((s) => (
                  <div key={s.id} className="absolute inset-x-0 bg-white" aria-hidden="true"
                    style={{ top: y(toMinutes(s.start_time.slice(0, 5))), height: y(toMinutes(s.end_time.slice(0, 5))) - y(toMinutes(s.start_time.slice(0, 5))) }} />
                ))}
                {hours.map((h) => (
                  <div key={h} className="absolute inset-x-0 border-t border-gray-100" style={{ top: y(h * 60) }} aria-hidden="true" />
                ))}

                {appts.map((appt) => {
                  const top = y(toMinutes(formatTime(appt.starts_at)));
                  const height = Math.max(y(toMinutes(formatTime(appt.ends_at))) - top, 22);
                  const cancelled = appt.status === "cancelled";
                  return (
                    <Link key={appt.id} href={`/agenda/consultas/${appt.id}`}
                      title={`${formatTime(appt.starts_at)}–${formatTime(appt.ends_at)} · ${appt.patient_name} · ${APPOINTMENT_STATUS_LABELS[appt.status]}`}
                      className={`absolute overflow-hidden rounded-md border-l-[3px] px-1.5 py-1 text-[11px] leading-tight shadow-sm transition hover:z-20 hover:shadow-md ${STATUS_BAR[appt.status]} ${cancelled ? "right-1 w-2/5 opacity-70" : "left-1 right-1 z-10"}`}
                      style={{ top: top + 1, height: height - 2 }}>
                      <span className="flex items-center gap-1 font-semibold tabular-nums">
                        {formatTime(appt.starts_at)}
                      </span>
                      {!cancelled && <span className="block truncate">{appt.patient_name}</span>}
                      {!cancelled && height > 46 && (
                        <span className="block truncate opacity-70">{APPOINTMENT_STATUS_LABELS[appt.status]}{appt.modality === "online" ? " · on-line" : ""}</span>
                      )}
                    </Link>
                  );
                })}

                {isToday && nowY !== null && nowY >= 0 && nowY <= gridHeight && (
                  <div className="pointer-events-none absolute inset-x-0 z-30 flex items-center" style={{ top: nowY }} aria-hidden="true">
                    <span className="-ml-1 h-2 w-2 rounded-full bg-red-500" />
                    <span className="h-px flex-1 bg-red-500" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Lista por dia (celular) */}
      <div className="flex flex-col gap-3 md:hidden">
        {days.map((day) => {
          const isToday = day === today;
          const appts = byDay.get(day) ?? [];
          return (
            <div key={day}
              className={`flex flex-col gap-2 rounded-xl border bg-white p-3 ${isToday ? "border-brand-400 ring-2 ring-brand-100" : "border-gray-200"}`}>
              <div className="flex items-center justify-between">
                <span className={`text-sm capitalize ${isToday ? "font-semibold text-brand-700" : "font-medium text-gray-700"}`}>
                  {formatDayLabel(day)}
                </span>
                <Link href={`/agenda/nova?dia=${day}`} aria-label={`Agendar em ${formatDate(day)}`}
                  className="grid h-7 w-7 place-items-center rounded-md text-gray-400 hover:bg-brand-50 hover:text-brand-700">
                  <PlusIcon className="h-4 w-4" />
                </Link>
              </div>
              {appts.length === 0 && <p className="text-xs text-gray-400">Livre</p>}
              {appts.map((appt) => (
                <Link key={appt.id} href={`/agenda/consultas/${appt.id}`}
                  className={`flex items-center justify-between gap-2 rounded-md border-l-[3px] px-2.5 py-2 text-xs ${STATUS_BAR[appt.status]}`}>
                  <span className="min-w-0">
                    <span className="font-semibold tabular-nums">{formatTime(appt.starts_at)}</span>
                    <span className="block truncate">{appt.patient_name}</span>
                  </span>
                  <span className="shrink-0 opacity-70">{APPOINTMENT_STATUS_LABELS[appt.status]}</span>
                </Link>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WeekStat({ icon, label, value, detail }: { icon: React.ReactNode; label: string; value: string; detail?: string }) {
  return (
    <div className="card flex items-start gap-3 p-4">
      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-600">{icon}</span>
      <div className="min-w-0">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="mt-0.5 truncate text-lg font-semibold tabular-nums text-gray-900">{value}</p>
        {detail && <p className="truncate text-xs text-gray-500">{detail}</p>}
      </div>
    </div>
  );
}
