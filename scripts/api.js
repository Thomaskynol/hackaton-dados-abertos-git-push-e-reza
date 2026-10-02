/**
 * AgroPilot 24/7 — Camada de Serviço de API
 * Conecta o frontend à FastAPI do Cauê seguindo o CONTRATO_API.md.
 *
 * Estratégia: API-first com fallback offline gracioso.
 * Se o backend não estiver disponível, usa os dados locais de data.js.
 */

const API_BASE_URL = window.AGROPILOT_API_URL || "http://localhost:8000";

// Timeout em ms para chamadas curtas (health etc)
const REQUEST_TIMEOUT_MS = 8000;
// Chat não-stream pode esperar LLM (~22s+): sem abort prematuro
const CHAT_TIMEOUT_MS = 120000;

// Estado de conectividade
let _backendOnline = null; // null = não verificado, true/false = verificado

// ─── Utilitários ─────────────────────────────────────────────────────────────

async function _fetchWithTimeout(url, options = {}, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });
    clearTimeout(timer);
    return response;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function _json(response) {
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  return response.json();
}

// ─── Health Check ─────────────────────────────────────────────────────────────

/**
 * Verifica se o backend está online.
 * @returns {Promise<boolean>}
 */
export async function checkHealth() {
  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/health`);
    const data = await _json(res);
    _backendOnline = data.status === "ok";
  } catch {
    _backendOnline = false;
  }

  // Atualiza badge de status no header
  _updateStatusBadge(_backendOnline);
  return _backendOnline;
}

export function isBackendOnline() {
  return _backendOnline === true;
}

function _updateStatusBadge(online) {
  const badge = document.getElementById("backend-status-badge");
  if (!badge) return;
  badge.textContent = online ? "API Online" : "Modo Offline";
  badge.className = `backend-badge ${online ? "badge-online" : "badge-offline"}`;
}

// ─── Onboarding / Cadastro ────────────────────────────────────────────────────

/**
 * Envia uma etapa do onboarding conversacional.
 * POST /api/onboarding
 * @param {string} telefone
 * @param {number} etapa
 * @param {string} resposta
 * @returns {Promise<{proximo_passo: number, pergunta: string, perfil_parcial: object}>}
 */
export async function postOnboarding(telefone, etapa, resposta) {
  if (!isBackendOnline()) {
    return _mockOnboarding(etapa, resposta);
  }

  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/onboarding`, {
      method: "POST",
      body: JSON.stringify({ telefone, etapa, resposta }),
    });
    return await _json(res);
  } catch (err) {
    console.warn("[AgroPilot API] onboarding falhou, usando mock:", err.message);
    return _mockOnboarding(etapa, resposta);
  }
}

function _mockOnboarding(etapa, resposta) {
  const mocks = {
    1: {
      proximo_passo: 2,
      pergunta: `Prazer, ${resposta}! Me manda sua cidade e estado (ex: Araraquara - SP).`,
      perfil_parcial: { nome: resposta },
    },
    2: {
      proximo_passo: 3,
      pergunta: "Show! Quais culturas você planta na sua propriedade? (ex: uva, tomate, feijão)",
      perfil_parcial: { municipio: resposta },
    },
    3: {
      proximo_passo: 4,
      pergunta: "Qual o tamanho aproximado da sua área plantada em hectares?",
      perfil_parcial: { culturas: resposta },
    },
    4: {
      proximo_passo: 5,
      pergunta: "Cadastro concluído! Agora você receberá alertas climáticos e recomendações direto por aqui. 🌱",
      perfil_parcial: { status: "concluido" },
    },
  };
  return mocks[etapa] || mocks[4];
}

// ─── Produtor ─────────────────────────────────────────────────────────────────

/**
 * Busca perfil do produtor por ID.
 * GET /api/produtor/{id}
 * @param {string} produtorId
 * @returns {Promise<object>}
 */
export async function getProdutor(produtorId) {
  if (!isBackendOnline()) return _getMockProdutor();

  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/produtor/${produtorId}`);
    return await _json(res);
  } catch (err) {
    console.warn("[AgroPilot API] getProdutor falhou:", err.message);
    return _getMockProdutor();
  }
}

/**
 * Cria ou atualiza o perfil do produtor.
 * POST /api/produtor
 * @param {object} payload
 * @returns {Promise<{id: string, mensagem: string, ok: boolean}>}
 */
export async function postProdutor(payload) {
  if (!isBackendOnline()) {
    const id = "local-" + Date.now();
    _saveLocalProfile({ ...payload, id });
    return { id, mensagem: "Perfil salvo localmente", ok: true };
  }

  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/produtor`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const data = await _json(res);
    _saveLocalProfile({ ...payload, id: data.id });
    return data;
  } catch (err) {
    console.warn("[AgroPilot API] postProdutor falhou:", err.message);
    const id = "local-" + Date.now();
    _saveLocalProfile({ ...payload, id });
    return { id, mensagem: "Perfil salvo localmente (offline)", ok: true };
  }
}

