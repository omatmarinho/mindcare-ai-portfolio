"use server";

/**
 * Server Actions de autenticação: executam no SERVIDOR Next.js.
 * O navegador envia o formulário; o servidor chama a API FastAPI
 * e guarda os tokens em cookies httpOnly.
 */
import { redirect } from "next/navigation";

import { apiFetch } from "@/lib/api";
import { clearSession, saveSession, type TokenPair } from "@/lib/session";
import type { FormState, Message } from "@/lib/types";

function field(formData: FormData, name: string) {
  return String(formData.get(name) ?? "").trim();
}

/**
 * Só aceita destinos dentro do próprio site depois do login.
 * "/\evil.com" e "//evil.com" são tratados pelo navegador como outro site,
 * por isso a checagem é feita resolvendo o endereço de verdade.
 */
function safeNext(value: string) {
  const fallback = "/";
  if (!value.startsWith("/") || value.includes("\\")) return fallback;
  try {
    const base = "http://psinara.local";
    const url = new URL(value, base);
    return url.origin === base ? url.pathname + url.search : fallback;
  } catch {
    return fallback;
  }
}

export async function loginAction(_prev: FormState, formData: FormData): Promise<FormState> {
  const email = field(formData, "email");
  const password = String(formData.get("password") ?? "");

  const result = await apiFetch<TokenPair>("/auth/login", {
    method: "POST",
    form: { username: email, password },
    auth: false,
  });

  if (!result.ok) return { error: result.error, values: { email } };

  await saveSession(result.data);
  redirect(safeNext(field(formData, "next")));
}

/** Demonstração: cria uma conta temporária com dados fictícios e entra nela. */
// O primeiro parâmetro (estado anterior) é exigido pelo useActionState e não é usado aqui
export async function demoAction(): Promise<FormState> {
  const result = await apiFetch<TokenPair>("/demo/session", { method: "POST", auth: false });
  if (!result.ok) return { error: result.status === 404 ? "A demonstração não está ligada neste servidor." : result.error };
  await saveSession(result.data);
  redirect("/");
}

export async function logoutAction() {
  // Encerra a sessão em TODOS os dispositivos (o backend revoga os tokens)
  await apiFetch<Message>("/auth/logout", { method: "POST" }).catch(() => null);
  await clearSession();
  redirect("/login?sessao=encerrada");
}
