"use client";

import { useState } from "react";
import { CheckCircle2, AlertTriangle, HelpCircle, MinusCircle, ChevronDown, FileText } from "lucide-react";
import type { Evidencia, EstadoEvidencia } from "@/lib/types";

/** Mapeia os 4 estados honestos para cor, ícone e rótulo em linguagem simples. */
const META: Record<
  EstadoEvidencia,
  { cor: string; faixa: string; Icone: typeof CheckCircle2; rotulo: string }
> = {
  favoravel: { cor: "text-favoravel", faixa: "bg-favoravel", Icone: CheckCircle2, rotulo: "Favorável" },
  atencao: { cor: "text-atencao", faixa: "bg-atencao", Icone: AlertTriangle, rotulo: "Atenção" },
  pendente: { cor: "text-terra-ink", faixa: "bg-terra", Icone: HelpCircle, rotulo: "Falta um dado" },
  sem_dado: { cor: "text-pendente", faixa: "bg-pendente", Icone: MinusCircle, rotulo: "Sem dado ainda" },
};

export function EvidenceCard({ evidencia }: { evidencia: Evidencia }) {
  const [aberto, setAberto] = useState(false);
  const m = META[evidencia.estado];
  const { Icone, fonte } = { Icone: m.Icone, fonte: evidencia.fonte };

  return (
    <article className="relative overflow-hidden rounded-xl2 border border-line bg-surface shadow-soft">
      <span className={`absolute left-0 top-0 h-full w-1.5 ${m.faixa}`} aria-hidden />
      <div className="p-4 pl-5">
        <div className="flex items-center gap-2">
          <Icone size={20} className={m.cor} aria-hidden />
          <span className={`text-[0.8rem] font-bold uppercase tracking-wide ${m.cor}`}>
            {m.rotulo}
          </span>
        </div>

        <h3 className="mt-1.5 font-display text-[1.1rem] font-extrabold text-ink">
          {evidencia.titulo}
        </h3>
        <p className="mt-1 text-[0.98rem] text-muted">{evidencia.detalhe}</p>

        <button
          onClick={() => setAberto((v) => !v)}
          aria-expanded={aberto}
          className="mt-3 inline-flex min-h-[40px] items-center gap-1.5 rounded-full bg-canvas px-3 text-[0.85rem] font-semibold text-muted transition hover:text-ink"
        >
          <FileText size={15} aria-hidden />
          Ver fonte
          <ChevronDown
            size={15}
            className={`transition-transform ${aberto ? "rotate-180" : ""}`}
            aria-hidden
          />
        </button>

        {aberto && (
          <dl className="mt-3 space-y-1.5 rounded-xl border border-line bg-canvas p-3 text-[0.88rem] animate-fade-up">
            <div className="flex gap-2">
              <dt className="shrink-0 font-semibold text-muted">Fonte:</dt>
              <dd className="text-ink">{fonte.nome}</dd>
            </div>
            {fonte.periodo && (
              <div className="flex gap-2">
                <dt className="shrink-0 font-semibold text-muted">Período:</dt>
                <dd className="text-ink">{fonte.periodo}</dd>
              </div>
            )}
            {fonte.limitacoes?.length ? (
              <div className="flex gap-2">
                <dt className="shrink-0 font-semibold text-muted">Limites:</dt>
                <dd className="text-ink">{fonte.limitacoes.join(" ")}</dd>
              </div>
            ) : null}
          </dl>
        )}
      </div>
    </article>
  );
}
