"use client";

import { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  MinusCircle,
  ChevronDown,
  FileText,
  Lightbulb,
  Info,
} from "lucide-react";
import type { Evidencia, EstadoEvidencia } from "@/lib/types";

/**
 * Os 4 estados honestos (documento mestre §6.2) → cor, ícone, rótulo
 * e UMA frase explicando o que aquele estado quer dizer para o produtor.
 */
const META: Record<
  EstadoEvidencia,
  {
    cor: string;
    faixa: string;
    chip: string;
    Icone: typeof CheckCircle2;
    rotulo: string;
    oQueSignifica: string;
  }
> = {
  favoravel: {
    cor: "text-favoravel",
    faixa: "bg-favoravel",
    chip: "bg-favoravel/12",
    Icone: CheckCircle2,
    rotulo: "Favorável",
    oQueSignifica: "o dado sustenta o que está escrito",
  },
  atencao: {
    cor: "text-atencao",
    faixa: "bg-atencao",
    chip: "bg-atencao/20",
    Icone: AlertTriangle,
    rotulo: "Atenção",
    oQueSignifica: "a fonte tem uma ressalva",
  },
  pendente: {
    cor: "text-terra-ink",
    faixa: "bg-terra",
    chip: "bg-terra-soft",
    Icone: HelpCircle,
    rotulo: "Falta um dado",
    oQueSignifica: "precisa de mais uma informação para concluir",
  },
  sem_dado: {
    cor: "text-pendente",
    faixa: "bg-pendente",
    chip: "bg-pendente/12",
    Icone: MinusCircle,
    rotulo: "Sem dado ainda",
    oQueSignifica: "a base oficial ainda não ligou",
  },
  informativo: {
    cor: "text-sky-700",
    faixa: "bg-sky-500",
    chip: "bg-sky-100",
    Icone: Info,
    rotulo: "Contexto da região",
    oQueSignifica: "dado para você comparar, não uma avaliação da sua lavoura",
  },
};

export function EvidenceCard({ evidencia }: { evidencia: Evidencia }) {
  const [aberto, setAberto] = useState(false);
  const m = META[evidencia.estado];
  const { Icone } = m;
  const { fonte, destaques, leitura } = evidencia;

  return (
    <article className="relative overflow-hidden rounded-xl2 border border-line bg-surface shadow-soft card-hover transition-all">
      <span className={`absolute left-0 top-0 h-full w-1.5 ${m.faixa}`} aria-hidden />
      <div className="p-4 pl-5">
        {/* estado + significado, em pílula com fundo suave da própria cor */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[0.76rem] font-bold ${m.chip} ${m.cor}`}
          >
            <Icone size={14} aria-hidden />
            {m.rotulo}
          </span>
          <span className="text-[0.78rem] italic text-muted">— {m.oQueSignifica}</span>
        </div>

        <h3 className="mt-2 font-display text-[1.12rem] font-extrabold leading-snug text-ink">
          {evidencia.titulo}
        </h3>

        {/* frase humanizada, já em português corrido */}
        <p className="mt-1 text-[1rem] leading-relaxed text-ink/85">{evidencia.detalhe}</p>

        {/* fichas: número compacto + legenda em palavra simples */}
        {destaques && destaques.length > 0 ? (
          <dl className="mt-3 grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(destaques.length, 3)}, minmax(0, 1fr))` }}>
            {destaques.map((d) => (
              <div
                key={d.rotulo}
                className="rounded-xl border border-line bg-canvas px-2.5 py-2 text-center"
              >
                <dt className="text-[0.68rem] font-bold uppercase tracking-wide text-muted">
                  {d.rotulo}
                </dt>
                <dd className="font-display text-[1.02rem] font-extrabold leading-tight text-ink">
                  {d.valor}
                </dd>
                {d.dica ? (
                  <dd className="mt-0.5 text-[0.7rem] leading-tight text-muted">{d.dica}</dd>
                ) : null}
              </div>
            ))}
          </dl>
        ) : null}

        {/* "o que isso significa" — uma linha, com ícone */}
        {leitura ? (
          <p className="mt-3 flex gap-2 rounded-xl bg-terra-soft/60 px-3 py-2 text-[0.88rem] leading-snug text-terra-ink">
            <Lightbulb size={16} className="mt-0.5 shrink-0" aria-hidden />
            <span>{leitura}</span>
          </p>
        ) : null}

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
