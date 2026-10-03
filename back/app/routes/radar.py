"""GET /api/radar — os 3 cartões da tela Radar, com dado REAL e estruturado.

Diferente de /api/alertas (que só devolve frases prontas), aqui cada bloco vem
com os números por trás, já traduzidos para linguagem do produtor:

  1. zarc  — janela de plantio em DATAS de calendário (não "decêndio"),
             filtrada pelo solo do produtor, com a Portaria como fonte e a
             contagem regressiva até a janela fechar.
  2. clima — previsão dos próximos dias (chuva, mínima, máxima) + leitura.
  3. psr   — eventos que mais causaram perda na região (seguro rural), reais.

Cada bloco tem um "estado" honesto: "disponivel" (tem dado) ou "sem_dado"
(a base foi consultada e não tem). Nunca inventa. O estado "sem_conexao" é
decidido no front, quando o fetch falha.
"""
import logging
from datetime import date, timedelta

from fastapi import APIRouter, Query

from ..db import get_db
from ..tools import dispatch, agregar_psr_uf

router = APIRouter(prefix="/api", tags=["Radar"])
log = logging.getLogger(__name__)

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_CURTO = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set",
               "out", "nov", "dez"]
DIAS_SEM = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

# solo do produtor (arenoso/media/argiloso) -> classes AD do ZARC equivalentes
SOLO_PARA_AD = {
    "arenoso": ["arenoso", "ad1", "ad2"],
    "media": ["media", "ad3", "ad4"],
    "argiloso": ["argiloso", "ad5", "ad6"],
}

# evento cru do PSR -> frase humana (sem jargão de seguro)
EVENTO_HUMANO = {
    "seca": "estiagem (falta de chuva)",
    "estiagem": "estiagem (falta de chuva)",
    "geada": "geada",
    "granizo": "chuva de granizo",
    "chuva excessiva": "excesso de chuva",
    "excesso de chuva": "excesso de chuva",
    "chuva": "excesso de chuva",
    "vento": "ventania",
    "variacao excessiva de temperatura": "variação brusca de temperatura",
    "demais causas": "outras causas",
    "doenca": "doença na lavoura",
    "praga": "ataque de praga",
}


def _ibge7(codigo) -> str:
    s = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    return s[:7] if len(s) > 7 else s


def _rotulo_cultura(cultura):
    try:
        from ..precos_dados import rotulo_cultura, canon_cultura
        return rotulo_cultura(canon_cultura(cultura)) if cultura else None
    except Exception:
        return str(cultura).capitalize() if cultura else None


def _reais(v) -> str:
    """Valor em reais, humano e sem centavos:
    1_300_000_000 -> 'R$ 1,3 bi'; 5_400_000 -> 'R$ 5,4 mi'; 345_000 -> 'R$ 345 mil'.
    """
    try:
        n = float(v or 0)
    except (TypeError, ValueError):
        return "R$ 0"
    if n >= 1_000_000_000:
        return f"R$ {n/1_000_000_000:.1f} bi".replace(".", ",")
    if n >= 1_000_000:
        return f"R$ {n/1_000_000:.1f} mi".replace(".", ",")
    if n >= 1_000:
        return f"R$ {int(round(n/1000))} mil"
    return f"R$ {int(round(n))}"


# ---------------------------------------------------------------- decêndios

def _data_do_decendio_inicio(dec: int, ano: int) -> date:
    """Primeiro dia de um decêndio (1..36)."""
    mes = (dec - 1) // 3 + 1
    pos = (dec - 1) % 3            # 0,1,2
    dia = 1 if pos == 0 else 11 if pos == 1 else 21
    return date(ano, mes, dia)


def _data_do_decendio_fim(dec: int, ano: int) -> date:
    """Último dia de um decêndio (1..36)."""
    mes = (dec - 1) // 3 + 1
    pos = (dec - 1) % 3
    if pos == 0:
        dia = 10
    elif pos == 1:
        dia = 20
    else:
        # fim do mês real
        prox = date(ano + (mes == 12), (mes % 12) + 1, 1)
        return prox - timedelta(days=1)
    return date(ano, mes, dia)


