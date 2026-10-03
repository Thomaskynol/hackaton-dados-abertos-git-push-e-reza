/**
 * Tipos do domínio AgroPilot.
 * Espelham o contrato da API (CONTRATO_API.md) para que, quando o backend
 * entrar, a troca da camada de dados seja direta — sem mexer na UI.
 *
 * NADA aqui carrega número "de pitch". Os dados vivos ficam em store.ts como
 * estado inicial honesto (vazio/neutro) ou vindos do onboarding do usuário.
 */

export type Intencao =
  | "PLANEJAMENTO"
  | "PRAGA"
  | "CLIMA"
  | "VENDA"
  | "PERFIL"
  | "SAUDACAO"
  | "NAO_ENTENDI";

export type UFSigla =
  | "AC" | "AL" | "AM" | "AP" | "BA" | "CE" | "DF" | "ES" | "GO"
  | "MA" | "MG" | "MS" | "MT" | "PA" | "PB" | "PE" | "PI" | "PR"
  | "RJ" | "RN" | "RO" | "RR" | "RS" | "SC" | "SE" | "SP" | "TO";

export type RegiaoBR = "Norte" | "Nordeste" | "Centro-Oeste" | "Sudeste" | "Sul";

/** Os 4 estados honestos do documento mestre (§6.2). Nunca "score 90%". */
export type EstadoEvidencia = "favoravel" | "atencao" | "pendente" | "sem_dado";

/** Estado da camada regional: honesto por padrão até o backend ligar. */
export type EstadoRegional = "disponivel" | "pendente" | "sem_dado";

export interface Lavoura {
  cultura: string;
  area_ha: number | null;
  solo: string | null;
  irrigacao: boolean | null;
}

export interface Perfil {
  id: string | null;
  nome: string;
  telefone: string;
  municipio: string;
  uf: string;
  cod_ibge: string;
  lavouras: Lavoura[];
  onboardingConcluido: boolean;
}

/** Proveniência visível — alimenta o botão "Ver fonte". */
export interface Fonte {
  nome: string;
  periodo?: string;
  extraido_em?: string;
  url?: string;
  limitacoes?: string[];
}

/**
 * Ficha numérica de um card: o número vem compacto ("215 ha") e o
 * `dica` explica em palavras do produtor ("hectares da lavoura").
 * A frase completa fica em `Evidencia.detalhe` — aqui é só o resumo visual.
 */
export interface DestaqueCard {
  rotulo: string;
  valor: string;
  dica?: string;
}

export interface Evidencia {
  tipo: "zarc" | "clima" | "psr" | "sigef" | "ana" | "agrofit";
  estado: EstadoEvidencia;
  titulo: string;
  /** Frase humanizada (já pronta, em português corrido) — nunca "campo · campo". */
  detalhe: string;
  /** Fichas de número opcionais, renderizadas em grade sob a frase. */
  destaques?: DestaqueCard[];
  /** "O que isso significa na prática" — uma linha, opcional. */
  leitura?: string;
  fonte: Fonte;
}

export interface Alerta {
  id: string;
  tipo: "geada" | "veranico" | "excesso_chuva" | "janela_zarc" | "seca";
  severidade: "alta" | "media" | "baixa";
  titulo: string;
  mensagem: string;
  fonte: string;
  quando: string;
  lido: boolean;
}

export type Autor = "usuario" | "copiloto";

export interface Mensagem {
  id: string;
  autor: Autor;
  texto: string;
  intencao?: Intencao;
  fonte?: string;
  evidencias?: Evidencia[];
  horario: string;
}

/* ------------------------------------------------------------------ */
/* Mapa de Oportunidade Regional — tipos (espelham a futura API).      */
/* Quando o backend ligar, só a origem do dado troca; a UI não muda.   */
/* ------------------------------------------------------------------ */

export interface UFInfo {
  sigla: UFSigla;
  nome: string;
  regiao: RegiaoBR;
}

/** "O que a região mais produz" — virá de sigef_agregado (SIGEF/MAPA). */
export interface ProducaoUF {
  uf: UFSigla;
  estado: EstadoRegional;
  culturaTopo: string | null;
  areaHa: number | null;
  producaoT: number | null;
  safraRef: string | null;
  fonte: Fonte;
  /** Sempre true enquanto for demonstração local — obriga rótulo "exemplo". */
  exemplo?: boolean;
}

/** "Força da cultura no seguro" — virá de PSR/SISSER (MAPA) 2016–2024. */
export interface SeguroUF {
  uf: UFSigla;
  estado: EstadoRegional;
  apolices: number | null;
  valorSegurado: number | null;
  culturaTopo: string | null;
  fonte: Fonte;
  exemplo?: boolean;
}

/** "Irrigação disponível" — virá do Atlas Irrigação (ANA). */
export interface IrrigacaoUF {
  uf: UFSigla;
  estado: EstadoRegional;
  areaIrrigadaHa: number | null;
  fonte: Fonte;
  exemplo?: boolean;
}

export type TipoPreco = "pgpm" | "conab_mercado" | "cepea";

export type EstadoPreco = "disponivel" | "pendente" | "sem_cotacao" | "link_externo";

/**
 * Preço de referência honesto. Quando não há número, `valor` é null e a UI
 * mostra "sem cotação disponível" — nunca estimativa. Cepea é só link
 * (restrição de licença: não redistribuir número).
 * `data` espelha `fonte.periodo` (pesquisa/dd/mm ou safra) para a UI ler direto.
 */
export interface PrecoRef {
  tipo: TipoPreco;
  cultura: string;
  uf: UFSigla | null;
  valor: number | null;
  unidade: string;
  fonte: Fonte;
  data: string | null;
  estado: EstadoPreco;
  url?: string;
  aviso?: string;
  exemplo?: boolean;
}

/** Tipo de solo predominante — dica em linguagem do produtor (ver SOLOS). */
export interface SoloRegional {
  uf: UFSigla;
  estado: EstadoRegional;
  soloId: "arenoso" | "media" | "argiloso" | null;
  descricao: string;
  fonte: Fonte;
}

/** Canal de comercialização por CATEGORIA — nunca nome de empresa. */
export interface CanalVenda {
  id: string;
  categoria: string;
  descricao: string;
}

/** Canal de comercialização por CATEGORIA — nunca nome de empresa. */
export interface CanalVenda {
  id: string;
  categoria: string;
  descricao: string;
}

/** Canais públicos de venda (PAA/PNAE) — camada declarada, ainda sem ingestão. */
export interface CanalPublico {
  uf: UFSigla;
  estado: EstadoRegional;
  programas: string[];
  canais: CanalVenda[];
  detalhe: string;
  fonte: Fonte;
}

/** Oportunidade ZARC × SIGEF — estruturada, pendente até o dado ligar. */
export interface OportunidadeRegional {
  uf: UFSigla;
  estado: EstadoRegional;
  culturasAptasPoucoExploradas: string[];
  detalhe: string;
  fonte: Fonte;
}

/** Agregado da tela Mapa para uma UF. Mesma assinatura que a futura GET /api/regiao?uf=. */
export interface ResumoRegional {
  uf: UFInfo;
  producao: ProducaoUF;
  solo: SoloRegional;
  seguro: SeguroUF;
  irrigacao: IrrigacaoUF;
  precos: PrecoRef[];
  canais: CanalPublico;
  oportunidade: OportunidadeRegional;
}

/** Alias pedido no enunciado: card de insights por UF = ResumoRegional. */
export type InsightsRegionais = ResumoRegional;

