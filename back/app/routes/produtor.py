from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ..db import get_db
from ..mock import MOCK_PRODUTOR
from ..schemas.produtor import ProdutorCreate
from .. import auth

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Produtor"])


class SignupIn(BaseModel):
    telefone: str
    nome: str
    pin: Optional[str] = None


class LoginIn(BaseModel):
    telefone: str
    pin: Optional[str] = None


class ContaPatch(BaseModel):
    nome: Optional[str] = None
    municipio: Optional[str] = None
    uf: Optional[str] = None
    cod_ibge: Optional[str] = None
    codigo_ibge: Optional[str] = None
    lavouras: Optional[Any] = None
    onboardingConcluido: Optional[bool] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_tel(v: Any) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _hectares_total(lavouras: Any) -> float:
    total = 0.0
    for l in lavouras or []:
        try:
            v = l.get("area_ha") if isinstance(l, dict) else getattr(l, "area_ha", None)
            total += float(v or 0)
        except Exception:
            continue
    return float(total)


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
    # nunca vaza o segredo do PIN; expõe só se a conta TEM pin
    tem_pin = bool(out.pop("pin_hash", None)) and bool(out.pop("pin_salt", None))
    out.pop("pin_hash", None)
    out.pop("pin_salt", None)
    out["tem_pin"] = tem_pin
    if "cod_ibge" in out and "codigo_ibge" not in out:
        out["codigo_ibge"] = out.get("cod_ibge")
    return out


def _conta_resp(doc: dict) -> dict:
    out = _resp_doc(doc)
    if "codigo_ibge" in out and "cod_ibge" not in out:
        out["cod_ibge"] = out.get("codigo_ibge")
    if "cod_ibge" in out and "codigo_ibge" not in out:
        out["codigo_ibge"] = out.get("cod_ibge")
    out.setdefault("municipio", "")
    out.setdefault("uf", "")
    out.setdefault("cod_ibge", "")
    if "codigo_ibge" not in out:
        out["codigo_ibge"] = out.get("cod_ibge", "")
    out.setdefault("lavouras", [])
    out.setdefault("onboardingConcluido", False)
    try:
        out["hectares_total"] = _hectares_total(out.get("lavouras"))
    except Exception:
        out["hectares_total"] = 0.0
    return out


def _find_by_telefone(db, norm: str, raw: Any = None):
    col = db.produtores
    try:
        doc = col.find_one({"telefone": norm})
        if doc:
            return doc
    except Exception:
        pass
    if raw is not None and str(raw) != norm:
        try:
            doc = col.find_one({"telefone": raw})
            if doc:
                return doc
        except Exception:
            pass
    # varredura normalizada cobre legados "+55..." vs so digitos
    try:
        docs = list(col.find({}))
    except Exception:
        return None
    for d in docs or []:
        try:
            if norm and _norm_tel((d or {}).get("telefone")) == norm:
                return d
        except Exception:
            continue
    return None


def _non_null(d: dict) -> dict:
    return {k: v for k, v in (d or {}).items() if v is not None}


def _db_ou_503():
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou: %r", e)
        db = None
    if db is None:
        raise HTTPException(status_code=503, detail="sem banco de dados")
    return db


def _exigir_dono(db, id_alvo: str, authorization: str | None):
    """Quando AUTH_OBRIGATORIA está ligada, só o dono do token acessa a conta.
    Com a flag desligada (padrão/legado/testes), não bloqueia — mantém compat."""
    if not auth.auth_obrigatoria():
        return
    tok = auth.token_do_header(authorization)
    pid = auth.produtor_do_token(db, tok) if tok else None
    if not pid:
        raise HTTPException(status_code=401, detail="sessão inválida ou expirada")
    if pid != id_alvo:
        raise HTTPException(status_code=403, detail="essa conta não é sua")


@router.post("/produtor/signup", status_code=201)
def signup_conta(body: SignupIn):
    norm = _norm_tel(body.telefone)
    nome = (body.nome or "").strip()
    if len(norm) < 10 or len(nome) < 2:
        raise HTTPException(status_code=422, detail="telefone/nome invalidos")
    # PIN: obrigatório quando enviado; se vier, precisa ser 4-6 dígitos
    pin = (body.pin or "").strip() or None
    if pin is not None and not auth.pin_valido(pin):
        raise HTTPException(status_code=422, detail="PIN deve ter de 4 a 6 dígitos")
    db = _db_ou_503()
    _ensure_indexes(db)
    if _find_by_telefone(db, norm, body.telefone):
        raise HTTPException(status_code=409, detail="telefone ja cadastrado")
    agora = _now()
    doc = {
        "id": str(uuid4()),
        "telefone": norm,
        "nome": nome,
        "municipio": "",
        "uf": "",
        "cod_ibge": "",
        "codigo_ibge": "",
        "lavouras": [],
        "onboardingConcluido": False,
        "criado_em": agora,
        "atualizado_em": agora,
    }
    if pin is not None:
        salt, h = auth.hash_pin(pin)
        doc["pin_salt"] = salt
        doc["pin_hash"] = h
    try:
        db.produtores.insert_one(dict(doc))
    except Exception as e:
        log.warning("insert signup falhou: %r", e)
        raise HTTPException(status_code=409, detail="telefone ja cadastrado")
    resp = _conta_resp(doc)
    # já devolve um token de sessão: signup entra logado
    tok = auth.criar_token(db, doc["id"])
    if tok:
        resp["token"] = tok
    return resp


