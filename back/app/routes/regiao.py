"""GET /api/regiao — agregado regional via dispatch de tools existentes.

Agrega buscar_janelas_zarc (maioria solo), buscar_area_sigef,
buscar_risco_psr, buscar_irrigacao_ana + buscar_municipio.
Nunca raise: camada ausente vira estado "sem_dado" honesto.
Preços sempre pendentes honestos (sem ingestão CONAB/PGPM).
"""
import logging
from collections import Counter
from datetime import date

from fastapi import APIRouter, Query

from ..db import get_db
from ..tools import dispatch, agregar_psr_uf

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Regiao"])

FONTE_REGIAO = "ZARC+SIGEF+PSR+ANA via tools"
DATA_EXTRACAO_FALLBACK = "2026-10-02"

UFS = {
    "AC": ("Acre", "Norte"), "AL": ("Alagoas", "Nordeste"),
    "AM": ("Amazonas", "Norte"), "AP": ("Amapá", "Norte"),
    "BA": ("Bahia", "Nordeste"), "CE": ("Ceará", "Nordeste"),
    "DF": ("Distrito Federal", "Centro-Oeste"),
    "ES": ("Espírito Santo", "Sudeste"), "GO": ("Goiás", "Centro-Oeste"),
    "MA": ("Maranhão", "Nordeste"), "MG": ("Minas Gerais", "Sudeste"),
    "MS": ("Mato Grosso do Sul", "Centro-Oeste"),
    "MT": ("Mato Grosso", "Centro-Oeste"), "PA": ("Pará", "Norte"),
    "PB": ("Paraíba", "Nordeste"), "PE": ("Pernambuco", "Nordeste"),
    "PI": ("Piauí", "Nordeste"), "PR": ("Paraná", "Sul"),
    "RJ": ("Rio de Janeiro", "Sudeste"),
    "RN": ("Rio Grande do Norte", "Nordeste"), "RO": ("Rondônia", "Norte"),
    "RR": ("Roraima", "Norte"), "RS": ("Rio Grande do Sul", "Sul"),
    "SC": ("Santa Catarina", "Sul"), "SE": ("Sergipe", "Nordeste"),
    "SP": ("São Paulo", "Sudeste"), "TO": ("Tocantins", "Norte"),
}

# ponytail: AD1-AD6 = água disponível (não textura); mapeamento aproximado
# ad1/ad2→arenoso, ad3/ad4→media, ad5/ad6→argiloso. Revisar com agrônomo.
SOLO_SIMPLES = {
    "arenoso": "arenoso", "media": "media", "argiloso": "argiloso",
    "ad1": "arenoso", "ad2": "arenoso",
    "ad3": "media", "ad4": "media",
    "ad5": "argiloso", "ad6": "argiloso",
}

SOLO_DESCRICAO = {
    "arenoso": "Solo arenoso: a água escorre rápido; precisa de chuva ou rega mais frequente. Predominante na sua região (ZARC).",
    "media": "Solo médio: equilibra água e drenagem; serve para a maioria das culturas. Predominante na sua região (ZARC).",
    "argiloso": "Solo argiloso: segura a água por mais tempo; cuidado com encharco. Predominante na sua região (ZARC).",
}


def _ibge7(codigo) -> str:
    s = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    if len(s) > 7:
        s = s[:-1]
    return s


def _solo_majoritario_raw(db, ibge: str):
    """Solo_canonico majoritário no ZARC para o ibge. None se sem dados. Nunca raise."""
    if db is None or not ibge:
        return None
    try:
        col = getattr(db, "zarc", None)
        if col is None:
            return None
        try:
            agg = list(col.aggregate([
                {"$match": {"cod_ibge": ibge}},
                {"$group": {"_id": "$solo_canonico", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}},
                {"$limit": 5},
            ]))
        except Exception:
            agg = []
        for g in agg or []:
            try:
                if (g or {}).get("_id"):
                    return g["_id"]
            except Exception:
                continue
        if agg:
            return None
        # fallback sem aggregate: conta em python
        cont = Counter()
        try:
            cur = col.find({"cod_ibge": ibge})
        except Exception:
            return None
        try:
            docs = list(cur)
        except Exception:
            return None
        for d in docs or []:
            try:
                s = (d or {}).get("solo_canonico")
                if s:
                    cont[s] += 1
            except Exception:
                continue
        return cont.most_common(1)[0][0] if cont else None
    except Exception as e:
        log.warning("solo majoritario falhou ibge=%s: %r", ibge, e)
        return None


