# 🌾 Histórico e Mapeamento da Branch `caue-backend-mvp`

**Repositório:** `Thomaskynol/hackaton-dados-abertos-sql-injection`  
**Branch:** `caue-backend-mvp`  
**Atualizado em:** 02 de Outubro de 2026  
**Status:** Integrada, testada (9/9 testes passando) e sincronizada com o GitHub

---

## 1. Visão Geral da Branch

A branch **`caue-backend-mvp`** é responsável pela implementação completa da infraestrutura de **Backend (API REST FastAPI)**, modelagem dos contratos de dados, testes automatizados e pela **integração ponta a ponta** com o Frontend do Copiloto Agrícola (**AgroPilot 24/7**), incluindo conexão real com MongoDB.

---

## 2. O Que Cada Parte da Branch Está Fazendo

### 2.1 Backend (`back/app/`)

O backend foi construído em **FastAPI (Python 3.12)** com validação estrita via **Pydantic** e suporte a banco de dados real (MongoDB) com **fallback automático para mocks** quando o banco não está disponível.

```
back/
├── app/
│   ├── main.py                  # Ponto de entrada, CORS e registro dos roteadores
│   ├── db.py                    # [NOVO] Conexão lazy ao MongoDB — retorna None se indisponível
│   ├── dados_reais.py           # [NOVO] Consultas reais ao MongoDB (ZARC e Agrofit)
│   ├── mock.py                  # Dados mockados — fallback quando MongoDB está fora
│   ├── core/
│   │   └── router_intencao.py   # Motor léxico de classificação de intenções agronômicas
│   ├── routes/
│   │   ├── health.py            # GET /api/health — liveness check
│   │   ├── chat.py              # POST /api/chat — MongoDB real + fallback mock
│   │   ├── onboarding.py        # POST /api/onboarding — fluxo guiado de cadastro
│   │   ├── produtor.py          # GET/POST /api/produtor — lê/grava no MongoDB
│   │   └── alertas.py           # GET/POST /api/alertas — listagem e simulação
│   └── schemas/
│       ├── chat.py              # Modelos Pydantic de request/response do chat
│       ├── produtor.py          # Modelos de lavouras, produtor, onboarding e respostas
│       ├── alertas.py           # Modelos de alertas e simulação
│       └── intencoes.py         # Enum tipado de intenções agronômicas
├── tests/
│   └── test_contrato.py         # 9 testes automatizados de integração (100% passando)
├── pytest.ini                   # pythonpath=. para execução direta de pytest
├── requirements.txt             # Dependências: FastAPI, Uvicorn, Pydantic, pymongo, etc.
└── .env.example                 # Variáveis de ambiente: MONGO_URL, CORS_ORIGINS, GROQ_API_KEY
```

#### Detalhamento dos Componentes:

* **`back/app/main.py`**:
  * Inicializa o FastAPI (`API Agro Familiar MVP`).
  * Configura **CORS** para que o frontend (`:8080`) consuma a API (`:8000`) sem bloqueios.
  * Registra os 5 roteadores em `/api`.

* **`back/app/db.py`** *(novo — integração MongoDB)*:
  * Mantém uma conexão singleton (`MongoClient`) ao MongoDB (`agropilot`).
  * `get_db()` retorna `None` silenciosamente quando:
    * `pymongo` não está instalado.
    * O Mongo não está acessível em `MONGO_URL` (timeout de 2s).
  * Todos os endpoints que usam o banco testam `if db is None` e caem no mock — **API nunca quebra**.

* **`back/app/dados_reais.py`** *(novo — consultas reais)*:
  * `buscar_janelas(db, cultura, ibge)`: Consulta a coleção `zarc` por município IBGE e cultura, ordenando pelas janelas de menor risco climático.
  * `buscar_produtos(db, cultura, alvo)`: Consulta a coleção `agrofit` por cultura e praga-alvo (com alias: `míldio` → `plasmopara`).
  * `extrair_cultura()` / `extrair_alvo()`: NLP leve determinístico para identificar a cultura e o alvo na mensagem do produtor.
  * `produto_resumo()`: Converte documento Mongo em dict `{nome, classe, organico}` para o frontend.

* **`back/app/routes/chat.py`** *(atualizado — dados reais + fallback)*:
  * `PRAGA`: Tenta `_praga_real()` → Agrofit no Mongo. Se não há dados → `MOCK_CHAT_PRAGA`.
  * `PLANEJAMENTO`: Tenta `_planejamento_real()` → ZARC no Mongo. Se não há dados → `MOCK_CHAT_PLANEJAMENTO`.
  * `CLIMA`, `SAUDACAO`, `PERFIL`, `VENDA`: Retornam respostas diretas (mock ou texto fixo).
  * `NAO_ENTENDI`: Fallback com sugestões guiadas.

