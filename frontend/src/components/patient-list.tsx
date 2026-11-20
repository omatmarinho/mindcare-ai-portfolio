"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ChevronRightIcon, SearchIcon } from "@/components/icons";
import { formatDateTime } from "@/lib/format";
import type { Patient } from "@/lib/types";
import { inputClasses } from "@/lib/ui-classes";

/** Remove acentos e maiúsculas: "João" encontra "joao". */
function normalize(text: string) {
  return text.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function initials(name: string) {
  return name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

/** Lista de pacientes com busca instantânea (nome ou e-mail). */
export function PatientList({ patients, archived, initialQuery = "" }: {
  patients: Patient[]; archived: boolean; initialQuery?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const filtered = useMemo(() => {
    const q = normalize(query.trim());
    if (!q) return patients;
    return patients.filter((p) => normalize(`${p.full_name} ${p.email ?? ""}`).includes(q));
  }, [patients, query]);

  return (
    <div className="flex flex-col gap-4">
      <div className="relative max-w-md">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar por nome ou e-mail"
          aria-label="Buscar paciente"
          className={`${inputClasses} border-gray-300 pl-9`}
        />
      </div>

      {filtered.length === 0 ? (
        <p className="rounded-xl border border-dashed border-gray-300 bg-white/60 px-6 py-8 text-center text-sm text-gray-500">
          Nenhum paciente encontrado para &quot;{query}&quot;.
        </p>
      ) : (
        <ul className="card divide-y divide-gray-100 overflow-hidden">
          {filtered.map((patient) => (
            <li key={patient.id}>
              <Link href={`/pacientes/${patient.id}`}
                className="group flex items-center gap-4 px-4 py-3.5 transition hover:bg-brand-50/40 sm:px-5">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
                  {initials(patient.full_name)}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-gray-900">{patient.full_name}</p>
                  <p className="truncate text-sm text-gray-500">
                    {archived ? `Arquivado em ${formatDateTime(patient.archived_at)}` : patient.email ?? "Sem e-mail"}
                  </p>
                </div>
                <div className="hidden items-center gap-2 sm:flex">
                  {patient.ai_consent_at && (
                    <span className="rounded-full border border-brand-200 bg-brand-50 px-2 py-0.5 text-xs text-brand-700">IA autorizada</span>
                  )}
                </div>
                <ChevronRightIcon className="h-4 w-4 shrink-0 text-gray-300 group-hover:text-brand-500" />
              </Link>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-gray-400">{filtered.length} de {patients.length} paciente(s)</p>
    </div>
  );
}
