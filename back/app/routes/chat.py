from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
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
from ..llm import (
    gerar_resposta,
    gerar_resposta_stream,
    responder_com_tools,
    responder_com_tools_stream,
)

router = APIRouter(prefix="/api", tags=["Chat"])

IBGE_DEFAULT = "3503208"  # Araraquara (3503307=Araras)
DATA_EXTRACAO = "2026-10-02"
SUGESTOES = [
    "Quando planto feijão?",
    "Minha uva está com míldio",
    "Vai gear?",
]


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
            "data_extracao": DATA_EXTRACAO,
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


def _planejamento_fallback(mensagem: str):
    cultura = extrair_cultura(mensagem) or "feijao"
    return {
        "resposta": (
            f"Para {cultura} em Araraquara/SP ({IBGE_DEFAULT}), "
            "não encontrei janelas ZARC no momento. "
            "Informe cultura e município ou consulte o ZARC 2025/26."
        ),
        "intencao": "PLANEJAMENTO",
        "fonte": "ZARC 2025/26",
        "data_extracao": DATA_EXTRACAO,
        "dados": {
            "cultura": cultura,
            "cod_ibge": IBGE_DEFAULT,
            "janelas": [],
            "cultivares": [],
        },
    }


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
            "data_extracao": DATA_EXTRACAO,
            "dados": {
                "cultura": cultura,
                "praga": alvo or "",
                "produtos": produtos,
            },
        }
    except Exception:
        return None


def _praga_fallback(mensagem: str):
    cultura = extrair_cultura(mensagem) or "uva"
    alvo = extrair_alvo(mensagem) or ""
    return {
        "resposta": (
            f"Para {alvo or 'praga'} em {cultura}, não encontrei produtos no Agrofit/MAPA com este filtro. "
            "Informe cultura e alvo (ex: míldio em uva) ou busque um responsável técnico."
        ),
        "intencao": "PRAGA",
        "fonte": "Agrofit/MAPA",
        "data_extracao": DATA_EXTRACAO,
        "dados": {
            "cultura": cultura,
            "praga": alvo or "",
            "produtos": [],
        },
    }


def _perfil_real(produtor_id: str):
    try:
        db = get_db()
        if db is not None:
            try:
                doc = db.produtores.find_one({"id": produtor_id})
            except Exception:
                doc = None
            if doc:
                nome = doc.get("nome") or "produtor"
                municipio = doc.get("municipio") or "n/d"
                uf = doc.get("uf") or "n/d"
                lavs = doc.get("lavouras") or []
                if lavs:
                    lav_txt = ", ".join(
                        f"{l.get('area_ha', '?')} ha de {l.get('cultura', '?')}" for l in lavs
                    )
                else:
                    lav_txt = "sem lavouras cadastradas"
                return {
                    "resposta": (
                        f"{nome}, seu cadastro: {lav_txt} em {municipio}/{uf}."
                    ),
                    "intencao": "PERFIL",
                    "fonte": "Cadastro Produtor Familiar",
                    "data_extracao": DATA_EXTRACAO,
                    "dados": {
                        "produtor_id": produtor_id,
                        "cadastrado": True,
                        "nome": nome,
                        "municipio": municipio,
                        "uf": uf,
                        "lavouras": lavs,
                    },
                }
    except Exception:
        pass
    return {
        "resposta": (
            "Produtor ainda sem cadastro na base. Complete o onboarding "
            "(nome, município/UF, culturas, área) para personalizar as respostas."
        ),
        "intencao": "PERFIL",
        "fonte": "Cadastro Produtor Familiar",
        "data_extracao": DATA_EXTRACAO,
        "dados": {"produtor_id": produtor_id, "cadastrado": False},
    }


