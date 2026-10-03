"""Baixa os CSVs do SISSER/PSR (dados abertos MAPA, CC-BY) de forma automatica.

Fonte oficial: portal CKAN https://dados.agricultura.gov.br
Dataset "sisser3" (Sistema de Subvencao Economica ao Premio do Seguro Rural).
URLs de download sao estaveis (resource id do CKAN).

Uso:
    python correlacao/baixar_psr.py [--hist] [--2025] [--out DIR]

    --hist : baixa o consolidado 2016-2024 (97 MB) — tem sinistros/eventos reais
    --2025 : baixa a safra corrente 2025 (adesao, sem sinistros liquidados ainda)
    (sem flag: baixa os dois)

Stdlib only (urllib). Streaming para disco, nunca carrega tudo em memoria.
"""
import os
import sys
import urllib.request

# resource ids do CKAN (verificados via /api/3/action/package_search em 2026-10)
FONTES = {
    "2016a2024": "https://dados.agricultura.gov.br/dataset/baefdc68-9bad-4204-83e8-f2888b79ab48/resource/54e04a6b-15b3-4bda-a330-b8e805deabe4/download/dados_abertos_psr_2016a2024csv.csv",
    "2025": "https://dados.agricultura.gov.br/dataset/baefdc68-9bad-4204-83e8-f2888b79ab48/resource/ac7e4351-974f-4958-9294-627c5cbf289a/download/dados_abertos_psr_2025csv.csv",
}

NOMES = {
    "2016a2024": "dados_abertos_psr_2016a2024csv.csv",
    "2025": "dados_abertos_psr_2025csv.csv",
}


def baixar(url: str, destino: str) -> int:
    """Baixa url -> destino em streaming. Retorna bytes gravados. Fecha o handle."""
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "AgroPilot/1.0 (dados abertos)"})
    total = 0
    with urllib.request.urlopen(req, timeout=300) as resp, open(destino, "wb") as fh:
        while True:
            bloco = resp.read(1 << 20)  # 1 MB
            if not bloco:
                break
            fh.write(bloco)
            total += len(bloco)
    return total


def main(argv):
    out = "base de dados"
    for i, a in enumerate(argv):
        if a == "--out" and i + 1 < len(argv):
            out = argv[i + 1]
    quer_hist = "--hist" in argv
    quer_2025 = "--2025" in argv
    if not quer_hist and not quer_2025:
        quer_hist = quer_2025 = True

    alvos = []
    if quer_hist:
        alvos.append("2016a2024")
    if quer_2025:
        alvos.append("2025")

    for chave in alvos:
        destino = os.path.join(out, NOMES[chave])
        print(f"baixando {chave} -> {destino} ...", flush=True)
        n = baixar(FONTES[chave], destino)
        print(f"  ok: {n/1024/1024:.1f} MB", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
