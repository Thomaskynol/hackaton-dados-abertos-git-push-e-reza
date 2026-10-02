"""Rota /api/onboarding — conversa guiada com persistência de sessão no MongoDB."""
from fastapi import APIRouter
from ..schemas.produtor import OnboardingRequest, OnboardingResponse
from ..db import get_db

router = APIRouter(prefix="/api", tags=["Onboarding"])

_PERGUNTAS = {
    1: "Olá! Eu sou o AgroPilot 🌾. Qual é o seu nome?",
    2: "Prazer, {nome}! Me diz sua cidade e estado (ex: Rio Verde - GO).",
    3: "Show! Quais culturas você planta? (ex: soja, feijão, milho, uva)",
    4: "Qual o tamanho aproximado da sua área plantada em hectares?",
    5: "Perfeito! Você usa irrigação? (sim / não)",
    6: "Cadastro concluído! 🎉 Agora você receberá alertas climáticos e recomendações do ZARC e Agrofit direto por aqui.",
}


def _col(db):
    try:
        return db["sessoes_onboarding"] if db is not None else None
    except Exception:
        return None


def _obter_sessao(col, telefone: str) -> dict:
    if col is None:
        return {}
    try:
        doc = col.find_one({"telefone": telefone}, {"_id": 0})
        return doc or {}
    except Exception:
        return {}


def _salvar_sessao(col, telefone: str, dados: dict):
    if col is None:
        return
    try:
        col.update_one({"telefone": telefone}, {"$set": dados}, upsert=True)
    except Exception:
        pass


@router.post("/onboarding")
def responder_onboarding(req: OnboardingRequest):
    db = get_db()
    col = _col(db)

    sessao = _obter_sessao(col, req.telefone)
    perfil_parcial = sessao.get("perfil_parcial", {})

    etapa = req.etapa
    resposta = (req.resposta or "").strip()

    # Salva a resposta da etapa atual no perfil parcial
    campo_map = {1: "nome", 2: "municipio", 3: "culturas", 4: "area_ha", 5: "irrigacao"}
    if etapa in campo_map:
        campo = campo_map[etapa]
        valor = resposta
        if campo == "area_ha":
            try:
                valor = float(resposta.replace(",", "."))
            except Exception:
                valor = resposta
        elif campo == "irrigacao":
            valor = resposta.lower() in ("sim", "s", "yes", "1")
        perfil_parcial[campo] = valor

    # Atualiza sessão no Mongo
    _salvar_sessao(col, req.telefone, {
        "telefone": req.telefone,
        "etapa_atual": etapa + 1,
        "perfil_parcial": perfil_parcial,
    })

    proximo_passo = etapa + 1
    nome = perfil_parcial.get("nome", "produtor")

    if etapa == 1:
        pergunta = _PERGUNTAS[2].format(nome=nome)
    elif etapa < 5:
        pergunta = _PERGUNTAS.get(etapa + 1, _PERGUNTAS[6])
    else:
        # Cadastro finalizado: tenta gravar produtor na coleção produtores
        _finalizar_onboarding(db, req.telefone, perfil_parcial)
        pergunta = _PERGUNTAS[6]
        proximo_passo = 6

    return {
        "proximo_passo": proximo_passo,
        "pergunta": pergunta,
        "perfil_parcial": perfil_parcial,
    }


def _finalizar_onboarding(db, telefone: str, perfil: dict):
    """Ao concluir o onboarding, grava o produtor na coleção produtores."""
    if db is None:
        return
    try:
        import uuid
        col_prod = db["produtores"]
        doc_existente = col_prod.find_one({"telefone": telefone})
        produtor_id = str(doc_existente.get("id")) if doc_existente else str(uuid.uuid4())[:8]
        col_prod.update_one(
            {"telefone": telefone},
            {"$set": {
                "id": produtor_id,
                "telefone": telefone,
                **{k: v for k, v in perfil.items()},
                "onboarding_completo": True,
            }},
            upsert=True,
        )
    except Exception:
        pass
