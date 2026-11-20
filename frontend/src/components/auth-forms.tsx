"use client";

import { useActionState } from "react";

import { demoAction, loginAction } from "@/actions/auth";
import { Alert, Field, SubmitButton } from "@/components/ui";
import type { FormState } from "@/lib/types";

const initial: FormState = {};

/** Botão principal da demonstração: cada visitante ganha a própria conta temporária. */
export function DemoButton() {
  const [state, action] = useActionState(demoAction, initial);
  return (
    <form action={action} className="flex flex-col gap-3">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <SubmitButton pendingText="Preparando a demonstração…">Experimentar a demonstração</SubmitButton>
      <p className="text-center text-xs text-gray-500">
        Sem cadastro. Você entra numa conta só sua, com pacientes e sessões fictícias, apagada em 24 horas.
        No primeiro acesso, o servidor gratuito pode levar até um minuto para acordar.
      </p>
    </form>
  );
}

export function LoginForm({ next, notice }: { next?: string; notice?: string }) {
  const [state, action] = useActionState(loginAction, initial);
  return (
    <form action={action} className="flex flex-col gap-4">
      {notice && !state.error && <Alert kind="info">{notice}</Alert>}
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <input type="hidden" name="next" value={next ?? "/"} />
      <Field label="E-mail" name="email" type="email" required autoComplete="email" defaultValue={state.values?.email} />
      <Field label="Senha" name="password" type="password" required autoComplete="current-password" />
      <SubmitButton variant="secondary" pendingText="Entrando…">Entrar</SubmitButton>
    </form>
  );
}