def _decendio_de(d: date) -> int:
    periodo = min(3, (d.day - 1) // 10 + 1)
    return (d.month - 1) * 3 + periodo


def _dia_mes(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]}"


def _intervalos(decs: list[int]) -> list[tuple[int, int]]:
    """Agrupa decêndios ordenados em faixas contíguas: [1,2,3,7,8] -> [(1,3),(7,8)]."""
    if not decs:
        return []
    s = sorted(set(decs))
    faixas = []
    ini = prev = s[0]
    for n in s[1:]:
        if n == prev + 1:
            prev = n
            continue
        faixas.append((ini, prev))
        ini = prev = n
    faixas.append((ini, prev))
    return faixas


def _bloco_zarc(db, ibge, cultura, solo) -> dict:
    base = {"estado": "sem_dado", "titulo": "Janela de plantio (ZARC)"}
    if db is None or not ibge or not cultura:
        base["detalhe"] = ("Me diga a sua cultura e escolha o município no mapa "
                           "para eu buscar a janela de plantio recomendada pelo governo.")
        base["fonte"] = {"nome": "MAPA — ZARC (Zoneamento Agrícola de Risco Climático)",
                         "periodo": "safra vigente"}
        return base

    args = {"cultura": cultura, "ibge": ibge}
    if solo and solo in SOLO_PARA_AD:
        # tenta o solo do produtor; a tool já faz retry sem solo se não achar
        for cand in SOLO_PARA_AD[solo]:
            r = dispatch(db, "buscar_janelas_zarc", {**args, "solo": cand})
            if (r or {}).get("janelas"):
                break
    else:
        r = dispatch(db, "buscar_janelas_zarc", args)

    janelas = (r or {}).get("janelas") or []
    if not janelas:
        base["detalhe"] = (f"O zoneamento do governo ainda não traz janela de "
                           f"{_rotulo_cultura(cultura).lower()} para o seu município.")
        base["fonte"] = {"nome": "MAPA — ZARC", "periodo": "safra vigente"}
        return base

    j = janelas[0]
    abertos = sorted({int(d) for d in (j.get("abertos") or []) if str(d).isdigit()})
    if not abertos:
        base["detalhe"] = ("A base tem o zoneamento, mas sem decêndios de plantio "
                           "abertos para esta combinação de cultura e solo.")
        base["fonte"] = {"nome": "MAPA — ZARC", "periodo": j.get("portaria") or "safra vigente"}
        return base

    hoje = date.today()
    ano = hoje.year
    faixas = _intervalos(abertos)
    # datas de calendário de cada faixa aberta
    linhas = []
    dec_map = j.get("dec") or {}
    for (a, b) in faixas:
        ini = _data_do_decendio_inicio(a, ano)
        fim = _data_do_decendio_fim(b, ano)
        riscos = [int(dec_map.get(str(k), dec_map.get(k, 0)) or 0) for k in range(a, b + 1)]
        risco = min([x for x in riscos if x] or [0])
        linhas.append({
            "rotulo": f"{_dia_mes(ini)} a {_dia_mes(fim)}",
            "valor": f"risco {risco}%" if risco else "indicado",
        })

    cult = _rotulo_cultura(cultura)
    ultimo = max(abertos)
    hoje_dec = _decendio_de(hoje)
    fim_janela = _data_do_decendio_fim(ultimo, ano)
    dias_restantes = (fim_janela - hoje).days

    cly = cult.lower()
    if hoje_dec > ultimo:
        estado = "atencao"
        detalhe = (f"A melhor época de plantar {cly} no seu município já passou "
                   f"nesta safra. Guarde para a próxima: a janela abre de novo em "
                   f"{_dia_mes(_data_do_decendio_inicio(min(abertos), ano + 1))}.")
        leitura = "Plantar fora da janela aumenta o risco de perder a safra por clima."
    elif dias_restantes <= 20:
        estado = "atencao"
        detalhe = (f"A janela boa para plantar {cly} fecha em cerca de "
                   f"{max(0, dias_restantes)} dias, no {_dia_mes(fim_janela)}. "
                   f"Se ainda não plantou, vale correr.")
        leitura = "Depois dessa data o risco de perder a safra por clima sobe."
    else:
        estado = "favoravel"
        detalhe = (f"Dá para plantar {cly} com tranquilidade: a janela recomendada "
                   f"segue aberta até {_dia_mes(fim_janela)}.")
        leitura = ("Essas datas vêm do zoneamento oficial — plantar dentro delas é "
                   "o que o governo considera de menor risco climático.")

    manejo = j.get("manejo")
    solo_zarc = j.get("solo")
    nota_solo = ""
    if solo and solo in SOLO_PARA_AD:
        nota_solo = f" Calculado para solo {solo}."
    return {
        "estado": estado,
        "titulo": "Janela de plantio (ZARC)",
        "detalhe": detalhe + nota_solo,
        "linhas": linhas[:4],
        "leitura": leitura,
        "fonte": {
            "nome": "MAPA — ZARC (Zoneamento Agrícola de Risco Climático)",
            "periodo": j.get("portaria") or "safra vigente",
            "limitacoes": [
                "Zoneamento por município e tipo de solo; não considera o microclima da sua gleba.",
                f"Manejo de referência: {manejo or 'n/d'}; classe de solo ZARC: {solo_zarc or 'n/d'}.",
            ],
        },
    }


