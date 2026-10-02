# 🌾 AgroPilot — Copiloto Agrícola 24/7 (Hackathon 2026)

> **"O pequeno produtor não pode errar. Ele não tem margem para errar."**

O **AgroPilot** é um copiloto agronômico 24/7 proativo e explicável, desenhado especificamente para a agricultura familiar e pequenos/médios produtores rurais. Ele acompanha toda a jornada da safra — **da compra da semente até o momento da venda** — prevenindo erros críticos de manejo, clima, fitossanidade e crédito rural antes que aconteçam.

---

## 🎯 Por Que o AgroPilot é Diferente?

| O que NÃO é | O que o AgroPilot É |
|---|---|
| ❌ Um site informativo estático | ✅ Um assistente diário que envia alertas antes dos desastres ocorrerem |
| ❌ Um dashboard cheio de gráficos vazios | ✅ Focado em **ações práticas e missões de campo** |
| ❌ Um ChatGPT genérico | ✅ Integrado ao **ZARC (Zoneamento Agrícola de Risco Climático)** oficial da Embrapa/MAPA, dados de radar INMET e solo local (AD1/AD2/AD3) |
| ❌ Um app passivo que só responde perguntas | ✅ **Proatividade 24/7**: ele avisa você sobre frentes frias, tempestades, veranicos e pragas sem você precisar perguntar |

---

## 🚀 Como Executar Localmente

### 1. Backend (FastAPI)

```bash
cd back

# Ative o ambiente virtual
source .venv/bin/activate

# Execute a API com reload automático
uvicorn app.main:app --reload --port 8000

# Documentação interativa Swagger:
# http://localhost:8000/docs

# Executar testes unitários e de contrato:
pytest
```

### 2. Frontend (AgroPilot Copilot UI)

Como foi construído em arquitetura web nativa (HTML5, Vanilla CSS com Design System AgTech e JavaScript ES6+), não há dependências pesadas de compilação:

```bash
# Na raiz do projeto:
python3 -m http.server 8080
# ou simplesmente abra index.html no navegador

# Acesse no navegador:
# http://localhost:8080
```

---

## 📱 Funcionalidades do MVP Chatbot Clean 24/7

### 1. 💬 Chatbot Conversacional Clean & Minimalista (Foco Total na Conversa)
- **Zero Poluição Visual:** Tela focada 100% no diálogo direto com o agricultor, como no WhatsApp.
- **Barra Superior Discreta:** 
  - Logo sutil com indicador de pulso verde (*Online 24/7*).
  - Pílula central com o produtor ativo (*👤 Seu Sebastião • Soja • Rio Verde*), que abre um painel lateral deslizante (*Drawer*) sob demanda.
  - Menu suspenso discreto (*⚡ Simular Cenário ▾*) para os jurados do Hackathon testarem eventos sem poluir a visão do agricultor.
- **Linguagem Natural com Contexto Agrícola:** Identifica o produtor pelo nome (*Seu Sebastião*), área (*14.5 ha*), relevo e riscos regionais.
- **Acessibilidade por Áudio (Princípio #6):** Barra de notas de voz compacta estilo WhatsApp com sintetizador de voz nativo (`SpeechSynthesis`).
- **Transparência e Explicabilidade Compacta (Princípio #4):** Pílula expansível (*"💡 Por que alertei você • 95% Confiança ▾"*), mantendo o balão de mensagem limpo e legível.

### 2. 📸 Diagnóstico Visual por Foto no Campo
- O produtor pode enviar ou simular o envio de fotos da lavoura diretamente no chat:
  - **Lagarta na Folha:** Análise de desfolha (MIP) e cálculo de dano econômico (recomenda controle biológico com *Bt* apenas se atingir o limiar).
  - **Ferrugem Asiática:** Alerta urgente sobre esporos e recomendação preventiva de fungicida com indicação de receituário agronômico.
  - **Clorose / Solo:** Diagnóstico de carência nutricional ou estresse hídrico no solo AD3.

### 3. 🌾 Acesso Integrado aos Dados da Safra (Modais Rápidos)
- **📊 Calendário ZARC Decendial:** Tabela oficial com matriz de risco (20%, 30%, 40%) e elegibilidade do Seguro Proagro Mais.
- **🚜 Missões de Campo do Dia:** Checklists práticos de manejo (desobstrução de terraços, pano de batida, calibração de bicos).
- **💰 Cotações Cepea/Conab & Canais de Venda:** Preços em tempo real e comparativo com compras públicas (PAA/PNAE merenda escolar com remuneração de até +7% a +10%).

### 4. 🎮 Barra de Simulação para a Banca Avaliadora
No topo da tela, botões interativos permitem disparar cenários reais em tempo real para demonstração:
- ⛈️ **Temporal / Frente Fria (75mm em 24h)**
- ❄️ **Risco de Geada (2.8°C na relva)**
- 🦗 **Surto de Cigarrinha / Praga**
- ⏳ **Janela ZARC Fechando em 6 dias**
- ☀️ **Veranico / Estresse Hídrico no Enchimento de Grãos**

### 5. ☀️ Modo Campo (Alto Contraste para Luz Solar)
- Alternância instantânea para paleta de alto contraste, ideal para uso direto sob o sol forte na roça.

---

## 📂 Estrutura Integrada do Projeto

```
hackthon/
├── back/                       # Backend FastAPI (API REST)
│   ├── app/
│   │   ├── main.py             # Aplicação FastAPI e CORS
│   │   ├── routes/             # Endpoints /api/chat, /api/health, /api/onboarding, /api/produtor, /api/alertas
│   │   ├── schemas/            # Schemas Pydantic tipados
│   │   ├── core/               # Regras de negócio e roteador de intenções
│   │   └── mock.py             # Mock de dados para desacoplamento
│   ├── tests/                  # Testes automatizados do contrato (pytest)
│   └── pytest.ini              # Configuração de execução de testes
├── docs/                       # Especificações e Dicionários
│   ├── PRODUCT_SPEC.md         # Especificação de produto e filosofia
│   └── dicionario-de-dados.md  # Dicionário oficial ZARC, Agrofit e SISSER
├── index.html                  # Interface Web Copilot 24/7
├── styles/
│   └── main.css                # Design System AgTech (Dark Mode e Modo Campo)
├── scripts/
│   ├── data.js                 # Base agronômica e ZARC
│   ├── copilot-ai.js           # Motor de inteligência conversacional
│   └── app.js                  # Controlador de UI e sintetizador de voz
├── CONTRATO_API.md             # Contrato de API entre Front e Back
├── INTEGRACAO_SISTEMA.md       # Relatório de integração do sistema
└── README.md                   # Documentação geral do projeto
```
