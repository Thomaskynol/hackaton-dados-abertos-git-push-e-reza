"""Autenticação simples por telefone + PIN (4 a 6 dígitos).

Decisões (público: produtor rural, sem "senha pra decorar"):
  - PIN numérico de 4 a 6 dígitos, com hash PBKDF2-HMAC-SHA256 + salt por conta
    (stdlib hashlib, sem dependência nova). Nunca guardamos o PIN em claro.
  - Sessão por TOKEN OPACO aleatório (secrets.token_urlsafe), guardado na coleção
    `sessoes_auth` com validade (TTL). O cliente manda `Authorization: Bearer`.
  - Nada de JWT: token opaco é mais simples de revogar (basta apagar o doc) e não
    expõe payload. Suficiente para o escopo.

Tudo stdlib. Funções nunca levantam para o chamador em caso de dado inválido —
retornam None/False e quem chama decide o HTTP.
"""
import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

log = logging.getLogger(__name__)

_PBKDF2_ROUNDS = 120_000
_TOKEN_TTL_DIAS = 30
_RE_PIN = re.compile(r"^\d{4,6}$")


def pin_valido(pin) -> bool:
    """True se o PIN tem 4 a 6 dígitos numéricos."""
    return bool(_RE_PIN.match(str(pin or "")))


def hash_pin(pin: str) -> tuple[str, str]:
    """Gera (salt_hex, hash_hex) para o PIN. Salt novo a cada chamada."""
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", str(pin).encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return salt.hex(), dk.hex()


def verificar_pin(pin: str, salt_hex: str, hash_hex: str) -> bool:
    """Compara o PIN informado com o hash guardado, em tempo constante."""
    if not (pin and salt_hex and hash_hex):
        return False
    try:
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", str(pin).encode("utf-8"), salt, _PBKDF2_ROUNDS)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception as e:
        log.warning("verificar_pin falhou: %r", e)
        return False


def _col_sessoes(db):
    try:
        col = db.sessoes_auth
        # índice TTL: o Mongo expira o doc em `expira_em`
        try:
            col.create_index("token", unique=True)
            col.create_index("expira_em", expireAfterSeconds=0)
        except Exception:
            pass
        return col
    except Exception as e:
        log.warning("col sessoes_auth indisponível: %r", e)
        return None


def criar_token(db, produtor_id: str) -> str | None:
    """Cria uma sessão e devolve o token opaco. None se não der para persistir."""
    col = _col_sessoes(db)
    if col is None or not produtor_id:
        return None
    token = secrets.token_urlsafe(32)
    agora = datetime.now(timezone.utc)
    try:
        col.insert_one({
            "token": token,
            "produtor_id": produtor_id,
            "criado_em": agora,
            "expira_em": agora + timedelta(days=_TOKEN_TTL_DIAS),
        })
    except Exception as e:
        log.warning("criar_token falhou: %r", e)
        return None
    return token


def produtor_do_token(db, token: str) -> str | None:
    """Resolve o token -> produtor_id. None se inválido/expirado."""
    if db is None or not token:
        return None
    col = _col_sessoes(db)
    if col is None:
        return None
    try:
        doc = col.find_one({"token": token})
    except Exception as e:
        log.warning("produtor_do_token falhou: %r", e)
        return None
    if not doc:
        return None
    # checagem explícita de expiração (não dependemos só do TTL do Mongo)
    exp = doc.get("expira_em")
    if isinstance(exp, datetime):
        exp_utc = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        if exp_utc < datetime.now(timezone.utc):
            try:
                col.delete_one({"token": token})
            except Exception:
                pass
            return None
    return doc.get("produtor_id")


def revogar_token(db, token: str) -> None:
    """Logout do servidor: apaga a sessão. Silencioso."""
    if db is None or not token:
        return
    col = _col_sessoes(db)
    if col is None:
        return
    try:
        col.delete_one({"token": token})
    except Exception as e:
        log.warning("revogar_token falhou: %r", e)


def token_do_header(authorization: str | None) -> str | None:
    """Extrai o token de 'Authorization: Bearer <token>'."""
    if not authorization:
        return None
    partes = authorization.split(None, 1)
    if len(partes) == 2 and partes[0].lower() == "bearer":
        return partes[1].strip()
    return None


# Flag de ambiente: permite desligar a exigência de auth em testes/legado.
def auth_obrigatoria() -> bool:
    return os.getenv("AUTH_OBRIGATORIA", "0").strip().lower() in ("1", "true", "yes", "on")
