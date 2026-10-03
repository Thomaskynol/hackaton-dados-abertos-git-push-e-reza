/**
 * Camada HTTP do AgroPilot — fetch only, sem dependências novas.
 * Espelha o contrato aditivo (docs/arquitetura-mapa-cadastro-chat-memoria.md §4):
 * POST /api/produtor, GET /api/regiao, POST /api/chat(+/stream),
 * POST/GET /api/sessoes, GET /api/sessoes/{id}/mensagens.
 * Rotas ainda inexistentes no backend viram throw — o chamador cai no
 * fallback honesto local (nunca número inventado).
 */

export function apiUrl(): string {
  // 127.0.0.1 (não "localhost") de propósito: no Windows "localhost" pode
  // resolver primeiro para IPv6 (::1); se a API escuta só em IPv4, o fetch do
  // navegador falha e a tela mostra "sem conexão" sem motivo. 127.0.0.1 evita isso.
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  return raw.replace(/\/+$/, "");
}

/* ---------------- sessão (token Bearer) ---------------- */

const CHAVE_TOKEN = "agropilot:token";

/** Lê o token da sessão (localStorage). Vazio quando deslogado. */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(CHAVE_TOKEN);
  } catch {
    return null;
  }
}

/** Grava (ou apaga, com null) o token da sessão. */
export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) localStorage.setItem(CHAVE_TOKEN, token);
    else localStorage.removeItem(CHAVE_TOKEN);
  } catch {
    /* storage indisponível: segue sem persistir */
  }
}

/** Headers com Authorization: Bearer quando há token. Mescla com os passados. */
export function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...(extra ?? {}) };
  const t = getToken();
  if (t) h["Authorization"] = `Bearer ${t}`;
  return h;
}

/* ---------------- produtor ---------------- */

export interface ProdutorPayload {
  nome: string;
  telefone: string;
  municipio: string;
  uf: string;
  cod_ibge: string;
  cultura: string;
}

export interface ProdutorCriado {
  id: string;
  [k: string]: unknown;
}

/** POST /api/produtor — traduz cod_ibge/lavoura do front p/ ProdutorCreate do back. */
export async function postProdutor(p: ProdutorPayload): Promise<ProdutorCriado> {
  const res = await fetch(`${apiUrl()}/api/produtor`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      nome: p.nome,
      telefone: p.telefone,
      codigo_ibge: p.cod_ibge,
      municipio: p.municipio,
      uf: p.uf,
      lavouras: [{ cultura: p.cultura, area_ha: 0, solo: 1, irrigacao: false }],
    }),
  });
  if (!res.ok) throw new Error(`POST /api/produtor ${res.status}`);
  const data = (await res.json()) as Record<string, unknown>;
  const id = data["id"] ?? data["produtor_id"] ?? "local";
  return { ...data, id: String(id) };
}

/* ---------------- conta (signup/login/GET/PATCH) ---------------- */

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface ContaLavoura {
  cultura: string;
  area_ha: number | null;
  solo?: string | number | null;
  irrigacao?: boolean | null;
  [k: string]: unknown;
}

export interface Conta {
  id: string;
  nome: string;
  telefone: string;
  municipio: string;
  uf: string;
  cod_ibge: string;
  codigo_ibge?: string;
  lavouras: ContaLavoura[];
  onboardingConcluido: boolean;
  hectares_total?: number;
  solo_inferido?: string | null;
  /** token de sessão (signup/login o devolvem; guardado via setToken). */
  token?: string;
  /** true quando a conta tem PIN definido. */
  tem_pin?: boolean;
  [k: string]: unknown;
}

export interface ContaPatch {
  nome?: string;
  municipio?: string;
  uf?: string;
  cod_ibge?: string;
  codigo_ibge?: string;
  lavouras?: Array<{
    cultura: string;
    area_ha: number | null;
    solo?: string | number | null;
    irrigacao?: boolean | null;
  }>;
  onboardingConcluido?: boolean;
}

async function erroApi(res: Response, rota: string): Promise<never> {
  let detalhe = "";
  try {
    const j = (await res.json()) as Record<string, unknown>;
    const d = j["detail"];
    if (typeof d === "string") detalhe = d;
  } catch {
    /* corpo sem JSON: segue só com o status */
  }
  throw new ApiError(res.status, `${rota} ${res.status}${detalhe ? `: ${detalhe}` : ""}`);
}

