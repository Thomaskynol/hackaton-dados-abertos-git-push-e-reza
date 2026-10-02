"""Métricas de cobertura e sinistralidade por (município, cultura).

Funções puras sobre grupos agregados. Nenhuma rede, nenhum Mongo aqui.
"""

import os
import sys

_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if _ROOT not in sys.path:  # ponytail: reuso sem duplicar parse/canon
    sys.path.insert(0, _ROOT)

try:
    from correlacao.canon import canonizar, parse_area
except ImportError:  # pragma: no cover - correlacao fora do path
    canonizar = None
    parse_area = None


def cobertura_pct(area_pequena, area_total):
    """area_pequena / area_total * 100. None se sem área. Sempre em [0, 100]."""
    try:
        peq = float(area_pequena)
        tot = float(area_total)
    except (TypeError, ValueError):
        return None
    if tot <= 0 or peq < 0:
        return None
    return round(min(peq / tot * 100.0, 100.0), 2)


def taxa_sinistro_pct(sinistros, apolices):
    """sinistros / apolices * 100. None se sem apólices."""
    try:
        s = float(sinistros)
        a = float(apolices)
    except (TypeError, ValueError):
        return None
    if a <= 0 or s < 0:
        return None
    return round(min(s / a * 100.0, 100.0), 2)


def resumir_grupo(grupo):
    """Grupo agregado (psr.py ou Mongo) -> métricas. Aceita os dois namings."""
    ap = grupo.get("apolices", grupo.get("total_apolices", 0)) or 0
    ap_peq = grupo.get("apolices_pequenas",
                       grupo.get("total_apolices_pequenas", 0)) or 0
    a_peq = grupo.get("area_pequena", grupo.get("area_pequena_ha", 0)) or 0
    a_tot = grupo.get("area_total", grupo.get("area_total_ha", 0)) or 0
    sin = grupo.get("sinistros", grupo.get("total_sinistros", 0)) or 0
    pago = grupo.get("pago", grupo.get("total_pago_reais", 0.0)) or 0.0
    return {
        "apolices": int(ap),
        "apolices_pequenas": int(ap_peq),
        "area_pequena_ha": round(float(a_peq), 2),
        "area_total_ha": round(float(a_tot), 2),
        "cobertura_pct": cobertura_pct(a_peq, a_tot),
        "sinistros": int(sin),
        "taxa_sinistro_pct": taxa_sinistro_pct(sin, ap),
        "pago_reais": round(float(pago), 2),
    }
