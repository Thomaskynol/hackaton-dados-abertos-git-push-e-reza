"""Clima real para alertas e Decisão do dia (Open-Meteo, grátis e sem chave).

Pipeline:
  1. cod_ibge -> nome/UF (API de localidades do IBGE)
  2. nome/UF -> latitude/longitude (geocoding do Open-Meteo)
  3. lat/lon -> previsão diária (Open-Meteo forecast): chuva dos últimos 3 dias
     e dos próximos 7, com temperatura mínima e máxima.

Tudo cacheado no Mongo (coleção `geo_municipios` para coordenadas, `clima_cache`
para a previsão com TTL curto), para não martelar as APIs. Nunca levanta exceção:
sem rede/sem dado -> devolve None e o chamador segue com fallback honesto.

Ligado/desligado por env CLIMA_AUTO (default ligado).
"""
import gzip
import json
import logging
import os
import time
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)

IBGE_LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"
OPENMETEO_GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
OPENMETEO_FORECAST = "https://api.open-meteo.com/v1/forecast"

FONTE_CLIMA = "Open-Meteo (previsão) + IBGE (localização)"
TTL_PREVISAO_S = 3 * 3600          # previsão revalida a cada ~3h
TTL_COORD_S = 365 * 86400          # coordenada de município praticamente não muda


def _auto_ligado():
    return os.getenv("CLIMA_AUTO", "1").strip().lower() not in ("0", "false", "no")


def _ibge7(codigo):
    s = "".join(ch for ch in str(codigo or "") if ch.isdigit())
    return s[:7] if len(s) >= 7 else s


def _get_json(url, timeout=12, tentativas=2, espera=1.2):
    """GET JSON robusto a gzip. None em falha (nunca raise)."""
    for i in range(tentativas):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "AgroPilot/1.0",
                              "Accept": "application/json",
                              "Accept-Encoding": "gzip, identity"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                return json.loads(raw.decode("utf-8"))
        except Exception as e:
            if i == tentativas - 1:
                log.info("clima: fonte indisponível (%s): %r", url[:70], e)
                return None
            time.sleep(espera)
    return None


# ------------------------------------------------------------------ #
# 1 + 2) cod_ibge -> coordenadas (com cache no Mongo)                 #
# ------------------------------------------------------------------ #
def _coord_do_cache(db, ibge):
    if db is None:
        return None
    try:
        doc = db.geo_municipios.find_one({"_id": ibge})
    except Exception:
        return None
    if not doc:
        return None
    if (int(time.time()) - int(doc.get("ts") or 0)) > TTL_COORD_S:
        return None
    if doc.get("lat") is None or doc.get("lon") is None:
        return None
    return doc


def _salvar_coord(db, ibge, dados):
    if db is None:
        return
    try:
        db.geo_municipios.update_one(
            {"_id": ibge}, {"$set": {**dados, "ts": int(time.time())}}, upsert=True)
    except Exception:
        pass


def resolver_coordenadas(db, ibge, nome=None, uf=None):
    """cod_ibge -> {lat, lon, nome, uf}. Usa cache; senão IBGE + Open-Meteo. None se falhar."""
    ibge = _ibge7(ibge)
    if not ibge:
        # dá pra geocodificar só por nome+uf se vier do perfil
        if not (nome and uf):
            return None

    cache = _coord_do_cache(db, ibge) if ibge else None
    if cache:
        return {"lat": cache["lat"], "lon": cache["lon"],
                "nome": cache.get("nome"), "uf": cache.get("uf")}

    # 1) nome/UF pelo IBGE (se não vieram do perfil)
    if ibge and not (nome and uf):
        loc = _get_json(f"{IBGE_LOCALIDADES}/{ibge}")
        if loc and isinstance(loc, dict):
            nome = nome or loc.get("nome")
            try:
                uf = uf or loc["microrregiao"]["mesorregiao"]["UF"]["sigla"]
            except Exception:
                pass
    if not nome:
        return None

    # 2) nome+UF -> lat/lon pelo geocoding do Open-Meteo
    q = urllib.parse.urlencode({"name": nome, "count": 10, "language": "pt", "country": "BR"})
    geo = _get_json(f"{OPENMETEO_GEOCODE}?{q}")
    resultados = (geo or {}).get("results") or []
    if not resultados:
        return None
    # escolhe o resultado da UF certa quando possível
    escolhido = None
    if uf:
        for r in resultados:
            if (r.get("admin1_id") and str(r.get("admin1", "")).strip()):
                # Open-Meteo retorna admin1 como nome do estado; casa por sigla via mapa simples
                if _sigla_estado(r.get("admin1")) == uf.upper():
                    escolhido = r
                    break
    escolhido = escolhido or resultados[0]
    lat, lon = escolhido.get("latitude"), escolhido.get("longitude")
    if lat is None or lon is None:
        return None
    dados = {"lat": float(lat), "lon": float(lon),
             "nome": nome, "uf": (uf or "").upper() or None}
    if ibge:
        _salvar_coord(db, ibge, dados)
    return dados


