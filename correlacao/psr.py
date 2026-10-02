"""Agregacao PSR/SISSER -> psr_agregado.jsonl (documento-mestre Sec. 5.2, 9, 11).

Stdlib only, streaming (csv.reader linha a linha, sem pandas).
Entrada: CSV `;` latin1 do MAPA/SISSER. Aceita 1+ arquivos (2025 hoje, 2016-2024 depois).
Saida: correlacao/output/psr_agregado.jsonl, grain geo x cultura x ano.

LGPD (Sec. 9): le APENAS as colunas em COLS_NECESSARIAS. NM_SEGURADO,
NR_DOCUMENTO_SEGURADO e coordenadas nunca sao lidas nem armazenadas.

Uso:
    python3 correlacao/psr.py [ENTRADA ...] [--out SAIDA] [--prov PROV]
"""
import csv
import json
import os
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from correlacao.canon import cultura_canonica, e_sinistro
except ImportError:  # executado de dentro de correlacao/
    from canon import cultura_canonica, e_sinistro

# LGPD: whitelist de colunas. Todo o resto (PII, coords) eh ignorado na leitura.
COLS_NECESSARIAS = ["NM_MUNICIPIO_PROPRIEDADE", "SG_UF_PROPRIEDADE",
                    "NM_CULTURA_GLOBAL", "ANO_APOLICE", "CD_GEOCMU",
                    "VALOR_INDENIZAÇÃO", "EVENTO_PREPONDERANTE"]


def num_br(raw):
    """'120587,38' -> 120587.38. '-'/'vazio' -> 0.0."""
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


def agregar(entradas):
    grupos = {}  # (cod_ibge, uf, municipio, cultura, ano) -> registro mutavel
    linhas = 0
    sem_geo = 0
    for caminho in entradas:
        with open(caminho, encoding="latin1", newline="") as fh:
            rdr = csv.reader(fh, delimiter=";")
            header = next(rdr)
            idx = {c: header.index(c) for c in COLS_NECESSARIAS}  # KeyError se faltar coluna
            for lin in rdr:
                linhas += 1
                # LGPD: so toca nas colunas da whitelist
                muni = lin[idx["NM_MUNICIPIO_PROPRIEDADE"]].strip()
                uf = lin[idx["SG_UF_PROPRIEDADE"]].strip().upper()
                cultura = cultura_canonica(lin[idx["NM_CULTURA_GLOBAL"]])
                try:
                    ano = int((lin[idx["ANO_APOLICE"]] or "").strip())
                except ValueError:
                    continue
                cod = "".join(ch for ch in lin[idx["CD_GEOCMU"]] if ch.isdigit())
                if not cod:
                    sem_geo += 1
                ev_raw = lin[idx["EVENTO_PREPONDERANTE"]]
                val_raw = lin[idx["VALOR_INDENIZAÇÃO"]]
                sin = e_sinistro(ev_raw, val_raw)  # regra medida Sec. 5.2
                valor = num_br(val_raw)
                chave = (cod, uf, muni, cultura, ano)
                g = grupos.get(chave)
                if g is None:
                    g = grupos[chave] = {"apolices": 0, "sinistros": 0,
                                         "pago": 0.0, "eventos": Counter(),
                                         "ev_valor": Counter()}
                g["apolices"] += 1
                if sin:
                    g["sinistros"] += 1
                    g["pago"] += valor
                    ev = ev_raw.strip()
                    g["eventos"][ev] += 1
                    g["ev_valor"][ev] += valor
    return grupos, linhas, sem_geo


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    entradas = args or ["base de dados/dados_abertos_psr_2025csv.csv"]
    out = "correlacao/output/psr_agregado.jsonl"
    prov = "correlacao/output/provenance/psr.json"
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
        if a == "--prov" and i + 1 < len(argv):
            prov = argv[i + 1]
    fonte = "+".join(sorted(os.path.basename(e) for e in entradas))

    grupos, linhas, sem_geo = agregar(entradas)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    total_sin = 0
    with open(out, "w", encoding="utf-8") as fh:
        for (cod, uf, muni, cultura, ano) in sorted(grupos):
            g = grupos[(cod, uf, muni, cultura, ano)]
            total_sin += g["sinistros"]
            por_evento = [{"evento": ev, "apolices": g["eventos"][ev],
                           "valor": round(g["ev_valor"][ev], 2)}
                          for ev in sorted(g["eventos"],
                                           key=lambda e: -g["ev_valor"][e])]
            fh.write(json.dumps({
                "cod_ibge": cod, "uf": uf, "municipio": muni,
                "cultura_canonica": cultura, "ano": ano,
                "total_apolices": g["apolices"], "total_sinistros": g["sinistros"],
                "taxa_sinistro_pct": round(g["sinistros"] / g["apolices"] * 100, 2),
                "total_pago_reais": round(g["pago"], 2),
                "por_evento": por_evento, "fonte_arquivo": fonte,
            }, ensure_ascii=False) + "\n")

    anos = sorted({k[4] for k in grupos})
    limitacoes = ["Dados de apolice, nao de producao individual."]
    if total_sin == 0:
        limitacoes.append("2025 sem sinistros validos; aguardar 2016-2024.")
    os.makedirs(os.path.dirname(prov) or ".", exist_ok=True)
    with open(prov, "w", encoding="utf-8") as fh:
        json.dump({
            "_id": "psr", "name": "MAPA — SISSER/PSR",
            "url": "https://dados.agricultura.gov.br/",
            "license": "CC-BY", "extracted_at": date.today().isoformat(),
            "reference_period": f"{anos[0]}-{anos[-1]}" if anos else "",
            "transformations": ["filtro colunas LGPD (whitelist)",
                                "regra sinistro Sec. 5.2",
                                "agrupamento geo x cultura x ano"],
            "fields_used": COLS_NECESSARIAS,
            "limitations": limitacoes,
            "stats": {"linhas_lidas": linhas, "grupos": len(grupos),
                      "anos": anos, "total_sinistros": total_sin,
                      "linhas_sem_geocodigo": sem_geo,
                      "fonte_arquivo": fonte},
        }, fh, ensure_ascii=False, indent=2)

    print(f"linhas={linhas} grupos={len(grupos)} anos={anos} "
          f"sinistros={total_sin} sem_geocodigo={sem_geo} fonte={fonte}")


if __name__ == "__main__":
    main(sys.argv[1:])