* **`back/app/routes/produtor.py`** *(atualizado — persistência real)*:
  * `GET /api/produtor/{id}`: Busca primeiro na coleção `produtores` do Mongo. Se não encontrar → mock.
  * `POST /api/produtor`: Salva/atualiza o produtor na coleção `produtores` via `upsert` por telefone.

* **`back/app/routes/alertas.py`**:
  * `GET /api/alertas/{id}`: Lista alertas ativos (mock — integração INMET/ZARC futura).
  * `POST /api/alertas/simular`: Simula alerta por tipo (geada, seca, praga) para demonstração.

* **`back/tests/test_contrato.py`**:
  * **9 testes** validando todos os endpoints. O fallback mock garante que os testes passam mesmo sem MongoDB.

---

### 2.2 Banco de Dados — MongoDB (`docker-compose.yml`)

```
docker-compose.yml          # MongoDB 7 + FastAPI API prontos para subir juntos
```

**Coleções relevantes no banco `agropilot`:**

| Coleção | Origem | Conteúdo |
|---|---|---|
| `zarc` | MAPA/ZARC 2025/26 | Janelas de plantio por município IBGE, cultura, solo e manejo |
| `agrofit` | Agrofit/MAPA | Produtos registrados por cultura e praga, classe toxicológica |
| `produtores` | App | Perfis dos produtores rurais cadastrados via onboarding |
| `municipios` | IBGE | Códigos IBGE, nomes e UFs dos municípios |

**Para subir o ambiente completo:**
```bash
# Sobe o MongoDB e a API juntos:
docker compose up

# A API estará em: http://localhost:8000/docs
# O MongoDB estará em: mongodb://localhost:27017
```

**Para carregar os dados reais (executado pela branch `correlacao-de-dados`):**
```bash
# Na raiz do projeto, com o Mongo rodando:
python correlacao/load_mongo.py
```

---

### 2.3 Frontend — Interface Copiloto 24/7

```
index.html           # Interface principal do chat AgroPilot 24/7
scripts/
  app.js             # Controlador: conecta ao FastAPI (:8000) com fallback local
  copilot-ai.js      # Motor conversacional local (fallback)
  data.js            # Base de conhecimento agronômica local (ZARC, alertas, cotações)
styles/
  main.css           # Design System AgTech (Dark Mode e Modo Campo)
```

* **`scripts/app.js`** — Integração Front ↔ Back:
  * `checkBackendHealth()`: Testa `GET /api/health` ao iniciar e atualiza badge de status.
  * `sendUserMessage()`: Envia `POST /api/chat`. Se a API falha → usa `copilot-ai.js` localmente.
  * `triggerCleanSimulation()`: Chama `POST /api/alertas/simular` e exibe o alerta no chat.

---

### 2.4 Documentação

```
CONTRATO_API.md                  # Contrato formal dos endpoints (Front ↔ Back)
docs/dicionario-de-dados.md      # Dicionário das bases abertas: Agrofit, ZARC, SISSER
docs/PRODUCT_SPEC.md             # Especificação de produto e filosofia do AgroPilot
README.md                        # Guia unificado de execução (Back + Front + Docker)
historico.me / historico.md      # Este arquivo — histórico técnico da branch
```

---

## 3. Resumo Cronológico dos Commits

| Commit | Mensagem | O que fez |
|---|---|---|
| `89ed536` | `feat(backend): implement FastAPI MVP` | Estrutura inicial: rotas, schemas, mock, 9 testes |
| `357fe3f` | `feat(backend): response_models + pytest.ini` | Tipagem Pydantic, Swagger docs, pytest configurado |
| `8ead20e` | `merge: origin/main` | Dicionário de dados e .gitignore |
| `7f0bb01` | `merge: marcelo-integracao-sistema` | Interface AgroPilot 24/7 integrada |
| `7c7be93` | `feat(frontend): connect to FastAPI` | app.js conecta ao backend com fallback resiliente |
| `5c41925` | `docs: historico` | Primeiros arquivos historico.me/md |
| `f98b913` | `bacoDeDados(commit1)` | Commit local de banco de dados (pendente detalhes) |
| *(atual)* | `feat(backend): MongoDB integration` | db.py, dados_reais.py, chat/produtor com dados reais, docker-compose |

---

## 4. Diagrama de Fluxo de Dados

```
Produtor Rural → index.html (chat)
                      │
                      ▼ POST /api/chat
                  FastAPI (back/)
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    MongoDB (:27017)         Mock (mock.py)
    ├── zarc                 (fallback se
    ├── agrofit              Mongo offline)
    └── produtores
```

---

## 5. Variáveis de Ambiente

Copie `back/.env.example` para `back/.env` e preencha:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
MONGO_URL=mongodb://localhost:27017
LLM_PROVIDER=groq
GROQ_API_KEY=<sua-chave-groq>   # opcional — para LLM real
```
