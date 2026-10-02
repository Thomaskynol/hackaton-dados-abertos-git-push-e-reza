# 05 — Descoberta: o que já existe (medido em 2026-10-02, branch `feat/lacuna-seguro`)

> Regra do projeto: código ganha do prompt. Divergências listadas em §5.

## 1. Estrutura real do repo

```text
back/            FastAPI (app/main.py +7 routers, app/routes/, app/schemas/, app/core/)
                 Lógica runtime: app/tools.py (dispatch 6 tools) + app/dados_reais.py (queries Mongo) + app/llm.py
                 Testes: back/tests/ (pytest 8 + conftest FakeDB em memória)
correlacao/      Ingestão stdlib-only (zarc.py, psr.py, sigef.py, agrofit.py, ana.py, canon.py, load_mongo.py)
                 Testes: test_canon.py, test_ingest.py (unittest stdlib)
front/           Next.js 14 + React 18 + Tailwind (sem tabela/ranking/export hoje)
docs/            5 arquivos, nenhum numerado 01–05 (ver §5)
docker-compose.yml  mongo:7 + api + front + seed (one-shot mongorestore, só se base vazia)
```

- **Roda com:** `docker compose up -d` (tudo) ou `up -d mongo` (só banco);
  back local: `cd back && uvicorn app.main:app --reload --port 8000`; testes: `pytest tests/ -v`.
- **NÃO existe:** `routes/services/orchestrators/models/schemas/tests` no formato do prompt,
  nem `services/zarc.py, psr.py, sigef.py, agrofit.py, ana.py, municipios.py, clima.py,
  culture_mapper.py, rules.py, evidence.py, ai.py, provider.py`.
  Equivalentes reais: `correlacao/*.py` (ingestão) + `back/app/tools.py,dados_reais.py,llm.py` (runtime).

## 2. Reuso possível

- `correlacao/psr.py` — agregação SISSER→JSONL (whitelist LGPD, streaming `;` latin1) — **estender** com `NR_AREA_TOTAL`+anos 2016–2024 (Rota B, §6).
- `correlacao/canon.py` — `sem_acento`, `ibge7`, `e_sinistro`, `tox_numerica` — reutilizar; criar `canonizar`/`parse_area` novos ao lado (não quebrar assinatura).
- `correlacao/load_mongo.py` — carga JSONL→Mongo (`FILES=[zarc,municipios,psr_agregado,sigef_agregado,agrofit,ana_atlas]`) — adicionar `lacuna_municipio_cultura` aqui.
- `correlacao/test_ingest.py` — invariantes de coleções + testes PII (`PII_PROIBIDO`, `test_psr_sem_pii`) — estender, não duplicar.
- `back/app/dados_reais.py` — padrão `buscar_*` retornando `None` sem dado — nova query de lacuna segue o padrão.
- `back/app/tools.py` — dispatch de tools (`_t_*` + `_HANDLERS` + `TOOLS_SCHEMA`) — novo handler de lacuna se virar endpoint.
- `back/app/routes/regiao.py` — padrão `_bloco_* → {estado: disponivel|sem_dado|pendente, fonte:{nome,periodo,limitacoes}}`, nunca raise — saída da análise segue o padrão.
- `back/app/llm.py` + `back/app/core/templates.py` — LLM opcional (OPENROUTER, sem chave→`None`) + templates fallback — síntese narrativa segue o padrão.
- `back/tests/conftest.py` (`make_db(FakeCol)`) + `test_regiao.py`/`test_tools.py` — modelo de teste sem rede — `test_lacuna.py` segue o modelo.
- `front/src/components/PainelRegional.tsx` / `radar/page.tsx` — encaixe futuro da tabela (hoje sem `<table>`/CSV/Markdown).

## 3. Coleções Mongo relevantes (banco `agropilot`, `mongodb://localhost:27017`, medido agora)

| Coleção | Docs | Amostra / campos | Tem área? |
|---|---|---|---|
| `psr_agregado` | 4.340 (**só ano 2025**; 46.137 apólices, **0 sinistros, R$ 0,00**) | `{cod_ibge, uf, municipio, cultura_canonica, ano, total_apolices, total_sinistros, taxa_sinistro_pct, total_pago_reais, por_evento[], fonte_arquivo}`; 53 culturas | **NÃO** — `NR_AREA_TOTAL` não lido nem gravado |
| `municipios` | 5.573 | `{cod_ibge, nome, uf}` | n/a (hub) |
| `zarc` | 957.490 | janelas plantio por cultura×município×solo | n/a |
| `sigef_agregado` | 10.084 | `{municipio_norm, uf, cod_ibge (vazio na amostra DF!), cultura_canonica, total_campos, area_total_ha, ...}` | parcial (sementes, não PSR) |
| `ana_atlas` | 5.570 | Atlas Irrigação por município | n/a |
| `agrofit` | 16.697 | formulados+técnicos | n/a |

