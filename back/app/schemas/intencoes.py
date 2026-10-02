from enum import Enum


class Intencao(str, Enum):
    PLANEJAMENTO = "PLANEJAMENTO"  # "quando planto X?"
    PRAGA = "PRAGA"                # "minha planta está com X"
    CLIMA = "CLIMA"                # "vai gear?"
    VENDA = "VENDA"                # "como vendo?"
    PERFIL = "PERFIL"              # "meu perfil"
    SAUDACAO = "SAUDACAO"          # "oi"
    NAO_ENTENDI = "NAO_ENTENDI"    # fallback
