/**
 * Humanização dos textos dos cards de evidência.
 *
 * O que acontece aqui (e por quê):
 *   O backend (back/app/routes/regiao.py) devolve CAMPOS CRUDOS:
 *     { culturaTopo: "feijao", areaHa: 215, producaoT: 742, safraRef: "2013–2017" }
 *   Antes, o front juntava tudo com `join(" · ")` e o produtor lia
 *   "feijao · 215 ha · 742 t · safra 2013–2017": sem sujeito, sem acento,
 *   sem dizer o que cada número significa.
 *
 *   Esta camada monta a SAÍDA humanizada na apresentação, para valer para
 *   o dado local (mapa-local.ts) E o dado da API — sem tocar no contrato.
 *
 * Regras seguidas:
 *   1. Sempre uma FRASE, com sujeito e período, em português corrido.
 *   2. Número em pt-BR com unidade por extenso na frase ("215 hectares");
 *      a ficha compacta ("215 ha") ganha `dica` explicando em palavra simples.
 *   3. Nunca inventar: o que não existe vira frase honesta de "sem dado"
 *      (documento mestre §6.2 — 4 estados honestos, nunca número estimado).
 *
 * Os construtores devolvem `TextoCard`, que `PainelRegional` despeja direto
 * nas props do `EvidenceCard`.
 */
import type { DestaqueCard, IrrigacaoUF, ProducaoUF, SeguroUF } from "./types";

export interface TextoCard {
  detalhe: string;
  destaques: DestaqueCard[];
  leitura?: string;
}

/* ------------------------------------------------------------------ */
/* 1. Cultura: slug do SIGEF → nome legível com artigo                */
/* ------------------------------------------------------------------ */

interface CulturaLegivel {
  nome: string;
  /** "o" | "a" — preciso para não escrever "a Feijão". */
  artigo: "o" | "a";
}

/**
 * Chaves canônicas do pipeline (correlacao/canon.py): primeiro token,
 * minúsculo, sem acento. Ex.: "Feijão Cores" → "feijao".
 */
const CULTURAS: Record<string, CulturaLegivel> = {
  feijao: { nome: "Feijão", artigo: "o" },
  soja: { nome: "Soja", artigo: "a" },
  milho: { nome: "Milho", artigo: "o" },
  arroz: { nome: "Arroz", artigo: "o" },
  trigo: { nome: "Trigo", artigo: "o" },
  triticale: { nome: "Triticale", artigo: "o" },
  cafe: { nome: "Café", artigo: "o" },
  algodao: { nome: "Algodão", artigo: "o" },
  cana: { nome: "Cana-de-açúcar", artigo: "a" },
  cana_acucar: { nome: "Cana-de-açúcar", artigo: "a" },
  mandioca: { nome: "Mandioca", artigo: "a" },
  batata: { nome: "Batata", artigo: "a" },
  tomate: { nome: "Tomate", artigo: "o" },
  sorgo: { nome: "Sorgo", artigo: "o" },
  amendoim: { nome: "Amendoim", artigo: "o" },
  girassol: { nome: "Girassol", artigo: "o" },
  aveia: { nome: "Aveia", artigo: "a" },
  cevada: { nome: "Cevada", artigo: "a" },
  mamona: { nome: "Mamona", artigo: "a" },
  gergelim: { nome: "Gergelim", artigo: "o" },
  uva: { nome: "Uva", artigo: "a" },
  laranja: { nome: "Laranja", artigo: "a" },
  seringueira: { nome: "Seringueira", artigo: "a" },
  cacau: { nome: "Cacau", artigo: "o" },
};

/** Normaliza para a chave canônica: "Feijão Cores" → "feijao_cores". */
function chaveCanonica(bruto: string): string {
  return bruto
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[\s-]+/g, "_")
    .trim();
}

/** Fallback honesto: só capitaliza, sem inventar acento. */
function capitalizar(bruto: string): string {
  return bruto
    .split(/[\s_]+/)
    .filter(Boolean)
    .map((p) => p.charAt(0).toUpperCase() + p.slice(1))
    .join(" ");
}

/**
 * "feijao" → { nome: "Feijão", artigo: "o" }.
 * Tenta a chave cheia e depois o primeiro token (mesma regra do backend).
 * Sem dado → usa "a cultura principal" (nunca um nome inventado).
 */
export function culturaLegivel(
  bruto?: string | null,
): CulturaLegivel & { desconhecida: boolean } {
  const valor = (bruto ?? "").trim();
  if (!valor) return { nome: "a cultura principal", artigo: "a", desconhecida: true };

  const chave = chaveCanonica(valor);
  const achou =
    CULTURAS[chave] ??
    CULTURAS[chave.split("_")[0]] ??
    CULTURAS[chave.replace(/^feijao_.*/, "feijao")];
  if (achou) return { ...achou, desconhecida: false };

  // Já vem acentuado da API? Só capitaliza e segue.
  return { nome: capitalizar(valor), artigo: "o", desconhecida: true };
}

