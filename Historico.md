# 📋 Histórico de Alterações — AgroPilot 24/7

> Registro cronológico de mudanças realizadas no projeto para facilitar explicações a colaboradores e apresentadores.

---

## [2026-10-02] — Sessão de ajustes de UI/UX

### 1. 🔤 Placeholder da caixa de pergunta não transborda mais
**Arquivo:** `styles/main.css`  
**Problema:** Em telas pequenas (mobile/tablet), o texto do placeholder da barra de input principal extrapolava a caixa e ficava visualmente "vazando".  
**Solução:**
- Adicionado `min-width: 0` ao `.clean-input-field` para permitir que o campo encolha corretamente dentro do flexbox.
- Adicionado `overflow: hidden`, `text-overflow: ellipsis` e `white-space: nowrap` tanto no campo quanto no `::placeholder`.
- O tamanho da fonte do placeholder agora usa `clamp(0.78rem, 2.5vw, 1.02rem)`, encolhendo proporcionalmente à largura da janela.

---

### 2. ➡️ Setas da barra de perguntas rápidas ocultadas no mobile/tablet
**Arquivo:** `styles/main.css`  
**Problema:** Em telas ≤768px (mobile e tablet), as setas de navegação das chips (perguntas frequentes) poluíam a interface e eram desnecessárias para uso por toque.  
**Solução:**
- Adicionado `@media (max-width: 768px)` com `display: none !important` para `.btn-scroll-chips`.
- A barra continua sendo navegável com arrasto do dedo (touch drag, já implementado via JS).
- A scrollbar horizontal dos chips também é ocultada no mobile para interface mais limpa.
- As setas continuam visíveis em telas maiores (>=769px, desktop).

---

### 3. 🌤️ Caixas de áudio e "Por que alertei você" agora seguem paleta no modo claro
**Arquivo:** `styles/main.css`  
**Problema:** Ao ativar o Modo Campo (luz solar / branco), as caixas de áudio do Copiloto (.clean-voice-bar) e o card de explicação (.clean-explain-card — "Por que alertei você • XX% Confiança") mantinham fundo escuro rgba(0,0,0,0.25), ficando incompatíveis com o tema claro.  
**Solução:**
- No body.sunlight-mode, a .clean-voice-bar recebe fundo verde esmeralda levíssimo e borda esverdeada, integrando-se à paleta do site.
- O .clean-explain-card recebe fundo verde ainda mais suave e borda equivalente.
- O texto do sumário .explain-summary passa para #047857 (verde escuro legível) e os detalhes .explain-details para #334155 (slate escuro), mantendo alto contraste no modo claro.

---

### 4. 📝 Campos do formulário de onboarding agora começam vazios
**Arquivo:** `index.html`, `scripts/app.js`  
**Problema:** Ao abrir o formulário de cadastro pela primeira vez, os campos "Cultura da Safra" e "Tipo de Solo" já vinham pré-selecionados e o campo "Área" exibia 14.5 por padrão.  
**Solução:**
- Adicionada `<option value="" disabled selected>` como placeholder em cada select do formulário.
- Na função loadStoredProfile(), quando não há perfil salvo, culturaAtual e tipoSolo agora são passados como "" em vez dos valores padrão.
- O fallback || 14.5 do campo Área foi removido — o campo inicia vazio.

---

*Arquivo mantido automaticamente pelo assistente de desenvolvimento. Cada sessão de modificação gera uma nova entrada aqui.*

---

### 5. 🐛 [BUG CRÍTICO] Tela de boas-vindas não avançava para o chat ao clicar em "Começar Monitoramento"
**Arquivo:** `styles/main.css`  
**Problema:** Ao preencher o formulário e clicar no botão de submit, a tela de onboarding permanecia visível — o site ficava travado na tela inicial sem avançar para o chat.  
**Causa raiz:** O JavaScript usa `onboardingScreen.classList.add("hidden")` para esconder a tela de onboarding, mas a classe `.hidden` **não existia em nenhum lugar do CSS**. Isso fazia com que adicionar a classe ao elemento não tivesse nenhum efeito visual.  
**Solução:**
- Adicionada a classe utilitária `.hidden { display: none !important; }` no `styles/main.css`, logo após o bloco de reset `* { ... }`.
- Agora ao submeter o formulário, a tela desaparece corretamente e o chat fica visível.

---

### 6. 🛠️ [CORREÇÃO COMPLETA] Resolução definitiva do clique do botão de início / mudança de tela
**Arquivos:** `scripts/data.js`, `scripts/copilot-ai.js`, `scripts/app.js`, `index.html`, `styles/main.css`  
**Problema:** Ao clicar no botão "Começar Monitoramento 24/7", a interface não avançava para o chat ("não muda para outra página") e permanecia na mesma tela de onboarding.  
**Causas Raízes Identificadas:**
1. **Scripts essenciais ausentes na branch:** Os arquivos `scripts/data.js` e `scripts/copilot-ai.js` estavam faltando na branch `gabriel/login` (retornando erro HTTP 404). Isso causava uma exceção fatal `ReferenceError: AGRO_DATA is not defined` no JavaScript no momento da submissão, interrompendo o código antes de esconder o modal.
2. **Bloqueio nativo do formulário HTML5:** O uso do atributo `required` nos campos impedia o submit caso algum campo estivesse vazio, travando silenciosamente a transição.
3. **Falta de listener direto no botão:** Apenas o evento `submit` do form estava mapeado, sem interceptação direta do clique no botão `#btn-submit-onboarding`.
4. **Resiliência do CSS de ocultação:** A regra `.onboarding-overlay.hidden` dependia apenas de opacidade e visibilidade sem garantir `display: none !important`.

