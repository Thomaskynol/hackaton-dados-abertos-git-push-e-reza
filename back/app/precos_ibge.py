"""Fetcher ao vivo da série de preço ao produtor (IBGE / PAM, tabela 1612 SIDRA).

Mantém a previsão SEMPRE com o dado mais recente que o IBGE publicou: o backend
busca a série direto da API oficial, converte valor da produção ÷ quantidade em
R$/saca, e devolve os pontos por cultura e UF. É o mesmo cálculo do ingestor
offline (correlacao/precos_conab.py), mas rodando sob demanda no servidor.

Nunca levanta exceção: timeout curto, retry leve; se a rede falhar, devolve
lista vazia e o chamador segue com o que já tem em cache (Mongo/arquivo).
"""
import gzip
import json
import logging
import os
import time
import urllib.request

log = logging.getLogger(__name__)

IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3/agregados/1612"
FONTE_IBGE = "IBGE — Produção Agrícola Municipal (PAM), tabela 1612 do SIDRA"
URL_IBGE = "https://sidra.ibge.gov.br/tabela/1612"

# código IBGE da UF (nível N3) -> sigla
UF_COD = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL",
    "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
_REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
UF_REGIAO = {uf: reg for reg, ufs in _REGIOES.items() for uf in ufs}

# cultura canônica -> código do produto na classificação c81 da PAM
CULTURA_C81 = {
    "arroz": "2692", "feijao": "2702", "milho": "2711", "soja": "2713", "trigo": "2716",
}
SACA_KG = {"arroz": 50.0, "feijao": 60.0, "milho": 60.0, "soja": 60.0, "trigo": 60.0}

CEPEA_LINKS = {
    "feijao": "https://www.cepea.esalq.usp.br/br/indicador/feijao.aspx",
    "milho": "https://www.cepea.esalq.usp.br/br/indicador/milho.aspx",
    "soja": "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
    "arroz": "https://www.cepea.esalq.usp.br/br/indicador/arroz.aspx",
    "trigo": "https://www.cepea.esalq.usp.br/br/indicador/trigo.aspx",
}
CEPEA_PADRAO = "https://www.cepea.esalq.usp.br/br"


def cultura_tem_ibge(cultura_canonica):
    return cultura_canonica in CULTURA_C81


def _get_json(url, tentativas=2, espera=1.5, timeout=12):
    for i in range(tentativas):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "AgroPilot/1.0",
                              "Accept": "application/json",
                              "Accept-Encoding": "gzip, identity"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except Exception as e:
            if i == tentativas - 1:
                log.info("IBGE indisponível (%s): %r", url[:70], e)
                return None
            time.sleep(espera)
    return None


def ultimo_ano_disponivel(timeout=10):
    """Último ano publicado na tabela 1612 (ex: 2025). None se a API falhar."""
    data = _get_json(f"{IBGE_BASE}/periodos", timeout=timeout)
    if not data:
        return None
    anos = []
    for p in data:
        try:
            anos.append(int(p.get("id")))
        except (TypeError, ValueError):
            continue
    return max(anos) if anos else None


def buscar_serie(cultura_canonica, anos=None, timeout=15):
    """Série de preço ao produtor (R$/saca) por UF/ano para uma cultura.

    `anos` é lista de inteiros a buscar; None = todos os anos disponíveis.
    Retorna lista de docs no mesmo formato do dataset precos_conab
    (tipo "serie_produtor"). Lista vazia se a cultura não tem PAM ou a API falha.
    """
    cult = (cultura_canonica or "").strip().lower()
    c81 = CULTURA_C81.get(cult)
    if not c81:
        return []
    periodo = "|".join(str(a) for a in anos) if anos else "all"
    url = (f"{IBGE_BASE}/periodos/{periodo}/variaveis/215|214"
           f"?localidades=N3[all]&classificacao=81[{c81}]")
    data = _get_json(url, timeout=timeout)
    if not data:
        return []

    acc = {}  # (uf, ano) -> {"valor_mil":, "qtd_t":}
    for bloco in data:
        chave = "valor_mil" if bloco.get("id") == "215" else "qtd_t"
        for res in bloco.get("resultados", []):
            for serie in res.get("series", []):
                uf = UF_COD.get(str((serie.get("localidade") or {}).get("id")))
                if not uf:
                    continue
                for ano, val in (serie.get("serie") or {}).items():
                    try:
                        v = float(val)
                    except (TypeError, ValueError):
                        continue
                    if v > 0:
                        acc.setdefault((uf, ano), {})[chave] = v

    saca = SACA_KG.get(cult, 60.0)
    cepea = CEPEA_LINKS.get(cult, CEPEA_PADRAO)
    docs = []
    for (uf, ano), d in acc.items():
        vm, qt = d.get("valor_mil"), d.get("qtd_t")
        if not vm or not qt:
            continue
        preco_t = (vm * 1000.0) / qt
        preco_saca = round(preco_t * (saca / 1000.0), 2)
        if preco_saca <= 0:
            continue
        docs.append({
            "cultura_canonica": cult, "tipo": "serie_produtor", "escopo": "uf_ano",
            "uf": uf, "regiao": UF_REGIAO.get(uf), "ano": int(ano),
            "valor": preco_saca, "valor_ton": round(preco_t, 2),
            "unidade": f"R$/{int(saca)}kg", "quantidade_t": round(qt, 1),
            "safra": None,
            "obs": "Preço médio recebido pelo produtor (valor da produção ÷ quantidade).",
            "fonte_nome": FONTE_IBGE, "fonte_url": URL_IBGE, "cepea_url": cepea,
        })
    return docs
