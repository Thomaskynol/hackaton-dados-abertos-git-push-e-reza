"use client";

import { Sparkles } from "lucide-react";
import type { AnaliseComercial as TAnalise } from "@/lib/api";

/**
 * Bloco de destaque com a orientação de venda do consultor. O texto vem do
 * backend: gerado por IA quando há chave LLM, ou montado dos dados oficiais
 * (heurística) caso contrário. Nunca manda "vender agora" — só ajuda a planejar.
 */
export function AnaliseComercial({ analise }: { analise: TAnalise }) {
  if (!analise?.texto) return null;
  const porIA = analise.origem === "ia";
  return (
    <section
      aria-label="Orientação do consultor comercial"
      className="relative overflow-hidden rounded-2xl border border-terra/30 bg-gradient-to-br from-terra-soft/70 to-surface p-5 sm:p-6 shadow-card"
    >
      <div className="flex items-center gap-2">
        <span className="grid h-9 w-9 place-items-center rounded-xl bg-terra text-white shadow-soft">
          <Sparkles size={18} aria-hidden />
        </span>
        <div>
          <p className="text-[0.78rem] font-bold uppercase tracking-wide text-terra-ink">
            Consultor AgroPilot
          </p>
          <p className="text-[0.72rem] text-muted">
            {porIA ? "Análise gerada por IA sobre os dados oficiais" : "Leitura dos dados oficiais"}
          </p>
        </div>
      </div>
      <p className="mt-3 whitespace-pre-line text-[1.02rem] leading-relaxed text-ink">
        {analise.texto}
      </p>
      {analise.fonte && (
        <p className="mt-3 text-[0.78rem] font-semibold text-muted">{analise.fonte}</p>
      )}
    </section>
  );
}
