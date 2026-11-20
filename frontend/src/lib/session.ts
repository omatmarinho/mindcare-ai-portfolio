/**
 * Sessão do usuário, guardada em cookies httpOnly.
 *
 * httpOnly = o JavaScript do navegador NÃO consegue ler o cookie.
 * Assim, mesmo que um script malicioso rode na página (ataque XSS),
 * ele não consegue roubar os tokens. Só o servidor Next.js os lê e os
 * envia para a API FastAPI.
 *
 * Use apenas em código de servidor (Server Components, Server Actions,
 * Route Handlers e proxy).
 */
import { cookies } from "next/headers";

export const ACCESS_COOKIE = "mc_access";
export const REFRESH_COOKIE = "mc_refresh";

const REFRESH_MAX_AGE = 7 * 24 * 60 * 60; // 7 dias, igual ao backend

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  expires_in: number; // segundos
};

export function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production", // só HTTPS em produção
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

/**
 * O cookie do access token expira 30 s ANTES do token. Quando ele some,
 * o proxy percebe e renova a sessão com o refresh token.
 */
export function accessMaxAge(expiresIn: number) {
  return Math.max(expiresIn - 30, 0);
}

export async function saveSession(tokens: TokenPair) {
  const store = await cookies();
  store.set(ACCESS_COOKIE, tokens.access_token, cookieOptions(accessMaxAge(tokens.expires_in)));
  store.set(REFRESH_COOKIE, tokens.refresh_token, cookieOptions(REFRESH_MAX_AGE));
}

export async function clearSession() {
  const store = await cookies();
  store.delete(ACCESS_COOKIE);
  store.delete(REFRESH_COOKIE);
}

export async function getAccessToken() {
  return (await cookies()).get(ACCESS_COOKIE)?.value;
}

export { REFRESH_MAX_AGE };
