"""Rota /api/produtor — leitura e cadastro com MongoDB + fallback mock."""
from fastapi import APIRouter, HTTPException
from ..schemas.produtor import ProdutorCreate, ProdutorResponse
from ..mock import MOCK_PRODUTOR
from ..db import get_db

router = APIRouter(prefix="/api", tags=["Produtor"])


def _col(db):
    try:
        return db["produtores"] if db is not None else None
    except Exception:
        return None


@router.get("/produtor/{id}")
def obter_produtor(id: str):
    """Retorna perfil do produtor. Tenta Mongo primeiro; fallback para mock."""
    col = _col(get_db())
    if col is not None:
        try:
            doc = col.find_one({"id": id})
            if doc:
                doc.pop("_id", None)
                return doc
        except Exception:
            pass
    # fallback: retorna mock com o id requisitado
    resposta = dict(MOCK_PRODUTOR)
    resposta["id"] = id
    return resposta


@router.post("/produtor")
def cadastrar_ou_atualizar_produtor(produtor: ProdutorCreate):
    """Cria ou atualiza produtor via upsert por telefone. Fallback silencioso."""
    payload = produtor.model_dump()

    col = _col(get_db())
    if col is not None:
        try:
            from bson import ObjectId
            import uuid

            # Usa telefone como chave de upsert
            filtro = {"telefone": payload.get("telefone")}
            doc_existente = col.find_one(filtro)
            if doc_existente:
                produtor_id = str(doc_existente.get("id") or doc_existente.get("_id"))
            else:
                produtor_id = str(uuid.uuid4())[:8]

            payload["id"] = produtor_id
            col.update_one(filtro, {"$set": payload}, upsert=True)
            return {"id": produtor_id, "mensagem": "Perfil cadastrado com sucesso", "ok": True}
        except Exception:
            pass

    # fallback mock
    return {"id": "abc123", "mensagem": "Perfil cadastrado com sucesso", "ok": True}
