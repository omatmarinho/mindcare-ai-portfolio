/**
 * Ícones em SVG (traço de 1.75px, estilo "outline"), desenhados aqui para não
 * depender de biblioteca externa. Herdam a cor do texto (currentColor).
 */
type IconProps = { className?: string };

function Svg({ className = "h-5 w-5", children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}
      strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      {children}
    </svg>
  );
}

export const LogoMark = ({ className = "h-8 w-8" }: IconProps) => (
  // "Perfil e broto": cabeça de perfil com um broto crescendo dentro (cuidado com a mente).
  // O mesmo desenho está em src/app/icon.svg (ícone da aba do navegador).
  <svg viewBox="0 0 48 48" className={className} aria-hidden="true">
    <rect width="48" height="48" rx="13" fill="var(--color-brand-600)" />
    <path d="M18 41V34C13 31 10 26 10 20C10 12.3 16.3 7 24.5 7C32.3 7 38 12.3 38 19.3L41 25.3C41.4 26 41 26.6 40.3 26.7L37.5 27V31C37.5 33 36 34.5 34 34.5H29V41Z" fill="#fff" />
    <path d="M23 29V20" stroke="var(--color-brand-600)" strokeWidth="2" strokeLinecap="round" />
    <path d="M23 22C23 18 20.5 15.5 16 15.5C16 19.5 18.5 22 23 22Z" fill="var(--color-brand-600)" />
    <path d="M23 20C23 15 26 12 31 12C31 17 28 20 23 20Z" fill="var(--color-accent-500)" />
  </svg>
);

export const HomeIcon = (p: IconProps) => (
  <Svg {...p}><path d="M3 10.5 12 3l9 7.5" /><path d="M5 9.5V20h14V9.5" /><path d="M10 20v-5h4v5" /></Svg>
);
export const CalendarIcon = (p: IconProps) => (
  <Svg {...p}><rect x="3.5" y="5" width="17" height="15" rx="2.5" /><path d="M3.5 10h17M8 3v4M16 3v4" /></Svg>
);
export const UsersIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5" /><path d="M16 4.8a3.3 3.3 0 0 1 0 6.4M18 14.8c2 .7 3.2 2.4 3.5 5.2" /></Svg>
);
export const WalletIcon = (p: IconProps) => (
  <Svg {...p}><rect x="3" y="6" width="18" height="14" rx="2.5" /><path d="M3 10h18" /><path d="M16 15h2" /><path d="M6 6V5a2 2 0 0 1 2-2h8" /></Svg>
);
export const ShieldIcon = (p: IconProps) => (
  <Svg {...p}><path d="M12 3 4.5 6v5.5c0 4.5 3.2 8 7.5 9.5 4.3-1.5 7.5-5 7.5-9.5V6L12 3Z" /><path d="m9 12 2 2 4-4" /></Svg>
);
export const GlobeIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c2.4 2.5 3.5 5.3 3.5 8.5s-1.1 6-3.5 8.5c-2.4-2.5-3.5-5.3-3.5-8.5s1.1-6 3.5-8.5Z" /></Svg>
);
export const SparkIcon = (p: IconProps) => (
  <Svg {...p}><path d="M12 3.5 13.9 9l5.6 1.9-5.6 1.9L12 18.5l-1.9-5.7-5.6-1.9L10.1 9 12 3.5Z" /><path d="M19 3v3M17.5 4.5h3" /></Svg>
);
export const LogoutIcon = (p: IconProps) => (
  <Svg {...p}><path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4" /><path d="M10 16l-4-4 4-4M6 12h10" /></Svg>
);
export const MenuIcon = (p: IconProps) => (
  <Svg {...p}><path d="M4 7h16M4 12h16M4 17h16" /></Svg>
);
export const CloseIcon = (p: IconProps) => (
  <Svg {...p}><path d="M6 6l12 12M18 6 6 18" /></Svg>
);
export const PlusIcon = (p: IconProps) => (
  <Svg {...p}><path d="M12 5v14M5 12h14" /></Svg>
);
export const SearchIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="11" cy="11" r="6.5" /><path d="m20 20-4.2-4.2" /></Svg>
);
export const ChevronLeftIcon = (p: IconProps) => (
  <Svg {...p}><path d="m15 6-6 6 6 6" /></Svg>
);
export const ChevronRightIcon = (p: IconProps) => (
  <Svg {...p}><path d="m9 6 6 6-6 6" /></Svg>
);
export const NoteIcon = (p: IconProps) => (
  <Svg {...p}><path d="M7 3h7l5 5v13H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M14 3v5h5M9 13h7M9 17h5" /></Svg>
);
export const AlertIcon = (p: IconProps) => (
  <Svg {...p}><path d="M12 4 2.5 20h19L12 4Z" /><path d="M12 10v4M12 17.5v.01" /></Svg>
);
export const ClockIcon = (p: IconProps) => (
  <Svg {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></Svg>
);
export const RepeatIcon = (p: IconProps) => (
  <Svg {...p}><path d="M4 11V9.5A3.5 3.5 0 0 1 7.5 6H19" /><path d="m16 3 3 3-3 3" /><path d="M20 13v1.5a3.5 3.5 0 0 1-3.5 3.5H5" /><path d="m8 21-3-3 3-3" /></Svg>
);
export const DownloadIcon = (p: IconProps) => (
  <Svg {...p}><path d="M12 4v11M7 10l5 5 5-5M5 20h14" /></Svg>
);
export const ArchiveIcon = (p: IconProps) => (
  <Svg {...p}><rect x="3" y="4" width="18" height="5" rx="1.5" /><path d="M5 9v9a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9M10 13h4" /></Svg>
);
export const MicIcon = (p: IconProps) => (
  <Svg {...p}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" /></Svg>
);
export const CheckIcon = (p: IconProps) => (
  <Svg {...p}><path d="m5 12.5 4.5 4.5L19 7.5" /></Svg>
);
export const CodeIcon = (p: IconProps) => (
  <Svg {...p}><path d="m8 8-4 4 4 4" /><path d="m16 8 4 4-4 4" /><path d="m14 5-4 14" /></Svg>
);
