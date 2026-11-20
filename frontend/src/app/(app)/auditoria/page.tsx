import Link from "next/link";

import { ChevronLeftIcon, ChevronRightIcon, ShieldIcon } from "@/components/icons";
import { EmptyState, PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import { ACTION_LABELS, formatDateTime } from "@/lib/format";
import type { AuditLog } from "@/lib/types";
import { buttonClasses } from "@/lib/ui-classes";

const PAGE_SIZE = 50;

// Ações que merecem atenção (destacadas em vermelho)
function isAlert(action: string) {
  return action.endsWith("access_denied") || action === "auth.login_failed" || action === "auth.token_reuse_detected";
}

export default async function AuditPage({ searchParams }: PageProps<"/auditoria">) {
  const { pagina } = await searchParams;
  const page = Math.max(1, Number(typeof pagina === "string" ? pagina : 1) || 1);

  const result = await apiFetch<AuditLog[]>(`/audit-logs?limit=${PAGE_SIZE}&offset=${(page - 1) * PAGE_SIZE}`);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Histórico de acessos"
        subtitle="Tudo o que foi feito com a sua conta. Este registro não pode ser alterado nem apagado."
      />

      {!result.ok ? (
        <Alert kind="error">{result.error}</Alert>
      ) : result.data.length === 0 ? (
        <EmptyState icon={<ShieldIcon />} title="Nenhum registro nesta página" />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th className="px-5 py-3 font-medium">Quando</th>
                <th className="px-3 py-3 font-medium">Ação</th>
                <th className="px-3 py-3 font-medium">Paciente</th>
                <th className="px-5 py-3 font-medium">Origem</th>
              </tr>
            </thead>
            <tbody>
              {result.data.map((log) => (
                <tr key={log.id} className="border-t border-gray-100 hover:bg-gray-50/60">
                  <td className="whitespace-nowrap px-5 py-2.5 text-gray-500">{formatDateTime(log.occurred_at)}</td>
                  <td className={`px-3 py-2.5 ${isAlert(log.action) ? "font-medium text-red-700" : "text-gray-800"}`}>
                    {ACTION_LABELS[log.action] ?? log.action}
                  </td>
                  <td className="px-3 py-2.5">
                    {log.resource_type === "patient" && log.resource_id ? (
                      <Link href={`/pacientes/${log.resource_id}`} className="text-brand-700 hover:underline">
                        Ver paciente
                      </Link>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-5 py-2.5 font-mono text-xs text-gray-400">{log.ip_address ?? "sistema"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex gap-2">
        {page > 1 && (
          <Link href={`/auditoria?pagina=${page - 1}`} className={buttonClasses("secondary", "sm")}>
            <ChevronLeftIcon className="h-4 w-4" /> Mais recentes
          </Link>
        )}
        {result.ok && result.data.length === PAGE_SIZE && (
          <Link href={`/auditoria?pagina=${page + 1}`} className={buttonClasses("secondary", "sm")}>
            Mais antigos <ChevronRightIcon className="h-4 w-4" />
          </Link>
        )}
      </div>
    </div>
  );
}