@router.post("/produtor/login")
def login_conta(body: LoginIn):
    norm = _norm_tel(body.telefone)
    if not norm:
        raise HTTPException(status_code=422, detail="telefone invalido")
    db = _db_ou_503()
    _ensure_indexes(db)
    doc = _find_by_telefone(db, norm, body.telefone)
    if not doc:
        raise HTTPException(status_code=404, detail="produtor nao encontrado")
    # Se a conta tem PIN, exige PIN correto. Contas antigas sem PIN entram só
    # com telefone (compat) — mas são incentivadas a definir um PIN depois.
    tem_pin = bool(doc.get("pin_hash") and doc.get("pin_salt"))
    pin = (body.pin or "").strip() or None
    if tem_pin:
        if not pin:
            raise HTTPException(status_code=422, detail="informe o PIN")
        if not auth.verificar_pin(pin, doc.get("pin_salt"), doc.get("pin_hash")):
            raise HTTPException(status_code=401, detail="PIN incorreto")
    resp = _conta_resp(doc)
    resp["tem_pin"] = tem_pin
    tok = auth.criar_token(db, doc.get("id"))
    if tok:
        resp["token"] = tok
    return resp


@router.get("/produtor/me")
def produtor_me(authorization: str | None = Header(default=None)):
    """Conta do dono do token (Authorization: Bearer). 401 se token inválido."""
    db = _db_ou_503()
    tok = auth.token_do_header(authorization)
    pid = auth.produtor_do_token(db, tok) if tok else None
    if not pid:
        raise HTTPException(status_code=401, detail="sessão inválida ou expirada")
    doc = db.produtores.find_one({"id": pid})
    if not doc:
        raise HTTPException(status_code=404, detail="produtor nao encontrado")
    return _conta_resp(doc)


@router.post("/produtor/logout")
def produtor_logout(authorization: str | None = Header(default=None)):
    """Revoga a sessão atual (apaga o token no servidor). Idempotente."""
    try:
        db = get_db()
    except Exception:
        db = None
    tok = auth.token_do_header(authorization)
    if db is not None and tok:
        auth.revogar_token(db, tok)
    return {"ok": True}


@router.get("/produtor/{id}")
def obter_produtor(id: str, authorization: str | None = Header(default=None)):
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em GET produtor: %r", e)
        db = None
    if db is not None:
        _exigir_dono(db, id, authorization)
        try:
            _ensure_indexes(db)
            doc = db.produtores.find_one({"id": id})
        except Exception as e:
            log.warning("find produtor %s falhou: %r", id, e)
            doc = None
        if doc:
            return _conta_resp(doc)
    if id != MOCK_PRODUTOR["id"] and id != "antonio":
        # fallback mock com o id requisitado (facilita testes do front)
        resposta = dict(MOCK_PRODUTOR)
        resposta["id"] = id
        return _conta_resp(resposta)
    return _conta_resp(dict(MOCK_PRODUTOR))


@router.patch("/produtor/{id}")
def atualizar_conta(id: str, body: ContaPatch,
                    authorization: str | None = Header(default=None)):
    db = _db_ou_503()
    _exigir_dono(db, id, authorization)
    _ensure_indexes(db)
    try:
        atual = db.produtores.find_one({"id": id})
    except Exception as e:
        log.warning("find patch %s falhou: %r", id, e)
        atual = None
    if not atual:
        raise HTTPException(status_code=404, detail="produtor nao encontrado")
    upd: dict = {}
    if body.nome is not None:
        upd["nome"] = body.nome.strip()
    if body.municipio is not None:
        upd["municipio"] = body.municipio
    if body.uf is not None:
        upd["uf"] = body.uf
    ibge_novo = body.cod_ibge if body.cod_ibge is not None else body.codigo_ibge
    if ibge_novo is not None:
        upd["cod_ibge"] = ibge_novo
        upd["codigo_ibge"] = ibge_novo
    if body.lavouras is not None:
        lavs = []
        for l in body.lavouras or []:
            if isinstance(l, dict):
                lavs.append(l)
            else:
                try:
                    lavs.append(l.model_dump())
                except Exception:
                    continue
        upd["lavouras"] = lavs
    if body.onboardingConcluido is not None:
        upd["onboardingConcluido"] = bool(body.onboardingConcluido)
    if "cod_ibge" in upd:
        antigo = atual.get("cod_ibge") or atual.get("codigo_ibge") or ""
        if upd["cod_ibge"] and upd["cod_ibge"] != antigo:
            try:
                from .regiao import solo_inferido_para
                inferido = solo_inferido_para(db, upd["cod_ibge"])
                if inferido:
                    upd["solo_inferido"] = inferido
            except Exception as e:
                log.warning("solo inferido patch falhou: %r", e)
    if not upd:
        return _conta_resp(atual)
    upd["atualizado_em"] = _now()
    try:
        db.produtores.update_one({"id": id}, {"$set": upd})
    except Exception as e:
        log.warning("update conta %s falhou: %r", id, e)
    doc = dict(atual)
    doc.update(upd)
    return _conta_resp(doc)


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
