"use client";

import {
  Store,
  GraduationCap,
  Users,
  Warehouse,
  Tractor,
  ExternalLink,
} from "lucide-react";
import type { CanaisComerciais } from "@/lib/api";

/** Ícone por categoria de canal — reforço visual rápido para o produtor. */
const ICONE_CANAL: Record<string, typeof Store> = {
  pnae: GraduationCap,
  paa: Store,
  cooperativas: Users,
  feiras: Tractor,
  cerealistas: Warehouse,
};

/**
 * Lista de canais de escoamento por categoria (PNAE, PAA, cooperativas,
 * feiras, cerealistas). Nunca nome de empresa — só categorias oficiais, com
 * uma etiqueta de "destaque" (ex: paga prêmio) para orientar o produtor.
 */
export function CanaisVenda({ canais }: { canais: CanaisComerciais }) {
  return (
    <section className="rounded-xl2 border border-line bg-surface p-5 shadow-soft">
      <h2 className="font-display text-[1.25rem] font-extrabold text-ink">
        Onde vender em {canais.uf}
      </h2>
      <p className="mt-1 text-[0.9rem] leading-relaxed text-muted">{canais.detalhe}</p>

      <div className="mt-4 space-y-2.5">
        {canais.canais.map((c) => {
          const Icone = ICONE_CANAL[c.id] ?? Store;
          return (
            <div
              key={c.id}
              className="flex gap-3 rounded-xl border border-line bg-canvas/60 p-3.5 transition hover:bg-canvas"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-terra-soft text-terra-ink">
                <Icone size={18} aria-hidden />
              </span>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-bold text-ink">{c.categoria}</p>
                  {c.destaque && (
                    <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[0.68rem] font-bold uppercase tracking-wide text-emerald-800 border border-emerald-200">
                      {c.destaque}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-[0.88rem] leading-relaxed text-muted">{c.descricao}</p>
              </div>
            </div>
          );
        })}
      </div>

      <p className="mt-4 flex flex-wrap items-center gap-1 text-[0.8rem] text-muted">
        <span>Fonte: {canais.fonte.nome}</span>
        {canais.fonte.periodo ? <span>· {canais.fonte.periodo}</span> : null}
        {canais.fonte.url && (
          <a
            href={canais.fonte.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-0.5 font-bold text-terra-ink hover:underline"
          >
            ver programa
            <ExternalLink size={12} aria-hidden />
          </a>
        )}
      </p>
    </section>
  );
}
