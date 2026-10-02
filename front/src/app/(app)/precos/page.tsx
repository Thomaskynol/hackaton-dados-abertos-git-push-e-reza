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
    <div className="space-y-4">
      <section>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[0.8rem] font-bold uppercase tracking-wide text-terra-ink">
              Consultor comercial
            </p>
            <h1 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
              Preços por região
            </h1>
          </div>
          <AudioButton texto={intro} />
        </div>
        <p className="mt-1 text-muted">{intro}</p>
      </section>

      <section aria-label="Escolher estado e cultura" className="space-y-2">
        <label htmlFor="seletor-uf-preco" className="text-[0.82rem] font-bold uppercase tracking-wide text-muted">
          Estado (UF)
        </label>
        <div className="relative">
          <MapPin size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
          <select
            id="seletor-uf-preco"
            value={uf}
            onChange={(e) => setUf(e.target.value as UFSigla)}
            className="min-h-[52px] w-full appearance-none rounded-xl2 border border-line bg-surface pl-10 pr-4 text-[1.05rem] font-semibold text-ink"
          >
            {UFS.map((u) => (
              <option key={u.sigla} value={u.sigla}>
                {u.nome} ({u.sigla})
              </option>
            ))}
          </select>
        </div>
        <p className="text-[0.85rem] text-muted">Cultura: {cultura} (do seu cadastro).</p>
      </section>

      <section aria-label="Preço de mercado" className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 shadow-card">
        <span className="absolute left-0 top-0 h-full w-1.5 bg-terra" aria-hidden />
        <div className="flex items-center gap-2">
          <TrendingUp size={18} className="text-terra-ink" aria-hidden />
          <h2 className="font-display text-[1.1rem] font-extrabold text-ink">
            Mercado em {uf}: {formatarPreco(mercado.valor, mercado.unidade)}
          </h2>
        </div>
        <p className="mt-1 text-[0.9rem] text-muted">
          {cultura} · fonte {mercado.fonte.nome} · {mercado.fonte.periodo}. Referência e contexto — não é ordem de venda.
        </p>
      </section>

      <section className="space-y-2">
        <article className="rounded-xl2 border border-line bg-surface p-4 shadow-soft">
          <h3 className="font-bold text-ink">Piso garantido (PGPM)</h3>
          <p className="mt-1 text-[1.05rem] font-extrabold text-ink">{formatarPreco(pgpm.valor, pgpm.unidade)}</p>
          <p className="text-[0.85rem] text-muted">
            Fonte: {pgpm.fonte.nome} · {pgpm.fonte.periodo}. Compare com o mercado acima.
          </p>
        </article>
        <article className="flex items-center justify-between gap-3 rounded-xl2 border border-line bg-surface p-4 shadow-soft">
          <div>
            <h3 className="font-bold text-ink">Indicador diário (Cepea/ESALQ)</h3>
            <p className="text-[0.85rem] text-muted">{cepea.aviso}</p>
          </div>
          <a
            href={cepea.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex min-h-[44px] shrink-0 items-center gap-1.5 rounded-full bg-terra-soft px-3 text-[0.85rem] font-bold text-terra-ink"
          >
            Ver indicador <ExternalLink size={15} aria-hidden />
          </a>
        </article>
      </section>

      <section className="rounded-xl2 border border-line bg-surface p-4 shadow-soft">
        <h2 className="font-display text-[1.1rem] font-extrabold text-ink">Onde vender em {uf}</h2>
        <p className="mt-1 text-[0.9rem] text-muted">{canais.detalhe}</p>
        <div className="mt-3 space-y-2">
          {canais.canais.map((c) => (
            <div key={c.id} className="rounded-xl border border-line bg-canvas p-3">
              <p className="font-bold text-ink">{c.categoria}</p>
              <p className="text-[0.9rem] text-muted">{c.descricao}</p>
            </div>
          ))}
        </div>
        <p className="mt-2 text-[0.82rem] text-muted">
          Fonte: {canais.fonte.nome} · {canais.fonte.periodo}. Categorias reais — nenhum nome de empresa sem fonte.
        </p>
      </section>

      <Link
        href={`/mapa?uf=${uf}`}
        className="inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-5 font-bold text-white shadow-soft transition hover:brightness-95"
      >
        Ver cenário completo no Mapa <ArrowRight size={20} aria-hidden />
      </Link>
    </div>
  );
}
