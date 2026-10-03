/**
 * Camada de dados LOCAL do Mapa Regional. REGRA DE OURO: nenhum numero
 * aqui e apresentado como fato. Tudo retorna "pendente"/"sem_dado" com
 * fonte + periodo. Assinaturas espelham a futura API GET /api/regiao?uf=SP.
 */
import type {
  CanalPublico,
  IrrigacaoUF,
  OportunidadeRegional,
  ProducaoUF,
  RegiaoBR,
  ResumoRegional,
  SeguroUF,
  SoloRegional,
  UFInfo,
  UFSigla,
} from "./types";
import { precosDaUF } from "./precos";

export const UFS: UFInfo[] = [
  { sigla: "AC", nome: "Acre", regiao: "Norte" },
  { sigla: "AL", nome: "Alagoas", regiao: "Nordeste" },
  { sigla: "AM", nome: "Amazonas", regiao: "Norte" },
  { sigla: "AP", nome: "Amapá", regiao: "Norte" },
  { sigla: "BA", nome: "Bahia", regiao: "Nordeste" },
  { sigla: "CE", nome: "Ceará", regiao: "Nordeste" },
  { sigla: "DF", nome: "Distrito Federal", regiao: "Centro-Oeste" },
  { sigla: "ES", nome: "Espírito Santo", regiao: "Sudeste" },
  { sigla: "GO", nome: "Goiás", regiao: "Centro-Oeste" },
  { sigla: "MA", nome: "Maranhão", regiao: "Nordeste" },
  { sigla: "MG", nome: "Minas Gerais", regiao: "Sudeste" },
  { sigla: "MS", nome: "Mato Grosso do Sul", regiao: "Centro-Oeste" },
  { sigla: "MT", nome: "Mato Grosso", regiao: "Centro-Oeste" },
  { sigla: "PA", nome: "Pará", regiao: "Norte" },
  { sigla: "PB", nome: "Paraíba", regiao: "Nordeste" },
  { sigla: "PE", nome: "Pernambuco", regiao: "Nordeste" },
  { sigla: "PI", nome: "Piauí", regiao: "Nordeste" },
  { sigla: "PR", nome: "Paraná", regiao: "Sul" },
  { sigla: "RJ", nome: "Rio de Janeiro", regiao: "Sudeste" },
  { sigla: "RN", nome: "Rio Grande do Norte", regiao: "Nordeste" },
  { sigla: "RO", nome: "Rondônia", regiao: "Norte" },
  { sigla: "RR", nome: "Roraima", regiao: "Norte" },
  { sigla: "RS", nome: "Rio Grande do Sul", regiao: "Sul" },
  { sigla: "SC", nome: "Santa Catarina", regiao: "Sul" },
  { sigla: "SE", nome: "Sergipe", regiao: "Nordeste" },
  { sigla: "SP", nome: "São Paulo", regiao: "Sudeste" },
  { sigla: "TO", nome: "Tocantins", regiao: "Norte" },
];

export const SIGLAS_VALIDAS: ReadonlySet<string> = new Set(UFS.map((u) => u.sigla));

export function infoDaUF(sigla: string): UFInfo | null {
  const s = sigla.trim().toUpperCase();
  return UFS.find((u) => u.sigla === s) ?? null;
}

export function ufsPorRegiao(regiao: RegiaoBR): UFInfo[] {
  return UFS.filter((u) => u.regiao === regiao);
}

export function ufDoPerfil(uf: string | null | undefined): UFSigla {
  const s = (uf ?? "").trim().toUpperCase();
  if ((SIGLAS_VALIDAS as ReadonlySet<string>).has(s)) return s as UFSigla;
  return "SP";
}

export function soloDaUF(uf: UFSigla): SoloRegional {
  return {
    uf,
    estado: "pendente",
    soloId: null,
    descricao:
      "Ainda não temos o solo desta região. Quando a base ligar, mostramos o solo predominante em linguagem simples: arenoso (a água escorre rápido), médio (equilíbrio) ou argiloso (segura a água).",
    fonte: {
      nome: "ZARC / dicionário de solos (MAPA)",
      periodo: "aguardando ingestão",
      limitacoes: ["O solo varia dentro do estado; o bloco mostra o predominante."],
    },
  };
}

