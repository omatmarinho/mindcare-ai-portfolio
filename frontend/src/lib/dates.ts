/**
 * Datas no fuso do consultório (America/Sao_Paulo).
 *
 * O servidor pode estar em qualquer fuso (em produção, normalmente UTC),
 * então NUNCA usamos o fuso "do computador": tudo é calculado de forma
 * explícita em America/Sao_Paulo. Desde 2019 o Brasil não tem horário de
 * verão, então o deslocamento é fixo: UTC-03:00.
 */
export const TIMEZONE = "America/Sao_Paulo";
export const UTC_OFFSET = "-03:00";

/** "AAAA-MM-DD" de hoje no fuso do consultório. */
export function todayISO(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE }).format(new Date());
}

export function isISODate(value: unknown): value is string {
  return typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value);
}

/** Soma dias a uma data "AAAA-MM-DD" (aritmética só de calendário). */
export function addDays(iso: string, days: number): string {
  const d = new Date(`${iso}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Segunda-feira da semana da data informada. */
export function mondayOf(iso: string): string {
  const weekday = new Date(`${iso}T12:00:00Z`).getUTCDay(); // 0 = domingo
  return addDays(iso, weekday === 0 ? -6 : 1 - weekday);
}

/** Início do dia no fuso do consultório, como ISO com deslocamento. */
export function startOfDay(iso: string): string {
  return `${iso}T00:00:00${UTC_OFFSET}`;
}

/** Junta data e hora digitadas ("2026-11-20" + "14:00") em ISO com fuso. */
export function combine(dateISO: string, time: string): string {
  return `${dateISO}T${time}:00${UTC_OFFSET}`;
}

/** Data "AAAA-MM-DD" de um instante, no fuso do consultório. */
export function localDateOf(instant: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TIMEZONE }).format(new Date(instant));
}

export function formatTime(instant: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: TIMEZONE, hour: "2-digit", minute: "2-digit" }).format(
    new Date(instant),
  );
}

export function formatDayLabel(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "UTC",
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  }).format(new Date(`${iso}T12:00:00Z`));
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC" }).format(new Date(`${iso}T12:00:00Z`));
}

export function currentMonth(): string {
  return todayISO().slice(0, 7);
}

export function addMonths(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(Date.UTC(y, m - 1 + delta, 1));
  return d.toISOString().slice(0, 7);
}

export function formatMonth(month: string): string {
  return new Intl.DateTimeFormat("pt-BR", { timeZone: "UTC", month: "long", year: "numeric" }).format(
    new Date(`${month}-01T12:00:00Z`),
  );
}

export const WEEKDAYS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
