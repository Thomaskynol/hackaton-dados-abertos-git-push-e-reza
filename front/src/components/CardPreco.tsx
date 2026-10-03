"use client";

import { ShieldCheck, TrendingUp, ExternalLink } from "lucide-react";
import { formatarPreco } from "@/lib/precos";
import type { PrecoRef } from "@/lib/types";

/**
 * Um card de preço de referência. Três variações pelo campo `tipo`:
 *  - pgpm: piso garantido (número herói quando disponível)
 *  - conab_mercado: contexto de mercado por UF (ainda sem número diário)
 *  - cepea: só link para o indicador do dia (nunca número embutido)
 *
 * Nunca inventa valor: quando `valor` é null, formatarPreco mostra
 * "sem cotação disponível" e o selo fica em "Aguardando".
 */
export function CardPreco({ preco, uf }: { preco: PrecoRef; uf: string }) {
  // Card do Cepea: o número do dia é do Cepea (não copiamos por licença),
  // MAS mostramos aqui o que é possível — o histórico real do IBGE e para
  // onde ir buscar o valor de hoje. Antes era um card quase vazio.
  if (preco.tipo === "cepea") {
    const ref = preco.referencia_ibge ?? null;
    const serie = preco.serie_ibge ?? [];
    const max = Math.max(...serie.map((s) => s.valor), 1);
    return (
      <article className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-soft card-hover">
        <span className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-500 to-terra" aria-hidden />
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div>
            <span className="text-[0.72rem] font-bold uppercase tracking-wider text-muted">
              Indicador diário
            </span>
            <h3 className="font-display text-base font-extrabold text-ink">
              Preço de hoje — {preco.cultura}
            </h3>
            <p className="mt-0.5 text-[0.84rem] text-muted">
              Atualizado todo dia pelo Cepea/ESALQ.
            </p>
          </div>
          <a
            href={preco.url ?? preco.fonte?.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-full bg-terra-soft px-4 text-[0.86rem] font-bold text-terra-ink transition hover:bg-terra hover:text-white"
          >
            Ver preço de hoje
            <ExternalLink size={15} aria-hidden />
          </a>
        </div>

        {preco.aviso && (
          <p className="mt-3 rounded-lg bg-canvas/70 p-3 text-[0.86rem] leading-relaxed text-ink">
            {preco.aviso}
          </p>
        )}

        {ref && (
          <div className="mt-3 rounded-lg border border-line bg-canvas/50 p-3">
            <p className="text-[0.7rem] font-bold uppercase tracking-wide text-muted">
              Histórico que já está no sistema (IBGE)
            </p>
            <p className="mt-1 font-display text-xl font-extrabold text-ink">
              {ref.valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
              <span className="ml-1 text-[0.85rem] font-semibold text-muted">
                /{preco.unidade}
              </span>
            </p>
            <p className="text-[0.8rem] text-muted">
              {ref.ano} · preço médio anual recebido pelo produtor em {uf}
            </p>
            {serie.length > 1 && (
              <div className="mt-2.5 flex flex-wrap items-end gap-1.5" aria-hidden>
                {serie.map((s) => {
                  const h = Math.max(8, Math.round((s.valor / max) * 38));
                  return (
                    <span key={s.ano} className="flex flex-col items-center gap-0.5">
                      <span className="w-4 rounded-sm bg-terra/45" style={{ height: `${h}px` }} />
                      <span className="text-[0.62rem] text-muted">
                        {String(s.ano).slice(2)}
                      </span>
                    </span>
                  );
                })}
              </div>
            )}
            <p className="mt-2 text-[0.76rem] leading-snug text-muted">
              Média anual do produtor (IBGE PAM) — não é cotação diária. Serve para ver a
              tendência dos últimos anos, não para fechar venda hoje.
            </p>
          </div>
        )}
      </article>
    );
  }

  const ehPgpm = preco.tipo === "pgpm";
  const ehReferencia = preco.estado === "referencia";
  const disponivel = preco.estado === "disponivel" && preco.valor != null;

  // Card de contexto de mercado: sem cotação do dia, mas com um piso de
  // referência real e uma explicação humana (nunca "sem cotação disponível").
  if (!ehPgpm && ehReferencia) {
    const piso = preco.referencia_piso ?? null;
    const pisoFmt =
      piso != null
        ? `${piso.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} · ${preco.unidade}`
        : null;
    return (
      <section
        aria-label={`Contexto de mercado em ${uf}`}
        className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-5 shadow-soft card-hover"
      >
        <span className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-500 to-terra" aria-hidden />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-terra-soft text-terra-ink">
              <TrendingUp size={18} aria-hidden />
            </span>
            <span className="text-[0.82rem] font-bold uppercase tracking-wide text-terra-ink">
              Sua região ({uf})
            </span>
          </div>
          <span className="rounded-full bg-amber-50 text-amber-800 border border-amber-200 px-2.5 py-0.5 text-xs font-bold">
            Referência
          </span>
        </div>
        {pisoFmt && (
          <p className="mt-3 font-display text-2xl font-extrabold text-ink">
            a partir de {pisoFmt}
          </p>
        )}
        <p className="mt-2 text-[0.9rem] leading-relaxed text-ink">{preco.aviso}</p>
        {preco.fonte?.url && (
          <a
            href={preco.fonte.url}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-flex items-center gap-1 text-[0.82rem] font-bold text-terra-ink hover:underline"
          >
            Fonte: {preco.fonte.nome}
            <ExternalLink size={13} aria-hidden />
          </a>
        )}
      </section>
    );
  }

  return (
    <section
      aria-label={ehPgpm ? "Preço mínimo garantido" : `Mercado em ${uf}`}
      className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-5 shadow-card card-hover"
    >
      <span
        className={`absolute left-0 top-0 h-full w-1.5 ${
          ehPgpm ? "bg-gradient-to-b from-emerald-500 to-terra" : "bg-gradient-to-b from-amber-500 to-terra"
        }`}
        aria-hidden
      />
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`grid h-8 w-8 place-items-center rounded-lg ${
              ehPgpm ? "bg-emerald-50 text-emerald-700" : "bg-terra-soft text-terra-ink"
            }`}
          >
            {ehPgpm ? <ShieldCheck size={18} aria-hidden /> : <TrendingUp size={18} aria-hidden />}
          </span>
          <span className="text-[0.82rem] font-bold uppercase tracking-wide text-terra-ink">
            {ehPgpm ? "Piso garantido (PGPM)" : `Mercado em ${uf}`}
          </span>
        </div>
        <span
          className={`rounded-full px-2.5 py-0.5 text-xs font-bold border ${
            disponivel
              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
              : "bg-canvas text-muted border-line"
          }`}
        >
          {disponivel ? "Oficial" : "Aguardando"}
        </span>
      </div>

      <p className={`mt-3 font-display font-extrabold ${disponivel ? "text-4xl text-ink" : "text-2xl text-muted"}`}>
        {formatarPreco(preco.valor, preco.unidade)}
      </p>
      <p className="mt-1 text-[0.88rem] text-muted">
        {preco.cultura}
        {preco.fonte?.periodo ? ` · ${preco.fonte.periodo}` : ""}
      </p>

      {preco.aviso && (
        <p className="mt-3 rounded-lg bg-canvas/70 p-3 text-[0.86rem] leading-relaxed text-ink">
          {preco.aviso}
        </p>
      )}

      {preco.fonte?.url && (
        <a
          href={preco.fonte.url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-[0.82rem] font-bold text-terra-ink hover:underline"
        >
          Fonte: {preco.fonte.nome}
          <ExternalLink size={13} aria-hidden />
        </a>
      )}
    </section>
  );
}
