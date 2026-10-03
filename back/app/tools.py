"""Ferramentas reais do agente (Mongo `agropilot`).

OpenAI-compatible function schemas + dispatch. Nunca raise, nunca loga chave.
Cap: limite<=5, strings<=2000 chars.
"""
import re
import unicodedata

SOLO_MAP = {1: "arenoso", 2: "media", 3: "argiloso",
            11: "ad1", 12: "ad2", 13: "ad3", 14: "ad4", 15: "ad5", 16: "ad6"}
MANEJO_MAP = {1: "sequeiro", 2: "irrigado", 3: "irrigado_geada"}

_MAX_STR = 2000
_MAX_LIMITE = 5


def _cap(s):
    if isinstance(s, str) and len(s) > _MAX_STR:
        return s[:_MAX_STR]
    return s


def _limite(v, default=3):
    try:
        n = int(v) if v is not None else default
    except (ValueError, TypeError):
        n = default
    return max(1, min(_MAX_LIMITE, n))


def _norm(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())


def _canon_cultura(nome):
    base = _norm(nome).split()
    return base[0].replace("-", "_") if base else ""


def _norm_solo(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return SOLO_MAP.get(int(str(v).strip()))
    except (ValueError, TypeError):
        pass
    return _norm(v) or None


def _norm_manejo(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    try:
        return MANEJO_MAP.get(int(str(v).strip()))
    except (ValueError, TypeError):
        pass
    return _norm(v) or None


def _ibge7(codigo):
    s = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    if len(s) > 7:
        s = s[:-1]
    return s


def _col(db, name):
    if db is None:
        return None
    try:
        c = getattr(db, name, None)
        if c is not None:
            return c
    except Exception:
        pass
    try:
        if isinstance(db, dict):
            return db.get(name)
    except Exception:
        pass
    try:
        return db[name]
    except Exception:
        return None


def _find_one(col, query, proj=None):
    try:
        if proj is not None:
            try:
                return col.find_one(query, proj)
            except TypeError:
                return col.find_one(query)
        return col.find_one(query)
    except Exception:
        return None


def _find_many(col, query, sort=None, limit=5):
    try:
        try:
            cur = col.find(query, {"_id": 0})
        except TypeError:
            cur = col.find(query)
    except Exception:
        return []
    try:
        if sort:
            try:
                cur = cur.sort(sort)
            except Exception:
                try:
                    cur = cur.sort(sort[0][0], sort[0][1])
                except Exception:
                    pass
        try:
            cur = cur.limit(limit)
        except Exception:
            pass
        return list(cur)[:limit]
    except Exception:
        try:
            return list(cur)[:limit]
        except Exception:
            return []


def _t_buscar_municipio(db, args):
    col = _col(db, "municipios")
    if col is None:
        return {"erro": "sem colecao municipios"}
    ibge = args.get("ibge") or args.get("cod_ibge")
    if ibge:
        code = _ibge7(ibge)
        if not code:
            return {"erro": "ibge invalido"}
        doc = _find_one(col, {"cod_ibge": code})
        if doc:
            return {"cod_ibge": doc.get("cod_ibge"),
                    "nome": _cap(doc.get("nome")), "uf": doc.get("uf")}
        return {"erro": f"municipio {code} nao encontrado"}
    nome = (args.get("nome") or "").strip()
    uf = (args.get("uf") or "").strip().upper()
    if not nome:
        return {"erro": "informe ibge ou nome+uf"}
    q: dict = {"nome": {"$regex": f"^{re.escape(nome)}$", "$options": "i"}}
    if uf:
        q["uf"] = uf
    doc = _find_one(col, q)
    if doc:
        return {"cod_ibge": doc.get("cod_ibge"),
                "nome": _cap(doc.get("nome")), "uf": doc.get("uf")}
    for d in _find_many(col, {"uf": uf} if uf else {}, limit=6000)[:6000]:
        try:
            if _norm(d.get("nome")) == _norm(nome) and (
                    not uf or (d.get("uf") or "").upper() == uf):
                return {"cod_ibge": d.get("cod_ibge"),
                        "nome": _cap(d.get("nome")), "uf": d.get("uf")}
        except Exception:
            continue
    return {"erro": f"municipio {nome}/{uf} nao encontrado"}


def _t_buscar_janelas_zarc(db, args):
    try:
        from .dados_reais import buscar_janelas
    except Exception:
        try:
            from app.dados_reais import buscar_janelas
        except Exception:
            return {"erro": "sem buscar_janelas"}
    cultura = _canon_cultura(args.get("cultura") or "")
    if not cultura:
        return {"erro": "informe cultura"}
    ibge = _ibge7(args.get("ibge") or args.get("cod_ibge") or "")
    if not ibge:
        return {"erro": "informe ibge"}
    solo = _norm_solo(args.get("solo"))
    manejo = _norm_manejo(args.get("manejo"))
    irrig = None
    if manejo:
        if "irrigado" in manejo:
            irrig = True
        elif "sequeiro" in manejo:
            irrig = False
    lim = _limite(args.get("limite", 3))
    try:
        docs = buscar_janelas(db, cultura, ibge, solo, irrig, lim)
    except Exception:
        return {"erro": "falha zarc"}
    if not docs:
        return {"erro": f"sem janelas ZARC para {cultura} em {ibge}"}
    out = []
    for d in docs[:lim]:
        try:
            out.append({
                "cultura": cultura, "cod_ibge": ibge,
                "solo": d.get("solo_canonico"), "manejo": d.get("manejo_canonico"),
                "ciclo_grupo": d.get("ciclo_grupo"),
                "portaria": _cap(d.get("Portaria")),
                "abertos": list(d.get("abertos") or [])[:36],
                "risco_min": d.get("risco_min"), "risco_max": d.get("risco_max"),
                "dec": {str(k): v for k, v in list((d.get("dec") or {}).items())[:36]},
            })
        except Exception:
            continue
    return {"janelas": out}


def _t_buscar_produtos_agrofit(db, args):
    try:
        from .dados_reais import buscar_produtos, produto_resumo
    except Exception:
        try:
            from app.dados_reais import buscar_produtos, produto_resumo
        except Exception:
            return {"erro": "sem buscar_produtos"}
    cultura = _canon_cultura(args.get("cultura") or "")
    if not cultura:
        return {"erro": "informe cultura"}
    alvo = (args.get("alvo") or None)
    if isinstance(alvo, str):
        alvo = alvo.strip() or None
    so_org = bool(args.get("so_organicos", False))
    max_tox = args.get("max_classe_tox")
    try:
        max_tox = int(max_tox) if max_tox is not None else None
    except (ValueError, TypeError):
        max_tox = None
    lim = _limite(args.get("limite", 5), default=5)
    try:
        docs = buscar_produtos(db, cultura, alvo, limite=lim * 2)
    except Exception:
        return {"erro": "falha agrofit"}
    if not docs:
        return {"erro": f"sem produtos Agrofit para {cultura}"}
    out = []
    for d in docs:
        try:
            if so_org and d.get("organicos") != "S":
                continue
            cx = d.get("classe_toxicologica")
            if max_tox is not None:
                if not isinstance(cx, int) or cx > max_tox:
                    continue
            r = produto_resumo(d)
            out.append({
                "nome": _cap(r.get("nome")),
                "ingrediente": _cap(d.get("ingrediente_ativo")),
                "praga": _cap(d.get("praga_nome_cientifico")),
                "classe": r.get("classe"),
                "organico": r.get("organico"),
            })
            if len(out) >= lim:
                break
        except Exception:
            continue
    if not out:
        return {"erro": "sem produtos no filtro (organico/classe)"}
    return {"produtos": out}


def agregar_psr_uf(db, uf, cultura=None, limite_docs=20000):
    """Agrega o seguro rural (PSR) por UF: total de apólices, perdas pagas e a
    cultura mais segurada. Usado quando não há município selecionado — dá um
    retrato real do estado inteiro em vez de 'sem dado'. Nunca raise.

    Retorna dict pronto ou None se não houver dado para a UF.
    """
    col = _col(db, "psr_agregado")
    uf = (uf or "").strip().upper()
    if col is None or not uf:
        return None
    cult = _canon_cultura(cultura or "") or None
    q = {"uf": uf}
    if cult:
        q["cultura_canonica"] = cult
    try:
        try:
            cur = col.find(q, {"_id": 0})
        except TypeError:
            cur = col.find(q)
        docs = list(cur)[:limite_docs]
    except Exception:
        return None
    if not docs:
        return None
    total_apolices = 0
    total_sinistros = 0
    total_pago = 0.0
    anos = set()
    por_cultura = {}       # cultura -> apólices (p/ achar a mais segurada)
    por_evento = {}        # evento -> valor pago (p/ ranquear causas de perda)
    for d in docs:
        try:
            ap = int(d.get("total_apolices") or 0)
            si = int(d.get("total_sinistros") or 0)
            pg = float(d.get("total_pago_reais") or 0)
        except (TypeError, ValueError):
            ap, si, pg = 0, 0, 0.0
        total_apolices += ap
        total_sinistros += si
        total_pago += pg
        if d.get("ano") is not None:
            anos.add(d.get("ano"))
        c = d.get("cultura_canonica")
        if c:
            por_cultura[c] = por_cultura.get(c, 0) + ap
        for ev in (d.get("por_evento") or []):
            try:
                nome = (ev or {}).get("evento")
                val = float((ev or {}).get("valor") or 0)
                if nome:
                    por_evento[nome] = por_evento.get(nome, 0.0) + val
            except Exception:
                continue
    if total_apolices <= 0:
        return None
    cultura_topo = cult or (max(por_cultura, key=por_cultura.get) if por_cultura else None)
    eventos_ord = sorted(por_evento.items(), key=lambda kv: -kv[1])
    por_evento_top = [{"evento": n, "valor": round(v, 2)} for n, v in eventos_ord[:3]]
    taxa = round(total_sinistros / total_apolices * 100, 1) if total_apolices else None
    anos_ord = sorted(a for a in anos if isinstance(a, int))
    periodo = f"{anos_ord[0]}–{anos_ord[-1]}" if anos_ord else "2016–2024"
    return {
        "escopo": "uf",
        "apolices": total_apolices,
        "sinistros": total_sinistros,
        "pago": round(total_pago, 2),
        "taxa_pct": taxa,
        "cultura_topo": cultura_topo,
        "por_evento": por_evento_top,
        "periodo": periodo,
    }


def _t_buscar_risco_psr(db, args):
    col = _col(db, "psr_agregado")
    if col is None:
        return {"erro": "sem colecao psr_agregado"}
    ibge = _ibge7(args.get("cod_ibge") or args.get("ibge") or "")
    q = {}
    if ibge:
        q["cod_ibge"] = ibge
    cultura = _canon_cultura(args.get("cultura") or "")
    if cultura:
        q["cultura_canonica"] = cultura
    if not q:
        return {"erro": "informe cod_ibge e/ou cultura"}
    docs = _find_many(col, q, sort=[("ano", -1)], limit=5)
    if not docs:
        return {"erro": "sem dados PSR para o filtro"}
    out = []
    for d in docs:
        try:
            ev = d.get("por_evento") or []
            out.append({
                "ano": d.get("ano"), "apolices": d.get("total_apolices"),
                "sinistros": d.get("total_sinistros"),
                "taxa_pct": d.get("taxa_sinistro_pct"),
                "pago": d.get("total_pago_reais"),
                "por_evento": ev[:3],
            })
        except Exception:
            continue
    return {"riscos": out}


def _t_buscar_area_sigef(db, args):
    col = _col(db, "sigef_agregado")
    if col is None:
        return {"erro": "sem colecao sigef_agregado"}
    q = {}
    ibge = _ibge7(args.get("cod_ibge") or args.get("ibge") or "")
    if ibge:
        q["cod_ibge"] = ibge
    cultura = _canon_cultura(args.get("cultura") or "")
    if cultura:
        q["cultura_canonica"] = cultura
    if not q:
        return {"erro": "informe cod_ibge e/ou cultura"}
    docs = _find_many(col, q, limit=5)
    if not docs:
        return {"erro": "sem dados SIGEF para o filtro"}
    out = []
    for d in docs:
        try:
            out.append({
                "cultura": d.get("cultura_canonica"),
                "cod_ibge": d.get("cod_ibge"),
                "municipio_norm": _cap(d.get("municipio_norm")),
                "uf": d.get("uf"),
                "area_total_ha": d.get("area_total_ha"),
                "producao_bruta_t": d.get("producao_bruta_t"),
                "producao_estimada_t": d.get("producao_estimada_t"),
            })
        except Exception:
            continue
    return {"areas": out}


def _t_buscar_irrigacao_ana(db, args):
    col = _col(db, "ana_atlas")
    if col is None:
        return {"erro": "sem colecao ana_atlas"}
    ibge = _ibge7(args.get("cod_ibge") or args.get("ibge") or "")
    if not ibge:
        return {"erro": "informe cod_ibge"}
    doc = _find_one(col, {"cod_ibge": ibge})
    if not doc:
        return {"erro": f"sem dados ANA para {ibge}"}

    def _res(d):
        if not isinstance(d, dict):
            return d
        return {k: v for k, v in list(d.items())[:12]}

    return {
        "cod_ibge": doc.get("cod_ibge"),
        "municipio": _cap(doc.get("municipio")),
        "uf": doc.get("uf"),
        "grupo": _cap(doc.get("grupo_predominante")),
        "sistema": _cap(doc.get("sistema_predominante")),
        "aai": _res(doc.get("aai") or {}),
        "projecao_2030": _res(doc.get("projecao_2030") or {}),
        "projecao_2040": _res(doc.get("projecao_2040") or {}),
    }
def _t_buscar_preco_conab(db, args):
    """Preço mínimo oficial (PGPM/CONAB) por cultura + link do indicador Cepea.

    Devolve só número oficial confirmado; sem valor -> estado pendente honesto.
    Reaproveita a camada precos_dados (Mongo com fallback de arquivo).
    """
    cultura = (args or {}).get("cultura")
    uf = (args or {}).get("uf") or "SP"
    if not cultura:
        return {"erro": "informe a cultura"}
    try:
        from .precos_dados import bloco_pgpm, bloco_cepea, resumo_tendencia
    except Exception:
        try:
            from app.precos_dados import bloco_pgpm, bloco_cepea, resumo_tendencia  # type: ignore
        except Exception:
            return {"erro": "camada de precos indisponivel"}
    pgpm = bloco_pgpm(db, cultura, uf)
    cepea = bloco_cepea(db, cultura, uf)
    tend = resumo_tendencia(db, cultura, uf)

    hist = None
    if tend.get("estado") == "disponivel":
        ult = tend.get("ultimo") or {}
        proj = tend.get("projecao") or {}
        hist = {
            "preco_recente_produtor": ult.get("valor"),
            "ano_recente": ult.get("ano"),
            "media_ultimos_anos": tend.get("media_recente"),
            "tendencia": tend.get("direcao"),
            "projecao_proximo_ano": proj.get("valor_estimado"),
            "projecao_faixa": [proj.get("faixa_min"), proj.get("faixa_max")] if proj else None,
            "fonte": "IBGE — Producao Agricola Municipal (PAM)",
        }
    return {
        "cultura": pgpm.get("cultura"),
        "preco_minimo_pgpm": pgpm.get("valor"),
        "unidade": pgpm.get("unidade"),
        "safra": pgpm.get("data"),
        "estado": pgpm.get("estado"),
        "fonte": (pgpm.get("fonte") or {}).get("nome"),
        "cepea_link": cepea.get("url"),
        "historico_preco": hist,
        "observacao": "Preco MINIMO oficial (piso), nao preco de mercado. O historico_preco e a media anual "
                      "do estado (IBGE); a projecao e estimativa de tendencia, nao garantia. "
                      "PAA/PNAE costumam pagar premio sobre o mercado para a agricultura familiar. "
                      "Nunca recomende 'vender agora'.",
    }


_HANDLERS = {
    "buscar_municipio": _t_buscar_municipio,
    "buscar_janelas_zarc": _t_buscar_janelas_zarc,
    "buscar_produtos_agrofit": _t_buscar_produtos_agrofit,
    "buscar_risco_psr": _t_buscar_risco_psr,
    "buscar_area_sigef": _t_buscar_area_sigef,
    "buscar_irrigacao_ana": _t_buscar_irrigacao_ana,
    "buscar_preco_conab": _t_buscar_preco_conab,
}


def dispatch(db, name, args):
    """Executa ferramenta. Nunca raise: erro vira {"erro": ...}."""
    try:
        fn = _HANDLERS.get(name)
        if fn is None:
            return {"erro": f"ferramenta desconhecida: {name}"}
        if not isinstance(args, dict):
            args = {}
        return fn(db, args)
    except Exception as e:
        return {"erro": f"falha em {name}"}


TOOLS_SCHEMA = [
    {"type": "function", "function": {
        "name": "buscar_municipio",
        "description": "Localiza municipio por IBGE ou nome+UF. Retorna cod_ibge, nome, uf.",
        "parameters": {"type": "object",
                       "properties": {"ibge": {"type": "string"},
                                      "nome": {"type": "string"},
                                      "uf": {"type": "string"}},
                       "required": []}}},
    {"type": "function", "function": {
        "name": "buscar_janelas_zarc",
        "description": "Janelas de plantio ZARC por cultura e IBGE, com Portaria, ciclo_grupo, abertos e risco_min.",
        "parameters": {"type": "object",
                       "properties": {"cultura": {"type": "string"},
                                      "ibge": {"type": "string"},
                                      "solo": {"type": "string"},
                                      "manejo": {"type": "string"},
                                      "limite": {"type": "integer"}},
                       "required": ["cultura", "ibge"]}}},
    {"type": "function", "function": {
        "name": "buscar_produtos_agrofit",
        "description": "Produtos Agrofit/MAPA por cultura e alvo, com filtro organico e classe toxicologica.",
        "parameters": {"type": "object",
                       "properties": {"cultura": {"type": "string"},
                                      "alvo": {"type": "string"},
                                      "so_organicos": {"type": "boolean"},
                                      "max_classe_tox": {"type": "integer"},
                                      "limite": {"type": "integer"}},
                       "required": ["cultura"]}}},
    {"type": "function", "function": {
        "name": "buscar_risco_psr",
        "description": "Risco PSR/SISSER por IBGE e cultura: apolices, sinistros, taxa, pago por ano.",
        "parameters": {"type": "object",
                       "properties": {"cod_ibge": {"type": "string"},
                                      "cultura": {"type": "string"}},
                       "required": ["cod_ibge"]}}},
    {"type": "function", "function": {
        "name": "buscar_area_sigef",
        "description": "Area e producao SIGEF sementes por IBGE e/ou cultura.",
        "parameters": {"type": "object",
                       "properties": {"cod_ibge": {"type": "string"},
                                      "cultura": {"type": "string"}},
                       "required": []}}},
    {"type": "function", "function": {
        "name": "buscar_irrigacao_ana",
        "description": "Irrigacao ANA Atlas por IBGE: grupo, sistema, AAI e projecoes 2030/2040.",
        "parameters": {"type": "object",
                       "properties": {"cod_ibge": {"type": "string"}},
                       "required": ["cod_ibge"]}}},
    {"type": "function", "function": {
        "name": "buscar_preco_conab",
        "description": "Preco MINIMO oficial (PGPM/CONAB) da cultura por saca + link do indicador diario Cepea. Use para perguntas sobre venda, preco, cotacao ou quanto vale a producao.",
        "parameters": {"type": "object",
                       "properties": {"cultura": {"type": "string"},
                                      "uf": {"type": "string"}},
                       "required": ["cultura"]}}},
]
