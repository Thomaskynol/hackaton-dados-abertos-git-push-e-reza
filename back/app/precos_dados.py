"""Camada de dados de PREÇOS de referência (CONAB/PGPM + Cepea link).

Lê o dataset real gerado por correlacao/precos_conab.py. Duas origens, nesta
ordem de preferência:
  1. Mongo (coleção `precos_conab`), quando get_db() devolve conexão.
  2. Arquivo correlacao/output/precos_conab.jsonl (fallback que SEMPRE funciona,
     mesmo sem Mongo/Docker — essencial para rodar local e em demo).

REGRA DE OURO: só devolve número com {valor, unidade, fonte, safra}. Sem valor
oficial confirmado -> estado "pendente"/"sem_cotacao" honesto, nunca estimativa.
Cepea/ESALQ nunca traz número: só o LINK oficial (restrição de licença).

Nunca raise: qualquer falha -> fallback honesto (pendente), nunca quebra a rota.
"""
import json
import logging
import os
import time
import unicodedata
from functools import lru_cache

log = logging.getLogger(__name__)

# Caminho do dataset gerado pelo ingestor (relativo à raiz do repo).
_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(os.path.dirname(_AQUI))  # back/app -> back -> raiz
_JSONL = os.path.join(_RAIZ, "correlacao", "output", "precos_conab.jsonl")

# --- Atualização VIVA da série (busca o dado mais recente do IBGE sob demanda) ---
# Liga/desliga por env (IBGE_AUTO_UPDATE=0 para desligar em ambiente sem rede).
# TTL evita martelar a API: só revalida uma cultura a cada N dias.
def _auto_update_ligado():
    return os.getenv("IBGE_AUTO_UPDATE", "1").strip().lower() not in ("0", "false", "no")


def _ttl_segundos():
    try:
        return max(3600, int(float(os.getenv("IBGE_TTL_DIAS", "7")) * 86400))
    except (TypeError, ValueError):
        return 7 * 86400


def _ano_mais_recente_no_db(db, cult):
    """Maior ano de serie_produtor já salvo para a cultura. 0 se não houver.

    Itera e pega o máximo (não depende de sort — funciona no Mongo e no fake).
    """
    try:
        cur = db.precos_conab.find(
            {"cultura_canonica": cult, "tipo": "serie_produtor"}, {"_id": 0, "ano": 1})
        anos = []
        for d in cur:
            try:
                anos.append(int(d.get("ano")))
            except (TypeError, ValueError):
                continue
        return max(anos) if anos else 0
    except Exception:
        return 0


def _marcar_checagem(db, cult, ok, ultimo_ano):
    try:
        db.precos_meta.update_one(
            {"_id": f"serie:{cult}"},
            {"$set": {"last_check_ts": int(time.time()), "last_ok": bool(ok),
                      "ultimo_ano": int(ultimo_ano or 0)}},
            upsert=True)
    except Exception:
        pass


def _precisa_revalidar(db, cult):
    try:
        meta = db.precos_meta.find_one({"_id": f"serie:{cult}"})
    except Exception:
        meta = None
    if not meta:
        return True
    return (int(time.time()) - int(meta.get("last_check_ts") or 0)) > _ttl_segundos()


