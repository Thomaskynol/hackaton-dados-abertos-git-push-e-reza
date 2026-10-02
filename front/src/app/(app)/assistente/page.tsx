"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ChatBubble } from "@/components/ChatBubble";
import { ChatInput } from "@/components/ChatInput";
import { Chip } from "@/components/Chip";
import { usePerfil, primeiroNome } from "@/lib/perfil-context";
import { SUGESTOES_CHAT, responderLocal } from "@/lib/dados-locais";
import { infoDaUF } from "@/lib/mapa-local";
import type { Mensagem } from "@/lib/types";

/**
 * Assistente: apoio para interpretar o Mapa e os preços. Voz, texto e chips.
 * A resposta vem do resolvedor LOCAL (sem backend), sempre honesto sobre isso.
 */
export default function Assistente() {
  return (
    <Suspense>
      <ConteudoAssistente />
    </Suspense>
  );
}

function ConteudoAssistente() {
  const params = useSearchParams();
  const ufCtx = (params.get("uf") ?? "").toUpperCase();
  const { perfil, carregado } = usePerfil();
  const pn = primeiroNome(perfil.nome);
  const [msgs, setMsgs] = useState<Mensagem[]>([]);
  const [pensando, setPensando] = useState(false);
  const fimRef = useRef<HTMLDivElement>(null);

  // mensagem inicial do copiloto (com contexto da UF vinda do Mapa, se houver)
  useEffect(() => {
    if (!carregado) return;
    const info = infoDaUF(ufCtx);
    setMsgs([
      {
        id: "boas-vindas",
        autor: "copiloto",
        texto: info
          ? `Oi, ${pn}! Vi que você estava olhando ${info.nome} (${info.sigla}) no Mapa. Posso ajudar a interpretar o cenário comercial de lá — preço, piso e canais. O que quer entender?`
          : `Oi, ${pn}! Sou o apoio do Mapa: ajudo a interpretar preço, piso e canais da sua região. Toque numa sugestão abaixo ou mande a sua dúvida.`,
        fonte: "AgroPilot",
        horario: agora(),
      },
    ]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [carregado]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [msgs.length, pensando]);

  function enviar(texto: string) {
    const minha: Mensagem = {
      id: `u-${Date.now()}`,
      autor: "usuario",
      texto,
      horario: agora(),
    };
    setMsgs((m) => [...m, minha]);
    setPensando(true);

    // simula o tempo de resposta; aqui entraria o POST /api/chat
    setTimeout(() => {
      const r = responderLocal(texto, pn);
      setMsgs((m) => [...m, { ...r, id: `c-${Date.now()}`, horario: agora() }]);
      setPensando(false);
    }, 450);
  }

  function enviarAudio() {
    // o áudio foi captado; a transcrição real virá do backend.
    const aviso: Mensagem = {
      id: `u-audio-${Date.now()}`,
      autor: "usuario",
      texto: "🎙️ Áudio enviado",
      horario: agora(),
    };
    const resposta: Mensagem = {
      id: `c-audio-${Date.now()}`,
      autor: "copiloto",
      texto: `Recebi seu áudio, ${pn}. A transcrição da sua fala vai ser feita no servidor na próxima etapa. Por enquanto, pode tocar numa sugestão ou escrever sua pergunta.`,
      fonte: "AgroPilot",
      horario: agora(),
    };
    setMsgs((m) => [...m, aviso, resposta]);
  }

  if (!carregado) return null;

  return (
    <div className="flex min-h-[calc(100vh-10rem)] flex-col">
      <div className="flex-1 space-y-3">
        {msgs.map((m) => (
          <ChatBubble key={m.id} msg={m} />
        ))}
        {pensando && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1.5 rounded-xl2 rounded-bl-md border border-line bg-surface px-4 py-3 shadow-soft">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-2 w-2 animate-wave rounded-full bg-terra"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          </div>
        )}
        <div ref={fimRef} />
      </div>

      {/* sugestões + input fixos acima da bottom-nav */}
      <div className="sticky bottom-20 mt-4 space-y-3">
        <div className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4">
          {SUGESTOES_CHAT.map((s) => (
            <Chip key={s.texto} emoji={s.emoji} onClick={() => enviar(s.texto)}>
              {s.texto}
            </Chip>
          ))}
        </div>
        <ChatInput onEnviar={enviar} onAudio={enviarAudio} />
      </div>
    </div>
  );
}

function agora() {
  const d = new Date();
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}