- `lacuna_*`: **não existe** (zero hits em `*.py` e `back/`). Rota `/analise|/lacuna`: **não existe**.
- CSVs fonte (`base de dados/`, gitignored) **ausentes localmente**; `correlacao/output/` ausente (derivado, gitignored).

## 4. O que NÃO existe e preciso criar

- [ ] Extensão `correlacao/psr.py`: ler `NR_AREA_TOTAL` (+subvenção? ver §5), anos 2016–2024, `zfill(7)` — **bloqueado até CSVs estarem disponíveis**.
- [ ] `back/app/lacuna/` (ou `analise/lacuna/` adaptado ao real: `back/app/`): `metricas.py`, `score.py`, `ranking.py`, `sintese.py` + prompt da síntese em arquivo.
- [ ] Coleção `lacuna_municipio_cultura` (+ entrada em `load_mongo.py:FILES`).
- [ ] `back/tests/test_lacuna.py`: golden numbers §4.2, encoding, regras PSR, métrica/escore, `test_sem_pii`.
- [ ] Tabela priorizada (CSV + Markdown) + Top 10 determinístico + resumos por cultura/UF.
- [ ] `docs/03-metodologia.md` (fórmula + pesos + sensibilidade) e `docs/04-resultados.md` (achados + limitações).

## 5. Divergências prompt × código (código ganha)

1. **Arquitetura:** prompt descreve `routes/services/orchestrators/models/schemas/tests` + 11 services — real é `routes/schemas/core` + `tools/dados_reais/llm` + `correlacao/*.py`. Sigo o real.
2. **Dados locais ≠ §4.2:** prompt assume 2016–2024 ingeridos (1.048.565 linhas, 16.428 pares…); **Mongo local tem só 2025** (4.340 docs, 46.137 apólices, 0 sinistros). Golden numbers **não reproduzíveis** até reingestão — documentado, não assumido.
3. **`cultura_canonica` colapsa safras:** `canon.py:33-36` pega só o 1º token (`"Milho 1ª Safra"→"milho"`), então `canonizar("Milho 1ª")==canonizar("Milho 2ª")` — o teste `test_safra_distinta` do prompt **falha contra o helper atual**. Criar `canonizar` novo preservando safra/ordinal; não mudar `cultura_canonica` (em uso).
4. **`e_sinistro` × milhar:** `canon.py:65-71` faz `float(valor.replace(",","."))` sem remover `.` de milhar (`"120.587,38"→ValueError→False`); `psr.py:num_br` trata certo. Usar `num_br` como referência no código novo.
5. **`ibge7` sem `zfill(7)`:** `canon.py:57-62` e `psr.py:65` só filtram dígitos (e cortam dígito extra); prompt exige `zfill(7)`. Aplicar `zfill` no código novo sem alterar o helper em uso.
6. **Docs numerados não existem:** sem `01/02/03/04/05`, sem `03-metodologia.md`/`04-resultados.md`; `dicionario-de-dados.md:89` cita `NR_AREA_TOTAL` mas **nenhum código lê esse campo**. `historico.md` corrige volume Agrofit (16.697 válidos, não 280k do prompt).
7. **Cobertura ZARC de uva/maçã:** premissa do prompt (§4.3) ainda **não verificada** contra o ZARC local (957k docs) — verificar na implementação, não assumir.
8. **Números de sinistro/área do prompt** (SECA 157.350, área pequena 12.985.903 ha etc.) **não verificáveis** sem os CSVs 2016–2024 — viram teste pendente, não verdade.

## 6. Decisão: Rota B (evidência, não preferência)

`psr_agregado.findOne()` **não tem nenhum campo de área** — `NR_AREA_TOTAL` nunca entra na whitelist (`psr.py:27-29`) nem no JSON gravado (`psr.py:111-118`).
→ Análise **não** pode ser só-leitura. Plano: script **incremental** estendendo `psr.py`
(whitelist + `NR_AREA_TOTAL` com parse `.replace(".","").replace(",", ".")`, filtro 2016–2024,
`zfill(7)`, `$set` do que falta), **só quando os CSVs SISSER 2016–2024 estiverem disponíveis**
(hoje ausentes: `base de dados/` não existe localmente). Custo a documentar na hora.
PII segue fora da whitelist (testes `test_ingest.py:115-125,253-260` já cobrem; novo `test_sem_pii` na saída).

## 7. Próximos passos

1. Obter CSVs SISSER 2016–2024 → rodar ingestão incremental (Rota B).
2. Criar módulo lacuna em `back/app/` + `test_lacuna.py` (golden numbers §4.2 como validação da leitura).
3. Tabela CSV+Markdown, Top 10 determinístico, resumos cultura/UF, `04-resultados.md`, PR sem merge.
