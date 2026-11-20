/**
 * Peças de layout das páginas (componentes de servidor, sem interatividade):
 * cabeçalho, cartão, tela vazia, rótulo de status e link "voltar".
 */
import Link from "next/link";

import { ChevronLeftIcon } from "@/components/icons";

export function PageHeader({ title, subtitle, actions, back }: {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  back?: { href: string; label: string };
}) {
  return (
    <div className="flex flex-col gap-3">
      {back && (
        <Link href={back.href} className="inline-flex w-fit items-center gap-1 text-sm text-gray-500 hover:text-brand-700">
          <ChevronLeftIcon className="h-4 w-4" /> {back.label}
        </Link>
      )}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-balance text-2xl font-semibold tracking-tight text-gray-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export function Card({ title, description, actions, children, className = "" }: {
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`card min-w-0 p-5 sm:p-6 ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-balance text-base font-semibold text-gray-900">{title}</h2>}
            {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
          </div>
          {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function EmptyState({ icon, title, text, action }: {
  icon?: React.ReactNode;
  title: string;
  text?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-gray-300 bg-white/60 px-6 py-10 text-center">
      {icon && <div className="mb-1 grid h-11 w-11 place-items-center rounded-full bg-brand-50 text-brand-600">{icon}</div>}
      <p className="font-medium text-gray-800">{title}</p>
      {text && <p className="max-w-md text-sm text-gray-500">{text}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Badge({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <span className={`inline-flex items-center whitespace-nowrap rounded-full border px-2.5 py-0.5 text-xs font-medium ${className}`}>
      {children}
    </span>
  );
}
