"""Alertas de verdade para o produtor, calculados dos dados oficiais.

Dois tipos, ambos a partir do Mongo (ZARC + Seguro Rural/PSR), sem mock:

  1. "Janela de plantio fechando" — a partir do zoneamento ZARC: pega os
     decêndios indicados para a cultura no município e compara com a data de
     hoje. Se falta pouco para o último decêndio bom, avisa.
  2. "Época de maior risco" — a partir do histórico do seguro rural (PSR): o
     evento que mais causou perda na região (seca, geada, chuva).

Tudo traduzido para linguagem do produtor, sem jargão (nada de "decêndio",
"apólice" ou "sinistro" na mensagem). Nunca quebra: sem dado -> lista vazia.
GET /api/alertas?ibge=&cultura=&uf=  (ou produtor_id, resolvido no front).
"""
import logging
import math
from datetime import date, datetime, timezone

from fastapi import APIRouter, Query

from ..db import get_db
from ..tools import dispatch, agregar_psr_uf
from ..schemas.alertas import SimularAlertaRequest

router = APIRouter(prefix="/api", tags=["Alertas"])
log = logging.getLogger(__name__)

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]

# Evento cru do PSR -> frase humana.
EVENTO_HUMANO = {
    "seca": "estiagem (falta de chuva)",
    "estiagem": "estiagem (falta de chuva)",
    "geada": "geada",
    "granizo": "chuva de granizo",
    "chuva excessiva": "excesso de chuva",
    "excesso de chuva": "excesso de chuva",
    "chuva": "excesso de chuva",
    "vento": "ventania",
    "doenca": "doença na lavoura",
    "praga": "ataque de praga",
}


