"use client";

import { useMemo, useState } from "react";
import {
  MapPin,
  Sprout,
  Layers,
  ShieldCheck,
  Droplets,
  TrendingUp,
  Compass,
  ExternalLink,
} from "lucide-react";
import { EvidenceCard } from "./EvidenceCard";
import type {
  EstadoEvidencia,
  EstadoRegional,
  PrecoRef,
  ResumoRegional,
} from "@/lib/types";
import { formatarPreco } from "@/lib/precos";
import { irrigacaoEmTexto, producaoEmTexto, seguroEmTexto } from "@/lib/texto-cards";

/**
 * Estes blocos são CONTEXTO da região (o que o estado produz, solo, seguro,
 * irrigação, oportunidade) — não um juízo "favorável" sobre a lavoura do
 * produtor. Por isso "disponível" vira "informativo" (azul neutro), nunca verde:
 * ter o dado não quer dizer que ele é bom para quem está vendo.
 */
function mapearEstado(e: EstadoRegional): EstadoEvidencia {
  if (e === "disponivel") return "informativo";
  if (e === "sem_dado") return "sem_dado";
  return "pendente";
}

/** Card de preço compacto, reaproveitado dentro da seção "Vender". */
function BlocoPreco({ preco }: { preco: PrecoRef }) {
  const [aberto, setAberto] = useState(false);
  const ehReferencia = preco.estado === "referencia";
  const semNada = preco.valor == null && !ehReferencia && preco.tipo !== "cepea";
  const rotulo =
    preco.tipo === "pgpm" ? "Piso garantido pelo governo"
    : preco.tipo === "conab_mercado" ? `Sua região${preco.uf ? ` (${preco.uf})` : ""}`
    : "Preço do dia (Cepea)";
  const etiqueta =
    preco.valor != null
      ? formatarPreco(preco.valor, preco.unidade)
      : ehReferencia && preco.referencia_piso != null
        ? `a partir de ${preco.referencia_piso.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}`
        : null;

  return (
    <div className="rounded-xl border border-line bg-canvas p-3">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-ink">{rotulo}</p>
          <p className="text-[0.82rem] text-muted">{preco.cultura} · {preco.unidade}</p>
        </div>
        {preco.tipo === "cepea" ? (
          <a href={preco.url} target="_blank" rel="noreferrer"
            className="inline-flex min-h-[40px] shrink-0 items-center gap-1.5 rounded-full bg-terra-soft px-3 text-[0.82rem] font-bold text-terra-ink">
            Ver preço <ExternalLink size={14} aria-hidden />
          </a>
        ) : etiqueta ? (
          <span className="shrink-0 rounded-full bg-surface px-2.5 py-1 text-[0.8rem] font-extrabold text-ink ring-1 ring-line">
            {etiqueta}
          </span>
        ) : null}
      </div>
      {preco.aviso && <p className="mt-1.5 text-[0.84rem] leading-relaxed text-muted">{preco.aviso}</p>}
      <button onClick={() => setAberto((v) => !v)} aria-expanded={aberto}
        className="mt-1 inline-flex min-h-[36px] items-center text-[0.8rem] font-semibold text-muted hover:text-ink">
        {aberto ? "Ocultar fonte" : "Ver fonte"}
      </button>
      {aberto && (
        <p className="mt-1 text-[0.8rem] leading-relaxed text-muted">
          {preco.fonte.nome}{preco.fonte.limitacoes?.length ? ` · ${preco.fonte.limitacoes.join(" ")}` : ""}
        </p>
      )}
      {semNada && <p className="mt-1 text-[0.8rem] font-semibold text-muted">preço do dia no Cepea ao lado</p>}
    </div>
  );
}

type SecaoId = "producao" | "solo" | "seguro" | "irrigacao" | "vender" | "oportunidade";

const SECOES: { id: SecaoId; rotulo: string; Icone: typeof Sprout }[] = [
  { id: "producao", rotulo: "Produção", Icone: Sprout },
  { id: "solo", rotulo: "Solo", Icone: Layers },
  { id: "seguro", rotulo: "Seguro", Icone: ShieldCheck },
  { id: "irrigacao", rotulo: "Irrigação", Icone: Droplets },
  { id: "vender", rotulo: "Vender", Icone: TrendingUp },
  { id: "oportunidade", rotulo: "Oportunidade", Icone: Compass },
];

/**
 * Painel do lugar selecionado (município ou UF), agrupado num card só.
 *
 * Mobile-first: um cabeçalho fixo com o nome do lugar e uma régua de chips
 * roláveis; o produtor toca num chip e vê só aquela seção (menos rolagem, menos
 * poluição). No desktop os chips continuam funcionando e o card ocupa a coluna
 * lateral. O conteúdo de cada seção reaproveita o EvidenceCard já existente.
 */
