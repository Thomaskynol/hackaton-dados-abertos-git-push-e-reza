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
    <section aria-label="Consultor comercial" className="relative overflow-hidden rounded-xl2 border border-line bg-surface p-4 shadow-card">
      <span className="absolute left-0 top-0 h-full w-1.5 bg-terra" aria-hidden />
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-terra-soft px-3 py-1 text-[0.78rem] font-bold uppercase tracking-wide text-terra-ink">
          <TrendingUp size={15} aria-hidden /> Consultor comercial
        </span>
        <AudioButton texto={texto} />
      </div>
      <p className="mt-2 text-[1.02rem] text-ink">{texto}</p>
      <p className="mt-1 text-[0.82rem] text-muted">
        Fonte: {mercado?.fonte.nome ?? "CONAB"} · {mercado?.fonte.periodo ?? mercado?.data ?? "aguardando ingestão"} · Região: {info?.nome} ({uf})
      </p>
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
    <div className="space-y-4">
      <section>
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[0.8rem] font-bold uppercase tracking-wide text-terra-ink">
              Carro-chefe · consultor comercial
            </p>
            <h1 className="font-display text-[1.6rem] font-extrabold leading-tight text-ink">
              Mapa de oportunidade
            </h1>
          </div>
          <AudioButton texto={intro} />
        </div>
        <p className="mt-1 text-muted">{intro}</p>
      </section>

      <ConsultorComercial uf={selecionada} culturaId={culturaId} precos={resumo.precos} />

      <section aria-label="Escolher estado" className="space-y-2">
        <label htmlFor="seletor-uf" className="text-[0.82rem] font-bold uppercase tracking-wide text-muted">
          Estado (UF)
        </label>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <MapPin size={18} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
            <select
              id="seletor-uf"
              value={selecionada}
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
          {uf !== null && uf !== ufPerfil ? (
            <button
              onClick={() => setUf(null)}
              className="inline-flex min-h-[52px] items-center gap-1.5 rounded-xl2 border border-line bg-surface px-3 text-[0.9rem] font-bold text-terra-ink"
              aria-label="Voltar para o meu estado"
            >
              <LocateFixed size={18} aria-hidden />
              Meu estado
            </button>
          ) : null}
        </div>
      </section>

      <MapaBrasil
        selecionada={selecionada}
        aoSelecionar={(nova) => {
          setUf(nova);
          setMunicipio(null);
        }}
        municipioIbge={municipio?.ibge ?? null}
        aoSelecionarMunicipio={(ibgeSel, nome) => setMunicipio({ ibge: ibgeSel, nome })}
      />

      {municipio ? (
        <p className="rounded-xl2 border border-terra bg-terra-soft px-4 py-3 text-[0.95rem] font-bold text-terra-ink" role="status">
          {municipio.nome} · IBGE {municipio.ibge} — cenário abaixo{remoto ? " (dados da região)" : " (cenário da UF, município ainda sem camada própria)"}.
        </p>
      ) : null}

      <div key={selecionada}>
        <PainelRegional resumo={resumo} />
      </div>

      <Link
        href={`/assistente?uf=${selecionada}`}
        className="inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 border border-line bg-surface px-5 font-bold text-terra-ink shadow-soft transition hover:border-terra"
      >
        <MessageCircle size={20} aria-hidden /> Perguntar sobre esta região
      </Link>
    </div>
  );
}
