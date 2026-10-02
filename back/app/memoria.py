"""Persistência sessoes/mensagens/memorias (Mongo, nunca raise).

Modelo (doc §3):
  sessoes   {id, produtor_id, titulo, uf, cod_ibge, criado_em, atualizado_em}
  mensagens {id, sessao_id, produtor_id, autor, texto, intencao, fonte,
             dados, criado_em}
  memorias  {id, produtor_id, texto, origem, sessao_id, criado_em}
Indexes: produtores.telefone/id unique (existente), sessoes.produtor_id,
         mensagens.sessao_id, memorias.produtor_id.
"""
import logging
import re
import unicodedata
from datetime import datetime, timezone
from uuid import uuid4

log = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_indexes_sessoes(db) -> None:
    """Indexes das coleções novas. Nunca raise."""
    if db is None:
        return
    for col, key, unique in (
        ("sessoes", "produtor_id", False),
        ("sessoes", "id", True),
        ("mensagens", "sessao_id", False),
        ("memorias", "produtor_id", False),
    ):
        try:
            c = getattr(db, col, None)
            if c is None:
                continue
            c.create_index(key, unique=unique)
        except Exception as e:
            log.warning("index %s.%s falhou: %r", col, key, e)


def _col(db, name):
    try:
        return getattr(db, name, None)
    except Exception:
        return None


def criar_sessao(db, produtor_id: str, titulo: str | None = None,
                 uf: str | None = None, cod_ibge: str | None = None) -> dict | None:
    if db is None or not (produtor_id or "").strip():
        return None
    try:
        col = _col(db, "sessoes")
        if col is None:
            return None
        t = (titulo or "").strip() or "Conversa"
        agora = _now()
        doc = {
            "id": str(uuid4()), "produtor_id": produtor_id,
            "titulo": t[:80], "uf": (uf or "").upper() or None,
            "cod_ibge": cod_ibge or None,
            "criado_em": agora, "atualizado_em": agora,
        }
        col.insert_one(dict(doc))
        return {k: v for k, v in doc.items() if k != "_id"}
    except Exception as e:
        log.warning("criar_sessao falhou: %r", e)
        return None


def listar_sessoes(db, produtor_id: str) -> list:
    try:
        col = _col(db, "sessoes")
        if col is None or not produtor_id:
            return []
        try:
            cur = col.find({"produtor_id": produtor_id}).sort("criado_em", -1)
        except Exception:
            cur = col.find({"produtor_id": produtor_id})
        out = []
        for d in list(cur):
            try:
                out.append({k: v for k, v in dict(d).items() if k != "_id"})
            except Exception:
                continue
        return out
    except Exception as e:
        log.warning("listar_sessoes falhou: %r", e)
        return []


def buscar_sessao(db, sessao_id: str) -> dict | None:
    try:
        col = _col(db, "sessoes")
        if col is None or not sessao_id:
            return None
        return col.find_one({"id": sessao_id})
    except Exception as e:
        log.warning("buscar_sessao falhou: %r", e)
        return None


def salvar_mensagem(db, sessao_id: str, produtor_id: str, autor: str,
                    texto: str, intencao: str | None = None,
                    fonte: str | None = None, dados: dict | None = None) -> dict | None:
    if db is None or not sessao_id or not (texto or "").strip():
        return None
    try:
        col = _col(db, "mensagens")
        if col is None:
            return None
        doc = {
            "id": str(uuid4()), "sessao_id": sessao_id,
            "produtor_id": produtor_id or "",
            "autor": autor if autor in ("usuario", "copiloto") else "usuario",
            "texto": texto[:4000], "intencao": intencao, "fonte": fonte,
            "dados": dados or {}, "criado_em": _now(),
        }
        col.insert_one(dict(doc))
        try:  # bump sessão — melhor esforço
            col_ses = _col(db, "sessoes")
            if col_ses is not None:
                col_ses.update_one({"id": sessao_id},
                                   {"$set": {"atualizado_em": _now()}})
        except Exception:
            pass
        return {k: v for k, v in doc.items() if k != "_id"}
    except Exception as e:
        log.warning("salvar_mensagem falhou: %r", e)
        return None


