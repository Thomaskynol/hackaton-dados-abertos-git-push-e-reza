"""Alertas reais: lógica de decêndio e geração ZARC/PSR (FakeDB, sem rede)."""
from datetime import date

from fastapi.testclient import TestClient

from app.main import app
import app.routes.alertas as alertas
from app.routes.alertas import _decendio_de, _alerta_janela, _alerta_risco
from tests.conftest import FakeCol, make_db

client = TestClient(app)
IBGE = "3503208"


def test_decendio_limites():
    assert _decendio_de(date(2026, 1, 1)) == 1
    assert _decendio_de(date(2026, 1, 10)) == 1
    assert _decendio_de(date(2026, 1, 11)) == 2
    assert _decendio_de(date(2026, 12, 31)) == 36


def test_alerta_janela_com_zarc(monkeypatch):
    """ZARC com janela aberta até o fim do ano -> alerta real (não exemplo)."""
    monkeypatch.setattr(
        alertas, "dispatch",
        lambda db, name, args: {"janelas": [{"cultura": "feijao", "abertos": [34, 35, 36]}]}
        if name == "buscar_janelas_zarc" else {},
    )
    a = _alerta_janela(object(), IBGE, "feijao", "SP")
    assert a is not None
    assert a["tipo"] == "janela_zarc"
    # mensagem humana: sem jargão "decêndio"
    assert "decêndio" not in a["mensagem"].lower()
    assert "plantar" in a["mensagem"].lower()


def test_alerta_janela_sem_zarc():
    a = _alerta_janela(make_db(), IBGE, "feijao", "SP")
    assert a is None


def test_alerta_risco_por_evento():
    """PSR com evento de perda -> alerta de risco histórico humano."""
    db = make_db(psr_agregado=FakeCol([{
        "cod_ibge": IBGE, "cultura_canonica": "feijao", "uf": "SP", "ano": 2020,
        "total_apolices": 10, "total_sinistros": 4, "taxa_sinistro_pct": 40.0,
        "total_pago_reais": 5000.0,
        "por_evento": [{"evento": "seca", "apolices": 3, "valor": 5000.0}],
    }]))
    a = _alerta_risco(db, IBGE, "feijao", "SP")
    assert a is not None and a["tipo"] == "risco_historico"
    assert "estiagem" in a["mensagem"].lower()  # "seca" traduzido
    assert "apólice" not in a["mensagem"].lower()


def test_endpoint_alertas_estrutura(monkeypatch):
    monkeypatch.setattr(alertas, "get_db", lambda: make_db())
    res = client.get("/api/alertas?uf=SP&cultura=feijao")
    assert res.status_code == 200
    d = res.json()
    assert isinstance(d["alertas"], list) and "vazio_ok" in d
