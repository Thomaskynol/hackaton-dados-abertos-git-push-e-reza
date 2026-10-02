"""Análise de lacuna de cobertura do seguro rural (município × cultura)."""

from .metricas import cobertura_pct, resumir_grupo, taxa_sinistro_pct

try:  # ponytail: parse/canon moram em correlacao.canon; sem duplicar
    from correlacao.canon import canonizar, parse_area
except ImportError:
    from .metricas import canonizar, parse_area
from .ranking import (COLUNAS_CSV, PII_PROIBIDO, linha_resultado, rankear,
                      sem_pii, to_csv, to_markdown)
from .score import (PESO_DESCOBERTURA, PESO_EXPOSICAO, PESO_RISCO,
                    escore_lacuna, normalizar_por_cultura)
from .sintese import (frase_top10, resumo_por_cultura, resumo_por_uf,
                      sintese_narrativa)

__all__ = ["canonizar", "parse_area", "cobertura_pct", "taxa_sinistro_pct",
           "resumir_grupo", "escore_lacuna", "normalizar_por_cultura",
           "PESO_EXPOSICAO", "PESO_RISCO", "PESO_DESCOBERTURA",
           "linha_resultado", "rankear", "to_csv", "to_markdown",
           "sem_pii", "COLUNAS_CSV", "PII_PROIBIDO",
           "frase_top10", "resumo_por_cultura", "resumo_por_uf",
           "sintese_narrativa"]