def solo_inferido_para(db, ibge) -> str | None:
    """Solo simplificado (arenoso|media|argiloso) para o ibge. None se sem dados. Nunca raise."""
    try:
        raw = _solo_majoritario_raw(db, _ibge7(ibge))
        if not raw:
            return None
        return SOLO_SIMPLES.get(str(raw).strip().lower())
    except Exception as e:
        log.warning("solo inferido falhou: %r", e)
        return None


def _fonte(nome: str, periodo: str, limitacoes: list | None = None) -> dict:
    f: dict = {"nome": nome, "periodo": periodo}
    if limitacoes:
        f["limitacoes"] = limitacoes
    return f


def _bloco_solo(db, ibge: str, uf: str) -> dict:
    raw = _solo_majoritario_raw(db, ibge) if (db is not None and ibge) else None
    simples = SOLO_SIMPLES.get(str(raw or "").strip().lower())
    if simples:
        return {
            "uf": uf, "estado": "disponivel", "soloId": simples,
            "descricao": SOLO_DESCRICAO[simples],
            "fonte": _fonte("ZARC / solos (MAPA)", "2026/2027"),
        }
    alvo = ibge or uf
    return {
        "uf": uf, "estado": "sem_dado", "soloId": None,
        "descricao": f"Sem dado de solo ZARC para {alvo}.",
        "fonte": _fonte("ZARC / solos (MAPA)", "2026/2027",
                         ["Nenhum zoneamento ZARC para este município/cultura."]),
    }


def _bloco_producao(db, ibge: str, cultura: str | None, uf: str) -> dict:
    if db is not None and ibge:
        args = {"cod_ibge": ibge}
        if cultura:
            args["cultura"] = cultura
        try:
            r: dict = dispatch(db, "buscar_area_sigef", args)
        except Exception as e:
            log.warning("sigef dispatch falhou: %r", e)
            r = {"erro": "falha sigef"}
        areas = (r or {}).get("areas") or []
        if areas and isinstance(areas[0], dict):
            a: dict = areas[0]
            try:
                bruta = a.get("producao_bruta_t") or 0
                est = a.get("producao_estimada_t") or 0
                return {
                    "uf": uf, "estado": "disponivel",
                    "culturaTopo": a.get("cultura") or cultura,
                    "areaHa": a.get("area_total_ha"),
                    "producaoT": bruta or est or None,
                    "safraRef": "2013–2017",
                    "fonte": _fonte("SIGEF Sementes / MAPA", "2013–2017"),
                }
            except Exception as e:
                log.warning("mapeamento sigef falhou: %r", e)
    alvo = f"{cultura or 'cultura'} em {ibge or uf}"
    return {
        "uf": uf, "estado": "sem_dado", "culturaTopo": cultura,
        "areaHa": None, "producaoT": None, "safraRef": None,
        "fonte": _fonte("SIGEF Sementes / MAPA", "2013–2017",
                         [f"Sem dado SIGEF para {alvo}."]),
    }