function _getMockProdutor() {
  const local = _loadLocalProfile();
  if (local) return local;
  return {
    id: "abc123",
    nome: "Seu Sebastião",
    telefone: "+5562999999999",
    codigo_ibge: "5218805",
    municipio: "Rio Verde",
    uf: "GO",
    lavouras: [{ cultura: "soja", area_ha: 12, solo: 2, irrigacao: false }],
    preferencias: { notificacoes: true, horario: "06:00" },
    criado_em: new Date().toISOString(),
  };
}

// ─── Chat / Copiloto ──────────────────────────────────────────────────────────

/**
 * Envia mensagem ao copiloto e recebe resposta estruturada.
 * POST /api/chat
 * @param {string} produtorId
 * @param {string} mensagem
 * @returns {Promise<object>} ChatResponseSuccess | ChatResponseError
 */
export async function postChat(produtorId, mensagem) {
  if (!isBackendOnline()) {
    return _mockChat(mensagem);
  }

  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/chat`, {
      method: "POST",
      body: JSON.stringify({ produtor_id: produtorId, mensagem }),
    }, CHAT_TIMEOUT_MS);
    return await _json(res);
  } catch (err) {
    console.warn("[AgroPilot API] postChat falhou, usando mock:", err.message);
    return _mockChat(mensagem);
  }
}

/**
 * Chat em streaming (SSE): POST /api/chat/stream sem timeout/abort.
 * Eventos: meta {intencao,fonte,...}, delta {texto}, message (JSON único p/ intents simples), done.
 * @param {string} produtorId
 * @param {string} mensagem
 * @param {{onMeta?: Function, onToken?: Function}} cbs
 * @returns {Promise<{resposta: string, meta: object|null}>}
 */
export async function postChatStream(produtorId, mensagem, { onMeta, onToken } = {}) {
  const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ produtor_id: produtorId, mensagem }),
  });
  if (!res.ok || !res.body) {
    throw new Error(`HTTP ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let meta = null;
  let texto = "";
  let unico = null;
  let curEvent = "message";

  const dispatch = (rawEvent, rawData) => {
    let data;
    try { data = JSON.parse(rawData); } catch { return; }
    if (rawEvent === "meta") {
      meta = data;
      if (onMeta) onMeta(data);
    } else if (rawEvent === "delta") {
      const t = data.texto || "";
      texto += t;
      if (onToken) onToken(t);
    } else if (rawEvent === "message") {
      unico = data;
      if (data.resposta) {
        texto = data.resposta;
        if (onToken) onToken(data.resposta);
      }
      if (data.intencao || data.fonte) {
        meta = { intencao: data.intencao, fonte: data.fonte, data_extracao: data.data_extracao, dados: data.dados };
        if (onMeta) onMeta(meta);
      }
    }
    // done: sem ação
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const bloco = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      let ev = curEvent;
      const datas = [];
      for (const linha of bloco.split("\n")) {
        if (linha.startsWith("event:")) ev = linha.slice(6).trim() || "message";
        else if (linha.startsWith("data:")) datas.push(linha.slice(5).trim());
      }
      curEvent = "message";
      if (datas.length) dispatch(ev, datas.join("\n"));
    }
  }
  if (buf.trim()) {
    let ev = curEvent;
    const datas = [];
    for (const linha of buf.split("\n")) {
      if (linha.startsWith("event:")) ev = linha.slice(6).trim() || "message";
      else if (linha.startsWith("data:")) datas.push(linha.slice(5).trim());
    }
    if (datas.length) dispatch(ev, datas.join("\n"));
  }
  return { resposta: texto, meta: unico || meta };
}