function normalizarConta(data: Record<string, unknown>): Conta {
  const id = data["id"] ?? data["produtor_id"] ?? "";
  return {
    ...data,
    id: String(id),
    nome: typeof data["nome"] === "string" ? (data["nome"] as string) : "",
    telefone: typeof data["telefone"] === "string" ? (data["telefone"] as string) : "",
    municipio: typeof data["municipio"] === "string" ? (data["municipio"] as string) : "",
    uf: typeof data["uf"] === "string" ? (data["uf"] as string) : "",
    cod_ibge: String(data["cod_ibge"] ?? data["codigo_ibge"] ?? ""),
    lavouras: Array.isArray(data["lavouras"]) ? (data["lavouras"] as ContaLavoura[]) : [],
    onboardingConcluido: Boolean(data["onboardingConcluido"]),
  } as Conta;
}

/** POST /api/produtor/signup {telefone,nome,pin} -> 201 conta+token; 409 existe; 422 PIN. */
export async function signup(telefone: string, nome: string, pin?: string): Promise<Conta> {
  const res = await fetch(`${apiUrl()}/api/produtor/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telefone, nome, ...(pin ? { pin } : {}) }),
  });
  if (!res.ok) await erroApi(res, "POST /api/produtor/signup");
  const conta = normalizarConta((await res.json()) as Record<string, unknown>);
  if (conta.token) setToken(conta.token); // signup entra logado
  return conta;
}

/** POST /api/produtor/login {telefone,pin?} -> 200 conta+token; 404 sem conta; 401 PIN; 422 falta PIN. */
export async function login(telefone: string, pin?: string): Promise<Conta> {
  const res = await fetch(`${apiUrl()}/api/produtor/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telefone, ...(pin ? { pin } : {}) }),
  });
  if (!res.ok) await erroApi(res, "POST /api/produtor/login");
  const conta = normalizarConta((await res.json()) as Record<string, unknown>);
  if (conta.token) setToken(conta.token);
  return conta;
}

/** POST /api/produtor/logout — revoga o token no servidor e limpa o local. */
export async function logout(): Promise<void> {
  try {
    await fetch(`${apiUrl()}/api/produtor/logout`, {
      method: "POST",
      headers: authHeaders(),
    });
  } catch {
    /* mesmo offline, limpamos o token local abaixo */
  }
  setToken(null);
}

/** GET /api/produtor/me — conta do dono do token. 401 se sessão inválida. */
export async function getMe(): Promise<Conta> {
  const res = await fetch(`${apiUrl()}/api/produtor/me`, { headers: authHeaders() });
  if (!res.ok) await erroApi(res, "GET /api/produtor/me");
  return normalizarConta((await res.json()) as Record<string, unknown>);
}

/* ---------------- cadastro por chat (onboarding guiado) ---------------- */

export interface OnboardingResposta {
  proximo_passo: number;
  pergunta: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  perfil_parcial?: Record<string, any>;
  erro?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  resumo?: Record<string, any> | null;
  fonte?: string;
}

/** POST /api/onboarding — uma etapa do cadastro por chat (extração real no back). */
export async function onboardingChat(args: {
  etapa: number;
  resposta: string;
  produtor_id?: string | null;
  telefone?: string | null;
}): Promise<OnboardingResposta> {
  const res = await fetch(`${apiUrl()}/api/onboarding`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      etapa: args.etapa,
      resposta: args.resposta,
      ...(args.produtor_id ? { produtor_id: args.produtor_id } : {}),
      ...(args.telefone ? { telefone: args.telefone } : {}),
    }),
  });
  if (!res.ok) await erroApi(res, "POST /api/onboarding");
  return (await res.json()) as OnboardingResposta;
}

/** GET /api/produtor/{id} — conta cheia (exige sessão). */
export async function getConta(id: string): Promise<Conta> {
  const res = await fetch(`${apiUrl()}/api/produtor/${encodeURIComponent(id)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) await erroApi(res, "GET /api/produtor/{id}");
  return normalizarConta((await res.json()) as Record<string, unknown>);
}

/** PATCH /api/produtor/{id} — atualização parcial (exige sessão). */
export async function patchConta(id: string, patch: ContaPatch): Promise<Conta> {
  const res = await fetch(`${apiUrl()}/api/produtor/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(patch),
  });
  if (!res.ok) await erroApi(res, "PATCH /api/produtor/{id}");
  return normalizarConta((await res.json()) as Record<string, unknown>);
}

