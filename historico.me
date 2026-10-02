# 🌾 Histórico e Mapeamento da Branch `caue-backend-mvp`

**Repositório:** `Thomaskynol/hackaton-dados-abertos-sql-injection`  
**Branch:** `caue-backend-mvp`  
**Atualizado em:** 02 de Outubro de 2026  
**Status:** Integrada, testada (43/43 testes passando) e sincronizada com o GitHub

---

## 1. Visão Geral da Branch

Esta branch implementa o **backend FastAPI** do AgroPilot 24/7 — um copiloto agrícola para pequenos produtores rurais da agricultura familiar, com:

- **Endpoints RESTful** conforme `CONTRATO_API.md` (7 rotas: `/api/chat`, `/api/chat/stream`, `/api/onboarding`, `/api/produtor`, `/api/alertas`, `/api/alertas/simular`, `/api/health`)
- **NLP local** para classificação de intenção (PLANEJAMENTO, PRAGA, CLIMA, VENDA, PERFIL, SAUDACAO, NAO_ENTENDI)
- **Integração com MongoDB** (fallback transparente para mock quando indisponível)
- **Agente LLM** com tool-calling via OpenRouter ou Groq (qualquer chave serve)
- **SSE streaming** para resposta incremental no chat (`/api/chat/stream`)
- **6 ferramentas agênticas** conectadas a dados abertos: ZARC, Agrofit, PSR, SIGEF, ANA, Municípios

---

## 2. Estrutura de Arquivos do Backend

```
back/
├── app/
│   ├── main.py              # FastAPI app + CORS + registro de rotas
│   ├── db.py                # Conexão lazy com MongoDB (agropilot db)
│   ├── mock.py              # Dados mockados (fallback quando Mongo offline)
│   ├── dados_reais.py       # Consultas diretas ao Mongo (ZARC + Agrofit)
│   ├── llm.py               # Camada LLM: OpenRouter + Groq (dual provider)
│   ├── tools.py             # 6 ferramentas agênticas (ZARC, Agrofit, PSR, SIGEF, ANA)
│   ├── core/
│   │   ├── router_intencao.py  # Classificador NLP de intenção (regex/keywords)
│   │   └── templates.py        # Templates de resposta estruturada
│   ├── routes/
│   │   ├── chat.py          # POST /api/chat + POST /api/chat/stream (SSE)
│   │   ├── produtor.py      # GET/POST /api/produtor (MongoDB + fallback mock)
│   │   ├── alertas.py       # GET /api/alertas + POST /api/alertas/simular (Mongo)
│   │   ├── onboarding.py    # POST /api/onboarding (sessão persistida no Mongo)
│   │   └── health.py        # GET /api/health
│   └── schemas/
│       ├── chat.py          # ChatRequest, ChatResponseSuccess, ChatResponseError
│       ├── produtor.py      # ProdutorCreate, ProdutorResponse, OnboardingRequest
│       ├── alertas.py       # SimularAlertaRequest
│       └── intencoes.py     # Enum Intencao
├── tests/
│   ├── test_contrato.py     # 8 testes de integração (todos os endpoints)
│   ├── test_llm.py          # 8 testes da camada LLM (sem rede real)
│   ├── test_nlp_e_dados.py  # 9 testes de NLP + dados reais/fallback
│   ├── test_no_mock.py      # 4 testes de comportamento sem mock
│   ├── test_stream.py       # 3 testes do SSE streaming
│   └── test_tools.py        # 7 testes do agente tool-calling
├── requirements.txt         # fastapi, uvicorn, pydantic, pymongo, httpx, pytest
├── .env.example             # Variáveis de ambiente documentadas
└── pytest.ini               # Configuração do pytest
```

---

## 3. Fluxo de Dados do Backend

```
Produtor → Front (NextJS/HTML) → POST /api/chat
                                     │
                              classificar_intencao()   ← NLP regex/keywords
                                     │
                    ┌───────────────►│◄────────────────────┐
                    │                │                     │
          responder_com_tools()    base_real()          fallback mock
          (loop agêntico LLM)   (dados_reais.py)        (mock.py)
               │                     │
         OpenRouter / Groq       MongoDB agropilot
         (6 tools ZARC etc.)    (zarc, agrofit, etc.)
```

### Hierarquia de resposta por intenção:

| Intenção | 1ª tentativa | Fallback |
|---|---|---|
| PLANEJAMENTO | MongoDB ZARC | Mock ZARC |
| PRAGA | MongoDB Agrofit | Mock Agrofit |
| CLIMA | Mock ZARC + INMET | — |
| VENDA | Perfil do Mongo | Mock produtor |
| PERFIL | MongoDB produtores | Mock produtor |
| SAUDACAO | Nome do Mongo | Mock saudação |
| NAO_ENTENDI | LLM (se chave) | Erro estruturado |