def _bloco_seguro(db, ibge: str, cultura: str | None, uf: str) -> dict:
    # 1) tenta o município exato (+cultura, se houver) — dado mais específico
    if db is not None and ibge:
        args = {"cod_ibge": ibge}
        if cultura:
            args["cultura"] = cultura
        try:
            r2: dict = dispatch(db, "buscar_risco_psr", args)
        except Exception as e:
            log.warning("psr dispatch falhou: %r", e)
            r2 = {"erro": "falha psr"}
        riscos = (r2 or {}).get("riscos") or []
        if riscos and isinstance(riscos[0], dict):
            x: dict = riscos[0]
            try:
                return {
                    "uf": uf, "estado": "disponivel", "escopo": "municipio",
                    "apolices": x.get("apolices"),
                    "valorSegurado": x.get("pago"),
                    "culturaTopo": cultura,
                    "ano": x.get("ano"), "taxa_pct": x.get("taxa_pct"),
                    "pago_reais": x.get("pago"),
                    "por_evento": (x.get("por_evento") or [])[:3],
                    "fonte": _fonte("MAPA — Seguro Rural (PSR)", "2016–2024",
                                     ["Baseado nas apólices do seguro rural da região, não na produção de cada propriedade."]),
                }
            except Exception as e:
                log.warning("mapeamento psr falhou: %r", e)

    # 2) sem município (ou sem match): agrega o estado inteiro — retrato real da UF
    if db is not None:
        try:
            ag = agregar_psr_uf(db, uf, cultura)
        except Exception as e:
            log.warning("agregacao psr uf falhou: %r", e)
            ag = None
        if ag:
            return {
                "uf": uf, "estado": "disponivel", "escopo": "uf",
                "apolices": ag.get("apolices"),
                "valorSegurado": ag.get("pago"),
                "culturaTopo": cultura or ag.get("cultura_topo"),
                "ano": None, "taxa_pct": ag.get("taxa_pct"),
                "pago_reais": ag.get("pago"),
                "sinistros": ag.get("sinistros"),
                "por_evento": ag.get("por_evento") or [],
                "fonte": _fonte("MAPA — Seguro Rural (PSR)", ag.get("periodo", "2016–2024"),
                                 ["Soma das apólices do estado inteiro, não da sua propriedade.",
                                  "Escolha o seu município no mapa para um retrato mais próximo de você."]),
            }

    alvo = f"{cultura or 'cultura'} em {ibge or uf}"
    return {
        "uf": uf, "estado": "sem_dado", "apolices": None,
        "valorSegurado": None, "culturaTopo": cultura,
        "fonte": _fonte("MAPA — Seguro Rural (PSR)", "2016–2024",
                         [f"Ainda sem registro de seguro rural para {alvo} na base."]),
    }


def _bloco_irrigacao(db, ibge: str, uf: str) -> dict:
    if db is not None and ibge:
        try:
            r3: dict = dispatch(db, "buscar_irrigacao_ana", {"cod_ibge": ibge})
        except Exception as e:
            log.warning("ana dispatch falhou: %r", e)
            r3 = {"erro": "falha ana"}
        if (r3 or {}).get("grupo") or (r3 or {}).get("sistema"):
            try:
                grupo, sistema = r3.get("grupo"), r3.get("sistema")
                return {
                    "uf": uf, "estado": "disponivel", "areaIrrigadaHa": None,
                    "grupo": grupo, "sistema": sistema,
                    "detalhe": f"Grupo {grupo or 'n/d'}, sistema {sistema or 'n/d'} (Atlas Irrigação ANA). Área irrigada em ha ainda não exposta — ver fonte.",
                    "fonte": _fonte("ANA — Atlas Irrigação", "2019 (obs) / 2030+2040 (proj)",
                                     ["Área atual por tipologia ainda não exposta neste endpoint; grupo/sistema predominantes acima."]),
                }
            except Exception as e:
                log.warning("mapeamento ana falhou: %r", e)
    alvo = ibge or uf
    return {
        "uf": uf, "estado": "sem_dado", "areaIrrigadaHa": None,
        "detalhe": f"Sem dado ANA para {alvo}.",
        "fonte": _fonte("ANA — Atlas Irrigação", "2019 (obs)",
                         [f"Sem dado ANA para {alvo}."]),
    }


def _bloco_precos(db, cultura: str | None, uf: str) -> list:
    """Preços reais via precos_dados (PGPM CONAB + Cepea link). Nunca raise."""
    try:
        from ..precos_dados import precos_da_uf
        return precos_da_uf(db, cultura, uf)
    except Exception as e:
        log.warning("bloco precos falhou: %r", e)
        cult = cultura or "sua cultura"
        return [
            {"tipo": "pgpm", "cultura": cult, "uf": None, "valor": None,
             "unidade": "R$/60kg",
             "fonte": _fonte("CONAB — PGPM (preço mínimo)", "safra vigente (quando publicado)",
                              ["Preço mínimo oficial, não preço de mercado."]),
             "data": None, "estado": "pendente",
             "aviso": "Preço mínimo de referência do governo. Serve de piso para planejar — não diz quando vender."},
            {"tipo": "conab_mercado", "cultura": cult, "uf": uf, "valor": None,
             "unidade": "R$/60kg",
             "fonte": _fonte("CONAB — preços de mercado por UF", "aguardando ingestão",
                              ["Camada ainda não ligada ao backend."]),
             "data": None, "estado": "pendente",
             "aviso": "Mostra o contexto de mercado da sua região — não é ordem de venda."},
            {"tipo": "cepea", "cultura": cult, "uf": None, "valor": None,
             "unidade": "indicador diário",
             "fonte": _fonte("Cepea/ESALQ — indicador diário (link externo)", "",
                              ["Número pertence ao Cepea; abrimos o site oficial em vez de copiar."]),
             "data": None, "estado": "link_externo",
             "url": "https://www.cepea.esalq.usp.br/br",
             "aviso": "Abre o indicador oficial no site do Cepea."},
        ]


