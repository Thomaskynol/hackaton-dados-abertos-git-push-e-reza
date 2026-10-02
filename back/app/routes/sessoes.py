"""Rotas sessoes/mensagens/memorias. Sem mock: sem db vira 503 honesto."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from ..db import get_db
from ..memoria import (buscar_sessao, criar_sessao, ensure_indexes_sessoes,
                       listar_memorias, listar_mensagens, listar_sessoes)
from ..schemas.sessao import SessaoCreate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Sessoes"])


def _db_ou_503():
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou: %r", e)
        db = None
    if db is None:
        raise HTTPException(status_code=503, detail="sem banco de dados")
    try:
        ensure_indexes_sessoes(db)
    except Exception as e:
        log.warning("indexes sessoes falhou: %r", e)
    return db


@router.post("/sessoes", status_code=201)
def post_sessao(body: SessaoCreate):
    db = _db_ou_503()
    doc = criar_sessao(db, body.produtor_id, body.titulo, body.uf, body.cod_ibge)
    if not doc:
        raise HTTPException(status_code=503, detail="nao foi possivel criar sessao")
    return doc


@router.get("/sessoes")
def get_sessoes(produtor_id: str = Query(...)):
    db = _db_ou_503()
    return listar_sessoes(db, produtor_id)


@router.get("/sessoes/{sessao_id}/mensagens")
def get_mensagens(sessao_id: str):
    db = _db_ou_503()
    return listar_mensagens(db, sessao_id)


@router.get("/memorias")
def get_memorias(produtor_id: str = Query(...)):
    db = _db_ou_503()
    return listar_memorias(db, produtor_id, 50)


@router.get("/sessoes/{sessao_id}")
def get_sessao(sessao_id: str):
    db = _db_ou_503()
    doc = buscar_sessao(db, sessao_id)
    if not doc:
        raise HTTPException(status_code=404, detail="sessao nao encontrada")
    doc = dict(doc)
    doc.pop("_id", None)
    # última atividade = mensagem mais recente (melhor esforço)
    try:
        msgs = listar_mensagens(db, sessao_id)
        if msgs:
            doc["ultima_atividade"] = msgs[-1].get("criado_em")
        else:
            doc["ultima_atividade"] = doc.get("atualizado_em") or doc.get("criado_em")
    except Exception:
        doc["ultima_atividade"] = doc.get("atualizado_em")
    return doc
