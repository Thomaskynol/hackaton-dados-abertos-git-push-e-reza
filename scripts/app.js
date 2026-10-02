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
  const btnReopenOnboarding = document.getElementById("btn-reopen-onboarding");

  // Histórico de Conversas (Estilo ChatGPT)
  const historyBackdrop = document.getElementById("history-backdrop");
  const historyPanel = document.getElementById("history-panel");
  const btnOpenHistory = document.getElementById("btn-open-history");
  const btnCloseHistory = document.getElementById("btn-close-history");
  const btnNewChat = document.getElementById("btn-new-chat");
  const historyChatList = document.getElementById("history-chat-list");
  const btnClearAllChats = document.getElementById("btn-clear-all-chats");
  const historyFarmerName = document.getElementById("history-farmer-name");

  // Onboarding Inicial
  const onboardingScreen = document.getElementById("onboarding-screen");
  const onboardingForm = document.getElementById("onboarding-form");
  const btnSubmitOnboarding = document.getElementById("btn-submit-onboarding");
  const onbNome = document.getElementById("onb-nome");
  const onbTelefone = document.getElementById("onb-telefone");
  const onbGleba = document.getElementById("onb-gleba");
  const onbMunicipio = document.getElementById("onb-municipio");
  const onbCultura = document.getElementById("onb-cultura");
  const onbSolo = document.getElementById("onb-solo");
  const onbArea = document.getElementById("onb-area");

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
    if (typeof AGRO_DATA === "undefined" || !AGRO_DATA.currentProfile) return;
    const p = AGRO_DATA.currentProfile;
    const c = (AGRO_DATA.culturas && AGRO_DATA.culturas[p.culturaAtual]) || (AGRO_DATA.culturas && AGRO_DATA.culturas.soja) || { nome: "Soja", icone: "🌱" };

    const rawNome = (p.nome || "Produtor").trim();
    const parts = rawNome.split(/\s+/);
    let shortName = parts[0] || "Produtor";
    if ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) {
      shortName = `${parts[0]} ${parts[1]}`;
    }

    if (navFarmerName) navFarmerName.textContent = shortName;
    if (navFarmerCulture) navFarmerCulture.textContent = `${c.nome.split(" ")[0]} V4`;
    if (navFarmerCity) navFarmerCity.textContent = (p.municipio || "Rio Verde").split(" - ")[0];

    if (drawerFarmName) drawerFarmName.textContent = p.propriedade || "Sítio Bela Vista";
    if (drawerFarmMeta) drawerFarmMeta.textContent = `${p.municipio || "Rio Verde - GO"} • ${p.areaHa || 14.5} ha`;

    const soilDesc = p.tipoSolo === "AD1" 
      ? "AD1 (Arenoso CAD < 35mm)" 
      : (p.tipoSolo === "AD2" ? "AD2 (Médio CAD 35-50mm)" : "AD3 (Argiloso CAD > 50mm)");
    if (drawerSoilVal) drawerSoilVal.textContent = soilDesc;

    const drawerBadge = document.querySelector(".gleba-safra-badge");
    if (drawerBadge) {
      drawerBadge.textContent = `${c.icone} ${c.nome.split(" ")[0]} Safra 2026/27`;
    }
  }

  // ==========================================================================
  // 4. Mensagens e Conversação no Chat
  // ==========================================================================
  function appendMessage(sender, text, meta = null, save = true) {
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
              <span>💡 Por que alertei você • ${meta.confianca || 95}% Confiança</span>
              <span style="font-size: 0.65rem;">▾</span>
            </div>
            <div class="explain-details" style="display: none;">
              ${meta.porQue || ""}
              <div style="font-size: 0.7rem; color: var(--text-muted); margin-top: 0.25rem;">Fonte: ${meta.fonte || "Embrapa & ZARC / MAPA"}</div>
            </div>
          </div>
        `;
      }

      if (meta && meta.acaoSugerida) {
        content += `
          <div>
            <button class="btn-msg-action" data-action="${escapeAttr(meta.acaoSugerida)}">
              <span>✓</span> ${escapeHTML(meta.acaoSugerida)}
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

    // Salva no chat ativo caso save === true
    if (save && typeof getActiveChat === "function") {
      const activeChat = getActiveChat();
      if (activeChat) {
        if (!activeChat.messages) activeChat.messages = [];
        activeChat.messages.push({ sender, text, meta });
        if (sender === "farmer" && (activeChat.title === "Nova Conversa" || activeChat.title.startsWith("Nova Conversa"))) {
          activeChat.title = text.length > 28 ? text.substring(0, 28) + "..." : text;
        }
        saveChatsToStorage();
        renderHistoryList();
      }
    }
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

    setTimeout(() => {
      typingRow.remove();
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

  // ==========================================================================
  // Navegação da Barra de Chips (Mouse Wheel, Teclado, Botões e Arrastar)
  // ==========================================================================
  const cleanChipsBar = document.getElementById("clean-chips-bar");
  const btnScrollLeft = document.getElementById("btn-scroll-chips-left");
  const btnScrollRight = document.getElementById("btn-scroll-chips-right");

  if (cleanChipsBar) {
    // 1. Scroll do Mouse: roda vertical converte em rolagem horizontal
    cleanChipsBar.addEventListener("wheel", (e) => {
      if (e.deltaY !== 0) {
        e.preventDefault();
        cleanChipsBar.scrollLeft += e.deltaY * 1.25;
      }
    }, { passive: false });

    // 2. Navegação pelo Teclado (Setas Esquerda e Direita)
    cleanChipsBar.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        cleanChipsBar.scrollBy({ left: 180, behavior: "smooth" });
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        cleanChipsBar.scrollBy({ left: -180, behavior: "smooth" });
      }
    });

    // 3. Botões laterais de rolagem rápida
    if (btnScrollLeft) {
      btnScrollLeft.addEventListener("click", () => {
        cleanChipsBar.scrollBy({ left: -220, behavior: "smooth" });
      });
    }
    if (btnScrollRight) {
      btnScrollRight.addEventListener("click", () => {
        cleanChipsBar.scrollBy({ left: 220, behavior: "smooth" });
      });
    }

    // 4. Arrastar com o mouse (Drag to Scroll)
    let isMouseDown = false;
    let startX = 0;
    let initialScrollLeft = 0;
    let isDragging = false;

    cleanChipsBar.addEventListener("mousedown", (e) => {
      isMouseDown = true;
      isDragging = false;
      startX = e.pageX - cleanChipsBar.offsetLeft;
      initialScrollLeft = cleanChipsBar.scrollLeft;
    });

    window.addEventListener("mouseup", () => {
      if (isMouseDown) {
        isMouseDown = false;
        cleanChipsBar.classList.remove("dragging");
        setTimeout(() => { isDragging = false; }, 50);
      }
    });

    cleanChipsBar.addEventListener("mousemove", (e) => {
      if (!isMouseDown) return;
      const currentX = e.pageX - cleanChipsBar.offsetLeft;
      const diff = currentX - startX;
      if (Math.abs(diff) > 4) {
        isDragging = true;
        cleanChipsBar.classList.add("dragging");
        cleanChipsBar.scrollLeft = initialScrollLeft - diff;
      }
    });

    // 5. Chips rápidos (com clique seguro após arrasto e scrollIntoView ao focar)
    cleanChips.forEach(chip => {
      chip.addEventListener("click", (e) => {
        if (isDragging) {
          e.preventDefault();
          return;
        }
        const p = chip.getAttribute("data-prompt");
        sendUserMessage(p);
      });

      chip.addEventListener("focus", () => {
        chip.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
      });
    });

    // 6. Atualização visual do estado dos botões laterais
    function updateScrollArrows() {
      if (!btnScrollLeft || !btnScrollRight) return;
      const maxScroll = cleanChipsBar.scrollWidth - cleanChipsBar.clientWidth;
      btnScrollLeft.style.opacity = cleanChipsBar.scrollLeft > 8 ? "1" : "0.35";
      btnScrollRight.style.opacity = cleanChipsBar.scrollLeft < maxScroll - 8 ? "1" : "0.35";
    }

    cleanChipsBar.addEventListener("scroll", updateScrollArrows);
    window.addEventListener("resize", updateScrollArrows);
    setTimeout(updateScrollArrows, 350);
  }

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
      const nomeInput = document.getElementById("prof-nome");
      const telInput = document.getElementById("prof-telefone");
      const glebaInput = document.getElementById("prof-gleba");
      const cidInput = document.getElementById("prof-municipio");
      if (nomeInput) nomeInput.value = AGRO_DATA.currentProfile.nome;
      if (telInput) telInput.value = AGRO_DATA.currentProfile.telefone;
      if (glebaInput) glebaInput.value = AGRO_DATA.currentProfile.propriedade;
      if (cidInput) cidInput.value = AGRO_DATA.currentProfile.municipio;
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
      const glebaInput = document.getElementById("prof-gleba");
      const gleba = glebaInput ? glebaInput.value : AGRO_DATA.currentProfile.propriedade;
      const cid = document.getElementById("prof-municipio").value;

      AGRO_DATA.currentProfile.nome = nome;
      AGRO_DATA.currentProfile.telefone = tel;
      AGRO_DATA.currentProfile.propriedade = gleba;
      AGRO_DATA.currentProfile.municipio = cid;

      window.agroCopilot.setFarmerProfile(AGRO_DATA.currentProfile);
      updateFarmerContextUI();
      modalProfileBackdrop.style.display = "none";

      const parts = nome.trim().split(/\s+/);
      const shortName = ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona") && parts[1]) 
        ? `${parts[0]} ${parts[1]}` 
        : parts[0];

      showCleanToast(`Perfil atualizado para ${shortName}!`);
      appendMessage("ai", `Perfil atualizado com sucesso, **${shortName}**! Gleba **${gleba}** e lavoura em **${cid}** salvas.`);
      updateWelcomeMessage(AGRO_DATA.currentProfile);
    });
  }

  // ==========================================================================
  // 10. Atualização Dinâmica da Mensagem de Boas-Vindas
  // ==========================================================================
  function updateWelcomeMessage(profile) {
    if (typeof AGRO_DATA === "undefined" || !AGRO_DATA.culturas) return;
    const cultura = AGRO_DATA.culturas[profile.culturaAtual] || AGRO_DATA.culturas.soja || { nome: "Soja (Grão)" };
    const rawNome = (profile.nome || "Produtor").trim();
    const parts = rawNome.split(/\s+/);
    let shortName = parts[0] || "Produtor";
    if ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) {
      shortName = `${parts[0]} ${parts[1]}`;
    }

    const firstBubble = document.querySelector("#chat-messages-stream .msg-row.ai .msg-bubble");
    if (firstBubble) {
      firstBubble.innerHTML = `
        <p>Olá, <strong>${escapeHTML(shortName)}</strong>! Sou o seu <strong>AgroPilot 24/7</strong>.</p>
        <p style="margin-top: 0.4rem;">
          Estou monitorando sua lavoura de <strong>${escapeHTML(cultura.nome)} no solo ${escapeHTML(profile.tipoSolo)}</strong> em ${escapeHTML(profile.municipio)}. Como no pequeno produtor <strong>não há margem para errar</strong>, estou de olho no tempo, no ZARC e nas pragas dia e noite.
        </p>
        <p style="margin-top: 0.4rem; color: var(--amber);">
          🌧️ <strong>Aviso de Hoje:</strong> Previsão de <strong>chuva forte (75mm)</strong> nas próximas 48h. Evite pulverizar defensivo hoje para não perder o produto e confira as saídas das curvas de nível.
        </p>

        <!-- Voice Note (WhatsApp style) -->
        <div class="clean-voice-bar">
          <button class="btn-play-clean" data-audio="Olá ${escapeAttr(shortName)}! Previsão de chuva forte de 75 milímetros em ${escapeAttr(profile.municipio)} nas próximas 48 horas. Não pulverize nada hoje pra não perder veneno e confira as curvas de nível no talhão." title="Ouvir áudio">
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
          <span style="font-size: 0.72rem; color: var(--text-secondary);">0:14 • Áudio do Copiloto</span>
        </div>

        <!-- Clean Explainability Tag -->
        <div class="clean-explain-card">
          <div class="explain-summary" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
            <span>💡 Por que alertei você • 95% Confiança</span>
            <span style="font-size: 0.65rem;">▾</span>
          </div>
          <div class="explain-details" style="display: none;">
            Frente polar no radar CPTEC com saturação rápida do solo argiloso ${escapeHTML(profile.tipoSolo)}. Fonte: INMET & ZARC MAPA Portaria 142/2024.
          </div>
        </div>

        <div class="msg-timestamp">Hoje • ✓✓</div>
      `;

      const playBtn = firstBubble.querySelector(".btn-play-clean");
      if (playBtn) {
        playBtn.addEventListener("click", () => {
          speakText(playBtn.getAttribute("data-audio"));
        });
      }
    }
  }

  // ==========================================================================
  // 11. Onboarding e Gestão de Perfil Inicial
  // ==========================================================================
  function populateOnboardingForm(profile) {
    if (onbNome) onbNome.value = profile.nome || "";
    if (onbTelefone) onbTelefone.value = profile.telefone || "";
    if (onbGleba) onbGleba.value = profile.propriedade || "";
    if (onbMunicipio) onbMunicipio.value = profile.municipio || "";
    if (onbCultura) onbCultura.value = profile.culturaAtual || "";
    if (onbSolo) onbSolo.value = profile.tipoSolo || "";
    if (onbArea) onbArea.value = profile.areaHa || "";
  }

  function loadStoredProfile() {
    const saved = localStorage.getItem("agropilot_profile");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        AGRO_DATA.currentProfile = { ...AGRO_DATA.currentProfile, ...parsed };
      } catch (e) {
        console.warn("Erro ao ler perfil salvo:", e);
      }
    }
    // Na tela de boas-vindas todos os campos devem sempre iniciar 100% vazios para o produtor preencher
    populateOnboardingForm({
      nome: "",
      telefone: "",
      propriedade: "",
      municipio: "",
      culturaAtual: "",
      tipoSolo: "",
      areaHa: ""
    });
  }

  // Submissão do Formulário de Onboarding
  function handleOnboardingSubmit(e) {
    if (e) {
      if (typeof e.preventDefault === "function") e.preventDefault();
      if (typeof e.stopPropagation === "function") e.stopPropagation();
    }

    const rawNome = onbNome ? onbNome.value.trim() : "";
    const rawTelefone = onbTelefone ? onbTelefone.value.trim() : "";
    const rawGleba = onbGleba ? onbGleba.value.trim() : "";
    const rawMunicipio = onbMunicipio ? onbMunicipio.value.trim() : "";
    const rawCultura = (onbCultura && onbCultura.value) ? onbCultura.value : "";
    const rawSolo = (onbSolo && onbSolo.value) ? onbSolo.value : "";
    const rawArea = onbArea ? parseFloat(onbArea.value) : NaN;

    const current = (typeof AGRO_DATA !== "undefined" && AGRO_DATA.currentProfile) ? AGRO_DATA.currentProfile : {};

    const newProfile = {
      nome: rawNome || current.nome || "Seu Sebastião",
      telefone: rawTelefone || current.telefone || "(64) 99821-4472",
      propriedade: rawGleba || current.propriedade || "Sítio Bela Vista",
      municipio: rawMunicipio || current.municipio || "Rio Verde - GO",
      culturaAtual: rawCultura || current.culturaAtual || "soja",
      tipoSolo: rawSolo || current.tipoSolo || "AD3",
      areaHa: (!isNaN(rawArea) && rawArea > 0) ? rawArea : (current.areaHa || 14.5),
      faseCiclo: current.faseCiclo || "vegetativo",
      proagroAtivo: true,
      pronafElegivel: true
    };

    if (typeof AGRO_DATA !== "undefined") {
      AGRO_DATA.currentProfile = { ...current, ...newProfile };
    }

    try {
      localStorage.setItem("agropilot_profile", JSON.stringify(newProfile));
      localStorage.setItem("agropilot_configured", "true");
    } catch (err) {
      console.warn("Erro ao salvar perfil no localStorage:", err);
    }

    if (window.agroCopilot && typeof window.agroCopilot.setFarmerProfile === "function") {
      window.agroCopilot.setFarmerProfile(newProfile);
    }

    try {
      updateFarmerContextUI();
    } catch (err) {
      console.warn("Erro ao atualizar contexto:", err);
    }

    try {
      updateWelcomeMessage(newProfile);
    } catch (err) {
      console.warn("Erro ao atualizar boas-vindas:", err);
    }

    // Fecha a tela de onboarding com classe e estilos imediatos
    if (onboardingScreen) {
      onboardingScreen.classList.add("hidden");
      onboardingScreen.style.display = "none";
      onboardingScreen.style.visibility = "hidden";
      onboardingScreen.style.opacity = "0";
      onboardingScreen.style.pointerEvents = "none";
      onboardingScreen.setAttribute("aria-hidden", "true");
    }

    const parts = (newProfile.nome || "Produtor").split(/\s+/);
    const shortName = ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) 
      ? `${parts[0]} ${parts[1]}` 
      : parts[0];

    if (historyFarmerName) {
      historyFarmerName.textContent = shortName;
    }

    // Se o chat ativo tiver boas-vindas, re-renderiza para refletir o novo produtor
    if (typeof renderActiveChat === "function") {
      renderActiveChat();
    }

    showCleanToast(`Propriedade configurada! Bem-vindo, ${shortName}!`);
    playCleanBeep("info");
  }

  if (onboardingForm) {
    onboardingForm.addEventListener("submit", handleOnboardingSubmit);
  }
  if (btnSubmitOnboarding) {
    btnSubmitOnboarding.addEventListener("click", handleOnboardingSubmit);
  }

  // Botão na gaveta para reabrir tela de onboarding
  if (btnReopenOnboarding) {
    btnReopenOnboarding.addEventListener("click", () => {
      closeDrawer();
      // Sempre limpa os campos ao reabrir a tela de cadastro para preenchimento limpo
      populateOnboardingForm({
        nome: "",
        telefone: "",
        propriedade: "",
        municipio: "",
        culturaAtual: "",
        tipoSolo: "",
        areaHa: ""
      });
      if (onboardingScreen) {
        onboardingScreen.style.display = "flex";
        onboardingScreen.style.visibility = "visible";
        onboardingScreen.style.opacity = "1";
        onboardingScreen.style.pointerEvents = "auto";
        onboardingScreen.removeAttribute("aria-hidden");
        onboardingScreen.classList.remove("hidden");
      }
    });
  }

  // ==========================================================================
  // 12. Histórico de Conversas (Estilo ChatGPT)
  // ==========================================================================
  const STORAGE_CHATS_KEY = "agropilot_chat_history";
  const STORAGE_ACTIVE_CHAT_KEY = "agropilot_active_chat_id";

  const DEFAULT_CHATS = [
    {
      id: "chat-default-1",
      title: "⛈️ Alerta de Chuva 75mm",
      timestamp: Date.now(),
      messages: [
        { type: "raw" }
      ]
    },
    {
      id: "chat-default-2",
      title: "🌾 Consulta Janela ZARC Soja",
      timestamp: Date.now() - 3600000 * 18,
      messages: [
        { sender: "farmer", text: "Posso plantar semana que vem?" },
        {
          sender: "ai",
          text: "Sim! Consultando o **ZARC oficial** para sua região no solo AD3:\n\n✅ Estamos no decêndio **Out/D3 a Nov/D2**, onde o risco climático é de apenas **20%** (Classe I - Risco Mínimo).\n🛡️ Plantando nesta janela, sua lavoura tem **cobertura garantida de 100%** do seguro Proagro.\n⚠️ Cuidado Crítico: Não atrase além de 25 de Novembro para não perder a garantia.",
          meta: {
            audioText: "Pode plantar sim! O ZARC indica risco de vinte por cento nesta semana com cobertura total do Proagro.",
            fonte: "Portaria ZARC MAPA vigente para Rio Verde/GO",
            porQue: "ISNA hídrico superior a 0.65 e boa umidade no solo argiloso.",
            confianca: 96
          }
        }
      ]
    },
    {
      id: "chat-default-3",
      title: "💰 Cotação da Saca e Proagro",
      timestamp: Date.now() - 3600000 * 42,
      messages: [
        { sender: "farmer", text: "Qual o preço da saca hoje e onde vender?" },
        {
          sender: "ai",
          text: "A saca de 60kg de soja está cotada hoje em **R$ 128,50** no mercado físico de Rio Verde (Cepea/Esalq).\n\n💡 **Oportunidade para Familiar:** O edital do PNAE/PAA da cooperativa local está pagando **R$ 138,00/saca** (+7,3% sobre a média) para lotes da agricultura familiar com CAF/DAP ativa.",
          meta: {
            audioText: "A saca de soja tá em cento e vinte e oito reais no Cepea, mas a prefeitura paga cento e trinta e oito no PNAE para quem tem Pronaf.",
            fonte: "Cepea/Esalq & Painel PNAE 2026",
            porQue: "Preços monitorados em tempo real com ágio para produtor Pronaf.",
            confianca: 98
          }
        }
      ]
    }
  ];

  let chats = [];
  let activeChatId = null;

  function loadChatsFromStorage() {
    try {
      const saved = localStorage.getItem(STORAGE_CHATS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          chats = parsed;
        } else {
          chats = JSON.parse(JSON.stringify(DEFAULT_CHATS));
        }
      } else {
        chats = JSON.parse(JSON.stringify(DEFAULT_CHATS));
      }
    } catch (e) {
      console.warn("Erro ao ler histórico de chats:", e);
      chats = JSON.parse(JSON.stringify(DEFAULT_CHATS));
    }

    const savedActive = localStorage.getItem(STORAGE_ACTIVE_CHAT_KEY);
    if (savedActive && chats.some(c => c.id === savedActive)) {
      activeChatId = savedActive;
    } else if (chats.length > 0) {
      activeChatId = chats[0].id;
    }
  }

  function saveChatsToStorage() {
    try {
      localStorage.setItem(STORAGE_CHATS_KEY, JSON.stringify(chats));
      if (activeChatId) {
        localStorage.setItem(STORAGE_ACTIVE_CHAT_KEY, activeChatId);
      }
    } catch (e) {
      console.warn("Erro ao salvar histórico de chats:", e);
    }
  }

  function getActiveChat() {
    return chats.find(c => c.id === activeChatId) || null;
  }

  function renderActiveChat() {
    if (!chatMessagesStream) return;
    chatMessagesStream.innerHTML = "";

    const chat = getActiveChat();
    if (!chat) return;

    if (!chat.messages || chat.messages.length === 0) {
      chat.messages = [{ type: "raw" }];
    }

    chat.messages.forEach(msg => {
      if (msg.type === "raw") {
        const row = document.createElement("div");
        row.className = "msg-row ai";
        const profile = (typeof AGRO_DATA !== "undefined" && AGRO_DATA.currentProfile) ? AGRO_DATA.currentProfile : {};
        const pNome = profile.nome || "Seu Sebastião";
        const parts = pNome.trim().split(/\s+/);
        const shortName = ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1])
          ? `${parts[0]} ${parts[1]}`
          : parts[0];
        const cultura = (typeof AGRO_DATA !== "undefined" && AGRO_DATA.culturas && AGRO_DATA.culturas[profile.culturaAtual]) || { nome: "Soja (Grão)" };
        const solo = profile.tipoSolo || "AD3";
        const cid = profile.municipio || "Rio Verde - GO";

        row.innerHTML = `
          <div class="msg-bubble">
            <p>Olá, <strong>${escapeHTML(shortName)}</strong>! Sou o seu <strong>AgroPilot 24/7</strong>.</p>
            <p style="margin-top: 0.4rem;">
              Estou monitorando sua lavoura de <strong>${escapeHTML(cultura.nome)} no solo ${escapeHTML(solo)}</strong> em ${escapeHTML(cid)}. Como no pequeno produtor <strong>não há margem para errar</strong>, estou de olho no tempo, no ZARC e nas pragas dia e noite.
            </p>
            <p style="margin-top: 0.4rem; color: var(--amber);">
              🌧️ <strong>Aviso de Hoje:</strong> Previsão de <strong>chuva forte (75mm)</strong> nas próximas 48h. Evite pulverizar defensivo hoje para não perder o produto e confira as saídas das curvas de nível.
            </p>

            <!-- Voice Note (WhatsApp style) -->
            <div class="clean-voice-bar">
              <button class="btn-play-clean" data-audio="Olá ${escapeAttr(shortName)}! Previsão de chuva forte de 75 milímetros em ${escapeAttr(cid)} nas próximas 48 horas. Não pulverize nada hoje pra não perder veneno e confira as curvas de nível no talhão." title="Ouvir áudio">
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
              <span style="font-size: 0.72rem; color: var(--text-secondary);">0:14 • Áudio do Copiloto</span>
            </div>

            <!-- Clean Explainability Tag -->
            <div class="clean-explain-card">
              <div class="explain-summary" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'none' ? 'block' : 'none'">
                <span>💡 Por que alertei você • 95% Confiança</span>
                <span style="font-size: 0.65rem;">▾</span>
              </div>
              <div class="explain-details" style="display: none;">
                Frente polar no radar CPTEC com saturação rápida do solo argiloso ${escapeHTML(solo)}. Fonte: INMET & ZARC MAPA Portaria 142/2024.
              </div>
            </div>

            <div class="msg-timestamp">Hoje • ✓✓</div>
          </div>
        `;
        chatMessagesStream.appendChild(row);

        const playBtn = row.querySelector(".btn-play-clean");
        if (playBtn) {
          playBtn.addEventListener("click", () => {
            speakText(playBtn.getAttribute("data-audio"));
          });
        }
      } else {
        appendMessage(msg.sender, msg.text, msg.meta, false);
      }
    });

    chatMessagesStream.scrollTop = chatMessagesStream.scrollHeight;
  }

  function renderHistoryList() {
    if (!historyChatList) return;
    historyChatList.innerHTML = "";

    if (chats.length === 0) {
      historyChatList.innerHTML = `
        <div style="font-size: 0.8rem; color: var(--text-muted); padding: 0.75rem 0.5rem; text-align: center;">
          Nenhuma conversa ainda. Clique em "Novo Chat" acima.
        </div>
      `;
      return;
    }

    chats.forEach(chat => {
      const item = document.createElement("div");
      item.className = `history-chat-item ${chat.id === activeChatId ? "active" : ""}`;
      item.setAttribute("data-chat-id", chat.id);

      item.innerHTML = `
        <div class="history-chat-content">
          <span class="history-chat-icon">💬</span>
          <span class="history-chat-title" title="${escapeAttr(chat.title)}">${escapeHTML(chat.title)}</span>
        </div>
        <div class="history-chat-actions">
          <button class="btn-history-action btn-delete-chat" data-chat-id="${escapeAttr(chat.id)}" title="Excluir conversa">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      `;

      item.addEventListener("click", (e) => {
        if (e.target.closest(".btn-delete-chat")) return;
        switchToChat(chat.id);
      });

      const delBtn = item.querySelector(".btn-delete-chat");
      if (delBtn) {
        delBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteChat(chat.id);
        });
      }

      historyChatList.appendChild(item);
    });

    if (historyFarmerName) {
      const p = (typeof AGRO_DATA !== "undefined" && AGRO_DATA.currentProfile) ? AGRO_DATA.currentProfile : {};
      const parts = (p.nome || "Seu Sebastião").trim().split(/\s+/);
      const shortName = ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1])
        ? `${parts[0]} ${parts[1]}`
        : parts[0];
      historyFarmerName.textContent = shortName;
    }
  }

  function switchToChat(chatId) {
    activeChatId = chatId;
    saveChatsToStorage();
    renderActiveChat();
    renderHistoryList();

    // Em telas mobile e tablet (<= 768px), fecha a gaveta para dar foco ao chat
    if (window.innerWidth <= 768) {
      closeHistoryDrawer();
    }
  }

  function startNewChat() {
    const newId = "chat-" + Date.now();
    const newChat = {
      id: newId,
      title: "Nova Conversa",
      timestamp: Date.now(),
      messages: [
        { type: "raw" }
      ]
    };
    chats.unshift(newChat);
    saveChatsToStorage();
    activeChatId = newId;
    renderActiveChat();
    renderHistoryList();

    closeHistoryDrawer();
    showCleanToast("Novo chat iniciado!");
    playCleanBeep("info");

    if (cleanInputField) {
      setTimeout(() => cleanInputField.focus(), 200);
    }
  }

  function deleteChat(chatId) {
    chats = chats.filter(c => c.id !== chatId);
    if (chats.length === 0) {
      chats = [{
        id: "chat-" + Date.now(),
        title: "Nova Conversa",
        timestamp: Date.now(),
        messages: [{ type: "raw" }]
      }];
    }
    if (activeChatId === chatId) {
      activeChatId = chats[0].id;
      renderActiveChat();
    }
    saveChatsToStorage();
    renderHistoryList();
    showCleanToast("Conversa excluída.");
  }

  function clearAllChats() {
    if (confirm("Tem certeza que deseja apagar todo o histórico de conversas?")) {
      chats = [{
        id: "chat-" + Date.now(),
        title: "Nova Conversa",
        timestamp: Date.now(),
        messages: [{ type: "raw" }]
      }];
      activeChatId = chats[0].id;
      saveChatsToStorage();
      renderActiveChat();
      renderHistoryList();
      showCleanToast("Histórico limpo!");
      closeHistoryDrawer();
    }
  }

  function openHistoryDrawer() {
    if (historyBackdrop) {
      historyBackdrop.style.display = "flex";
      renderHistoryList();
    }
  }

  function closeHistoryDrawer() {
    if (historyBackdrop) {
      historyBackdrop.style.display = "none";
    }
  }

  if (btnOpenHistory) {
    btnOpenHistory.addEventListener("click", openHistoryDrawer);
  }
  if (btnCloseHistory) {
    btnCloseHistory.addEventListener("click", closeHistoryDrawer);
  }
  if (historyBackdrop) {
    historyBackdrop.addEventListener("click", (e) => {
      if (e.target === historyBackdrop) closeHistoryDrawer();
    });
  }
  if (btnNewChat) {
    btnNewChat.addEventListener("click", startNewChat);
  }
  if (btnClearAllChats) {
    btnClearAllChats.addEventListener("click", clearAllChats);
  }

  // ==========================================================================
  // 13. Inicialização do App
  // ==========================================================================
  loadStoredProfile();
  updateFarmerContextUI();
  updateWelcomeMessage(AGRO_DATA.currentProfile);
  loadChatsFromStorage();
  renderActiveChat();
  renderHistoryList();

  console.log("🌾 AgroPilot Clean Chatbot ativo.");
});