/* ---------------- regiao ---------------- */

/** GET /api/regiao?uf=&ibge=&cultura= — retorna o agregado bruto (normalizado na page). */
export async function getRegiao(
  uf: string,
  ibge?: string,
  cultura?: string | null,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<any> {
  const q = new URLSearchParams({ uf });
  if (ibge) q.set("ibge", ibge);
  if (cultura) q.set("cultura", cultura);
  const res = await fetch(`${apiUrl()}/api/regiao?${q.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/regiao ${res.status}`);
  return res.json();
}

/* ---------------- precos (consultor comercial) ---------------- */

import type { PrecoRef } from "./types";

export interface CanalComercial {
  id: string;
  categoria: string;
  descricao: string;
  destaque?: string;
}

export interface CanaisComerciais {
  uf: string;
  estado: string;
  programas: string[];
  canais: CanalComercial[];
  detalhe: string;
  fonte: { nome: string; periodo?: string; url?: string; limitacoes?: string[] };
}

export interface AnaliseComercial {
  texto: string;
  /** "ia" quando gerada por LLM, "heuristica" quando montada dos dados. */
  origem: "ia" | "heuristica";
  fonte: string;
}

export interface PontoSerie {
  ano: number;
  valor: number;
  unidade: string;
}

export interface ProjecaoPreco {
  ano: number;
  valor_estimado: number;
  faixa_min: number;
  faixa_max: number;
  unidade: string;
  /** "ia" quando a previsão veio do modelo; "tendencia" quando foi regressão. */
  origem?: "ia" | "tendencia";
  /**
   * Regressão embutida na projeção da IA, para o card mostrar os dois
   * números lado a lado: o da IA (leitura) e o da reta (determinístico).
   */
  valor_tendencia?: number | null;
  /** Frase curta explicando o porquê (quando a IA gera). */
  racional?: string | null;
}

export interface TendenciaPreco {
  estado: "disponivel" | "insuficiente";
  cultura?: string;
  uf?: string;
  unidade?: string;
  ultimo?: PontoSerie;
  media_recente?: number;
  menor?: PontoSerie;
  maior?: PontoSerie;
  direcao?: "subindo" | "caindo" | "estável";
  /**
   * Variação do ÚLTIMO ano em % (ex.: -19.4), calculada do dado oficial.
   * É o que manda no selo `direcao`. Bug corrigido: antes o selo vinha da
   * reta de 8 anos, que é NOMINAL e sobe com a inflação em todas as
   * culturas — o feijão de SP, que CAIU 19,4%, aparecia como "subindo".
   */
  variacao_ultimo_ano?: number | null;
  /**
   * Inclinação NOMINAL da reta em %/ano. Contexto histórico apenas:
   * preço nominal subindo NÃO é preço real subindo.
   */
  variacao_media_anual?: number | null;
  projecao?: ProjecaoPreco | null;
  /**
   * Passo 5: regressão SEMPRE presente, mesmo com a IA ligada. É o número
   * determinístico e auditável — a IA pode mudar entre versões do modelo,
   * esta não. Sem ela, desligar a IA deixaria o card sem número nenhum.
   */
  projecao_tendencia?: ProjecaoPreco | null;
  serie?: PontoSerie[];
  fonte?: string;
  /** Ex.: "valor médio ANUAL por UF" — evita o produtor achar que é cotação diária. */
  periodicidade?: string;
  aviso?: string;
}

export interface PrecosResposta {
  uf: { sigla: string; nome: string };
  cultura: string;
  precos: PrecoRef[];
  canais: CanaisComerciais;
  tendencia?: TendenciaPreco;
  analise: AnaliseComercial;
}

/** GET /api/precos?uf=&cultura= — preços reais + canais + análise comercial. */
export async function getPrecos(
  uf: string,
  cultura?: string | null,
): Promise<PrecosResposta> {
  const q = new URLSearchParams({ uf });
  if (cultura) q.set("cultura", cultura);
  const res = await fetch(`${apiUrl()}/api/precos?${q.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/precos ${res.status}`);
  return res.json();
}

/* ---------------- alertas ---------------- */

export interface AlertaReal {
  id: string;
  tipo: string;
  severidade: "alta" | "media" | "baixa";
  mensagem: string;
  fonte: string;
  /** Clima traz título próprio (ex: "Risco de geada"). */
  titulo?: string;
  local?: string | null;
  data_extracao?: string;
  enviado_em?: string;
  lido?: boolean;
}

export interface AlertasResposta {
  alertas: AlertaReal[];
  uf: string;
  vazio_ok: boolean;
  data: string;
}

export interface EventoClima {
  tipo: string;
  titulo?: string;
  severidade: "alta" | "media" | "baixa";
  mensagem: string;
  janela?: string;
}

export interface DecisaoDia {
  resposta: string;
  origem: "ia" | "regras";
  severidade: "alta" | "media" | "baixa" | "info";
  acoes: string[];
  fontes: string[];
  local: { nome: string | null; uf: string | null };
  cultura: string;
  tem_clima: boolean;
  eventos_clima: EventoClima[];
  data: string;
}

/** GET /api/decisao-dia — a decisão do dia (clima+ZARC+preço+memória) por IA. */
export async function getDecisaoDia(
  args: { produtor_id?: string | null; uf?: string | null; ibge?: string | null; cultura?: string | null },
): Promise<DecisaoDia> {
  const q = new URLSearchParams();
  if (args.produtor_id) q.set("produtor_id", args.produtor_id);
  if (args.uf) q.set("uf", args.uf);
  if (args.ibge) q.set("ibge", args.ibge);
  if (args.cultura) q.set("cultura", args.cultura);
  const res = await fetch(`${apiUrl()}/api/decisao-dia?${q.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/decisao-dia ${res.status}`);
  return res.json();
}

/* ---------------- radar (3 cartões com dado estruturado) ---------------- */

export interface RadarLinha {
  rotulo: string;
  valor: string;
  aviso?: boolean;
}

export interface RadarDestaque {
  rotulo: string;
  valor: string;
  dica?: string;
}

export interface RadarFonte {
  nome: string;
  periodo?: string;
  url?: string;
  limitacoes?: string[];
}

export interface RadarBloco {
  estado: "favoravel" | "atencao" | "pendente" | "sem_dado" | "informativo";
  titulo: string;
  detalhe: string;
  linhas?: RadarLinha[];
  destaques?: RadarDestaque[];
  leitura?: string;
  fonte: RadarFonte;
}

export interface RadarResposta {
  clima: RadarBloco;
  zarc: RadarBloco;
  psr: RadarBloco;
  uf: string;
  ibge: string | null;
  cultura: string | null;
  data: string;
}

/** GET /api/radar?uf=&ibge=&cultura=&solo= — os 3 cartões do Radar, com dado real. */
export async function getRadar(
  uf: string,
  ibge?: string | null,
  cultura?: string | null,
  solo?: string | null,
): Promise<RadarResposta> {
  const q = new URLSearchParams({ uf });
  if (ibge) q.set("ibge", ibge);
  if (cultura) q.set("cultura", cultura);
  if (solo) q.set("solo", solo);
  const res = await fetch(`${apiUrl()}/api/radar?${q.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/radar ${res.status}`);
  return res.json();
}

/** GET /api/alertas?ibge=&cultura=&uf= — avisos reais (clima + janela ZARC + risco PSR). */
export async function getAlertas(
  uf: string,
  ibge?: string | null,
  cultura?: string | null,
): Promise<AlertasResposta> {
  const q = new URLSearchParams({ uf });
  if (ibge) q.set("ibge", ibge);
  if (cultura) q.set("cultura", cultura);
  const res = await fetch(`${apiUrl()}/api/alertas?${q.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/alertas ${res.status}`);
  return res.json();
}

/* ---------------- chat ---------------- */

export interface ChatMeta {
  intencao?: string;
  fonte?: string;
  data_extracao?: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dados?: any;
}

export interface ChatResposta extends ChatMeta {
  resposta: string;
  erro?: string;
  mensagem?: string;
  sugestoes?: string[];
}

/** POST /api/chat — envia produtor_id + sessao_id? + mensagem. */
export async function postChat(
  produtor_id: string,
  mensagem: string,
  sessao_id?: string | null,
): Promise<ChatResposta> {
  const res = await fetch(`${apiUrl()}/api/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      produtor_id,
      mensagem,
      ...(sessao_id ? { sessao_id } : {}),
    }),
  });
  if (!res.ok) throw new Error(`POST /api/chat ${res.status}`);
  const data = (await res.json()) as ChatResposta;
  if (data.erro && !data.resposta) throw new Error(data.erro);
  return data;
}

/**
 * POST /api/chat/stream — SSE com eventos meta/delta/done.
 * meta: {intencao, fonte, data_extracao, dados}; delta: {texto}; done: {}.
 */
export async function postChatStream(
  args: { produtor_id: string; mensagem: string; sessao_id?: string | null },
  cb: {
    onMeta?: (m: ChatMeta) => void;
    onDelta: (texto: string) => void;
    onDone?: () => void;
  },
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${apiUrl()}/api/chat/stream`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json", Accept: "text/event-stream" }),
    body: JSON.stringify({
      produtor_id: args.produtor_id,
      mensagem: args.mensagem,
      ...(args.sessao_id ? { sessao_id: args.sessao_id } : {}),
    }),
    signal,
  });
  if (!res.ok) throw new Error(`POST /api/chat/stream ${res.status}`);
  if (!res.body) throw new Error("stream sem corpo");

  const tratar = (bloco: string) => {
    let ev = "";
    const datas: string[] = [];
    for (const l of bloco.split("\n")) {
      if (l.startsWith("event:")) ev = l.slice(6).trim();
      else if (l.startsWith("data:")) datas.push(l.slice(5).trim());
    }
    if (!datas.length) return;
    const bruto = datas.join("\n");
    let json: Record<string, unknown> | null = null;
    try {
      json = JSON.parse(bruto) as Record<string, unknown>;
    } catch {
      json = null;
    }
    if (ev === "meta") {
      cb.onMeta?.((json ?? {}) as ChatMeta);
    } else if (ev === "delta") {
      const t =
        typeof json?.["texto"] === "string"
          ? (json["texto"] as string)
          : typeof json?.["delta"] === "string"
            ? (json["delta"] as string)
            : null;
      cb.onDelta(t ?? (!json ? bruto : ""));
    } else if (ev === "done" || ev === "[DONE]") {
      cb.onDone?.();
    } else if (!ev && json && typeof json["texto"] === "string") {
      cb.onDelta(json["texto"] as string);
    } else if (json && typeof json["resposta"] === "string") {
      cb.onDelta(json["resposta"] as string);
    }
  };

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const partes = buf.split("\n\n");
    buf = partes.pop() ?? "";
    for (const p of partes) if (p.trim()) tratar(p);
  }
  buf += dec.decode();
  if (buf.trim()) tratar(buf);
  cb.onDone?.();
}

