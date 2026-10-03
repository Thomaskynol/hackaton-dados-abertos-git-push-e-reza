# AgroPilot — Copiloto Agrícola 24/7 (Hackathon 2026)

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

Um comando. Funciona igual no **Windows, Linux e macOS**:

```bash
git clone <url-do-repo> hackaton-dados-abertos-sql-injection
cd hackaton-dados-abertos-sql-injection

python scripts/agropilot.py
```

Isso instala o que falta (MongoDB, Python, Node), cria o ambiente, baixa a
base de dados e sobe tudo. Depois:

| Endereço | O que é |
|---|---|
| http://localhost:3000 | o aplicativo |
| http://127.0.0.1:8000/docs | a API (Swagger) |
| http://127.0.0.1:8000/api/health | se a API está viva |

Atalhos, se preferir:

```powershell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1
```

```bash
# Linux / macOS
./scripts/agropilot.sh
```

### Sem `sudo` (notebook da faculdade, máquina de aula, container)

O instalador primeiro tenta o gerenciador do SO. Se ele não puder — sem senha,
sem `sudo`, sem pacote no repositório — ele baixa os binários oficiais e deixa
tudo em `~/.local/bin`, sem pedir root e sem escrever em `/usr`. Cobre MongoDB,
`mongosh`, Database Tools (`mongorestore`) e Node.js.

Nada muda na frente: é o mesmo comando.

```bash
python scripts/agropilot.py doctor    # mostra se a máquina é rootless
```

Se preferir garantir que `sudo` nunca é chamado:

```bash
AGROPILOT_SEM_ROOT=1 python scripts/agropilot.py
```

### Comandos do dia a dia

```bash
python scripts/agropilot.py doctor        # o que falta na máquina
python scripts/agropilot.py status        # o que está de pé
python scripts/agropilot.py up / down     # sobe / derruba API e front
python scripts/agropilot.py logs -f       # acompanha os logs ao vivo
python scripts/agropilot.py seed --force  # repõe a base do zero
```

### Se você tem Docker

```bash
docker compose up
```

Sobe Mongo, API e front, e restaura o seed sozinho.

### ⚠️ A base de dados é privada

O dump (~34 MB, com ZARC, PSR, SIGEF, Agrofit, ANA e preços do IBGE) fica na
GitHub Release `data`. Como o repositório é **privado**, o download só funciona
com autenticação. O instalador tenta, sozinho:

1. o arquivo que já estiver em `seed/agropilot.gz`;
2. o GitHub CLI, se você estiver logado (`gh auth login`);
3. um token em `GH_TOKEN`;
4. uma URL aberta em `SEED_URL`.

Se você já tem o arquivo, é só copiar para `seed/agropilot.gz` e rodar de novo.

### 🔑 IA (opcional)

Sem `OPENROUTER_API_KEY` o sistema funciona inteiro, com dados oficiais e
respostas honestas sem IA. Para ligar a leitura em linguagem natural, edite
`back/.env` e preencha a chave.

---

## 🗂️ Comandos úteis

```bash
# regerar o seed limpo a partir do Mongo local
python scripts/gerar_seed.py

# conferir o que falta na máquina
python scripts/agropilot.py doctor
```

---

## 📱 Funcionalidades do MVP Chatbot Clean 24/7

### 1. 💬 Chatbot Conversacional Clean & Minimalista (Foco Total na Conversa)
- **Zero Poluição Visual:** Removemos barras laterais pesadas e dashboards complexos. A tela é focada 100% no diálogo direto com o agricultor, como no WhatsApp ou ChatGPT.
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

### 5. 💰 Mercado, Canais de Venda & Cotações
- Preços em tempo real da saca de 60kg (Soja, Milho, Café Arábica, Feijão e Mandioca) via Cepea/Conab/B3.
- Comparativo entre canais: **Cooperativa local**, **Programas Públicos (PAA / PNAE merenda escolar com +7% sobre mercado)** e **Cerealista Regional**.

### 6. 🎮 Barra de Simulação para a Banca Avaliadora
No topo da tela, botões interativos permitem disparar cenários reais em tempo real para demonstração:
- ⛈️ **Temporal / Frente Fria (75mm em 24h)**
- ❄️ **Risco de Geada (2.8°C na relva)**
- 🦗 **Surto de Cigarrinha / Praga**
- ⏳ **Janela ZARC Fechando em 6 dias**
- ☀️ **Veranico / Estresse Hídrico no Enchimento de Grãos**

### 7. ☀️ Modo Campo (Alto Contraste para Luz Solar)
- Alternância instantânea para paleta de alto contraste, ideal para uso direto sob o sol forte na roça.

---

## 📂 Estrutura de Arquivos

```
hackthon/
├── index.html              # Interface completa responsiva
├── styles/
│   └── main.css            # Design System AgTech (Dark Mode, Modo Campo, Glassmorphism)
├── scripts/
│   ├── data.js             # Base agronômica (ZARC, solos AD1/AD2/AD3, alertas, missões, cotações)
│   ├── copilot-ai.js       # Motor conversacional com regras agronômicas e explicabilidade
│   └── app.js              # Controlador de UI, abas, áudio Web Audio API e simulações
├── docs/
│   └── PRODUCT_SPEC.md     # Documento de Definição de Produto (PRD) completo
└── README.md               # Este guia de apresentação
```
