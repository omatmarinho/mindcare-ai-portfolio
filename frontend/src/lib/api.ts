/**
 * Cliente da API FastAPI, usado SOMENTE no servidor Next.js.
 *
 * O navegador nunca fala diretamente com a API: ele fala com o Next.js,
 * que adiciona o token (lido do cookie httpOnly) e repassa a chamada.
 */
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { getAccessToken } from "./session";

export const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/**
 * Chave interna combinada com a API (INTERNAL_API_KEY nos dois lados). Com ela, a API
 * pode ficar exposta na internet e mesmo assim só aceitar chamadas deste servidor.
 * Só existe no servidor: não tem o prefixo NEXT_PUBLIC_, então nunca vai ao navegador.
 */
export function internalKeyHeader(): Record<string, string> {
  const key = process.env.INTERNAL_API_KEY;
  return key ? { "X-Internal-Key": key } : {};
}

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; error: string; fieldErrors?: Record<string, string> };

/** Repassa IP e navegador do usuário (para rate limiting e auditoria no backend). */
async function forwardedHeaders(): Promise<Record<string, string>> {
  const incoming = await headers();
  const result: Record<string, string> = { ...internalKeyHeader() };
  const forwardedFor = incoming.get("x-forwarded-for") ?? incoming.get("x-real-ip");
  if (forwardedFor) result["X-Forwarded-For"] = forwardedFor;
  const userAgent = incoming.get("user-agent");
  if (userAgent) result["User-Agent"] = userAgent;
  return result;
}

/** Transforma a resposta de erro do FastAPI em mensagens legíveis. */
function parseError(status: number, body: unknown): { error: string; fieldErrors?: Record<string, string> } {
  const detail = (body as { detail?: unknown })?.detail;

  if (typeof detail === "string") return { error: detail };

  // 422: erros de validação do Pydantic, um por campo
  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    for (const item of detail as { loc?: unknown[]; msg?: string }[]) {
      const field = String(item.loc?.[item.loc.length - 1] ?? "geral");
      fieldErrors[field] = translateValidation(item.msg ?? "Valor inválido");
    }
    return { error: "Verifique os campos destacados.", fieldErrors };
  }

  if (status === 429) return { error: "Muitas tentativas. Aguarde um minuto e tente novamente." };
  return { error: "Não foi possível concluir a operação. Tente novamente." };
}

function translateValidation(msg: string): string {
  if (msg.includes("at least 8 characters")) return "Use pelo menos 8 caracteres.";
  if (msg.includes("at most 128")) return "Use no máximo 128 caracteres.";
  if (msg.includes("at least 1 character")) return "Campo obrigatório.";
  if (msg.includes("at most 150")) return "Use no máximo 150 caracteres.";
  if (msg.toLowerCase().includes("email")) return "Informe um e-mail válido.";
  return msg;
}

type FetchOptions = {
  method?: string;
  json?: unknown;
  form?: Record<string, string>;
  multipart?: FormData; // envio de arquivos (ex.: áudio)
  auth?: boolean; // envia o token do usuário (padrão: true)
};

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<ApiResult<T>> {
  const { method = "GET", json, form, multipart, auth = true } = options;
  const requestHeaders: Record<string, string> = await forwardedHeaders();

  if (auth) {
    const token = await getAccessToken();
    if (!token) redirect("/login");
    requestHeaders["Authorization"] = `Bearer ${token}`;
  }

  let body: BodyInit | undefined;
  if (json !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    requestHeaders["Content-Type"] = "application/x-www-form-urlencoded";
    body = new URLSearchParams(form).toString();
  } else if (multipart) {
    body = multipart; // o fetch define o Content-Type (com o "boundary") sozinho
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers: requestHeaders,
      body,
      cache: "no-store", // dados de pacientes nunca são armazenados em cache
    });
  } catch {
    return { ok: false, status: 0, error: "Não foi possível conectar ao servidor. Tente novamente." };
  }

  // Sessão inválida (ex.: logout em outro dispositivo): volta ao login
  if (auth && response.status === 401) redirect("/login?sessao=expirada");

  const data = response.status === 204 ? null : await response.json().catch(() => null);

  if (!response.ok) return { ok: false, status: response.status, ...parseError(response.status, data) };
  return { ok: true, status: response.status, data: data as T };
}