def atualizar_serie_viva(db, cultura):
    """Best-effort: busca no IBGE os anos que faltam e grava no Mongo (upsert).

    Só roda se: auto-update ligado, há Mongo, a cultura tem PAM e o TTL venceu.
    Nunca raise; nunca bloqueia a resposta por muito tempo (timeout curto).
    """
    if not _auto_update_ligado() or db is None:
        return
    cult = canon_cultura(cultura) if cultura else None
    if not cult:
        return
    try:
        from .precos_ibge import cultura_tem_ibge, ultimo_ano_disponivel, buscar_serie
    except Exception:
        return
    if not cultura_tem_ibge(cult):
        return
    if not _precisa_revalidar(db, cult):
        return

    try:
        ultimo_api = ultimo_ano_disponivel()
    except Exception:
        ultimo_api = None
    if not ultimo_api:
        _marcar_checagem(db, cult, False, _ano_mais_recente_no_db(db, cult))
        return

    ultimo_db = _ano_mais_recente_no_db(db, cult)
    if ultimo_api <= ultimo_db:
        _marcar_checagem(db, cult, True, ultimo_db)  # já estamos em dia
        return

    anos_novos = list(range(ultimo_db + 1, ultimo_api + 1)) if ultimo_db else None
    docs = buscar_serie(cult, anos=anos_novos)
    if not docs:
        _marcar_checagem(db, cult, False, ultimo_db)
        return
    gravados = 0
    for d in docs:
        try:
            db.precos_conab.update_one(
                {"cultura_canonica": d["cultura_canonica"], "tipo": "serie_produtor",
                 "uf": d["uf"], "ano": d["ano"]},
                {"$set": d}, upsert=True)
            gravados += 1
        except Exception:
            continue
    _carregar_arquivo.cache_clear()  # invalida cache de arquivo p/ refletir o novo
    log.info("serie viva: %s +%d docs (ate %s)", cult, gravados, ultimo_api)
    _marcar_checagem(db, cult, True, ultimo_api)

# Rótulos amigáveis por cultura canônica (espelha o front CULTURA_LABEL).
CULTURA_LABEL = {
    "milho": "Milho", "soja": "Soja", "feijao": "Feijão",
    "arroz": "Arroz", "trigo": "Trigo", "cafe": "Café arábica",
    "cafe_conilon": "Café conilon",
}

CEPEA_LINK_PADRAO = "https://www.cepea.esalq.usp.br/br"

# UF -> macrorregião (preço PGPM pode variar por região).
_REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
}
UF_REGIAO = {uf: reg for reg, ufs in _REGIOES.items() for uf in ufs}


def _norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def canon_cultura(nome):
    """'Feijão carioca' -> 'feijao'. Primeiro token, minúsculo, sem acento."""
    base = _norm(nome).split()
    return base[0].replace("-", "_") if base else ""


def rotulo_cultura(culturaId):
    if not culturaId:
        return "sua cultura"
    return CULTURA_LABEL.get(culturaId, str(culturaId).capitalize())


@lru_cache(maxsize=1)
def _carregar_arquivo():
    """Lê o JSONL uma vez (cacheado). Lista vazia se ausente."""
    docs = []
    try:
        with open(_JSONL, encoding="utf-8") as fh:
            for linha in fh:
                linha = linha.strip()
                if linha:
                    docs.append(json.loads(linha))
    except Exception:
        return []
    return docs


def _linhas(db, cultura):
    """Todas as linhas de preço de uma cultura. Mongo primeiro, senão arquivo."""
    cult = canon_cultura(cultura)
    if not cult:
        return []
    if db is not None:
        try:
            docs = list(db.precos_conab.find(
                {"cultura_canonica": cult}, {"_id": 0}))
            if docs:
                return docs
        except Exception:
            pass
    return [d for d in _carregar_arquivo() if d.get("cultura_canonica") == cult]


def _escolher_pgpm(linhas, uf):
    """Melhor linha PGPM para a UF: região específica > nacional."""
    pgpm = [l for l in linhas if l.get("tipo") == "pgpm" and l.get("valor") is not None]
    if not pgpm:
        return None
    regiao = UF_REGIAO.get((uf or "").strip().upper())
    por_regiao = [l for l in pgpm if l.get("regiao") == regiao]
    if por_regiao:
        return por_regiao[0]
    nacionais = [l for l in pgpm if l.get("escopo") == "nacional"]
    return nacionais[0] if nacionais else pgpm[0]


def _cepea_url(linhas, cultura):
    for l in linhas:
        if l.get("cepea_url"):
            return l["cepea_url"]
    return CEPEA_LINK_PADRAO


def _fonte(nome, periodo="", limitacoes=None, url=None):
    f = {"nome": nome}
    if periodo:
        f["periodo"] = periodo
    if url:
        f["url"] = url
    if limitacoes:
        f["limitacoes"] = limitacoes
    return f


