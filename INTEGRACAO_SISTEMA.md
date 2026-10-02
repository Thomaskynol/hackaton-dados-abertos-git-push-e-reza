# 🌾 AgroPilot 24/7 — Relatório de Integração do Sistema

**Branch:** `marcelo-integracao-sistema`  
**Data:** 02 de Outubro de 2026  
**Projeto:** AgroPilot — Copiloto Agrícola 24/7 (Hackathon)

---

## 1. Resumo Executivo

Este documento detalha todas as etapas, decisões técnicas, arquiteturais e de design realizadas no desenvolvimento do **AgroPilot 24/7**. O sistema foi construído a partir da premissa fundamental:

> *"O pequeno produtor não pode errar. Ele não tem margem para errar."*

O objetivo principal é mitigar erros do pequeno produtor rural e auxiliá-lo a obter o melhor resultado de sua produção com base em sua realidade específica, acompanhando toda a jornada **desde a compra da semente até a comercialização da safra**.

---

## 2. Histórico de Desenvolvimento Baseado nos Prompts

### Etapa 1: Definição do Produto e Arquitetura Técnica
- **Arquivo Criado:** `docs/PRODUCT_SPEC.md`
- **Conteúdo:** Estruturação completa da filosofia do produto, os **6 princípios fundamentais** (Universal, Proativo, Personalizado, Explicável, Seguro e Acessível), os anti-padrões (o que o AgroPilot *NÃO* é), e o ciclo de 5 fases da safra (*Comprar Semente, Plantar Janela, Cuidar/Monitorar, Colher no Momento, Vender no Melhor Canal*).

### Etapa 2: Base de Conhecimento Agronômica
- **Arquivo Criado:** `scripts/data.js`
- **Conteúdo:**
  - Base de dados de culturas brasileiras (Soja, Milho Safrinha, Café Arábica, Feijão Carioca e Mandioca).
  - Tabela oficial do **ZARC (Zoneamento Agrícola de Risco Climático)** baseada na Portaria MAPA nº 142/2024 para o município de Rio Verde - GO, categorizando os riscos por decêndio (Out/D1 a Dez/D2) para solos **AD1 (Arenoso)**, **AD2 (Médio)** e **AD3 (Argiloso)**.
  - Regras de elegibilidade para cobertura a 100% pelo **Seguro Proagro Mais** (risco ≤ 20%).
  - Feed de alertas proativos com severidades, causas e ações preventivas.
  - Missões de campo práticas (ex: *Desobstrução de terraços*, *Pano de batida MIP*, *Calibração de pulverizador*).
  - Cotações diárias de mercado (Cepea/Esalq, Conab, B3) e comparativo de canais (Cooperativas vs. Programas Públicos PAA/PNAE da merenda escolar).

### Etapa 3: Motor de Inteligência do Copiloto Agrícola
- **Arquivo Criado:** `scripts/copilot-ai.js`
- **Conteúdo:**
  - Processamento de linguagem natural focado no pequeno produtor, tratando-o de forma acolhedora e personalizada (*"Seu Sebastião"*).
  - **Explicabilidade Transparente:** Todas as recomendações exibem a fonte oficial (Embrapa/ZARC), a justificativa agronômica e o nível de confiança (%).
  - **Salvaguardas Éticas e de Segurança:** Nunca receita agrotóxicos sem indicação de receituário de responsável técnico e prioriza manejo biológico integrado (MIP).
  - **Diagnóstico Visual por Foto (`analyzeImage`):** Algoritmo que simula a análise de fotos enviadas pelo produtor:
    - *Lagarta na folha:* calcula a desfolha e avalia se atingiu o limiar de dano econômico antes de recomendar controle.
    - *Ferrugem asiática:* emite alerta de alto risco fitossanitário preventivo.
    - *Clorose/solo:* diagnostica início de deficiência mineral ou estresse hídrico.
  - **Áudio Nativo:** Geração de texto para síntese de voz (TTS) reproduzível em estilo nota de voz de WhatsApp.

### Etapa 4: Foco no MVP Chatbot
- **Prompt:** *"Nosso MVP será um chatbot."*
- **Transformação:** A aplicação foi reorientada para colocar o **Chatbot no centro absoluto da experiência**, eliminando a necessidade de navegação por abas complexas e permitindo que o produtor resolva tudo por conversa e áudio.