def _nivel_chuva(mm) -> tuple[str, bool]:
    try:
        v = float(mm or 0)
    except (TypeError, ValueError):
        return "—", False
    if v >= 30:
        return f"{v:.0f} mm (forte)", True
    if v >= 10:
        return f"{v:.0f} mm", False
    if v >= 1:
        return f"{v:.0f} mm (fraca)", False
    return "sem chuva", False


def _bloco_clima(db, ibge, cultura, uf) -> dict:
    base = {"estado": "sem_dado", "titulo": "Previsão do tempo"}
    try:
        from ..clima import buscar_previsao
    except Exception:
        base["detalhe"] = "A camada de clima não está disponível neste servidor."
        base["fonte"] = {"nome": "Open-Meteo"}
        return base
    try:
        prev = buscar_previsao(db, ibge=ibge, uf=uf)
    except Exception as e:
        log.warning("clima radar falhou: %r", e)
        prev = None
    if not prev or not prev.get("dias"):
        base["detalhe"] = ("Para mostrar a previsão eu preciso saber o seu "
                           "município — escolha ele no mapa.")
        base["fonte"] = {"nome": "Open-Meteo + IBGE", "periodo": "próximos 7 dias"}
        return base

    hoje = date.today().isoformat()
    futuros = [d for d in prev["dias"] if d.get("data", "") >= hoje][:7]
    if not futuros:
        futuros = prev["dias"][-7:]

    linhas = []
    chuva_total = 0.0
    tmin_geral = None
    tmax_geral = None
    for d in futuros:
        try:
            dt = date.fromisoformat(d["data"])
            rotulo = f"{DIAS_SEM[dt.weekday()]} {dt.day}/{dt.month}"
        except Exception:
            rotulo = d.get("data", "?")
        chuva_txt, forte = _nivel_chuva(d.get("chuva_mm"))
        tmin = d.get("tmin")
        tmax = d.get("tmax")
        try:
            chuva_total += float(d.get("chuva_mm") or 0)
        except (TypeError, ValueError):
            pass
        if isinstance(tmin, (int, float)):
            tmin_geral = tmin if tmin_geral is None else min(tmin_geral, tmin)
        if isinstance(tmax, (int, float)):
            tmax_geral = tmax if tmax_geral is None else max(tmax_geral, tmax)
        temp = ""
        if isinstance(tmin, (int, float)) and isinstance(tmax, (int, float)):
            temp = f"{tmin:.0f}–{tmax:.0f}°C · "
        linhas.append({"rotulo": rotulo, "valor": f"{temp}{chuva_txt}", "aviso": forte})

    local = (prev.get("local") or {}).get("nome") or "sua região"
    partes = [f"Previsão para {local} nos próximos dias."]
    if chuva_total >= 30:
        partes.append(f"Vem chuva: cerca de {chuva_total:.0f} mm somados na semana.")
    elif chuva_total >= 5:
        partes.append(f"Chuva fraca a moderada ({chuva_total:.0f} mm na semana).")
    else:
        partes.append("Pouca ou nenhuma chuva à vista.")
    if isinstance(tmin_geral, (int, float)) and tmin_geral <= 4:
        partes.append(f"Atenção à mínima de {tmin_geral:.0f}°C — risco de geada.")
    elif isinstance(tmax_geral, (int, float)) and tmax_geral >= 34:
        partes.append(f"Calor forte, até {tmax_geral:.0f}°C.")

    leitura = None
    cult = _rotulo_cultura(cultura)
    if cult:
        if chuva_total >= 30:
            leitura = (f"Muita chuva atrapalha pulverização e colheita de {cult.lower()}; "
                       f"bom para quem acabou de plantar.")
        elif chuva_total < 5:
            leitura = (f"Tempo seco ajuda a colher {cult.lower()}, mas atenção à "
                       f"necessidade de água se a lavoura é nova.")

    return {
        "estado": "informativo",
        "titulo": f"Previsão do tempo — {local}",
        "detalhe": " ".join(partes),
        "linhas": linhas,
        "leitura": leitura,
        "fonte": {
            "nome": prev.get("fonte") or "Open-Meteo + IBGE",
            "periodo": "próximos 7 dias",
            "limitacoes": ["Previsão de curto prazo; muda a cada atualização do modelo."],
        },
    }


