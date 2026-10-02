"""Ranking, linha de resultado e saídas CSV/Markdown (sem PII, sempre)."""

from .metricas import resumir_grupo
from .score import escore_lacuna, normalizar_por_cultura

# LGPD: essas chaves nunca passam do ranking para qualquer saída.
PII_PROIBIDO = {"NM_SEGURADO", "NR_DOCUMENTO_SEGURADO", "CPF", "CNPJ",
                "LATITUDE", "LONGITUDE", "LAT", "LON", "COORDENADAS"}

COLUNAS_CSV = ["rank", "cod_ibge", "municipio", "uf", "cultura",
               "area_pequena_ha", "area_total_ha", "cobertura_pct",
               "apolices", "apolices_pequenas", "sinistros",
               "taxa_sinistro_pct", "pago_reais", "escore_lacuna"]


def sem_pii(obj):
    """Copia dicts/listas removendo chaves PII em qualquer profundidade."""
    if isinstance(obj, dict):
        return {k: sem_pii(v) for k, v in obj.items() if k not in PII_PROIBIDO}
    if isinstance(obj, list):
        return [sem_pii(v) for v in obj]
    return obj


def linha_resultado(meta, grupo):
    """meta {cod_ibge, municipio, uf, cultura} + grupo agregado -> linha."""
    lin = {"cod_ibge": meta.get("cod_ibge", ""),
           "municipio": meta.get("municipio", ""),
           "uf": meta.get("uf", ""),
           "cultura": meta.get("cultura", "")}
    lin.update(resumir_grupo(grupo))
    lin["escore_lacuna"] = escore_lacuna(lin["area_pequena_ha"],
                                        lin["taxa_sinistro_pct"] or 0.0,
                                        lin["cobertura_pct"]
                                        if lin["cobertura_pct"] is not None
                                        else -1)
    return sem_pii(lin)


def rankear(linhas, top_n=None):
    """Ordena por escore_norm desc; desempate: area_pequena desc, cod_ibge asc.

    Calcula escore_norm se ausente. Atribui rank 1..N (determinístico).
    """
    base = (linhas if any("escore_norm" in l for l in linhas)
            else normalizar_por_cultura(linhas))
    ords = sorted(base,
                  key=lambda l: (-float(l.get("escore_norm", 0.0) or 0.0),
                                 -float(l.get("area_pequena_ha", 0.0) or 0.0),
                                 str(l.get("cod_ibge", ""))))
    if top_n is not None:
        ords = ords[: max(0, int(top_n))]
    return [sem_pii({**dict(lin), "rank": i + 1})
            for i, lin in enumerate(ords)]


def to_csv(linhas):
    """CSV com header exato da spec (§6.4a)."""
    vals = []
    for lin in linhas:
        vals.append(",".join(
            "" if lin.get(c) is None else str(lin.get(c)) for c in COLUNAS_CSV))
    return "\n".join([",".join(COLUNAS_CSV)] + vals) + "\n"


def to_markdown(linhas):
    """Tabela Markdown (inclui escore_norm)."""
    head = COLUNAS_CSV + ["escore_norm"]
    md = ["| " + " | ".join(head) + " |",
          "|" + "|".join(["---"] * len(head)) + "|"]
    for lin in linhas:
        md.append("| " + " | ".join(
            "" if lin.get(c) is None else str(lin.get(c)) for c in head) + " |")
    return "\n".join(md) + "\n"
