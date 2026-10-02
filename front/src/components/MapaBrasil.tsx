"use client";

import { memo, useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent, PointerEvent as ReactPointerEvent } from "react";
import { ZoomIn, ZoomOut, Maximize, ArrowLeft, Loader2, Search, MapPin } from "lucide-react";
import { UFS, infoDaUF } from "@/lib/mapa-local";
import { CONTORNOS_UF } from "@/lib/brasil-uf";
import type { MalhaMunicipios } from "@/lib/geo-tipos";
import type { UFSigla } from "@/lib/types";

/* Projetor lon/lat -> plano local do SVG (equiretangular ajustado p/ Brasil). */
const LON_MIN = -74.5;
const LON_MAX = -34.5;
const LAT_MIN = -34.0;
const LAT_MAX = 6.0;
const W = 400;
const H = 430;
/* Zoom máximo alto: o nome do município só aparece no hover/selecionado, então
   é preciso aproximar bastante para inspecionar área por área. */
const ZOOM_MAX = 8;

type Nivel = { tipo: "brasil" } | { tipo: "uf"; uf: UFSigla; munIbge: string | null };

function proj(lng: number, lat: number): [number, number] {
  const x = ((lng - LON_MIN) / (LON_MAX - LON_MIN)) * W;
  const y = ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * H;
  return [x, y];
}

function anelParaPath(anel: readonly (readonly number[])[]): string {
  return anel.map(([lng, lat], i) => `${i === 0 ? "M" : "L"}${proj(lng, lat)[0].toFixed(1)},${proj(lng, lat)[1].toFixed(1)}`).join(" ") + "Z";
}

/* ViewBox que enquadra uma UF com margem (zoom-in automático no drill-down). */
function bboxDaUF(sigla: string): [number, number, number, number] {
  const aneis = CONTORNOS_UF[sigla] as [number, number][][];
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const a of aneis) {
    for (const [lng, lat] of a) {
      const [x, y] = proj(lng, lat);
      if (x < x0) x0 = x;
      if (y < y0) y0 = y;
      if (x > x1) x1 = x;
      if (y > y1) y1 = y;
    }
  }
  const m = 14;
  return [x0 - m, y0 - m, x1 - x0 + m * 2, y1 - y0 + m * 2];
}


/* Centroide de polígono (fórmula do sapateiro, ponderado pela área).
   pts em coordenadas JÁ projetadas; null se degenerado. */
function centroideDePts(pts: readonly (readonly number[])[]): [number, number] | null {
  const n = pts.length;
  if (n < 3) return null;
  let a2 = 0;
  let cx = 0;
  let cy = 0;
  for (let i = 0; i < n; i++) {
    const [x1, y1] = pts[i];
    const [x2, y2] = pts[(i + 1) % n];
    const cr = x1 * y2 - x2 * y1;
    a2 += cr;
    cx += (x1 + x2) * cr;
    cy += (y1 + y2) * cr;
  }
  if (Math.abs(a2) < 1e-9) return null;
  return [cx / (3 * a2), cy / (3 * a2)];
}

