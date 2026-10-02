/**
 * AgroPilot — Login / Onboarding Script
 * Integração com FastAPI (/api/onboarding, /api/produtor) via api.js
 *
 * Fluxo:
 * 1. Login: usuário informa telefone → verifica localStorage → redireciona para index.html
 * 2. Cadastro: nome + telefone → conversa guiada (etapas 1-4) → salva perfil → redireciona
 */

// ─── Config ───────────────────────────────────────────────────────────────────
const API_BASE = window.AGROPILOT_API_URL || "http://localhost:8000";
const MAIN_APP = "../../../index.html"; // caminho relativo para o app principal

// ─── Estado ───────────────────────────────────────────────────────────────────
let currentTab = "login";
let onboardingEtapa = 1;
let perfilParcial = {};
let pendingName = "";
let pendingPhone = "";

// ─── Utils ────────────────────────────────────────────────────────────────────

function $(id) { return document.getElementById(id); }

function formatPhone(value) {
  const digits = value.replace(/\D/g, "").slice(0, 11);
  if (digits.length <= 2) return `(${digits}`;
  if (digits.length <= 7) return `(${digits.slice(0,2)}) ${digits.slice(2)}`;
  if (digits.length <= 11) return `(${digits.slice(0,2)}) ${digits.slice(2,7)}-${digits.slice(7)}`;
  return `(${digits.slice(0,2)}) ${digits.slice(2,7)}-${digits.slice(7,11)}`;
}

function toE164(phone) {
  const digits = phone.replace(/\D/g, "");
  return digits.startsWith("55") ? `+${digits}` : `+55${digits}`;
}

function saveLocalProfile(profile) {
  try { localStorage.setItem("agropilot_profile", JSON.stringify(profile)); } catch {}
}