def bloco_pgpm(db, cultura, uf):
    """Card 'Piso Garantido (PGPM)'. Valor real quando houver, senão pendente."""
    cult_label = rotulo_cultura(canon_cultura(cultura) if cultura else None)
    linhas = _linhas(db, cultura)
    escolhido = _escolher_pgpm(linhas, uf)
    if escolhido:
        periodo = f"safra {escolhido.get('safra')}" if escolhido.get("safra") else "safra vigente"
        return {
            "tipo": "pgpm", "cultura": cult_label, "uf": None,
            "valor": escolhido["valor"], "unidade": escolhido.get("unidade", "R$/60kg"),
            "fonte": _fonte(
                escolhido.get("fonte_nome", "CONAB — PGPM (preço mínimo)"),
                periodo,
                ["Preço mínimo oficial, não preço de mercado.",
                 "Serve de piso para planejar — não diz quando vender."],
                escolhido.get("fonte_url"),
            ),
            "data": escolhido.get("safra"), "estado": "disponivel",
            "aviso": "Preço mínimo garantido pelo governo. É o piso para o seu planejamento — se o mercado pagar abaixo disso, há instrumentos de apoio (PGPM).",
        }
    return {
        "tipo": "pgpm", "cultura": cult_label, "uf": None,
        "valor": None, "unidade": "R$/60kg",
        "fonte": _fonte("CONAB — PGPM (preço mínimo)", "safra vigente (quando publicado)",
                        ["Preço mínimo oficial, não preço de mercado.",
                         "Esta cultura ainda não tem piso publicado na base."]),
        "data": None, "estado": "pendente",
        "aviso": "Preço mínimo de referência do governo. Serve de piso para planejar — não diz quando vender.",
    }


def bloco_mercado(db, cultura, uf):
    """Card 'Contexto da sua região'.

    Não existe série de preço de mercado DIÁRIO público por UF que a gente possa
    redistribuir. Em vez de deixar "aguardando ingestão" (jargão, e inútil para o
    produtor), damos um contexto REAL e honesto: usamos o piso PGPM como régua de
    preço e, quando houver, a escala de produção da região (SIGEF) — deixando claro
    que o preço do dia vem do Cepea ao lado. Nunca inventa cotação.
    """
    cult_label = rotulo_cultura(canon_cultura(cultura) if cultura else None)
    pgpm = _escolher_pgpm(_linhas(db, cultura), uf)

    if pgpm:
        piso = pgpm["valor"]
        unidade = pgpm.get("unidade", "R$/60kg")
        piso_fmt = ("R$ %.2f" % piso).replace(".", ",")
        aviso = (
            f"No seu estado, o governo garante pelo menos {piso_fmt} por saca para o "
            f"{cult_label.lower()}. O preço do dia costuma ficar acima disso — confira no Cepea ao lado "
            f"antes de fechar negócio."
        )
        return {
            "tipo": "conab_mercado", "cultura": cult_label, "uf": uf,
            "valor": None, "unidade": unidade,
            "referencia_piso": piso,
            "fonte": _fonte("CONAB / MAPA — preço mínimo como referência da região",
                            f"safra {pgpm.get('safra')}" if pgpm.get("safra") else "safra vigente",
                            ["O número que mostramos é o piso garantido, não o preço do dia.",
                             "O preço do dia, atualizado, está no indicador do Cepea ao lado."],
                            pgpm.get("fonte_url")),
            "data": pgpm.get("safra"), "estado": "referencia",
            "aviso": aviso,
        }

    return {
        "tipo": "conab_mercado", "cultura": cult_label, "uf": uf,
        "valor": None, "unidade": "R$/60kg",
        "fonte": _fonte("CONAB — contexto de mercado da região", "",
                        ["Ainda não temos um piso de referência publicado para esta cultura.",
                         "O preço do dia está no indicador do Cepea ao lado."]),
        "data": None, "estado": "pendente",
        "aviso": "Para esta cultura, veja o preço do dia no Cepea ao lado — é a fonte mais atual.",
    }


