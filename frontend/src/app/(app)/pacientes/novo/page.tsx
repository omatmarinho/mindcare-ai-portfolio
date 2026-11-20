import { Card, PageHeader } from "@/components/page";
import { NewPatientForm } from "@/components/patient-forms";

export default function NewPatientPage() {
  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <PageHeader title="Novo paciente" back={{ href: "/pacientes", label: "Pacientes" }}
        subtitle="Só o nome é obrigatório. O restante pode ser preenchido depois." />
      <Card>
        <NewPatientForm />
      </Card>
    </div>
  );
}
