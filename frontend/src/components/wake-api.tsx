"use client";

import { useEffect } from "react";

/**
 * Acorda a API assim que a tela de entrada abre. No plano gratuito ela "dorme" depois
 * de um tempo parada; com isso, quando o visitante clica no botão, ela já está de pé.
 * Usa o /health do próprio site (o navegador nunca fala direto com a API).
 */
export function WakeApi() {
  useEffect(() => {
    fetch("/health", { cache: "no-store" }).catch(() => {});
  }, []);
  return null;
}