export function PainelLocal({
  resumo,
  municipioNome,
  ibge,
  culturaProdutorId,
}: {
  resumo: ResumoRegional;
  municipioNome?: string | null;
  ibge?: string | null;
  culturaProdutorId?: string | null;
}) {
  const { uf, producao, solo, seguro, irrigacao, precos, canais, oportunidade } = resumo;
  const [secao, setSecao] = useState<SecaoId>("producao");

  const prod = useMemo(
    () => producaoEmTexto(producao, uf.nome, culturaProdutorId),
    [producao, uf.nome, culturaProdutorId],
  );
  const seg = useMemo(() => seguroEmTexto(seguro, uf.nome), [seguro, uf.nome]);
  const irr = useMemo(() => irrigacaoEmTexto(irrigacao, uf.nome), [irrigacao, uf.nome]);

  const titulo = municipioNome || uf.nome;
  const subtitulo = municipioNome ? `${uf.nome} · ${uf.sigla}` : `${uf.regiao} · ${uf.sigla}`;

  return (
    <section
      aria-label={`Painel de ${titulo}`}
      className="overflow-hidden rounded-2xl border border-line bg-surface shadow-card animate-fade-up"
    >
      {/* Cabeçalho do lugar */}
      <header className="bg-gradient-to-br from-terra-soft/80 to-surface p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-terra text-white shadow-soft">
            <MapPin size={22} aria-hidden />
          </span>
          <div className="min-w-0">
            <span className="inline-block rounded-full bg-surface/70 px-2 py-0.5 text-[0.68rem] font-bold uppercase tracking-wide text-terra-ink">
              {subtitulo}
            </span>
            <h2 className="mt-0.5 font-display text-[1.4rem] font-extrabold leading-tight text-ink truncate">
              {titulo}
            </h2>
          </div>
        </div>
        <p className="mt-2 text-[0.86rem] leading-relaxed text-muted">
          {municipioNome
            ? "Retrato da região, com dados oficiais para apoiar suas decisões."
            : "Cenário do estado. Toque num município no mapa para aproximar."}
        </p>
      </header>

      {/* Régua de chips (navegação por seção) — rolável no mobile */}
      <nav
        aria-label="Seções"
        className="flex gap-2 overflow-x-auto border-y border-line bg-canvas/50 px-3 py-2.5 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden"
      >
        {SECOES.map(({ id, rotulo, Icone }) => {
          const ativo = secao === id;
          return (
            <button
              key={id}
              onClick={() => setSecao(id)}
              aria-pressed={ativo}
              className={`inline-flex min-h-[40px] shrink-0 items-center gap-1.5 rounded-full px-3.5 text-[0.84rem] font-bold transition ${
                ativo
                  ? "bg-terra text-white shadow-soft"
                  : "bg-surface text-muted ring-1 ring-line hover:text-ink"
              }`}
            >
              <Icone size={15} aria-hidden />
              {rotulo}
            </button>
          );
        })}
      </nav>

      {/* Conteúdo da seção ativa */}
      <div className="space-y-3.5 p-3.5 sm:p-4">
        {secao === "producao" && (
          <EvidenceCard
            evidencia={{
              tipo: "sigef",
              estado: mapearEstado(producao.estado),
              titulo:
                producao.natureza === "sementes"
                  ? "Maior produção de semente na região"
                  : "O que a região mais produz",
              detalhe: prod.detalhe,
              destaques: prod.destaques,
              leitura: prod.leitura,
              fonte: producao.fonte,
            }}
          />
        )}

        {secao === "solo" && (
          <EvidenceCard
            evidencia={{
              tipo: "zarc",
              estado: mapearEstado(solo.estado),
              titulo: "Tipo de solo predominante",
              detalhe: solo.descricao,
              fonte: solo.fonte,
            }}
          />
        )}

        {secao === "seguro" && (
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
        )}

        {secao === "irrigacao" && (
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
        )}

        {secao === "vender" && (
          <div className="space-y-3.5">
            <article className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 shadow-soft">
              <span className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-500 to-terra" aria-hidden />
              <h3 className="font-display text-[1.1rem] font-extrabold text-ink">Para vender melhor</h3>
              <p className="mt-1 text-[0.88rem] text-muted">
                Preço de referência e canais de escoamento, com fonte.
              </p>
              <div className="mt-3 space-y-2.5">
                {precos.map((p) => <BlocoPreco key={p.tipo} preco={p} />)}
              </div>
            </article>

            <div className="space-y-2.5" aria-label="Canais de comercialização">
              <p className="text-[0.86rem] leading-relaxed text-muted">{canais.detalhe}</p>
              {canais.canais.map((c) => (
                <div key={c.id} className="rounded-xl border border-line bg-canvas/60 p-3">
                  <p className="font-bold text-ink">{c.categoria}</p>
                  <p className="mt-0.5 text-[0.86rem] leading-relaxed text-muted">{c.descricao}</p>
                </div>
              ))}
              <div className="flex flex-wrap gap-2 pt-1">
                {canais.programas.map((p) => (
                  <span key={p} className="rounded-full border border-line bg-surface px-3 py-1 text-[0.8rem] font-bold text-terra-ink shadow-soft">
                    ✓ {p}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {secao === "oportunidade" && (
          <EvidenceCard
            evidencia={{
              tipo: "zarc",
              estado: mapearEstado(oportunidade.estado),
              titulo: "Oportunidade regional (ZARC × SIGEF)",
              detalhe: oportunidade.detalhe,
              fonte: oportunidade.fonte,
            }}
          />
        )}
      </div>
    </section>
  );
}
