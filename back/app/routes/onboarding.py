"""POST /api/onboarding — cadastro por chat com EXTRAÇÃO REAL.

Diferente da versão antiga (script fixo que ignorava a resposta), aqui cada
etapa interpreta o que o produtor escreveu e casa com dado oficial:

  etapa 1  -> nome (texto livre; guarda)
  etapa 2  -> cidade/UF: resolve cod_ibge REAL (municípios/IBGE). Se não achar,
              repete a pergunta pedindo "cidade e estado".
  etapa 3  -> culturas: converte para as canônicas conhecidas. Se nenhuma bater,
              repete pedindo um exemplo.
  etapa 4  -> área em hectares: extrai número; distribui nas lavouras.
  etapa 5  -> conclui (marca onboardingConcluido) e devolve o resumo com a fonte.

Salva no produtor a cada etapa (quando produtor_id/telefone vier), via a mesma
camada de persistência do PATCH. Nunca inventa cod_ibge: dado só com fonte.
"""
import logging

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Optional

from ..db import get_db
from ..extracao import (
    resolver_municipio, extrair_culturas, extrair_area, separar_cidade_uf,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Onboarding"])


class OnboardingIn(BaseModel):
    etapa: int
    resposta: str
    telefone: Optional[str] = None
    produtor_id: Optional[str] = None


def _norm_tel(v: Any) -> str:
    return "".join(ch for ch in str(v or "") if ch.isdigit())


def _acha_produtor(db, produtor_id, telefone):
    if db is None:
        return None
    try:
        if produtor_id:
            d = db.produtores.find_one({"id": produtor_id})
            if d:
                return d
        norm = _norm_tel(telefone)
        if norm:
            return db.produtores.find_one({"telefone": norm})
    except Exception as e:
        log.warning("acha produtor onboarding falhou: %r", e)
    return None


def _rotulo(canon):
    try:
        from ..precos_dados import rotulo_cultura
        return rotulo_cultura(canon)
    except Exception:
        return str(canon).capitalize()


def _salvar(db, doc, patch: dict):
    """Aplica patch no produtor (quando há doc). Silencioso."""
    if db is None or not doc:
        return
    try:
        patch = dict(patch)
        db.produtores.update_one({"id": doc.get("id")}, {"$set": patch})
    except Exception as e:
        log.warning("salvar etapa onboarding falhou: %r", e)


@router.post("/onboarding")
def responder_onboarding(req: OnboardingIn):
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db onboarding falhou: %r", e)
        db = None

    doc = _acha_produtor(db, req.produtor_id, req.telefone)
    resposta = (req.resposta or "").strip()
    etapa = req.etapa

    # etapa 1: nome
    if etapa == 1:
        nome = resposta
        if doc and nome:
            _salvar(db, doc, {"nome": nome})
        return {
            "proximo_passo": 2,
            "pergunta": f"Prazer, {nome or 'produtor'}! Em qual cidade fica a sua terra? "
                        f"Me diga a cidade e o estado — ex.: Araraquara - SP.",
            "perfil_parcial": {"nome": nome},
        }

    # etapa 2: cidade/UF -> cod_ibge real
    if etapa == 2:
        mun = resolver_municipio(db, resposta)
        if not mun:
            cidade, uf = separar_cidade_uf(resposta)
            dica = ("Não encontrei esse município. Pode escrever a cidade e o estado juntos? "
                    "Ex.: Ribeirão Preto - SP.")
            if cidade and not uf:
                dica = (f"Achei a cidade \"{cidade}\", mas preciso do estado para ter certeza. "
                        f"Pode mandar assim: {cidade} - SP?")
            return {
                "proximo_passo": 2,  # repete a mesma etapa
                "pergunta": dica,
                "perfil_parcial": {},
                "erro": "municipio_nao_resolvido",
            }
        if doc:
            _salvar(db, doc, {
                "municipio": mun["nome"], "uf": mun["uf"],
                "cod_ibge": mun["cod_ibge"], "codigo_ibge": mun["cod_ibge"],
            })
        return {
            "proximo_passo": 3,
            "pergunta": f"{mun['nome']}/{mun['uf']}, anotado! O que você planta por aí? "
                        f"Pode listar — ex.: feijão e milho.",
            "perfil_parcial": {"municipio": mun["nome"], "uf": mun["uf"],
                               "cod_ibge": mun["cod_ibge"]},
        }

    # etapa 3: culturas -> canônicas
    if etapa == 3:
        culturas = extrair_culturas(resposta)
        if not culturas:
            return {
                "proximo_passo": 3,
                "pergunta": "Não reconheci a cultura. Pode dizer o nome da lavoura? "
                            "Ex.: feijão, milho, soja, café, cana…",
                "perfil_parcial": {},
                "erro": "cultura_nao_reconhecida",
            }
        lavouras = [{"cultura": c, "area_ha": None, "solo": None, "irrigacao": None}
                    for c in culturas]
        if doc:
            _salvar(db, doc, {"lavouras": lavouras})
        nomes = ", ".join(_rotulo(c) for c in culturas)
        return {
            "proximo_passo": 4,
            "pergunta": f"Boa — {nomes}. Mais ou menos quantos hectares você planta no total?",
            "perfil_parcial": {"culturas": culturas},
        }

    # etapa 4: área -> hectares
    if etapa == 4:
        area = extrair_area(resposta)
        if area is None:
            return {
                "proximo_passo": 4,
                "pergunta": "Só preciso de um número aproximado de hectares. Ex.: 10.",
                "perfil_parcial": {},
                "erro": "area_nao_reconhecida",
            }
        if doc:
            lavs = list(doc.get("lavouras") or [])
            if lavs:
                # divide a área informada entre as lavouras cadastradas
                por_lav = round(area / len(lavs), 2)
                for l in lavs:
                    l["area_ha"] = por_lav
            else:
                lavs = [{"cultura": None, "area_ha": area, "solo": None, "irrigacao": None}]
            _salvar(db, doc, {"lavouras": lavs})
        return {
            "proximo_passo": 5,
            "pergunta": f"Tudo certo! Guardei {area:.0f} hectares. "
                        f"Seu AgroPilot já está pronto — vou te mostrar a sua safra.",
            "perfil_parcial": {"area_ha": area},
        }

    # etapa 5+: conclui
    if doc:
        _salvar(db, doc, {"onboardingConcluido": True})
    resumo = None
    if doc:
        atual = _acha_produtor(db, doc.get("id"), None) or doc
        resumo = {
            "nome": atual.get("nome"),
            "municipio": atual.get("municipio"),
            "uf": atual.get("uf"),
            "cod_ibge": atual.get("cod_ibge"),
            "lavouras": atual.get("lavouras") or [],
        }
    return {
        "proximo_passo": 5,
        "pergunta": "Cadastro concluído! Agora é só perguntar o que quiser sobre a sua safra.",
        "perfil_parcial": {"status": "concluido"},
        "resumo": resumo,
        "fonte": "Dados do cadastro casados com IBGE (município) e ZARC/PAM/PSR (cultura).",
    }
