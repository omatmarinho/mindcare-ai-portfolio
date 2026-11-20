import { Suspense } from "react";

import { CheckIcon, CodeIcon, LogoMark } from "@/components/icons";
import { REPO_URL } from "@/lib/project";

const PROMISES = [
  "Agenda e pacientes em um só lugar, com indicadores do consultório",
  "IA que transcreve e organiza seus registros, sempre com a sua revisão",
  "Registros criptografados, trilha de auditoria e exportação (LGPD)",
];

// Layout das telas públicas (login, cadastro, senha...): painel da marca + formulário.
// <Suspense>: algumas telas leem parâmetros da URL (ex.: ?token=...)
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid flex-1 lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-brand-800 px-12 py-14 text-white lg:flex lg:flex-col lg:justify-between">
        {/* Formas suaves ao fundo */}
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-brand-600/40 blur-2xl" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-accent-500/20 blur-3xl" aria-hidden="true" />

        <div className="relative flex items-center gap-3">
          <LogoMark className="h-10 w-10" />
          <span className="text-xl font-semibold tracking-tight" translate="no">MindCare <span className="text-accent-300">AI</span></span>
        </div>

        <div className="relative max-w-md">
          <h2 className="text-3xl font-semibold leading-tight tracking-tight">
            Mais tempo para o cuidado, menos tempo com burocracia.
          </h2>
          <ul className="mt-8 flex flex-col gap-4">
            {PROMISES.map((text) => (
              <li key={text} className="flex items-start gap-3 text-brand-100">
                <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-white/10 text-accent-300">
                  <CheckIcon className="h-4 w-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-brand-200">A IA não faz diagnósticos: todo conteúdo passa pela revisão do psicólogo.</p>
      </section>

      <section className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center justify-center gap-2.5 lg:hidden">
            <LogoMark className="h-9 w-9" />
            <span className="text-xl font-semibold tracking-tight text-brand-800" translate="no">MindCare <span className="text-accent-600">AI</span></span>
          </div>
          <Suspense fallback={<p className="text-sm text-gray-500">Carregando…</p>}>{children}</Suspense>
          <a href={REPO_URL} target="_blank" rel="noreferrer"
            className="mt-10 flex items-center justify-center gap-1.5 text-xs text-gray-500 hover:text-brand-700">
            <CodeIcon className="h-4 w-4" /> Código-fonte no GitHub
          </a>
        </div>
      </section>
    </main>
  );
}
