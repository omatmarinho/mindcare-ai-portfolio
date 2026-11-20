"use client";

import { useRouter } from "next/navigation";
import { useActionState, useEffect, useRef, useState } from "react";

import {
  createAudioNoteAction,
  createTextNoteAction,
  giveConsentAction,
  retryNoteAction,
  updateNoteAction,
} from "@/actions/notes";
import { MicIcon, NoteIcon } from "@/components/icons";
import { Alert, ConfirmSubmit, SubmitButton } from "@/components/ui";
import type { FormState, NoteDetail } from "@/lib/types";
import { buttonClasses, inputClasses } from "@/lib/ui-classes";

const initial: FormState = {};

const textareaClass = `${inputClasses} border-gray-300 leading-relaxed`;

/** Novo registro: abas "Áudio" e "Texto" para não mostrar dois formulários de uma vez. */
export function NewNoteTabs({ patientId, appointmentId }: { patientId: number; appointmentId?: number }) {
  const [tab, setTab] = useState<"audio" | "text">("audio");
  const tabClass = (active: boolean) =>
    `flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition ${
      active ? "bg-white font-medium text-brand-800 shadow-sm" : "text-gray-500 hover:text-gray-800"
    }`;
  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label="Tipo de registro" className="inline-flex w-fit gap-1 rounded-lg bg-gray-100 p-1">
        <button type="button" role="tab" aria-selected={tab === "audio"} onClick={() => setTab("audio")} className={tabClass(tab === "audio")}>
          <MicIcon className="h-4 w-4" /> Áudio
        </button>
        <button type="button" role="tab" aria-selected={tab === "text"} onClick={() => setTab("text")} className={tabClass(tab === "text")}>
          <NoteIcon className="h-4 w-4" /> Texto
        </button>
      </div>
      <div role="tabpanel">
        {tab === "audio" ? <AudioNoteForm patientId={patientId} appointmentId={appointmentId} />
          : <TextNoteForm patientId={patientId} appointmentId={appointmentId} />}
      </div>
    </div>
  );
}

export function ConsentForm({ patientId }: { patientId: number }) {
  const [state, action] = useActionState(giveConsentAction, initial);
  return (
    <form action={action} className="flex flex-col gap-3">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <input type="hidden" name="patient_id" value={patientId} />
      <label className="flex items-start gap-3 rounded-lg border border-accent-100 bg-accent-50/60 p-4 text-sm text-gray-700">
        <input type="checkbox" name="confirm" className="mt-1 accent-brand-600" />
        <span>
          Confirmo que o paciente foi informado e <strong>consentiu</strong> com o uso de inteligência artificial
          para transcrever e organizar os registros das sessões. O processamento é feito nos servidores do
          MindCare AI, sem envio a terceiros, e todo conteúdo gerado passa pela minha revisão.
        </span>
      </label>
      <div>
        <SubmitButton pendingText="Registrando…">Registrar consentimento</SubmitButton>
      </div>
    </form>
  );
}

export function TextNoteForm({ patientId, appointmentId }: { patientId: number; appointmentId?: number }) {
  const [state, action] = useActionState(createTextNoteAction, initial);
  return (
    <form action={action} className="flex flex-col gap-3">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <input type="hidden" name="patient_id" value={patientId} />
      {appointmentId && <input type="hidden" name="appointment_id" value={appointmentId} />}
      <label htmlFor="text" className="text-sm font-medium text-gray-700">Texto da sessão ou ditado</label>
      <textarea id="text" name="text" rows={7} defaultValue={state.values?.text} className={textareaClass}
        placeholder="Escreva ou cole suas anotações da sessão. A IA organiza em resumo, tópicos e pontos de acompanhamento." />
      {state.fieldErrors?.text && <p className="text-xs text-red-600">{state.fieldErrors.text}</p>}
      <div>
        <SubmitButton pendingText="Enviando…">Organizar com IA</SubmitButton>
      </div>
    </form>
  );
}

export function AudioNoteForm({ patientId, appointmentId }: { patientId: number; appointmentId?: number }) {
  const [state, action] = useActionState(createAudioNoteAction, initial);
  const fileInput = useRef<HTMLInputElement>(null);
  return (
    <form action={action} className="flex flex-col gap-3">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <input type="hidden" name="patient_id" value={patientId} />
      {appointmentId && <input type="hidden" name="appointment_id" value={appointmentId} />}
      <span className="text-sm font-medium text-gray-700">Áudio da sessão ou ditado</span>
      <Recorder fileInput={fileInput} />
      <label htmlFor="audio" className="text-xs text-gray-600">…ou escolha um arquivo (até 100 MB):</label>
      <input ref={fileInput} id="audio" name="audio" type="file" accept="audio/*,video/webm,video/mp4"
        className="text-sm text-gray-600 file:mr-3 file:rounded-lg file:border file:border-gray-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:text-gray-700 hover:file:bg-gray-50" />
      {state.fieldErrors?.audio && <p className="text-xs text-red-600">{state.fieldErrors.audio}</p>}
      <p className="text-xs text-gray-500">O áudio é transcrito e em seguida apagado: ele não fica guardado.</p>
      <div>
        <SubmitButton pendingText="Enviando áudio…">Transcrever e organizar</SubmitButton>
      </div>
    </form>
  );
}

