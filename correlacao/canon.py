"""Contratos canonicos da correlacao AgroPilot (documento-mestre Sec. 5 e 11).

Stdlib only. Importado pelos scripts de ingestao de cada base.
"""
import unicodedata

# --- Mapas canonicos (dicionario oficial ZARC 2026, conferidos) ---
SOLO_MAP = {1: "arenoso", 2: "media", 3: "argiloso",
            11: "ad1", 12: "ad2", 13: "ad3", 14: "ad4", 15: "ad5", 16: "ad6"}
MANEJO_MAP = {1: "sequeiro", 2: "irrigado", 3: "irrigado_geada"}
CICLO_MAP = {13: "perene", 19: "semiperene", 20: "grupo_i", 21: "grupo_ii",
             22: "grupo_iii", 24: "grupo_iv", 25: "grupo_v", 26: "grupo_vi"}
CLIMA_MAP = {0: "nao_se_aplica", 1: "alta_frio", 2: "media_frio",
             3: "baixa_frio", 4: "semiarido", 5: "ameno", 6: "quente",
             7: "tropical", 8: "subtropical_ameno", 9: "subtropical_frio",
             11: "subtropical"}

# --- Toxicidade Agrofit -> escala numerica (Sec. 5.3) ---
TOX = {"Categoria 1": 1, "Categoria 2": 2, "Categoria 3": 3,
       "Categoria 4": 4, "Categoria 5": 5,
       "Extremamente Toxico": 1, "Altamente Toxico": 2,
       "Medianamente Toxico": 3, "Pouco Toxico": 4}
# 'Nao Classificado' / 'NAO DETERMINADO' / 'Nao Classificado - ...' -> None

CULTURAS_FOCO = {"milho", "soja", "feijao", "arroz", "trigo"}


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def cultura_canonica(nome: str) -> str:
    """'Milho 1a Safra' -> 'milho'. Primeiro token, minusculo, sem acento."""
    base = sem_acento(nome or "").lower().strip().split()
    return base[0].replace("-", "_") if base else ""


def tox_numerica(rotulo: str):
    """Rotulo toxicidade -> 1..5 ou None (nao-numerico nao passa em $gte)."""
    import re
    if not rotulo:
        return None
    r = sem_acento(rotulo).strip()
    low = r.lower()
    if low.startswith("nao classificado") or "nao determinado" in low:
        return None
    m = re.search(r"categoria\s*([1-5])", low)  # "Categoria 4 - Produto..." -> 4
    if m:
        return int(m.group(1))
    for k, v in TOX.items():
        if sem_acento(k).lower() == low:
            return v
    return None


def ibge7(codigo) -> str:
    """Normaliza codigo IBGE p/ 7 digitos (ANA traz digito extra)."""
    s = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    if len(s) > 7:
        s = s[:-1]
    return s


def e_sinistro(evento: str, valor) -> bool:
    """Regra medida Sec. 5.2: evento preenchido E indenizacao > 0."""
    if (evento or "").strip() in ("", "-"):
        return False
    try:
        return float(str(valor).replace(",", ".")) > 0
    except (ValueError, TypeError):
        return False