/* Ponto dentro do polígono (ray casting) — evita rótulo fora do estado. */
function dentroDoAnel(pt: [number, number], anel: readonly (readonly number[])[]): boolean {
  const [x, y] = pt;
  let dentro = false;
  for (let i = 0, j = anel.length - 1; i < anel.length; j = i++) {
    const [xi, yi] = anel[i];
    const [xj, yj] = anel[j];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}

/* Centroide do maior anel ponderado pela área — centro visual real do estado
   (o centro da bbox caía "fora da forma" em estados irregulares). Se cair
   fora do polígono, volta ao centro da bbox. */
function centroide(sigla: string): [number, number] {
  const aneis = CONTORNOS_UF[sigla] as [number, number][][];
  let maior = aneis[0];
  for (const a of aneis) if (a.length > maior.length) maior = a;
  const pts = maior.map(([lng, lat]) => proj(lng, lat));
  // Contenção testada em coords. PROJETADAS — antes misturava lng/lat com x/y,
  // o teste era lixo e caía sempre no fallback do centro da bbox.
  const c = centroideDePts(pts);
  if (c && dentroDoAnel(c, pts)) return c;
  let x0 = Infinity;
  let y0 = Infinity;
  let x1 = -Infinity;
  let y1 = -Infinity;
  for (const [x, y] of pts) {
    if (x < x0) x0 = x;
    if (y < y0) y0 = y;
    if (x > x1) x1 = x;
    if (y > y1) y1 = y;
  }
  return [(x0 + x1) / 2, (y0 + y1) / 2];
}

/* Estimativa de área projetada (p/ esconder rótulo de município minúsculo). */
function areaAnel(anel: readonly (readonly number[])[]): number {
  let s = 0;
  for (let i = 0; i < anel.length; i++) {
    const [x1, y1] = proj(anel[i][0], anel[i][1]);
    const [x2, y2] = proj(anel[(i + 1) % anel.length][0], anel[(i + 1) % anel.length][1]);
    s += x1 * y2 - x2 * y1;
  }
  return Math.abs(s / 2);
}

/* Deslocamentos finos p/ micro-UFs do Nordeste/Sudeste (evita sobreposição). */
const AJUSTE_ROTULO: Partial<Record<string, [number, number]>> = {
  DF: [16, 4],
  SE: [14, 6],
  AL: [13, -6],
  PB: [10, -8],
  RN: [9, -9],
  PE: [0, 13],
  ES: [14, 2],
  RJ: [13, 7],
  SC: [-8, 9],
  AP: [0, -8],
  CE: [5, -9],
  MS: [0, 2],
};

/* Transform do grupo pan/zoom (usado no render e na escrita direta no DOM). */
function transformDe(px: number, py: number, z: number): string {
  return `translate(${W / 2 + px} ${(H + 14) / 2 + py}) scale(${z}) translate(${-W / 2} ${-(H + 14) / 2})`;
}

/* Lê o data-ibge do path atingido (delegação de eventos na camada). */
function ibgeDe(alvo: EventTarget | null): string | null {
  return (alvo as Element | null)?.closest?.("[data-ibge]")?.getAttribute("data-ibge") ?? null;
}

/* Município = só a FORMA (path). O NOME nunca é escrito dentro do polígono —
   texto SVG não quebra linha nem elide, então nome longo estourava o estado e
   invadia os vizinhos (o "feio/quebrado"). Como mapa de verdade (Google Maps),
   o nome aparece só no hover (tooltip) e no selecionado — e o detalhe vai para
   os cards do painel. Fica o <title> nativo para acessibilidade/mouse. */
const MunicipioG = memo(function MunicipioG({
  ibge, d, nome, ativo, emHover, destaque,
}: {
  ibge: string;
  d: string;
  nome: string;
  ativo: boolean;
  emHover: boolean;
  destaque: boolean;
}) {
  // Realce de FORMA (mais fácil de ler que texto minúsculo): hover acende a
  // cor e engrossa o contorno, dando mira clara antes de tocar/clicar.
  const fill = ativo
    ? "rgb(var(--c-terra))"
    : emHover
      ? "rgb(var(--c-terra) / 0.45)"
      : destaque
        ? "rgb(var(--c-terra-soft))"
        : "#FEFCF8";
  return (
    <path
      d={d}
      data-ibge={ibge}
      role="button"
      tabIndex={-1}
      aria-label={`${nome} — toque para ver detalhes`}
      aria-pressed={ativo}
      className="cursor-pointer outline-none transition-[fill] duration-100"
      style={{
        fill,
        stroke: ativo || emHover ? "rgb(var(--c-terra-ink))" : "#B5986B",
        strokeWidth: ativo ? 1.6 : emHover ? 1.1 : 0.55,
        strokeLinejoin: "round",
      }}
    >
      <title>{nome}</title>
    </path>
  );
});

interface Props {
  selecionada: UFSigla;
  aoSelecionar: (uf: UFSigla) => void;
  culturaId?: string | null;
  municipioIbge?: string | null;
  aoSelecionarMunicipio?: (ibge: string, nome: string) => void;
}

export function MapaBrasil({ selecionada, aoSelecionar, municipioIbge, aoSelecionarMunicipio }: Props) {
  const tituloId = useId();
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [nivel, setNivel] = useState<Nivel>({ tipo: "brasil" });
  const [malha, setMalha] = useState<MalhaMunicipios | null>(null);
  const [carregandoMun, setCarregandoMun] = useState(false);
  const [erroMun, setErroMun] = useState(false);
  const [busca, setBusca] = useState("");
  const [hoverMun, setHoverMun] = useState<string | null>(null);
  const arrasto = useRef<{ x: number; y: number; px: number; py: number } | null>(null);
  const panRef = useRef({ x: 0, y: 0 }); // fonte da verdade durante o arraste
  const gRef = useRef<SVGGElement>(null);
  const arrastouRef = useRef(false); // suprime clique pós-arraste
  const zoomRef = useRef(1); // espelho do zoom p/ uso dentro de handlers de gesto
  // Pinça (2 dedos no celular): guarda os ponteiros ativos e a distância inicial.
  const ponteiros = useRef(new Map<number, { x: number; y: number }>());
  const pinca = useRef<{ dist: number; zoom: number } | null>(null);

  const emUF = nivel.tipo === "uf" ? nivel.uf : null;

  // zoomRef acompanha o zoom para os handlers de gesto (pinça/wheel) lerem o
  // valor atual sem recriar os callbacks.
  useEffect(() => {
    zoomRef.current = zoom;
  }, [zoom]);

  /* Pan: o estado React é só espelho do panRef. Durante o arraste gravamos o
     transform direto no DOM (zero re-render dos 600+ nós) e sincronizamos o
     estado no pointerup (um re-render por gesto). */
  const moverPan = useCallback(
    (x: number, y: number) => {
      panRef.current = { x, y };
      setPan({ x, y });
      gRef.current?.setAttribute("transform", transformDe(x, y, zoom));
    },
    [zoom],
  );

  const abrirUF = useCallback((uf: UFSigla) => {
    aoSelecionar(uf);
    setNivel({ tipo: "uf", uf, munIbge: nivel.tipo === "uf" && nivel.uf === uf ? nivel.munIbge : null });
    setZoom(1);
    moverPan(0, 0);
    setBusca("");
    setHoverMun(null);
  }, [aoSelecionar, nivel, moverPan]);

  /* Carrega a malha de municípios da UF sob demanda (arquivo estático local). */
  useEffect(() => {
    if (nivel.tipo !== "uf") {
      setMalha(null);
      setErroMun(false);
      return;
    }
    let vivo = true;
    setCarregandoMun(true);
    setErroMun(false);
    fetch(`/geo/municipios/${nivel.uf}.geo.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<MalhaMunicipios>;
      })
      .then((m) => {
        if (vivo) {
          setMalha(m);
          setCarregandoMun(false);
        }
      })
      .catch(() => {
        if (vivo) {
          setMalha(null);
          setErroMun(true);
          setCarregandoMun(false);
        }
      });
    return () => {
      vivo = false;
    };
  }, [nivel]);

  const aproximar = useCallback(() => setZoom((z) => Math.min(ZOOM_MAX, +(z + (z < 3 ? 0.5 : 1)).toFixed(2))), []);
  const afastar = useCallback(() => setZoom((z) => Math.max(1, +(z - (z <= 3 ? 0.5 : 1)).toFixed(2))), []);
  const recentrar = useCallback(() => {
    setZoom(1);
    moverPan(0, 0);
  }, [moverPan]);

  const paths = useMemo(() => {
    const m = new Map<string, string>();
    for (const u of UFS) {
      const aneis = CONTORNOS_UF[u.sigla] as [number, number][][];
      m.set(u.sigla, aneis.map(anelParaPath).join(" "));
    }
    return m;
  }, []);

  const pathsMun = useMemo(() => {
    if (!malha) return new Map<string, string>();
    const m = new Map<string, string>();
    for (const mun of malha.municipios) {
      m.set(mun.ibge, mun.aneis.map(anelParaPath).join(" "));
    }
    return m;
  }, [malha]);

  const voltarBrasil = useCallback(() => {
    setNivel({ tipo: "brasil" });
    setZoom(1);
    moverPan(0, 0);
    setBusca("");
    setHoverMun(null);
  }, [moverPan]);

  // ViewBox animado: zoom suave Brasil <-> UF (rAF; respeita reduced-motion).
  const vbAlvo: [number, number, number, number] = emUF ? bboxDaUF(emUF) : [-14, -10, W + 28, H + 24];
  const chaveVb = emUF ?? "BR";
  const [vb, setVb] = useState<[number, number, number, number]>(vbAlvo);
  const vbRef = useRef<[number, number, number, number]>(vbAlvo);

  useEffect(() => {
    const alvo: [number, number, number, number] = emUF ? bboxDaUF(emUF) : [-14, -10, W + 28, H + 24];
    const ini = vbRef.current;
    if (ini.every((v, i) => Math.abs(v - alvo[i]) < 0.05)) return;
    const aplicar = (c: [number, number, number, number]) => {
      vbRef.current = c;
      setVb(c);
    };
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      aplicar(alvo);
      return;
    }
    const t0 = performance.now();
    const dur = 450;
    let id = requestAnimationFrame(function passo(t: number) {
      const k = Math.min(1, (t - t0) / dur);
      const e = 1 - Math.pow(1 - k, 3);
      aplicar([
        ini[0] + (alvo[0] - ini[0]) * e,
        ini[1] + (alvo[1] - ini[1]) * e,
        ini[2] + (alvo[2] - ini[2]) * e,
        ini[3] + (alvo[3] - ini[3]) * e,
      ] as [number, number, number, number]);
      if (k < 1) id = requestAnimationFrame(passo);
    });
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chaveVb]);

  const buscaN = busca.trim().toLowerCase();
  const resultadosBusca = useMemo(() => {
    if (!malha || buscaN.length < 2) return [];
    return malha.municipios.filter((m) => m.nome.toLowerCase().includes(buscaN)).slice(0, 6);
  }, [malha, buscaN]);

  /* Centros (área-ponderados) de TODOS os municípios — usados pelo tooltip de
     hover e pelo rótulo flutuante do município selecionado. */
  const centrosMun = useMemo(() => {
    const r = new Map<string, { x: number; y: number; nome: string; area: number }>();
    if (!malha) return r;
    for (const m of malha.municipios) {
      let maior = m.aneis[0];
      let areaMax = 0;
      for (const a of m.aneis) {
        const ar = areaAnel(a);
        if (ar > areaMax) {
          areaMax = ar;
          maior = a;
        }
      }
      if (!maior || areaMax <= 0) continue; // sem contorno válido
      const pts = maior.map(([lng, lat]) => proj(lng, lat));
      const c = centroideDePts(pts);
      if (c) r.set(m.ibge, { x: c[0], y: c[1], nome: m.nome, area: areaMax });
    }
    return r;
  }, [malha]);

  const porIbge = useMemo(
    () => new Map((malha?.municipios ?? []).map((m) => [m.ibge, m] as const)),
    [malha],
  );

  /* Rótulos PERMANENTES de referência: só os maiores por área (proxy honesto de
     "município mais influente/visível"), em número pequeno e com anti-colisão.
     Servem de âncora para o usuário se localizar; o resto aparece no hover.
     Ao aproximar (zoom), liberamos mais nomes — como mapa de verdade. */
  const rotulosReferencia = useMemo(() => {
    if (!centrosMun.size) return [] as { ibge: string; x: number; y: number; nome: string }[];
    const quantos = zoom >= 5 ? 24 : zoom >= 3 ? 16 : zoom >= 1.8 ? 10 : 6;
    const ordenados = Array.from(centrosMun.entries())
      .map(([ibge, c]) => ({ ibge, ...c }))
      .sort((a, b) => b.area - a.area);
    const escolhidos: { ibge: string; x: number; y: number; nome: string }[] = [];
    const ocup: [number, number, number, number][] = [];
    const fonte = 6 / Math.sqrt(zoom); // encolhe com o zoom p/ não gigantizar
    for (const p of ordenados) {
      if (escolhidos.length >= quantos) break;
      const larg = p.nome.length * fonte * 0.6 + 6;
      const alt = fonte + 4;
      const rect: [number, number, number, number] = [p.x - larg / 2, p.y - alt / 2, p.x + larg / 2, p.y + alt / 2];
      if (ocup.some((o) => !(rect[2] < o[0] || rect[0] > o[2] || rect[3] < o[1] || rect[1] > o[3]))) continue;
      ocup.push(rect);
      escolhidos.push({ ibge: p.ibge, x: p.x, y: p.y, nome: p.nome });
    }
    return escolhidos;
  }, [centrosMun, zoom]);

  const aoSelMunRef = useRef(aoSelecionarMunicipio);
  aoSelMunRef.current = aoSelecionarMunicipio;

  /* Delegação: 1 handler na camada em vez de 3 × 645 handlers nos paths. */
  const clicarMun = useCallback(
    (e: ReactMouseEvent<SVGGElement>) => {
      if (arrastouRef.current) {
        arrastouRef.current = false;
        return; // foi arraste, não clique
      }
      const ibge = ibgeDe(e.target);
      if (!ibge || !emUF) return;
      const m = porIbge.get(ibge);
      if (!m) return;
      setNivel({ tipo: "uf", uf: emUF, munIbge: ibge });
      aoSelMunRef.current?.(ibge, m.nome);
    },
    [emUF, porIbge],
  );

  const hoverEntrar = useCallback((e: ReactPointerEvent<SVGGElement>) => {
    const ibge = ibgeDe(e.target);
    if (ibge) setHoverMun((h) => (h === ibge ? h : ibge));
  }, []);

  const hoverSair = useCallback((e: ReactPointerEvent<SVGGElement>) => {
    const ibge = ibgeDe(e.target);
    setHoverMun((h) => (ibge === null ? null : h === ibge ? null : h));
  }, []);

  return (
    <div className="overflow-hidden rounded-xl2 border border-line bg-surface shadow-card">
      <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
        <div className="flex min-w-0 items-center gap-2">
          {emUF ? (
            <button
              onClick={voltarBrasil}
              aria-label="Voltar para o mapa do Brasil"
              className="grid h-[44px] w-[44px] shrink-0 place-items-center rounded-full text-terra-ink transition hover:bg-terra-soft"
            >
              <ArrowLeft size={20} />
            </button>
          ) : null}
          <p id={tituloId} className="truncate text-[0.82rem] font-bold uppercase tracking-wide text-muted">
            {emUF ? `${infoDaUF(emUF)?.nome} · municípios` : "Brasil · toque num estado"}
          </p>
        </div>
        {emUF && malha ? (
          <div className="relative">
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
            <input
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar município…"
              aria-label="Buscar município pelo nome"
              className="min-h-[44px] w-36 rounded-full border border-line bg-canvas pl-9 pr-3 text-[0.88rem] text-ink outline-none placeholder:text-muted focus:border-terra sm:w-48"
            />
            {resultadosBusca.length > 0 ? (
              <ul className="absolute right-0 top-full z-20 mt-1 w-56 overflow-hidden rounded-xl border border-line bg-surface shadow-lift" role="listbox" aria-label="Municípios encontrados">
                {resultadosBusca.map((m) => (
                  <li key={m.ibge}>
                    <button
                      role="option"
                      aria-selected={municipioIbge === m.ibge}
                      onClick={() => {
                        setNivel({ tipo: "uf", uf: emUF, munIbge: m.ibge });
                        aoSelecionarMunicipio?.(m.ibge, m.nome);
                        setBusca("");
                      }}
                      className="flex min-h-[44px] w-full items-center gap-2 px-3 text-left text-[0.9rem] font-semibold text-ink transition hover:bg-terra-soft"
                    >
                      <MapPin size={15} className="shrink-0 text-terra-ink" aria-hidden />
                      {m.nome}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        ) : null}
        <div className="flex items-center gap-1" role="group" aria-label="Controles do mapa">
          <button onClick={afastar} disabled={zoom <= 1} aria-label="Afastar mapa"
            className="grid h-[44px] w-[44px] place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink disabled:opacity-40">
            <ZoomOut size={20} />
          </button>
          <button onClick={aproximar} disabled={zoom >= ZOOM_MAX} aria-label="Aproximar mapa"
            className="grid h-[44px] w-[44px] place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink disabled:opacity-40">
            <ZoomIn size={20} />
          </button>
          <button onClick={recentrar} aria-label="Recentralizar mapa"
            className="grid h-[44px] w-[44px] place-items-center rounded-full text-muted hover:bg-canvas hover:text-ink">
            <Maximize size={18} />
          </button>
        </div>
      </div>
      <svg
        viewBox={`${vb[0]} ${vb[1]} ${vb[2]} ${vb[3]}`}
        role="group"
        aria-labelledby={tituloId}
        className="block w-full touch-none select-none"
        style={{ aspectRatio: `${vb[2]} / ${vb[3]}`, background: "linear-gradient(180deg, #F6EFE3 0%, #EFE3CE 55%, #E7D6B8 100%)" }}
        onPointerDown={(e) => {
          // NÃO captura aqui: capturar no pointerdown redireciona o click
          // para o <svg> e o toque deixa de selecionar estado/município.
          ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
          if (ponteiros.current.size === 2) {
            // 2 dedos → inicia pinça; cancela o pan de 1 dedo em andamento.
            const [a, b] = Array.from(ponteiros.current.values());
            pinca.current = { dist: Math.hypot(a.x - b.x, a.y - b.y), zoom: zoomRef.current };
            arrasto.current = null;
            arrastouRef.current = true; // suprime o clique ao soltar
          } else {
            arrasto.current = { x: panRef.current.x, y: panRef.current.y, px: e.clientX, py: e.clientY };
            arrastouRef.current = false;
          }
        }}
        onPointerMove={(e) => {
          if (ponteiros.current.has(e.pointerId)) {
            ponteiros.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
          }
          // Pinça (celular): dois dedos controlam o zoom.
          if (pinca.current && ponteiros.current.size >= 2) {
            const [a, b] = Array.from(ponteiros.current.values());
            const dist = Math.hypot(a.x - b.x, a.y - b.y);
            if (pinca.current.dist > 0) {
              const z = Math.max(1, Math.min(ZOOM_MAX, +(pinca.current.zoom * (dist / pinca.current.dist)).toFixed(2)));
              zoomRef.current = z;
              setZoom(z);
            }
            return;
          }
          const a = arrasto.current;
          if (!a) return;
          const dx = e.clientX - a.px;
          const dy = e.clientY - a.py;
          if (!arrastouRef.current && Math.abs(dx) + Math.abs(dy) > 6) {
            arrastouRef.current = true;
            // captura só quando virou arraste de verdade
            e.currentTarget.setPointerCapture?.(e.pointerId);
          }
          panRef.current = { x: a.x + dx / zoomRef.current, y: a.y + dy / zoomRef.current };
          // escrita direta no DOM: arraste sem re-render do React
          gRef.current?.setAttribute("transform", transformDe(panRef.current.x, panRef.current.y, zoomRef.current));
        }}
        onPointerUp={(e) => {
          if (e.currentTarget.hasPointerCapture?.(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
          ponteiros.current.delete(e.pointerId);
          if (ponteiros.current.size < 2) pinca.current = null;
          arrasto.current = null;
          setPan({ ...panRef.current }); // sincroniza o espelho (1 re-render por gesto)
        }}
        onPointerCancel={(e) => {
          if (e.currentTarget.hasPointerCapture?.(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId);
          ponteiros.current.delete(e.pointerId);
          if (ponteiros.current.size < 2) pinca.current = null;
          arrasto.current = null;
          setPan({ ...panRef.current });
        }}
        onWheel={(e) => {
          // Zoom pela roda do mouse (desktop). Passivo: só ajusta o zoom.
          const passo = zoomRef.current < 3 ? 0.3 : 0.6;
          const z = Math.max(1, Math.min(ZOOM_MAX, +(zoomRef.current + (e.deltaY < 0 ? passo : -passo)).toFixed(2)));
          zoomRef.current = z;
          setZoom(z);
        }}
      >
        <g ref={gRef} transform={transformDe(pan.x, pan.y, zoom)}>
          <defs>
            <filter id="sombra-uf" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="3" stdDeviation="4" floodColor="#2A2420" floodOpacity="0.25" />
            </filter>
          </defs>
          {emUF && malha ? (
            /* Nível município estilo Google Maps: nome em cada área + hover. */
            <g onClick={clicarMun} onPointerOver={hoverEntrar} onPointerOut={hoverSair}>
              {malha.municipios.map((mun) => {
                const ativoMun = municipioIbge === mun.ibge;
                return (
                  <MunicipioG
                    key={mun.ibge}
                    ibge={mun.ibge}
                    d={pathsMun.get(mun.ibge) ?? ""}
                    nome={mun.nome}
                    ativo={ativoMun}
                    emHover={hoverMun === mun.ibge}
                    destaque={buscaN.length >= 2 && mun.nome.toLowerCase().includes(buscaN)}
                  />
                );
              })}
              {/* HIERARQUIA DE RÓTULO — uma só camada "fala" por vez, para não
                  empilhar texto (o problema do "não some perto do hover").
                  Foco ativo = selecionado tem prioridade sobre o hover. */}
              {(() => {
                const focoIbge = municipioIbge ?? hoverMun;
                const focoCentro = focoIbge ? centrosMun.get(focoIbge) : null;
                const k = 1 / Math.sqrt(zoom); // tamanho visual estável ao aproximar

                // Rótulos de referência: escondem perto do foco (raio em unidades
                // do viewBox) — assim nenhum nome colide com a pílula ativa.
                const raio = 26 * k;
                const refs = rotulosReferencia.filter((r) => {
                  if (r.ibge === focoIbge) return false;
                  if (focoCentro && Math.hypot(r.x - focoCentro.x, r.y - focoCentro.y) < raio) return false;
                  return true;
                });

                const mFoco = focoIbge ? porIbge.get(focoIbge) : null;

                return (
                  <>
                    {refs.map((r) => (
                      <text
                        key={`ref-${r.ibge}`}
                        x={r.x} y={r.y}
                        textAnchor="middle" dominantBaseline="central" aria-hidden
                        className="pointer-events-none font-display"
                        style={{
                          fontSize: 6 * k,
                          fontWeight: 800,
                          fill: "rgb(var(--c-terra-ink))",
                          fillOpacity: 0.85,
                          paintOrder: "stroke",
                          stroke: "#FEFCF8",
                          strokeWidth: 1.8 * k,
                        }}
                      >
                        {r.nome}
                      </text>
                    ))}

                    {/* UMA pílula só, para o foco ativo (selecionado > hover). */}
                    {mFoco && focoCentro ? (
                      <g aria-hidden className="pointer-events-none" transform={`translate(${focoCentro.x} ${focoCentro.y - 11 * k})`}>
                        <rect
                          x={-(mFoco.nome.length * 5.2 + 18) * k / 2}
                          y={-9 * k}
                          width={(mFoco.nome.length * 5.2 + 18) * k}
                          height={17 * k}
                          rx={8 * k}
                          style={{
                            fill: municipioIbge ? "rgb(var(--c-terra-ink))" : "rgb(var(--c-ink))",
                            opacity: 0.96,
                          }}
                        />
                        {/* bico da pílula apontando o município */}
                        <path
                          d={`M${-3 * k},${8 * k} L${3 * k},${8 * k} L0,${12 * k} Z`}
                          style={{ fill: municipioIbge ? "rgb(var(--c-terra-ink))" : "rgb(var(--c-ink))", opacity: 0.96 }}
                        />
                        <text textAnchor="middle" dominantBaseline="central"
                          style={{ fontSize: 8 * k, fontWeight: 800, fill: "#fff" }}>
                          {mFoco.nome}
                        </text>
                      </g>
                    ) : null}
                  </>
                );
              })()}
            </g>
          ) : emUF && !malha ? (
            /* UF carregando ou sem malha local: contorno da UF + estado honesto. */
            <g>
              <path
                d={paths.get(emUF) ?? ""}
                style={{ fill: "rgb(var(--c-terra-soft))", stroke: "rgb(var(--c-terra-ink))", strokeWidth: 1.6, strokeLinejoin: "round" }}
              />
              <foreignObject x={bboxDaUF(emUF)[0]} y={bboxDaUF(emUF)[1]} width={bboxDaUF(emUF)[2]} height={bboxDaUF(emUF)[3]}>
                <div
                  // @ts-expect-error foreignObject + div (namespace xhtml implícito)
                  xmlns="http://www.w3.org/1999/xhtml"
                  style={{ display: "flex", height: "100%", alignItems: "center", justifyContent: "center", textAlign: "center", padding: 12 }}
                >
                  <p style={{ fontSize: 13, color: "rgb(var(--c-muted))", background: "rgb(var(--c-surface))", border: "1px solid rgb(var(--c-line))", borderRadius: 12, padding: "8px 12px" }}>
                    {erroMun ? `Municípios de ${emUF} ainda sem arquivo local — cenário da UF continua abaixo.` : "Carregando municípios…"}
                  </p>
                </div>
              </foreignObject>
            </g>
          ) : (
          <g>
          {UFS.map((info) => {
            const ativa = info.sigla === selecionada;
            const d = paths.get(info.sigla) ?? "";
            const [cx, cy] = centroide(info.sigla);
            const [dx, dy] = AJUSTE_ROTULO[info.sigla] ?? [0, 0];
            const micro = ["DF", "SE", "AL", "PB", "RN", "ES", "RJ", "SC", "CE", "PE", "AP", "RS", "PR"].includes(info.sigla);
            return (
              <g key={info.sigla}>
                <path
                  d={d}
                  onClick={() => {
                    if (arrastouRef.current) {
                      arrastouRef.current = false;
                      return;
                    }
                    abrirUF(info.sigla);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      abrirUF(info.sigla);
                    }
                  }}
                  tabIndex={0}
                  role="button"
                  aria-label={`${info.nome} (${info.sigla}), ${info.regiao}${ativa ? ", selecionado" : ""}. Toque para ver municípios.`}
                  aria-pressed={ativa}
                  className="cursor-pointer outline-none transition-all duration-200"
                  filter={ativa ? "url(#sombra-uf)" : undefined}
                  style={{
                    fill: ativa ? "rgb(var(--c-terra))" : "#FDF9F1",
                    fillOpacity: ativa ? 1 : 0.92,
                    stroke: ativa ? "rgb(var(--c-terra-ink))" : "#C9B591",
                    strokeWidth: ativa ? 2.4 : 1.1,
                    strokeLinejoin: "round",
                  }}
                  onMouseEnter={(e) => {
                    if (!ativa) (e.currentTarget as SVGPathElement).style.fill = "rgb(var(--c-terra-soft))";
                  }}
                  onMouseLeave={(e) => {
                    if (!ativa) (e.currentTarget as SVGPathElement).style.fill = "#FDF9F1";
                  }}
                >
                  <title>{`${info.nome} — toque para ver municípios`}</title>
                </path>
                <text
                  x={cx + dx} y={cy + dy - 7}
                  textAnchor="middle" dominantBaseline="central" aria-hidden
                  className="pointer-events-none font-display"
                  style={{
                    fontSize: ativa ? 13 : micro ? 10 : 12,
                    fontWeight: 800,
                    fill: ativa ? "#fff" : "rgb(var(--c-terra-ink))",
                    paintOrder: "stroke",
                    stroke: ativa ? "rgb(var(--c-terra-ink))" : "#FDF9F1",
                    strokeWidth: 2.5,
                  }}
                >
                  {info.sigla}
                </text>
                <text
                  x={cx + dx} y={cy + dy + 8}
                  textAnchor="middle" dominantBaseline="central" aria-hidden
                  className="pointer-events-none"
                  style={{
                    fontSize: ativa ? 8.5 : 7.5,
                    fontWeight: 600,
                    fill: ativa ? "#fff" : "rgb(var(--c-muted))",
                    fillOpacity: ativa ? 1 : 0.9,
                    paintOrder: "stroke",
                    stroke: ativa ? "rgb(var(--c-terra-ink))" : "#FDF9F1",
                    strokeWidth: 2.5,
                  }}
                >
                  {info.nome}
                </text>
              </g>
            );
          })}
          </g>
          )}
        </g>
      </svg>
      <div className="flex flex-wrap items-center gap-2 border-t border-line px-3 py-2.5">
        {carregandoMun ? (
          <span className="inline-flex items-center gap-1.5 text-[0.78rem] font-semibold text-muted">
            <Loader2 size={14} className="animate-spin" aria-hidden />
            Carregando municípios…
          </span>
        ) : null}
        {emUF && malha ? (
          <span className="inline-flex min-w-0 items-center gap-1.5 text-[0.78rem] font-semibold text-muted">
            <MapPin size={13} className="shrink-0 text-terra-ink" aria-hidden />
            <span className="truncate">
              {(() => {
                const foco = municipioIbge ?? hoverMun;
                const nome = foco ? porIbge.get(foco)?.nome : null;
                if (nome) return <strong className="text-ink">{nome}</strong>;
                return "toque num município";
              })()}
              {" · "}
              {malha.total} municípios
            </span>
          </span>
        ) : null}
        <span className="inline-flex items-center gap-1.5 text-[0.78rem] font-semibold text-muted">
          <span className="h-3 w-3 rounded-md bg-terra-soft ring-1 ring-line" aria-hidden />
          Sem dado — escala neutra
        </span>
        <span className="inline-flex items-center gap-1.5 text-[0.78rem] font-semibold text-muted">
          <span className="h-3 w-3 rounded-md bg-terra" aria-hidden />
          {emUF ? "Município selecionado" : "UF selecionada"}
        </span>
      </div>
    </div>
  );
}