def listar_mensagens(db, sessao_id: str) -> list:
    try:
        col = _col(db, "mensagens")
        if col is None or not sessao_id:
            return []
        try:
            cur = col.find({"sessao_id": sessao_id}).sort("criado_em", 1)
        except Exception:
            cur = col.find({"sessao_id": sessao_id})
        out = []
        for d in list(cur):
            try:
                out.append({k: v for k, v in dict(d).items() if k != "_id"})
            except Exception:
                continue
        return out
    except Exception as e:
        log.warning("listar_mensagens falhou: %r", e)
        return []


def listar_memorias(db, produtor_id: str, limite: int = 8) -> list:
    try:
        col = _col(db, "memorias")
        if col is None or not produtor_id:
            return []
        try:
            cur = col.find({"produtor_id": produtor_id}).sort("criado_em", -1).limit(limite)
        except Exception:
            cur = col.find({"produtor_id": produtor_id})
        out = []
        for d in list(cur)[:limite]:
            try:
                out.append({k: v for k, v in dict(d).items() if k != "_id"})
            except Exception:
                continue
        return list(reversed(out))  # cronológica p/ injeção no prompt
    except Exception as e:
        log.warning("listar_memorias falhou: %r", e)
        return []


def salvar_memoria(db, produtor_id: str, texto: str,
                   origem: str = "chat", sessao_id: str | None = None) -> dict | None:
    if db is None or not produtor_id or not (texto or "").strip():
        return None
    try:
        col = _col(db, "memorias")
        if col is None:
            return None
        t = texto.strip()[:280]
        try:  # dedup barato: mesma chave não duplica
            if col.find_one({"produtor_id": produtor_id, "texto": t}):
                return None
        except Exception:
            pass
        doc = {"id": str(uuid4()), "produtor_id": produtor_id, "texto": t,
               "origem": origem if origem in ("chat", "onboarding") else "chat",
               "sessao_id": sessao_id, "criado_em": _now()}
        col.insert_one(dict(doc))
        return {k: v for k, v in doc.items() if k != "_id"}
    except Exception as e:
        log.warning("salvar_memoria falhou: %r", e)
        return None


# --- extração mínima sem LLM (regex/keyword, doc pede "no extra LLM call") ---

_CULTURAS = ["milho", "soja", "feijao", "feijão", "arroz", "trigo", "uva",
             "tomate", "cafe", "café", "algodao", "amendoim", "sorgo",
             "batata", "cebola", "mandioca", "cana"]
_PRAGAS = ["mildio", "míldio", "oidio", "oídio", "lagarta", "ferrugem",
           "pulg", "broca", "mosca", "fungo", "doenca", "doença", "praga",
           "percevejo", "cigarrinha", "nemat"]
_LOCAIS = ["hectare", "hectares", " ha", "alqueire", "talhao", "talhão",
           "lote", "area", "área"]


def _norm(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def extrair_memorias(mensagem: str, resposta: str | None = None) -> list[str]:
    """Fatos duráveis da troca. Só keyword, nunca inventa. Max 3, 1 linha cada."""
    achados: list[str] = []
    texto = _norm(f"{mensagem or ''} {resposta or ''}")
    curto = (mensagem or "").strip()
    for c in _CULTURAS:
        if _norm(c) in texto:
            achados.append(f"planta {c}")
            break
    for p in _PRAGAS:
        if _norm(p) in texto:
            achados.append(f"problema: {p} ({curto[:60]})")
            break
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(ha|hectares?|alqueires?)", texto)
    if m:
        achados.append(f"area citada: {m.group(0).strip()}")
    elif any(_norm(w) in texto for w in _LOCAIS):
        achados.append(f"local/area: {curto[:80]}")
    return achados[:3]


def contexto_memorias(db, produtor_id: str) -> str:
    """Últimas 8 memórias como bloco de prompt. Vazio se sem db. Cap 2000 chars."""
    mems = listar_memorias(db, produtor_id, 8) if produtor_id else []
    if not mems:
        return ""
    linhas = [f"- {m.get('texto')}" for m in mems if (m.get("texto") or "").strip()]
    if not linhas:
        return ""
    return ("\nmemorias do produtor:\n" + "\n".join(linhas))[:2000]
