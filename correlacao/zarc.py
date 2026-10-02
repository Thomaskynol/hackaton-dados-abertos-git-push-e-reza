"""Ingestao ZARC 2026/2027 -> hub municipios + fato zarc + proveniencia.

Uso: python3 correlacao/zarc.py  (a partir da raiz do repo)
Stdlib only, streaming (csv module). Contrato: docs/documento-mestre-agropilot.md Sec. 5.1/5.5/11.
Mapas e normalizacao importados de correlacao/canon.py (nao redefinidos aqui).

0 na coluna decN significa "nao indicado" -> excluido de dec, abertos, risco_min/max.
nm = null quando Cod_NM == "" (97%+ dos casos; so existe p/ soja).
"""
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from canon import CICLO_MAP, MANEJO_MAP, SOLO_MAP, cultura_canonica, ibge7

CORRELACAO = Path(__file__).resolve().parent
REPO = CORRELACAO.parent
CSV_PATH = REPO / "base de dados" / "dados-abertos-tabua-de-risco-safra-2026-2027.csv"
OUT_DIR = CORRELACAO / "output"
PROV_DIR = OUT_DIR / "provenance"

ORIGINAIS = ["Nome_cultura", "SafraIni", "SafraFin", "geocodigo", "UF",
             "municipio", "Portaria", "Cod_Solo", "Cod_Ciclo",
             "Cod_Outros_Manejos", "Cod_NM"]
DEC_COLS = [f"dec{n}" for n in range(1, 37)]


def _to_int(raw, default=None):
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError, AttributeError):
        return default


def abrir_csv(path):
    """Tenta utf-8-sig (encoding real do arquivo, com BOM); cai p/ latin1."""
    err = None
    for enc in ("utf-8-sig", "latin1"):
        f = open(path, encoding=enc, newline="")
        try:
            r = csv.DictReader(f, delimiter=";")
            next(r)  # forca decode do header + 1a linha
            f.seek(0)
            r = csv.DictReader(f, delimiter=";")
            if r.fieldnames and r.fieldnames[0].startswith("\ufeff"):
                r.fieldnames = [r.fieldnames[0].lstrip("\ufeff"), *r.fieldnames[1:]]
            return f, r
        except (UnicodeDecodeError, StopIteration) as e:
            err = e
            f.close()
    raise err


def montar_doc(row):
    cod_ibge = ibge7(row.get("geocodigo", ""))
    cod_nm = (row.get("Cod_NM") or "").strip()
    dec = {}
    for n in range(1, 37):
        v = _to_int(row.get(f"dec{n}"), 0) or 0
        if v != 0:
            dec[str(n)] = v
    abertos = sorted(int(k) for k in dec)
    vals = list(dec.values())
    cs, cc, cm = (_to_int(row.get(k)) for k in ("Cod_Solo", "Cod_Ciclo", "Cod_Outros_Manejos"))
    doc = {k: (row.get(k) or "") for k in ORIGINAIS}
    doc.update({
        "cod_ibge": cod_ibge,
        "cultura_canonica": cultura_canonica(row.get("Nome_cultura", "")),
        "ciclo_grupo": CICLO_MAP.get(cc) if cc is not None else None,
        "solo_canonico": SOLO_MAP.get(cs) if cs is not None else None,
        "manejo_canonico": MANEJO_MAP.get(cm) if cm is not None else None,
        "nm": _to_int(cod_nm) if cod_nm else None,
        "dec": dec,
        "abertos": abertos,
        "risco_min": min(vals) if vals else None,
        "risco_max": max(vals) if vals else None,
    })
    return doc


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROV_DIR.mkdir(parents=True, exist_ok=True)
    fz = open(OUT_DIR / "zarc.jsonl", "w", encoding="utf-8")
    municipios = {}
    total = nm_vazio = 0
    # spot-check Araraquara (3503208): milho x solo -> ciclos distintos
    ara_ad1_ciclos = set()
    ara_argiloso = 0
    try:
        f, reader = abrir_csv(CSV_PATH)
        with f:
            for row in reader:
                if not (row.get("geocodigo") or "").strip():
                    continue
                doc = montar_doc(row)
                fz.write(json.dumps(doc, ensure_ascii=False) + "\n")
                total += 1
                if doc["nm"] is None:
                    nm_vazio += 1
                if doc["cod_ibge"] not in municipios:
                    municipios[doc["cod_ibge"]] = {
                        "cod_ibge": doc["cod_ibge"],
                        "nome": doc["municipio"],
                        "uf": doc["UF"],
                    }
                if (doc["cod_ibge"] == "3503208"
                        and doc["cultura_canonica"] == "milho"
                        and doc["Nome_cultura"] == "Milho 1ª Safra"):
                    if doc["solo_canonico"] == "ad1":
                        ara_ad1_ciclos.add(doc["Cod_Ciclo"])
                    if doc["solo_canonico"] == "argiloso":
                        ara_argiloso += 1
    finally:
        fz.close()
    with open(OUT_DIR / "municipios.jsonl", "w", encoding="utf-8") as fm:
        for m in municipios.values():
            fm.write(json.dumps(m, ensure_ascii=False) + "\n")
    prov = {
        "_id": "zarc",
        "name": "MAPA — ZARC Tábua de Risco 2026/2027",
        "url": "https://dados.agricultura.gov.br/",
        "license": "CC-BY",
        "extracted_at": datetime.now(timezone.utc).date().isoformat(),
        "reference_period": "2026/2027",
        "transformations": [
            "streaming csv (delimiter ';', utf-8-sig BOM)",
            "normalizacao cultura via canon.cultura_canonica",
            "mapas canonicos SOLO_MAP/MANEJO_MAP/CICLO_MAP",
            "dec=0 tratado como nao indicado (excluido de dec/abertos/risco_min/risco_max)",
            "Cod_NM vazio -> nm=null",
            "hub municipios dedup por cod_ibge (ibge7)",
        ],
        "fields_used": ORIGINAIS + DEC_COLS,
        "limitations": ["ZARC e zoneamento municipal; nao considera microclima."],
    }
    with open(PROV_DIR / "zarc.json", "w", encoding="utf-8") as fp:
        json.dump(prov, fp, ensure_ascii=False, indent=2)
        fp.write("\n")
    pct_nm = 100.0 * nm_vazio / total if total else 0
    print(f"zarc docs: {total}")
    print(f"municipios: {len(municipios)}")
    print(f"Cod_NM vazio: {nm_vazio} ({pct_nm:.1f}%)")
    print(f"Araraquara 3503208 Milho 1a Safra/solo ad1 ciclos: {sorted(ara_ad1_ciclos)} "
          f"({len(ara_ad1_ciclos)} ciclos)")
    print(f"Araraquara 3503208 milho/solo argiloso docs: {ara_argiloso} "
          f"(safra 2026/27 so zoneia milho em solos AD p/ Araraquara)")


if __name__ == "__main__":
    main()
