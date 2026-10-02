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

  // Onboarding Inicial
  const onboardingScreen = document.getElementById("onboarding-screen");
  const onboardingForm = document.getElementById("onboarding-form");
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
    const p = AGRO_DATA.currentProfile;
    const c = AGRO_DATA.culturas[p.culturaAtual] || AGRO_DATA.culturas.soja;

    const parts = p.nome.trim().split(/\s+/);
    let shortName = parts[0];
    if ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) {
      shortName = `${parts[0]} ${parts[1]}`;
    }

    if (navFarmerName) navFarmerName.textContent = shortName;
    if (navFarmerCulture) navFarmerCulture.textContent = `${c.nome.split(" ")[0]} V4`;
    if (navFarmerCity) navFarmerCity.textContent = p.municipio.split(" - ")[0];

    if (drawerFarmName) drawerFarmName.textContent = p.propriedade;
    if (drawerFarmMeta) drawerFarmMeta.textContent = `${p.municipio} • ${p.areaHa} ha`;

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
    const cultura = AGRO_DATA.culturas[profile.culturaAtual] || AGRO_DATA.culturas.soja;
    const parts = profile.nome.trim().split(/\s+/);
    let shortName = parts[0];
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
    if (onbCultura && profile.culturaAtual) onbCultura.value = profile.culturaAtual;
    if (onbSolo && profile.tipoSolo) onbSolo.value = profile.tipoSolo;
    if (onbArea) onbArea.value = profile.areaHa || "";
  }

  function loadStoredProfile() {
    const saved = localStorage.getItem("agropilot_profile");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        AGRO_DATA.currentProfile = { ...AGRO_DATA.currentProfile, ...parsed };
        populateOnboardingForm(AGRO_DATA.currentProfile);
      } catch (e) {
        console.warn("Erro ao ler perfil salvo:", e);
      }
    } else {
      // Deixar os campos limpos para a apresentação / primeiro preenchimento
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
  }

  // Submissão do Formulário de Onboarding
  if (onboardingForm) {
    onboardingForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const newProfile = {
        nome: onbNome.value.trim(),
        telefone: onbTelefone.value.trim(),
        propriedade: onbGleba.value.trim(),
        municipio: onbMunicipio.value.trim(),
        culturaAtual: onbCultura.value,
        tipoSolo: onbSolo.value,
        areaHa: parseFloat(onbArea.value) || 14.5,
        faseCiclo: "vegetativo",
        proagroAtivo: true,
        pronafElegivel: true
      };

      AGRO_DATA.currentProfile = { ...AGRO_DATA.currentProfile, ...newProfile };
      localStorage.setItem("agropilot_profile", JSON.stringify(AGRO_DATA.currentProfile));
      localStorage.setItem("agropilot_configured", "true");

      if (window.agroCopilot) {
        window.agroCopilot.setFarmerProfile(AGRO_DATA.currentProfile);
      }

      updateFarmerContextUI();
      updateWelcomeMessage(AGRO_DATA.currentProfile);

      if (onboardingScreen) {
        onboardingScreen.classList.add("hidden");
      }

      const parts = newProfile.nome.split(/\s+/);
      const shortName = ((parts[0].toLowerCase() === "seu" || parts[0].toLowerCase() === "dona" || parts[0].toLowerCase() === "sr." || parts[0].toLowerCase() === "sra.") && parts[1]) 
        ? `${parts[0]} ${parts[1]}` 
        : parts[0];

      showCleanToast(`Propriedade configurada! Bem-vindo, ${shortName}!`);
      playCleanBeep("info");
    });
  }

  // Botão na gaveta para reabrir tela de onboarding
  if (btnReopenOnboarding) {
    btnReopenOnboarding.addEventListener("click", () => {
      closeDrawer();
      populateOnboardingForm(AGRO_DATA.currentProfile);
      if (onboardingScreen) {
        onboardingScreen.classList.remove("hidden");
      }
    });
  }

  // ==========================================================================
  // 12. Inicialização do App
  // ==========================================================================
  loadStoredProfile();
  updateFarmerContextUI();
  updateWelcomeMessage(AGRO_DATA.currentProfile);

  // Conectar botões de áudio iniciais
  document.querySelectorAll(".btn-play-clean").forEach(btn => {
    btn.addEventListener("click", () => {
      const audioMsg = btn.getAttribute("data-audio");
      speakText(audioMsg);
    });
  });

  console.log("🌾 AgroPilot Clean Chatbot ativo.");
});
