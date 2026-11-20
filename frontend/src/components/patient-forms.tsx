"use client";

import { useActionState } from "react";

import { createPatientAction, updatePatientAction } from "@/actions/patients";
import { Alert, Field, SubmitButton } from "@/components/ui";
import type { FormState, Patient } from "@/lib/types";

const initial: FormState = {};

export function NewPatientForm() {
  const [state, action] = useActionState(createPatientAction, initial);
  const errors = state.fieldErrors ?? {};
  return (
    <form action={action} className="flex flex-col gap-4">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <Field label="Nome completo" name="full_name" required defaultValue={state.values?.full_name} error={errors.full_name} />
      <Field label="E-mail (opcional)" name="email" type="email" defaultValue={state.values?.email} error={errors.email} />
      <Field label="Celular (opcional)" name="phone" type="tel" autoComplete="off" defaultValue={state.values?.phone}
        error={errors.phone} hint="Com DDD. Ex.: (11) 98888-7777" />
      <div>
        <SubmitButton pendingText="Salvando…">Cadastrar paciente</SubmitButton>
      </div>
    </form>
  );
}

export function EditPatientForm({ patient }: { patient: Patient }) {
  const [state, action] = useActionState(updatePatientAction, initial);
  const errors = state.fieldErrors ?? {};
  return (
    <form action={action} className="flex flex-col gap-4">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      {state.success && <Alert kind="success">{state.success}</Alert>}
      <input type="hidden" name="id" value={patient.id} />
      <Field label="Nome completo" name="full_name" required defaultValue={state.values?.full_name ?? patient.full_name} error={errors.full_name} />
      <Field label="E-mail (opcional)" name="email" type="email" defaultValue={state.values?.email ?? patient.email ?? ""} error={errors.email} />
      <Field label="Celular (opcional)" name="phone" type="tel" autoComplete="off"
        defaultValue={state.values?.phone ?? patient.phone ?? ""} error={errors.phone} hint="Com DDD. Ex.: (11) 98888-7777" />
      <div>
        <SubmitButton pendingText="Salvando…">Salvar alterações</SubmitButton>
      </div>
    </form>
  );
}
