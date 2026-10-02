# 04 — Resultados: tabela priorizada (estado honesto)

> Medido em 2026-10-02, branch `feat/lacuna-seguro`, Mongo local `agropilot` (`mongodb://localhost:27017`). Código ganha da spec.

## 1. Tabela priorizada: vazia por falta de dado ranqueável (honesto)

- `docs/tabela-lacuna.csv` + `docs/tabela-lacuna.md`: **só header, 0 linhas**.
- Gerado por `cd back && python -m app.lacuna.tabela --csv ../docs/tabela-lacuna.csv --md ../docs/tabela-lacuna.md` → `linhas=0`.
- Motivo: `gerar()` colapsa `psr_agregado` 2016–2024 e descarta grupo sem `area_total > 0`; Mongo local tem **só 2025, sem nenhum campo de área** (ver §2). Sem área + sem sinistro, `escore_lacuna = 0.0` para tudo → nada ranqueável → header-only. Nenhum número inventado.

## 2. O que o Mongo local tem (medido agora)

- `psr_agregado`: 4.340 docs, **só `ano: 2025`**, 0 sinistros, R$ 0,00 pagos.
- Chaves reais: `ano, cod_ibge, cultura_canonica, fonte_arquivo, municipio, por_evento, taxa_sinistro_pct, total_apolices, total_pago_reais, total_sinistros, uf` — **nenhum `area_*`**.
- `NR_AREA_TOTAL` nunca entrou na whitelist (`psr.py` antes desta branch) nem no JSON gravado → Rota B era obrigatória (feita: `psr.py` + `canon.py`, commit `f5b4a5a`).
- CSVs fonte (`base de dados/`, gitignored) **ausentes localmente**; `correlacao/output/` ausente. Série 2016–2024 indisponível → reingestão pendente.

## 3. Testes (repro)

```bash
pytest correlacao -q                    # 61 passed
cd back && pytest tests/ -q             # 69 passed, 1 skipped
```

- `test_golden_leitura_real` (§4.2: 16.428 pares, 684.997 apólices pequenas, 12.985.903 ha, SECA 157.350…): **SKIP honesto** — série 2016–2024 ausente. Nunca XFAIL, nunca número ajustado.
- `test_apolice_2025_sem_sinistro`: **passa** — trava viva do estado medido (2025 = 0 sinistros).
- `test_lacuna.py` (20) + `test_tabela.py` (3): passam sem rede/Mongo (FakeDB + sintético).

## 4. Sensibilidade e Top 10: não há — sem dado real

- Análise de sensibilidade dos pesos existe, mas sobre **sintético** (ver `docs/03-metodologia.md` §5) — não é achado.
- Top 10 determinístico, frases `frase_top10`, resumos cultura/UF e `sintese_narrativa`: **implementados e testados**, mas sem saída real até a reingestão. Rodar `sintese_narrativa([])` hoje retorna "Sem dados suficientes…" (fonte + incerteza declaradas).

## 5. Limitações (o que o gestor precisa saber)

1. Cobertura por apólice ≠ cobertura por produtor (um produtor, N apólices; nem toda lavoura segurada aparece no PSR).
2. Janela 2016–2024 fixa em `tabela.py`; 2025 excluído por desenho (0 sinistros, sem área).
3. `AREA_PEQUENA_MAX = 50` ha é ponto de partida, não norma.
4. `cultura_canonica` legado colapsa safras; `canonizar` novo (preserva safra) usado só no código novo.
5. Sem endpoint/coleção `lacuna_*` ainda — módulo + tabela + docs nesta branch; carga Mongo (`load_mongo.py:FILES`) e API ficam para o próximo passo.

## 6. Próximos passos

1. Obter CSVs SISSER 2016–2024 → `python3 correlacao/psr.py [CSVs]` → `load_mongo.py` → `test_golden_leitura_real` sai do SKIP.
2. Regenerar `docs/tabela-lacuna.csv/md` (mesmo comando §1) → Top 10 + `04` atualizado com achados reais.
3. Encaixe: `lacuna_municipio_cultura` em `load_mongo.py:FILES`, query `buscar_lacuna` em `dados_reais.py`, handler em `tools.py`, painel no front.
