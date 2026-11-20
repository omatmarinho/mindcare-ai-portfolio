/**
 * Proxy (antigo "middleware"): roda ANTES de cada página.
 *
 * 1. Páginas protegidas sem sessão -> manda para /login.
 * 2. Access token vencido mas refresh token válido -> renova a sessão
 *    em silêncio, sem o psicólogo perceber.
 * 3. Usuário logado tentando abrir /login ou /cadastro -> manda para /pacientes.
 *
 * Importante: o proxy é só a primeira barreira. A proteção real está no
 * backend, que valida o token em TODA chamada.
 */
import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  REFRESH_MAX_AGE,
  accessMaxAge,
  cookieOptions,
  type TokenPair,
} from "@/lib/session";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const PUBLIC_ONLY = ["/login"];

function isProtected(pathname: string) {
  return (
    pathname === "/" ||
    pathname.startsWith("/pacientes") ||
    pathname.startsWith("/registros") ||
    pathname === "/agenda" ||
    pathname.startsWith("/agenda/") ||
    pathname.startsWith("/auditoria")
  );
}

async function refresh(refreshToken: string, request: NextRequest): Promise<TokenPair | null> {
  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "User-Agent": request.headers.get("user-agent") ?? "",
        ...(process.env.INTERNAL_API_KEY ? { "X-Internal-Key": process.env.INTERNAL_API_KEY } : {}),
        ...(request.headers.get("x-forwarded-for")
          ? { "X-Forwarded-For": request.headers.get("x-forwarded-for")! }
          : {}),
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
    return response.ok ? ((await response.json()) as TokenPair) : null;
  } catch {
    return null;
  }
}

export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;

  if (PUBLIC_ONLY.includes(pathname) && access) {
    return NextResponse.redirect(new URL("/", request.url));
  }

  if (!isProtected(pathname) || access) {
    return NextResponse.next();
  }

  // Sem access token: tenta renovar com o refresh token
  const tokens = refreshToken ? await refresh(refreshToken, request) : null;

  if (!tokens) {
    const login = new URL("/login", request.url);
    login.searchParams.set("next", pathname + search);
    const response = NextResponse.redirect(login);
    response.cookies.delete(ACCESS_COOKIE);
    response.cookies.delete(REFRESH_COOKIE);
    return response;
  }

  // Coloca os tokens novos na requisição atual (para a página já usá-los)...
  request.cookies.set(ACCESS_COOKIE, tokens.access_token);
  request.cookies.set(REFRESH_COOKIE, tokens.refresh_token);
  const response = NextResponse.next({ request: { headers: request.headers } });

  // ...e manda o navegador guardá-los para as próximas
  response.cookies.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(accessMaxAge(tokens.expires_in)));
  response.cookies.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE));
  return response;
}

export const config = {
  // Não roda em arquivos estáticos, imagens e no ícone da aba
  matcher: ["/((?!_next/static|_next/image|icon.svg).*)"],
};
