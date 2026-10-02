import re
from ..schemas.intencoes import Intencao


def classificar_intencao(mensagem: str) -> Intencao:
    """Classifica a intenção da mensagem do usuário com base em regras e palavras-chave."""
    msg = mensagem.lower().strip()

    # Saudação
    if re.search(r"\b(oi|ol[aá]|bom dia|boa tarde|boa noite|opa|fala)\b", msg):
        return Intencao.SAUDACAO

    # Praga / Doença
    if any(palavra in msg for palavra in ["míldio", "mildio", "praga", "doen[cç]a", "lagarta", "fungo", "inseto", "veneno", "defensivo", "remedio", "remédio"]):
        return Intencao.PRAGA

    # Planejamento / Plantio
    if any(palavra in msg for palavra in ["plantar", "plantio", "quando planto", "semente", "cultivar", "janela", "zarc", "colher", "colheita"]):
        return Intencao.PLANEJAMENTO

    # Clima / Geada / Chuva
    if any(palavra in msg for palavra in ["gear", "geada", "clima", "tempo", "chover", "chuva", "temperatura", "frio", "seca"]):
        return Intencao.CLIMA

    # Venda / Mercado / PAA / PNAE
    if any(palavra in msg for palavra in ["vender", "venda", "preço", "cotacao", "cotação", "paa", "pnae", "comercializar"]):
        return Intencao.VENDA

    # Perfil / Propriedade
    if any(palavra in msg for palavra in ["meu perfil", "minha terra", "minha propriedade", "minhas lavouras", "meu cadastro"]):
        return Intencao.PERFIL

    return Intencao.NAO_ENTENDI
