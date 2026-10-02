"use client";

import { Volume2, Square } from "lucide-react";
import { useFala } from "@/lib/audio";

/** Botão "ouvir": lê o texto em voz alta. Acessibilidade para quem prefere áudio. */
export function AudioButton({ texto, rotulo = "Ouvir" }: { texto: string; rotulo?: string }) {
  const { falar, parar, falando, suportado } = useFala();
  if (!suportado) return null;

  return (
    <button
      onClick={() => (falando ? parar() : falar(texto))}
      aria-label={falando ? "Parar leitura" : `${rotulo} em voz alta`}
      className="inline-flex min-h-[40px] items-center gap-2 rounded-full bg-terra-soft px-3 text-[0.9rem] font-semibold text-terra-ink transition hover:brightness-95"
    >
      {falando ? (
        <Square size={16} className="fill-current" />
      ) : (
        <Volume2 size={18} />
      )}
      <span>{falando ? "Parar" : rotulo}</span>
    </button>
  );
}
