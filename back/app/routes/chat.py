from fastapi import APIRouter
from ..schemas.chat import ChatRequest, ChatResponseSuccess, ChatResponseError
from ..schemas.intencoes import Intencao
from ..core.router_intencao import classificar_intencao
from ..db import get_db
from ..dados_reais import (
    buscar_janelas,
    buscar_produtos,
    extrair_alvo,
    extrair_cultura,
    produto_resumo,
)
from ..mock import (
    MOCK_CHAT_PRAGA,
    MOCK_CHAT_PLANEJAMENTO,
    MOCK_CHAT_CLIMA,
    MOCK_CHAT_SAUDACAO,
)

router = APIRouter(prefix="/api", tags=["Chat"])

IBGE_DEFAULT = "3503208"  # Araraquara (3503307=Araras; mock antigo usa 3503307)


def _planejamento_real(mensagem: str):
    try:
        db = get_db()
        if db is None:
            return None
        cultura = extrair_cultura(mensagem) or "feijao"
        docs = buscar_janelas(db, cultura, IBGE_DEFAULT)
        if not docs:
            return None
        mun = db.municipios.find_one({"cod_ibge": IBGE_DEFAULT}, {"_id": 0}) or {}
        melhor = docs[0]
        decs = sorted(melhor.get("dec") or {}, key=lambda d: (melhor["dec"][d], int(d)))[:4]
        janelas = [{"dec": int(d), "risco": melhor["dec"][d]} for d in decs]
        janela_txt = ", ".join(f"dec {j['dec']} (risco {j['risco']}%)" for j in janelas)
        return {
            "resposta": (
                f"Para {cultura} em {mun.get('nome', 'Araraquara')}/{mun.get('uf', 'SP')} "
                f"({melhor.get('solo_canonico')}, {melhor.get('manejo_canonico')}):\n"
                f"• Melhores janelas: {janela_txt}\n"
                f"• {len(docs)} combinações solo/manejo/ciclo no ZARC"
            ),
            "intencao": "PLANEJAMENTO",
            "fonte": "ZARC 2025/26",
            "data_extracao": "2026-10-02",
            "dados": {
                "cultura": cultura,
                "cod_ibge": IBGE_DEFAULT,
                "solo": melhor.get("solo_canonico"),
                "manejo": melhor.get("manejo_canonico"),
                "janelas": janelas,
                "cultivares": [],
            },
        }
    except Exception:
        return None


def _praga_real(mensagem: str):
    try:
        db = get_db()
        if db is None:
            return None
        cultura = extrair_cultura(mensagem) or "uva"
        alvo = extrair_alvo(mensagem)
        docs = buscar_produtos(db, cultura, alvo)
        if not docs:
            return None
        produtos = [produto_resumo(d) for d in docs]
        linhas = "\n".join(
            f"• {p['nome']} (classe {p['classe']})" + (" [ORGÂNICO]" if p["organico"] else "")
            for p in produtos
        )
        return {
            "resposta": f"Para {alvo or 'praga'} em {cultura}, os produtos registrados são:\n{linhas}",
            "intencao": "PRAGA",
            "fonte": "Agrofit/MAPA",
            "data_extracao": "2026-10-02",
            "dados": {
                "cultura": cultura,
                "praga": alvo or "",
                "produtos": produtos,
            },
        }
    except Exception:
        return None


@router.post("/chat")
def processar_chat(req: ChatRequest):
    intencao = classificar_intencao(req.mensagem)

    if intencao == Intencao.PRAGA:
        return _praga_real(req.mensagem) or MOCK_CHAT_PRAGA
    elif intencao == Intencao.PLANEJAMENTO:
        return _planejamento_real(req.mensagem) or MOCK_CHAT_PLANEJAMENTO
    elif intencao == Intencao.CLIMA:
        return MOCK_CHAT_CLIMA
    elif intencao == Intencao.SAUDACAO:
        return MOCK_CHAT_SAUDACAO
    elif intencao == Intencao.PERFIL:
        return {
            "resposta": "Antônio, seu cadastro conta com 5 ha de uva e 3 ha de tomate em Araraquara/SP.",
            "intencao": "PERFIL",
            "fonte": "Cadastro Produtor Familiar",
            "data_extracao": "2026-10-02",
            "dados": {"produtor_id": req.produtor_id},
        }
    elif intencao == Intencao.VENDA:
        return {
            "resposta": "Para comercialização da sua safra, há chamada pública do PAA aberta em Araraquara até o fim do mês.",
            "intencao": "VENDA",
            "fonte": "CONAB / PAA Dados Abertos",
            "data_extracao": "2026-10-02",
            "dados": {},
        }
    else:
        return {
            "erro": "NAO_ENTENDI",
            "mensagem": "Não consegui entender. Pode reformular?",
            "sugestoes": [
                "Quando planto feijão?",
                "Minha uva está com míldio",
                "Vai gear?",
            ],
        }