function _mockChat(mensagem) {
  const msg = mensagem.toLowerCase();
  const nome = _loadLocalProfile()?.nome || "Produtor";

  if (/\b(oi|olá|ola|bom dia|boa tarde|boa noite)\b/.test(msg)) {
    return {
      resposta: `Olá, ${nome}! Como posso ajudar você hoje na sua lavoura?`,
      intencao: "SAUDACAO",
      fonte: "AgroPilot Local",
      data_extracao: new Date().toISOString().slice(0, 10),
      dados: {},
    };
  }
  if (/míldio|mildio|praga|lagarta|fungo|inseto|defensivo/.test(msg)) {
    return {
      resposta: `${nome}, para míldio em uva, os produtos registrados pelo Agrofit/MAPA são:\n• Produto X (classe II)\n• Produto Z (ORGÂNICO — sem carência)`,
      intencao: "PRAGA",
      fonte: "Agrofit/MAPA",
      data_extracao: new Date().toISOString().slice(0, 10),
      dados: { cultura: "uva", praga: "mildio" },
    };
  }
  if (/plantar|plantio|semente|colher|zarc|janela/.test(msg)) {
    return {
      resposta: `${nome}, para feijão na sua região (solo 1, sequeiro):\n• Melhor janela: decêndios 29-32 (risco 20%)\n• Cultivares indicadas: BRS Estilo, BRS Pérola`,
      intencao: "PLANEJAMENTO",
      fonte: "ZARC 2025/26 + Embrapa",
      data_extracao: new Date().toISOString().slice(0, 10),
      dados: { cultura: "feijao" },
    };
  }
  if (/gear|geada|clima|chuva|temperatura|frio|seca/.test(msg)) {
    return {
      resposta: "Risco moderado de queda brusca de temperatura nas próximas 72h. Monitore suas áreas mais baixas e considere cobertura nas mudas mais novas.",
      intencao: "CLIMA",
      fonte: "INMET + ZARC",
      data_extracao: new Date().toISOString().slice(0, 10),
      dados: { alerta_geada: true, previsao_dias: 3 },
    };
  }
  if (/vend|preço|cotação|paa|pnae|comercializ/.test(msg)) {
    return {
      resposta: "Para comercialização da safra, há chamada pública do PAA aberta. Acesse o portal CONAB para inscrição e preços de referência.",
      intencao: "VENDA",
      fonte: "CONAB / PAA Dados Abertos",
      data_extracao: new Date().toISOString().slice(0, 10),
      dados: {},
    };
  }

  return {
    erro: "NAO_ENTENDI",
    mensagem: "Não consegui entender. Pode reformular?",
    sugestoes: ["Quando planto feijão?", "Minha uva está com míldio", "Vai gear?"],
  };
}

// ─── Alertas ──────────────────────────────────────────────────────────────────

/**
 * Busca alertas ativos do produtor.
 * GET /api/alertas/{id}
 * @param {string} produtorId
 * @returns {Promise<{alertas: Array}>}
 */
export async function getAlertas(produtorId) {
  if (!isBackendOnline()) return _mockAlertas();

  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/alertas/${produtorId}`);
    return await _json(res);
  } catch (err) {
    console.warn("[AgroPilot API] getAlertas falhou:", err.message);
    return _mockAlertas();
  }
}

/**
 * Simula/dispara um alerta climático (para demo/pitch).
 * POST /api/alertas/simular
 * @param {string} produtorId
 * @param {string} tipo — ex: "geada", "seca", "temporal"
 * @returns {Promise<{ok: boolean, alerta: object}>}
 */
export async function simularAlerta(produtorId, tipo) {
  if (!isBackendOnline()) {
    return {
      ok: true,
      alerta: {
        id: `alerta-${tipo}-sim`,
        tipo,
        severidade: "alta",
        mensagem: `Alerta simulado de ${tipo} para sua propriedade. Risco detectado.`,
        fonte: "ZARC + INMET",
        enviado_em: new Date().toISOString(),
        lido: false,
      },
    };
  }

  try {
    const res = await _fetchWithTimeout(`${API_BASE_URL}/api/alertas/simular`, {
      method: "POST",
      body: JSON.stringify({ produtor_id: produtorId, tipo }),
    });
    return await _json(res);
  } catch (err) {
    console.warn("[AgroPilot API] simularAlerta falhou:", err.message);
    return {
      ok: true,
      alerta: {
        id: `alerta-${tipo}-local`,
        tipo,
        severidade: "alta",
        mensagem: `Alerta de ${tipo}: verifique sua lavoura.`,
        fonte: "Local",
        enviado_em: new Date().toISOString(),
        lido: false,
      },
    };
  }
}

function _mockAlertas() {
  return {
    alertas: [
      {
        id: "alerta1",
        tipo: "geada",
        severidade: "alta",
        mensagem: "Geada prevista para quinta (3 dias). Sua lavoura está em risco.",
        fonte: "ZARC + INMET",
        data_extracao: new Date().toISOString().slice(0, 10),
        enviado_em: new Date().toISOString(),
        lido: false,
      },
    ],
  };
}

// ─── LocalStorage helpers ─────────────────────────────────────────────────────

const PROFILE_KEY = "agropilot_profile";
const SESSION_KEY = "agropilot_session";

export function _saveLocalProfile(profile) {
  try {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  } catch {}
}

export function _loadLocalProfile() {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function saveSession(session) {
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {}
}

export function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}

// ─── Inicialização ────────────────────────────────────────────────────────────

// Verifica health ao carregar a página
window.addEventListener("DOMContentLoaded", () => {
  checkHealth().then((online) => {
    console.info(`[AgroPilot API] Backend: ${online ? "✅ online" : "⚠️ offline (modo local)"}`);
  });
});

// Expõe no escopo global para scripts não-módulo
window.AgroAPI = {
  checkHealth,
  isBackendOnline,
  postOnboarding,
  getProdutor,
  postProdutor,
  postChat,
  postChatStream,
  getAlertas,
  simularAlerta,
  saveSession,
  loadSession,
  clearSession,
  _loadLocalProfile,
  _saveLocalProfile,
};
