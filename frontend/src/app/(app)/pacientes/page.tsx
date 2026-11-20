import Link from "next/link";

import { ArchiveIcon, PlusIcon, UsersIcon } from "@/components/icons";
import { EmptyState, PageHeader } from "@/components/page";
import { PatientList } from "@/components/patient-list";
import { Alert } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { Patient } from "@/lib/types";
import { buttonClasses } from "@/lib/ui-classes";

export default async function PatientsPage({ searchParams }: PageProps<"/pacientes">) {
  const { arquivados, busca } = await searchParams;
  const showArchived = arquivados === "1";

  const result = await apiFetch<Patient[]>(`/patients?archived=${showArchived}`);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title={showArchived ? "Pacientes arquivados" : "Pacientes"}
        subtitle={showArchived ? "Os dados continuam guardados e podem ser restaurados." : undefined}
        actions={
          <>
            <Link href={showArchived ? "/pacientes" : "/pacientes?arquivados=1"} className={buttonClasses("secondary")}>
              {showArchived ? <UsersIcon className="h-4 w-4" /> : <ArchiveIcon className="h-4 w-4" />}
              {showArchived ? "Ver ativos" : "Arquivados"}
            </Link>
            {!showArchived && (
              <Link href="/pacientes/novo" className={buttonClasses("primary")}>
                <PlusIcon className="h-4 w-4" /> Novo paciente
              </Link>
            )}
          </>
        }
      />

      {!result.ok ? (
        <Alert kind="error">{result.error}</Alert>
      ) : result.data.length === 0 ? (
        showArchived ? (
          <EmptyState icon={<ArchiveIcon />} title="Nenhum paciente arquivado" />
        ) : (
          <EmptyState icon={<UsersIcon />} title="Nenhum paciente cadastrado ainda"
            text="Cadastre seu primeiro paciente para começar a agendar consultas e registrar sessões."
            action={<Link href="/pacientes/novo" className={buttonClasses("primary")}><PlusIcon className="h-4 w-4" /> Cadastrar paciente</Link>} />
        )
      ) : (
        <PatientList key={typeof busca === "string" ? busca : ""} patients={result.data} archived={showArchived}
          initialQuery={typeof busca === "string" ? busca.slice(0, 100) : ""} />
      )}
    </div>
  );
}
