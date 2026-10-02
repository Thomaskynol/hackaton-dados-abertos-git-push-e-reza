"use client";

import { AudioButton } from "./AudioButton";
import { EvidenceCard } from "./EvidenceCard";
import type { Mensagem } from "@/lib/types";

/** Bolha de conversa. Resposta do copiloto traz "ouvir", fonte e evidências. */
export function ChatBubble({ msg }: { msg: Mensagem }) {
  const doUsuario = msg.autor === "usuario";

  if (doUsuario) {
    return (
      <div className="flex justify-end animate-fade-up">
        <div className="max-w-[84%] rounded-xl2 rounded-br-md bg-terra px-4 py-3 text-white shadow-soft">
          <p className="whitespace-pre-wrap text-[1rem]">{msg.texto}</p>
          <p className="mt-1 text-right text-[0.7rem] text-white/70">{msg.horario}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start animate-fade-up">
      <div className="max-w-[88%] rounded-xl2 rounded-bl-md border border-line bg-surface px-4 py-3 shadow-soft">
        <p className="whitespace-pre-wrap text-[1rem] text-ink">{msg.texto}</p>

        <div className="mt-2.5 flex flex-wrap items-center gap-2">
          <AudioButton texto={msg.texto} rotulo="Ouvir resposta" />
          {msg.fonte && (
            <span className="rounded-full bg-canvas px-2.5 py-1 text-[0.78rem] font-semibold text-muted">
              Fonte: {msg.fonte}
            </span>
          )}
        </div>

        {msg.evidencias?.length ? (
          <div className="mt-3 space-y-2.5">
            {msg.evidencias.map((e, i) => (
              <EvidenceCard key={`${e.tipo}-${i}`} evidencia={e} />
            ))}
          </div>
        ) : null}

        <p className="mt-1.5 text-[0.7rem] text-muted">{msg.horario}</p>
      </div>
    </div>
  );
}
