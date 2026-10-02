"""Ingestao Agrofit -> correlacao/output/agrofit.jsonl (stdlib only, streaming).

Le formulados (~391MB, linhas fisicas fragmentadas: campo EMPRESA_PAIS_TIPO
contem quebras de linha + cauda binaria apos o bloco valido) e tecnicos (3k),
gera 1 doc por registro logico SEM explodir (CULTURA nao contem separadores).

Uso: python3 correlacao/agrofit.py
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from canon import cultura_canonica, tox_numerica

# Sugestao: rode com o cwd na raiz do repo; caminhos relativos ao script.
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMULADOS = os.path.join(BASE, "base de dados", "agrofitprodutosformulados.csv")
TECNICOS = os.path.join(BASE, "base de dados", "agrofitprodutostecnicos.csv")
OUT_JSONL = os.path.join(BASE, "correlacao", "output", "agrofit.jsonl")
OUT_PROV = os.path.join(BASE, "correlacao", "output", "provenance", "agrofit.json")

HEAD = re.compile(r"^[A-Z0-9]{1,10};")  # inicio de registro logico: NR_REGISTRO
MAX_CHUNK_LINES = 500  # trava: lixo binario gera chunks gigantes -> descarta
SEP = (";", ",", "/")


def fix(s):
    """Desfaz mojibake UTF-8 lido como latin1/cap1252; preserva bytes 8-bit puros."""
    if not s:
        return ""
    try:
        return s.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def clean(s):
    return fix(s).strip()


def org_canon(v):
    v = (v or "").strip().upper()
    if v == "NAO":
        return "N"
    if v == "SIM":
        return "S"
    return (v or "")  # como vier: "", "OUTROS", ...


def reassemble(chunk):
    """Chunk (linhas fisicas de 1 registro) -> 15 campos ou None."""
    rows = list(csv.reader(io.StringIO(chunk), delimiter=";"))
    if not rows:
        return None
    head, tail = rows[0], rows[-1]
    if len(head) < 11 or len(tail) < 5:
        return None
    empresa = "".join(head[10:] + [f for r in rows[1:-1] for f in r] + tail[:-4])
    fields = head[:10] + [empresa] + tail[-4:]
    if len(fields) != 15:
        return None
    return [clean(f) for f in fields]


def iter_formulados(path):
    """Gera registros logicos validos (lista de 15 campos). Contadores p/ report."""
    stats = Counter(n_physical=0, chunks=0, dropped_chunk=0, bad_reassemble=0,
                    bad_nr=0, bad_tail=0, ok=0, cultura_com_sep=0)
    chunk = []
    with open(path, encoding="cp1252", errors="replace", newline="") as fh:
        for line in fh:
            stats["n_physical"] += 1
            if HEAD.match(line) and chunk:
                yield from flush(chunk, stats)
                chunk = [line]
            else:
                chunk.append(line)
                if len(chunk) > MAX_CHUNK_LINES:
                    stats["dropped_chunk"] += 1
                    chunk = []  # perde o registro; ressincroniza no proximo HEAD
        if chunk:
            yield from flush(chunk, stats)
    yield stats


def flush(chunk, stats):
    stats["chunks"] += 1
    text = "".join(chunk)
    if not text.rstrip("\r\n").upper().endswith("TRUE"):
        stats["bad_tail"] += 1
        return
    f = reassemble("".join(chunk))
    if f is None:
        stats["bad_reassemble"] += 1
        return
    if not re.fullmatch(r"[A-Z0-9]+", f[0]):
        stats["bad_nr"] += 1
        return
    if any(s in (f[7] or "") for s in SEP):
        stats["cultura_com_sep"] += 1
    stats["ok"] += 1
    yield f


def main():
    os.makedirs(os.path.dirname(OUT_JSONL), exist_ok=True)
    os.makedirs(os.path.dirname(OUT_PROV), exist_ok=True)
    tox_dist = Counter()
    n_form = n_tec = 0

    with open(OUT_JSONL, "w", encoding="utf-8") as out:
        gen = iter_formulados(FORMULADOS)
        stats = Counter()
        for item in gen:
            if isinstance(item, Counter):
                stats = item
                continue
            (nr, marca, _form, ingr, _tit, _classe, _modo, cultura,
             praga, _praga_comum, _empresa, tox, _amb, org, sit) = item
            t = tox_numerica(tox)
            tox_dist[t if t is not None else "null"] += 1
            out.write(json.dumps({
                "nr_registro": nr, "marca_comercial": marca,
                "ingrediente_ativo": ingr, "tipo": "formulado",
                "cultura_canonica": cultura_canonica(cultura),
                "praga_nome_cientifico": praga or None,
                "classe_toxicologica": t, "organicos": org_canon(org),
                "situacao": sit,
            }, ensure_ascii=False) + "\n")
            n_form += 1

        with open(TECNICOS, encoding="cp1252", errors="replace", newline="") as fh:
            for row in csv.DictReader(fh, delimiter=";"):
                t = tox_numerica(clean(row.get("CLASSIFICACAO_TOXICOLOGICA")))
                tox_dist[t if t is not None else "null"] += 1
                out.write(json.dumps({
                    "nr_registro": clean(row.get("NUMERO_REGISTRO")),
                    "marca_comercial": clean(row.get("PRODUTO_TECNICO_MARCA_COMERCIAL")),
                    "ingrediente_ativo": clean(row.get(
                        "INGREDIENTE_ATIVO(GRUPO_QUIMICI)(CONCENTRACAO)")),
                    "tipo": "tecnico", "cultura_canonica": None,
                    "praga_nome_cientifico": None,
                    "classe_toxicologica": t, "organicos": None,
                    "situacao": None,
                }, ensure_ascii=False) + "\n")
                n_tec += 1

    prov = {
        "_id": "agrofit", "name": "MAPA — Agrofit (produtos formulados + tecnicos)",
        "url": "https://www.gov.br/agricultura/pt-br/assuntos/insumos-agropecuarios/insumos-agricolas/agrotoxicos/agrofit",
        "license": "desconhecida — verificar em dados.agricultura.gov.br",
        "extracted_at": "2026-10-02", "reference_period": "desconhecido (arquivo local)",
        "transformations": [
            "leitura streaming ';' cp1252 (superset de latin1) + desfaz mojibake UTF-8",
            "reagrupamento de linhas fisicas em registros logicos (EMPRESA_PAIS_TIPO tem quebras)",
            "descarte de cauda binaria pos-bloco valido + chunks > 500 linhas",
            "1 doc por registro, sem split de CULTURA",
            "cultura_canonica/tox_numerica via correlacao/canon.py; ORGANICOS NAO/SIM->N/S",
        ],
        "fields_used": ["NR_REGISTRO", "MARCA_COMERCIAL", "INGREDIENTE_ATIVO",
                        "CULTURA", "PRAGA_NOME_CIENTIFICO", "CLASSE_TOXICOLOGICA",
                        "ORGANICOS", "SITUACAO"],
        "limitations": [
            "rotulos compostos ('Categoria 4 - ...') -> classe_toxicologica null (contrato tox_numerica)",
            "tecnicos sem cultura/praga/organicos/situacao -> null",
            "sem geo: join por cultura_canonica + praga_cientifica",
        ],
        "measured": {"formulados_validos": n_form, "tecnicos": n_tec,
                     "linhas_fisicas": stats["n_physical"],
                     "chunks_descartados": stats["dropped_chunk"] + stats["bad_reassemble"]
                     + stats["bad_nr"] + stats["bad_tail"],
                     "cultura_com_separador": stats["cultura_com_sep"]},
    }
    with open(OUT_PROV, "w", encoding="utf-8") as fh:
        json.dump(prov, fh, ensure_ascii=False, indent=2)

    print(f"docs: formulados={n_form} tecnicos={n_tec} total={n_form + n_tec}")
    print("tox:", dict(sorted(tox_dist.items(), key=str)))
    print("parse:", {k: stats[k] for k in
                     ("n_physical", "chunks", "ok", "bad_tail", "bad_reassemble",
                      "bad_nr", "dropped_chunk", "cultura_com_sep")})


if __name__ == "__main__":
    main()
