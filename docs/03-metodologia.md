# 03 — Metodologia: indicador lacuna-seguro (município × cultura)

> Implementado em `back/app/lacuna/` + `correlacao/psr.py` + `correlacao/canon.py`. Código ganha da spec.

## 1. Grain e janela

- Grain: 1 linha = (cod_ibge, cultura) colapsando anos 2016–2024 (`tabela.py:colapsar_por_municipio_cultura`).
- Anos fora de 2016–2024 ignorados (2025 cai fora — 0 sinistros, sem área).
- Município/UF do doc mais recente (`ano_max`).
- Grupo sem `area_total > 0` descartado — sem área não entra no ranking.

## 2. Ingestão (Rota B, `correlacao/`)

- Whitelist LGPD em `psr.py:COLS_NECESSARIAS` (+`NR_AREA_TOTAL`); PII/coords nunca lidos.
- `parse_area`: `12,5→12.5`, `1.234,56→1234.56`, `''/'-'/None/lixo→None`.
- `AREA_PEQUENA_MAX = 50` ha: apólice pequena = `area <= 50` (inclusivo).
- CSV sem coluna área (ex. 2025) → fallback sem área, não quebra.
- `ibge7z`: só dígitos, len>7 corta último, `zfill(7)`.
- `canonizar`: slug `[a-z0-9-]` preservando safra/ordinal (`Milho 1ª≠Milho 2ª`) + mojibake latin1; `cultura_canonica` antigo mantido intacto (em uso).

## 3. Métricas (`metricas.py`)

- `cobertura_pct = area_pequena / area_total * 100`, clamp [0,100], `None` se sem área.
- `taxa_sinistro_pct = sinistros / apolices * 100`, clamp [0,100], `None` se sem apólices.
- `resumir_grupo` aceita os dois namings (psr.py curto e Mongo `total_*`).

## 4. Escore (`score.py`)

```
exposicao = log(1 + area_pequena_ha)
risco     = taxa_sinistro_pct
lacuna    = exposicao^w_exp * risco^w_risco * (1 - cobertura_pct/100)^w_desc
```

- Pesos default 1.0 (`PESO_*`). Sem área/cobertura inválida/sinistro 0 → `0.0` (fora do ranking). Sempre finito, determinístico.
- Normalização min-max **por cultura** → `escore_norm ∈ [0,1]`; cultura com escore único recebe 0.5; não muta entrada.

## 5. Sensibilidade (sintético, 10 linhas espelhando §4.4)

| w_risco | top soja | efeito |
|---|---|---|
| 0.5 | Sorriso (norm 1.0), Itabera 0.998 | exposição domina: área pequena grande sobe mesmo com cobertura baixa |
| 1.0 | Itabera 1.0, Sorriso 0.825, Rio Verde 0.753 | ponto de partida |
| 2.0 | Itabera 1.0, Sorriso 0.529, Rio Verde 0.468 | risco domina: taxa alta compensa área menor |

`Assis Chateaubriand/milho` fica norm 1.0 nos três (único milho de alto escore no sintético — artefato do exemplo, não achado). Uva/maçã norm 0.5 (escore único por cultura). Conclusão: peso do risco move o meio do ranking, não o topo — fórmula estável para priorização, sensibilidade documentada para o gestor ajustar `w_*`.

## 6. Ranking e saídas (`ranking.py`, `tabela.py`)

- `linha_resultado(meta, grupo)`: meta + métricas + `escore_lacuna`, sempre via `sem_pii`.
- `rankear`: sort `escore_norm desc, area_pequena desc, cod_ibge asc`; `rank 1..N`; `top_n` opcional. Determinístico.
- `to_csv`: header exato spec §6.4a (`rank,cod_ibge,...,escore_lacuna`). `to_markdown`: mesmo + `escore_norm`.
- `PII_PROIBIDO` (9 chaves) removido em qualquer profundidade; `test_sem_pii` cobre CSV/Markdown/frase/síntese.

## 7. Síntese (`sintese.py`, `PROMPT_SINTESE.md`)

- Template determinístico 3 parágrafos: onde · por que importa · o que fazer. Fonte `MAPA/SISSER 2016–2024`, incerteza declarada (apólice ≠ produtor), sem receita agronômica (Lei 14.785/2023 art. 39), sem promessa financeira.
- LLM opcional via `llm_call(prompt+tabela)`: só usa resposta se string não-vazia **e** todo número citado existir na tabela (`_numeros_validos`); senão cai no template. `frase_top10` 1 frase/entrada estilo §6.4b; `resumo_por_cultura/uf` agregam área/apólices/sinistros/pago ordenados por área pequena desc.

## 8. Repro

```bash
pytest correlacao -q                                   # 61 passed
cd back && pytest tests/ -q                            # 69 passed, 1 skipped
cd back && python -m app.lacuna.tabela --csv ../docs/tabela-lacuna.csv --md ../docs/tabela-lacuna.md  # linhas=0 (sem dado ranqueavel)
```