def _bloco_oportunidade(zarc_ok: bool, sigef_ok: bool, cultura: str | None,
                        municipio: str | None, area_ha, uf: str) -> dict:
    if zarc_ok and sigef_ok and cultura:
        local = municipio or uf
        return {
            "uf": uf, "estado": "disponivel",
            "culturasAptasPoucoExploradas": [],
            "detalhe": f"{cultura} tem janela ZARC em {local} e {area_ha} ha em SIGEF — cenário para estudar, não ordem de plantio.",
            "fonte": _fonte("ZARC/MAPA x SIGEF", "2026/27 x 2013–2017"),
        }
    return {
        "uf": uf, "estado": "pendente",
        "culturasAptasPoucoExploradas": [],
        "detalhe": "Quando o cruzamento ZARC x SIGEF ligar, mostramos aqui culturas aptas para a região. É um cenário para estudar — não uma ordem de plantio.",
        "fonte": _fonte("ZARC/MAPA x SIGEF — cruzamento pendente", "aguardando ingestão",
                         ["Requer as duas camadas ligadas para calcular."]),
    }


@router.get("/regiao")
def get_regiao(uf: str = Query(...), ibge: str | None = None,
               cultura: str | None = None):
    uf = (uf or "").strip().upper()
    ibge = _ibge7(ibge) or None
    cultura = (cultura or "").strip().lower() or None
    nome, regiao = UFS.get(uf, (uf or "n/d", "n/d"))
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em /regiao: %r", e)
        db = None

    municipio = None
    if db is not None and ibge:
        try:
            m = dispatch(db, "buscar_municipio", {"ibge": ibge})
            if (m or {}).get("nome"):
                municipio = m["nome"]
                if (m.get("uf") or "").upper() in UFS:
                    uf = m["uf"].upper()
                    nome, regiao = UFS[uf]
        except Exception as e:
            log.warning("buscar_municipio falhou: %r", e)

    solo = _bloco_solo(db, ibge or "", uf)
    producao = _bloco_producao(db, ibge or "", cultura, uf)
    seguro = _bloco_seguro(db, ibge or "", cultura, uf)
    irrigacao = _bloco_irrigacao(db, ibge or "", uf)

    zarc_ok, sigef_ok, area_ha = False, False, None
    if db is not None and ibge and cultura:
        try:
            z = dispatch(db, "buscar_janelas_zarc", {"cultura": cultura, "ibge": ibge})
            zarc_ok = bool((z or {}).get("janelas"))
        except Exception as e:
            log.warning("zarc oportunidade falhou: %r", e)
    try:
        sigef_ok = producao.get("estado") == "disponivel"
        area_ha = producao.get("areaHa")
    except Exception:
        pass
    oportunidade = _bloco_oportunidade(zarc_ok, sigef_ok, cultura, municipio, area_ha, uf)

    try:
        hoje = date.today().isoformat()
    except Exception:
        hoje = DATA_EXTRACAO_FALLBACK
    return {
        "uf": {"sigla": uf, "nome": nome, "regiao": regiao},
        "ibge": ibge, "municipio": municipio,
        "producao": producao, "solo": solo, "seguro": seguro,
        "irrigacao": irrigacao, "precos": _bloco_precos(db, cultura, uf),
        "oportunidade": oportunidade,
        "fonte": FONTE_REGIAO, "data_extracao": hoje,
    }
