"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { MapPin, LocateFixed, MessageCircle, TrendingUp } from "lucide-react";
import { AudioButton } from "@/components/AudioButton";
import { MapaBrasil } from "@/components/MapaBrasil";
import { PainelRegional } from "@/components/PainelRegional";
import { usePerfil } from "@/lib/perfil-context";
import { UFS, insightsDaUF, infoDaUF, ufDoPerfil } from "@/lib/mapa-local";
import { precosDaUF, rotuloCultura } from "@/lib/precos";
import { getRegiao } from "@/lib/api";
import type { PrecoRef, ResumoRegional, UFSigla } from "@/lib/types";

/** Resumo consultor comercial: preço + piso + canais, sempre honesto. */
function ConsultorComercial({ uf, culturaId, precos }: { uf: UFSigla; culturaId: string | null; precos: PrecoRef[] }) {
  const info = infoDaUF(uf);
  const cultura = rotuloCultura(culturaId);
  const mercado = precos.find((p) => p.tipo === "conab_mercado");
  const pgpm = precos.find((p) => p.tipo === "pgpm");
  const temNumero = (mercado?.valor ?? pgpm?.valor) != null;
  const texto = temNumero
    ? `Cenário comercial de ${cultura} em ${uf}, com fonte e data abaixo.`
    : `Na sua região (${uf}), ${cultura} ainda está sem cotação disponível (CONAB a conectar). O piso PGPM aparece quando confirmado. Nada aqui é ordem de venda.`;
  return (
    <section aria-label="Consultor comercial" className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 sm:p-5 shadow-card card-hover">
      <span className="absolute left-0 top-0 h-full w-1.5 bg-gradient-to-b from-amber-500 to-terra" aria-hidden />
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-terra-soft px-3 py-1 text-[0.78rem] font-bold uppercase tracking-wide text-terra-ink">
          <TrendingUp size={15} aria-hidden /> Consultor comercial inteligente
        </span>
        <AudioButton texto={texto} />
      </div>
      <p className="mt-2.5 text-[1.05rem] font-medium leading-relaxed text-ink">{texto}</p>
      <div className="mt-2.5 flex flex-wrap items-center gap-2 pt-2 border-t border-line/60 text-[0.8rem] text-muted">
        <span>Fonte: <strong className="text-ink font-semibold">{mercado?.fonte.nome ?? "CONAB"}</strong></span>
        <span>·</span>
        <span>{mercado?.fonte.periodo ?? mercado?.data ?? "aguardando ingestão"}</span>
        <span>·</span>
        <span>Região: <strong className="text-ink font-semibold">{info?.nome} ({uf})</strong></span>
      </div>
    </section>
  );
}

const ESTADOS_VALIDOS = new Set(["disponivel", "pendente", "sem_dado"]);

/** Normaliza o bruto de GET /api/regiao sobre o fallback local honesto. */
function normalizarRegiao(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  bruto: any,
  base: ResumoRegional,
): ResumoRegional {
  if (!bruto || typeof bruto !== "object") return base;
  const b = bruto as Record<string, unknown>;
  const pega = (obj: unknown, fb: object) =>
    obj && typeof obj === "object" ? { ...fb, ...(obj as object) } : fb;
  const comEstado = <T extends { estado: string }>(obj: T, fb: T): T => ({
    ...obj,
    estado: ESTADOS_VALIDOS.has(obj.estado) ? obj.estado : fb.estado,
  });
  const ufInfo =
    b["uf"] && typeof b["uf"] === "object"
      ? { ...base.uf, ...(b["uf"] as object) }
      : base.uf;
  return {
    uf: ufInfo,
    producao: comEstado(
      pega(b["producao"], base.producao) as ResumoRegional["producao"],
      base.producao,
    ),
    solo: comEstado(pega(b["solo"], base.solo) as ResumoRegional["solo"], base.solo),
    seguro: comEstado(
      pega(b["seguro"], base.seguro) as ResumoRegional["seguro"],
      base.seguro,
    ),
    irrigacao: comEstado(
      pega(b["irrigacao"], base.irrigacao) as ResumoRegional["irrigacao"],
      base.irrigacao,
    ),
    precos: Array.isArray(b["precos"]) && (b["precos"] as unknown[]).length > 0
      ? (b["precos"] as ResumoRegional["precos"])
      : base.precos,
    canais: comEstado(
      pega(b["canais"], base.canais) as ResumoRegional["canais"],
      base.canais,
    ),
    oportunidade: comEstado(
      pega(b["oportunidade"], base.oportunidade) as ResumoRegional["oportunidade"],
      base.oportunidade,
    ),
  };
}

/** Aba Mapa: Brasil por UF + card de insights regionais por UF. */
export default function MapaPage() {
  return (
    <Suspense>
      <ConteudoMapa />
    </Suspense>
  );
}

