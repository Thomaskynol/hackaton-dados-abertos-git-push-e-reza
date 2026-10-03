"use client";

import { TrendingUp, TrendingDown, Minus, LineChart, Sparkles } from "lucide-react";
import type { TendenciaPreco } from "@/lib/api";

function brl(v: number) {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

/**
 * Card de tendência e projeção de preço, a partir da série histórica real do
 * IBGE (preço médio recebido pelo produtor por ano). Mostra para onde o preço
 * vem indo e uma estimativa para o próximo ano — sempre com faixa e o aviso de
 * que é apoio ao planejamento, não garantia. Linguagem do produtor.
 */
export function TendenciaPrecos({ tendencia }: { tendencia: TendenciaPreco }) {
  if (!tendencia || tendencia.estado !== "disponivel" || !tendencia.ultimo) return null;

  const { direcao, ultimo, media_recente, projecao, serie } = tendencia;
  const Icone = direcao === "subindo" ? TrendingUp : direcao === "caindo" ? TrendingDown : Minus;
  const cor =
    direcao === "subindo" ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : direcao === "caindo" ? "text-red-700 bg-red-50 border-red-200"
    : "text-muted bg-canvas border-line";
  const frase =
    direcao === "subindo" ? "vem subindo nos últimos anos"
    : direcao === "caindo" ? "vem caindo nos últimos anos"
    : "tem se mantido estável";

  // mini-gráfico de barras com os últimos pontos da série
  const ult = (serie ?? []).slice(-8);
  const max = Math.max(...ult.map((p) => p.valor), 1);

  return (
    <section
      aria-label="Tendência de preço"
      className="rounded-2xl border border-line bg-surface p-5 sm:p-6 shadow-card"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-terra-soft text-terra-ink">
            <LineChart size={18} aria-hidden />
          </span>
          <div>
            <h2 className="font-display text-[1.15rem] font-extrabold text-ink">Para onde o preço vem indo</h2>
            <p className="text-[0.78rem] text-muted">Preço médio recebido pelo produtor · IBGE</p>
          </div>
        </div>
        <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[0.78rem] font-bold ${cor}`}>
          <Icone size={14} aria-hidden />
          {direcao}
        </span>
      </div>

      <p className="mt-3 text-[0.98rem] leading-relaxed text-ink">
        Na sua região, o preço do {tendencia.cultura?.toLowerCase()} {frase}. No dado mais recente
        ({ultimo.ano}), ficou perto de <strong>{brl(ultimo.valor)}</strong> a saca
        {media_recente ? <> (média dos últimos anos: {brl(media_recente)}).</> : "."}
      </p>

      {ult.length >= 3 && (
        <div className="mt-4 flex items-end gap-1.5" aria-hidden>
          {ult.map((p) => (
            <div key={p.ano} className="flex flex-1 flex-col items-center gap-1">
              <div
                className="w-full rounded-t bg-terra/70"
                style={{ height: `${Math.max(6, (p.valor / max) * 64)}px` }}
                title={`${p.ano}: ${brl(p.valor)}`}
              />
              <span className="text-[0.6rem] text-muted">{String(p.ano).slice(2)}</span>
            </div>
          ))}
        </div>
      )}

      {projecao && (
        <div className="mt-4 rounded-xl border border-dashed border-terra/40 bg-terra-soft/40 p-3.5">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[0.82rem] font-bold uppercase tracking-wide text-terra-ink">
              Estimativa para {projecao.ano}
            </p>
            {projecao.origem === "ia" && (
              <span className="inline-flex items-center gap-1 rounded-full bg-terra px-2 py-0.5 text-[0.68rem] font-bold text-white">
                <Sparkles size={11} aria-hidden /> por IA
              </span>
            )}
          </div>
          <p className="mt-1 text-[1.05rem] font-extrabold text-ink">
            cerca de {brl(projecao.valor_estimado)}
            <span className="ml-1 text-[0.82rem] font-semibold text-muted">
              (entre {brl(projecao.faixa_min)} e {brl(projecao.faixa_max)})
            </span>
          </p>
          {projecao.racional && (
            <p className="mt-1.5 text-[0.86rem] leading-relaxed text-ink">{projecao.racional}</p>
          )}
          <p className="mt-1 text-[0.8rem] leading-relaxed text-muted">
            {tendencia.aviso}
          </p>
        </div>
      )}
    </section>
  );
}