def _clima_real():
    nome, uf, janela_txt, janelas = "Araraquara", "SP", "n/d", []
    try:
        db = get_db()
        if db is not None:
            try:
                mun = db.municipios.find_one({"cod_ibge": IBGE_DEFAULT}, {"_id": 0})
            except Exception:
                mun = None
            if mun:
                nome = mun.get("nome") or nome
                uf = mun.get("uf") or uf
            try:
                docs = buscar_janelas(db, "feijao", IBGE_DEFAULT)
            except Exception:
                docs = None
            if docs:
                melhor = docs[0]
                try:
                    decs = sorted(
                        melhor.get("dec") or {},
                        key=lambda d: (melhor["dec"][d], int(d)),
                    )[:4]
                    janelas = [{"dec": int(d), "risco": melhor["dec"][d]} for d in decs]
                    janela_txt = ", ".join(
                        f"dec {j['dec']} (risco {j['risco']}%)" for j in janelas
                    )
                except Exception:
                    pass
    except Exception:
        pass
    return {
        "resposta": (
            f"Em {nome}/{uf}: janelas ZARC feijão ({janela_txt}); "
            "previsão INMET não consultada em tempo real — "
            "monitore queda brusca de temperatura nas próximas 72h e áreas baixas."
        ),
        "intencao": "CLIMA",
        "fonte": "INMET + ZARC",
        "data_extracao": DATA_EXTRACAO,
        "dados": {
            "municipio": nome,
            "uf": uf,
            "cod_ibge": IBGE_DEFAULT,
            "cultura_ref": "feijao",
            "janelas": janelas,
            "previsao_dias": 3,
        },
    }


def _venda_real(produtor_id: str):
    culturas = []
    try:
        db = get_db()
        if db is not None:
            try:
                doc = db.produtores.find_one({"id": produtor_id})
            except Exception:
                doc = None
            if doc:
                for l in doc.get("lavouras") or []:
                    c = (l or {}).get("cultura")
                    if c:
                        culturas.append(c)
    except Exception:
        pass
    culturas_txt = ", ".join(culturas) if culturas else "sem culturas cadastradas"
    return {
        "resposta": (
            f"Culturas: {culturas_txt}. Para comercialização, orientação PAA/CONAB: "
            "verifique chamada pública e preços de referência no portal CONAB."
        ),
        "intencao": "VENDA",
        "fonte": "CONAB / PAA Dados Abertos",
        "data_extracao": DATA_EXTRACAO,
        "dados": {"culturas": culturas, "produtor_id": produtor_id},
    }


def _saudacao_real(produtor_id: str):
    nome = "produtor"
    try:
        db = get_db()
        if db is not None:
            try:
                doc = db.produtores.find_one({"id": produtor_id})
            except Exception:
                doc = None
            if doc and doc.get("nome"):
                nome = doc.get("nome")
    except Exception:
        pass
    return {
        "resposta": f"Olá, {nome}! Como posso ajudar hoje na sua lavoura?",
        "intencao": "SAUDACAO",
        "fonte": "Assistente Agro Familiar",
        "data_extracao": DATA_EXTRACAO,
        "dados": {},
    }


def _nao_entendi_base():
    return {
        "resposta": (
            "Não consegui entender. Pode reformular? "
            "Ex: Quando planto feijão? / Minha uva está com míldio / Vai gear?"
        ),
        "intencao": "NAO_ENTENDI",
        "fonte": "Assistente Agro Familiar",
        "data_extracao": DATA_EXTRACAO,
        "dados": {},
    }


def _ctx_planejamento(base: dict) -> str:
    d = base.get("dados") or {}
    janelas = d.get("janelas") or []
    janela_txt = ", ".join(f"dec {j.get('dec')} (risco {j.get('risco')}%)" for j in janelas)
    return (
        f"fonte: {base.get('fonte')}; cultura: {d.get('cultura')}; "
        f"cod_ibge: {d.get('cod_ibge', IBGE_DEFAULT)}; solo: {d.get('solo')}; "
        f"manejo: {d.get('manejo')}; janelas: {janela_txt or 'n/d'}; "
        f"cultivares: {', '.join(d.get('cultivares') or []) or 'n/d'}"
    )


