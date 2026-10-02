"""Consultas reais ao Mongo para PLANEJAMENTO (zarc) e PRAGA (agrofit).

Ambas retornam None quando sem dados — o chamador cai no MOCK.
"""
import re

# alias mínimo medido (míldio da uva = Plasmopara viticola); ampliar quando nova cultura pedir
PRAGA_ALIAS = {
    "mildio": "plasmopara",
    "míldio": "plasmopara",
    "mildew": "plasmopara",
    "oidio": "oidium",
    "oídio": "oidium",
}

CLASSE_ROMANO = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}

CULTURAS = ["feijao", "feijão", "milho", "soja", "arroz", "trigo",
            "uva", "tomate", "cafe", "café", "algodao", "amendoim", "sorgo"]


def extrair_cultura(mensagem):
    msg = mensagem.lower()
    for c in CULTURAS:
        if c in msg:
            return "feijao" if c == "feijão" else "cafe" if c == "café" else c
    return None


def extrair_alvo(mensagem):
    msg = mensagem.lower()
    for nome in list(PRAGA_ALIAS) + ["lagarta", "ferrugem", "pulg", "broca", "mosca", "fungo"]:
        if nome in msg:
            return nome
    return None


def buscar_janelas(db, cultura, ibge, solo=None, irrigacao=None, limite=3):
    q = {"cod_ibge": ibge, "cultura_canonica": cultura}
    if solo:
        q["solo_canonico"] = solo
    if irrigacao is not None:
        q["manejo_canonico"] = "irrigado" if irrigacao else "sequeiro"
    docs = list(db.zarc.find(q, {"_id": 0}).sort("risco_min", 1).limit(limite))
    if not docs:
        # retry sem solo/manejo antes de desistir
        docs = list(db.zarc.find(
            {"cod_ibge": ibge, "cultura_canonica": cultura}, {"_id": 0}
        ).sort("risco_min", 1).limit(limite))
    if not docs:
        return None
    return docs


def buscar_produtos(db, cultura, alvo=None, limite=5):
    base = list(db.agrofit.find({"cultura_canonica": cultura}, {"_id": 0}).limit(limite * 10))
    if not base:
        return None
    if alvo:
        padrao = str(PRAGA_ALIAS.get(alvo.lower(), alvo))
        rx = re.compile(re.escape(padrao), re.IGNORECASE)
        match = [d for d in base if rx.search(d.get("praga_nome_cientifico") or "")]
        if match:
            return match[:limite]
    return base[:limite]


def produto_resumo(doc):
    classe = CLASSE_ROMANO.get(doc.get("classe_toxicologica"), "—")
    return {
        "nome": doc.get("marca_comercial") or doc.get("ingrediente_ativo") or "?",
        "classe": classe,
        "organico": doc.get("organicos") == "S",
    }