/** "feijao" → "Feijão". Rótulo curto, sem artigo. */
export function rotuloCulturaAmigavel(bruto?: string | null): string {
  return culturaLegivel(bruto).nome;
}

/* ------------------------------------------------------------------ */
/* 2. Números e unidades em pt-BR                                     */
/* ------------------------------------------------------------------ */

const NF = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });

export function numeroBR(valor: number): string {
  return NF.format(valor);
}

/** 1 → singular; 1,5 e 2+ → plural (pt-BR). */
function plural(valor: number, um: string, muitos: string): string {
  return Math.abs(valor) === 1 ? um : muitos;
}

/** 215 → "215 hectares" (1 → "1 hectare"). */
export function hectares(valor: number): string {
  return `${numeroBR(valor)} ${plural(valor, "hectare", "hectares")}`;
}

/** 742 → "742 toneladas" (1 → "1 tonelada"). */
export function toneladas(valor: number): string {
  return `${numeroBR(valor)} ${plural(valor, "tonelada", "toneladas")}`;
}

/**
 * "2013–2017" → "2013 a 2017". Aceita travessão, hífen e barra.
 * Retorna null quando não há safra — a frase simplesmente a omite.
 */
export function safraAmigavel(ref?: string | null): string | null {
  const bruto = (ref ?? "").trim();
  if (!bruto) return null;
  const m = bruto.match(/^(\d{4})\s*(?:[–—-]|a|\/)\s*(\d{4})$/);
  if (m && m[1] !== m[2]) return `${m[1]} a ${m[2]}`;
  return bruto;
}

/** Liga pedaços de frase: "a, b e c" / "a e b" / "a". */
function juntar(pedacos: string[]): string {
  const limpos = pedacos.filter(Boolean);
  if (limpos.length === 0) return "";
  if (limpos.length === 1) return limpos[0];
  return `${limpos.slice(0, -1).join(", ")} e ${limpos[limpos.length - 1]}`;
}

/** true quando o valor é singular (1 ou -1) — para concordar o verbo. */
function eSingular(valor: number): boolean {
  return Math.abs(valor) === 1;
}

/**
 * "São 215 hectares..." / "É 1 hectare...".
 * Com sujeito composto ("1 hectare e 742 toneladas") o verbo no plural é
 * correto em português, então só caímos no singular quando TODOS são 1.
 */
function serPara(medidas: { singular: boolean }[]): string {
  const todosSingular = medidas.length > 0 && medidas.every((m) => m.singular);
  return todosSingular ? "É" : "São";
}

/** Sem dado: mesma frase honesta para todos os blocos do painel. */
function semDado(queE: string): TextoCard {
  return {
    detalhe: `Ainda não temos ${queE} para a sua região. O dado entra aqui assim que a base oficial ligar — sem estimativa.`,
    destaques: [],
    leitura:
      "Enquanto isso, a aba Preços mostra o que já está disponível, com fonte e período.",
  };
}

/* ------------------------------------------------------------------ */
/* 3. Frases humanizadas por bloco do card                            */
/* ------------------------------------------------------------------ */

/**
 * "O que a região mais produz" (SIGEF/MAPA).
 *
 * ANTES:  "feijao · 215 ha · 742 t · safra 2013–2017"
 * DEPOIS: "É o Feijão, a cultura que mais se planta em São Paulo.
 *         São 215 hectares de área plantada e 742 toneladas de produção,
 *         no período de 2013 a 2017."
 * + fichas com o número compacto e uma `dica` em palavra simples.
 */
export function producaoEmTexto(
  p: Pick<ProducaoUF, "estado" | "culturaTopo" | "areaHa" | "producaoT" | "safraRef">,
  regiao: string,
): TextoCard {
  const temDado =
    p.estado === "disponivel" &&
    (p.culturaTopo != null || p.areaHa != null || p.producaoT != null);

  if (!temDado) return semDado("os dados de produção do SIGEF");

  const cult = culturaLegivel(p.culturaTopo);
  const safra = safraAmigavel(p.safraRef);

  const medidas: { texto: string; singular: boolean }[] = [];
  if (p.areaHa != null)
    medidas.push({ texto: `${hectares(p.areaHa)} de área plantada`, singular: eSingular(p.areaHa) });
  if (p.producaoT != null)
    medidas.push({ texto: `${toneladas(p.producaoT)} de produção`, singular: eSingular(p.producaoT) });

  const periodo = safra ? `, no período de ${safra}` : "";

  const destaques: DestaqueCard[] = [];
  if (p.areaHa != null)
    destaques.push({
      rotulo: "Área plantada",
      valor: `${numeroBR(p.areaHa)} ha`,
      dica: "hectares ocupados por essa cultura",
    });
  if (p.producaoT != null)
    destaques.push({
      rotulo: "Produção",
      valor: `${numeroBR(p.producaoT)} t`,
      dica: "toneladas produzidas",
    });
  if (safra)
    destaques.push({ rotulo: "Período", valor: safra, dica: "safra de referência" });

  const sujeito = `É ${cult.artigo} ${cult.nome}, a cultura que mais se planta em ${regiao}.`;
  const detalhe =
    medidas.length > 0
      ? `${sujeito} ${serPara(medidas)} ${juntar(medidas.map((m) => m.texto))}${periodo}.`
      : `${sujeito} O total publicado pelo SIGEF ainda não foi exposto.`;

  return {
    detalhe,
    destaques,
    leitura:
      "Compare com a área e a colheita da sua propriedade para ver se você está na média da região.",
  };
}

