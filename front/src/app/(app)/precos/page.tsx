"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { MapPin, TrendingUp, ExternalLink, ArrowRight } from "lucide-react";
import { AudioButton } from "@/components/AudioButton";
import { usePerfil } from "@/lib/perfil-context";
import { UFS, canaisDaUF, ufDoPerfil } from "@/lib/mapa-local";
import { formatarPreco, precosDaUF, rotuloCultura } from "@/lib/precos";
import type { UFSigla } from "@/lib/types";

/** Aba Preços: consultor comercial em lista — preço + piso + canais por UF. */
export default function PrecosPage() {
  const { perfil, carregado } = usePerfil();
  const ufPerfil = ufDoPerfil(perfil.uf);
  const culturaId = perfil.lavouras[0]?.cultura ?? null;
  const [uf, setUf] = useState<UFSigla>(ufPerfil);

  const precos = useMemo(() => precosDaUF(uf, culturaId), [uf, culturaId]);
  const canais = useMemo(() => canaisDaUF(uf), [uf]);
  const cultura = rotuloCultura(culturaId);

  if (!carregado) return null;

  const intro = `Preços de referência de ${cultura} em ${uf}. Mercado CONAB por UF, piso PGPM e indicador Cepea. Contexto para planejar — não é recomendação de venda.`;
  const [mercado, pgpm, cepea] = precos;

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="rounded-2xl border border-line bg-surface/60 p-4 sm:p-6 backdrop-blur shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-terra-soft px-3 py-0.5 text-[0.75rem] font-extrabold uppercase tracking-wide text-terra-ink">
              Consultor Comercial & Cotações
            </span>
            <h1 className="mt-1.5 font-display text-2xl sm:text-3xl font-extrabold leading-tight text-ink">
              Preços de Referência por Região
            </h1>
            <p className="mt-2 max-w-2xl text-[0.95rem] leading-relaxed text-muted">{intro}</p>
          </div>
          <div className="shrink-0 pt-1">
            <AudioButton texto={intro} />
          </div>
        </div>
      </section>

      {/* Grid Principal */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Coluna 1: Filtro e Preços */}
        <div className="lg:col-span-6 space-y-4">
          <section aria-label="Escolher estado e cultura" className="rounded-xl2 border border-line bg-surface p-4 shadow-soft space-y-2">
            <label htmlFor="seletor-uf-preco" className="text-[0.8rem] font-bold uppercase tracking-wide text-muted">
              Estado (UF) para consulta
            </label>
            <div className="relative">
              <MapPin size={18} className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
              <select
                id="seletor-uf-preco"
                value={uf}
                onChange={(e) => setUf(e.target.value as UFSigla)}
                className="min-h-[50px] w-full appearance-none rounded-xl border border-line bg-canvas pl-10 pr-4 text-[1rem] font-semibold text-ink transition focus:border-terra outline-none"
              >
                {UFS.map((u) => (
                  <option key={u.sigla} value={u.sigla}>
                    {u.nome} ({u.sigla})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between text-[0.85rem] text-muted pt-1">
              <span>Cultura: <strong className="text-ink font-semibold">{cultura}</strong> (do seu cadastro)</span>
              <span className="text-[0.75rem] bg-canvas px-2 py-0.5 rounded border border-line">Oficial MAPA</span>
            </div>
          </section>

          {/* Card Preço de Mercado */}
          <section aria-label="Preço de mercado" className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-5 shadow-card card-hover">
            <span className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-500 to-terra" aria-hidden />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="grid h-8 w-8 place-items-center rounded-lg bg-terra-soft text-terra-ink">
                  <TrendingUp size={18} aria-hidden />
                </span>
                <span className="text-[0.82rem] font-bold uppercase tracking-wide text-terra-ink">
                  Mercado em {uf}
                </span>
              </div>
              <span className="rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 px-2.5 py-0.5 text-xs font-bold">
                Ativo
              </span>
            </div>
            <div className="mt-3">
              <p className="font-display text-3xl font-extrabold text-ink">
                {formatarPreco(mercado.valor, mercado.unidade)}
              </p>
              <p className="mt-1 text-[0.88rem] text-muted">
                {cultura} · Fonte <strong className="text-ink font-semibold">{mercado.fonte.nome}</strong> · {mercado.fonte.periodo}
              </p>
            </div>
          </section>

          {/* Piso PGPM e CEPEA */}
          <div className="space-y-3">
            <article className="rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-soft card-hover">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[0.75rem] font-bold uppercase tracking-wider text-muted">Política Pública</span>
                  <h3 className="font-bold text-ink text-base">Piso Garantido (PGPM)</h3>
                </div>
                <span className="rounded-full bg-canvas px-3 py-1 text-[0.95rem] font-extrabold text-ink border border-line">
                  {formatarPreco(pgpm.valor, pgpm.unidade)}
                </span>
              </div>
              <p className="mt-2 text-[0.84rem] text-muted leading-relaxed">
                Fonte: {pgpm.fonte.nome} · {pgpm.fonte.periodo}. Valor mínimo garantido pelo governo para cobrir custos operacionais.
              </p>
            </article>

            <article className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-soft card-hover">
              <div>
                <span className="text-[0.75rem] font-bold uppercase tracking-wider text-muted">Bolsa / Indicador Diário</span>
                <h3 className="font-bold text-ink text-base">Cepea / ESALQ</h3>
                <p className="mt-0.5 text-[0.84rem] text-muted">{cepea.aviso}</p>
              </div>
              <a
                href={cepea.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-1.5 rounded-xl bg-terra-soft px-4 text-[0.88rem] font-bold text-terra-ink transition hover:bg-terra hover:text-white"
              >
                <span>Acessar Cepea</span>
                <ExternalLink size={15} aria-hidden />
              </a>
            </article>
          </div>
        </div>

        {/* Coluna 2: Onde Vender e Canais */}
        <div className="lg:col-span-6 space-y-4">
          <section className="rounded-xl2 border border-line bg-surface p-5 shadow-soft card-hover">
            <h2 className="font-display text-[1.25rem] font-extrabold text-ink">
              Onde comercializar em {uf}
            </h2>
            <p className="mt-1 text-[0.9rem] text-muted leading-relaxed">{canais.detalhe}</p>

            <div className="mt-4 space-y-2.5">
              {canais.canais.map((c) => (
                <div key={c.id} className="rounded-xl border border-line bg-canvas/60 p-3.5 transition hover:bg-canvas">
                  <p className="font-bold text-ink">{c.categoria}</p>
                  <p className="mt-0.5 text-[0.88rem] text-muted">{c.descricao}</p>
                </div>
              ))}
            </div>

            <p className="mt-3 text-[0.8rem] text-muted">
              Fonte oficial: {canais.fonte.nome} · {canais.fonte.periodo}. Categorias regulamentadas.
            </p>
          </section>

          <Link
            href={`/mapa?uf=${uf}`}
            className="inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-6 font-bold text-white shadow-soft transition hover:brightness-105 active:scale-[0.99]"
          >
            <span>Ver mapa territorial completo</span>
            <ArrowRight size={18} aria-hidden />
          </Link>
        </div>
      </div>
    </div>
  );
}
