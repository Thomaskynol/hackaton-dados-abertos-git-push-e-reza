"""Passo 3 (operacional): revalida as 5 culturas da PAM contra o IBGE vivo.

Uso (a partir de back/):
    IBGE_AUTO_UPDATE=1 python scripts/revalidar_series.py

Idempotente: a rotina de auto-update tem TTL (IBGE_TTL_DIAS, default 7), então
rodar de novo não martela a API.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(message)s")

from app.db import get_db           # noqa: E402
from app.precos_dados import (     # noqa: E402
    CULTURA_LABEL,
    atualizar_serie_viva,
    _ano_mais_recente_no_db,
)

CULTURAS = ["feijao", "arroz", "milho", "soja", "trigo"]


def main() -> int:
    db = get_db()
    if db is None:
        print("Sem Mongo — nada a revalidar.")
        return 1
    print(f"Ano mais recente publicado pelo IBGE: ", end="")
    try:
        from app.precos_ibge import ultimo_ano_disponivel
        print(ultimo_ano_disponivel())
    except Exception as e:
        print(f"indisponivel ({e!r})")
    print()
    for c in CULTURAS:
        antes = _ano_mais_recente_no_db(db, c)
        try:
            atualizar_serie_viva(db, c)
        except Exception as e:
            print(f"  {CULTURA_LABEL.get(c, c):14s} FALHOU: {e!r}")
            continue
        depois = _ano_mais_recente_no_db(db, c)
        sinal = "atualizado" if depois > antes else "ja estava em dia"
        print(f"  {CULTURA_LABEL.get(c, c):14s} ano {antes} -> {depois}  ({sinal})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())