"""Dados mockados para o backend, permitindo desenvolvimento e testes antes da integração com banco de dados real."""

MOCK_PRODUTOR = {
    "id": "abc123",
    "nome": "Antônio",
    "telefone": "+5519999999999",
    "codigo_ibge": "3503307",
    "municipio": "Araraquara",
    "uf": "SP",
    "lavouras": [
        {"cultura": "uva", "area_ha": 5.0, "solo": 1, "irrigacao": False},
        {"cultura": "tomate", "area_ha": 3.0, "solo": 1, "irrigacao": False},
    ],
    "preferencias": {
        "notificacoes": True,
        "horario": "06:00",
    },
    "criado_em": "2026-10-02T10:00:00Z",
}

MOCK_CHAT_PRAGA = {
    "resposta": "Antônio, para míldio em uva, os produtos registrados são:\n• Produto X (classe II)\n• Produto Z (ORGÂNICO)",
    "intencao": "PRAGA",
    "fonte": "Agrofit/MAPA",
    "data_extracao": "2026-10-02",
    "dados": {
        "cultura": "uva",
        "praga": "mildio",
        "produtos": [
            {"nome": "Produto X", "classe": "II", "organico": False},
            {"nome": "Produto Z", "classe": "IV", "organico": True},
        ],
    },
}

MOCK_CHAT_PLANEJAMENTO = {
    "resposta": "Antônio, para feijão em Araraquara (solo 1, sequeiro):\n• Melhor janela: dec 29-32 (risco 20%)\n• Cultivares: BRS Estilo, BRS Pérola\n• Semente local: BRS Estilo (30 km)",
    "intencao": "PLANEJAMENTO",
    "fonte": "ZARC 2025/26 + SIGEF",
    "data_extracao": "2026-10-02",
    "dados": {
        "cultura": "feijao",
        "janelas": [{"dec": 29, "risco": 20}, {"dec": 30, "risco": 20}],
        "cultivares": ["BRS Estilo", "BRS Pérola"],
    },
}

MOCK_CHAT_CLIMA = {
    "resposta": "Previsão para Araraquara/SP: Risco moderado de queda brusca de temperatura nas próximas 72h. Monitore suas áreas de uva mais baixas.",
    "intencao": "CLIMA",
    "fonte": "INMET + ZARC",
    "data_extracao": "2026-10-02",
    "dados": {
        "municipio": "Araraquara",
        "uf": "SP",
        "alerta_geada": True,
        "previsao_dias": 3,
    },
}

MOCK_CHAT_SAUDACAO = {
    "resposta": "Olá, Antônio! Como posso ajudar você hoje na sua lavoura?",
    "intencao": "SAUDACAO",
    "fonte": "Assistente Agro Familiar",
    "data_extracao": "2026-10-02",
    "dados": {},
}

MOCK_ALERTA_GEADA = {
    "id": "alerta1",
    "tipo": "geada",
    "severidade": "alta",
    "mensagem": "Geada prevista para quinta (3 dias). Sua uva está em risco.",
    "fonte": "ZARC + INMET",
    "data_extracao": "2026-10-02",
    "enviado_em": "2026-10-02T06:00:00Z",
    "lido": False,
}
