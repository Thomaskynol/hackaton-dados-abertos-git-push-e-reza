"""Escore de lacuna + normalização por cultura.

Fórmula (ponto de partida, ver docs/03-metodologia.md)::

    exposicao  = log(1 + area_pequena_ha)
    risco      = taxa_sinistro_pct
    lacuna     = exposicao * risco * (1 - cobertura_pct / 100)

Sem área ou sem sinistralidade o escore é 0.0 (fora do ranking) — finito sempre.
"""

import math

# ponytail: pesos 1.0 = fórmula pura; sensibilidade em docs/03-metodologia.md
PESO_EXPOSICAO = 1.0
PESO_RISCO = 1.0
PESO_DESCOBERTURA = 1.0


def escore_lacuna(area_pequena_ha, taxa_sinistro_pct, cobertura_pct,
                  w_exp=PESO_EXPOSICAO, w_risco=PESO_RISCO,
                  w_desc=PESO_DESCOBERTURA):
    """Escore bruto >= 0, finito e determinístico. None/faltante -> 0.0."""
    try:
        area = max(float(area_pequena_ha), 0.0)
        risco = max(float(taxa_sinistro_pct), 0.0)
        cob = float(cobertura_pct)
    except (TypeError, ValueError):
        return 0.0
    if not (0.0 <= cob <= 100.0):
        return 0.0
    expo = math.log1p(area)
    desc = 1.0 - cob / 100.0
    out = (expo ** w_exp) * (risco ** w_risco) * (desc ** w_desc)
    if not math.isfinite(out):
        return 0.0
    return round(out, 4)


def normalizar_por_cultura(linhas):
    """Min-max de escore_lacuna -> escore_norm em [0, 1], por cultura.

    Preserva ordem relativa dentro da cultura. Cultura com escore único
    (max == min) recebe 0.5 para todas. Não muta a entrada.
    """
    por_cult = {}
    for lin in linhas:
        por_cult.setdefault(lin.get("cultura"), []).append(lin)
    saida = []
    for cultura, grupo in por_cult.items():
        vals = [float(g.get("escore_lacuna", 0.0) or 0.0) for g in grupo]
        lo, hi = min(vals), max(vals)
        for lin, v in zip(grupo, vals):
            nova = dict(lin)
            nova["escore_norm"] = 0.5 if hi == lo else round((v - lo) / (hi - lo), 4)
            saida.append(nova)
    return saida