def bloco_cepea(db, cultura, uf):
    """Card Cepea/ESALQ: SÓ link externo, nunca número (licença)."""
    cult_label = rotulo_cultura(canon_cultura(cultura) if cultura else None)
    linhas = _linhas(db, cultura)
    url = _cepea_url(linhas, cultura)
    return {
        "tipo": "cepea", "cultura": cult_label, "uf": None,
        "valor": None, "unidade": "indicador diário",
        "fonte": _fonte("Cepea/ESALQ — indicador diário (link externo)", "",
                        ["O número pertence ao Cepea; abrimos o site oficial em vez de copiar."],
                        url),
        "data": None, "estado": "link_externo", "url": url,
        "aviso": "Abre o preço do dia no site oficial do Cepea/ESALQ.",
    }


def precos_da_uf(db, cultura, uf):
    """Os três cards, nesta ordem: PGPM -> CONAB mercado -> Cepea."""
    return [bloco_pgpm(db, cultura, uf), bloco_mercado(db, cultura, uf), bloco_cepea(db, cultura, uf)]


# ------------------------------------------------------------------
# Série histórica de preço ao produtor (IBGE/PAM) + tendência/predição.
# É o que dá à IA base real para projetar — não um número solto.
# ------------------------------------------------------------------

def serie_historica(db, cultura, uf, anos=None):
    """Série anual (ano -> R$/saca) do preço ao produtor para cultura+UF.

    Preferência por UF; se a UF não tiver dado, usa a média nacional por ano.
    Retorna lista ordenada [{"ano": int, "valor": float, "unidade": str}].
    """
    cult = canon_cultura(cultura) if cultura else None
    if not cult:
        return []
    # Mantém a série viva: busca anos novos do IBGE sob demanda (best-effort).
    try:
        atualizar_serie_viva(db, cultura)
    except Exception:
        pass
    linhas = [l for l in _linhas(db, cultura) if l.get("tipo") == "serie_produtor"]
    if not linhas:
        return []
    uf = (uf or "").strip().upper()
    da_uf = [l for l in linhas if (l.get("uf") or "").upper() == uf and l.get("valor") is not None]

    if da_uf:
        base = da_uf
        pontos = {int(l["ano"]): float(l["valor"]) for l in base if l.get("ano") is not None}
        unidade = base[0].get("unidade", "R$/60kg")
    else:
        # média nacional por ano (contexto quando a UF não tem a cultura)
        por_ano = {}
        unidade = linhas[0].get("unidade", "R$/60kg")
        for l in linhas:
            if l.get("ano") is None or l.get("valor") is None:
                continue
            por_ano.setdefault(int(l["ano"]), []).append(float(l["valor"]))
        pontos = {a: round(sum(v) / len(v), 2) for a, v in por_ano.items()}

    serie = [{"ano": a, "valor": round(pontos[a], 2), "unidade": unidade}
             for a in sorted(pontos)]
    if anos:
        serie = serie[-int(anos):]
    return serie


def _tendencia_linear(serie):
    """Regressão linear simples (mínimos quadrados) sobre (ano, valor).

    Retorna (coef_angular_por_ano, intercepto) ou (None, None) se insuficiente.
    """
    pts = [(p["ano"], p["valor"]) for p in serie if p.get("valor") is not None]
    n = len(pts)
    if n < 3:
        return None, None
    sx = sum(x for x, _ in pts)
    sy = sum(y for _, y in pts)
    sxx = sum(x * x for x, _ in pts)
    sxy = sum(x * y for x, y in pts)
    denom = n * sxx - sx * sx
    if denom == 0:
        return None, None
    a = (n * sxy - sx * sy) / denom       # inclinação (R$/ano)
    b = (sy - a * sx) / n                  # intercepto
    return a, b