**Modo agêntico** (ativado se GROQ_API_KEY ou OPENROUTER_API_KEY disponível):
- Loop de até 3 rounds, chamando ferramentas reais (ZARC, Agrofit, PSR, SIGEF, ANA)
- Se agente retornar resultado → resposta final com ferramentas usadas
- Caso contrário → fluxo normal (base_real → fallback mock)

---

## 4. Integrações MongoDB

### Coleções usadas no db `agropilot`:

| Coleção | Rota | Operação |
|---|---|---|
| `produtores` | GET/POST `/api/produtor` | `find_one` / `update_one` upsert por telefone |
| `alertas` | GET `/api/alertas/{id}` | `find` por produtor_id |
| `alertas` | POST `/api/alertas/simular` | `insert_one` |
| `sessoes_onboarding` | POST `/api/onboarding` | `update_one` upsert por telefone |
| `zarc` | dados_reais + tools | `find` por cultura/IBGE |
| `agrofit` | dados_reais + tools | `find` por cultura/praga |
| `municipios` | tools | `find_one` por nome/IBGE |
| `psr_agregado` | tools | `find` por IBGE/cultura |
| `sigef_agregado` | tools | `find` por IBGE/cultura |
| `ana_atlas` | tools | `find_one` por IBGE |

Todas as operações têm **fallback automático** — se o Mongo estiver offline, retornam mock sem quebrar o serviço.

---

## 5. Camada LLM — Dual Provider

O backend suporta dois provedores de LLM transparentemente. Configure qualquer uma das chaves:

| Variável | Provider | Modelo | Gratuito? |
|---|---|---|---|
| `GROQ_API_KEY` | Groq | llama3-8b-8192 | ✅ Sim (tier gratuito) |
| `OPENROUTER_API_KEY` | OpenRouter | xiaomi/mimo-v2.6-flash | 💰 Pago |

A função `_get_key()` em `llm.py` testa Groq primeiro, depois OpenRouter. Sem nenhuma chave, todas as funções LLM retornam `None` e o sistema cai no mock/dados formatados normalmente.

---

## 6. Variáveis de Ambiente

Copie `back/.env.example` para `back/.env` e preencha:

```env
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
MONGO_URL=mongodb://localhost:27017

# LLM — preencha UMA das chaves:
GROQ_API_KEY=<sua-chave-groq>         # gratuito em console.groq.com
OPENROUTER_API_KEY=<sua-chave>        # pago em openrouter.ai
```

---

## 7. Como Executar

```bash
# 1. Entrar no diretório back
cd back

# 2. Criar e ativar virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Configurar variáveis
cp .env.example .env   # edite o arquivo

# 5. Iniciar a API
uvicorn app.main:app --reload --port 8000

# 6. Rodar os testes (sem MongoDB nem chave LLM necessários)
pytest -v
```

**Com Docker (MongoDB + API):**
```bash
docker compose up   # na raiz do projeto
```

---

## 8. Histórico de Commits (resumo)

| Data | Commit | Descrição |
|---|---|---|
| 02/10/26 | `init` | Estrutura FastAPI inicial, schemas, mock, rotas base |
| 02/10/26 | `feat: NLP + intenções` | classificar_intencao(), intencoes.py, 5 intenções |
| 02/10/26 | `feat: dados_reais + db.py` | Consultas reais ao MongoDB com fallback |
| 02/10/26 | `feat: LLM OpenRouter` | gerar_resposta(), gerar_resposta_stream(), RAG |
| 02/10/26 | `feat: agente tool-calling` | responder_com_tools(), 6 tools ZARC/Agrofit/PSR/SIGEF/ANA |
| 02/10/26 | `feat: SSE chat/stream` | Streaming incremental com SSE (meta → delta → done) |
| 02/10/26 | `test: 43 testes unitários` | Contrato, LLM, NLP, stream, tools — todos sem rede real |
| 02/10/26 | `feat: MongoDB completo` | produtor/alertas/onboarding com Mongo + upsert + sessões |
| 02/10/26 | `feat: dual LLM provider` | Suporte a GROQ_API_KEY + OPENROUTER_API_KEY em llm.py |

---

## 9. Status Atual e Próximos Passos

### ✅ Implementado
- 7 endpoints conforme CONTRATO_API.md
- NLP local (classificação de intenção)
- MongoDB com fallback automático
- Camada LLM dual-provider (Groq + OpenRouter)
- Agente tool-calling com 6 ferramentas de dados abertos
- SSE streaming para chat incremental
- 43 testes passando (0 falhas, sem rede real)
- docker-compose.yml (MongoDB 7 + API)
- Onboarding com persistência de sessão e finalização automática

### 🔜 Próximos Passos
- Integrar INMET API real para alertas climáticos em tempo real
- Implementar autenticação JWT para produtores
- Adicionar webhook para notificações proativas (WhatsApp/SMS)
- Deploy em produção (Railway / Fly.io / VPS)