/**
 * Grava áudio pelo microfone do navegador (MediaRecorder).
 * A gravação fica só na memória do navegador até o envio; ao terminar,
 * ela é colocada no campo de arquivo do formulário, como se o usuário
 * tivesse escolhido um arquivo.
 */
function Recorder({ fileInput }: { fileInput: React.RefObject<HTMLInputElement | null> }) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
  }, []);

  async function start() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => e.data.size > 0 && chunks.push(e.data);
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop()); // desliga o microfone
        const type = recorder.mimeType || "audio/webm";
        const file = new File(chunks, `gravacao.${type.includes("mp4") ? "mp4" : "webm"}`, { type });
        const transfer = new DataTransfer();
        transfer.items.add(file);
        if (fileInput.current) fileInput.current.files = transfer.files;
        setPreviewUrl((old) => {
          if (old) URL.revokeObjectURL(old);
          return URL.createObjectURL(file);
        });
      };
      recorder.start(1000);
      recorderRef.current = recorder;
      setSeconds(0);
      setRecording(true);
      timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch {
      setError("Não foi possível acessar o microfone. Verifique a permissão do navegador.");
    }
  }

  function stop() {
    recorderRef.current?.stop();
    if (timerRef.current) clearInterval(timerRef.current);
    setRecording(false);
  }

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        {recording ? (
          <button type="button" onClick={stop} className={buttonClasses("danger")}>
            <span className="h-2.5 w-2.5 rounded-sm bg-red-600" aria-hidden="true" /> Parar · {mm}:{ss}
          </button>
        ) : (
          <button type="button" onClick={start} className={buttonClasses("secondary")}>
            <MicIcon className="h-4 w-4 text-brand-600" /> {previewUrl ? "Gravar de novo" : "Gravar pelo microfone"}
          </button>
        )}
        {recording && (
          <span className="flex items-center gap-1.5 text-xs text-red-600">
            <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" aria-hidden="true" /> Gravando
          </span>
        )}
      </div>
      {previewUrl && !recording && <audio controls src={previewUrl} className="w-full" />}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function RetryNoteForm({ noteId }: { noteId: number }) {
  const [state, action] = useActionState(retryNoteAction, initial);
  return (
    <form action={action} className="flex flex-col gap-2">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      <input type="hidden" name="note_id" value={noteId} />
      <div><SubmitButton variant="secondary" pendingText="Reprocessando…">Reprocessar</SubmitButton></div>
    </form>
  );
}

/** Recarrega a página a cada 5 s enquanto a IA processa o registro. */
export function AutoRefresh({ seconds = 5 }: { seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    const timer = setInterval(() => router.refresh(), seconds * 1000);
    return () => clearInterval(timer);
  }, [router, seconds]);
  return null;
}

function ListField({ label, name, items }: { label: string; name: string; items: string[] }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={name} className="text-sm font-medium text-gray-700">{label}</label>
      <textarea id={name} name={name} rows={Math.max(3, items.length + 1)} defaultValue={items.join("\n")} className={textareaClass} />
      <p className="text-xs text-gray-500">Um item por linha.</p>
    </div>
  );
}

export function ReviewNoteForm({ note }: { note: NoteDetail }) {
  const [state, action] = useActionState(updateNoteAction, initial);
  const summary = note.summary ?? { resumo: "", topicos: [], pontos_de_acompanhamento: [], trechos_para_revisao: [] };

  return (
    <form action={action} className="flex flex-col gap-4">
      {state.error && <Alert kind="error">{state.error}</Alert>}
      {state.success && <Alert kind="success">{state.success}</Alert>}
      <input type="hidden" name="note_id" value={note.id} />

      <div className="flex flex-col gap-1.5">
        <label htmlFor="resumo" className="text-sm font-medium text-gray-700">Resumo</label>
        <textarea id="resumo" name="resumo" rows={5} defaultValue={summary.resumo} className={textareaClass} />
      </div>
      <ListField label="Tópicos discutidos" name="topicos" items={summary.topicos} />
      <ListField label="Pontos de acompanhamento" name="pontos_de_acompanhamento" items={summary.pontos_de_acompanhamento} />
      <ListField label="Trechos para revisão" name="trechos_para_revisao" items={summary.trechos_para_revisao} />

      <details className="group rounded-lg border border-gray-200">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50">
          Transcrição completa <span className="font-normal text-gray-400">(clique para ver e corrigir)</span>
        </summary>
        <div className="border-t border-gray-200 p-4">
          <textarea id="transcript" name="transcript" rows={12} defaultValue={note.transcript ?? ""} className={textareaClass}
            aria-label="Transcrição" />
        </div>
      </details>

      <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 pt-4">
        <ConfirmSubmit tone="primary" variant="primary" name="intent" value="approve"
          question="Aprovar? Depois o registro não pode mais ser alterado." confirmText="Salvar e aprovar"
          pendingText="Aprovando…">
          Salvar e aprovar
        </ConfirmSubmit>
        <SubmitButton variant="secondary" pendingText="Salvando…">Salvar rascunho</SubmitButton>
      </div>
    </form>
  );
}
