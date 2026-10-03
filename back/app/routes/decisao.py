"""GET /api/decisao-dia — a "Decisão do dia" do produtor, por IA (RAG).

Junta, para a cultura e o município do produtor, tudo que o sistema sabe HOJE:
  · Clima real (Open-Meteo): chuva recente e eventos à frente (geada, calor, chuva)
  · Janela de plantio (ZARC)
  · Preço e tendência (IBGE/PGPM)
  · Risco histórico (seguro rural / PSR)
  · Memória da conversa (o que o produtor já contou)

Monta um contexto de texto com esses blocos REAIS e pede ao LLM uma recomendação
curta e acionável ("o que fazer hoje"). Sem chave de IA ou sem rede, cai num
resumo determinístico montado dos próprios dados — nunca inventa, nunca fica vazio.

Nunca raise: cada bloco falha para "sem dado" e a decisão se adapta ao que há.
"""
import logging
from datetime import date

from fastapi import APIRouter, Query

from ..db import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Decisao"])

IBGE_DEFAULT = "3503208"  # Araraquara/SP — mesmo default do chat


def _perfil(db, produtor_id, ibge, cultura, uf):
    """Resolve cultura/ibge/uf: primeiro o que veio na query, senão o perfil salvo."""
    nome_mun = None
    if db is not None and produtor_id and not (ibge and cultura):
        try:
            doc = db.produtores.find_one({"id": produtor_id}) or {}
            lavs = doc.get("lavouras") or []
            if not cultura and lavs:
                cultura = (lavs[0] or {}).get("cultura")
            ibge = ibge or doc.get("cod_ibge") or doc.get("codigo_ibge")
            uf = uf or doc.get("uf")
            nome_mun = doc.get("municipio")
        except Exception as e:
            log.warning("perfil decisao falhou: %r", e)
    return (ibge or None), (cultura or None), (uf or "SP").upper(), nome_mun


def _bloco_clima(db, ibge, uf, cultura_label):
    try:
        from ..clima import buscar_previsao, detectar_eventos
        prev = buscar_previsao(db, ibge=ibge, uf=uf)
        if not prev:
            return None, []
        eventos = detectar_eventos(prev, cultura_label)
        return prev, eventos
    except Exception as e:
        log.warning("bloco clima falhou: %r", e)
        return None, []


def _bloco_zarc(db, ibge, cultura):
    if db is None or not ibge or not cultura:
        return None
    try:
        from ..tools import dispatch
        z = dispatch(db, "buscar_janelas_zarc", {"cultura": cultura, "ibge": ibge})
        janelas = (z or {}).get("janelas") or []
        return janelas[0] if janelas else None
    except Exception as e:
        log.warning("bloco zarc falhou: %r", e)
        return None


def _bloco_preco(db, cultura, uf):
    if not cultura:
        return None
    try:
        from ..precos_dados import resumo_tendencia
        t = resumo_tendencia(db, cultura, uf)
        return t if t.get("estado") == "disponivel" else None
    except Exception as e:
        log.warning("bloco preco falhou: %r", e)
        return None


def _ctx_texto(cultura_label, local_nome, uf, prev, eventos, zarc, preco, mem):
    """Monta o contexto REAL em texto para o LLM."""
    linhas = [
        f"Produtor de {cultura_label} em {local_nome or uf}. Hoje é {date.today().strftime('%d/%m/%Y')}.",
    ]
    if eventos:
        linhas.append("Clima previsto (fonte Open-Meteo):")
        for e in eventos:
            linhas.append(f"- {e['titulo']}: {e['mensagem']}")
    elif prev:
        linhas.append("Clima: sem eventos extremos previstos para os próximos dias.")
    else:
        linhas.append("Clima: não foi possível consultar a previsão agora.")

    if zarc:
        abertos = zarc.get("abertos") or []
        linhas.append(
            f"Janela de plantio (ZARC): {len(abertos)} períodos indicados; "
            f"risco mínimo {zarc.get('risco_min')}%."
        )
    if preco:
        ult = preco.get("ultimo") or {}
        proj = preco.get("projecao") or {}
        linhas.append(
            f"Preço ao produtor (IBGE): último {ult.get('valor')} em {ult.get('ano')}; "
            f"tendência {preco.get('direcao')}"
            + (f"; estimativa p/ {proj.get('ano')}: {proj.get('valor_estimado')}." if proj else ".")
        )
    if mem:
        linhas.append(mem.strip())

    linhas.append(
        "Gere a DECISÃO DO DIA: 2 a 4 frases, linguagem simples de produtor, dizendo o que "
        "fazer hoje/nos próximos dias com base no que for mais urgente acima (clima manda quando "
        "há evento). Depois liste de 1 a 3 ações curtas começando com verbo. Nunca invente dado; "
        "se algo faltar, foque no que há. Cite as fontes no fim."
    )
    return "\n".join(linhas)


