import { AvailabilityForm } from "@/components/agenda-forms";
import { Card, PageHeader } from "@/components/page";
import { Alert } from "@/components/ui";
import { apiFetch } from "@/lib/api";
import type { AvailabilitySlot } from "@/lib/types";

export default async function AvailabilityPage() {
  const result = await apiFetch<AvailabilitySlot[]>("/agenda/availability");
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <PageHeader title="Horários de atendimento" back={{ href: "/agenda", label: "Agenda" }}
        subtitle="Usados para sugerir horários livres ao agendar. Você pode ter até dois períodos por dia." />
      <Card>
        {result.ok ? <AvailabilityForm slots={result.data} /> : <Alert kind="error">{result.error}</Alert>}
      </Card>
    </div>
  );
}
