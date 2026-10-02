from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from .intencoes import Intencao


class ChatRequest(BaseModel):
    produtor_id: str
    mensagem: str
    sessao_id: Optional[str] = None


class ChatResponseSuccess(BaseModel):
    resposta: str
    intencao: Intencao
    fonte: str
    data_extracao: str
    dados: Optional[Dict[str, Any]] = None


class ChatResponseError(BaseModel):
    erro: str = "NAO_ENTENDI"
    mensagem: str = "Não consegui entender. Pode reformular?"
    sugestoes: List[str] = [
        "Quando planto feijão?",
        "Minha uva está com míldio",
        "Vai gear?",
    ]
