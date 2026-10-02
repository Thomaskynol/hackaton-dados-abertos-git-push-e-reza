"""Ingestao ANA Atlas Irrigacao -> correlacao/output/ana_atlas.jsonl (stdlib only).

Le os 2 XLSX via zipfile+ElementTree (sem openpyxl/pandas) e gera 1 doc por
cod_ibge, juntando area atual+potencial (grupo/sistema/AAI) com projecoes
2030/2040. Uso: python3 correlacao/ana.py
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canon import ibge7

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_ATUAL = os.path.join(BASE, "base de dados",
                       "_ANA_AtlasIrrigacao_AreaAtualePotencial_Mun_UF.xlsx")
F_PROJ = os.path.join(BASE, "base de dados",
                      "_ANA_AtlasIrrigacao_AreaAtual_Projecao2030-2040_env.xlsx")
OUT_JSONL = os.path.join(BASE, "correlacao", "output", "ana_atlas.jsonl")
OUT_PROV = os.path.join(BASE, "correlacao", "output", "provenance", "ana.json")

M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
CODE = re.compile(r"^\d{7}\d?$")


def col_idx(ref):
    """'C10' -> 2. Celulas esparsas: mapeia pela letra da coluna."""
    letters = "".join(ch for ch in ref if ch.isalpha())
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read_sheet(path, sheet_no=1):
    """Retorna dict {excel_row: {col: valor}} + shared strings resolvidas."""
    z = zipfile.ZipFile(path)
    try:
        ss_root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        ss = ["".join(t.text or "" for t in si.iter(f"{M}t"))
              for si in ss_root.findall(f"{M}si")]
    except KeyError:
        ss = []
    sh = ET.fromstring(z.read(f"xl/worksheets/sheet{sheet_no}.xml"))
    grid = {}
    for row in sh.iter(f"{M}row"):
        rn = int(row.get("r", "0"))
        cells = {}
        for c in row.findall(f"{M}c"):
            ref = c.get("r", "")
            if not ref:
                continue
            v = c.find(f"{M}v")
            txt = v.text if v is not None and v.text is not None else ""
            if c.get("t") == "s" and txt != "":
                try:
                    txt = ss[int(txt)]
                except (IndexError, ValueError):
                    pass
            cells[col_idx(ref)] = txt
        if cells:
            grid[rn] = cells
    return grid


def num(v):
    if v is None or v == "":
        return None
    try:
        f = float(str(v).replace(",", "."))
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


def code_str(v):
    s = "".join(ch for ch in str(v or "") if ch.isdigit())
    if not CODE.match(s):
        return None
    return ibge7(s)


TIPOS_2019 = ["arroz_inundado", "cafe", "cana_irrigada", "outras_pivos",
              "pivos_total", "outras_sistemas", "area_total_irrigada",
              "cana_fertirrigada", "area_total_geral"]
TIPOS_PROJ = TIPOS_2019[:7]  # sem fertirrigada/geral nas projecoes


def main():
    os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PROV), exist_ok=True)

    g_atual = read_sheet(F_ATUAL)  # header excel-row 7, dados a partir da 8
    g_proj = read_sheet(F_PROJ)    # header excel-row 9, dados a partir da 10
    docs = {}

    for rn, cells in g_atual.items():
        if rn < 8:
            continue
        cod = code_str(cells.get(1))
        if not cod:
            continue
        vals = [num(cells.get(i)) for i in range(4, 13)]
        docs[cod] = {
            "cod_ibge": cod, "municipio": (cells.get(2) or "").strip(),
            "uf": (cells.get(3) or "").strip(),
            "tipologias_2019": dict(zip(TIPOS_2019, vals)),
            "grupo_predominante": (cells.get(13) or "").strip() or None,
            "sistema_predominante": (cells.get(14) or "").strip() or None,
            "aai": {
                "superficial_sequeiro": num(cells.get(15)),
                "superficial_pastagem": num(cells.get(16)),
                "subterranea": num(cells.get(17)),
                "potencial_total": num(cells.get(18)),
                "potencial_efetivo": num(cells.get(19)),
            },
            "projecao_2030": {}, "projecao_2040": {},
        }

    n_proj = 0
    for rn, cells in g_proj.items():
        if rn < 10:
            continue
        cod = code_str(cells.get(1))
        if not cod or cod not in docs:
            continue
        docs[cod]["projecao_2030"] = dict(
            zip(TIPOS_PROJ, (num(cells.get(i)) for i in range(13, 20))))
        docs[cod]["projecao_2040"] = dict(
            zip(TIPOS_PROJ, (num(cells.get(i)) for i in range(20, 27))))
        n_proj += 1

    with open(OUT_JSONL, "w", encoding="utf-8") as out:
        for cod in sorted(docs):
            out.write(json.dumps(docs[cod], ensure_ascii=False) + "\n")

    prov = {
        "_id": "ana_atlas", "name": "ANA — Atlas Irrigacao 2021 (area atual + projecoes)",
        "url": "https://www.snirh.gov.br/portal/snirh",
        "license": "desconhecida — verificar portal SNIRH/ANA",
        "extracted_at": "2026-10-02", "reference_period": "2019 (obs) / 2030+2040 (proj)",
        "transformations": [
            "leitura stdlib zipfile+ElementTree (sem openpyxl/pandas)",
            "header real linhas 7/9; merge dos 2 arquivos por codigo IBGE",
            "cod_ibge via ibge7 (corta digito extra); numericos->float/int",
        ],
        "fields_used": ["Codigo", "Municipio", "UF", "tipologias 2019 (9)",
                        "Grupo/Sistema Predominante", "AAI (5)", "projecoes 2030/2040 (7+7)"],
        "limitations": ["projecoes sao cenarios do Atlas, nao observacao",
                        "ignora aba Atlas_UF (agregado por UF)"],
        "measured": {"municipios": len(docs), "com_projecao": n_proj},
    }
    with open(OUT_PROV, "w", encoding="utf-8") as fh:
        json.dump(prov, fh, ensure_ascii=False, indent=2)

    print(f"municipios={len(docs)} com_projecao={n_proj}")
    ara = docs.get("3503208")
    print("Araraquara 3503208:", json.dumps(ara, ensure_ascii=False) if ara else "NAO ACHADO")


if __name__ == "__main__":
    main()
