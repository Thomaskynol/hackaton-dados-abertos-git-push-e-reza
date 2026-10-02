"use client";

import { useState } from "react";
import { Send, Mic, Square } from "lucide-react";
import { useGravacao } from "@/lib/audio";

/**
 * Entrada do chat: texto + microfone.
 * A gravação captura o áudio no aparelho; a TRANSCRIÇÃO real virá do backend.
 * Por ora, ao terminar de gravar, sinalizamos que o áudio foi captado.
 */
export function ChatInput({
  onEnviar,
  onAudio,
}: {
  onEnviar: (texto: string) => void;
  onAudio: () => void;
}) {
  const [texto, setTexto] = useState("");
  const { estado, iniciar, parar, suportado } = useGravacao(() => onAudio());
  const gravando = estado === "gravando";

  function enviar(e: React.FormEvent) {
    e.preventDefault();
    const t = texto.trim();
    if (!t) return;
    onEnviar(t);
    setTexto("");
  }

  return (
    <form
      onSubmit={enviar}
      className="flex items-center gap-2 rounded-full border border-line bg-surface p-2 pl-4 shadow-card focus-within:border-terra"
    >
      <input
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        placeholder={gravando ? "Gravando… pode falar" : "Fale ou escreva…"}
        aria-label="Escreva sua pergunta"
        className="min-h-[44px] w-full bg-transparent text-[1.05rem] text-ink outline-none placeholder:text-muted"
      />

      {texto.trim() ? (
        <button
          type="submit"
          aria-label="Enviar pergunta"
          className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-terra text-white transition hover:brightness-95"
        >
          <Send size={20} />
        </button>
      ) : suportado ? (
        <button
          type="button"
          onClick={() => (gravando ? parar() : iniciar())}
          aria-label={gravando ? "Parar gravação" : "Gravar áudio"}
          className={`grid h-12 w-12 shrink-0 place-items-center rounded-full text-white transition ${
            gravando ? "animate-pulse-dot bg-risco" : "bg-terra hover:brightness-95"
          }`}
        >
          {gravando ? <Square size={18} className="fill-current" /> : <Mic size={20} />}
        </button>
      ) : (
        <button
          type="submit"
          aria-label="Enviar pergunta"
          disabled
          className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-line text-muted"
        >
          <Send size={20} />
        </button>
      )}
    </form>
  );
}
