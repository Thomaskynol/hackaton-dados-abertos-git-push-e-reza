# Histórico — branch `correlacao-de-dados`

Log de trabalho da parte de correlação de dados (documento-mestre §4, §5, §11, §15).
Atualizado a cada entrega. Front/back estão em outras branches; merge no final.

## Linha do tempo

| Data | Commit | O quê |
|---|---|---|
| 2026-10-02 | `753dbdf` | `base de dados/` entra no `.gitignore` (680MB, não commitar) |
| 2026-10-02 | `0b71658` | `docs/dicionario-de-dados.md` — coluna-a-coluna das 8 bases |
| 2026-10-02 | branch | `correlacao-de-dados` criada da main |
| 2026-10-02 | `fd1e9b1` | `docs/documento-mestre-agropilot.md` (referência) |
| 2026-10-02 | `60da2a7` | Ingestão completa + `docker-compose.yml` + `load_mongo.py` |
| 2026-10-02 | `7df70c3` | 48 testes unitários + fix toxicidade compostos |

## Arquivos desta branch (para o merge)

- `correlacao/canon.py` — mapas canônicos (SOLO/MANEJO/CICLO/CLIMA), `cultura_canonica`, `tox_numerica`, `ibge7`, `e_sinistro`
- `correlacao/{zarc,psr,sigef,agrofit,ana}.py` — ingestão stdlib (sem pandas), gera `correlacao/output/*.jsonl` (gitignored)
- `correlacao/load_mongo.py` — bulk load → db `agropilot` + índices Sec. 5 (pymongo)
- `correlacao/test_{canon,ingest}.py` — 48 testes, `python3 -m unittest discover -s correlacao` (~2s)
- `docker-compose.yml` — **raiz**, só serviço `mongo:7` + volume nomeado (backend/front entram aqui no merge)
- `docs/dicionario-de-dados.md`, `docs/documento-mestre-agropilot.md`

## Decisões (não reverter sem ler)

1. Compose na raiz, não em `mongo/` — mestre prevê um comando só p/ mongo+backend+front.
2. Volume nomeado, não bind em pasta — evita permissão/lixo no repo.
3. Stdlib only na ingestão — zero deps (sem pandas/openpyxl; XLSX via zipfile+ElementTree).
4. Outputs `correlacao/output/` gitignored — colegas regeneram local com `base de dados/` + scripts.
5. PII filtrada na entrada (§9) — `NM_SEGURADO` etc. nunca entram no Mongo (assert em teste).
6. PSR local é só 2025 (zero sinistros válidos) — pipeline pronto p/ 2016-2024, provenance registra limitação.

## Divergências medidas vs documento-mestre

1. Agrofit: 16.697 registros válidos (não 280k) — resto do CSV é lixo binário descartado.
2. `Cod_NM` vazio 71% (não 97%) — safra 2026/27 ≠ 2025/26 medida.
3. Araraquara: milho só em solos AD nesta safra (sem argiloso); área irrigada 426 ha (não 472).
4. Toxicidade: rótulos compostos `Categoria N – ...` → N via regex (era null).

## Guia de merge p/ main

1. `git checkout main && git pull && git merge correlacao-de-dados` (conflito esperado só se mexeram em `.gitignore`/`docker-compose.yml` — preferir esta versão).
2. Subir mongo: `docker compose up -d`.
3. Ter `base de dados/` local → `python3 correlacao/{zarc,psr,sigef,agrofit,ana}.py` → `python3 correlacao/load_mongo.py`.
4. Validar: `python3 -m unittest discover -s correlacao` (tudo verde, ~2s).
5. Backend consome coleções `agropilot.*` (schemas Sec. 5 do mestre); RiskEngine/motor ficam na branch backend.

## Merge main → correlacao-de-dados (2026-10-02, `89ee137`)

Main trouxe p/ branch:
- `back/` FastAPI mock (routes health/chat/onboarding/produtor/alertas + schemas + `mock.py`, módulo `app.main`, `requirements.txt`, `back/tests/test_contrato.py`)
- front estático (`index.html`, `styles/main.css`, `scripts/{api,app,copilot-ai,data}.js`, `hackathon/login/`)
- docs `CONTRATO_API.md` / `INTEGRACAO_SISTEMA.md` / `docs/PRODUCT_SPEC.md` (+ `arquitetura-front-and-end.md`, `README.md`)

Limpeza pós-merge (neste commit):
- junk removido: 16× `back/**/__pycache__/*.pyc` (vieram commitados no merge) — `git rm -r --cached` + rm; `.gitignore` já cobria `__pycache__/` e `*.pyc`, sem alteração
- compose: serviço `api` (python:3.12-slim, working_dir `/app`, `./back:/app`, 8000:8000, `MONGO_URL=mongodb://mongo:27017` + `CORS_ORIGINS`, `uvicorn app.main:app --host 0.0.0.0 --port 8000`, depends_on mongo); mongo intacto; `docker compose config` OK

## Rotina de trabalho (acordo)

- Commit pequeno e frequente; `git pull --rebase` a cada poucos commits.
- Wiki do projeto via dono: pergunta vai, resposta volta — usar quando faltar contexto profundo.