/* ---------------- sessoes ---------------- */

export interface Sessao {
  id: string;
  titulo?: string;
  produtor_id?: string;
  uf?: string;
  cod_ibge?: string;
  criado_em?: string;
  atualizado_em?: string;
  [k: string]: unknown;
}

/** GET /api/sessoes?produtor_id= — lista desc (ChatGPT-style). */
export async function listSessoes(produtor_id: string): Promise<Sessao[]> {
  const q = new URLSearchParams({ produtor_id });
  const res = await fetch(`${apiUrl()}/api/sessoes?${q.toString()}`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/sessoes ${res.status}`);
  const data = (await res.json()) as unknown;
  if (Array.isArray(data)) return data as Sessao[];
  if (data && typeof data === "object") {
    const rec = data as Record<string, unknown>;
    for (const k of ["sessoes", "items", "sessions"]) {
      if (Array.isArray(rec[k])) return rec[k] as Sessao[];
    }
  }
  return [];
}

/** POST /api/sessoes — cria (título = 40 primeiros chars quando omitido no back). */
export async function createSessao(input: {
  produtor_id: string;
  titulo?: string;
  uf?: string;
  cod_ibge?: string;
}): Promise<Sessao> {
  const res = await fetch(`${apiUrl()}/api/sessoes`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`POST /api/sessoes ${res.status}`);
  return (await res.json()) as Sessao;
}

/** GET /api/sessoes/{id}/mensagens — turnos asc (bruto; mapeado na page). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function getMensagens(sessao_id: string): Promise<any[]> {
  const res = await fetch(`${apiUrl()}/api/sessoes/${sessao_id}/mensagens`, { headers: authHeaders() });
  if (!res.ok) throw new Error(`GET /api/sessoes/mensagens ${res.status}`);
  const data = (await res.json()) as unknown;
  if (Array.isArray(data)) return data;
  if (data && typeof data === "object") {
    const rec = data as Record<string, unknown>;
    for (const k of ["mensagens", "items", "messages"]) {
      if (Array.isArray(rec[k])) return rec[k] as unknown[];
    }
  }
  return [];
}
