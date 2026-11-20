/**
 * Gráficos simples em SVG (componentes de servidor, sem bibliotecas):
 * anel de progresso e calendário do mês.
 */
import Link from "next/link";

/** Anel de progresso: `value` de `total`, com um texto no centro. */
export function Ring({ value, total, center, caption, size = 76 }: {
  value: number; total: number; center: React.ReactNode; caption?: string; size?: number;
}) {
  const stroke = 7;
  const r = (size - stroke) / 2;
  const length = 2 * Math.PI * r;
  const ratio = total > 0 ? Math.min(value / total, 1) : 0;
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="stroke-brand-100" />
        {ratio > 0 && (
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} strokeLinecap="round"
            strokeDasharray={`${length * ratio} ${length}`} className="stroke-brand-600" />
        )}
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center leading-none">
        <span className="text-lg font-semibold text-gray-900">{center}</span>
        {caption && <span className="mt-1 text-[10px] text-gray-500">{caption}</span>}
      </div>
    </div>
  );
}

const WEEK_INITIALS = ["D", "S", "T", "Q", "Q", "S", "S"];

// "quinta-feira, 19 de novembro" (para leitores de tela)
const fullDate = (iso: string) =>
  new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long", timeZone: "UTC" })
    .format(new Date(`${iso}T12:00:00Z`));

/**
 * Calendário do mês (domingo primeiro). Dias com consultas ficam marcados;
 * cada dia abre a semana correspondente na agenda.
 */
