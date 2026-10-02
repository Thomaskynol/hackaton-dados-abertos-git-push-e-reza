/**
 * Camada HTTP do AgroPilot — fetch only, sem dependências novas.
 * Espelha o contrato aditivo (docs/arquitetura-mapa-cadastro-chat-memoria.md §4):
 * POST /api/produtor, GET /api/regiao, POST /api/chat(+/stream),
 * POST/GET /api/sessoes, GET /api/sessoes/{id}/mensagens.
 * Rotas ainda inexistentes no backend viram throw — o chamador cai no
 * fallback honesto local (nunca número inventado).
 */

export function apiUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  return raw.replace(/\/+$/, "");
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
    headers: { "Content-Type": "application/json" },
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
  const res = await fetch(`${apiUrl()}/api/regiao?${q.toString()}`);
  if (!res.ok) throw new Error(`GET /api/regiao ${res.status}`);
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
    headers: { "Content-Type": "application/json" },
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
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
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
  const res = await fetch(`${apiUrl()}/api/sessoes?${q.toString()}`);
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error(`POST /api/sessoes ${res.status}`);
  return (await res.json()) as Sessao;
}

/** GET /api/sessoes/{id}/mensagens — turnos asc (bruto; mapeado na page). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function getMensagens(sessao_id: string): Promise<any[]> {
  const res = await fetch(`${apiUrl()}/api/sessoes/${sessao_id}/mensagens`);
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
