"""Agregacao SIGEF sementes -> sigef_agregado.jsonl (documento-mestre Sec. 5, 11).

Stdlib only, streaming (csv.reader linha a linha, sem pandas).
Entradas (CSV `;`; SIGEF em UTF-8, PSR em latin1 — ver psr.py):
  - campos:     Safra;Especie;...;Municipio;UF;...;Area;Producao bruta;Producao estimada
  - declaracao: ...;AREATOTAL;MUNICIPIO;UF;ESPECIE;...;AREAPLANTADA;AREAESTIMADA;QUANTRESERVADA;...
Saida: correlacao/output/sigef_agregado.jsonl, grain geo x cultura.

Mapeamento declaracao (ver provenance.transformations):
  area_total_ha     = AREAPLANTADA (fallback AREATOTAL se plantada vazia)
  producao_estimada = AREAESTIMADA | area_reserva_ha = QUANTRESERVADA (unidade
  original preservada; caveat em provenance)
  campos: Area -> area_total_ha, Producao bruta/estimada -> respectivos.

cod_ibge via lookup nome+uf em correlacao/output/municipios.jsonl; se o
arquivo nao existir, cod_ibge sai "" (cobertura 0%).

Uso:
    python3 correlacao/sigef.py [--campos CSV] [--decl CSV] [--out JSONL] [--prov JSON]
"""
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from correlacao.canon import cultura_canonica, sem_acento
except ImportError:  # executado de dentro de correlacao/
    from canon import cultura_canonica, sem_acento

MUNICIPIOS = "correlacao/output/municipios.jsonl"

# Nome cientifico (prefixo) -> cultura comum. Prefix-match ordenado (maior 1o).
# Fallback: cultura_canonica(especie) = genero em latim (ex. 'urochloa').
ESPECIE_MAP = [
    ("Glicina max", "soja"), ("Glycine max", "soja"),
    ("Zea mays", "milho"), ("Triticum aestivum", "trigo"),
    ("Oryza sativa", "arroz"), ("Phaseolus vulgaris", "feijao"),
    ("Vigna unguiculata", "feijao"), ("Gossypium hirsutum", "algodao"),
    ("Solanum tuberosum", "batata"), ("Solanum lycopersicum", "tomate"),
    ("Avena sativa", "aveia"), ("Avena strigosa", "aveia"),
    ("Avena brevis", "aveia"), ("Avena byzantina", "aveia"),
    ("Hordeum vulgare", "cevada"), ("Secale cereale", "centeio"),
    ("Triticosecale", "triticale"), ("Sorghum bicolor", "sorgo"),
    ("Sorghum sudanense", "sorgo"), ("Arachis hypogaea", "amendoim"),
    ("Allium cepa", "cebola"), ("Coffea arabica", "cafe"),
    ("Cenchrus americanus", "milheto"), ("Pennisetum glaucum", "milheto"),
    ("Cucurbita", "abobora"), ("Cucumis sativus", "pepino"),
    ("Cucumis melo", "melao"), ("Citrullus", "melancia"),
    ("Daucus carota", "cenoura"), ("Lactuca sativa", "alface"),
    ("Nicotiana", "fumo"), ("Sesamum indicum", "gergelim"),
    ("Capsicum annuum", "pimentao"), ("Capsicum chinense", "pimenta"),
    ("Megathyrsus", "pastagem"), ("Urochloa", "pastagem"),
    ("Brachiaria", "pastagem"), ("Lolium", "pastagem"),
    ("Crotalaria", "crotalaria"), ("Vicia sativa", "ervilhaca"),
    ("Raphanus sativus", "nabo"), ("Fagopyrum", "trigo_sarraceno"),
]


def cultura_de_especie(especie):
    esp = " ".join((especie or "").split())
    for prefixo, cultura in ESPECIE_MAP:
        if esp.startswith(prefixo):
            return cultura
    return cultura_canonica(esp)  # fallback: genero em latim


