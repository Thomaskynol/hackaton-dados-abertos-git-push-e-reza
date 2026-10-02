/**
 * AgroPilot 24/7 — Minimalist, Clean Chatbot Controller
 * Foco em simplicidade, facilidade de uso pelo produtor e clareza visual.
 */

document.addEventListener("DOMContentLoaded", () => {
  let isSunlight = false;
  let audioCtx = null;

  // Elementos da Navbar
  const btnToggleSimMenu = document.getElementById("btn-toggle-sim-menu");
  const simMenu = document.getElementById("sim-menu");
  const btnToggleSunlight = document.getElementById("btn-toggle-sunlight");
  const btnOpenDrawerPill = document.getElementById("btn-open-drawer-pill");
  const btnOpenDrawer = document.getElementById("btn-open-drawer");
  const navFarmerName = document.getElementById("nav-farmer-name");
  const navFarmerCulture = document.getElementById("nav-farmer-culture");
  const navFarmerCity = document.getElementById("nav-farmer-city");

  // Chat Canvas
  const chatMessagesStream = document.getElementById("chat-messages-stream");
  const cleanChatForm = document.getElementById("clean-chat-form");
  const cleanInputField = document.getElementById("clean-input-text");
  const cleanChips = document.querySelectorAll(".clean-chip");
  const btnOpenPhoto = document.getElementById("btn-open-photo");
  const btnCleanMic = document.getElementById("btn-clean-mic");
  const cleanToastContainer = document.getElementById("clean-toast-container");

  // Drawer Lateral
  const drawerBackdrop = document.getElementById("drawer-backdrop");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const drawerFarmName = document.getElementById("drawer-farm-name");
  const drawerFarmMeta = document.getElementById("drawer-farm-meta");
  const drawerSoilVal = document.getElementById("drawer-soil-val");
  const btnAskZarc = document.getElementById("btn-ask-zarc");
  const btnOpenEditProfile = document.getElementById("btn-open-edit-profile");

  // Modais
  const modalPhotoBackdrop = document.getElementById("modal-photo-backdrop");
  const btnClosePhotoModal = document.getElementById("btn-close-photo-modal");
  const modalProfileBackdrop = document.getElementById("modal-profile-backdrop");
  const btnCloseProfileModal = document.getElementById("btn-close-profile-modal");
  const btnCancelProfile = document.getElementById("btn-cancel-profile");
  const formCleanProfile = document.getElementById("form-clean-profile");

  // ==========================================================================
  // 1. Áudio & Fala (Web Audio & SpeechSynthesis)
  // ==========================================================================
  function playCleanBeep(type = "info") {
    try {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtx.state === "suspended") {
        audioCtx.resume();
      }

      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      const freq = type === "critical" ? 440 : 587;
      osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(880, audioCtx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.28);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.28);
    } catch (e) {
      // Audio muted
    }
  }

  function speakText(text) {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = "pt-BR";
      utter.rate = 1.05;
      utter.pitch = 0.95;
      window.speechSynthesis.speak(utter);
    } else {
      showCleanToast("Reproduzindo áudio...");
    }
  }

  // ==========================================================================
  // 2. Notificação Limpa (Toast)
  // ==========================================================================
  function showCleanToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = "clean-toast";

    const icon = type === "critical" ? "⚠️" : (type === "warning" ? "⛈️" : "✓");
    toast.innerHTML = `
      <span style="font-size: 1.1rem;">${icon}</span>
      <div style="flex: 1; color: var(--text-primary); font-weight: 500;">${message}</div>
    `;

    cleanToastContainer.appendChild(toast);
    playCleanBeep(type);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-6px)";
      toast.style.transition = "all 0.25s ease";
      setTimeout(() => toast.remove(), 250);
    }, 4000);
  }

  // ==========================================================================
  // 3. Atualizar Dados do Produtor
  // ==========================================================================
  function updateFarmerContextUI() {
    const p = AGRO_DATA.currentProfile;
    const c = AGRO_DATA.culturas[p.culturaAtual] || AGRO_DATA.culturas.soja;

    const parts = p.nome.trim().split(/\s+/);
    let shortName = parts[0];
    if ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona") && parts[1]) {
      shortName = `${parts[0]} ${parts[1]}`;
    }

    if (navFarmerName) navFarmerName.textContent = shortName;
    if (navFarmerCulture) navFarmerCulture.textContent = `${c.nome.split(" ")[0]} V4`;
    if (navFarmerCity) navFarmerCity.textContent = p.municipio.split(" - ")[0];

    if (drawerFarmName) drawerFarmName.textContent = p.propriedade;
    if (drawerFarmMeta) drawerFarmMeta.textContent = `${p.municipio} • ${p.areaHa} ha`;
    if (drawerSoilVal) drawerSoilVal.textContent = `${p.tipoSolo} (Argiloso CAD > 50mm)`;
  }

  // ==========================================================================
  // 4. Mensagens e Conversação no Chat
  // ==========================================================================
  function appendMessage(sender, text, meta = null) {
    const row = document.createElement("div");
    row.className = `msg-row ${sender === "farmer" ? "user" : "ai"}`;

    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";

    if (sender === "farmer") {
      bubble.innerHTML = `<p>${escapeHTML(text)}</p><div class="msg-timestamp">${timeStr} • ✓✓</div>`;
    } else {
      let content = `<p>${formatMarkdown(text)}</p>`;

      if (meta && meta.audioText) {
        content += `
          <div class="clean-voice-bar">
            <button class="btn-play-clean" data-audio="${escapeAttr(meta.audioText)}" title="Ouvir áudio da resposta">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </button>
            <div class="voice-wave">
              <span class="wave-line" style="height: 6px;"></span>
              <span class="wave-line" style="height: 12px;"></span>
              <span class="wave-line" style="height: 16px;"></span>
              <span class="wave-line" style="height: 8px;"></span>
              <span class="wave-line" style="height: 14px;"></span>
              <span class="wave-line" style="height: 10px;"></span>
            </div>
            <span style="font-size: 0.72rem; color: var(--text-secondary);">Áudio do Copiloto</span>
          </div>
        `;
      }

      if (meta && (meta.fonte || meta.porQue)) {
        content += `
          <div class="clean-explain-card">
            <div class="explain-summary" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
              <span>💡 Por que alertei você • ${meta.confianca}% Confiança</span>
              <span style="font-size: 0.65rem;">▾</span>
            </div>
            <div class="explain-details" style="display: none;">
              ${meta.porQue}
              <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.25rem;">Fonte: ${meta.fonte}</div>
            </div>
          </div>
        `;
      }

      if (meta && meta.acaoSugerida) {
        content += `
          <div>
            <button class="btn-msg-action" data-action="${meta.acaoSugerida}">
              <span>✓</span> ${meta.acaoSugerida}
            </button>
          </div>
        `;
      }

      content += `<div class="msg-timestamp">${timeStr} • ✓✓</div>`;
      bubble.innerHTML = content;
    }

    row.appendChild(bubble);
    chatMessagesStream.appendChild(row);
    chatMessagesStream.scrollTop = chatMessagesStream.scrollHeight;

    // Conecta áudio
    bubble.querySelectorAll(".btn-play-clean").forEach(btn => {
      btn.addEventListener("click", () => {
        const audioMsg = btn.getAttribute("data-audio");
        speakText(audioMsg);
      });
    });

    // Conecta ação sugerida
    bubble.querySelectorAll(".btn-msg-action").forEach(btn => {
      btn.addEventListener("click", () => {
        const act = btn.getAttribute("data-action");
        if (act.includes("ZARC")) {
          openDrawer();
        } else if (act.includes("Amostragem") || act.includes("Missão")) {
          openDrawer();
        } else {
          sendUserMessage(`Como executar: ${act}?`);
        }
      });
    });
  }

  function escapeHTML(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function escapeAttr(str) {
    return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function formatMarkdown(str) {
    return str
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n\n/g, "</p><p style='margin-top: 0.45rem;'>")
      .replace(/\n/g, "<br>");
  }

  function sendUserMessage(text) {
    if (!text || !text.trim()) return;
    appendMessage("farmer", text);

    const typingRow = document.createElement("div");
    typingRow.className = "msg-row ai";
    typingRow.id = "typing-row";
    typingRow.innerHTML = `
      <div class="msg-bubble" style="font-size: 0.8rem; color: var(--text-muted); font-style: italic;">
        Consultando ZARC e sensores de Rio Verde...
      </div>
    `;
    chatMessagesStream.appendChild(typingRow);
    chatMessagesStream.scrollTop = chatMessagesStream.scrollHeight;

    setTimeout(async () => {
      typingRow.remove();

      // Tenta API real primeiro; fallback para copilot local
      if (window.AgroAPI && window.AgroAPI.isBackendOnline()) {
        const session = window.AgroAPI.loadSession();
        const produtorId = session?.id || "demo-user";
        // Streaming: bolha AI vazia com cursor, anexa tokens
        if (window.AgroAPI.postChatStream) {
          try {
            const row = document.createElement("div");
            row.className = "msg-row ai";
            const now = new Date();
            const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
            const bubble = document.createElement("div");
            bubble.className = "msg-bubble";
            bubble.innerHTML = `<p>▍</p><div class="msg-timestamp">${timeStr} • ✓✓</div>`;
            row.appendChild(bubble);
            chatMessagesStream.appendChild(row);
            chatMessagesStream.scrollTop = chatMessagesStream.scrollHeight;
            const p = bubble.querySelector("p");
            let full = "";
            const { resposta, meta } = await window.AgroAPI.postChatStream(produtorId, text, {
              onMeta: () => {},
              onToken: (tok) => {
                full += tok;
                p.innerHTML = (full ? formatMarkdown(escapeHTML(full)) : "") + "▍";
                chatMessagesStream.scrollTop = chatMessagesStream.scrollHeight;
              },
            });
            row.remove();
            if (meta && (meta.erro || (!resposta && meta.mensagem))) {
              const sugestoes = (meta.sugestoes || []).map(s => `\n• ${s}`).join("");
              const msg = `${meta.mensagem || "Não consegui entender."}${sugestoes ? `\n\nTente perguntar:${sugestoes}` : ""}`;
              appendMessage("ai", msg, { fonte: "AgroPilot", confianca: 60, audioText: meta.mensagem });
            } else {
              appendMessage("ai", resposta || full, {
                fonte: (meta && meta.fonte) || "API",
                porQue: meta && meta.intencao ? `Intenção: ${meta.intencao}` : undefined,
                confianca: 92,
                audioText: resposta || full,
              });
            }
            return;
          } catch {}
        }
        try {
          const apiResp = await window.AgroAPI.postChat(produtorId, text);
          if (apiResp.erro) {
            // Fallback sugestões
            const sugestoes = (apiResp.sugestoes || []).map(s => `\n• ${s}`).join("");
            const msg = `${apiResp.mensagem}${sugestoes ? `\n\nTente perguntar:${sugestoes}` : ""}`;
            appendMessage("ai", msg, { fonte: "AgroPilot", confianca: 60, audioText: apiResp.mensagem });
          } else {
            const meta = {
              fonte: apiResp.fonte || "API",
              porQue: `Intenção: ${apiResp.intencao}`,
              confianca: 92,
              audioText: apiResp.resposta,
            };
            appendMessage("ai", apiResp.resposta, meta);
          }
          return;
        } catch {}
      }

      // Fallback: copilot local
      const answer = window.agroCopilot.processMessage(text);
      appendMessage("ai", answer.text, answer);
    }, 380);
  }

  // Submit do formulário do chat
  if (cleanChatForm) {
    cleanChatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const msg = cleanInputField.value;
      cleanInputField.value = "";
      sendUserMessage(msg);
    });
  }

  // Chips rápidos
  cleanChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const p = chip.getAttribute("data-prompt");
      sendUserMessage(p);
    });
  });

  // Microfone (gravação de áudio do produtor)
  if (btnCleanMic) {
    btnCleanMic.addEventListener("click", () => {
      showCleanToast("🎙️ Gravando áudio do produtor...", "info");
      setTimeout(() => {
        sendUserMessage("Oi AgroPilot! O tempo tá fechando aqui em Rio Verde, posso passar o veneno hoje ou a chuva vai lavar?");
      }, 1400);
    });
  }

  // ==========================================================================
  // 5. Drawer Lateral (Clean Slide-out)
  // ==========================================================================
  function openDrawer() {
    drawerBackdrop.style.display = "flex";
  }

  function closeDrawer() {
    drawerBackdrop.style.display = "none";
  }

  if (btnOpenDrawerPill) btnOpenDrawerPill.addEventListener("click", openDrawer);
  if (btnOpenDrawer) btnOpenDrawer.addEventListener("click", openDrawer);
  if (btnCloseDrawer) btnCloseDrawer.addEventListener("click", closeDrawer);

  drawerBackdrop.addEventListener("click", (e) => {
    if (e.target === drawerBackdrop) closeDrawer();
  });

  if (btnAskZarc) {
    btnAskZarc.addEventListener("click", () => {
      closeDrawer();
      sendUserMessage("Quais são as datas recomendadas do calendário ZARC para a soja na minha região?");
    });
  }

  // ==========================================================================
  // 6. Diagnóstico por Foto
  // ==========================================================================
  if (btnOpenPhoto) {
    btnOpenPhoto.addEventListener("click", () => {
      modalPhotoBackdrop.style.display = "flex";
    });
  }
  if (btnClosePhotoModal) {
    btnClosePhotoModal.addEventListener("click", () => {
      modalPhotoBackdrop.style.display = "none";
    });
  }
  modalPhotoBackdrop.addEventListener("click", (e) => {
    if (e.target === modalPhotoBackdrop) modalPhotoBackdrop.style.display = "none";
  });

  document.querySelectorAll(".btn-choose-photo").forEach(btn => {
    btn.addEventListener("click", () => {
      const photoType = btn.getAttribute("data-photo");
      modalPhotoBackdrop.style.display = "none";

      let promptMsg = "";
      if (photoType === "lagarta") {
        promptMsg = "📸 [Foto do Produtor]: Folha de soja com lagarta verde no baixeiro.";
      } else if (photoType === "ferrugem") {
        promptMsg = "📸 [Foto do Produtor]: Pontos castanhos na face inferior da folha.";
      } else {
        promptMsg = "📸 [Foto do Produtor]: Folha com amarelecimento internerval.";
      }

      appendMessage("farmer", promptMsg);

      setTimeout(() => {
        const diag = window.agroCopilot.analyzeImage(photoType);
        appendMessage("ai", diag.text, diag);
      }, 500);
    });
  });

  // ==========================================================================
  // 7. Simulações da Banca (Menu Dropdown Clean)
  // ==========================================================================
  if (btnToggleSimMenu) {
    btnToggleSimMenu.addEventListener("click", (e) => {
      e.stopPropagation();
      simMenu.classList.toggle("open");
    });
  }

  document.addEventListener("click", (e) => {
    if (simMenu && !simMenu.contains(e.target) && e.target !== btnToggleSimMenu) {
      simMenu.classList.remove("open");
    }
  });

  document.querySelectorAll(".sim-menu-item").forEach(item => {
    item.addEventListener("click", () => {
      const scenarioKey = item.getAttribute("data-scenario");
      simMenu.classList.remove("open");
      triggerCleanSimulation(scenarioKey);
    });
  });

  function triggerCleanSimulation(key) {
    const cenario = AGRO_DATA.cenariosSimulacao[key];
    if (!cenario) return;

    showCleanToast(`${cenario.titulo}: ${cenario.descricao}`, cenario.tipo);

    const alertaMsg = `🚨 **ALERTA PROATIVO 24/7:** ${cenario.chatPrompt}\n\n` +
      `📌 **O que você deve fazer agora:** ${cenario.acaoRecomendada}`;

    appendMessage("ai", alertaMsg, {
      audioText: `Atenção Seu Sebastião! ${cenario.chatPrompt}`,
      fonte: cenario.fonte,
      porQue: cenario.porQue,
      confianca: cenario.confianca
    });
  }

  // ==========================================================================
  // 8. Modo Campo (Luz Solar Forte)
  // ==========================================================================
  if (btnToggleSunlight) {
    btnToggleSunlight.addEventListener("click", () => {
      isSunlight = !isSunlight;
      if (isSunlight) {
        document.body.classList.add("sunlight-mode");
        btnToggleSunlight.textContent = "🌙";
        showCleanToast("Modo Campo: Alto contraste ativado");
      } else {
        document.body.classList.remove("sunlight-mode");
        btnToggleSunlight.textContent = "☀️";
        showCleanToast("Modo Padrão reativado");
      }
    });
  }

  // ==========================================================================
  // 9. Cadastro do Produtor
  // ==========================================================================
  if (btnOpenEditProfile) {
    btnOpenEditProfile.addEventListener("click", () => {
      closeDrawer();
      modalProfileBackdrop.style.display = "flex";
    });
  }
  if (btnCloseProfileModal) {
    btnCloseProfileModal.addEventListener("click", () => {
      modalProfileBackdrop.style.display = "none";
    });
  }
  if (btnCancelProfile) {
    btnCancelProfile.addEventListener("click", () => {
      modalProfileBackdrop.style.display = "none";
    });
  }
  modalProfileBackdrop.addEventListener("click", (e) => {
    if (e.target === modalProfileBackdrop) modalProfileBackdrop.style.display = "none";
  });

  if (formCleanProfile) {
    formCleanProfile.addEventListener("submit", (e) => {
      e.preventDefault();
      const nome = document.getElementById("prof-nome").value;
      const tel = document.getElementById("prof-telefone").value;
      const cid = document.getElementById("prof-municipio").value;

      AGRO_DATA.currentProfile.nome = nome;
      AGRO_DATA.currentProfile.telefone = tel;
      AGRO_DATA.currentProfile.municipio = cid;

      window.agroCopilot.setFarmerProfile(AGRO_DATA.currentProfile);
      updateFarmerContextUI();
      modalProfileBackdrop.style.display = "none";

      const parts = nome.trim().split(/\s+/);
      const shortName = ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona") && parts[1]) 
        ? `${parts[0]} ${parts[1]}` 
        : parts[0];

      showCleanToast(`Perfil atualizado para ${shortName}!`);
      appendMessage("ai", `Perfil atualizado com sucesso, **${shortName}**! Estou monitorando sua lavoura em **${cid}**.`);
    });
  }

  // ==========================================================================
  // 10. Inicialização
  // ==========================================================================

  // Carrega perfil salvo no localStorage (vindo do login)
  function loadProfileFromSession() {
    try {
      const profile = window.AgroAPI ? window.AgroAPI._loadLocalProfile() : JSON.parse(localStorage.getItem("agropilot_profile") || "null");
      if (!profile) return;

      // Atualiza AGRO_DATA com dados reais do produtor
      if (profile.nome) AGRO_DATA.currentProfile.nome = profile.nome;
      if (profile.municipio && profile.uf) AGRO_DATA.currentProfile.municipio = `${profile.municipio} - ${profile.uf}`;
      if (profile.lavouras && profile.lavouras.length > 0) {
        const c = profile.lavouras[0].cultura?.toLowerCase() || "soja";
        AGRO_DATA.currentProfile.culturaAtual = AGRO_DATA.culturas[c] ? c : "soja";
      }

      // Atualiza boas-vindas iniciais
      const welcomeEl = document.querySelector(".msg-row.ai .msg-bubble strong");
      const parts = profile.nome.trim().split(/\s+/);
      const shortName = (parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona") && parts[1]
        ? `${parts[0]} ${parts[1]}` : parts[0];
      if (welcomeEl) welcomeEl.textContent = shortName;
    } catch {}
  }

  loadProfileFromSession();
  updateFarmerContextUI();

  // Conectar botões de áudio iniciais
  document.querySelectorAll(".btn-play-clean").forEach(btn => {
    btn.addEventListener("click", () => {
      const audioMsg = btn.getAttribute("data-audio");
      speakText(audioMsg);
    });
  });

  console.log("🌾 AgroPilot Clean Chatbot ativo.");
});

// ─── Global: Logout ───────────────────────────────────────────────────────────
function handleLogout() {
  localStorage.removeItem("agropilot_session");
  localStorage.removeItem("agropilot_profile");
  // Redireciona para tela de login
  window.location.href = "hackathon/login/login.html";
}
window.handleLogout = handleLogout;
