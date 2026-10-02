"""Gera a tabela priorizada a partir do Mongo (psr_agregado -> CSV + Markdown).

Uso:
    cd back && python -m app.lacuna.tabela [--csv SAIDA] [--md SAIDA] [--top N]

Colapsa o grain geo x cultura x ano em (município, cultura), calcula métricas
+ escore, normaliza por cultura e escreve o ranking. Sem dado ranqueável
(area + sinistro) a saída é só header — honesto, nunca inventado.
"""
import argparse
import os

from app.db import get_db
from .metricas import resumir_grupo
from .ranking import linha_resultado, rankear, to_csv, to_markdown


def colapsar_por_municipio_cultura(docs):
    """Docs psr_agregado (aceita os dois namings) -> 1 grupo por (ibge, cultura).

    Soma apólices/sinistros/pago/áreas; município/uf do doc mais recente.
    """
    grupos = {}
    for d in docs or []:
        ano = d.get("ano")
        if ano is not None:
            try:
                if not (2016 <= int(ano) <= 2024):
                    continue
            except (TypeError, ValueError):
                continue
        chave = (d.get("cod_ibge", ""), d.get("cultura_canonica",
                                              d.get("cultura", "")))
        g = grupos.get(chave)
        r = resumir_grupo(d)
        if g is None:
            g = grupos[chave] = {"meta": {"cod_ibge": chave[0],
                                          "municipio": d.get("municipio", ""),
                                          "uf": d.get("uf", ""),
                                          "cultura": chave[1]},
                                 "grupo": {"apolices": 0, "apolices_pequenas": 0,
                                           "area_pequena": 0.0, "area_total": 0.0,
                                           "sinistros": 0, "pago": 0.0},
                                 "ano_max": -1}
        g["grupo"]["apolices"] += r["apolices"]
        g["grupo"]["apolices_pequenas"] += r["apolices_pequenas"]
        g["grupo"]["area_pequena"] += r["area_pequena_ha"]
        g["grupo"]["area_total"] += r["area_total_ha"]
        g["grupo"]["sinistros"] += r["sinistros"]
        g["grupo"]["pago"] += r["pago_reais"]
        try:
            a = int(ano) if ano is not None else -1
        except (TypeError, ValueError):
            a = -1
        if a >= g["ano_max"]:
            g["ano_max"] = a
            g["meta"]["municipio"] = d.get("municipio", "") or g["meta"]["municipio"]
            g["meta"]["uf"] = d.get("uf", "") or g["meta"]["uf"]
    return [v for v in grupos.values() if v["grupo"]["area_total"] > 0]


def gerar(db, top_n=None):
    """Mongo -> linhas ranqueadas (com escore_norm). Vazio se sem área."""
    try:
        docs = list(db.psr_agregado.find({}, {"_id": 0}))
    except Exception:
        return []
    linhas = [linha_resultado(v["meta"], v["grupo"])
               for v in colapsar_por_municipio_cultura(docs)]
    com_risco = [l for l in linhas if l["escore_lacuna"] > 0]
    return rankear(com_risco, top_n=top_n)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="docs/tabela-lacuna.csv")
    ap.add_argument("--md", default="docs/tabela-lacuna.md")
    ap.add_argument("--top", type=int, default=None)
    args = ap.parse_args(argv)
    db = get_db()
    if db is None:
        print("sem Mongo (get_db None); nada gerado")
        return 1
    linhas = gerar(db, top_n=args.top)
    for path, texto in ((args.csv, to_csv(linhas)), (args.md, to_markdown(linhas))):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(texto)
    print(f"linhas={len(linhas)} csv={args.csv} md={args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