def _decendio_de(d: date) -> int:
    """Data -> decêndio do ano (1..36). Cada mês tem 3 períodos de ~10 dias."""
    periodo = min(3, (d.day - 1) // 10 + 1)  # 1,2,3
    return (d.month - 1) * 3 + periodo


def _fim_do_decendio(dec: int) -> date:
    """Último dia aproximado de um decêndio (1..36), no ano corrente."""
    mes = (dec - 1) // 3 + 1
    pos = (dec - 1) % 3  # 0,1,2
    dia = 10 if pos == 0 else 20 if pos == 1 else 28
    ano = date.today().year
    try:
        return date(ano, mes, dia)
    except ValueError:
        return date(ano, mes, 28)


def _periodo_humano(dec: int) -> str:
    """Decêndio -> 'início/meio/fim de <mês>' em linguagem simples."""
    mes = MESES[min(11, (dec - 1) // 3)]
    pos = (dec - 1) % 3
    quando = "início" if pos == 0 else "meio" if pos == 1 else "fim"
    return f"{quando} de {mes}"


def _alerta_janela(db, ibge, cultura, uf):
    """Janela de plantio fechando (ZARC). Retorna dict de alerta ou None."""
    if db is None or not ibge or not cultura:
        return None
    try:
        z = dispatch(db, "buscar_janelas_zarc", {"cultura": cultura, "ibge": ibge})
    except Exception as e:
        log.warning("zarc alerta falhou: %r", e)
        return None
    janelas = (z or {}).get("janelas") or []
    abertos = []
    for j in janelas:
        for d in (j.get("abertos") or []):
            try:
                n = int(d)
                if 1 <= n <= 36:
                    abertos.append(n)
            except (ValueError, TypeError):
                continue
    if not abertos:
        return None
    ultimo = max(abertos)
    hoje_dec = _decendio_de(date.today())

    # Fora da janela (já passou): não alarma — é cenário de planejar a próxima.
    if hoje_dec > ultimo:
        return None

    faltam = ultimo - hoje_dec  # em decêndios (~10 dias cada)
    fim = _fim_do_decendio(ultimo)
    dias = max(0, (fim - date.today()).days)
    try:
        from ..precos_dados import rotulo_cultura, canon_cultura
        cult = rotulo_cultura(canon_cultura(cultura))
    except Exception:
        cult = str(cultura).capitalize()

    if faltam <= 2:
        sev = "alta" if faltam <= 1 else "media"
        msg = (
            f"A melhor época para plantar {cult.lower()} na sua região vai até o {_periodo_humano(ultimo)} "
            f"— faltam cerca de {dias} dias. Depois disso o risco de perder a safra por clima sobe. "
            f"Se ainda não plantou, vale correr."
        )
    else:
        sev = "baixa"
        msg = (
            f"A época boa para plantar {cult.lower()} na sua região segue aberta até o {_periodo_humano(ultimo)}. "
            f"Ainda dá tempo com tranquilidade — organize semente e preparo do solo."
        )
    return {
        "id": f"janela-{cultura}-{ibge}",
        "tipo": "janela_zarc",
        "severidade": sev,
        "mensagem": msg,
        "fonte": "Zoneamento de plantio do governo (ZARC/MAPA)",
        "data_extracao": "2026/2027",
        "enviado_em": datetime.now(timezone.utc).isoformat(),
        "lido": False,
    }


def _alerta_risco(db, ibge, cultura, uf):
    """Época/evento de maior risco histórico (seguro rural). Dict ou None."""
    if db is None:
        return None
    dados = None
    # tenta o município; se nada, agrega o estado
    if ibge:
        try:
            r = dispatch(db, "buscar_risco_psr", {"cod_ibge": ibge, "cultura": cultura} if cultura else {"cod_ibge": ibge})
            riscos = (r or {}).get("riscos") or []
            if riscos:
                dados = riscos[0]
        except Exception as e:
            log.warning("psr alerta municipio falhou: %r", e)
    if not dados or not (dados.get("por_evento")):
        ag = agregar_psr_uf(db, uf, cultura)
        if ag and ag.get("por_evento"):
            dados = {"por_evento": ag["por_evento"]}
    if not dados:
        return None
    eventos = dados.get("por_evento") or []
    if not eventos:
        return None
    top = eventos[0]
    nome = str((top or {}).get("evento") or "").strip().lower()
    if not nome:
        return None
    humano = EVENTO_HUMANO.get(nome, nome)
    try:
        from ..precos_dados import rotulo_cultura, canon_cultura
        cult = rotulo_cultura(canon_cultura(cultura)).lower() if cultura else "a lavoura"
    except Exception:
        cult = str(cultura or "a lavoura").lower()
    msg = (
        f"Na sua região, o que mais fez produtores perderem {cult} no passado foi {humano}. "
        f"Fique de olho nisso na hora de decidir o plantio e pense no seguro da safra como proteção."
    )
    return {
        "id": f"risco-{nome}-{ibge or uf}",
        "tipo": "risco_historico",
        "severidade": "media",
        "mensagem": msg,
        "fonte": "Histórico do seguro rural (PSR/MAPA)",
        "data_extracao": "2016–2024",
        "enviado_em": datetime.now(timezone.utc).isoformat(),
        "lido": False,
    }


def _alertas_clima(db, ibge, cultura, uf):
    """Alertas climáticos REAIS (previsão Open-Meteo): geada, onda de calor,
    chuva forte, veranico, chuva recente. Lista (pode ter vários). Nunca raise."""
    try:
        from ..clima import buscar_previsao, detectar_eventos
        from ..precos_dados import rotulo_cultura, canon_cultura
    except Exception:
        return []
    try:
        prev = buscar_previsao(db, ibge=ibge, uf=uf)
    except Exception as e:
        log.warning("clima previsao falhou: %r", e)
        prev = None
    if not prev:
        return []
    cult_label = rotulo_cultura(canon_cultura(cultura)) if cultura else None
    try:
        eventos = detectar_eventos(prev, cult_label)
    except Exception as e:
        log.warning("detectar_eventos falhou: %r", e)
        return []
    local = prev.get("local") or {}
    saida = []
    for ev in eventos:
        saida.append({
            "id": f"clima-{ev['tipo']}-{ibge or uf}",
            "tipo": ev["tipo"],
            "severidade": ev.get("severidade", "media"),
            "titulo": ev.get("titulo"),
            "mensagem": ev["mensagem"],
            "fonte": ev.get("fonte", "Open-Meteo + IBGE"),
            "local": local.get("nome"),
            "data_extracao": "previsão dos próximos dias",
            "enviado_em": datetime.now(timezone.utc).isoformat(),
            "lido": False,
        })
    return saida


# Ordem de severidade para ranquear os alertas (mais grave primeiro).
_PESO_SEV = {"alta": 0, "media": 1, "baixa": 2}


@router.get("/alertas")
def listar_alertas(ibge: str | None = None, cultura: str | None = None,
                   uf: str = Query("SP")):
    """Alertas reais: clima (Open-Meteo) + janela ZARC + risco PSR.

    Clima é a camada de PREVISÃO (o que vem aí); ZARC/PSR são contexto. Lista
    vazia honesta se não houver nada relevante. Nunca inventa.
    """
    uf = (uf or "SP").strip().upper()
    ibge = "".join(ch for ch in str(ibge or "") if ch.isdigit()) or None
    cultura = (cultura or "").strip().lower() or None
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em /alertas: %r", e)
        db = None

    alertas = []
    # clima pode gerar vários; ZARC/PSR geram um cada
    try:
        alertas.extend(_alertas_clima(db, ibge, cultura, uf))
    except Exception as e:
        log.warning("alertas clima falhou: %r", e)
    for fn in (_alerta_janela, _alerta_risco):
        try:
            a = fn(db, ibge, cultura, uf)
            if a:
                alertas.append(a)
        except Exception as e:
            log.warning("alerta %s falhou: %r", getattr(fn, "__name__", "?"), e)

    # mais graves primeiro
    alertas.sort(key=lambda a: _PESO_SEV.get(a.get("severidade"), 1))

    return {
        "alertas": alertas,
        "uf": uf,
        "vazio_ok": len(alertas) == 0,
        "data": date.today().isoformat(),
    }


@router.post("/alertas/simular")
def simular_alerta(req: SimularAlertaRequest):
    """Dispara um alerta de demonstração (pitch/banca). Marcado como simulado."""
    return {
        "ok": True,
        "alerta": {
            "id": f"alerta-{req.tipo}-simulado",
            "tipo": req.tipo,
            "severidade": "alta",
            "mensagem": f"Alerta simulado de {req.tipo} para sua propriedade. Risco detectado para suas culturas.",
            "fonte": "ZARC + INMET",
            "enviado_em": datetime.now(timezone.utc).isoformat(),
            "lido": False,
        },
    }


@router.get("/alertas/{id}")
def listar_alertas_legado(id: str):
    """Compat: rota antiga por id. Sem produtor real -> lista vazia honesta."""
    return {"alertas": []}
