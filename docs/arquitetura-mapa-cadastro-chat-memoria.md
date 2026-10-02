# Arquitetura — Mapa no onboarding, Painel real, Chat real, Cadastro + Sessoes + Memoria

Status: approved for implementation. PT-BR for team. Code identifiers English.

## 1. Problems (measured)

1. Onboarding asks city as free text (`front/src/app/onboarding/page.tsx:125-133`, split `"-"` + default Araraquara in `concluir:46-55`) and never sets `cod_ibge`. IBGE only exists as map banner (`mapa/page.tsx:140-144`), ignored by data layer.
2. Onboarding asks solo (`onboarding/page.tsx:153-175`, `SOLOS` in `dados-locais.ts:23-27`) but solo is never read — panel uses static `soloDaUF` pendente (`mapa-local.ts:67-80`).
3. `PainelRegional` (`components/PainelRegional.tsx:77-80`) shows hardcoded "Sem dado ainda" for producao/solo/seguro/irrigacao. All `mapa-local.ts` functions return `estado:"pendente"`, nulls. Prices (`precos.ts:41-119`) always null → "sem cotação disponível".
4. `/assistente` (`src/app/(app)/assistente/page.tsx:58-74`) uses `responderLocal` + `setTimeout 450ms`, zero fetch. Comment line 68 says "aqui entraria o POST /api/chat". So "modo navegação" is expected, not a bug.
5. Backend `/api/chat` works (agentico `chat.py:389-407` + 6 tools `tools.py:358-365`) but always defaults to `IBGE_DEFAULT 3503208` (`chat.py:24`) because front never sends IBGE/cultura. No `sessao_id` in `schemas/chat.py:6-8`.
6. No persistence: `produtor.py:18-24` returns fixed `id abc123`; `onboarding.py:7-32` stateless; zero collections for sessions/messages/memories (grep zero). `perfil-context.tsx:45-62` localStorage only.

## 2. Decisions (ponytail)

- Reuse `MapaBrasil` (already fetches `/geo/municipios/{UF}.geo.json`, returns `ibge+nome`) as picker inside onboarding. No new map code.
- Solo NEVER asked again. Inferred server-side from ZARC majority `solo_canonico` per `cod_ibge`. Stored on produtor as `solo_inferido` + shown in plain language.
- One new backend endpoint `GET /api/regiao` aggregates EXISTING tools dispatch (no new ingestion). Prices stay honest pendente until CONAB/PGPM ingestion exists — UI keeps "sem cotação disponível", no fake numbers.
- Chat persists by default: every `/api/chat` with `sessao_id` saves user+assistant turns into `mensagens`. Sessions listed ChatGPT-style.
- Memory minimal: LLM extracts 1-line facts post-turn (praga, cultura, area, local), stored in `memorias`, injected (last 8) into agent context. No vector DB, no embeddings.
- Auth minimal: no password/JWT now. Identity = `telefone` (unique) + `id` uuid. Front sends `produtor_id`; backend resolves. JWT only when asked.

## 3. Data model (Mongo `agropilot`, via existing `get_db()` in `back/app/db.py:17`)

```
produtores { id:str(uuid), telefone:str(unique), nome, municipio, uf, cod_ibge,
             solo_inferido, lavouras:[{cultura, area_ha, solo, irrigacao}],
             onboardingConcluido:bool, criado_em, atualizado_em }
sessoes    { id:str(uuid), produtor_id, titulo, uf, cod_ibge, criado_em, atualizado_em }
mensagens  { id:str(uuid), sessao_id, produtor_id, autor:"usuario"|"copiloto",
             texto, intencao, fonte, dados, criado_em }
memorias   { id:str(uuid), produtor_id, texto, origem:"chat"|"onboarding",
             sessao_id, criado_em }
```

Indexes: `produtores.telefone unique`, `produtores.id unique`, `sessoes.produtor_id`,
`mensagens.sessao_id`, `memorias.produtor_id`. No migration — collections created on first insert.

## 4. API contract (additive, old routes untouched)

- `POST /api/produtor` real: upsert by `telefone`. Body = `ProdutorCreate` (already exists in `schemas/produtor.py:17-24`) + optional `solo_inferido`. Returns `{id, ...perfil}` persisted. `GET /api/produtor/{id}` reads Mongo, fallback mock only if db None.
- `GET /api/regiao?uf=SP&ibge=3503208&cultura=milho` → `{uf:{sigla,nome,regiao}, ibge, municipio, producao:{...from buscar_area_sigef}, solo:{soloId, descricao, fonte}, seguro:{...from buscar_risco_psr}, irrigacao:{...from buscar_irrigacao_ana}, precos:[3 pendente honest], oportunidade:{...}, fonte, data_extracao}`. Solo rule: majority `solo_canonico` in `zarc` for ibge; map `ad1-ad6→argiloso-ish/media` simplified: `arenoso|media|argiloso` + plain description. Errors never raise: missing layer → `estado:"sem_dado"` + honest detalhe.
- `POST /api/sessoes {produtor_id, titulo?, uf?, cod_ibge?}` → `{id,...}`; `GET /api/sessoes?produtor_id=` → list desc; `GET /api/sessoes/{id}/mensagens` → turns asc.
- `POST /api/chat {produtor_id, mensagem, sessao_id?}`: if `sessao_id` absent, auto-create session titled from first 40 chars. Save user turn before agent, assistant turn after. Inject `memorias` (last 8) + `perfil` (municipio/uf/ibge/cultura/solo_inferido) into `SYSTEM_AGENT` context. After answer, fire-and-forget memory extraction (LLM 1 call, never blocks response; failure → skip). Same for `/api/chat/stream` (save after done).
- `GET /api/memorias?produtor_id=` → list (for profile screen later).

