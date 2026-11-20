import { DemoButton, LoginForm } from "@/components/auth-forms";

const NOTICES: Record<string, string> = {
  expirada: "Sua sessão expirou. Entre novamente.",
  encerrada: "Você saiu da sua conta.",
};

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const params = await searchParams;
  const next = typeof params.next === "string" ? params.next : undefined;
  const sessao = typeof params.sessao === "string" ? params.sessao : "";

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">Conheça o MindCare AI</h1>
        <p className="mt-1 text-sm text-gray-500">
          Gestão de consultório para psicólogos, com registros de sessão organizados por IA e revisados pelo profissional.
        </p>
      </div>
      <DemoButton />
      <details className="mt-8 border-t border-gray-200 pt-4">
        <summary className="cursor-pointer text-sm text-gray-500 hover:text-gray-800">Já tenho uma conta</summary>
        <div className="mt-4">
          <LoginForm next={next} notice={NOTICES[sessao]} />
        </div>
      </details>
    </>
  );
}
