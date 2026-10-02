from fastapi import APIRouter, HTTPException
from ..schemas.produtor import ProdutorCreate, ProdutorResponse, ProdutorCreateResponse
from ..mock import MOCK_PRODUTOR
from ..db import get_db
import uuid

router = APIRouter(prefix="/api", tags=["Produtor"])


@router.get(
    "/produtor/{id}",
    response_model=ProdutorResponse,
    summary="Obter perfil do produtor",
    description="Retorna os dados cadastrais, lavouras e preferências do produtor rural.",
)
def obter_produtor(id: str):
    # Tenta buscar no MongoDB por id ou telefone
    db = get_db()
    if db is not None:
        clean_digits = "".join(filter(str.isdigit, id))
        filtros = [{"id": id}, {"telefone": id}]
        if clean_digits:
            filtros.extend([
                {"telefone": clean_digits},
                {"telefone": f"+{clean_digits}"},
                {"telefone": f"+55{clean_digits}"},
                {"telefone": {"$regex": clean_digits}},
            ])
        doc = db.produtores.find_one({"$or": filtros}, {"_id": 0})
        if doc:
            return doc

    # Fallback mock
    if id != MOCK_PRODUTOR["id"] and id != "antonio":
        resposta = dict(MOCK_PRODUTOR)
        resposta["id"] = id
        return resposta
    return MOCK_PRODUTOR


@router.post(
    "/produtor",
    response_model=ProdutorCreateResponse,
    summary="Cadastrar ou atualizar perfil",
    description="Cria ou atualiza as características do produtor e suas lavouras.",
)
def cadastrar_ou_atualizar_produtor(produtor: ProdutorCreate):
    produtor_id = str(uuid.uuid4())[:8]

    # Tenta persistir no MongoDB
    db = get_db()
    if db is not None:
        doc = produtor.model_dump()
        doc["id"] = produtor_id
        doc["criado_em"] = "2026-10-02T10:00:00Z"
        db.produtores.update_one({"telefone": doc["telefone"]}, {"$set": doc}, upsert=True)

    return {
        "id": produtor_id,
        "mensagem": "Perfil cadastrado com sucesso",
        "ok": True,
    }

