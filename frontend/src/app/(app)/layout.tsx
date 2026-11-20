import Form from "next/form";
import Link from "next/link";
import { Suspense } from "react";

import { logoutAction } from "@/actions/auth";
import { AppNav } from "@/components/app-nav";
import { CodeIcon, LogoutIcon, PlusIcon, SearchIcon } from "@/components/icons";
import { apiFetch } from "@/lib/api";
import { DEMO_HOURS, REPO_URL } from "@/lib/project";
import type { User } from "@/lib/types";

function initialsOf(name: string) {
  return name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
}

// Nome do psicólogo: depende da sessão, então carrega dentro de <Suspense>
async function CurrentUser({ compact = false }: { compact?: boolean }) {
  const me = await apiFetch<User>("/auth/me");
  const name = me.ok ? me.data.full_name : "";
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent-100 text-xs font-semibold text-accent-700 ring-2 ring-white">
        {initialsOf(name) || "·"}
      </span>
      <span className="min-w-0 leading-tight">
        <span className="block truncate text-sm font-medium text-gray-900">{name}</span>
        {!compact && <span className="block text-xs text-gray-500">Psicólogo(a)</span>}
      </span>
    </div>
  );
}

function LogoutButton({ className = "" }: { className?: string }) {
  return (
    <form action={logoutAction}>
      <button type="submit" title="Sair de todos os dispositivos"
        className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-800 ${className}`}>
        <LogoutIcon className="h-4 w-4" /> Sair
      </button>
    </form>
  );
}

/** Aviso fixo: é uma demonstração, com dados fictícios e conta temporária. */
function DemoBanner() {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-accent-200 bg-accent-50 px-4 py-3 text-sm text-accent-900 sm:flex-row sm:items-center sm:justify-between">
      <p>
        <strong className="font-semibold">Demonstração.</strong> Todos os dados são fictícios e esta conta é apagada em {DEMO_HOURS} horas.
        A IA está simulada; o código da IA real está no repositório.
      </p>
      <a href={REPO_URL} target="_blank" rel="noreferrer"
        className="inline-flex shrink-0 items-center gap-1.5 self-start rounded-lg bg-white px-3 py-1.5 font-medium text-gray-800 ring-1 ring-accent-200 hover:bg-accent-100 sm:self-auto">
        <CodeIcon className="h-4 w-4" /> Ver código
      </a>
    </div>
  );
}

/** Pé do menu lateral: atalho para agendar e botão de sair. */
function SidebarBottom() {
  return (
    <div className="flex flex-col gap-2">
      <div className="relative overflow-hidden rounded-2xl bg-brand-800 p-4 text-white">
        <div className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-brand-600/60" aria-hidden="true" />
        <p className="relative text-sm font-semibold">Nova consulta</p>
        <p className="relative mt-1 text-xs leading-relaxed text-brand-100">
          Escolha o paciente e um horário livre da sua agenda.
        </p>
        <Link href="/agenda/nova"
          className="relative mt-3 flex items-center justify-center gap-1.5 rounded-lg bg-accent-500 px-3 py-2 text-sm font-medium text-brand-900 transition hover:bg-accent-300">
          <PlusIcon className="h-4 w-4" /> Agendar
        </Link>
      </div>
      <LogoutButton className="w-full" />
    </div>
  );
}

function MobileFooter() {
  return (
    <div className="flex items-center justify-between gap-2">
      <Suspense fallback={<span className="text-sm text-gray-400">…</span>}>
        <CurrentUser compact />
      </Suspense>
      <LogoutButton />
    </div>
  );
}

/** Barra do topo (computador): busca de pacientes e o psicólogo logado. */
function TopBar() {
  return (
    <div className="hidden items-center justify-between gap-4 lg:flex">
      <Form action="/pacientes" className="relative w-full max-w-sm">
        <SearchIcon className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input type="search" name="busca" placeholder="Buscar paciente…" aria-label="Buscar paciente" autoComplete="off"
          className="w-full rounded-xl border border-gray-200/70 bg-white py-2.5 pl-10 pr-3 text-sm text-gray-900 outline-none transition placeholder:text-gray-400 focus:border-brand-400 focus:ring-3 focus:ring-brand-500/15" />
      </Form>
      <div className="rounded-xl border border-gray-200/70 bg-white py-1.5 pl-2 pr-4">
        <Suspense fallback={<span className="block h-9 w-40" />}>
          <CurrentUser />
        </Suspense>
      </div>
    </div>
  );
}

// Layout da área logada: menu lateral flutuante (ou superior, no celular) + conteúdo
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 flex-col">
      {/* Atalho para quem navega pelo teclado: pula o menu e vai direto ao conteúdo */}
      <a href="#conteudo"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-brand-800 focus:shadow-lg">
        Pular para o conteúdo
      </a>
      <AppNav footer={<MobileFooter />} sidebarBottom={<SidebarBottom />} />
      <main id="conteudo" className="flex-1 scroll-mt-20 lg:pl-[16.5rem]">
        <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-3">
          <TopBar />
          <DemoBanner />
          <div className="lg:pb-8">{children}</div>
        </div>
      </main>
    </div>
  );
}