def _ctx_praga(base: dict) -> str:
    d = base.get("dados") or {}
    prods = d.get("produtos") or []
    linhas = "; ".join(
        f"{p.get('nome')} (classe {p.get('classe')}){' [ORGÂNICO]' if p.get('organico') else ''}"
        for p in prods
    )
    return (
        f"fonte: {base.get('fonte')}; cultura: {d.get('cultura')}; "
        f"praga/alvo: {d.get('praga') or 'n/d'}; produtos: {linhas or 'n/d'}"
    )


def _ctx_perfil(base: dict) -> str:
    d = base.get("dados") or {}
    if not d.get("cadastrado"):
        return (
            "produtor ainda sem cadastro na base; "
            "convidar a completar onboarding (nome, municipio/UF, culturas, área)"
        )
    lavs = d.get("lavouras") or []
    lav_txt = ", ".join(
        f"{l.get('area_ha', '?')} ha de {l.get('cultura', '?')}" for l in lavs
    ) or "sem lavouras"
    return (
        f"fonte: {base.get('fonte')}; nome: {d.get('nome')}; "
        f"municipio/UF: {d.get('municipio')}/{d.get('uf')}; lavouras: {lav_txt}"
    )


def _ctx_clima(base: dict) -> str:
    d = base.get("dados") or {}
    janelas = d.get("janelas") or []
    janela_txt = ", ".join(f"dec {j.get('dec')} (risco {j.get('risco')}%)" for j in janelas)
    return (
        f"fonte: {base.get('fonte')}; municipio: {d.get('municipio')}/{d.get('uf')} "
        f"({d.get('cod_ibge')}); janelas ZARC feijao: {janela_txt or 'n/d'}; "
        "INMET como fonte externa não consultada em tempo real"
    )


def _ctx_venda(base: dict) -> str:
    d = base.get("dados") or {}
    culturas = ", ".join(d.get("culturas") or []) or "sem culturas cadastradas"
    return (
        f"fonte: {base.get('fonte')}; culturas do perfil: {culturas}; "
        "orientação PAA/CONAB: chamada pública e preços de referência no portal CONAB"
    )


def _ctx_saudacao(base: dict) -> str:
    return f"fonte: {base.get('fonte')}; saudação ao produtor; resposta: {base.get('resposta')}"


def _ctx_nao_entendi(mensagem: str) -> str:
    return (
        f"pergunta fora do escopo ZARC/Agrofit/PAA: {mensagem}; "
        "pedir reformulação com exemplos: Quando planto feijão? / Minha uva está com míldio / Vai gear?"
    )


def _com_llm(intencao: str, mensagem: str, base: dict, contexto: str) -> dict:
    try:
        texto = gerar_resposta(intencao, mensagem, contexto)
    except Exception:
        texto = None
    if texto:
        return {**base, "resposta": texto}
    return base


_FONTE_AGENT = "ZARC+Agrofit+PSR+SIGEF+ANA via tools"


def _responder_agentico(mensagem: str, produtor_id: str):
    intencao = classificar_intencao(mensagem)
    usadas, texto = [], None
    try:
        db = get_db()
    except Exception:
        db = None
    try:
        texto, usadas = responder_com_tools(mensagem, db, produtor_id) or (None, [])
    except Exception:
        texto, usadas = None, usadas or []
    if texto:
        base, _ = _base_e_ctx(intencao, mensagem, produtor_id)
        dados = dict(base.get("dados") or {})
        dados["ferramentas_usadas"] = usadas
        return {**base, "resposta": texto, "intencao": intencao.value,
                "fonte": _FONTE_AGENT if usadas else base.get("fonte"),
                "dados": dados}, intencao
    return None, intencao