# nome do estado -> sigla (para casar o geocoding com a UF do produtor)
_ESTADOS = {
    "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM", "bahia": "BA",
    "ceará": "CE", "distrito federal": "DF", "espírito santo": "ES", "goiás": "GO",
    "maranhão": "MA", "mato grosso": "MT", "mato grosso do sul": "MS",
    "minas gerais": "MG", "pará": "PA", "paraíba": "PB", "paraná": "PR",
    "pernambuco": "PE", "piauí": "PI", "rio de janeiro": "RJ",
    "rio grande do norte": "RN", "rio grande do sul": "RS", "rondônia": "RO",
    "roraima": "RR", "santa catarina": "SC", "são paulo": "SP", "sergipe": "SE",
    "tocantins": "TO",
}


def _sigla_estado(nome):
    return _ESTADOS.get((nome or "").strip().lower(), "")


# ------------------------------------------------------------------ #
# 3) coordenadas -> previsão (com cache curto)                        #
# ------------------------------------------------------------------ #
def _previsao_do_cache(db, ibge):
    if db is None or not ibge:
        return None
    try:
        doc = db.clima_cache.find_one({"_id": ibge})
    except Exception:
        return None
    if not doc:
        return None
    if (int(time.time()) - int(doc.get("ts") or 0)) > TTL_PREVISAO_S:
        return None
    return doc.get("previsao")


def _salvar_previsao(db, ibge, previsao):
    if db is None or not ibge:
        return
    try:
        db.clima_cache.update_one(
            {"_id": ibge}, {"$set": {"previsao": previsao, "ts": int(time.time())}}, upsert=True)
    except Exception:
        pass


def buscar_previsao(db, ibge=None, nome=None, uf=None):
    """Previsão diária para o município. Dict com dias, ou None (nunca raise).

    Retorno:
      {
        "local": {"nome","uf","lat","lon"},
        "dias": [{"data","tmin","tmax","chuva_mm","futuro":bool}],
        "fonte": "...",
      }
    """
    if not _auto_ligado():
        return None
    ibge = _ibge7(ibge)

    cache = _previsao_do_cache(db, ibge) if ibge else None
    if cache:
        return cache

    coord = resolver_coordenadas(db, ibge, nome, uf)
    if not coord:
        return None

    q = urllib.parse.urlencode({
        "latitude": round(coord["lat"], 4),
        "longitude": round(coord["lon"], 4),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "past_days": 3,
        "forecast_days": 7,
        "timezone": "America/Sao_Paulo",
    })
    data = _get_json(f"{OPENMETEO_FORECAST}?{q}", timeout=15)
    daily = (data or {}).get("daily") or {}
    tempos = daily.get("time") or []
    if not tempos:
        return None

    import datetime as _dt
    hoje = _dt.date.today().isoformat()
    tmax = daily.get("temperature_2m_max") or []
    tmin = daily.get("temperature_2m_min") or []
    chuva = daily.get("precipitation_sum") or []
    dias = []
    for i, t in enumerate(tempos):
        dias.append({
            "data": t,
            "tmax": tmax[i] if i < len(tmax) else None,
            "tmin": tmin[i] if i < len(tmin) else None,
            "chuva_mm": chuva[i] if i < len(chuva) else None,
            "futuro": t >= hoje,
        })

    previsao = {
        "local": {"nome": coord.get("nome"), "uf": coord.get("uf"),
                  "lat": coord["lat"], "lon": coord["lon"]},
        "dias": dias,
        "fonte": FONTE_CLIMA,
    }
    _salvar_previsao(db, ibge, previsao)
    return previsao


# ------------------------------------------------------------------ #
# 4) Detector de eventos climáticos a partir da previsão              #
# ------------------------------------------------------------------ #
# Limiares simples e honestos (agronômicos de bolso). Não são verdade
# absoluta — são gatilhos de ATENÇÃO, sempre com o dado por trás.
_GEADA_TMIN = 3.0        # °C: risco de geada quando a mínima chega perto de 0
_CALOR_TMAX = 34.0       # °C: calor forte
_CALOR_DIAS = 3          # dias seguidos quentes = onda de calor
_CHUVA_FORTE_DIA = 30.0  # mm num dia só = chuva forte
_VERANICO_DIAS = 7       # dias secos seguidos à frente = veranico
_CHUVA_SECO_MM = 1.0     # abaixo disso o dia conta como "seco"


def _fmt_data(iso):
    """'2026-10-06' -> '06/10'."""
    try:
        _, m, d = iso.split("-")
        return f"{d}/{m}"
    except Exception:
        return iso