### Etapa 5: Refatoração para Interface Clean & Minimalista
- **Prompt:** *"Tem muitas informações nessa tela, preciso que seja criado uma interface mais clean."*
- **Melhorias de Design:**
  1. **Remoção de Poluição Visual:** Eliminou-se a barra lateral fixa pesada e banners excessivos. O chat agora respira no centro da tela (`max-width: 860px`), gerando sensação de clareza imediata similar ao WhatsApp ou ChatGPT.
  2. **Barra Superior Minimalista:** Contém apenas o logo sutil, o status *Online 24/7*, uma pílula central com a gleba do produtor (*"👤 Seu Sebastião • Soja V4 • Rio Verde"*), o botão de modo campo (`☀️`) e um menu suspenso discreto para a banca (`⚡ Simular`).
  3. **Drawer Deslizante sob Demanda:** Informações profundas da fazenda, tabela decendial ZARC e checklists de missões agora ficam recolhidos em um painel lateral deslizante, que só abre quando o produtor clica na pílula ou no menu.
  4. **Cápsula de Entrada Flutuante:** Barra de entrada arredondada estilo iMessage com atalhos de sugestão rápida (*"Posso plantar semana que vem?"*, *"Vi uma lagarta"*, etc.), botão de foto `📷`, microfone `🎙️` e botão de envio `➤`.
  5. **Modo Campo (Sunlight Mode):** Botão para alternar instantaneamente para paleta de alto contraste para facilitar a leitura sob sol forte.

---

## 3. Estrutura de Arquivos do Projeto

```
hackthon/
├── index.html                   # Interface web minimalista centrada no Chatbot MVP
├── styles/
│   └── main.css                 # Design System AgTech Clean (Dark mode, Modo Campo, Animações)
├── scripts/
│   ├── data.js                  # Base de dados (ZARC Portaria 142/2024, solos AD1/AD2/AD3, cotações)
│   ├── copilot-ai.js            # Motor de IA agronômica com explicabilidade e visão computacional
│   └── app.js                   # Controlador da aplicação (chat, áudio, drawer, simulações)
├── docs/
│   └── PRODUCT_SPEC.md          # Documento de Especificação de Produto (PRD) expandido
├── INTEGRACAO_SISTEMA.md        # Este documento detalhado de integração
└── README.md                    # Documentação geral e guia rápido de execução
```

---

## 4. Como Executar e Validar

O servidor local já está configurado na porta `8080`:

```bash
# Execução nativa (sem dependências externas):
python3 -m http.server 8080

# URL de Acesso no Navegador:
http://localhost:8080
```

---

## 5. Roteiro de Demonstração para a Banca Avaliadora

1. **Apresentação Inicial:** Mostrar a interface limpa e acolhedora que cumprimenta *"Seu Sebastião"* e já emite um **alerta proativo de chuva forte de 75mm em 48h** com nota de voz de áudio WhatsApp.
2. **Proatividade na Prática:** Clicar no menu `⚡ Simular` no topo e disparar o cenário *"Frente Fria / Temporal"* ou *"Alerta de Geada"*. O copiloto imediatamente notifica o produtor e orienta as medidas de proteção antes da perda de insumos.
3. **Consulta ZARC:** Clicar na pergunta rápida *"Posso plantar semana que vem?"*. O copiloto responde consultando a Portaria ZARC 142/2024, indicando risco de 20% e cobertura 100% do Seguro Proagro.
4. **Diagnóstico por Foto:** Clicar no ícone de câmera `📷` e escolher *"Lagarta na Folha"*. O AgroPilot faz a identificação (*Anticarsia gemmatalis*), calcula a desfolha (12%) e orienta não gastar dinheiro com defensivos químicos prematuros.
5. **Drawer de Dados da Safra:** Clicar na pílula central do cabeçalho para exibir o painel deslizante com os dados da gleba e a tabela decendial ZARC.
6. **Modo Campo:** Clicar no ícone de sol `☀️` para demonstrar a alta legibilidade sob luz solar direta na roça.
