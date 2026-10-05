# AgroPilot — Copiloto Agrícola 24/7 (Hackathon Dados Abertos IFSP 2026)

> **"O pequeno produtor não tem margem para errar — nem no campo, nem na venda."**

O **AgroPilot** é um copiloto agrícola para a **agricultura familiar**, criado no **1º Hackathon de Dados Abertos do IFSP Araraquara**. Ele acompanha a jornada da safra **da compra da semente até a venda**, combinando dados oficiais abertos (ZARC, PSR, SIGEF, Agrofit, ANA, CONAB/PGPM, IBGE/PAM, Open-Meteo) num **consultor comercial regional** + **copiloto de safra com memória**.

Regra de ouro: **todo número tem fonte + data. Sem dado → estado honesto, nunca inventa. Nunca manda "venda agora", nunca receita defensivo.**

Este arquivo é a visão completa e atual do projeto. O `README.md` antigo foi mantido por histórico — partes dele (árvore `index.html/styles/scripts`, pitch do protótipo estático) estão desatualizadas.

---

## Índice

1. [O que é e por que existe](#1-o-que-é-e-por-que-existe)
2. [Funcionalidades](#2-funcionalidades)
3. [Stack tecnológica](#3-stack-tecnológica)
4. [Arquitetura](#4-arquitetura)
5. [Estrutura do repositório](#5-estrutura-do-repositório)
6. [Fontes de dados e seed](#6-fontes-de-dados-e-seed)
7. [Como executar](#7-como-executar)
8. [Variáveis de ambiente](#8-variáveis-de-ambiente)
9. [API (FastAPI `/api/*`)](#9-api-fastapi-apiprefixo-api)
10. [Frontend (Next 14)](#10-frontend-next-14)
11. [Autenticação telefone+PIN](#11-autenticação-telefonepin)
12. [IA (opcional, com fallback honesto)](#12-ia-opcional-com-fallback-honesto)
13. [Testes e qualidade](#13-testes-e-qualidade)
14. [Scripts úteis](#14-scripts-úteis)
15. [Documentação interna](#15-documentação-interna)
16. [Legado: protótipo estático](#16-legado-protótipo-estático)

---

## 1. O que é e por que existe

Pesquisa fundadora (`relatorio-agricultura-familiar-dados-abertos.md`) mostrou: **65% das apólices do PSR ≤50 ha cobrem só 19% da área segurada**, joins entre bases públicas batem **100% / 99,8%** por `cod_ibge`. Ideia vencedora: **Janela (ZARC) + Cobertura (PSR)**.

O AgroPilot responde duas perguntas do produtor familiar:

1. **Quando plantar e o que vigiar?** → janela ZARC em datas, clima 7 dias, risco PSR, alertas (geada, calor, chuva, veranico, janela fechando).
2. **Onde e por quanto vender?** → mapa comercial por UF (preço × piso PGPM × canal: cooperativa, cerealista, feira, PAA/PNAE), tendência IBGE, previsão determinística, análise comercial.

Princípios vivos (`docs/PRODUCT_SPEC.md`):
- Mapa é o carro-chefe, chat é apoio.
- 4 estados honestos de dado (vivo / cache / indisponível / sem cobertura).
- Endpoint único de bundle regional.
- Síntese determinística quando IA desligada.
- Mobile-first, alvos ≥44px, paleta terrosa, `.modo-campo` alto contraste para sol forte.
- Acessibilidade por áudio (SpeechSynthesis + gravação de microfone).

O que **NÃO** é vs o que **É** (do README original, ainda válido):

| O que NÃO é | O que É |
|---|---|
| Site informativo estático | Assistente diário com alertas antes do desastre |
| Dashboard de gráficos vazios | Ações práticas e missões de campo |
| ChatGPT genérico | Integrado a ZARC/MAPA, PSR, SIGEF, Agrofit, ANA, CONAB, IBGE, Open-Meteo |
| App passivo | Proativo: avisa de frente fria, veranico, praga, janela fechando sem precisar perguntar |

---

## 2. Funcionalidades

### 🗺️ Mapa comercial por UF (carro-chefe) — `/(app)/mapa`
- SVG do Brasil clicável, coroplético por preço.
- Card por UF em 4 blocos + "ver mais".
- **Leitura AgroPilot: preço × piso × canal** (ex: "mercado X, piso PGPM Y, PNAE paga até +10%").
- Painel local (`PainelLocal`, `MapaBrasil`, `AnaliseComercial`, `CanaisVenda`).

### 💰 Preços — `/(app)/precos`
- Mercado (CONAB), piso (PGPM), tendência (IBGE SIDRA tabela 1612 sob demanda).
- Previsão IA **determinística + cacheada 30 dias** (reprodutível, `check_determinismo_preco.py`).
- Cepea entra só como link externo.
- Componentes: `CardPreco`, `TendenciaPrecos`.

### 📡 Radar (3 cartões evidência) — `/(app)/radar`
- Cartão 1: janela ZARC em datas.
- Cartão 2: clima 7 dias (Open-Meteo).
- Cartão 3: risco PSR histórico.
- `EvidenceCard` com fonte + data sempre visíveis.

### 🌱 Safra + Decisão do dia — `/(app)/safra`
- Estado da propriedade + decisão do dia (RAG: clima + ZARC + preço + PSR + memória).

### 💬 Chat assistente — `/(app)/perguntar` e `/(app)/assistente`
- `perguntar` = chat simples; `assistente` = chat real com **stream SSE** (`meta/delta/message/done`).
- Sessões estilo ChatGPT (`/sessoes`), memória 1-linha/fato injetada (últimas 8).
- `ChatBubble`, `ChatInput`, áudio mic (`src/lib/audio.ts`), TTS nativo.
- Barra simulação para banca: temporal 75mm/24h, geada 2,8 °C, praga, janela 6 dias, veranico.

### 🧭 Onboarding — `/onboarding` + `/login`
- Chat de 5 passos: nome → cidade/UF → culturas → área → resumo, com `cod_ibge` real via IBGE.
- Alternativa com mapa-picker (`arquitetura-mapa-cadastro-chat-memoria.md`).
- Login com abas **Entrar (tel+PIN) / Cadastrar (nome+tel+PIN)**.

### 🚨 Alertas
- Janela fechando, risco histórico, geada/calor/chuva/veranico.
- `GET /alertas?ibge&cultura&uf`, `POST /alertas/simular`, `GET /alertas/{id}`.

### 👤 Conta — `/(app)/conta`
- Perfil, troca de PIN, logout.

### ☀️ Modo campo
- Alto contraste instantâneo para uso sob sol na roça.

---

## 3. Stack tecnológica

| Camada | Tech |
|---|---|
| Back | Python 3.12, FastAPI, Pydantic, httpx, pymongo, pytest |
| Front | Next 14.2.33 (App Router), React 18, TypeScript 5, Tailwind 3, lucide-react |
| Banco | MongoDB 7, db `agropilot`, ~1.071.126 docs no seed |
| IA | OpenRouter free-first (`nemotron-3-super:free` → `gemma-4-31b:free` → `qwen3-8b:free` aprox.), `OPENROUTER_MODEL` sobrescreve; **fallback determinístico sempre** |
| Clima | Open-Meteo (grátis, sem chave) + IBGE localidades p/ geocode |
| Preços vivos | IBGE SIDRA tabela 1612 (PAM) sob demanda + PGPM/CONAB ingerido + Cepea só link |
| Infra | Docker Compose (mongo + api + front + seed one-shot) + instalador Python cross-platform |
| Ingestão | **stdlib only** (sem pandas; XLSX via zipfile) |

---

## 4. Arquitetura

```
[Next 14 mobile-first]  --fetch NEXT_PUBLIC_API_URL-->  [FastAPI /api/* + CORS]
        |                                                          |
 localStorage (perfil+token, cache)                    [MongoDB agropilot lazy get_db()]
                                                        null-safe: degrada p/ mock/arquivo
                                                                   |
                                                     OpenRouter / Open-Meteo / IBGE externos
```

- **IA só onde há linguagem** (entrada do chat, síntese de saída). Resto é determinístico.
- Roteador de intenção por keywords (PLANEJAMENTO / PRAGA / CLIMA / VENDA / PERFIL / SAUDACAO / NAO_ENTENDI) + agente LLM com **8 tools** + **3 camadas anti-injection**.
- Join central por **`cod_ibge`** (+ `cultura_canonica`; Agrofit sem geo).
- `municipios` é o hub; todo resto pendura nele.
- Coleções runtime: `produtores, sessoes, mensagens, memorias, sessoes_auth`.

```
municipios (hub cod_ibge)
  <- zarc (957k) | psr_agregado (72k) | sigef_agregado (10k)
  <- ana_atlas (5570) | agrofit (16,7k, sem geo) | precos_conab (2860)
  <- precos_meta | precos_previsao | geo_municipios | clima_cache
```

---

## 5. Estrutura do repositório

```
.
├── README.md                    # pitch + quickstart (parcialmente desatualizado na árvore)
├── README2.md                   # este arquivo — visão completa atual
├── CONTRATO_API.md              # contrato original 7 endpoints (base dos tipos do front; real tem ~20)
├── INTEGRACAO_SISTEMA.md        # histórico do protótipo estático antigo
├── arquitetura-front-and-end.md # estratégia "contrato primeiro, mock dos 2 lados"
├── relatorio-agricultura-familiar-dados-abertos.md  # pesquisa fundadora (5 achados, joins, matriz 24h)
├── Arquivo\ de\ dados           # índice textual: 19 fontes MAPA/ANA
├── docker-compose.yml           # mongo + api + front + seed one-shot restore
├── .env / .env.example          # raiz: IA, IBGE, previsão, clima, seed/GH_TOKEN
├── seed/agropilot.gz + manifest.json  # dump Mongo ~34-35 MB, sha256 validado
├── base\ de\ dados/ (gitignored, ~680 MB)  # 8 brutos: ZARC 2026/27, PSR 2025, agrofit x2, SIGEF x2, ANA x2
│
├── scripts/
│   ├── agropilot.py             # CLI cross-platform: doctor/setup/up/down/status/logs/seed/tudo
│   ├── agropilot.ps1 / agropilot.sh   # wrappers que chamam o .py
│   ├── gerar_seed.py            # regenera seed limpo (só dados públicos + sha256)
│   ├── gerar-municipios.py      # gera GeoJSON IBGE p/ front/public/geo
│   ├── seed.sh                  # seed manual
│   └── data.js / copilot-ai.js / app.js / api.js  # LEGADO protótipo estático
├── styles/main.css              # LEGADO protótipo estático
│
├── correlacao/                  # ingestão stdlib-only → Mongo
│   ├── canon.py                 # mapas canônicos SOLO/MANEJO/CICLO/CLIMA, toxicidade, ibge7
│   ├── zarc.py / psr.py / sigef.py / agrofit.py / ana.py / precos_conab.py
│   ├── load_mongo.py            # bulk load JSONL → agropilot + índices
│   ├── baixar_psr.py / _load_psr_only.py
│   └── test_canon.py / test_ingest.py   # 48 testes unittest (~2s)
│
├── back/                        # FastAPI
│   ├── requirements.txt         # fastapi, uvicorn, pydantic, dotenv, httpx, pymongo, pytest
│   ├── pytest.ini / README.md / .env.example
│   ├── app/main.py              # app + CORS + 10 routers
│   ├── app/{db,auth,memoria,llm,tools,dados_reais,extracao,clima,mock,precos_dados,precos_ibge}.py
│   ├── app/core/{router_intencao,templates}.py
│   ├── app/schemas/{chat,produtor,alertas,sessao,intencoes}.py
│   ├── app/routes/{health,chat,onboarding,produtor,alertas,regiao,sessoes,precos,decisao,radar}.py
│   ├── scripts/{revalidar_series,check_determinismo_preco}.py
│   └── tests/test_{contrato,sessoes,auth,conta,produtor,regiao,precos,precos_vivo,producao_pam,clima,alertas,llm,tools,stream,no_mock,seguranca_assistente}.py
│       └── conftest.py          # FakeDB em memória + rede/IA desligadas
│
├── front/                       # Next 14 + TS + Tailwind
│   ├── package.json / next.config.mjs / tailwind.config.ts / tsconfig.json
│   ├── public/ (+geo/municipios/*.geo.json gerados)
│   ├── src/app/page.tsx         # raiz: redireciona /mapa ou /login
│   ├── src/app/layout.tsx / globals.css
│   ├── src/app/login/page.tsx   # Entrar tel+PIN / Cadastrar nome+tel+PIN + onboarding-chat
│   ├── src/app/signup/page.tsx  # legado
│   ├── src/app/onboarding/page.tsx  # nome→local→cultura→fim (mapa-picker)
│   ├── src/app/(app)/layout.tsx # casca TopBar+BottomNav+GuardaSessao
│   ├── src/app/(app)/mapa|precos|radar|safra|perguntar|assistente|conta/page.tsx
│   ├── src/components/{TopBar,BottomNav,GuardaSessao,Button,Chip,ChatBubble,ChatInput,EvidenceCard,MapaBrasil,PainelLocal,CardPreco,TendenciaPrecos,CanaisVenda,AnaliseComercial,Logo}.tsx
│   ├── src/lib/{api,types,perfil-context,audio,dados-locais,mapa-local,precos,brasil-uf,geo-tipos,texto-cards}.ts
│   └── src/assets/logo/logo-agropilot.svg
│
├── docs/
│   ├── PRODUCT_SPEC.md          # PRD vivo: virada chat→mapa, 7 princípios
│   ├── documento-mestre-agropilot.md  # referência técnica: grafo, coleções, RiskEngine, golden tests
│   ├── arquitetura-mapa-cadastro-chat-memoria.md  # spec implementada (onboarding, região, sessões, memória)
│   ├── dicionario-de-dados.md   # coluna-a-coluna das 8 bases brutas (encoding latin1, `;`)
│   └── historico.md             # log do branch correlacao-de-dados + guia de merge
│
└── e2e/test_stack.py            # smoke web→api→mongo (stdlib urllib, skip se stack down)
```

---

## 6. Fontes de dados e seed

| Fonte | O que entra | Ingestor |
|---|---|---|
| ZARC 2026/27 (MAPA/Embrapa) | Janela de plantio por município/cultura/solo/ciclo (~957k linhas) | `correlacao/zarc.py` |
| PSR 2025 (SISSER) | Seguro rural agregado por município/cultura (~72k) | `correlacao/psr.py` |
| SIGEF | Malha fundiária agregada (~10k) | `correlacao/sigef.py` |
| Agrofit (MAPA) | Defensivos registrados (~16,7k, sem geo) | `correlacao/agrofit.py` |
| ANA Atlas | Água/abastecimento 5570 municípios | `correlacao/ana.py` |
| CONAB / PGPM | Preços mercado + preço mínimo (~2860) | `correlacao/precos_conab.py` |
| IBGE PAM SIDRA t.1612 | Produção/área sob demanda (preços vivos, tendência) | `back/app/precos_ibge.py` |
| IBGE localidades | Geocode cidade/UF → `cod_ibge` | `back/app/extracao.py` + onboarding |
| Open-Meteo | Clima 7 dias + cache (`clima_cache`) | `back/app/clima.py` |
| IBGE malha | GeoJSON municípios p/ `front/public/geo` | `scripts/gerar-municipios.py` |

- **Normalização:** `correlacao/canon.py` (SOLO/MANEJO/CICLO/CLIMA canônicos, toxicidade, `ibge7`).
- **Carga:** `correlacao/load_mongo.py` (bulk JSONL → `agropilot` + índices).
- **Seed distribuído:** `seed/agropilot.gz` (~34 MB) + `seed/manifest.json` (contagens + sha256). **Só dados públicos.**
- **Regenerar seed limpo:** `python scripts/gerar_seed.py` a partir do Mongo local.

---

## 7. Como executar

### Opção A — instalador (recomendado, 1 comando, Win/Linux/Mac igual)

```bash
git clone <url-do-repo> hackaton-dados-abertos
cd hackaton-dados-abertos

python scripts/agropilot.py        # = tudo (setup + up)
```

Depois:

| Endereço | O que é |
|---|---|
| http://localhost:3000 | o aplicativo |
| http://127.0.0.1:8000/docs | a API (Swagger) |
| http://127.0.0.1:8000/api/health | se a API está viva |

Atalhos:

```powershell
# Windows
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\agropilot.ps1
```

```bash
# Linux / macOS
./scripts/agropilot.sh
```

Comandos do dia a dia:

```bash
python scripts/agropilot.py doctor        # o que falta na máquina
python scripts/agropilot.py setup         # instala Mongo/Python/Node, cria .env, puxa seed
python scripts/agropilot.py up / down     # sobe / derruba API e front
python scripts/agropilot.py status        # o que está de pé
python scripts/agropilot.py logs -f       # logs ao vivo
python scripts/agropilot.py seed --force  # repõe a base do zero
python scripts/agropilot.py tudo          # setup + up + seed
```

### Opção B — Docker

```bash
docker compose up
```

Sobe mongo + api + front e restaura o seed sozinho.

### Opção C — manual

```bash
# back
cd back
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# front (outro terminal)
cd front
npm install
npm run dev    # porta 3000
```

### Seed privada (por que às vezes pede login)

O dump fica na GitHub Release `data`. Como o repo é **privado**, o instalador tenta sozinho, nesta ordem:

1. arquivo já em `seed/agropilot.gz`;
2. GitHub CLI logado (`gh auth login`);
3. token em `GH_TOKEN`;
4. URL aberta em `SEED_URL`.

Se você já tem o arquivo, copie para `seed/agropilot.gz` e rode de novo. Restaura **só se o banco estiver vazio** (valida sha256 do `manifest.json`).

---

## 8. Variáveis de ambiente

Copie os exemplos (tudo opcional — **sobe sem IA**):

```bash
cp .env.example .env
cp back/.env.example back/.env
```

| Var | Onde | Efeito |
|---|---|---|
| `OPENROUTER_API_KEY` | `back/.env` | liga IA (leitura em linguagem natural). Sem ela: dados oficiais + respostas honestas |
| `OPENROUTER_MODEL` | `back/.env` | sobrescreve a cascata free-first |
| `MONGO_URL` | `back/.env` | default aponta p/ compose/local |
| `CORS_ORIGINS` | `back/.env` | libera front |
| `AUTH_OBRIGATORIA` | `back/.env` | `0` default (aberto p/ demo); `1` exige Bearer |
| `IBGE_AUTO_UPDATE` / `IBGE_TTL_*` | `back/.env` | preços vivos SIDRA sob demanda + TTL |
| `PRECO_PREVISAO_IA` / `PRECO_PREVISAO_TTL` / `PRECO_PREVISAO_OFFSET` | `back/.env` | previsão determinística cacheada |
| `CLIMA_AUTO` | `back/.env` | liga/desliga clima Open-Meteo |
| `GH_TOKEN` / `SEED_URL` | `.env` raiz | download do seed privado |
| `NEXT_PUBLIC_API_URL` | `front` | URL da API usada pelo fetch |

---

## 9. API (FastAPI, prefixo `/api`)

`back/app/main.py` monta **10 routers**. Lista real (~20 rotas — `CONTRATO_API.md` tem só as 7 originais):

| Método + rota | Módulo | O que faz |
|---|---|---|
| `GET /health` | `routes/health.py` | vivo? + versão + mongo? |
| `POST /chat` | `routes/chat.py` | agente com 8 tools (intenção → dados → síntese) |
| `POST /chat/stream` | `routes/chat.py` | SSE `meta/delta/message/done` |
| `POST /onboarding` | `routes/onboarding.py` | 5 etapas com extração real IBGE |
| `POST /produtor` | `routes/produtor.py` | upsert por telefone (legado compat) |
| `POST /produtor/signup` | `routes/produtor.py` | cria conta nome+tel+PIN |
| `POST /produtor/login` | `routes/produtor.py` | tel+PIN → token |
| `POST /produtor/logout` | `routes/produtor.py` | invalida token |
| `GET /produtor/me` | `routes/produtor.py` | perfil do Bearer atual |
| `GET /produtor/{id}` / `PATCH /produtor/{id}` | `routes/produtor.py` | lê/atualiza produtor |
| `GET /regiao?uf&ibge&cultura` | `routes/regiao.py` | **bundle único**: ZARC+SIGEF+PSR+ANA |
| `GET /radar` | `routes/radar.py` | 3 cartões (ZARC/clima/PSR) |
| `GET /precos` | `routes/precos.py` | CONAB/PGPM + canais + análise IA/heurística |
| `GET /decisao-dia` | `routes/decisao.py` | RAG do dia |
| `GET /alertas?ibge&cultura&uf` | `routes/alertas.py` | lista alertas |
| `POST /alertas/simular` | `routes/alertas.py` | dispara cenário (banca) |
| `GET /alertas/{id}` | `routes/alertas.py` | detalhe |
| `POST /sessoes` / `GET /sessoes` | `routes/sessoes.py` | cria/lista sessões de chat |
| `GET /sessoes/{id}` / `GET /sessoes/{id}/mensagens` | `routes/sessoes.py` | histórico |
| `GET /memorias` | `routes/sessoes.py` | fatos 1-linha do produtor |

- `GET /docs` (Swagger) em `127.0.0.1:8000/docs`.
- Banco lazy (`get_db()` null-safe): sem mongo → degrada para mock/arquivo, nunca quebra.
- Schemas em `back/app/schemas/`; serviços em `back/app/{db,auth,memoria,llm,tools,dados_reais,extracao,clima,mock,precos_dados,precos_ibge}.py`.

---

## 10. Frontend (Next 14)

- **Rotas:** `/` (redirect) → `/mapa` (logado) ou `/login`; `/login`, `/signup` (legado), `/onboarding`, `/(app)/mapa|precos|radar|safra|perguntar|assistente|conta`.
- **Casca app:** `(app)/layout.tsx` = `TopBar` + `BottomNav` + `GuardaSessao` (guarda de token).
- **Lib:** `src/lib/api.ts` (fetch `NEXT_PUBLIC_API_URL`), `types.ts`, `perfil-context.ts`, `audio.ts`, `dados-locais.ts`, `mapa-local.ts`, `precos.ts`, `brasil-uf.ts`, `geo-tipos.ts`, `texto-cards.ts`.
- **Mapa:** `MapaBrasil` (SVG) + `PainelLocal` + `AnaliseComercial` + `CanaisVenda`.
- **Geo:** `public/geo/municipios/*.geo.json` gerados por `scripts/gerar-municipios.py`.
- **Logo:** `src/assets/logo/logo-agropilot.svg`.

---

## 11. Autenticação telefone+PIN

`back/app/auth.py`:

- PIN 4–6 dígitos, hash **PBKDF2-HMAC-SHA256 120k rounds + salt**.
- Token opaco `secrets.token_urlsafe`, Bearer, TTL 30 dias em `sessoes_auth` (índice TTL). **Sem JWT.**
- `AUTH_OBRIGATORIA=0` por default (demo aberta).
- PIN nunca vaza na API (`tem_pin: boolean`).

---

## 12. IA (opcional, com fallback honesto)

- `back/app/llm.py` (~830 linhas): cascata OpenRouter free-first, `OPENROUTER_MODEL` sobrescreve.
- Sem `OPENROUTER_API_KEY`: tudo funciona com dados oficiais + templates determinísticos (`app/core/templates.py`).
- Previsão de preço: determinística, cache 30 dias, verificável (`scripts/check_determinismo_preco.py`, `revalidar_series.py`).
- Segurança do assistente: 3 camadas anti-injection (testes em `test_seguranca_assistente.py`, `test_no_mock.py`).

---

## 13. Testes e qualidade

```bash
# back (a partir da raiz ou com PYTHONPATH=back)
pytest back/tests -q

# ingestão stdlib (48 testes, ~2s)
python -m unittest correlacao.test_canon correlacao.test_ingest

# smoke web→api→mongo (pula se stack down)
python e2e/test_stack.py
```

- `back/tests/conftest.py`: FakeDB em memória, rede/IA desligadas — teste nunca bate em produção.
- Cobertura: contrato, sessões, auth, conta, produtor, região, preços (+vivo), produção PAM, clima, alertas, LLM, tools, stream, no-mock, segurança.

---

## 14. Scripts úteis

```bash
python scripts/agropilot.py doctor       # diagnostica máquina
python scripts/agropilot.py seed --force # restaura dump
python scripts/gerar_seed.py             # regenera seed limpo do Mongo local
python scripts/gerar-municipios.py       # regenera GeoJSON do front
./scripts/seed.sh                        # seed manual
```

---

## 15. Documentação interna

| Doc | O que é |
|---|---|
| `docs/PRODUCT_SPEC.md` | PRD vivo (virada chat→mapa, 7 princípios) |
| `docs/documento-mestre-agropilot.md` | referência técnica (grafo, schemas, RiskEngine veto→score, workers, LGPD, golden tests Araraquara) |
| `docs/arquitetura-mapa-cadastro-chat-memoria.md` | spec implementada (onboarding com mapa, solo inferido, região, sessões, memória) |
| `docs/dicionario-de-dados.md` | coluna-a-coluna das 8 bases brutas |
| `docs/historico.md` | log do branch `correlacao-de-dados` + guia de merge |
| `CONTRATO_API.md` | contrato inicial (7 rotas) |
| `arquitetura-front-and-end.md` | paralelismo front/back via mock |
| `back/README.md` | quickstart venv + Windows sem Docker + pytest |
| `relatorio-agricultura-familiar-dados-abertos.md` | pesquisa fundadora |
| `Arquivo de dados` | catálogo 19 fontes MAPA/ANA |

---

## 16. Legado: protótipo estático

`index.html` na raiz (se existir), `styles/main.css`, `scripts/{data,copilot-ai,app,api}.js` e `INTEGRACAO_SISTEMA.md` são o **protótipo estático anterior** (chat clean, diagnóstico por foto simulado, modais ZARC/missões/cotações). Foi supersedido por `front/` + `back/`. Mantido por histórico; **não usar como referência de estrutura**.

---

*AgroPilot — Hackathon de Dados Abertos IFSP Araraquara 2026. Dados oficiais, fonte e data sempre. Sem dado, sem chute.*
