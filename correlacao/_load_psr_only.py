"""Carrega SOMENTE psr_agregado.jsonl no Mongo (sem tocar nas outras colecoes).

Uso: python correlacao/_load_psr_only.py [--uri mongodb://127.0.0.1:27017]
"""
import argparse
import json
from pathlib import Path

from pymongo import MongoClient

OUT = Path(__file__).resolve().parent / "output"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="mongodb://127.0.0.1:27017")
    ap.add_argument("--batch", type=int, default=5000)
    args = ap.parse_args()

    db = MongoClient(args.uri, serverSelectionTimeoutMS=5000)["agropilot"]
    col = db["psr_agregado"]
    col.drop()

    buf, total = [], 0
    with open(OUT / "psr_agregado.jsonl", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            buf.append(json.loads(ln))
            if len(buf) >= args.batch:
                col.insert_many(buf, ordered=False)
                total += len(buf)
                buf.clear()
    if buf:
        col.insert_many(buf, ordered=False)
        total += len(buf)

    col.create_index(
        [("cod_ibge", 1), ("cultura_canonica", 1), ("ano", -1)],
        name="psr_geo_cultura_ano",
    )
    # indice extra para a agregacao por UF (agregar_psr_uf filtra por uf)
    col.create_index([("uf", 1), ("cultura_canonica", 1)], name="psr_uf_cultura")

    print("inseridos", total)
    print("count", col.estimated_document_count())
    print("anos", sorted(col.distinct("ano")))
    print("com_sinistro", col.count_documents({"total_sinistros": {"$gt": 0}}))
    print("com_evento", col.count_documents({"por_evento.0": {"$exists": True}}))


if __name__ == "__main__":
    main()
