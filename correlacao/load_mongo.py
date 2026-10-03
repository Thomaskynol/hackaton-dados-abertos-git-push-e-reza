"""Carrega JSONLs de correlacao/output/ no Mongo local (db agropilot).

Colecoes homonimas aos arquivos + indices da Sec. 5 do documento-mestre.
Uso: python3 correlacao/load_mongo.py [--uri mongodb://localhost:27017] [--batch 5000]
"""
import argparse
import json
import sys
from pathlib import Path

from pymongo import MongoClient

OUT = Path(__file__).resolve().parent / "output"
DB = "agropilot"
BATCH = 5000

FILES = ["zarc", "municipios", "psr_agregado", "sigef_agregado", "agrofit", "ana_atlas", "precos_conab"]


def load_collection(db, name, batch):
    path = OUT / f"{name}.jsonl"
    col = db[name]
    col.drop()
    buf = []
    total = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            buf.append(json.loads(line))
            if len(buf) >= batch:
                col.insert_many(buf, ordered=False)
                total += len(buf)
                buf.clear()
                print(f"  {name}: {total}...", flush=True)
    if buf:
        col.insert_many(buf, ordered=False)
        total += len(buf)
    print(f"  {name}: {total} docs OK")
    return total


def create_indexes(db):
    db.zarc.create_index(
        [("cod_ibge", 1), ("manejo_canonico", 1), ("solo_canonico", 1),
         ("cultura_canonica", 1), ("abertos", 1)], name="zarc_join")
    db.agrofit.create_index(
        [("cultura_canonica", 1), ("praga_nome_cientifico", 1)], name="agrofit_cultura_praga")
    # ponytail: indice simples (doc sugere parcial organicos="S"); parcial quando filtro provar necessidade
    db.agrofit.create_index(
        [("cultura_canonica", 1), ("organicos", 1)], name="agrofit_cultura_organicos")
    db.psr_agregado.create_index(
        [("cod_ibge", 1), ("cultura_canonica", 1), ("ano", -1)], name="psr_geo_cultura_ano")
    db.municipios.create_index([("cod_ibge", 1)], unique=True, name="municipios_cod_ibge")
    db.precos_conab.create_index(
        [("cultura_canonica", 1), ("tipo", 1), ("uf", 1), ("ano", 1)], name="precos_cultura_uf_ano")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--uri", default="mongodb://localhost:27017")
    ap.add_argument("--batch", type=int, default=BATCH)
    args = ap.parse_args()
    client = MongoClient(args.uri)
    db = client[DB]
    totals = {}
    for name in FILES:
        print(f"loading {name}...")
        totals[name] = load_collection(db, name, args.batch)
    print("indexes...")
    create_indexes(db)
    for n in FILES:
        print(f"  {n}: count={db[n].count_documents({})}")
    print("indexes zarc:", sorted(i["name"] for i in db.zarc.list_indexes()))
    print("indexes agrofit:", sorted(i["name"] for i in db.agrofit.list_indexes()))
    print("indexes psr_agregado:", sorted(i["name"] for i in db.psr_agregado.list_indexes()))
    print("indexes municipios:", sorted(i["name"] for i in db.municipios.list_indexes()))


if __name__ == "__main__":
    sys.exit(main())
