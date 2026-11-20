/** Avatar com as iniciais do paciente; a cor sai do nome (sempre a mesma para a mesma pessoa). */
const TONES = [
  "bg-brand-100 text-brand-800",
  "bg-accent-100 text-accent-700",
  "bg-emerald-100 text-emerald-800",
  "bg-sky-100 text-sky-800",
  "bg-rose-100 text-rose-800",
  "bg-violet-100 text-violet-800",
  "bg-amber-100 text-amber-800",
  "bg-teal-100 text-teal-800",
];

export function initials(name: string) {
  return name.split(" ").filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("") || "·";
}

function toneOf(name: string) {
  let hash = 0;
  for (const ch of name) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return TONES[hash % TONES.length];
}

export function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  const dims = { sm: "h-8 w-8 text-[11px]", md: "h-10 w-10 text-xs", lg: "h-16 w-16 text-lg" }[size];
  return (
    <span className={`grid shrink-0 place-items-center rounded-full font-semibold ${dims} ${toneOf(name)}`} aria-hidden="true">
      {initials(name)}
    </span>
  );
}
