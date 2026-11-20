"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";

import { CalendarIcon, CloseIcon, HomeIcon, LogoMark, MenuIcon, ShieldIcon, UsersIcon } from "@/components/icons";

const ITEMS = [
  { href: "/", label: "Início", icon: HomeIcon },
  { href: "/agenda", label: "Agenda", icon: CalendarIcon },
  { href: "/pacientes", label: "Pacientes", icon: UsersIcon },
  { href: "/auditoria", label: "Histórico de acessos", icon: ShieldIcon },
];

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  // Registros de sessão fazem parte da área de pacientes
  if (href === "/pacientes" && pathname.startsWith("/registros")) return true;
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** Menu sem destaque, mostrado enquanto o endereço atual ainda não é conhecido. */
function NavLinksStatic() {
  return (
    <ul className="flex flex-col gap-1">
      {ITEMS.map(({ href, label, icon: Icon }) => (
        <li key={href}>
          <Link href={href} className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900">
            <Icon className="h-5 w-5 text-gray-400" />
            {label}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Menu com o item da página atual em destaque (lê o endereço: precisa de <Suspense>). */
function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Suspense fallback={<NavLinksStatic />}>
      <ActiveNavLinks onNavigate={onNavigate} />
    </Suspense>
  );
}

function ActiveNavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <ul className="flex flex-col gap-1">
      {ITEMS.map(({ href, label, icon: Icon }) => {
        const active = isActive(pathname, href);
        return (
          <li key={href}>
            <Link
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                active
                  ? "bg-brand-600 font-medium text-white shadow-sm shadow-brand-900/10"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Icon className={`h-5 w-5 ${active ? "text-accent-300" : "text-gray-400"}`} />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2.5">
      <LogoMark />
      <span className="text-[1.05rem] font-semibold tracking-tight text-brand-800" translate="no">Psi<span className="text-accent-600">nara</span></span>
    </Link>
  );
}

/**
 * Menu lateral flutuante (computador) e barra superior com menu recolhível (celular).
 * `sidebarBottom`: conteúdo fixo no pé do menu lateral; `footer`: pé do menu do celular.
 */
export function AppNav({ footer, sidebarBottom }: { footer: React.ReactNode; sidebarBottom: React.ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Computador */}
      <aside className="fixed inset-y-3 left-3 z-30 hidden w-60 flex-col overflow-y-auto rounded-2xl border border-gray-200/70 bg-white lg:flex">
        <div className="px-5 pb-4 pt-6"><Brand /></div>
        <p className="px-6 pb-2 pt-2 text-[11px] font-medium uppercase tracking-wider text-gray-400">Menu</p>
        <nav aria-label="Menu principal" className="flex-1 px-3">
          <NavLinks />
        </nav>
        <div className="p-3">{sidebarBottom}</div>
      </aside>

      {/* Celular */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-gray-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden">
        <Brand />
        <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="menu-celular"
          className="rounded-lg p-2 text-gray-600 hover:bg-gray-100" aria-label={open ? "Fechar menu" : "Abrir menu"}>
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
      </header>
      {open && (
        <div id="menu-celular" className="sticky top-[61px] z-20 border-b border-gray-200 bg-white px-3 pb-3 shadow-sm lg:hidden">
          <nav aria-label="Menu principal" className="pt-2"><NavLinks onNavigate={() => setOpen(false)} /></nav>
          <div className="mt-3 border-t border-gray-200 pt-3">{footer}</div>
        </div>
      )}
    </>
  );
}
