# 🌾 Histórico e Mapeamento Consolidado da Branch `caue-backend-mvp`

**Repositório:** `Thomaskynol/hackaton-dados-abertos-sql-injection`  
**Branch:** `caue-backend-mvp`  
**Atualizado em:** 02 de Outubro de 2026  
**Status:** Totalmente sincronizada com `origin/main` (incluindo PR #1 de Zenon `feat/mapa-consultor-comercial` e `correlacao-de-dados`), 31/31 testes de backend passando (100%), stack Docker unificada e 48 testes de correlação validados.

---

## 1. Visão Geral da Branch

A branch **`caue-backend-mvp`** reúne e consolida o ecossistema completo do **AgroPilot 24/7**:
1. **API REST FastAPI (Python 3.12)** com OpenAPI Swagger, endpoints síncronos e **SSE Streaming (`/api/chat/stream`)**.
2. **Camada Agêntica com Tool-Calling Real (`back/app/tools.py`)**: A LLM consulta o banco de dados MongoDB dinamicamente chamando 6 ferramentas especializadas:
   * `buscar_municipio`: Resolve IBGE/nome/UF.
   * `buscar_janelas_zarc`: Janelas de plantio e risco ZARC.
   * `buscar_produtos_agrofit`: Defensivos e bioinsumos com filtros toxicológicos e orgânicos.
   * `buscar_risco_psr`: Sinistralidade histórica do seguro rural.
   * `buscar_area_sigef`: Lavouras e sementes declaradas.
   * `buscar_irrigacao_ana`: Tipologia e infraestrutura de irrigação municipal.
3. **OpenRouter LLM (`xiaomi/mimo-v2.6-flash`)** com fallback resiliente para templates locais determinísticos e dados mockados quando offline.
4. **Novo Frontend Next.js 14 + Tailwind (`front/`) criado por Zenon (`ZenonPB` via PR #1):**
   * **Mapa Interativo do Brasil** por UF com drill-down municipal GeoJSON (27 UFs em `front/public/geo/municipios/`).
   * **Painel Regional de Insights Comerciais** e cotações CONAB/PGPM com links Cepea.
   * **Assistente com suporte a áudio/voz**, texto e chips interativos contextualizados por UF.
   * Telas de Safra, Radar de Evidências, Perguntas e Onboarding.
5. **Frontend Chatbot 24/7 Clássico (`index.html`) e Login (`hackathon/login/`)**: Interface conversacional direta com modo campo e autenticação por telefone.

---

## 2. O Que Cada Parte do Backend Faz

```
back/
├── app/
│   ├── main.py                  # Ponto de entrada FastAPI, CORS e inclusão de rotas /api
│   ├── db.py                    # Conexão lazy singleton ao MongoDB (banco 'agropilot')
│   ├── tools.py                 # [NOVO] 6 ferramentas agênticas de consulta direta ao Mongo
│   ├── dados_reais.py           # Consultas determinísticas ZARC e Agrofit
│   ├── llm.py                   # Loop agêntico de tool-calling + streaming OpenRouter
│   ├── mock.py                  # Base mockada para fallback offline
│   ├── core/
│   │   ├── router_intencao.py   # Motor léxico de intenções agronômicas
│   │   └── templates.py         # Formatadores de mensagens para agricultura familiar
│   ├── routes/
│   │   ├── health.py            # GET /api/health
│   │   ├── chat.py              # POST /api/chat e POST /api/chat/stream (SSE)
│   │   ├── onboarding.py        # POST /api/onboarding (4 etapas)
│   │   ├── produtor.py          # GET/POST /api/produtor (leitura e gravação no Mongo)
│   │   └── alertas.py           # GET/POST /api/alertas (simulações de risco)
│   └── schemas/
│       ├── chat.py              # Schemas de chat e requisições
│       ├── produtor.py          # Schemas de produtor, lavouras e onboarding
│       ├── alertas.py           # Schemas de alertas
│       └── intencoes.py         # Enum tipado de intenções
├── tests/
│   ├── test_contrato.py         # 9 testes dos endpoints do contrato
│   ├── test_llm.py              # 8 testes da camada de LLM e mock HTTP
│   ├── test_tools.py            # 7 testes das 6 tools e dispatch agêntico
│   ├── test_stream.py           # 3 testes do endpoint SSE /api/chat/stream
│   └── test_no_mock.py          # 4 testes verificando ausência de dados hardcoded
├── pytest.ini                   # pythonpath=. para execução direta de testes
├── requirements.txt             # Dependências da API
└── .env.example                 # OPENROUTER_API_KEY, MONGO_URL, CORS_ORIGINS
```

---

## 3. Cobertura de Testes (31/31 Passando no Backend)

```bash
$ cd back && .venv/bin/pytest -v
======================== 31 passed, 1 warning in 0.68s =========================
```

* **Testes de Contrato (9 testes):** Health, Chat (Praga, Planejamento, Fallback), Onboarding, Produtor (GET/POST), Alertas (GET/POST).
* **Testes de LLM (8 testes):** OpenRouter mockado, timeouts tratados, respostas sem chave tratadas.
* **Testes de Tools (7 testes):** Schema das 6 ferramentas, dispatch no banco de dados e loop agêntico.
* **Testes de Streaming (3 testes):** SSE emitindo `event: meta`, `event: delta` e `event: done`.
* **Testes No-Mock (4 testes):** Verificação de chamadas dinâmicas sem dependência de mocks fixos.

Além disso, os **48 testes unitários da pasta `correlacao/`** rodam com 100% de sucesso.

---

## 4. Como Subir o Sistema Completo via Docker

O [docker-compose.yml](file:///home/aluno/Downloads/hackthon/docker-compose.yml) na raiz sobe os serviços de banco, API e aplicação web:

```bash
# Sobe MongoDB 7 + API FastAPI (com SSE e tools) + Servidor Web:
docker compose up
```

* **Web:** `http://localhost:8080` (Interface Web e Login)
* **API REST & Swagger Docs:** `http://localhost:8000/docs`
* **MongoDB:** `mongodb://localhost:27017`
