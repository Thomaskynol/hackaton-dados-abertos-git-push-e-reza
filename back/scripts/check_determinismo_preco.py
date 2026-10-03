"""Verificação manual do determinismo da previsão (Passo 1) e do ano-alvo (Passo 2).

Uso (a partir de back/):
    python scripts/check_determinismo_preco.py

Compara o card visto DUAS vezes seguidas: antes, a IA devolvia números
diferentes a cada chamada (R$ 265 numa hora, R$ 321 na outra). Agora tem que
vir sempre igual. Mostra também a regressão ao lado da IA — a regressão é o
número determinístico que fica na tela mesmo com a IA desligada.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db                       # noqa: E402
from app.precos_dados import resumo_tendencia   # noqa: E402

CASOS = [("feijao", "SP"), ("arroz", "SP"), ("milho", "MS"), ("soja", "BA")]


def main() -> int:
    db = get_db()
    falhas = 0
    for cult, uf in CASOS:
        a = resumo_tendencia(db, cult, uf)
        b = resumo_tendencia(db, cult, uf)
        pa, pb = a.get("projecao") or {}, b.get("projecao") or {}
        igual = pa == pb
        pt = a.get("projecao_tendencia") or {}
        ult = a.get("ultimo") or {}
        print(f"{cult}/{uf}")
        print(f"   IA      : {pa.get('valor_estimado')} ({pa.get('origem')}) ano {pa.get('ano')}")
        print(f"   Regress.: {pt.get('valor_estimado')} ano {pt.get('ano')}")
        print(f"   ultimo  : {ult.get('ano')} {ult.get('valor')} | "
              f"var {a.get('variacao_ultimo_ano')}% | {a.get('direcao')}")
        print(f"   estavel : {'SIM' if igual else 'NAO - o numero mudou!'}")
        if not igual:
            falhas += 1
        print()
    print("RESULTADO:", "tudo estavel" if falhas == 0 else f"{falhas} caso(s) variando")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())