function loadLocalProfile() {
  try {
    const raw = localStorage.getItem("agropilot_profile");
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

function saveSession(session) {
  try { localStorage.setItem("agropilot_session", JSON.stringify(session)); } catch {}
}

function setLoading(btnId, loading) {
  const btn = $(btnId);
  if (!btn) return;
  const text = btn.querySelector(".btn-text");
  const spinner = btn.querySelector(".btn-spinner");
  btn.disabled = loading;
  if (text) text.style.opacity = loading ? "0.5" : "1";
  if (spinner) spinner.classList.toggle("hidden", !loading);
}

function showError(fieldId, msg) {
  const el = $(fieldId);
  if (el) el.textContent = msg;
  const input = $(fieldId.replace("-error", ""));
  if (input) input.classList.toggle("error", !!msg);
}

function clearError(fieldId) { showError(fieldId, ""); }

// ─── Partículas ───────────────────────────────────────────────────────────────

function initParticles() {
  const container = $("particles");
  if (!container) return;
  for (let i = 0; i < 18; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    const size = Math.random() * 4 + 2;
    p.style.cssText = `
      width:${size}px; height:${size}px;
      left:${Math.random() * 100}%;
      bottom:${-size}px;
      animation-duration:${Math.random() * 12 + 8}s;
      animation-delay:${Math.random() * 8}s;
    `;
    container.appendChild(p);
  }
}

// ─── Tab switching ────────────────────────────────────────────────────────────

function switchTab(tab) {
  currentTab = tab;
  const panels = document.querySelectorAll(".tab-panel");
  const tabs = document.querySelectorAll(".tab-btn");
  const slider = $("tab-slider");

  panels.forEach(p => p.classList.remove("active"));
  tabs.forEach(t => { t.classList.remove("active"); t.setAttribute("aria-selected", "false"); });

  $(`panel-${tab}`).classList.add("active");
  $(`tab-${tab}`).classList.add("active");
  $(`tab-${tab}`).setAttribute("aria-selected", "true");
  if (slider) slider.classList.toggle("right", tab === "register");
}

window.switchTab = switchTab;

// ─── Validação ────────────────────────────────────────────────────────────────

function validatePhone(phone) {
  const digits = phone.replace(/\D/g, "");
  return digits.length >= 10;
}

function validateName(name) {
  return name.trim().length >= 2;
}

// ─── LOGIN ────────────────────────────────────────────────────────────────────

$("form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError("login-phone-error");

  const rawPhone = $("login-phone").value.trim();
  if (!validatePhone(rawPhone)) {
    showError("login-phone-error", "Informe um telefone válido.");
    return;
  }

  const phone = toE164(rawPhone);
  setLoading("btn-login", true);

  // Verifica se já tem perfil local com esse telefone
  const local = loadLocalProfile();
  if (local && local.telefone === phone) {
    saveSession({ id: local.id, nome: local.nome, telefone: phone });
    setTimeout(() => { window.location.href = MAIN_APP; }, 600);
    return;
  }

  // Tenta buscar perfil no backend (aqui usamos telefone como ID para MVP)
  const cleanId = phone.replace(/\D/g, "");
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/produtor/${cleanId}`);
    if (res.ok) {
      const data = await res.json();
      saveLocalProfile(data);
      saveSession({ id: data.id, nome: data.nome, telefone: phone });
      window.location.href = MAIN_APP;
      return;
    }
  } catch {}

  // Não encontrou → redireciona para cadastro
  setLoading("btn-login", false);
  $("login-phone").value = "";
  showError("login-phone-error", "Telefone não encontrado. Faça seu cadastro.");
  setTimeout(() => switchTab("register"), 1200);
});

// Máscara de telefone
["login-phone", "reg-phone"].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.addEventListener("input", (e) => {
    const pos = e.target.selectionStart;
    e.target.value = formatPhone(e.target.value);
    const newPos = Math.min(pos + 1, e.target.value.length);
    try { e.target.setSelectionRange(newPos, newPos); } catch {}
  });
});

// ─── CADASTRO — Etapa 1: Nome + Telefone ─────────────────────────────────────

$("form-register").addEventListener("submit", async (e) => {
  e.preventDefault();
  clearError("reg-name-error");
  clearError("reg-phone-error");

  const name = $("reg-name").value.trim();
  const rawPhone = $("reg-phone").value.trim();

  let valid = true;
  if (!validateName(name)) { showError("reg-name-error", "Informe seu nome (mínimo 2 letras)."); valid = false; }
  if (!validatePhone(rawPhone)) { showError("reg-phone-error", "Informe um telefone válido."); valid = false; }
  if (!valid) return;

  pendingName = name;
  pendingPhone = toE164(rawPhone);
  perfilParcial = { nome: name, telefone: pendingPhone };

  setLoading("btn-register", true);

  // Chama onboarding etapa 1
  const resultado = await callOnboarding(1, name);

  setLoading("btn-register", false);

  // Transição para chat guiado
  $("register-step-1").classList.remove("active");
  $("register-step-onboarding").classList.add("active");
  $("register-switch-hint").style.display = "none";

  updateProgress(2);
  appendBotBubble(resultado.pergunta);
  onboardingEtapa = resultado.proximo_passo;
});

// ─── CADASTRO — Etapas do Chat Onboarding ────────────────────────────────────

$("btn-onboard-send").addEventListener("click", sendOnboardAnswer);
$("onboard-answer").addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendOnboardAnswer();
});

async function sendOnboardAnswer() {
  const input = $("onboard-answer");
  const answer = input.value.trim();
  if (!answer) return;

  input.value = "";
  input.disabled = true;
  $("btn-onboard-send").disabled = true;

  appendUserBubble(answer);

  const resultado = await callOnboarding(onboardingEtapa, answer);
  mergePerfilParcial(resultado.perfil_parcial);
  updateProgress(resultado.proximo_passo);

  // Última etapa → finaliza cadastro
  if (resultado.proximo_passo >= 5) {
    appendBotBubble(resultado.pergunta);
    await finalizeRegistration();
    return;
  }

  appendBotBubble(resultado.pergunta);
  onboardingEtapa = resultado.proximo_passo;

  input.disabled = false;
  $("btn-onboard-send").disabled = false;
  input.focus();
}

function mergePerfilParcial(partial) {
  if (!partial) return;
  // Interpreta respostas das etapas
  if (partial.municipio) {
    const parts = partial.municipio.split(/[-–,]/);
    perfilParcial.municipio = parts[0]?.trim() || partial.municipio;
    perfilParcial.uf = parts[1]?.trim().toUpperCase() || "BR";
  }
  if (partial.culturas) {
    perfilParcial.culturas = partial.culturas;
    perfilParcial.lavouras = partial.culturas.split(/[,e ]+/).filter(Boolean).map(c => ({
      cultura: c.trim().toLowerCase(),
      area_ha: 5,
      solo: 1,
      irrigacao: false,
    }));
  }
  if (partial.area_ha) {
    const ha = parseFloat(partial.area_ha) || 5;
    (perfilParcial.lavouras || []).forEach(l => { l.area_ha = ha; });
  }
  Object.assign(perfilParcial, partial);
}

async function finalizeRegistration() {
  // Salva perfil completo
  const payload = {
    nome: perfilParcial.nome || pendingName,
    telefone: pendingPhone,
    codigo_ibge: perfilParcial.codigo_ibge || "0000000",
    municipio: perfilParcial.municipio || "Não informado",
    uf: perfilParcial.uf || "BR",
    lavouras: perfilParcial.lavouras || [],
    preferencias: { notificacoes: true, horario: "06:00" },
  };

  let produtorId = "local-" + Date.now();
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/produtor`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      produtorId = data.id || produtorId;
    }
  } catch {}

  saveLocalProfile({ ...payload, id: produtorId });
  saveSession({ id: produtorId, nome: payload.nome, telefone: pendingPhone });

  // Pequeno delay para o usuário ler a última mensagem
  setTimeout(() => { window.location.href = MAIN_APP; }, 2200);
}

