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
from datetime import date
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


# ---------------------------------------------------------------------------
# PRODUÇÃO AGRÍCOLA REAL (IBGE PAM — tabela 1612)
# ---------------------------------------------------------------------------
# Reaproveita a MESMA série já ingerida para preço (tipo "serie_produtor"),
# que guarda `quantidade_t` = toneladas produzidas e `valor_ton` = R$/t.
#
# POR QUE ISSO EXISTE: o card "O que a região mais produz" usava SIGEF, que
# é produção de SEMENTE — não da lavoura. Em São Paulo o SIGEF apontava
# feijão (215 ha de semente) enquanto a produção real é soja (4,7 mi t).
#
# Limite honesto: a PAM do IBGE cobre 5 culturas (arroz, feijão, milho, soja,
# trigo) — NÃO traz cana, café, algodão. Então este card responde "qual das
# cinco PRECISADAS mais o estado produz", e o texto diz isso explicitamente.


def _linhas_serie(col, uf: str, cultura: str | None = None) -> list:
    """Docs da série do produtor (IBGE) para a UF/cultura. Só Mongo."""
    try:
        q: dict = {"tipo": "serie_produtor"}
        u = (uf or "").strip().upper()
        if u:
            q["uf"] = u
        c = canon_cultura(cultura) if cultura else None
        if c:
            q["cultura_canonica"] = c
        try:
            return list(col.find(q, {"_id": 0}))
        except TypeError:
            return list(col.find(q))
    except Exception:
        return []