def _bloco_psr(db, ibge, cultura, uf) -> dict:
    base = {"estado": "sem_dado", "titulo": "Histórico de perdas (seguro rural)"}
    if db is None:
        base["detalhe"] = "O histórico de seguro rural não está disponível agora."
        base["fonte"] = {"nome": "MAPA — Seguro Rural (PSR/SISSER)"}
        return base

    dados = None
    escopo = "uf"
    # 1) município + cultura (dado mais específico)
    if ibge:
        try:
            r = dispatch(db, "buscar_risco_psr",
                         {"cod_ibge": ibge, "cultura": cultura} if cultura
                         else {"cod_ibge": ibge})
            riscos = (r or {}).get("riscos") or []
            # junta eventos de todos os anos do município
            if riscos:
                eventos = {}
                ap = si = 0
                pago = 0.0
                for x in riscos:
                    ap += int(x.get("apolices") or 0)
                    si += int(x.get("sinistros") or 0)
                    pago += float(x.get("pago") or 0)
                    for ev in (x.get("por_evento") or []):
                        nome = (ev or {}).get("evento")
                        if nome:
                            eventos[nome] = eventos.get(nome, 0.0) + float(ev.get("valor") or 0)
                if eventos:
                    top = sorted(eventos.items(), key=lambda kv: -kv[1])[:3]
                    dados = {"apolices": ap, "sinistros": si, "pago": pago,
                             "por_evento": [{"evento": n, "valor": v} for n, v in top]}
                    escopo = "municipio"
        except Exception as e:
            log.warning("psr radar municipio falhou: %r", e)

    # 2) agrega o estado (cultura; senão geral)
    if not dados:
        ag = None
        if cultura:
            ag = agregar_psr_uf(db, uf, cultura)
        if not ag or not ag.get("por_evento"):
            ag = agregar_psr_uf(db, uf, None)
            if ag:
                ag["_geral"] = True
        if ag and ag.get("por_evento"):
            dados = ag
            escopo = "uf"

    if not dados or not dados.get("por_evento"):
        base["detalhe"] = ("Ainda não há registro de perdas de seguro rural para a "
                           "sua região na base pública. Isso é bom sinal — ou pouca "
                           "gente aciona o seguro aqui.")
        base["fonte"] = {"nome": "MAPA — Seguro Rural (PSR/SISSER)", "periodo": "2016–2025"}
        return base

    eventos = dados.get("por_evento") or []
    top = eventos[0]
    nome = str((top or {}).get("evento") or "").strip().lower()
    humano = EVENTO_HUMANO.get(nome, nome or "clima")
    cult = _rotulo_cultura(cultura)
    geral = dados.get("_geral")

    onde = "no seu município" if escopo == "municipio" else f"em {uf}"
    if cult and not geral:
        detalhe = (f"O que mais fez produtores de {cult.lower()} perderem dinheiro "
                   f"{onde} foi {humano}. Veja as três maiores causas de perda:")
    else:
        detalhe = (f"As maiores causas de perda no seguro rural {onde} foram estas. "
                   f"Serve de alerta do que mais ameaça a lavoura por aqui:")

    linhas = []
    for ev in eventos[:3]:
        n = str((ev or {}).get("evento") or "").strip().lower()
        linhas.append({
            "rotulo": EVENTO_HUMANO.get(n, n).capitalize(),
            "valor": _reais(ev.get("valor")),
        })

    destaques = []
    if dados.get("apolices"):
        destaques.append({"rotulo": "Apólices", "valor": f"{int(dados['apolices']):,}".replace(",", "."),
                          "dica": "contratos de seguro na região"})
    if dados.get("sinistros"):
        destaques.append({"rotulo": "Perdas pagas", "valor": f"{int(dados['sinistros']):,}".replace(",", "."),
                          "dica": "vezes que o seguro indenizou"})
    taxa = dados.get("taxa_pct")
    if taxa:
        destaques.append({"rotulo": "Taxa de perda", "valor": f"{taxa:.0f}%".replace(".0", ""),
                          "dica": "apólices que viraram perda"})

    return {
        "estado": "informativo",
        "titulo": "Histórico de perdas (seguro rural)",
        "detalhe": detalhe,
        "destaques": destaques[:3],
        "linhas": linhas,
        "leitura": ("O seguro rural (PSR) devolve parte do prejuízo quando a safra se "
                    "perde por clima. Vale perguntar no banco ou cooperativa no plantio."),
        "fonte": {
            "nome": "MAPA — Seguro Rural (PSR/SISSER)",
            "periodo": dados.get("periodo", "2016–2025"),
            "limitacoes": [
                "Baseado nas apólices do seguro rural, não na produção de cada propriedade.",
                "Mostra o que já causou perda no passado — não é previsão.",
            ],
        },
    }


