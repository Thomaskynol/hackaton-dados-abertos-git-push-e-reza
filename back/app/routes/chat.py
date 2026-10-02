from typing import Union
from fastapi import APIRouter
from ..schemas.chat import ChatRequest, ChatResponseSuccess, ChatResponseError
from ..schemas.intencoes import Intencao
from ..core.router_intencao import classificar_intencao
from ..mock import (
    MOCK_CHAT_PRAGA,
    MOCK_CHAT_PLANEJAMENTO,
    MOCK_CHAT_CLIMA,
    MOCK_CHAT_SAUDACAO,
)

router = APIRouter(prefix="/api", tags=["Chat"])


@router.post(
    "/chat",
    response_model=Union[ChatResponseSuccess, ChatResponseError],
    summary="Processar mensagem de chat",
    description="Classifica a intenção do produtor e retorna resposta com dados estruturados e fontes oficiais.",
)
def processar_chat(req: ChatRequest):

    intencao = classificar_intencao(req.mensagem)

    if intencao == Intencao.PRAGA:
        return MOCK_CHAT_PRAGA
    elif intencao == Intencao.PLANEJAMENTO:
        return MOCK_CHAT_PLANEJAMENTO
    elif intencao == Intencao.CLIMA:
        return MOCK_CHAT_CLIMA
    elif intencao == Intencao.SAUDACAO:
        return MOCK_CHAT_SAUDACAO
    elif intencao == Intencao.PERFIL:
        return {
            "resposta": "Antônio, seu cadastro conta com 5 ha de uva e 3 ha de tomate em Araraquara/SP.",
            "intencao": "PERFIL",
            "fonte": "Cadastro Produtor Familiar",
            "data_extracao": "2026-10-02",
            "dados": {"produtor_id": req.produtor_id},
        }
    elif intencao == Intencao.VENDA:
        return {
            "resposta": "Para comercialização da sua safra, há chamada pública do PAA aberta em Araraquara até o fim do mês.",
            "intencao": "VENDA",
            "fonte": "CONAB / PAA Dados Abertos",
            "data_extracao": "2026-10-02",
            "dados": {},
        }
    else:
        return {
            "erro": "NAO_ENTENDI",
            "mensagem": "Não consegui entender. Pode reformular?",
            "sugestoes": [
                "Quando planto feijão?",
                "Minha uva está com míldio",
                "Vai gear?",
            ],
        }
