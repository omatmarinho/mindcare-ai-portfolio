// Esqueleto exibido enquanto uma página carrega os dados (troca de tela imediata)
export function PageSkeleton() {
  return (
    <div className="flex animate-pulse flex-col gap-6" aria-busy="true" aria-label="Carregando">
      <div className="flex flex-col gap-2">
        <div className="h-7 w-48 rounded-md bg-gray-200" />
        <div className="h-4 w-64 rounded-md bg-gray-200/70" />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {[0, 1, 2].map((i) => <div key={i} className="h-24 rounded-xl bg-white" />)}
      </div>
      <div className="h-64 rounded-xl bg-white" />
    </div>
  );
}