export function producaoDaUF(uf: UFSigla): ProducaoUF {
  return {
    uf,
    estado: "pendente",
    culturaTopo: null,
    areaHa: null,
    producaoT: null,
    safraRef: null,
    fonte: {
      nome: "SIGEF Sementes / MAPA — agregado por UF",
      periodo: "aguardando ingestão",
      limitacoes: ["Camada ainda não ligada ao backend.", "Nenhum valor exibido antes da ingestão real."],
    },
  };
}

export function seguroDaUF(uf: UFSigla): SeguroUF {
  return {
    uf,
    estado: "pendente",
    apolices: null,
    valorSegurado: null,
    culturaTopo: null,
    fonte: {
      nome: "MAPA — PSR/SISSER",
      periodo: "2016–2024 (quando ligado)",
      limitacoes: ["Dados de apólice, não de produção individual.", "Camada ainda não ligada ao backend."],
    },
  };
}

export function irrigacaoDaUF(uf: UFSigla): IrrigacaoUF {
  return {
    uf,
    estado: "pendente",
    areaIrrigadaHa: null,
    fonte: {
      nome: "ANA — Atlas Irrigação",
      periodo: "aguardando ingestão",
      limitacoes: ["Camada ainda não ligada ao backend."],
    },
  };
}

export function canaisDaUF(uf: UFSigla): CanalPublico {
  return {
    uf,
    estado: "pendente",
    programas: ["PAA — Aquisicao de Alimentos", "PNAE — Alimentacao Escolar"],
    canais: [
      { id: "cooperativas", categoria: "Cooperativas", descricao: "Entrega conjunta e venda em escala; as regras variam de cooperativa para cooperativa." },
      { id: "cerealistas", categoria: "Cerealistas e armazéns", descricao: "Compra na região; as condições mudam por praça e época do ano." },
      { id: "paa", categoria: "PAA — compras públicas", descricao: "O governo compra da agricultura familiar por chamada pública." },
      { id: "pnae", categoria: "PNAE — merenda escolar", descricao: "Escolas compram do produtor familiar, com prêmio sobre o preço de mercado." },
      { id: "feiras", categoria: "Feiras e venda direta", descricao: "Venda direta ao consumidor, sem intermediário." },
    ],
    detalhe: "Os canais públicos (PAA/PNAE) compram da agricultura familiar por chamada pública. A lista de chamadas da sua região entra aqui quando a ingestão ligar. Enquanto isso, procure a secretaria de agricultura do município.",
    fonte: {
      nome: "PAA / PNAE — camada declarada (sem ingestão)",
      periodo: "em breve",
      limitacoes: ["Sem lista de compradores: nenhum nome exibido sem fonte oficial.", "Regras variam por município e edital."],
    },
  };
}

export function oportunidadeDaUF(uf: UFSigla): OportunidadeRegional {
  return {
    uf,
    estado: "pendente",
    culturasAptasPoucoExploradas: [],
    detalhe: "Quando o cruzamento ZARC x SIGEF ligar, mostramos aqui as culturas aptas para o seu estado que a região ainda explora pouco. É um cenário para estudar — não uma ordem de plantio.",
    fonte: {
      nome: "ZARC/MAPA x SIGEF — cruzamento pendente",
      periodo: "aguardando ingestão",
      limitacoes: ["Requer as duas camadas ligadas para calcular."],
    },
  };
}

export function intensidadeDaUF(_uf: UFSigla, _culturaId?: string): number {
  return 0;
}

export function resumoRegional(uf: UFSigla): ResumoRegional {
  const info = infoDaUF(uf) ?? infoDaUF("SP")!;
  return {
    uf: info,
    producao: producaoDaUF(uf),
    solo: soloDaUF(uf),
    seguro: seguroDaUF(uf),
    irrigacao: irrigacaoDaUF(uf),
    precos: precosDaUF(uf, null),
    canais: canaisDaUF(uf),
    oportunidade: oportunidadeDaUF(uf),
  };
}

/** Alias pedido no enunciado: insights por UF, mesma assinatura da futura API. */
export function insightsDaUF(uf: UFSigla): ResumoRegional {
  return resumoRegional(uf);
}