def _base_e_ctx(intencao, mensagem: str, produtor_id: str):
    if intencao == Intencao.PRAGA:
        base = _praga_real(mensagem) or _praga_fallback(mensagem)
        return base, _ctx_praga(base)
    if intencao == Intencao.PLANEJAMENTO:
        base = _planejamento_real(mensagem) or _planejamento_fallback(mensagem)
        return base, _ctx_planejamento(base)
    if intencao == Intencao.CLIMA:
        base = _clima_real()
        return base, _ctx_clima(base)
    if intencao == Intencao.SAUDACAO:
        base = _saudacao_real(produtor_id)
        return base, _ctx_saudacao(base)
    if intencao == Intencao.PERFIL:
        base = _perfil_real(produtor_id)
        return base, _ctx_perfil(base)
    if intencao == Intencao.VENDA:
        base = _venda_real(produtor_id)
        return base, _ctx_venda(base)
    base = _nao_entendi_base()
    return base, _ctx_nao_entendi(mensagem)


@router.post("/chat")
def processar_chat(req: ChatRequest):
    intencao = classificar_intencao(req.mensagem)
    agentico, _ = _responder_agentico(req.mensagem, req.produtor_id)
    if agentico is not None:
        return agentico
    base, ctx = _base_e_ctx(intencao, req.mensagem, req.produtor_id)
    if intencao == Intencao.NAO_ENTENDI:
        try:
            texto = gerar_resposta(intencao.value, req.mensagem, ctx)
        except Exception:
            texto = None
        if texto:
            return {**base, "resposta": texto}
        return {
            "erro": "NAO_ENTENDI",
            "mensagem": "Não consegui entender. Pode reformular?",
            "sugestoes": SUGESTOES,
        }
    return _com_llm(intencao.value, req.mensagem, base, ctx)


def _sse(event: str, payload) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    intencao = classificar_intencao(req.mensagem)

    def gen():
        try:
            db = get_db()
        except Exception:
            db = None
        usadas = []
        try:
            eventos = responder_com_tools_stream(req.mensagem, db, req.produtor_id)
        except Exception:
            eventos = iter([])
        meta_enviada, texto_final = False, []
        try:
            for kind, payload in eventos:
                if kind == "tool":
                    if not meta_enviada:
                        base0, _ = _base_e_ctx(intencao, req.mensagem, req.produtor_id)
                        dados0 = dict(base0.get("dados") or {})
                        yield _sse("meta", {
                            "intencao": base0.get("intencao"),
                            "fonte": _FONTE_AGENT,
                            "data_extracao": base0.get("data_extracao"),
                            "dados": dados0,
                        })
                        meta_enviada = True
                    nome, args = "?", {}
                    if isinstance(payload, dict):
                        nome = payload.get("name", "?")
                        args = payload.get("args", {})
                    usadas.append({"name": nome, "args": args})
                    yield _sse("delta", {"texto": f"🔍 consultando {nome}..."})
                elif kind == "delta" and payload:
                    if not meta_enviada:
                        base0, _ = _base_e_ctx(intencao, req.mensagem, req.produtor_id)
                        dados0 = dict(base0.get("dados") or {})
                        dados0["ferramentas_usadas"] = usadas
                        yield _sse("meta", {
                            "intencao": base0.get("intencao"),
                            "fonte": _FONTE_AGENT,
                            "data_extracao": base0.get("data_extracao"),
                            "dados": dados0,
                        })
                        meta_enviada = True
                    texto_final.append(payload if isinstance(payload, str) else "")
                    yield _sse("delta", {"texto": payload})
        except Exception:
            pass
        if meta_enviada:
            yield _sse("done", {})
            return
        base, ctx = _base_e_ctx(intencao, req.mensagem, req.produtor_id)
        yield _sse("meta", {
            "intencao": base.get("intencao"),
            "fonte": base.get("fonte"),
            "data_extracao": base.get("data_extracao"),
            "dados": base.get("dados") or {},
        })
        vazio = True
        try:
            for chunk in gerar_resposta_stream(intencao.value, req.mensagem, ctx):
                if chunk:
                    vazio = False
                    yield _sse("delta", {"texto": chunk})
        except Exception:
            pass
        if vazio:
            yield _sse("delta", {"texto": base.get("resposta", "")})
        yield _sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    })