function ConteudoMapa() {
  const params = useSearchParams();
  const ufParam = (params.get("uf") ?? "").toUpperCase();
  const { perfil, carregado } = usePerfil();
  const ufPerfil = ufDoPerfil(perfil.uf);
  const culturaId = perfil.lavouras[0]?.cultura ?? null;

  // Estado inicial sempre neutro (SSR == 1º render cliente). O ?uf= entra via
  // efeito após montar — evita mismatch de hidratação.
  const [uf, setUf] = useState<UFSigla | null>(null);
  useEffect(() => {
    if (ufParam && UFS.some((u) => u.sigla === ufParam)) setUf(ufParam as UFSigla);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const selecionada: UFSigla = uf ?? ufPerfil;
  const [municipio, setMunicipio] = useState<{ ibge: string; nome: string } | null>(null);

  // ibge do mapa ou do perfil (map pick); sem default silencioso além do perfil.
  const ibge = municipio?.ibge || perfil.cod_ibge || undefined;

  const base = useMemo(() => {
    const b = insightsDaUF(selecionada);
    if (!culturaId) return b;
    return { ...b, precos: precosDaUF(selecionada, culturaId) };
  }, [selecionada, culturaId]);

  const [remoto, setRemoto] = useState<ResumoRegional | null>(null);
  useEffect(() => {
    let vivo = true;
    setRemoto(null);
    getRegiao(selecionada, ibge, culturaId)
      .then((bruto) => {
        if (vivo) setRemoto(normalizarRegiao(bruto, base));
      })
      .catch(() => {
        if (vivo) setRemoto(null); // sem backend: fallback local honesto
      });
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selecionada, ibge, culturaId]);

  const resumo = remoto ?? base;

  if (!carregado) return null;

  const intro =
    "Toque num estado para dar zoom e ver os municípios. Toque num município para ver o cenário da região: preço, solo, produção, seguro, irrigação e canais. Tudo com fonte. Nada aqui é ordem de venda.";

  return (
    <div className="space-y-6">
      {/* Cabeçalho do Carro-Chefe */}
      <section className="rounded-2xl border border-line bg-surface/60 p-4 sm:p-6 backdrop-blur shadow-soft">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-terra-soft px-3 py-0.5 text-[0.75rem] font-extrabold uppercase tracking-wide text-terra-ink">
                Inteligência Territorial & Comercial
              </span>
              <span className="hidden sm:inline-block h-1.5 w-1.5 rounded-full bg-terra/40" />
              <span className="hidden sm:inline-block text-[0.8rem] font-semibold text-muted">
                ZARC · SIGEF · PSR · CONAB
              </span>
            </div>
            <h1 className="mt-1.5 font-display text-2xl sm:text-3xl font-extrabold leading-tight text-ink">
              Mapa de Oportunidades Agrícolas
            </h1>
            <p className="mt-2 max-w-3xl text-[0.96rem] leading-relaxed text-muted">{intro}</p>
          </div>
          <div className="shrink-0 pt-1">
            <AudioButton texto={intro} />
          </div>
        </div>
      </section>

      {/* Grid Principal: 2 colunas no Desktop */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Coluna Esquerda: Consultor, Filtro de Estado e Mapa */}
        <div className="lg:col-span-7 xl:col-span-7 space-y-4">
          <ConsultorComercial uf={selecionada} culturaId={culturaId} precos={resumo.precos} />

          <section aria-label="Escolher estado" className="rounded-xl2 border border-line bg-surface p-3.5 shadow-soft space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="seletor-uf" className="text-[0.8rem] font-bold uppercase tracking-wide text-muted">
                Navegar por Estado (UF)
              </label>
              <span className="text-[0.78rem] font-semibold text-terra-ink">
                {UFS.length} estados disponíveis
              </span>
            </div>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <MapPin size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
                <select
                  id="seletor-uf"
                  value={selecionada}
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
              {uf !== null && uf !== ufPerfil ? (
                <button
                  onClick={() => setUf(null)}
                  className="inline-flex min-h-[50px] items-center gap-1.5 rounded-xl border border-line bg-surface px-4 text-[0.88rem] font-bold text-terra-ink shadow-soft transition hover:bg-terra-soft"
                  aria-label="Voltar para o meu estado"
                >
                  <LocateFixed size={17} aria-hidden />
                  <span className="hidden sm:inline">Meu estado</span>
                </button>
              ) : null}
            </div>
          </section>

          <div className="transition-all duration-300">
            <MapaBrasil
              selecionada={selecionada}
              aoSelecionar={(nova) => {
                setUf(nova);
                setMunicipio(null);
              }}
              municipioIbge={municipio?.ibge ?? null}
              aoSelecionarMunicipio={(ibgeSel, nome) => setMunicipio({ ibge: ibgeSel, nome })}
            />
          </div>
        </div>

        {/* Coluna Direita: Informações Regionais e Ações */}
        <div className="lg:col-span-5 xl:col-span-5 space-y-4 lg:sticky lg:top-20">
          {municipio ? (
            <div className="flex items-center gap-3 rounded-xl2 border border-terra/60 bg-terra-soft/80 p-3.5 shadow-soft animate-fade-up" role="status">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-terra text-white shadow-soft">
                <MapPin size={20} />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-display font-extrabold text-ink text-[1.05rem] truncate">
                  {municipio.nome}
                </p>
                <p className="text-[0.8rem] font-semibold text-terra-ink">
                  Código IBGE: {municipio.ibge} · {remoto ? "Dados integrados da região" : "Cenário estadual (UF)"}
                </p>
              </div>
            </div>
          ) : null}

          <div key={selecionada} className="transition-all">
            <PainelRegional resumo={resumo} />
          </div>

          <Link
            href={`/assistente?uf=${selecionada}`}
            className="inline-flex min-h-[54px] w-full items-center justify-center gap-2.5 rounded-xl2 bg-terra px-6 font-bold text-white shadow-card transition hover:brightness-105 active:scale-[0.99]"
          >
            <MessageCircle size={20} aria-hidden />
            <span>Perguntar ao Copiloto sobre esta região</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
