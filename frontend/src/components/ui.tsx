"use client";

import { useState } from "react";
import { useFormStatus } from "react-dom";

import { AlertIcon, CheckIcon } from "@/components/icons";
import { buttonClasses, inputClasses, type ButtonSize, type ButtonVariant } from "@/lib/ui-classes";

/** Campo de formulário com rótulo, dica e mensagem de erro. */
export function Field({
  label,
  name,
  type = "text",
  defaultValue,
  error,
  required,
  autoComplete,
  hint,
}: {
  label: string;
  name: string;
  type?: string;
  defaultValue?: string;
  error?: string;
  required?: boolean;
  autoComplete?: string;
  hint?: string;
}) {
  const errorId = `${name}-error`;
  const hintId = `${name}-hint`;
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={name} className="text-sm font-medium text-gray-700">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        defaultValue={defaultValue}
        required={required}
        autoComplete={autoComplete}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : hint ? hintId : undefined}
        className={`${inputClasses} ${error ? "border-red-400 focus:border-red-500 focus:ring-red-500/15" : "border-gray-300"}`}
      />
      {hint && !error && <p id={hintId} className="text-xs text-gray-500">{hint}</p>}
      {error && (
        <p id={errorId} className="text-xs text-red-600">
          {error}
        </p>
      )}
    </div>
  );
}

/** Botão de envio que se desativa enquanto o formulário é processado. */
export function SubmitButton({
  children,
  pendingText = "Aguarde…",
  variant = "primary",
  size = "md",
}: {
  children: React.ReactNode;
  pendingText?: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}) {
  const { pending } = useFormStatus();
  return (
    <button type="submit" disabled={pending} className={buttonClasses(variant, size)}>
      {pending && <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" />}
      {pending ? pendingText : children}
    </button>
  );
}

/**
 * Botão para ações difíceis de desfazer (arquivar, cancelar, excluir).
 * O primeiro clique só pergunta; a ação acontece ao confirmar.
 */
export function ConfirmSubmit({
  children,
  question,
  confirmText = "Confirmar",
  pendingText = "Aguarde…",
  variant = "danger",
  size = "md",
  tone = "danger",
  name,
  value,
}: {
  children: React.ReactNode;
  question: string;
  confirmText?: string;
  pendingText?: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** "danger" para ações destrutivas; "primary" para ações definitivas mas positivas (ex.: aprovar). */
  tone?: "danger" | "primary";
  /** Enviados junto com o formulário pelo botão de confirmação (ex.: intent=approve). */
  name?: string;
  value?: string;
}) {
  const [asking, setAsking] = useState(false);
  const { pending } = useFormStatus();

  if (!asking) {
    return (
      <button type="button" onClick={() => setAsking(true)} className={buttonClasses(variant, size)}>
        {children}
      </button>
    );
  }
  const box = tone === "danger" ? "border-red-200 bg-red-50 text-red-800" : "border-brand-200 bg-brand-50 text-brand-800";
  return (
    <span className={`inline-flex flex-wrap items-center gap-2 rounded-lg border px-3 py-1.5 ${box}`} role="group">
      <span className="text-sm">{question}</span>
      <button type="submit" name={name} value={value} disabled={pending}
        className={buttonClasses(tone === "danger" ? "danger" : "primary", "sm")}>
        {pending ? pendingText : confirmText}
      </button>
      <button type="button" disabled={pending} onClick={() => setAsking(false)} className={buttonClasses("ghost", "sm")}>
        Voltar
      </button>
    </span>
  );
}

/** Mensagem de sucesso, erro ou informação. */
export function Alert({ kind, children }: { kind: "error" | "success" | "info"; children: React.ReactNode }) {
  const styles = {
    error: "border-red-200 bg-red-50 text-red-800",
    success: "border-brand-200 bg-brand-50 text-brand-800",
    info: "border-accent-100 bg-accent-50 text-accent-700",
  }[kind];
  return (
    <div role={kind === "error" ? "alert" : "status"} className={`flex items-start gap-2 rounded-lg border px-3 py-2.5 text-sm ${styles}`}>
      {kind === "success" ? <CheckIcon className="mt-0.5 h-4 w-4 shrink-0" /> : kind === "error" ? <AlertIcon className="mt-0.5 h-4 w-4 shrink-0" /> : null}
      <div>{children}</div>
    </div>
  );
}
