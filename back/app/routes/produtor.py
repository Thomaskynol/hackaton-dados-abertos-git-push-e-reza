from fastapi import APIRouter, HTTPException
from ..schemas.produtor import ProdutorCreate, ProdutorResponse
from ..mock import MOCK_PRODUTOR

router = APIRouter(prefix="/api", tags=["Produtor"])


@router.get("/produtor/{id}")
def obter_produtor(id: str):
    if id != MOCK_PRODUTOR["id"] and id != "antonio":
        # Retorna o perfil mockado com o id requisitado para facilitar testes do front
        resposta = dict(MOCK_PRODUTOR)
        resposta["id"] = id
        return resposta
    return MOCK_PRODUTOR


@router.post("/produtor")
def cadastrar_ou_atualizar_produtor(produtor: ProdutorCreate):
    return {
        "id": "abc123",
        "mensagem": "Perfil cadastrado com sucesso",
        "ok": True,
    }