def _acoes_das_evidencias(eventos, zarc, preco):
    """Ações determinísticas (fallback sem IA), direto dos dados reais."""
    acoes = []
    for e in eventos:
        if e["tipo"] == "geada":
            acoes.append("Proteja as áreas baixas da geada e não irrigue à noite nos dias frios.")
        elif e["tipo"] == "onda_calor":
            acoes.append("Reforce a rega no começo e no fim do dia por causa do calor.")
        elif e["tipo"] == "chuva_forte":
            acoes.append("Segure pulverização e colheita no dia de chuva forte e cuide da drenagem.")
        elif e["tipo"] == "veranico":
            acoes.append("Planeje a irrigação: vem um período seco pela frente.")
        elif e["tipo"] == "chuva_recente":
            acoes.append("Espere o solo firmar antes de entrar com máquina, para não compactar.")
    if zarc and not acoes:
        acoes.append("Confira a janela de plantio do ZARC antes de semear.")
    if preco:
        acoes.append("Compare o preço do dia (Cepea) com o piso antes de negociar a venda.")
    return acoes[:3]


def _decisao_heuristica(cultura_label, eventos, zarc, preco, prev):
    """Texto determinístico quando não há IA. Honesto, montado dos dados."""
    if eventos:
        maior = sorted(eventos, key=lambda e: {"alta": 0, "media": 1, "baixa": 2}.get(e.get("severidade"), 1))[0]
        corpo = f"Atenção para o clima: {maior['mensagem']}"
    elif prev:
        corpo = (f"O tempo nos próximos dias está sem extremos para {cultura_label.lower()}. "
                 f"Bom momento para seguir o manejo normal e acompanhar a lavoura.")
    else:
        corpo = (f"Não consegui ver a previsão do tempo agora. Acompanhe o céu e, se tiver dúvida "
                 f"sobre plantio ou venda de {cultura_label.lower()}, me pergunte no chat.")
    fontes = []
    if eventos or prev:
        fontes.append("Open-Meteo")
    if zarc:
        fontes.append("ZARC/MAPA")
    if preco:
        fontes.append("IBGE")
    return corpo, fontes


@router.get("/decisao-dia")
def decisao_dia(produtor_id: str | None = None, ibge: str | None = None,
                cultura: str | None = None, uf: str | None = None):
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em /decisao-dia: %r", e)
        db = None

    ibge, cultura, uf, nome_mun = _perfil(db, produtor_id, ibge, cultura, uf)
    try:
        from ..precos_dados import rotulo_cultura, canon_cultura
        cultura_label = rotulo_cultura(canon_cultura(cultura)) if cultura else "sua cultura"
    except Exception:
        cultura_label = (cultura or "sua cultura").capitalize()

    prev, eventos = _bloco_clima(db, ibge, uf, cultura_label)
    zarc = _bloco_zarc(db, ibge, cultura)
    preco = _bloco_preco(db, cultura, uf)
    local_nome = (prev or {}).get("local", {}).get("nome") or nome_mun

    # memória da conversa (RAG)
    mem = ""
    if db is not None and produtor_id:
        try:
            from ..memoria import contexto_memorias
            mem = contexto_memorias(db, produtor_id) or ""
        except Exception as e:
            log.warning("memoria decisao falhou: %r", e)

    # 1) tenta a IA (RAG one-shot)
    texto_ia = None
    try:
        from ..llm import gerar_resposta, _timeout_dados
        ctx = _ctx_texto(cultura_label, local_nome, uf, prev, eventos, zarc, preco, mem)
        texto_ia = gerar_resposta("DECISAO_DIA", "qual a decisão do dia para a minha lavoura?",
                                  ctx, timeout=_timeout_dados())
    except Exception as e:
        log.warning("llm decisao falhou: %r", e)

    acoes = _acoes_das_evidencias(eventos, zarc, preco)
    corpo_fb, fontes = _decisao_heuristica(cultura_label, eventos, zarc, preco, prev)

    if texto_ia:
        resposta, origem = texto_ia, "ia"
    else:
        resposta, origem = corpo_fb, "regras"

    # severidade geral: a maior entre os eventos de clima
    sev = "baixa"
    for e in eventos:
        if e.get("severidade") == "alta":
            sev = "alta"
            break
        if e.get("severidade") == "media":
            sev = "media"

    return {
        "resposta": resposta,
        "origem": origem,
        "severidade": sev if eventos else "info",
        "acoes": acoes,
        "fontes": fontes or ["AgroPilot"],
        "local": {"nome": local_nome, "uf": uf},
        "cultura": cultura_label,
        "tem_clima": bool(prev),
        "eventos_clima": [
            {"tipo": e["tipo"], "titulo": e.get("titulo"), "severidade": e.get("severidade"),
             "mensagem": e["mensagem"], "janela": e.get("janela")}
            for e in eventos
        ],
        "data": date.today().isoformat(),
    }
