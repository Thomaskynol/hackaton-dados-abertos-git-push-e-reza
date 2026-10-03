"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { EvidenceCard } from "./EvidenceCard";
import type {
  EstadoEvidencia,
  EstadoRegional,
  PrecoRef,
  ResumoRegional,
} from "@/lib/types";
import { formatarPreco } from "@/lib/precos";
import { irrigacaoEmTexto, producaoEmTexto, seguroEmTexto } from "@/lib/texto-cards";

function mapearEstado(e: EstadoRegional): EstadoEvidencia {
  if (e === "disponivel") return "favoravel";
  if (e === "sem_dado") return "sem_dado";
  return "pendente";
}

function BlocoPreco({ preco }: { preco: PrecoRef }) {
  const [aberto, setAberto] = useState(false);
  const semValor = preco.valor == null;
  const rotulo =
    preco.tipo === "pgpm" ? "Preço mínimo (PGPM)"
    : preco.tipo === "conab_mercado" ? `Mercado (CONAB)${preco.uf ? ` - ${preco.uf}` : ""}`
    : "Indicador diário (Cepea/ESALQ)";
  return (
    <div className="rounded-xl border border-line bg-canvas p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-bold text-ink">{rotulo}</p>
          <p className="text-[0.85rem] text-muted">{preco.cultura} - {preco.unidade}</p>
        </div>
        {preco.tipo === "cepea" ? (
          <a href={preco.url} target="_blank" rel="noreferrer"
            className="inline-flex min-h-[44px] items-center gap-1.5 rounded-full bg-terra-soft px-3 text-[0.85rem] font-bold text-terra-ink">
            Ver indicador <ExternalLink size={15} aria-hidden />
          </a>
        ) : (
          <span className="shrink-0 rounded-full bg-canvas px-2.5 py-1 text-[0.78rem] font-bold text-muted ring-1 ring-line">
            {formatarPreco(preco.valor, preco.unidade)}
          </span>
        )}
      </div>
      {preco.aviso && <p className="mt-1 text-[0.85rem] text-muted">{preco.aviso}</p>}
      <div className="mt-1 flex items-center gap-2">
        <button onClick={() => setAberto((v) => !v)} aria-expanded={aberto}
          className="inline-flex min-h-[40px] items-center rounded-full px-2 text-[0.85rem] font-semibold text-muted hover:text-ink">
          Ver fonte
        </button>
        <span className="text-[0.78rem] text-muted">{preco.fonte.nome}</span>
      </div>
      {aberto && preco.fonte.limitacoes?.length ? (
        <p className="mt-1 text-[0.82rem] text-muted">Limites: {preco.fonte.limitacoes.join(" ")}</p>
      ) : null}
      {semValor && preco.tipo !== "cepea" ? (
        <p className="mt-1 text-[0.82rem] font-semibold text-muted">sem cotação disponível</p>
      ) : null}
    </div>
  );
}

export function PainelRegional({ resumo }: { resumo: ResumoRegional }) {
  const { uf, producao, solo, seguro, irrigacao, precos, canais, oportunidade } = resumo;

  // Os três blocos abaixo saem humanizados (frase + fichas) em vez de "campo · campo".
  const prod = producaoEmTexto(producao, uf.nome);
  const seg = seguroEmTexto(seguro, uf.nome);
  const irr = irrigacaoEmTexto(irrigacao, uf.nome);

  return (
    <section aria-label={`Painel regional de ${uf.nome}`} className="space-y-3.5 animate-fade-up">
      <div className="flex items-start justify-between gap-3 rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-card card-hover">
        <div>
          <span className="inline-block rounded-full bg-terra-soft px-2.5 py-0.5 text-[0.75rem] font-bold uppercase tracking-wide text-terra-ink">
            {uf.regiao} · {uf.sigla}
          </span>
          <h2 className="mt-1 font-display text-[1.45rem] font-extrabold text-ink">{uf.nome}</h2>
          <p className="mt-0.5 text-[0.92rem] text-muted">Cenário regional consolidado. Informações para apoiar suas decisões.</p>
        </div>
      </div>

      <EvidenceCard
        evidencia={{
          tipo: "sigef",
          estado: mapearEstado(producao.estado),
          titulo: "O que a região mais produz",
          detalhe: prod.detalhe,
          destaques: prod.destaques,
          leitura: prod.leitura,
          fonte: producao.fonte,
        }}
      />
      <EvidenceCard evidencia={{ tipo: "zarc", estado: mapearEstado(solo.estado), titulo: "Tipo de solo predominante", detalhe: solo.descricao, fonte: solo.fonte }} />
      <EvidenceCard
        evidencia={{
          tipo: "psr",
          estado: mapearEstado(seguro.estado),
          titulo: "Força da cultura no seguro agrícola",
          detalhe: seg.detalhe,
          destaques: seg.destaques,
          leitura: seg.leitura,
          fonte: seguro.fonte,
        }}
      />
      <EvidenceCard
        evidencia={{
          tipo: "ana",
          estado: mapearEstado(irrigacao.estado),
          titulo: "Irrigação disponível",
          detalhe: irr.detalhe,
          destaques: irr.destaques,
          leitura: irr.leitura,
          fonte: irrigacao.fonte,
        }}
      />
      <article className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-soft card-hover">
        <span className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-500 to-terra" aria-hidden />
        <h3 className="font-display text-[1.15rem] font-extrabold text-ink">Para vender melhor</h3>
        <p className="mt-1 text-[0.92rem] text-muted">Preço de referência e canais de escoamento. Contexto mercadológico transparente.</p>
        <div className="mt-3.5 space-y-2.5">
          {precos.map((p) => <BlocoPreco key={p.tipo} preco={p} />)}
        </div>
      </article>
      <EvidenceCard evidencia={{ tipo: "zarc", estado: mapearEstado(canais.estado), titulo: "Canais de comercialização", detalhe: canais.detalhe, fonte: canais.fonte }} />
      <div className="space-y-2.5" aria-label="Categorias de canal">
        {canais.canais.map((c) => (
          <div key={c.id} className="rounded-xl border border-line bg-surface p-3.5 shadow-soft card-hover">
            <p className="font-bold text-ink">{c.categoria}</p>
            <p className="mt-0.5 text-[0.9rem] text-muted">{c.descricao}</p>
          </div>
        ))}
      </div>
      <p className="rounded-xl border border-line bg-canvas/70 p-3 text-[0.84rem] text-muted leading-relaxed">
        ℹ️ Compradores específicos e parceiros locais são validados continuamente pelas cooperativas e fontes oficiais.
      </p>
      <div className="flex flex-wrap gap-2" aria-label="Programas governamentais">
        {canais.programas.map((p) => (
          <span key={p} className="rounded-full border border-line bg-surface px-3 py-1 text-[0.82rem] font-bold text-terra-ink shadow-soft hover:bg-terra-soft transition">
            ✓ {p}
          </span>
        ))}
      </div>
      <EvidenceCard evidencia={{ tipo: "zarc", estado: mapearEstado(oportunidade.estado), titulo: "Oportunidade regional (ZARC x SIGEF)", detalhe: oportunidade.detalhe, fonte: oportunidade.fonte }} />
    </section>
  );
}