Schemas: extend `ChatRequest` with `sessao_id?: str|None` (optional, backward compat). New `SessaoCreate`, `MensagemOut` in `schemas/chat.py` or new `schemas/sessao.py`.

## 5. Front changes

- `lib/api.ts` NEW: `apiUrl()` from `NEXT_PUBLIC_API_URL`, `postProdutor`, `getRegiao(uf,ibge,cultura)`, `postChat`, `postChatStream` (SSE meta/delta/done), `listSessoes/createSessao/getMensagens`. No new deps, fetch only.
- Onboarding (`onboarding/page.tsx`): ORDEM `nome → local → cultura → fim`. Remove `cidade` text input (lines 125-133) and `solo` block (153-175) entirely. New `local` step embeds `MapaBrasil` compact + UF select; selection sets `{municipio, uf, cod_ibge}`. `concluir()` calls `POST /api/produtor` (persist) then `atualizar({...perfil, onboardingConcluido:true})` → `/mapa`. Solo inferred shown on `fim` summary as "Solo da sua região (ZARC): X" read-only.
- `perfil-context.tsx`: add `id` from backend response; keep localStorage as cache. `cod_ibge` now always set from map pick, never default Araraquara silently.
- `mapa/page.tsx` + `PainelRegional`: fetch `GET /api/regiao?uf=&ibge=&cultura=` (ibge from perfil or selected municipio). Replace `insightsDaUF/precosDaUF` local with response; keep `EvidenceCard` states — `disponivel` shows numbers, missing stays `pendente/sem_dado` honest. Prices: still null until ingestion → keep current honest UI.
- `/assistente`: replace `responderLocal` with `postChatStream` (fallback `postChat`). Send `produtor_id + sessao_id + mensagem`. Render `fonte` + `dados.ferramentas_usadas`. Sidebar sessions list (like ChatGPT): new chat button, click loads `getMensagens`. Greeting uses perfil nome + municipio real.
- `dados-locais.ts`: keep `CULTURAS/SUGESTOES` (static lists fine). Delete `SOLOS` usage in onboarding; keep export (unused) or remove. `responderLocal` stays as offline fallback only when fetch fails.

## 6. Memory extraction (minimal)

After assistant answer: one LLM call `gerar_resposta("MEMORIA", turn, prompt)` asking "liste fatos duráveis (cultura, praga, área, local, preferência), 1 por linha, ou VAZIO". Each line → `memorias` doc. Injection: `_ctx_usuario` gains `\nmemorias:\n- ...` (last 8) + `\nperfil: nome; municipio/UF (ibge); cultura; solo_inferido`. Cap 2000 chars total. Never invents: only stored lines.

## 7. Build order (lanes)

- Phase 0 (done): recon + this doc.
- Phase 1 backend A: `produtores` real + `GET /api/regiao` + solo-majority (+ tests). No front dependency.
- Phase 2 backend B: `sessoes/mensagens/memorias` + chat persist + memory inject (+ tests). Depends on A for perfil shape only (can run parallel with contract above).
- Phase 3 front C: onboarding map picker + remove cidade/solo + `POST /api/produtor` wiring. Depends on A contract.
- Phase 4 front D: painel fetch regiao + assistente real + sessions sidebar. Depends on A+B contracts.
- Phase 5 validate: `PYTHONPATH=back pytest back/tests -q`, `npm run build` front, `docker compose up -d` curls (regiao, chat milho, stream), commit + push main.

## 8. Validation per phase

- A: pytest new `test_regiao.py` (solo majority fake db, sigef/psr/ana passthrough, missing → sem_dado); curl `GET /api/regiao?uf=SP&ibge=3503208&cultura=milho` real.
- B: pytest `test_sessoes.py` (auto-create, save turns, memory inject mocked LLM); curl chat with `sessao_id` then `GET mensagens`.
- C: `npm run build` OK; manual onboarding creates produtor in Mongo (`db.produtores.findOne`).
- D: manual `/assistente` "risco plantar milho minha região" returns ZARC real (not "modo navegação"); painel SP shows SIGEF/PSR/ANA numbers with fonte.

## 9. Honest gaps kept

- PGPM/CONAB prices: no ingestion → stay "sem cotação disponível". Cepea stays external link (license).
- Oportunidade ZARC×SIGEF: computed only if both layers present, else pendente.
- Clima realtime: ZARC windows + INMET note, no fake forecast.
- No JWT/password now; telefone identity documented.
