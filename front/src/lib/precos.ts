/**
 * Camada de PREÇO honesta do Mapa de Oportunidade Regional.
 *
 * REGRA DE OURO: todo preço exibido precisa de { valor, unidade, fonte, data }.
 * Sem número confirmado → estado "sem_cotacao" / "pendente" e a UI mostra
 * "sem cotação disponível". Nunca estimar, nunca "venda agora" — o card deixa
 * explícito que é REFERÊNCIA/CONTEXTO, não recomendação de venda.
 *
 * Três origens prontas:
 *  1. PGPM (CONAB) — preço MÍNIMO oficial por cultura/safra. Estável e público.
 *     Valores reais SÓ entram confirmados pela equipe; até lá, pendente.
 *  2. CONAB preços de mercado por UF — estrutura pronta, pendente até ingestão.
 *  3. Cepea/ESALQ — NUNCA copiar número (licença). Só LINK externo com rótulo
 *     "ver indicador diário (Cepea/ESALQ)".
 *
 * Assinatura espelha a futura API (GET /api/precos?uf=&cultura=).
 * Quando o backend ligar, trocar o corpo por fetch sem mexer na UI.
 */
import type { PrecoRef, UFSigla } from "./types";

/** Nome amigável da cultura para os cards (ids de CULTURAS em dados-locais). */
export const CULTURA_LABEL: Record<string, string> = {
  milho: "Milho",
  soja: "Soja",
  feijao: "Feijão",
  arroz: "Arroz",
  trigo: "Trigo",
};

export function rotuloCultura(culturaId: string | null | undefined): string {
  if (!culturaId) return "sua cultura";
  return CULTURA_LABEL[culturaId] ?? culturaId;
}

/**
 * PGPM — preço mínimo oficial (CONAB).
 * Sem valores embutidos até confirmação da equipe: retorna pendente honesto.
 * Para plugar um valor confirmado depois, preencha `valor` + `safra` e troque
 * `estado` para "disponivel" — a UI já trata.
 */
export function pgpmDaCultura(culturaId: string | null | undefined): PrecoRef {
  const cultura = rotuloCultura(culturaId);
  return {
    tipo: "pgpm",
    cultura,
    uf: null,
    valor: null,
    unidade: "R$/60kg",
    fonte: {
      nome: "CONAB — PGPM (preço mínimo)",
      periodo: "safra 2026/27 (quando confirmado)",
      limitacoes: [
        "Preço mínimo oficial, não preço de mercado.",
        "Valor exibido somente após confirmação da equipe.",
      ],
    },
    data: null,
    estado: "pendente",
    aviso:
      "Preço mínimo de referência do governo. Serve de piso para planejar — não diz quando vender.",
  };
}

/**
 * CONAB — preços de mercado por UF. Estrutura pronta, pendente até ingestão.
 */
export function conabMercadoDaUF(
  uf: UFSigla,
  culturaId: string | null | undefined,
): PrecoRef {
  const cultura = rotuloCultura(culturaId);
  return {
    tipo: "conab_mercado",
    cultura,
    uf,
    valor: null,
    unidade: "R$/60kg",
    fonte: {
      nome: "CONAB — preços de mercado por UF",
      periodo: "aguardando ingestão",
      limitacoes: ["Camada ainda não ligada ao backend."],
    },
    data: null,
    estado: "pendente",
    aviso: "Mostra o contexto de mercado da sua região — não é ordem de venda.",
  };
}

/**
 * Cepea/ESALQ — SOMENTE link externo. Nunca embutir número (licença).
 */
export function cepeaLink(culturaId: string | null | undefined): PrecoRef {
  const cultura = rotuloCultura(culturaId);
  return {
    tipo: "cepea",
    cultura,
    uf: null,
    valor: null,
    unidade: "indicador diário",
    fonte: {
      nome: "Cepea/ESALQ — indicador diário (link externo)",
      limitacoes: [
        "Número pertence ao Cepea; abrimos o site oficial em vez de copiar.",
      ],
    },
    data: null,
    estado: "link_externo",
    url: "https://www.cepea.esalq.usp.br/br",
    aviso: "Abre o indicador oficial no site do Cepea.",
  };
}

/** Os três blocos do card de preço, sempre nesta ordem: PGPM → CONAB → Cepea. */
export function precosDaUF(
  uf: UFSigla,
  culturaId: string | null | undefined,
): PrecoRef[] {
  return [pgpmDaCultura(culturaId), conabMercadoDaUF(uf, culturaId), cepeaLink(culturaId)];
}

/** Formata R$ pt-BR sem inventar casa decimal além do dado. Null-safe. */
export function formatarPreco(valor: number | null, unidade: string): string {
  if (valor == null) return "sem cotação disponível";
  return `${valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })} · ${unidade}`;
}
