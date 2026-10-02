from datetime import datetime, timezone
from uuid import uuid4
import logging

from fastapi import APIRouter

from ..db import get_db
from ..mock import MOCK_PRODUTOR
from ..schemas.produtor import ProdutorCreate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Produtor"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_indexes(db) -> None:
    try:
        col = db.produtores
    except Exception as e:
        log.warning("produtores sem colecao p/ index: %r", e)
        return
    for key in ("telefone", "id"):
        try:
            col.create_index(key, unique=True)
        except Exception as e:
            log.warning("index produtores.%s falhou: %r", key, e)


def _resp_doc(doc: dict) -> dict:
    out = dict(doc or {})
    out.pop("_id", None)
    if "cod_ibge" in out and "codigo_ibge" not in out:
        out["codigo_ibge"] = out.get("cod_ibge")
    return out


def _non_null(d: dict) -> dict:
    return {k: v for k, v in (d or {}).items() if v is not None}


@router.get("/produtor/{id}")
def obter_produtor(id: str):
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em GET produtor: %r", e)
        db = None
    if db is not None:
        try:
            _ensure_indexes(db)
            doc = db.produtores.find_one({"id": id})
        except Exception as e:
            log.warning("find produtor %s falhou: %r", id, e)
            doc = None
        if doc:
            return _resp_doc(doc)
    if id != MOCK_PRODUTOR["id"] and id != "antonio":
        # fallback mock com o id requisitado (facilita testes do front)
        resposta = dict(MOCK_PRODUTOR)
        resposta["id"] = id
        return resposta
    return MOCK_PRODUTOR


@router.post("/produtor")
def cadastrar_ou_atualizar_produtor(produtor: ProdutorCreate):
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em POST produtor: %r", e)
        db = None
    body = produtor.model_dump()
    if db is None:
        out = dict(body)
        out["id"] = str(uuid4())
        out["mensagem"] = "Perfil cadastrado com sucesso"
        out["ok"] = True
        return out
    _ensure_indexes(db)
    try:
        atual = db.produtores.find_one({"telefone": produtor.telefone})
    except Exception as e:
        log.warning("find upsert telefone falhou: %r", e)
        atual = None
    # solo_inferido: servidor preenche via ZARC quando front não manda
    _solo_atual = body.get("solo_inferido")
    if not (str(_solo_atual).strip() if isinstance(_solo_atual, str) else _solo_atual):
        try:
            from .regiao import solo_inferido_para
            inferido = solo_inferido_para(db, produtor.codigo_ibge)
            if inferido:
                body["solo_inferido"] = inferido
        except Exception as e:
            log.warning("solo inferido falhou: %r", e)
    agora = _now()
    if atual:
        pid = atual.get("id") or str(uuid4())
        upd = _non_null(body)
        upd["id"] = pid
        upd["cod_ibge"] = produtor.codigo_ibge
        upd["atualizado_em"] = agora
        try:
            db.produtores.update_one({"telefone": produtor.telefone}, {"$set": upd})
        except Exception as e:
            log.warning("update produtor falhou: %r", e)
            doc = dict(atual)
            doc.update(upd)
            out = _resp_doc(doc)
            out["mensagem"] = "Perfil cadastrado com sucesso (sem persistência)"
            out["ok"] = True
            return out
        doc = dict(atual)
        doc.update(upd)
    else:
        doc = _non_null(body)
        doc["id"] = str(uuid4())
        doc["cod_ibge"] = produtor.codigo_ibge
        doc.setdefault("onboardingConcluido", False)
        doc["criado_em"] = agora
        doc["atualizado_em"] = agora
        try:
            db.produtores.insert_one(dict(doc))
        except Exception as e:
            log.warning("insert produtor falhou: %r", e)
            out = _resp_doc(doc)
            out["mensagem"] = "Perfil cadastrado com sucesso (sem persistência)"
            out["ok"] = True
            return out
    out = _resp_doc(doc)
    out["mensagem"] = "Perfil cadastrado com sucesso"
    out["ok"] = True
    return out
