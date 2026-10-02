# 🌾 Histórico e Mapeamento Consolidado da Branch `caue-backend-mvp`

**Repositório:** `Thomaskynol/hackaton-dados-abertos-sql-injection`  
**Branch:** `caue-backend-mvp`  
**Atualizado em:** 02 de Outubro de 2026  
**Status:** Integrada com todas as branches (`main`, `correlacao-de-dados`, `gabriel/login`, `marcelo-integracao-sistema`), 17/17 testes de backend passando (100%), stack Docker unificada e sincronizada.

---

## 1. Visão Geral da Branch

A branch **`caue-backend-mvp`** é a espinha dorsal de infraestrutura e serviços do projeto **AgroPilot 24/7**. Ela unifica:
1. **API REST FastAPI (Python 3.12)** com validação tipada via Pydantic e OpenAPI Swagger.
2. **Integração Real ao MongoDB** com conexão resiliente lazy (`get_db()`) e consultas reais a coleções de dados abertos (`zarc`, `agrofit`, `produtores`, `municipios`).
3. **Camada de IA Conversacional RAG via OpenRouter** (`xiaomi/mimo-v2.6-flash`), gerando respostas naturais estritamente embasadas nas evidências dos dados oficiais.
4. **Resiliência e Degradação Graciosa**: Se a LLM estiver sem chave ou fora do ar, o sistema devolve templates estruturados com os dados reais do MongoDB; se o MongoDB estiver indisponível, devolve mocks determinísticos — **o sistema nunca quebra**.
5. **Autenticação, Onboarding e Frontend Integrados**: Suporte completo às telas de login/cadastro (`hackathon/login/`), cliente HTTP de API (`scripts/api.js`) e interface conversacional com modo campo (`index.html`).

---

## 2. Análise dos Documentos e Bases do Projeto (Leitura de Todos os `.md`)

Todas as documentações do repositório em todas as branches foram analisadas para garantir que o backend atenda a 100% dos requisitos agronômicos, técnicos e legais:

