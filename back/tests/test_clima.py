"""Clima (Open-Meteo) + Decisão do dia: detecção de eventos e endpoint, sem rede."""
from fastapi.testclient import TestClient

from app.main import app
import app.clima as clima
import app.routes.decisao as decisao
from tests.conftest import make_db

client = TestClient(app)


def _prev(dias):
    return {"local": {"nome": "Teste", "uf": "SP", "lat": -22.0, "lon": -47.0},
            "dias": dias, "fonte": clima.FONTE_CLIMA}


def test_detecta_geada():
    hoje = "2026-07-01"
    dias = [
        {"data": "2026-06-30", "tmin": 10, "tmax": 20, "chuva_mm": 0, "futuro": False},
        {"data": hoje, "tmin": 2, "tmax": 18, "chuva_mm": 0, "futuro": True},
    ]
    evs = clima.detectar_eventos(_prev(dias), "Feijão")
    tipos = [e["tipo"] for e in evs]
    assert "geada" in tipos
    g = next(e for e in evs if e["tipo"] == "geada")
    assert g["severidade"] in ("alta", "media")
    assert "decêndio" not in g["mensagem"].lower()


def test_detecta_onda_calor():
    dias = [{"data": f"2026-02-0{i+1}", "tmin": 22, "tmax": 36, "chuva_mm": 0, "futuro": True}
            for i in range(4)]
    evs = clima.detectar_eventos(_prev(dias), "Milho")
    assert any(e["tipo"] == "onda_calor" for e in evs)


def test_detecta_chuva_forte():
    dias = [{"data": "2026-03-10", "tmin": 20, "tmax": 28, "chuva_mm": 55, "futuro": True}]
    evs = clima.detectar_eventos(_prev(dias), "Soja")
    cf = next(e for e in evs if e["tipo"] == "chuva_forte")
    assert cf["severidade"] == "alta"  # >=50mm


def test_detecta_veranico():
    dias = [{"data": f"2026-08-{10+i:02d}", "tmin": 15, "tmax": 30, "chuva_mm": 0, "futuro": True}
            for i in range(8)]
    evs = clima.detectar_eventos(_prev(dias), "Feijão")
    assert any(e["tipo"] == "veranico" for e in evs)


def test_sem_eventos_tempo_calmo():
    dias = [{"data": f"2026-05-0{i+1}", "tmin": 16, "tmax": 26, "chuva_mm": 2, "futuro": True}
            for i in range(5)]
    evs = clima.detectar_eventos(_prev(dias), "Feijão")
    # tempo ameno e sem chuva recente forte -> nenhum alerta de perigo
    assert all(e["tipo"] not in ("geada", "onda_calor", "chuva_forte", "veranico") for e in evs)


def test_previsao_vazia_nao_quebra():
    assert clima.detectar_eventos(None, "Feijão") == []
    assert clima.detectar_eventos({"dias": []}, "Feijão") == []


def test_decisao_dia_fallback_sem_clima(monkeypatch):
    """Sem previsão (rede off) e sem IA, a decisão ainda responde honestamente."""
    monkeypatch.setattr(decisao, "get_db", lambda: make_db())
    monkeypatch.setattr(clima, "buscar_previsao", lambda *a, **k: None)
    r = client.get("/api/decisao-dia?uf=SP&cultura=feijao&ibge=3509502")
    assert r.status_code == 200
    d = r.json()
    assert d["resposta"]
    assert d["origem"] in ("ia", "regras")
    assert isinstance(d["acoes"], list)
    assert d["tem_clima"] is False


def test_decisao_dia_com_clima(monkeypatch):
    """Com previsão de geada (mock), a decisão prioriza o clima e lista ação."""
    monkeypatch.setattr(decisao, "get_db", lambda: make_db())
    dias = [{"data": "2026-07-02", "tmin": 1, "tmax": 17, "chuva_mm": 0, "futuro": True}]
    monkeypatch.setattr(clima, "buscar_previsao", lambda *a, **k: _prev(dias))
    r = client.get("/api/decisao-dia?uf=SP&cultura=feijao&ibge=3509502")
    d = r.json()
    assert d["tem_clima"] is True
    assert any(e["tipo"] == "geada" for e in d["eventos_clima"])
    assert d["severidade"] in ("alta", "media")
    assert len(d["acoes"]) >= 1


def test_tool_buscar_clima(monkeypatch):
    """A tool do agente devolve previsão + eventos (sem rede, mockado)."""
    import app.tools as tools
    dias = [{"data": "2026-07-02", "tmin": 1, "tmax": 17, "chuva_mm": 0, "futuro": True}]
    monkeypatch.setattr(clima, "buscar_previsao", lambda *a, **k: _prev(dias))
    r = tools.dispatch(make_db(), "buscar_clima", {"ibge": "3509502", "cultura": "feijao"})
    assert r.get("local") == "Teste"
    assert any(e["tipo"] == "geada" for e in r.get("eventos", []))
    assert r.get("proximos_dias")
