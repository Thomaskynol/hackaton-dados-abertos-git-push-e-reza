"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { AudioButton } from "./AudioButton";
import { EvidenceCard } from "./EvidenceCard";
import type {
  EstadoEvidencia,
  EstadoRegional,
  PrecoRef,
  ResumoRegional,
} from "@/lib/types";
import { formatarPreco, rotuloCultura } from "@/lib/precos";

function mapearEstado(e: EstadoRegional): EstadoEvidencia {
  if (e === "disponivel") return "favoravel";
  if (e === "sem_dado") return "sem_dado";
  return "pendente";
}

function detalheProducao(p: ResumoRegional["producao"]): string {
  if (p.estado === "disponivel" && (p.culturaTopo || p.areaHa != null || p.producaoT != null)) {
    const partes = [
      p.culturaTopo ?? "cultura principal",
      p.areaHa != null ? `${p.areaHa.toLocaleString("pt-BR")} ha` : null,
      p.producaoT != null ? `${p.producaoT.toLocaleString("pt-BR")} t` : null,
      p.safraRef ? `safra ${p.safraRef}` : null,
    ].filter(Boolean);
    return partes.join(" · ");
  }
  return "Sem dado ainda. Quando o SIGEF ligar, aparece cultura, area e producao da UF.";
}

function detalheSeguro(s: ResumoRegional["seguro"]): string {
  if (s.estado === "disponivel" && (s.apolices != null || s.culturaTopo)) {
    const partes = [
      s.culturaTopo ? `topo: ${s.culturaTopo}` : null,
      s.apolices != null ? `${s.apolices.toLocaleString("pt-BR")} apólices` : null,
      s.valorSegurado != null ? `R$ ${s.valorSegurado.toLocaleString("pt-BR")}` : null,
    ].filter(Boolean);
    return partes.join(" · ") || "Dados do seguro disponíveis — ver fonte.";
  }
  return "Sem dado ainda. Vira do PSR/SISSER (2016-2024): apolices por cultura.";
}

function detalheIrrigacao(i: ResumoRegional["irrigacao"]): string {
  if (i.estado === "disponivel" && i.areaIrrigadaHa != null) {
    return `${i.areaIrrigadaHa.toLocaleString("pt-BR")} ha irrigados.`;
  }
  return "Sem dado ainda. Vira do Atlas Irrigacao (ANA).";
}

function BlocoPreco({ preco }: { preco: PrecoRef }) {
  const [aberto, setAberto] = useState(false);
  const semValor = preco.valor == null;
  const rotulo =
    preco.tipo === "pgpm" ? "Preco minimo (PGPM)"
    : preco.tipo === "conab_mercado" ? `Mercado (CONAB)${preco.uf ? ` - ${preco.uf}` : ""}`
    : "Indicador diario (Cepea/ESALQ)";
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
        <p className="mt-1 text-[0.82rem] font-semibold text-muted">sem cotacao disponivel</p>
      ) : null}
    </div>
  );
}

export function PainelRegional({ resumo }: { resumo: ResumoRegional }) {
  const { uf, producao, solo, seguro, irrigacao, precos, canais, oportunidade } = resumo;
  const voz = `${uf.nome}. Producao, seguro, irrigacao, preco e canais ainda pendentes. Nada aqui e recomendacao de venda.`;
  return (
    <section aria-label={`Painel regional de ${uf.nome}`} className="space-y-3 animate-fade-up">
      <div className="flex items-start justify-between gap-3 rounded-xl2 border border-line bg-surface p-4 shadow-card">
        <div>
          <p className="text-[0.8rem] font-bold uppercase tracking-wide text-muted">{uf.regiao} - {uf.sigla}</p>
          <h2 className="font-display text-[1.4rem] font-extrabold text-ink">{uf.nome}</h2>
          <p className="text-[0.92rem] text-muted">Cenario da regiao. O sistema mostra — nao decide por voce.</p>
        </div>
        <AudioButton texto={voz} />
      </div>
      <EvidenceCard evidencia={{ tipo: "sigef", estado: mapearEstado(producao.estado), titulo: "O que a regiao mais produz", detalhe: detalheProducao(producao), fonte: producao.fonte }} />
      <EvidenceCard evidencia={{ tipo: "zarc", estado: mapearEstado(solo.estado), titulo: "Tipo de solo predominante", detalhe: solo.descricao, fonte: solo.fonte }} />
      <EvidenceCard evidencia={{ tipo: "psr", estado: mapearEstado(seguro.estado), titulo: "Forca da cultura no seguro", detalhe: detalheSeguro(seguro), fonte: seguro.fonte }} />
      <EvidenceCard evidencia={{ tipo: "ana", estado: mapearEstado(irrigacao.estado), titulo: "Irrigacao disponivel", detalhe: detalheIrrigacao(irrigacao), fonte: irrigacao.fonte }} />
      <article className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 shadow-soft">
        <span className="absolute left-0 top-0 h-full w-1.5 bg-terra" aria-hidden />
        <h3 className="font-display text-[1.1rem] font-extrabold text-ink">Para vender melhor</h3>
        <p className="mt-1 text-[0.92rem] text-muted">Preço de referência + canais — contexto, nao e recomendacao de venda.</p>
        <div className="mt-3 space-y-2">
          {precos.map((p) => <BlocoPreco key={p.tipo} preco={p} />)}
        </div>
      </article>
      <EvidenceCard evidencia={{ tipo: "zarc", estado: mapearEstado(canais.estado), titulo: "Canais de comercializacao", detalhe: canais.detalhe, fonte: canais.fonte }} />
      <div className="space-y-2" aria-label="Categorias de canal">
        {canais.canais.map((c) => (
          <div key={c.id} className="rounded-xl border border-line bg-surface p-3 shadow-soft">
            <p className="font-bold text-ink">{c.categoria}</p>
            <p className="text-[0.9rem] text-muted">{c.descricao}</p>
          </div>
        ))}
      </div>
      <p className="rounded-xl border border-line bg-canvas p-3 text-[0.85rem] text-muted">
        Nomes de compradores especificos dependem de base futura — aqui mostramos so categorias reais, sem empresa fabricada.
      </p>
      <div className="flex flex-wrap gap-2" aria-label="Programas">
        {canais.programas.map((p) => (
          <span key={p} className="rounded-full border border-line bg-surface px-3 py-1.5 text-[0.85rem] font-semibold text-muted">{p}</span>
        ))}
      </div>
      <EvidenceCard evidencia={{ tipo: "zarc", estado: mapearEstado(oportunidade.estado), titulo: "Oportunidade regional (ZARC x SIGEF)", detalhe: oportunidade.detalhe, fonte: oportunidade.fonte }} />
      <div className="flex items-center gap-2">
        <AudioButton texto={oportunidade.detalhe} />
      </div>
    </section>
  );
}
