"""Série histórica de PREÇOS -> precos_conab.jsonl (documento-mestre Sec. 5, 11).

Duas camadas de dados REAIS e públicos, pensadas para a IA fazer predição:

  1. SÉRIE HISTÓRICA DE PREÇO AO PRODUTOR (IBGE / PAM — tabela 1612 do SIDRA).
     Para cada cultura, UF e ano, o IBGE publica o Valor da produção (R$) e a
     Quantidade produzida (t). O preço médio recebido pelo produtor é
     valor/quantidade (R$/t), que convertemos para R$/saca de 60 kg. É uma
     série anual longa (décadas), por estado — base real para tendência e
     predição. Fonte oficial, domínio público, baixada via API ao rodar.

  2. PREÇO MÍNIMO OFICIAL (PGPM — CONAB/MAPA), o "piso" por cultura/safra.
     Poucos pontos, mas é a rede de proteção do produtor. Mantido como
     referência (tipo "pgpm").

Também guardamos os links do indicador diário Cepea/ESALQ (tipo "cepea_link"),
sem copiar número (licença).

Sem rede: se a API do IBGE não responder, o script ainda grava PGPM + Cepea e
avisa no provenance — nunca quebra o pipeline.

Uso:
    python3 correlacao/precos_conab.py [--sem-ibge] [--anos 2010-2023] [--out ...] [--prov ...]
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Macrorregião por UF (PGPM varia por região) ---
REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
UF_REGIAO = {uf: reg for reg, ufs in REGIOES.items() for uf in ufs}

# Código IBGE da UF (nível N3 do SIDRA) -> sigla.
UF_COD = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

# Culturas foco -> código do produto na classificação c81 da tabela 1612 (PAM/IBGE).
CULTURA_C81 = {
    "arroz": "2692",   # Arroz (em casca)
    "feijao": "2702",  # Feijão (em grão)
    "milho": "2711",   # Milho (em grão)
    "soja": "2713",    # Soja (em grão)
    "trigo": "2716",   # Trigo (em grão)
}

# Saca de referência (kg) por cultura — para converter R$/t -> R$/saca.
SACA_KG = {"arroz": 50.0, "feijao": 60.0, "milho": 60.0, "soja": 60.0, "trigo": 60.0}

# --- Preços mínimos OFICIAIS da PGPM (CONAB/MAPA), piso por cultura/safra ---
#
# FONTE: Portaria nº 812 (09/07/2025) — CONAB/Globo Rural.
# CORRIGIDO em 2026-10: a versão anterior tinha 2 erros que mostravam valor
# errado ao produtor:
#   1. feijao usava 181.23 (que é o PRETO) rotulado como "cores/carioca" —
#      o feijão em CORES vale 152.91. Agora são duas entradas distintas.
#   2. milho tinha 19.21, que não existe na tabela oficial (o menor é 38.28).
#      O preço do milho é REGIONAL por natureza — 5 faixas, não valor nacional.
#
# `regioes: None` = escopo NACIONAL (vale para todo o Brasil).
# `regioes: [...]`  = escopo REGIONAL (a UF cai na sua faixa).
PGPM = {
    # Feijão: dois tipos oficiais, ambos nacionais, inalterados na safra.
    "feijao": [
        {"regioes": None, "valor": 152.91, "unidade": "R$/60kg", "safra": "2025/26",
         "obs": "Feijão em CORES (comum/carioca). Piso nacional."},
        {"regioes": None, "valor": 181.23, "unidade": "R$/60kg", "safra": "2025/26",
         "obs": "Feijão PRETO. Piso nacional."},
    ],
    # Milho: 4 faixas macrorregionais (as UFs do NE oeste caem no Nordeste).
    "milho": [
        {"regioes": ["Sul"], "valor": 55.64, "unidade": "R$/60kg", "safra": "2025/26",
         "obs": "Milho em grão — Rio Grande do Sul e Santa Catarina."},
        {"regioes": ["Sudeste"], "valor": 51.03, "unidade": "R$/60kg", "safra": "2025/26",
         "obs": "Milho em grão — Sudeste e Paraná."},
        {"regioes": ["Centro-Oeste", "Norte"], "valor": 38.28, "unidade": "R$/60kg",
         "safra": "2025/26",
         "obs": "Milho em grão — Centro-Oeste e Norte (exceto Tocantins e Pará)."},
        {"regioes": ["Nordeste"], "valor": 63.08, "unidade": "R$/60kg", "safra": "2026/27",
         "obs": "Milho em grão — Nordeste (vigência jun/2026 a mai/2027)."},
    ],
    "soja": [
        {"regioes": None, "valor": 71.04, "unidade": "R$/60kg", "safra": "2025/26",
         "obs": "Soja em grão. Único item com PREÇO REDUZIDO nesta safra (-6,87%)."},
    ],
    "cafe": [{"regioes": None, "valor": 792.53, "unidade": "R$/60kg", "safra": "2026/27",
              "obs": "Café arábica (saca beneficiada de 60 kg)."}],
    "cafe_conilon": [{"regioes": None, "valor": 556.97, "unidade": "R$/60kg", "safra": "2026/27",
                      "obs": "Café conilon/robusta (saca beneficiada de 60 kg)."}],
}

FONTE_PGPM = "CONAB / MAPA — Política de Garantia de Preços Mínimos (PGPM)"
URL_PGPM = "https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/precos-agropecuarios"
URL_PGPM_DET = {
    "feijao": "https://www.gov.br/conab/pt-br/assuntos/noticias/novos-precos-minimos-para-produtos-de-verao-e-regionais-sao-definidos-para-a-safra-2025-2026",
    "milho": "https://www.gov.br/conab/pt-br/assuntos/noticias/novos-precos-minimos-para-produtos-de-verao-e-regionais-sao-definidos-para-a-safra-2025-2026",
    "cafe": "https://www.gov.br/conab/pt-br/assuntos/noticias/precos-minimos-para-a-safra-2026-2027-de-cafe-laranja-sisal-e-trigo-sao-estabelecidos",
    "cafe_conilon": "https://www.gov.br/conab/pt-br/assuntos/noticias/precos-minimos-para-a-safra-2026-2027-de-cafe-laranja-sisal-e-trigo-sao-estabelecidos",
}

# Indicador diário Cepea/ESALQ: SÓ link (licença não permite redistribuir número).
CEPEA_LINKS = {
    "feijao": "https://www.cepea.esalq.usp.br/br/indicador/feijao.aspx",
    "milho": "https://www.cepea.esalq.usp.br/br/indicador/milho.aspx",
    "soja": "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
    "arroz": "https://www.cepea.esalq.usp.br/br/indicador/arroz.aspx",
    "trigo": "https://www.cepea.esalq.usp.br/br/indicador/trigo.aspx",
    "cafe": "https://www.cepea.esalq.usp.br/br/indicador/cafe.aspx",
}
CEPEA_PADRAO = "https://www.cepea.esalq.usp.br/br"

# --- IBGE SIDRA (PAM tabela 1612): preço ao produtor por UF/ano ---
IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados/1612"
FONTE_IBGE = "IBGE — Produção Agrícola Municipal (PAM), tabela 1612 do SIDRA"
URL_IBGE = "https://sidra.ibge.gov.br/tabela/1612"


def _get_json(url, tentativas=3, espera=2.0):
    """GET JSON com retry simples. Devolve objeto ou None (nunca raise)."""
    for i in range(tentativas):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AgroPilot/1.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if i == tentativas - 1:
                print(f"  IBGE falhou ({url[:80]}...): {e}", flush=True)
                return None
            time.sleep(espera)
    return None


def _serie_valor_qtd(cultura, c81, anos_param):
    """Baixa valor (215) e quantidade (214) do IBGE para a cultura, todas UFs.

    Retorna dict {(uf_sigla, ano): {"valor_mil": float, "qtd_t": float}}.
    """
    url = (f"{IBGE_BASE}/periodos/{anos_param}/variaveis/215|214"
           f"?localidades=N3[all]&classificacao=81[{c81}]")
    data = _get_json(url)
    if not data:
        return {}
    acc = {}
    for bloco in data:
        var = bloco.get("id")  # "215" ou "214"
        chave = "valor_mil" if var == "215" else "qtd_t"
        for res in bloco.get("resultados", []):
            for serie in res.get("series", []):
                cod_uf = (serie.get("localidade") or {}).get("id")
                uf = UF_COD.get(str(cod_uf))
                if not uf:
                    continue
                for ano, val in (serie.get("serie") or {}).items():
                    try:
                        v = float(val)
                    except (TypeError, ValueError):
                        continue
                    if v <= 0:
                        continue
                    acc.setdefault((uf, ano), {})[chave] = v
    return acc


def _docs_ibge(anos_param):
    """Monta os docs de preço histórico ao produtor (R$/saca) por cultura/UF/ano."""
    docs = []
    anos_vistos = set()
    for cultura, c81 in CULTURA_C81.items():
        print(f"  IBGE {cultura}...", flush=True)
        bruto = _serie_valor_qtd(cultura, c81, anos_param)
        saca = SACA_KG.get(cultura, 60.0)
        for (uf, ano), d in bruto.items():
            valor_mil = d.get("valor_mil")
            qtd_t = d.get("qtd_t")
            if not valor_mil or not qtd_t:
                continue
            # valor em MIL reais; preço R$/t = (valor_mil*1000)/qtd_t
            preco_t = (valor_mil * 1000.0) / qtd_t
            preco_saca = round(preco_t * (saca / 1000.0), 2)
            if preco_saca <= 0:
                continue
            anos_vistos.add(ano)
            docs.append({
                "cultura_canonica": cultura,
                "tipo": "serie_produtor",
                "escopo": "uf_ano",
                "uf": uf,
                "regiao": UF_REGIAO.get(uf),
                "ano": int(ano),
                "valor": preco_saca,
                "valor_ton": round(preco_t, 2),
                "unidade": f"R$/{int(saca)}kg",
                "quantidade_t": round(qtd_t, 1),
                "safra": None,
                "obs": "Preço médio recebido pelo produtor (valor da produção ÷ quantidade).",
                "fonte_nome": FONTE_IBGE,
                "fonte_url": URL_IBGE,
                "cepea_url": CEPEA_LINKS.get(cultura, CEPEA_PADRAO),
            })
    return docs, sorted(anos_vistos)


def _docs_pgpm():
    docs = []
    for cultura, faixas in PGPM.items():
        for faixa in faixas:
            escopos = ([{"escopo": "nacional", "regiao": None}] if not faixa.get("regioes")
                       else [{"escopo": "regiao", "regiao": r} for r in faixa["regioes"]])
            for esc in escopos:
                docs.append({
                    "cultura_canonica": cultura, "tipo": "pgpm",
                    "escopo": esc["escopo"], "uf": None, "regiao": esc["regiao"],
                    "ano": None, "valor": round(float(faixa["valor"]), 2),
                    "unidade": faixa.get("unidade", "R$/60kg"),
                    "safra": faixa.get("safra"), "obs": faixa.get("obs"),
                    "fonte_nome": FONTE_PGPM,
                    "fonte_url": URL_PGPM_DET.get(cultura, URL_PGPM),
                    "cepea_url": CEPEA_LINKS.get(cultura, CEPEA_PADRAO),
                })
    return docs


def _docs_cepea():
    docs = []
    culturas_pgpm = set(PGPM)
    for cultura, url in CEPEA_LINKS.items():
        if cultura in culturas_pgpm:
            continue
        docs.append({
            "cultura_canonica": cultura, "tipo": "cepea_link",
            "escopo": "nacional", "uf": None, "regiao": None, "ano": None,
            "valor": None, "unidade": "indicador diário", "safra": None,
            "obs": "Indicador diário Cepea/ESALQ — abrir no site oficial.",
            "fonte_nome": "Cepea/ESALQ — indicador diário",
            "fonte_url": url, "cepea_url": url,
        })
    return docs


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="correlacao/output/precos_conab.jsonl")
    ap.add_argument("--prov", default="correlacao/output/provenance/precos_conab.json")
    ap.add_argument("--anos", default=f"2000-{date.today().year}",
                    help="intervalo de anos do IBGE, ex: 2010-2025 (default 2000-ano atual)")
    ap.add_argument("--sem-ibge", action="store_true",
                    help="pula o download do IBGE (só PGPM + Cepea)")
    args = ap.parse_args(argv)

    # intervalo "2000-2023" -> "2000|2001|...|2023" para o SIDRA
    try:
        ini, fim = (int(x) for x in args.anos.split("-"))
        anos_param = "|".join(str(a) for a in range(ini, fim + 1))
    except Exception:
        anos_param = "all"

    docs_pgpm = _docs_pgpm()
    docs_cepea = _docs_cepea()
    docs_ibge, anos_ibge = ([], [])
    ibge_ok = False
    if not args.sem_ibge:
        print("baixando série histórica do IBGE (PAM 1612)...", flush=True)
        docs_ibge, anos_ibge = _docs_ibge(anos_param)
        ibge_ok = len(docs_ibge) > 0

    docs = docs_ibge + docs_pgpm + docs_cepea

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")

    culturas = sorted({d["cultura_canonica"] for d in docs})
    com_valor = sum(1 for d in docs if d.get("valor") is not None)
    por_tipo = {}
    for d in docs:
        por_tipo[d["tipo"]] = por_tipo.get(d["tipo"], 0) + 1

    os.makedirs(os.path.dirname(args.prov) or ".", exist_ok=True)
    with open(args.prov, "w", encoding="utf-8") as fh:
        json.dump({
            "_id": "precos_conab",
            "name": "Preços agrícolas — IBGE/PAM (série ao produtor) + CONAB/PGPM (piso) + Cepea (link)",
            "sources": [
                {"name": FONTE_IBGE, "url": URL_IBGE,
                 "license": "IBGE — dados públicos, uso livre com citação"},
                {"name": FONTE_PGPM, "url": URL_PGPM,
                 "license": "Conteúdo público CONAB — reprodução autorizada citando a fonte"},
                {"name": "Cepea/ESALQ — indicador diário", "url": CEPEA_PADRAO,
                 "license": "Somente link; número não é redistribuído (licença Cepea)"},
            ],
            "extracted_at": date.today().isoformat(),
            "reference_period": f"IBGE {anos_ibge[0] if anos_ibge else '—'}–{anos_ibge[-1] if anos_ibge else '—'}; PGPM safra 2025/26 e 2026/27",
            "transformations": [
                "preço ao produtor = valor da produção (R$) ÷ quantidade (t), convertido para R$/saca",
                "série anual por cultura e UF (IBGE PAM tabela 1612)",
                "piso PGPM por cultura/safra (CONAB/MAPA)",
                "Cepea só como link (sem redistribuir número)",
            ],
            "limitations": [
                "Preço IBGE é MÉDIA anual do estado (não é cotação diária).",
                "PGPM é piso oficial, não preço de mercado.",
                "Cepea nunca traz número embutido (restrição de licença).",
            ],
            "stats": {
                "docs": len(docs), "com_valor": com_valor,
                "por_tipo": por_tipo, "culturas": culturas,
                "anos_ibge": anos_ibge, "ibge_ok": ibge_ok,
            },
        }, fh, ensure_ascii=False, indent=2)

    print(f"docs={len(docs)} (serie_ibge={len(docs_ibge)}, pgpm={len(docs_pgpm)}, "
          f"cepea={len(docs_cepea)}) anos_ibge={anos_ibge[:1]}..{anos_ibge[-1:]} culturas={culturas}")
    if not ibge_ok and not args.sem_ibge:
        print("AVISO: IBGE não respondeu; gravei só PGPM + Cepea. Rode de novo com rede.")


if __name__ == "__main__":
    main(sys.argv[1:])
