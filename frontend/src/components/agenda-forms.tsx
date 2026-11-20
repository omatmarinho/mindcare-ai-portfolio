"use client";

import { useActionState } from "react";

import {
  createAppointmentAction,
  saveAvailabilityAction,
  setAppointmentStatusAction,
  updateAppointmentAction,
} from "@/actions/agenda";
import { Alert, ConfirmSubmit, Field, SubmitButton } from "@/components/ui";
import { WEEKDAYS } from "@/lib/dates";
import type { AvailabilitySlot, FormState, Patient } from "@/lib/types";
import { inputClasses } from "@/lib/ui-classes";

const initial: FormState = {};
const selectClass = `${inputClasses} border-gray-300`;

function Select({ label, name, defaultValue, children, error, onChange }: {
  label: string; name: string; defaultValue?: string; children: React.ReactNode; error?: string;
  onChange?: (value: string) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={name} className="text-sm font-medium text-gray-700">{label}</label>
      <select id={name} name={name} defaultValue={defaultValue} className={selectClass}
        onChange={onChange ? (e) => onChange(e.target.value) : undefined}>{children}</select>
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

const DURATIONS = ["30", "40", "45", "50", "60", "90"];

export function NewAppointmentForm({
  patients, defaultDate, defaultTime, defaultPatientId,
}: {
  patients: Patient[]; defaultDate: string; defaultTime?: string; defaultPatientId?: string;
}) {
  const [state, action] = useActionState(createAppointmentAction, initial);
  const v = state.values ?? {};
  const e = state.fieldErrors ?? {};
  return (
    <form action={action} className="flex flex-col gap-4">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <Select label="Paciente" name="patient_id" defaultValue={v.patient_id ?? defaultPatientId ?? ""} error={e.patient_id}>
        <option value="">Escolha…</option>
        {patients.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
      </Select>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Data" name="date" type="date" required defaultValue={v.date ?? defaultDate} error={e.date} />
        <Field label="Horário" name="time" type="time" required defaultValue={v.time ?? defaultTime} error={e.time} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Select label="Duração (min)" name="duration" defaultValue={v.duration ?? "50"}>
          {DURATIONS.map((d) => <option key={d} value={d}>{d}</option>)}
        </Select>
        <Select label="Modalidade" name="modality" defaultValue={v.modality ?? "presencial"}>
          <option value="presencial">Presencial</option>
          <option value="online">On-line</option>
        </Select>
      </div>
      <div>
        <SubmitButton pendingText="Agendando…">Agendar consulta</SubmitButton>
      </div>
    </form>
  );
}

export function RescheduleForm({ id, date, time, duration, modality }: {
  id: number; date: string; time: string; duration: string; modality: string;
}) {
  const [state, action] = useActionState(updateAppointmentAction, initial);
  const v = state.values ?? {};
  const e = state.fieldErrors ?? {};
  return (
    <form action={action} className="flex flex-col gap-4">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      {state.success && <Alert kind="success">{state.success}</Alert>}
      <input type="hidden" name="id" value={id} />
      <div className="grid grid-cols-2 gap-3">
        <Field label="Data" name="date" type="date" required defaultValue={v.date ?? date} error={e.date} />
        <Field label="Horário" name="time" type="time" required defaultValue={v.time ?? time} error={e.time} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Select label="Duração (min)" name="duration" defaultValue={v.duration ?? duration}>
          {[...new Set([...DURATIONS, duration])].map((d) => <option key={d} value={d}>{d}</option>)}
        </Select>
        <Select label="Modalidade" name="modality" defaultValue={v.modality ?? modality}>
          <option value="presencial">Presencial</option>
          <option value="online">On-line</option>
        </Select>
      </div>
      <div><SubmitButton variant="secondary" pendingText="Salvando…">Salvar alterações</SubmitButton></div>
    </form>
  );
}

const STATUS_ACTIONS: { status: string; label: string; variant: "primary" | "secondary" | "danger" }[] = [
  { status: "completed", label: "Marcar como realizada", variant: "primary" },
  { status: "no_show", label: "Paciente faltou", variant: "secondary" },
  { status: "cancelled", label: "Cancelar consulta", variant: "danger" },
  { status: "scheduled", label: "Voltar para agendada", variant: "secondary" },
];

export function StatusButtons({ id, current }: { id: number; current: string }) {
  const [state, action] = useActionState(setAppointmentStatusAction, initial);
  return (
    <div className="flex flex-col gap-3">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <div className="flex flex-wrap gap-2">
        {STATUS_ACTIONS.filter((a) => a.status !== current).map((a) => (
          <form key={a.status} action={action}>
            <input type="hidden" name="id" value={id} />
            <input type="hidden" name="status" value={a.status} />
            {a.status === "cancelled" ? (
              <ConfirmSubmit question="Cancelar esta consulta?" confirmText="Cancelar consulta" pendingText="Cancelando…">
                {a.label}
              </ConfirmSubmit>
            ) : (
              <SubmitButton variant={a.variant} pendingText="Salvando…">{a.label}</SubmitButton>
            )}
          </form>
        ))}
      </div>
    </div>
  );
}

export function AvailabilityForm({ slots }: { slots: AvailabilitySlot[] }) {
  const [state, action] = useActionState(saveAvailabilityAction, initial);
  const byDay = WEEKDAYS.map((_, day) => slots.filter((s) => s.weekday === day));
  const timeInput = `${inputClasses} w-auto border-gray-300 px-2 py-1.5`;

  return (
    <form action={action} className="flex flex-col gap-4">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      {state.success && <Alert kind="success">{state.success}</Alert>}
      <div className="overflow-x-auto">
        <table className="text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-gray-500">
            <tr><th className="py-2 pr-6 font-medium">Dia</th><th className="pr-6 font-medium">Manhã (ou período 1)</th><th className="font-medium">Tarde (ou período 2)</th></tr>
          </thead>
          <tbody>
            {WEEKDAYS.map((label, day) => (
              <tr key={day} className="border-t border-gray-100">
                <td className="py-2.5 pr-6 font-medium text-gray-800">{label}</td>
                {[0, 1].map((i) => (
                  <td key={i} className="pr-6">
                    <div className="flex items-center gap-1.5 text-gray-400">
                      <input type="time" name={`start_${day}_${i}`} aria-label={`${label} período ${i + 1} início`}
                        defaultValue={byDay[day][i]?.start_time.slice(0, 5)} className={timeInput} />
                      <span>às</span>
                      <input type="time" name={`end_${day}_${i}`} aria-label={`${label} período ${i + 1} fim`}
                        defaultValue={byDay[day][i]?.end_time.slice(0, 5)} className={timeInput} />
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">Deixe em branco os dias sem atendimento. Ex.: manhã 08:00 às 12:00 e tarde 14:00 às 18:00.</p>
      <div><SubmitButton pendingText="Salvando…">Salvar horários</SubmitButton></div>
    </form>
  );
}