// ─── Chat UI helpers ──────────────────────────────────────────────────────────

function appendBotBubble(text) {
  const container = $("chat-onboard");
  const el = document.createElement("div");
  el.className = "chat-bubble bubble-bot";
  el.textContent = text;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

function appendUserBubble(text) {
  const container = $("chat-onboard");
  const el = document.createElement("div");
  el.className = "chat-bubble bubble-user";
  el.textContent = text;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
}

// ─── Progresso ────────────────────────────────────────────────────────────────

function updateProgress(nextStep) {
  const bar = $("progress-bar");
  const label = $("progress-label");
  const total = 4;
  const current = Math.min(nextStep - 1, total);
  const pct = Math.round((current / total) * 100);
  if (bar) bar.style.width = `${pct}%`;
  if (label) label.textContent = `Passo ${current} de ${total}`;
}

// ─── API calls ────────────────────────────────────────────────────────────────

async function fetchWithTimeout(url, options = {}, ms = 7000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  try {
    const res = await fetch(url, { ...options, signal: ctrl.signal });
    clearTimeout(timer);
    return res;
  } catch (err) {
    clearTimeout(timer);
    throw err;
  }
}

async function callOnboarding(etapa, resposta) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/api/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telefone: pendingPhone, etapa, resposta }),
    });
    if (res.ok) return await res.json();
  } catch {}

  // Fallback offline
  return mockOnboarding(etapa, resposta);
}

function mockOnboarding(etapa, resposta) {
  const mocks = {
    1: { proximo_passo: 2, pergunta: `Prazer, ${resposta}! Me manda sua cidade e estado (ex: Rio Verde - GO).`, perfil_parcial: { nome: resposta } },
    2: { proximo_passo: 3, pergunta: "Ótimo! Quais culturas você planta? (ex: soja, milho, feijão)", perfil_parcial: { municipio: resposta } },
    3: { proximo_passo: 4, pergunta: "Qual o tamanho aproximado da sua área plantada em hectares?", perfil_parcial: { culturas: resposta } },
    4: { proximo_passo: 5, pergunta: `Tudo certo! Cadastro concluído, ${perfilParcial.nome}. Preparando seu AgroPilot... 🌱`, perfil_parcial: { status: "concluido" } },
  };
  return mocks[etapa] || mocks[4];
}

// ─── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  initParticles();

  // Se já tem sessão válida, vai direto pro app
  try {
    const session = JSON.parse(localStorage.getItem("agropilot_session") || "null");
    if (session?.id) {
      window.location.href = MAIN_APP;
      return;
    }
  } catch {}
});