export function MonthCalendar({ month, today, busyDays }: {
  month: string; // "2026-11"
  today: string; // "2026-11-19"
  busyDays: Map<string, number>; // "2026-11-19" -> número de consultas
}) {
  const [year, monthNumber] = month.split("-").map(Number);
  const firstWeekday = new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  const cells: (string | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: daysInMonth }, (_, i) => `${month}-${String(i + 1).padStart(2, "0")}`),
  ];

  return (
    <div>
      <div className="grid grid-cols-7 gap-1 text-center text-xs tabular-nums">
        {WEEK_INITIALS.map((d, i) => (
          <span key={i} aria-hidden="true" className="pb-1 font-medium text-gray-400">{d}</span>
        ))}
        {cells.map((day, i) => {
          if (!day) return <span key={`vazio-${i}`} aria-hidden="true" />;
          const count = busyDays.get(day) ?? 0;
          const isToday = day === today;
          const style = isToday
            ? "bg-brand-600 font-semibold text-white"
            : count > 0
              ? "bg-brand-100 font-medium text-brand-800 hover:bg-brand-200"
              : "text-gray-600 hover:bg-gray-100";
          const label = `${fullDate(day)}${isToday ? " (hoje)" : ""}: ${count ? `${count} consulta${count > 1 ? "s" : ""}` : "sem consultas"}`;
          return (
            <Link key={day} href={`/agenda?semana=${day}`} aria-label={label} title={label}
              className={`relative grid aspect-square place-items-center rounded-lg transition ${style}`}>
              {Number(day.slice(8))}
              {isToday && count > 0 && <span className="absolute bottom-1 h-1 w-1 rounded-full bg-accent-300" />}
            </Link>
          );
        })}
      </div>
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 border-t border-gray-100 pt-3 text-xs text-gray-500">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-brand-600" /> Hoje</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded bg-brand-100" /> Dias com consultas</span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------
// Gráficos com dados do consultório
// ---------------------------------------------------------------------

const MONTH_SHORT = new Intl.DateTimeFormat("pt-BR", { month: "short", timeZone: "UTC" });
const MONTH_LONG = new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric", timeZone: "UTC" });
const monthShort = (key: string) => MONTH_SHORT.format(new Date(`${key}-01T12:00:00Z`)).replace(".", "");
const monthLong = (key: string) => MONTH_LONG.format(new Date(`${key}-01T12:00:00Z`));

/**
 * Barras por mês: recebido (verde) com o "a receber" empilhado (verde claro)
 * e despesas pagas ao lado (cinza). Escala única para todas as barras.
 */
/** Sessões por mês: realizadas (verde) com as faltas empilhadas por cima (dourado). */
export function SessionBars({ months }: { months: { month: string; completed: number; no_show: number }[] }) {
  const max = Math.max(1, ...months.map((m) => m.completed + m.no_show));
  const ticks = [1, 0.5, 0];
  const pct = (v: number) => `${(v / max) * 100}%`;
  return (
    <div>
      <div className="flex gap-3">
        <div className="flex h-44 w-8 shrink-0 flex-col justify-between text-right text-[11px] tabular-nums text-gray-400" aria-hidden="true">
          {ticks.map((t) => <span key={t}>{Math.round(max * t)}</span>)}
        </div>
        <div className="relative h-44 min-w-0 flex-1">
          {ticks.map((t) => (
            <div key={t} className="absolute inset-x-0 border-t border-dashed border-gray-200" style={{ bottom: `${t * 100}%` }} aria-hidden="true" />
          ))}
          <ul className="relative flex h-full items-end justify-around gap-2">
            {months.map((m, i) => {
              const current = i === months.length - 1;
              const label = `${monthLong(m.month)}: ${m.completed} sessões realizadas, ${m.no_show} faltas`;
              return (
                <li key={m.month} className="flex h-full flex-1 items-end justify-center" aria-label={label} title={label}>
                  <div className="flex h-full w-full max-w-9 flex-col justify-end">
                    {m.no_show > 0 && <div className="w-full rounded-t-md bg-accent-300" style={{ height: pct(m.no_show) }} />}
                    <div className={`w-full ${m.no_show > 0 ? "" : "rounded-t-md"} ${current ? "bg-brand-600" : "bg-brand-500/80"}`}
                      style={{ height: pct(m.completed), minHeight: m.completed ? 2 : 0 }} />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>
      <div className="ml-11 mt-2 flex justify-around gap-2 text-xs text-gray-500" aria-hidden="true">
        {months.map((m, i) => (
          <span key={m.month} className={`flex-1 text-center capitalize ${i === months.length - 1 ? "font-semibold text-gray-900" : ""}`}>
            {monthShort(m.month)}
          </span>
        ))}
      </div>
      <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand-600" /> Realizadas</span>
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-accent-300" /> Faltas</span>
      </div>
    </div>
  );
}

/** Rosca com segmentos (ex.: realizadas, faltas, canceladas) e um texto no centro. */
export function Donut({ segments, center, caption, size = 132 }: {
  segments: { value: number; className: string; label: string }[];
  center: React.ReactNode; caption?: string; size?: number;
}) {
  const stroke = 14;
  const r = (size - stroke) / 2;
  const length = 2 * Math.PI * r;
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  const arcs = segments.map((s, i) => {
    const before = segments.slice(0, i).reduce((sum, x) => sum + x.value, 0);
    return { ...s, part: total ? (s.value / total) * length : 0, offset: total ? (before / total) * length : 0 };
  });
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="-rotate-90" aria-hidden="true">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="stroke-gray-100" />
        {arcs.filter((a) => a.value > 0).map((a) => (
          <circle key={a.label} cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke}
            strokeDasharray={`${a.part} ${length - a.part}`} strokeDashoffset={-a.offset} className={a.className} />
        ))}
      </svg>
      <div className="absolute inset-0 grid place-content-center text-center leading-none">
        <span className="text-2xl font-semibold tabular-nums text-gray-900">{center}</span>
        {caption && <span className="mt-1 text-[11px] text-gray-500">{caption}</span>}
      </div>
    </div>
  );
}

const WEEKDAY_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const WEEKDAY_FULL = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"];

/** Barras verticais por dia da semana (0 = segunda); o dia mais movimentado fica em destaque. */
export function WeekdayBars({ load }: { load: number[] }) {
  const max = Math.max(1, ...load);
  const peak = load.indexOf(Math.max(...load));
  return (
    <ul className="flex h-36 items-end justify-between gap-2">
      {load.map((count, i) => {
        const label = `${WEEKDAY_FULL[i]}: ${count} consulta${count === 1 ? "" : "s"}`;
        const highlight = count > 0 && i === peak;
        return (
          <li key={i} className="flex h-full flex-1 flex-col items-center justify-end gap-1.5" aria-label={label} title={label}>
            <span className="text-[11px] tabular-nums text-gray-500">{count || ""}</span>
            <div className={`w-full max-w-8 rounded-md ${highlight ? "bg-accent-500" : "bg-brand-200"}`}
              style={{ height: `${(count / max) * 100}%`, minHeight: 4 }} />
            <span className={`text-[11px] ${highlight ? "font-semibold text-gray-900" : "text-gray-500"}`}>{WEEKDAY_SHORT[i]}</span>
          </li>
        );
      })}
    </ul>
  );
}

/** Barras horizontais (ex.: despesas por categoria), maiores primeiro. */
export function HBars({ items, format, barClass = "bg-brand-500" }: {
  items: { label: string; value: number }[];
  format: (v: number) => string;
  barClass?: string;
}) {
  const sorted = [...items].sort((a, b) => b.value - a.value);
  const max = Math.max(1, ...sorted.map((i) => i.value));
  const total = sorted.reduce((sum, i) => sum + i.value, 0);
  return (
    <ul className="flex flex-col gap-3">
      {sorted.map((item) => (
        <li key={item.label}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 truncate text-gray-700">{item.label}</span>
            <span className="shrink-0 tabular-nums text-gray-900">
              {format(item.value)} <span className="text-xs text-gray-400">{total ? Math.round((item.value / total) * 100) : 0}%</span>
            </span>
          </div>
          <div className="h-2 rounded-full bg-gray-100">
            <div className={`h-2 rounded-full ${barClass}`} style={{ width: `${(item.value / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}
