/**
 * Verificação de saúde para o monitor de disponibilidade.
 *
 * Responde 200 só se o site E a API estiverem funcionando (a API não é
 * acessível pela internet, então o monitor pergunta por aqui).
 * Não devolve detalhes internos: só "ok" ou "erro".
 */
import { connection } from "next/server";

import { API_URL } from "@/lib/api";

export async function GET() {
  await connection(); // sempre na hora do pedido, nunca uma resposta pronta do build

  try {
    const response = await fetch(`${API_URL}/health`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) return Response.json({ status: "ok" });
  } catch {
    // API fora do ar ou lenta demais: cai no erro abaixo
  }
  return Response.json({ status: "erro" }, { status: 503 });
}