def producao_uf(db, uf: str, cultura: str | None = None) -> dict:
    """Produção agrícola real por UF (IBGE PAM). Dict ou None.

    Usa o ano mais recente disponível para aquele par (UF, cultura) — assim
    um estado com dado 2025 e outro com 2024 não se comparam errado.
    """
    try:
        if db is None:
            return None
        docs = _linhas_serie(db.precos_conab, uf, cultura)
        if not docs:
            return None
        com_qtd = [d for d in docs if (d.get("quantidade_t") or 0) > 0]
        if not com_qtd:
            return None
        ano = max(int(d.get("ano") or 0) for d in com_qtd)
        do_ano = [d for d in com_qtd if int(d.get("ano") or 0) == ano]
        do_ano.sort(key=lambda d: -(d.get("quantidade_t") or 0))
        topo = do_ano[0]
        total_t = sum(float(d.get("quantidade_t") or 0) for d in do_ano)
        return {
            "uf": (uf or "").upper(),
            "ano": ano,
            "culturaTopo": topo.get("cultura_canonica"),
            "culturaLabel": rotulo_cultura(topo.get("cultura_canonica")),
            "quantidadeTopoT": float(topo.get("quantidade_t") or 0.0),
            "totalT": round(total_t, 2),
            "culturas": [
                {
                    "cultura": d.get("cultura_canonica"),
                    "label": rotulo_cultura(d.get("cultura_canonica")),
                    "quantidade_t": float(d.get("quantidade_t") or 0),
                    "valor_ton": float(d.get("valor_ton") or 0),
                }
                for d in do_ano
            ],
            "cobertura": "arroz, feijão, milho, soja e trigo (culturas da PAM)",
        }
    except Exception as e:
        log.warning("producao_uf falhou uf=%s: %r", uf, e)
        return None

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
        # Marca o escopo para a UI (front/src/app/(app)/mapa/page.tsx ler este texto):
        # sem isso o front dizia "no seu estado (XX)" para um piso nacional.
        escopo = escolhido.get("escopo") or "nacional"
        escopo_limite = (
            "Piso específico da sua região."
            if escopo == "regiao"
            else "Piso de referência nacional — vale igual em todos os estados."
        )
        return {
            "tipo": "pgpm", "cultura": cult_label, "uf": None,
            "valor": escolhido["valor"], "unidade": escolhido.get("unidade", "R$/60kg"),
            "fonte": _fonte(
                escolhido.get("fonte_nome", "CONAB — PGPM (preço mínimo)"),
                periodo,
                ["Preço mínimo oficial, não preço de mercado.",
                 escopo_limite,
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
        # Escopo real: diz "no seu estado" só quando o piso É da região da UF.
        # Senão diz "vale para todo o Brasil" — o produtor precisa saber a
        # diferença entre o que o governo garante AQUI e a referência nacional.
        regional = pgpm.get("escopo") == "regiao" and pgpm.get("regiao")
        escopo_txt = (
            f"No seu estado ({uf}), o governo garante pelo menos {piso_fmt} por saca"
            if regional and uf
            else f"O governo garante no mínimo {piso_fmt} por saca em todo o Brasil"
        )
        obs = (pgpm.get("obs") or "").strip().rstrip(".")
        aviso = (
            f"{escopo_txt} para {cult_label.lower()}"
            + (f". {obs}" if obs else "")
            + ". O preço do dia costuma ficar acima disso — confira no Cepea ao lado "
            "antes de fechar negócio."
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
    """Card Cepea/ESALQ.

    O NÚMERO do dia não pode ser copiado (licença do Cepea) — mas isso não
    significa deixar o card vazio. Entregamos o que É possível ver aqui:
      · o último preço REAL que temos (IBGE PAM, média anual do estado),
      · o ano desse número e a série dos últimos anos,
      · o link do indicador diário para o valor de agora.
    """
    cult_label = rotulo_cultura(canon_cultura(cultura) if cultura else None)
    linhas = _linhas(db, cultura)
    url = _cepea_url(linhas, cultura)

    # Sem cultura escolhida: usa a MAIOR cultura do estado (IBGE) só como
    # referência de leitura, deixando isso explícito no texto — assim o card
    # nunca fica vazio nem finge saber o que o produtor plantou.
    uf_txt = (uf or "").upper()
    exe_topo = False
    if not cultura:
        try:
            top = producao_uf(db, uf) if db is not None else None
            if top and top.get("culturaTopo"):
                cultura = top["culturaTopo"]
                cult_label = f"{top.get('culturaLabel') or rotulo_cultura(cultura)} (maior cultura do estado)"
                linhas = _linhas(db, cultura)
                url = _cepea_url(linhas, cultura) or url
                exe_topo = True
        except Exception:
            pass

    # Último preço real que temos no IBGE (média anual da UF).
    ultimo = None
    serie = []
    try:
        serie = serie_historica(db, cultura, uf, anos=5) or []
        if serie:
            ultimo = serie[-1]
    except Exception:
        serie = []

    if ultimo and uf_txt and uf_txt != "BR":
        brl = ("R$ %.2f" % float(ultimo.get("valor") or 0)).replace(".", ",")
        quem = "Maior cultura do estado. " if exe_topo else ""
        aviso = (
            f"{quem}Último preço real que temos: {brl}/{ultimo.get('unidade', 'saca 60kg')} "
            f"em {ultimo.get('ano')} — preço médio anual recebido pelo produtor em "
            f"{uf_txt} (IBGE). O preço do DIA muda todo dia e só o Cepea publica: "
            f"toque no link para ver o valor de hoje."
        )
    elif ultimo:
        brl = ("R$ %.2f" % float(ultimo.get("valor") or 0)).replace(".", ",")
        aviso = (
            f"Último preço real que temos: {brl}/{ultimo.get('unidade', 'saca 60kg')} "
            f"em {ultimo.get('ano')} (IBGE). O preço do DIA muda todo dia e só o "
            f"Cepea publica — toque no link para ver o valor de hoje."
        )
    else:
        aviso = (
            "O preço do dia muda todo dia e só o Cepea/ESALQ publica esse número. "
            "Toque no link para ver o valor de agora da sua cultura."
        )

    return {
        "tipo": "cepea", "cultura": cult_label, "uf": None,
        "valor": None, "unidade": "indicador diário",
        "referencia_ibge": ultimo,
        "serie_ibge": serie,
        "fonte": _fonte(
            "Cepea/ESALQ — indicador diário (link externo) + IBGE PAM (histórico)",
            f"histórico até {ultimo.get('ano')}" if ultimo else "sem histórico local",
            ["O número do dia pertence ao Cepea: por licença não o copiamos aqui.",
             "O histórico exibido é a média anual do preço recebido pelo produtor "
             "pelo IBGE — não é cotação diária nem preço de mercado.",
             "Para o preço de hoje, abra o indicador oficial."],
            url),
        "data": ultimo.get("ano") if ultimo else None,
        "estado": "link_externo", "url": url,
        "aviso": aviso,
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


def _previsao_ia_ligada() -> bool:
    """A IA é uma LEITURA sobre a série real, não a fonte do número. Pode ser
    desligada (PRECO_PREVISAO_IA=0) e o card continua funcionando com a
    regressão, que é determinística."""
    return os.getenv("PRECO_PREVISAO_IA", "1").strip().lower() not in ("0", "false", "no")


def _ano_alvo_projecao(ultimo_ano_real: int) -> int:
    """Ano que a estimativa pretende olhar.

    Bug corrigido: era `max(ult.ano + 1, ano_de_hoje)`. Em outubro/2026, com
    último oficial 2025, isso devolvia 2026 — um ano quase acabando, inútil
    para quem vai decidir a PRÓXIMA venda. Agora mira a próxima safra
    (PRECO_ANO_ALVO_OFFSET, default +2 anos a partir do último dado oficial),
    mas nunca fica no passado nem inventa salto maior que o configurado.
    """
    try:
        offset = int(float(os.getenv("PRECO_ANO_ALVO_OFFSET", "2")))
    except (TypeError, ValueError):
        offset = 2
    offset = max(1, min(3, offset))
    alvo = int(ultimo_ano_real) + offset
    # Nunca projeta para trás; se o alvo ficou no passado, joga para hoje+1.
    hoje = date.today().year
    if alvo < hoje:
        alvo = hoje + 1
    return alvo


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
    var_anual = None
    var_anual_medio = None
    proj_tendencia = None
    if a is not None:
        # Passo 2: mira a PRÓXIMA safra, não o ano corrente já quase acabado.
        prox_ano = _ano_alvo_projecao(ult["ano"])
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
        # Passo 5: a regressão é SEMPRE calculada e devolvida, mesmo quando a IA
        # responde. Assim existe um número determinístico, auditável e
        # reproduzível na tela — a IA vira leitura, não a única fonte do valor.
        proj_tendencia = {
            "ano": prox_ano,
            "valor_estimado": proj,
            "faixa_min": round(max(0.0, proj - margem), 2),
            "faixa_max": round(proj + margem, 2),
            "unidade": ult["unidade"],
            "origem": "tendencia",
            "racional": None,
        }
        projecao = proj_tendencia
        # Direção: o selo tem que refletir o ÚLTIMO MOVIMENTO REAL, não a
        # reta de 8 anos. Bug corrigido: a inclinação longa é nominal (sobe
        # com a inflação em TODAS as culturas), então as 15 combinações
        # teste/test_producao diziam "subindo" — inclusive o feijão de SP que
        # CAIU 19,4% (298,80 -> 240,90). Isso é o produtor tomar uma decisão
        # de venda pelo contrário. Agora o selo segue o último ano, e a
        # tendência longa vira um número separado, com o valor nominal
        # declarado (não é alta de preço real, é alta de preço nominal).
        if len(serie) >= 2:
            pen = serie[-2]
            var_anual = (ult["valor"] / pen["valor"] - 1.0) if pen["valor"] else 0.0
            var_anual = round(var_anual * 100.0, 1)
            # Faixa morta de ±3%: dentro dela o preço "está parado", e dizer
            # "subindo" seria leitura de ruído.
            if var_anual > 3:
                direcao = "subindo"
            elif var_anual < -3:
                direcao = "caindo"
            else:
                direcao = "estável"
        else:
            var_anual = None
        # Inclinação nominal da reta (só para contexto, com aviso explícito).
        var_anual_medio = None
        if a is not None and media_rec:
            var_anual_medio = round((a / media_rec) * 100.0, 1)

        # Previsão por IA: usa a série REAL como entrada. É COMPLEMENTO da
        # regressão, não substituto — se desligar (PRECO_PREVISAO_IA=0) ou se
        # falhar, o número determinístico da regressão continua na tela.
        if _previsao_ia_ligada():
            try:
                from .llm import prever_preco_ia
                cult_label = rotulo_cultura(canon_cultura(cultura))
                ia = prever_preco_ia(cult_label, (uf or "").upper(), ult["unidade"],
                                     serie, prox_ano, db=db)
                if ia and ia.get("valor_estimado"):
                    # Mesmo clamp de realidade aplicado à IA: ela usa a série real,
                    # mas ainda assim não deixamos a estimativa fugir do último preço.
                    ia["valor_estimado"] = round(min(max(ia["valor_estimado"], max(0.0, piso)), teto), 2)
                    if ia.get("faixa_min") is not None:
                        ia["faixa_min"] = round(min(max(ia["faixa_min"], 0.0), ia["valor_estimado"]), 2)
                    if ia.get("faixa_max") is not None:
                        ia["faixa_max"] = round(max(ia["faixa_max"], ia["valor_estimado"]), 2)
                    ia["valor_tendencia"] = (proj_tendencia or {}).get("valor_estimado")
                    projecao = ia
            except Exception as e:
                log.info("previsao IA indisponivel, segue regressao: %r", e)

    por_ia = bool(projecao and projecao.get("origem") == "ia")
    como = "pela IA, a partir da série real do IBGE" if por_ia else "pela tendência dos últimos anos"

    # Defasagem: o IBGE publica com atraso, então a estimativa olha para a
    # PRÓXIMA safra. O aviso precisa dizer isso — antes só aparecia com 2+ anos
    # de defasagem, ou seja NUNCA.
    aviso = f"Estimativa feita {como}. É apoio ao planejamento, não garantia de preço."
    if projecao:
        defasagem = projecao["ano"] - ult["ano"]
        ano_corrente = date.today().year
        if projecao["ano"] <= ano_corrente:
            aviso = (f"Último preço oficial do IBGE: {ult['ano']}. A estimativa para "
                     f"{projecao['ano']} foi feita {como}, mas esse ano já passou — use-a como "
                     f"histórico, não como previsão. É apoio ao planejamento, não garantia de preço.")
        elif projecao["ano"] == ano_corrente:
            aviso = (f"Último preço oficial do IBGE: {ult['ano']}, a média anual que o produtor "
                     f"recebeu na sua região. A estimativa para {projecao['ano']} foi feita {como} — "
                     f"como o ano já está em andamento, ela serve mais como referência de patamar "
                     f"do que como previsão fechada. É apoio ao planejamento, não garantia de preço.")
        else:
            aviso = (f"O último preço oficial do IBGE é de {ult['ano']}. Esta é uma estimativa "
                     f"para a próxima safra ({projecao['ano']}), feita {como} olhando "
                     f"{defasagem} anos à frente do dado real — por isso a faixa é larga. "
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
        # Variação do ÚLTIMO ano em % (base do selo "subindo/caindo").
        "variacao_ultimo_ano": var_anual,
        # Inclinação NOMINAL da reta (%/ano) — contexto, não previsão.
        "variacao_media_anual": var_anual_medio,
        # Passo 5: regressão sempre presente. É o número DETERMINÍSTICO — a IA
        # pode variar, esta não. O front mostra as duas lado a lado.
        "projecao_tendencia": proj_tendencia,
        "projecao": projecao,
        "serie": serie,
        "fonte": "IBGE — Produção Agrícola Municipal (PAM), tabela 1612",
        "periodicidade": "valor médio ANUAL por UF (valor da produção ÷ quantidade)",
        "aviso": aviso,
    }