@router.get("/radar")
def get_radar(uf: str = Query("SP"), ibge: str | None = None,
              cultura: str | None = None, solo: str | None = None):
    """Os 3 cartões do Radar com dado real e estruturado. Nunca raise."""
    uf = (uf or "SP").strip().upper()
    ibge = _ibge7(ibge) or None
    cultura = (cultura or "").strip().lower() or None
    solo = (solo or "").strip().lower() or None
    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em /radar: %r", e)
        db = None

    try:
        zarc = _bloco_zarc(db, ibge, cultura, solo)
    except Exception as e:
        log.warning("bloco zarc falhou: %r", e)
        zarc = {"estado": "sem_dado", "titulo": "Janela de plantio (ZARC)",
                "detalhe": "Não consegui calcular a janela agora.",
                "fonte": {"nome": "MAPA — ZARC"}}
    try:
        clima = _bloco_clima(db, ibge, cultura, uf)
    except Exception as e:
        log.warning("bloco clima falhou: %r", e)
        clima = {"estado": "sem_dado", "titulo": "Previsão do tempo",
                 "detalhe": "Não consegui buscar a previsão agora.",
                 "fonte": {"nome": "Open-Meteo"}}
    try:
        psr = _bloco_psr(db, ibge, cultura, uf)
    except Exception as e:
        log.warning("bloco psr falhou: %r", e)
        psr = {"estado": "sem_dado", "titulo": "Histórico de perdas (seguro rural)",
               "detalhe": "Não consegui buscar o histórico agora.",
               "fonte": {"nome": "MAPA — Seguro Rural (PSR)"}}

    return {
        "clima": clima,
        "zarc": zarc,
        "psr": psr,
        "uf": uf,
        "ibge": ibge,
        "cultura": cultura,
        "data": date.today().isoformat(),
    }