**Soluções Aplicadas:**
- Restaurados os arquivos `scripts/data.js` e `scripts/copilot-ai.js` da branch de integração, garantindo que `AGRO_DATA` e `window.agroCopilot` existam.
- Adicionado `novalidate` ao formulário e removido `required` bloqueador, provendo valores padrão seguros no JavaScript caso o usuário avance sem preencher algum campo.
- Criada a função `handleOnboardingSubmit` com escuta dupla (evento de `submit` do formulário E evento de `click` direto no botão `#btn-submit-onboarding`).
- Ocultação imediata e à prova de falhas: o JavaScript agora aplica `classList.add("hidden")`, `style.display = "none"`, `opacity = "0"`, `visibility = "hidden"`, `pointerEvents = "none"` e `aria-hidden="true"`.
- Protegidas as funções `updateFarmerContextUI` e `updateWelcomeMessage` contra valores vazios ou ausência de dados, evitando qualquer quebra em runtime.

---

### 7. 💬 [NOVA FUNCIONALIDADE & UI] Histórico de Chats Estilo ChatGPT e Limpeza Completa da Tela de Boas-Vindas
**Arquivos:** `index.html`, `styles/main.css`, `scripts/app.js`, `Historico.md`  
**Solicitação:**
1. Garantir que todas as caixas de texto e opções da tela de boas-vindas iniciem 100% vazias para preenchimento do produtor.
2. Criar um histórico de conversas lateral no estilo do ChatGPT, com as cores e identidade visual do site (verde esmeralda, modo escuro e modo campo/luz solar).
3. Incluir botão proeminente de "+ Novo Chat".
4. Deixar o layout totalmente responsivo e redimensionável para PC, tablet e smartphone.
5. Posicionar o gatilho de abertura no canto superior esquerdo, exatamente ao lado esquerdo da logo, como um botão hambúrguer idêntico ao já existente no canto direito.

**Implementações Realizadas:**
- **Campos do Onboarding 100% Vazios:**
  - Ajustada a função `populateOnboardingForm` para resetar os valores dos selects `onb-cultura` e `onb-solo` para a opção placeholder (`""`) mesmo quando chamados com strings vazias.
  - Na inicialização `loadStoredProfile()` e no botão de reabertura "Nova Propriedade / Trocar Produtor", todos os 7 campos (nome, telefone, gleba, município, cultura, solo e área) são forçados a iniciar limpos.
- **Botão Hambúrguer no Topo Esquerdo:**
  - Adicionado o botão `#btn-open-history` à esquerda da logo `.nav-brand`, dentro de um contêiner `.nav-left-group`, mantendo o mesmo tamanho (32px), bordas arredondadas e ícone SVG idêntico ao menu da direita.
- **Gaveta Lateral de Histórico (ChatGPT-style):**
  - Criado o componente `#history-backdrop` e o painel deslizante `#history-panel` que desliza da esquerda para a direita (`slideDrawerLeft`).
  - Botão destacado **"+ Novo Chat" (`#btn-new-chat`)**, estilizado com verde esmeralda, sombra suave e feedback visual ao passar o mouse ou clicar.
  - Lista de conversas categorizadas e dinâmicas com ícone de balão, título da conversa, destaque do chat ativo (`.active`) e botão de lixeira (🗑️) para excluir conversas individuais.
  - Botão no rodapé para limpar todo o histórico de conversas (`#btn-clear-all-chats`).
- **Gerenciador de Múltiplos Chats no JavaScript:**
  - Criação de novas conversas com identificador único (`chat-timestamp`).
  - Salvamento e persistência de todas as conversas e do chat ativo no `localStorage`.
  - Nomeação automática: quando o produtor envia a primeira pergunta em um novo chat, o título da conversa é atualizado dinamicamente com o texto da pergunta na barra lateral.
  - Alternância imediata entre conversas com reconstrução do fluxo de mensagens e reativação dos reprodutores de áudio e botões de ação.
  - Em telas de tablet e mobile (≤768px), selecionar uma conversa ou criar um novo chat fecha automaticamente a gaveta para que o usuário interaja direto com a conversa.
- **Responsividade e Paleta de Cores:**
  - Total integração com as variáveis do tema escuro e do Modo Campo (luz solar / branco).
  - Painel com largura ajustada para PC (320px), tablet (300px / 82vw) e mobile (88vw), com espaçamentos otimizados para toque.