def resumo_tendencia(db, cultura, uf):
    """Resumo honesto da série para alimentar a análise/predição da IA.

    Devolve dicionário com último preço, média recente, variação, mínimo/máximo,
    tendência (subindo/caindo/estável) e uma PROJEÇÃO simples para o próximo ano
    (regressão linear), sempre com faixa de incerteza e aviso. Nunca promete.
    """
    serie = serie_historica(db, cultura, uf)
    if len(serie) < 3:
        return {"estado": "insuficiente", "serie": serie}

    valores = [p["valor"] for p in serie]
    ult = serie[-1]
    recentes = valores[-5:]
    media_rec = round(sum(recentes) / len(recentes), 2)
    menor = min(serie, key=lambda p: p["valor"])
    maior = max(serie, key=lambda p: p["valor"])

    a, b = _tendencia_linear(serie[-8:] if len(serie) >= 8 else serie)
    projecao = None
    direcao = "estável"
    if a is not None:
        # Projeta sempre 1 ano à frente do ÚLTIMO DADO REAL — assim a estimativa
        # fica ancorada no presente e perto da realidade (nunca extrapola anos a
        # fio no escuro). Se por acaso esse ano já passou, avança para o ano que vem.
        from datetime import date as _date
        prox_ano = max(ult["ano"] + 1, _date.today().year)
        proj = a * prox_ano + b
        # faixa de incerteza: base = dispersão dos resíduos recentes, crescendo
        # conforme o ano projetado se afasta do último dado real.
        resid = [abs(p["valor"] - (a * p["ano"] + b)) for p in serie[-8:]]
        margem = round(sum(resid) / len(resid), 2) if resid else 0.0
        anos_adiante = max(1, prox_ano - ult["ano"])
        margem = round(margem * (1 + 0.15 * (anos_adiante - 1)), 2)
        # Clamp de realidade: a projeção não pode se afastar mais de ~35% por ano
        # do último preço real. Impede que a reta de longo prazo ignore uma queda
        # ou alta recente e cuspa um número irreal.
        teto = ult["valor"] * (1 + 0.35 * anos_adiante)
        piso = ult["valor"] * (1 - 0.35 * anos_adiante)
        proj = round(min(max(proj, max(0.0, piso)), teto), 2)
        projecao = {
            "ano": prox_ano,
            "valor_estimado": proj,
            "faixa_min": round(max(0.0, proj - margem), 2),
            "faixa_max": round(proj + margem, 2),
            "unidade": ult["unidade"],
            "origem": "tendencia",
            "racional": None,
        }
        # direção pela inclinação relativa à média recente
        if media_rec and abs(a) / media_rec > 0.02:
            direcao = "subindo" if a > 0 else "caindo"

        # Previsão por IA: usa a série REAL como entrada. Se houver chave e o
        # modelo responder, ela substitui a regressão (que vira o fallback).
        try:
            from .llm import prever_preco_ia
            cult_label = rotulo_cultura(canon_cultura(cultura))
            ia = prever_preco_ia(cult_label, (uf or "").upper(), ult["unidade"], serie, prox_ano)
            if ia and ia.get("valor_estimado"):
                # Mesmo clamp de realidade aplicado à IA: ela usa a série real,
                # mas ainda assim não deixamos a estimativa fugir do último preço.
                ia["valor_estimado"] = round(min(max(ia["valor_estimado"], max(0.0, piso)), teto), 2)
                if ia.get("faixa_min") is not None:
                    ia["faixa_min"] = round(min(max(ia["faixa_min"], 0.0), ia["valor_estimado"]), 2)
                if ia.get("faixa_max") is not None:
                    ia["faixa_max"] = round(max(ia["faixa_max"], ia["valor_estimado"]), 2)
                projecao = ia
        except Exception:
            pass

    por_ia = bool(projecao and projecao.get("origem") == "ia")
    como = "pela IA, a partir da série real do IBGE" if por_ia else "pela tendência dos últimos anos"
    aviso = (f"Estimativa feita {como}. É apoio ao planejamento, não garantia de preço.")
    if projecao and (projecao["ano"] - ult["ano"]) >= 2:
        aviso = (f"O dado oficial mais recente do IBGE é de {ult['ano']}; a estimativa para "
                 f"{projecao['ano']} foi feita {como}, com margem maior por olhar mais anos à frente. "
                 f"É apoio ao planejamento, não garantia de preço.")

    return {
        "estado": "disponivel",
        "cultura": rotulo_cultura(canon_cultura(cultura)),
        "uf": (uf or "").upper(),
        "unidade": ult["unidade"],
        "ultimo": ult,
        "media_recente": media_rec,
        "menor": menor,
        "maior": maior,
        "direcao": direcao,
        "projecao": projecao,
        "serie": serie,
        "fonte": "IBGE — Produção Agrícola Municipal (PAM)",
        "aviso": aviso,
    }