/**
 * "Força da cultura no seguro agrícola" (PSR/SISSER — MAPA, 2016–2024).
 *
 * ANTES:  "topo: feijao · 7 apólices · R$ ..."
 * DEPOIS: "É o Feijão, a cultura que mais concentra seguro rural em São Paulo.
 *         São 7 apólices, entre 2016 e 2024."
 */
export function seguroEmTexto(
  s: Pick<SeguroUF, "estado" | "apolices" | "valorSegurado" | "culturaTopo">,
  regiao: string,
): TextoCard {
  const temDado =
    s.estado === "disponivel" && (s.apolices != null || s.valorSegurado != null);

  if (!temDado) return semDado("o histórico de apólices do seguro rural");

  const cult = culturaLegivel(s.culturaTopo);

  const medidas: { texto: string; singular: boolean }[] = [];
  if (s.apolices != null)
    medidas.push({
      texto: `${numeroBR(s.apolices)} ${plural(s.apolices, "apólice", "apólices")}`,
      singular: eSingular(s.apolices),
    });
  if (s.valorSegurado != null)
    medidas.push({ texto: `R$ ${numeroBR(s.valorSegurado)} segurados`, singular: false });

  const detalhe =
    medidas.length > 0
      ? `É ${cult.artigo} ${cult.nome}, a cultura que mais concentra seguro rural em ${regiao}: ` +
        `${serPara(medidas)} ${juntar(medidas.map((m) => m.texto))}, entre 2016 e 2024.`
      : `É ${cult.artigo} ${cult.nome}, a cultura que mais concentra seguro rural em ${regiao}. ` +
        `O detalhe por cultura ainda não foi exposto.`;

  const destaques: DestaqueCard[] = [];
  if (s.apolices != null)
    destaques.push({ rotulo: "Apólices", valor: numeroBR(s.apolices), dica: "contratos firmados" });
  if (s.valorSegurado != null)
    destaques.push({ rotulo: "Valor segurado", valor: `R$ ${numeroBR(s.valorSegurado)}`, dica: "total das apólices" });
  destaques.push({ rotulo: "Período", valor: "2016 a 2024", dica: "histórico do PSR/SISSER" });

  return {
    detalhe,
    destaques,
    leitura:
      "Muita apólice nessa cultura significa mercado maduro: o produtor vizinho já contrata seguro e há histórico para conferir.",
  };
}

/**
 * "Irrigação disponível" (Atlas de Irrigação — ANA).
 * Aceita tanto o `detalhe` que o backend devolve (grupo/sistema) quanto a área.
 */
export function irrigacaoEmTexto(
  i: { estado: string; areaIrrigadaHa: number | null; detalhe?: string | null },
  regiao: string,
): TextoCard {
  if (i.estado === "disponivel" && i.areaIrrigadaHa != null) {
    const ha = i.areaIrrigadaHa;
    const verbos = eSingular(ha) ? { ser: "É", adj: "irrigado" } : { ser: "São", adj: "irrigados" };
    return {
      detalhe: `${verbos.ser} ${hectares(ha)} ${verbos.adj} em ${regiao}, segundo o Atlas da ANA.`,
      destaques: [
        { rotulo: "Área irrigada", valor: `${numeroBR(ha)} ha`, dica: "hectares com água controlada" },
      ],
      leitura:
        "Irrigação segura a produção em ano seco — mas aumenta o custo de energia e de manutenção.",
    };
  }

  if (i.estado === "disponivel" && i.detalhe) {
    // Backend já devolveu a frase pronta (grupo/sistema do Atlas) — usamos tal qual.
    return {
      detalhe: i.detalhe,
      destaques: [],
      leitura: "Irrigação segura a produção em ano seco — mas aumenta custo de energia e manutenção.",
    };
  }

  return semDado("a área irrigada do Atlas da ANA");
}

