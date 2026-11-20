/**
 * Baixa todos os dados do paciente em um arquivo JSON (LGPD: acesso e portabilidade).
 *
 * O navegador não fala com a API: este handler roda no servidor Next.js,
 * usa o token do cookie httpOnly e devolve o arquivo para download.
 */
import type { NextRequest } from "next/server";

import { apiFetch } from "@/lib/api";

export async function GET(_req: NextRequest, ctx: RouteContext<"/pacientes/[id]/exportar">) {
  const { id } = await ctx.params;
  if (!/^\d+$/.test(id)) return new Response("Paciente inválido", { status: 400 });

  const result = await apiFetch<unknown>(`/patients/${id}/export`);
  if (!result.ok) return new Response(result.error, { status: result.status || 502 });

  const today = new Date().toISOString().slice(0, 10);
  return new Response(JSON.stringify(result.data, null, 2), {
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Content-Disposition": `attachment; filename="paciente-${id}-${today}.json"`,
      "Cache-Control": "no-store",
    },
  });
}
