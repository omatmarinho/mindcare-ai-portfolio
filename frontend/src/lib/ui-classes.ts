/**
 * Classes de estilo compartilhadas (podem ser usadas em componentes de
 * servidor e de cliente, por isso ficam fora dos arquivos "use client").
 */
export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
export type ButtonSize = "sm" | "md";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-brand-600 text-white shadow-sm hover:bg-brand-700",
  secondary: "border border-gray-300 bg-white text-gray-700 hover:border-gray-400 hover:bg-gray-50",
  ghost: "text-brand-700 hover:bg-brand-50",
  danger: "border border-red-200 bg-white text-red-700 hover:bg-red-50",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
};

export function buttonClasses(variant: ButtonVariant = "primary", size: ButtonSize = "md") {
  return `inline-flex items-center justify-center gap-2 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${SIZES[size]}`;
}

export const inputClasses =
  "w-full rounded-lg border bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition focus:border-brand-500 focus:ring-3 focus:ring-brand-500/15";