* **[docs/documento-mestre-agropilot.md](file:///home/aluno/Downloads/hackthon/docs/documento-mestre-agropilot.md)**:
  * **O que o MVP prova:** Dado público vira evidência operacional; a IA tem função de linguagem e acolhimento, e não de decisão agronômica arbitrária.
  * **O que o MVP NÃO é:** Não é chatbot genérico, não emite receita agronômica sem responsável técnico (Lei 14.785/2023, art. 39), não calcula probabilidade falsa de plantio.
  * **Decisão ZARC:** Distinção entre "não zoneado" e "fora da janela"; janelas organizadas por decêndios com percentual de risco de perda (≤ 20% = janela recomendada).
  * **Toxicológica Agrofit:** Normalização numérica das classes 1 a 5 (Cat 5 = 76,7% dos registros, Cat 1 = 920 registros).
  * **Privacidade / LGPD (§9):** Nenhuma informação pessoal identificável (PII de segurados) é ingerida no banco de dados.

* **[CONTRATO_API.md](file:///home/aluno/Downloads/hackthon/CONTRATO_API.md) & [arquitetura-front-and-end.md](file:///home/aluno/Downloads/hackthon/arquitetura-front-and-end.md)**:
  * Define os endpoints canônicos: `POST /api/chat`, `POST /api/onboarding`, `GET /api/produtor/{id}`, `POST /api/produtor`, `GET /api/alertas/{id}`, `POST /api/alertas/simular`, `GET /api/health`.
  * Define o enum de intenções: `PLANEJAMENTO`, `PRAGA`, `CLIMA`, `VENDA`, `PERFIL`, `SAUDACAO`, `NAO_ENTENDI`.

* **[INTEGRACAO_SISTEMA.md](file:///home/aluno/Downloads/hackthon/INTEGRACAO_SISTEMA.md) & [docs/PRODUCT_SPEC.md](file:///home/aluno/Downloads/hackthon/docs/PRODUCT_SPEC.md)**:
  * Especifica o design clean do chatbot AgroPilot 24/7, a linguagem empática para o agricultor familiar (*"Seu Sebastião"*), e a necessidade de modo campo de alto contraste para visibilidade sob luz solar direta.

* **[relatorio-agricultura-familiar-dados-abertos.md](file:///home/aluno/Downloads/hackthon/relatorio-agricultura-familiar-dados-abertos.md)**:
  * Apresenta dados estatísticos consolidados: 65,3% das apólices de seguro rural (SISSER 2016–2024) são de agricultores familiares (≤ 50 ha), mas correspondem a apenas 19,2% da área segurada.
  * Seca responde por **52,2% dos sinistros no Brasil** (157.350 casos) e **67,0% dos sinistros de milho** (55.595 casos), justificando os alertas climáticos como missão central do sistema.

* **[docs/dicionario-de-dados.md](file:///home/aluno/Downloads/hackthon/docs/dicionario-de-dados.md)**:
  * Dicionário detalhado campo a campo dos 8 datasets governamentais abertos: Agrofit, ZARC, PSR/SISSER, Atlas Irrigação da ANA, SIPEAGRO e SIGEF.

---

## 3. O Que Cada Parte do Backend Faz

```
back/
├── app/
│   ├── main.py                  # Ponto de entrada FastAPI, configuração CORS e rotas /api
│   ├── db.py                    # Conexão lazy singleton ao MongoDB (banco 'agropilot')
│   ├── dados_reais.py           # Consultas reais ZARC (janelas) e Agrofit (defensivos/biológicos)
│   ├── llm.py                   # [NOVO] Integração RAG OpenRouter com xiaomi/mimo-v2.6-flash
│   ├── mock.py                  # Fallback offline estruturado (MOCK_CHAT_*, MOCK_PRODUTOR, etc.)
│   ├── core/
│   │   ├── router_intencao.py   # Motor determinístico léxico de classificação de intenções
│   │   └── templates.py         # [NOVO] Formatadores de mensagens no vocabulário do produtor
│   ├── routes/
│   │   ├── health.py            # GET /api/health — status de liveness da API
│   │   ├── chat.py              # POST /api/chat — RAG: Mongo Real + OpenRouter LLM + Fallback Mock
│   │   ├── onboarding.py        # POST /api/onboarding — cadastro conversacional em 4 etapas
│   │   ├── produtor.py          # GET/POST /api/produtor — busca por ID/Telefone e upsert no Mongo
│   │   └── alertas.py           # GET/POST /api/alertas — consulta e simulação sob demanda para o pitch
│   └── schemas/
│       ├── chat.py              # Modelos Pydantic ChatRequest, ChatResponseSuccess, ChatResponseError
│       ├── produtor.py          # Modelos ProdutorCreate, ProdutorResponse (com campos opcionais seguros)
│       ├── alertas.py           # Modelos de alertas e simulação
│       └── intencoes.py         # Enum tipado de intenções agrícolas
├── tests/
│   ├── test_contrato.py         # 9 testes automatizados dos endpoints do contrato REST
│   └── test_llm.py              # [NOVO] 8 testes automatizados da camada de LLM e RAG
├── pytest.ini                   # pythonpath=. para execução direta de testes
├── requirements.txt             # fastapi, uvicorn, pydantic, httpx, pymongo, pytest
└── .env.example                 # Configurações de ambiente (MONGO_URL, OPENROUTER_API_KEY, CORS)
```

---

## 4. Integrações com as Outras Branches

A branch `caue-backend-mvp` consolidou as melhores contribuições de cada ramo do repositório:

| Branch de Origem | Conteúdo Integrado | O que faz no sistema |
|---|---|---|
| `origin/correlacao-de-dados` | `correlacao/` (scripts ETL), `back/app/llm.py`, `test_llm.py`, `docs/documento-mestre-agropilot.md`, `e2e/test_stack.py` | Pipeline de dados abertos para o MongoDB, IA conversacional e testes E2E |
| `origin/gabriel/login` | `hackathon/login/` (`login.html`, `login.js`, `login.css`) | Tela moderna de autenticação por telefone e onboarding de cadastro |
| `origin/marcelo-integracao-sistema` | `index.html`, `scripts/app.js`, `scripts/copilot-ai.js`, `styles/main.css` | Interface limpa e minimalista do chat AgroPilot 24/7 com modo campo |
| `origin/main` | `CONTRATO_API.md`, `docs/dicionario-de-dados.md`, `db.py`, `dados_reais.py` | Modelagem canônica dos dados e contrato de integração |

---

## 5. Testes Automatizados (17/17 Passando)

O backend possui cobertura automatizada completa, executada com sucesso via `pytest`:

```bash
$ cd back && .venv/bin/pytest -v
======================== 17 passed, 1 warning in 0.58s =========================
```

* **9 Testes de Contrato (`tests/test_contrato.py`):**
  * `test_health`: Validação do liveness check.
  * `test_chat_praga`: Consulta de pragas (Agrofit).
  * `test_chat_planejamento`: Consulta de plantio (ZARC).
  * `test_chat_fallback`: Tratamento de mensagens não compreendidas.
  * `test_onboarding`: Ciclo de 4 passos de onboarding.
  * `test_get_produtor` & `test_post_produtor`: Obtenção e criação de perfil.
  * `test_get_alertas` & `test_simular_alerta`: Listagem e disparo de alertas.

* **8 Testes da Camada de IA/LLM (`tests/test_llm.py`):**
  * Ausência de chave não levanta exceção (`None`).
  * Contexto vazio não consome API.
  * Sucesso na chamada OpenRouter reescreve resposta.
  * Falha HTTP ou timeout cai com segurança no fallback determinístico.
  * Integração de injeção no endpoint de chat funcionando.

---

## 6. Como Executar a Stack Completa via Docker

O arquivo **`docker-compose.yml`** na raiz orquestra os 3 serviços essenciais:

```bash
# Subir todo o ecossistema (MongoDB + FastAPI + Servidor Web):
docker compose up
```

* **Serviço Web:** `http://localhost:8080` (Interface de Chat e Login)
* **API FastAPI:** `http://localhost:8000` (Documentação interativa em `/docs`)
* **MongoDB:** `mongodb://localhost:27017` (Banco `agropilot`)