def detectar_eventos(previsao, cultura_label=None):
    """Lê a previsão e devolve eventos climáticos acionáveis (lista de dicts).

    Cada evento: {tipo, severidade, titulo, mensagem, fonte, janela}.
    Lista vazia = tempo sem nada que mereça aviso (também é informação útil).
    """
    if not previsao or not previsao.get("dias"):
        return []
    dias = previsao["dias"]
    futuros = [d for d in dias if d.get("futuro")]
    passados = [d for d in dias if not d.get("futuro")]
    cult = (cultura_label or "a lavoura").lower()
    eventos = []

    # --- Geada à frente (mínima perigosa nos próximos dias) ---
    frios = [d for d in futuros if _num(d.get("tmin")) is not None and _num(d["tmin"]) <= _GEADA_TMIN]
    if frios:
        d0 = frios[0]
        tmin = _num(d0["tmin"])
        eventos.append({
            "tipo": "geada",
            "severidade": "alta" if tmin <= 1.0 else "media",
            "titulo": "Risco de geada",
            "mensagem": (
                f"A temperatura pode cair para cerca de {tmin:.0f}°C no dia {_fmt_data(d0['data'])}. "
                f"Geada queima a folha e pode comprometer {cult}. Se puder, proteja as áreas baixas "
                f"e evite irrigar à noite nesses dias."
            ),
            "janela": _fmt_data(d0["data"]),
        })

    # --- Onda de calor (vários dias seguidos de calor forte) ---
    seq = _maior_sequencia(futuros, lambda d: _num(d.get("tmax")) is not None and _num(d["tmax"]) >= _CALOR_TMAX)
    if seq and len(seq) >= _CALOR_DIAS:
        tmax = max(_num(d["tmax"]) for d in seq)
        eventos.append({
            "tipo": "onda_calor",
            "severidade": "media",
            "titulo": "Onda de calor chegando",
            "mensagem": (
                f"Vêm {len(seq)} dias seguidos de calor forte (até ~{tmax:.0f}°C), "
                f"de {_fmt_data(seq[0]['data'])} a {_fmt_data(seq[-1]['data'])}. "
                f"Calor assim estressa {cult} e seca o solo rápido — reforce a rega cedo ou no fim do dia "
                f"e evite trabalho pesado no sol do meio-dia."
            ),
            "janela": f"{_fmt_data(seq[0]['data'])}–{_fmt_data(seq[-1]['data'])}",
        })

    # --- Chuva forte à frente ---
    forte = [d for d in futuros if _num(d.get("chuva_mm")) is not None and _num(d["chuva_mm"]) >= _CHUVA_FORTE_DIA]
    if forte:
        d0 = max(forte, key=lambda d: _num(d["chuva_mm"]))
        mm = _num(d0["chuva_mm"])
        eventos.append({
            "tipo": "chuva_forte",
            "severidade": "alta" if mm >= 50 else "media",
            "titulo": "Chuva forte à vista",
            "mensagem": (
                f"Previsão de chuva forte no dia {_fmt_data(d0['data'])} (cerca de {mm:.0f} mm). "
                f"Segure pulverização e colheita para esse dia, e cuide da drenagem para a água não "
                f"empoçar na lavoura."
            ),
            "janela": _fmt_data(d0["data"]),
        })

    # --- Veranico (sequência longa de dias secos à frente) ---
    secos = _maior_sequencia(futuros, lambda d: _num(d.get("chuva_mm")) is not None and _num(d["chuva_mm"]) < _CHUVA_SECO_MM)
    if secos and len(secos) >= _VERANICO_DIAS and not forte:
        eventos.append({
            "tipo": "veranico",
            "severidade": "media",
            "titulo": "Período seco pela frente",
            "mensagem": (
                f"Não há chuva prevista por cerca de {len(secos)} dias. "
                f"Se {cult} estiver em fase sensível, planeje a irrigação e segure a adubação "
                f"que depende de chuva."
            ),
            "janela": f"{_fmt_data(secos[0]['data'])}–{_fmt_data(secos[-1]['data'])}",
        })

    # --- Choveu nos últimos dias (contexto, não alerta de perigo) ---
    chuva_recente = sum(_num(d.get("chuva_mm")) or 0 for d in passados)
    if chuva_recente >= 10 and not forte:
        eventos.append({
            "tipo": "chuva_recente",
            "severidade": "baixa",
            "titulo": "Choveu bem nos últimos dias",
            "mensagem": (
                f"Nos últimos dias caíram cerca de {chuva_recente:.0f} mm de chuva na sua região. "
                f"Solo úmido é bom para o plantio e para a adubação pegar — mas espere firmar antes "
                f"de entrar com máquina para não compactar."
            ),
            "janela": "últimos 3 dias",
        })

    for e in eventos:
        e["fonte"] = FONTE_CLIMA
    return eventos


def _num(v):
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _maior_sequencia(dias, cond):
    """Maior sequência consecutiva de dias que satisfazem cond(d)."""
    melhor, atual = [], []
    for d in dias:
        if cond(d):
            atual.append(d)
            if len(atual) > len(melhor):
                melhor = list(atual)
        else:
            atual = []
    return melhor