def norm_municipio(nome):
    return " ".join(sem_acento(nome or "").lower().split())


def num_br(raw):
    """'9,5' -> 9.5. ''/'-' -> 0.0."""
    s = (raw or "").strip()
    if s in ("", "-"):
        return 0.0
    s = s.replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def carregar_lookup(caminho=MUNICIPIOS):
    """(municipio_norm, UF) -> cod_ibge. {} se arquivo ausente."""
    lookup = {}
    try:
        fh = open(caminho, encoding="utf-8")
    except FileNotFoundError:
        return lookup
    with fh:
        for lin in fh:
            lin = lin.strip()
            if not lin:
                continue
            try:
                d = json.loads(lin)
            except ValueError:
                continue
            cod = str(d.get("cod_ibge") or d.get("geocodigo") or "")
            nome = d.get("nome") or d.get("municipio") or d.get("NM_MUNICIPIO") or ""
            uf = str(d.get("uf") or d.get("SG_UF") or "").strip().upper()
            if cod and nome and uf:
                lookup[(norm_municipio(nome), uf)] = cod
    return lookup


def agregar(campos_csv, decl_csv, lookup):
    grupos = {}  # (municipio_norm, uf, cultura) -> acumuladores
    linhas = {"campos": 0, "declaracao": 0}

    def grupo(muni_norm, uf, cultura):
        g = grupos.get((muni_norm, uf, cultura))
        if g is None:
            g = grupos[(muni_norm, uf, cultura)] = {
                "cod_ibge": lookup.get((muni_norm, uf), ""),
                "campos": 0, "area": 0.0, "bruta": 0.0,
                "estimada": 0.0, "reserva": 0.0, "fontes": set()}
        return g

    with open(campos_csv, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.reader(fh, delimiter=";")
        h = next(rdr)
        i = {c: h.index(c) for c in
             ["Especie", "Municipio", "UF", "Area", "Producao bruta", "Producao estimada"]}
        for lin in rdr:
            linhas["campos"] += 1
            muni, uf = norm_municipio(lin[i["Municipio"]]), lin[i["UF"]].strip().upper()
            g = grupo(muni, uf, cultura_de_especie(lin[i["Especie"]]))
            g["campos"] += 1
            g["area"] += num_br(lin[i["Area"]])
            g["bruta"] += num_br(lin[i["Producao bruta"]])
            g["estimada"] += num_br(lin[i["Producao estimada"]])
            g["fontes"].add("campos")

    with open(decl_csv, encoding="utf-8-sig", newline="") as fh:
        rdr = csv.reader(fh, delimiter=";")
        h = next(rdr)
        i = {c: h.index(c) for c in
             ["MUNICIPIO", "UF", "ESPECIE", "AREATOTAL", "AREAPLANTADA",
              "AREAESTIMADA", "QUANTRESERVADA"]}
        for lin in rdr:
            linhas["declaracao"] += 1
            muni, uf = norm_municipio(lin[i["MUNICIPIO"]]), lin[i["UF"]].strip().upper()
            g = grupo(muni, uf, cultura_de_especie(lin[i["ESPECIE"]]))
            g["campos"] += 1
            plantada = num_br(lin[i["AREAPLANTADA"]])
            g["area"] += plantada if plantada else num_br(lin[i["AREATOTAL"]])
            g["estimada"] += num_br(lin[i["AREAESTIMADA"]])
            g["reserva"] += num_br(lin[i["QUANTRESERVADA"]])
            g["fontes"].add("declaracao")

    return grupos, linhas


def main(argv):
    cfg = {"campos": "base de dados/sigefcamposproducaodesementes.csv",
           "decl": "base de dados/sigefdeclaracaoareaproducao.csv",
           "out": "correlacao/output/sigef_agregado.jsonl",
           "prov": "correlacao/output/provenance/sigef.json"}
    for k, flag in (("campos", "--campos"), ("decl", "--decl"),
                    ("out", "--out"), ("prov", "--prov")):
        if flag in argv:
            cfg[k] = argv[argv.index(flag) + 1]

    lookup = carregar_lookup()
    grupos, linhas = agregar(cfg["campos"], cfg["decl"], lookup)

    os.makedirs(os.path.dirname(cfg["out"]) or ".", exist_ok=True)
    with open(cfg["out"], "w", encoding="utf-8") as fh:
        for (muni, uf, cultura) in sorted(grupos):
            g = grupos[(muni, uf, cultura)]
            fh.write(json.dumps({
                "municipio_norm": muni, "uf": uf, "cod_ibge": g["cod_ibge"],
                "cultura_canonica": cultura, "total_campos": g["campos"],
                "area_total_ha": round(g["area"], 2),
                "producao_bruta_t": round(g["bruta"], 2),
                "producao_estimada_t": round(g["estimada"], 2),
                "area_reserva_ha": round(g["reserva"], 2),
                "fonte": "+".join(sorted(g["fontes"])),
            }, ensure_ascii=False) + "\n")

    n_grupos = len(grupos)
    com_ibge = sum(1 for g in grupos.values() if g["cod_ibge"])
    cobertura = round(com_ibge / n_grupos * 100, 2) if n_grupos else 0.0
    por_muni = defaultdict(float)
    for (muni, uf, _), g in grupos.items():
        por_muni[(muni, uf)] += g["area"]
    top5 = sorted(por_muni.items(), key=lambda kv: -kv[1])[:5]

    os.makedirs(os.path.dirname(cfg["prov"]) or ".", exist_ok=True)
    with open(cfg["prov"], "w", encoding="utf-8") as fh:
        json.dump({
            "_id": "sigef", "name": "MAPA — SIGEF Sementes",
            "url": "https://dados.agricultura.gov.br/",
            "license": "CC-BY", "extracted_at": date.today().isoformat(),
            "reference_period": "2013-2017 (campos + declaracao)",
            "transformations": [
                "especie cientifica -> cultura comum (ESPECIE_MAP, fallback genero)",
                "campos.Area -> area_total_ha; Producao bruta/estimada -> respectivos",
                "declaracao.AREAPLANTADA (fallback AREATOTAL) -> area_total_ha",
                "declaracao.AREAESTIMADA -> producao_estimada_t",
                "declaracao.QUANTRESERVADA -> area_reserva_ha (unidade original)",
                "lookup (municipio_norm, UF) -> cod_ibge via municipios.jsonl",
            ],
            "fields_used": ["Especie/ESPECIE", "Municipio/MUNICIPIO", "UF",
                             "Area", "Producao bruta", "Producao estimada",
                             "AREATOTAL", "AREAPLANTADA", "AREAESTIMADA",
                             "QUANTRESERVADA"],
            "limitations": [
                "SIGEF cobre 2.414 pares municipio+UF de 5.570 — join tem lacuna.",
                "QUANTRESERVADA/AREAESTIMADA em unidade original do CSV.",
                "Especies sem mapa usam genero em latim como cultura_canonica.",
            ] + ([] if lookup else [
                "municipios.jsonl ausente: cod_ibge saiu vazio; rodar ZARC 1o."]),
            "stats": {"linhas_campos": linhas["campos"],
                      "linhas_declaracao": linhas["declaracao"],
                      "grupos": n_grupos, "grupos_com_ibge": com_ibge,
                      "cobertura_ibge_pct": cobertura},
        }, fh, ensure_ascii=False, indent=2)

    print(f"linhas={linhas} grupos={n_grupos} cobertura_ibge={cobertura}% "
          f"({com_ibge}/{n_grupos}) lookup_municipios={len(lookup)}")
    print("top-5 area_ha:")
    for (muni, uf), area in top5:
        print(f"  {muni} {uf}: {area:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))


if __name__ == "__main__":
    main(sys.argv[1:])
