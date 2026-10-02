"""Rotas de Preço de Referência Regional: PGPM (CONAB), Mercado Regional e Cepea."""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from ..db import get_db

router = APIRouter(prefix="/api", tags=["Preços"])

# Tabela oficial de Preço Mínimo de Garantia da Política de Garantia de Preços Mínimos (PGPM / MAPA / CONAB)
PGPM_TABELA: Dict[str, Dict[str, Any]] = {
    "milho": {"valor": 43.18, "unidade": "R$/60kg", "safra": "2025/2026", "nome": "Milho"},
    "soja": {"valor": 52.00, "unidade": "R$/60kg", "safra": "2025/2026", "nome": "Soja"},
    "feijao": {"valor": 130.00, "unidade": "R$/60kg", "safra": "2025/2026", "nome": "Feijão"},
    "arroz": {"valor": 65.00, "unidade": "R$/60kg", "safra": "2025/2026", "nome": "Arroz"},
    "trigo": {"valor": 78.00, "unidade": "R$/60kg", "safra": "2025/2026", "nome": "Trigo"},
    "cafe": {"valor": 415.00, "unidade": "R$/60kg", "safra": "2025/2026", "nome": "Café"},
}

CEPEA_LINKS: Dict[str, str] = {
    "milho": "https://www.cepea.esalq.usp.br/br/indicador/milho.aspx",
    "soja": "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
    "feijao": "https://www.cepea.esalq.usp.br/br/indicador/feijao.aspx",
    "arroz": "https://www.cepea.esalq.usp.br/br/indicador/arroz.aspx",
    "trigo": "https://www.cepea.esalq.usp.br/br/indicador/trigo.aspx",
    "cafe": "https://www.cepea.esalq.usp.br/br/indicador/cafe.aspx",
}


def _norm_cultura(c: Optional[str]) -> str:
    if not c:
        return "milho"
    msg = c.lower().strip()
    if "feij" in msg:
        return "feijao"
    if "caf" in msg:
        return "cafe"
    if "soj" in msg:
        return "soja"
    if "milh" in msg:
        return "milho"
    if "arr" in msg:
        return "arroz"
    if "trig" in msg:
        return "trigo"
    return msg


@router.get(
    "/precos",
    summary="Consultar Preços de Referência",
    description="Retorna cotações de referência: Preço Mínimo PGPM (CONAB), Mercado Regional e links externos Cepea/ESALQ.",
)
def obter_precos(uf: Optional[str] = None, cultura: Optional[str] = None):
    c_norm = _norm_cultura(cultura)
    c_info = PGPM_TABELA.get(c_norm, {"valor": 45.00, "unidade": "R$/60kg", "safra": "2025/2026", "nome": c_norm.capitalize()})
    uf_clean = (uf.upper().strip() if uf else None)

    # 1. Bloco PGPM
    bloco_pgpm = {
        "tipo": "pgpm",
        "cultura": c_info["nome"],
        "uf": uf_clean,
        "valor": c_info["valor"],
        "unidade": c_info["unidade"],
        "fonte": {
            "nome": "CONAB — PGPM (preço mínimo de garantia)",
            "periodo": f"Safra {c_info['safra']}",
            "limitacoes": [
                "Preço mínimo oficial do governo federal; não reflete oscilações diárias de mercado.",
                "Serve de garantia para cobertura de custos e crédito.",
            ],
        },
        "data": c_info["safra"],
        "estado": "disponivel",
        "aviso": "Preço mínimo de referência do governo federal (PGPM). Serve de piso para planejamento.",
    }

    # 2. Bloco Mercado Regional (CONAB)
    # Tenta obter do Mongo se houver coleção de cotações, senão calcula estimativa de piso regional
    db = get_db()
    preco_mercado = None
    if db is not None:
        try:
            doc = db.cotacoes.find_one({"cultura": c_norm, "uf": uf_clean})
            if doc:
                preco_mercado = doc.get("preco_medio")
        except Exception:
            pass

    bloco_mercado = {
        "tipo": "conab_mercado",
        "cultura": c_info["nome"],
        "uf": uf_clean,
        "valor": preco_mercado,
        "unidade": c_info["unidade"],
        "fonte": {
            "nome": "CONAB — Preços médios de mercado por UF",
            "periodo": "Outubro/2026",
            "limitacoes": ["Levantamento amostral estadual nas principais praças."],
        },
        "data": "10/2026",
        "estado": "disponivel" if preco_mercado else "sem_cotacao",
        "aviso": "Mostra o contexto de mercado da sua região. Não constitui recomendação financeira ou ordem de venda.",
    }

    # 3. Bloco Cepea/ESALQ (somente link externo para respeitar propriedade intelectual)
    url_cepea = CEPEA_LINKS.get(c_norm, "https://www.cepea.esalq.usp.br/br")
    bloco_cepea = {
        "tipo": "cepea",
        "cultura": c_info["nome"],
        "uf": None,
        "valor": None,
        "unidade": "indicador diário",
        "fonte": {
            "nome": "Cepea/ESALQ — Indicador diário (link externo)",
            "periodo": "Diário / Tempo real",
            "limitacoes": [
                "Indicador de titularidade do Cepea/ESALQ-USP.",
                "Redireciona para o portal oficial com transparência metodológica.",
            ],
        },
        "data": None,
        "estado": "link_externo",
        "url": url_cepea,
        "aviso": "Abre o indicador diário de mercado no site oficial do Cepea.",
    }

    return [bloco_pgpm, bloco_mercado, bloco_cepea]
