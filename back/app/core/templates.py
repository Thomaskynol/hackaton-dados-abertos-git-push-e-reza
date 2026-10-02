"""Gera templates de respostas formatadas para a linguagem do produtor da agricultura familiar."""
from typing import Dict, Any


def montar_resposta_praga(produtor_nome: str, cultura: str, praga: str) -> Dict[str, Any]:
    return {
        "resposta": f"{produtor_nome}, para {praga} em {cultura}, os produtos registrados no MAPA são:\n• Produto X (classe II - uso com receituário)\n• Produto Z (ORGÂNICO certificado)",
        "dados": {
            "cultura": cultura,
            "praga": praga,
            "produtos": [
                {"nome": "Produto X", "classe": "II", "organico": False},
                {"nome": "Produto Z", "classe": "IV", "organico": True},
            ],
        },
    }


def montar_resposta_planejamento(produtor_nome: str, cultura: str, municipio: str) -> Dict[str, Any]:
    return {
        "resposta": f"{produtor_nome}, para {cultura} em {municipio} (solo 1, sequeiro):\n• Melhor janela de plantio: decêndio 29 a 32 (risco climático 20%)\n• Cultivares indicadas: BRS Estilo, BRS Pérola\n• Produtor de sementes próximo: BRS Estilo (a 30 km)",
        "dados": {
            "cultura": cultura,
            "janelas": [{"dec": 29, "risco": 20}, {"dec": 30, "risco": 20}],
            "cultivares": ["BRS Estilo", "BRS Pérola"],
        },
    }
