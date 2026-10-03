"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { MapPin, ArrowRight, Loader2 } from "lucide-react";
import { precisaOnboarding, usePerfil } from "@/lib/perfil-context";
import { UFS, ufDoPerfil } from "@/lib/mapa-local";
import { rotuloCultura } from "@/lib/precos";
import { getPrecos, type PrecosResposta } from "@/lib/api";
import type { UFSigla } from "@/lib/types";
import { CardPreco } from "@/components/CardPreco";
import { CanaisVenda } from "@/components/CanaisVenda";
import { AnaliseComercial } from "@/components/AnaliseComercial";
import { TendenciaPrecos } from "@/components/TendenciaPrecos";

/**
 * Aba "Para vender melhor": consultor comercial com dados reais do backend
 * (preço mínimo PGPM/CONAB, mercado por UF, indicador Cepea), canais de
 * escoamento e recomendação de planejamento (IA/heurística). A página só
 * orquestra; o visual vive nos componentes CardPreco/CanaisVenda/AnaliseComercial.
 */
export default function PrecosPage() {
  const router = useRouter();
  const { perfil, carregado } = usePerfil();
  const culturaId = perfil.lavouras[0]?.cultura ?? null;
  const [uf, setUf] = useState<UFSigla>(ufDoPerfil(perfil.uf));
  const [dados, setDados] = useState<PrecosResposta | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState(false);

  const cultura = rotuloCultura(culturaId);

  useEffect(() => {
    if (precisaOnboarding(perfil, carregado)) router.replace("/onboarding");
  }, [perfil, carregado, router]);

  const buscar = useCallback(async () => {
    setCarregando(true);
    setErro(false);
    try {
      setDados(await getPrecos(uf, culturaId));
    } catch {
      setErro(true);
      setDados(null);
    } finally {
      setCarregando(false);
    }
  }, [uf, culturaId]);

  useEffect(() => {
    if (carregado) void buscar();
  }, [carregado, buscar]);

  const precos = dados?.precos ?? [];
  const pgpm = useMemo(() => precos.find((p) => p.tipo === "pgpm"), [precos]);
  const mercado = useMemo(() => precos.find((p) => p.tipo === "conab_mercado"), [precos]);
  const cepea = useMemo(() => precos.find((p) => p.tipo === "cepea"), [precos]);

  if (!carregado) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="rounded-2xl border border-line bg-surface/60 p-4 sm:p-6 backdrop-blur shadow-soft">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-terra-soft px-3 py-0.5 text-[0.75rem] font-extrabold uppercase tracking-wide text-terra-ink">
          Para vender melhor
        </span>
        <h1 className="mt-1.5 font-display text-2xl sm:text-3xl font-extrabold leading-tight text-ink">
          Preço de referência e canais de escoamento
        </h1>
        <p className="mt-2 max-w-2xl text-[0.95rem] leading-relaxed text-muted">
          Contexto de mercado transparente para <strong className="text-ink">{cultura}</strong> em {uf}:
          o piso garantido pelo governo, o indicador do dia e os melhores caminhos de venda.
          É informação para você planejar — a decisão de vender é sempre sua.
        </p>
      </section>

      {/* Seletor de UF */}
      <section aria-label="Escolher estado" className="rounded-xl2 border border-line bg-surface p-4 shadow-soft">
        <label htmlFor="seletor-uf-preco" className="text-[0.8rem] font-bold uppercase tracking-wide text-muted">
          Estado (UF) para consulta
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative sm:max-w-sm sm:flex-1">
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
          <div className="flex items-center gap-2 text-[0.85rem] text-muted">
            <span>Cultura: <strong className="text-ink font-semibold">{cultura}</strong> (do seu cadastro)</span>
            <span className="text-[0.72rem] bg-canvas px-2 py-0.5 rounded border border-line">Oficial MAPA</span>
          </div>
        </div>
      </section>

      {carregando && (
        <div className="flex items-center justify-center gap-2 rounded-xl2 border border-line bg-surface p-8 text-muted shadow-soft">
          <Loader2 size={18} className="animate-spin" aria-hidden />
          <span className="text-[0.9rem] font-semibold">Buscando preços oficiais…</span>
        </div>
      )}

      {erro && !carregando && (
        <div className="rounded-xl2 border border-amber-300 bg-amber-50 p-5 text-amber-900 shadow-soft">
          <p className="font-bold">Não deu para carregar os preços agora.</p>
          <p className="mt-1 text-[0.9rem]">Verifique sua conexão e tente de novo.</p>
          <button
            onClick={() => void buscar()}
            className="mt-3 inline-flex min-h-[44px] items-center rounded-xl bg-amber-600 px-4 font-bold text-white transition hover:brightness-105"
          >
            Tentar de novo
          </button>
        </div>
      )}

      {!carregando && !erro && dados && (
        <>
          {dados.analise && <AnaliseComercial analise={dados.analise} />}

          {dados.tendencia?.estado === "disponivel" && (
            <TendenciaPrecos tendencia={dados.tendencia} />
          )}

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Coluna 1: Preços */}
            <div className="lg:col-span-6 space-y-4">
              {pgpm && <CardPreco preco={pgpm} uf={uf} />}
              {mercado && <CardPreco preco={mercado} uf={uf} />}
              {cepea && <CardPreco preco={cepea} uf={uf} />}
            </div>

            {/* Coluna 2: Canais */}
            <div className="lg:col-span-6 space-y-4">
              {dados.canais && <CanaisVenda canais={dados.canais} />}
              <Link
                href={`/mapa?uf=${uf}`}
                className="inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl2 bg-terra px-6 font-bold text-white shadow-soft transition hover:brightness-105 active:scale-[0.99]"
              >
                <span>Ver mapa territorial completo</span>
                <ArrowRight size={18} aria-hidden />
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
