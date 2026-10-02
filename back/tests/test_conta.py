"""Conta real: signup/login/PATCH/GET conta (FakeDB, sem rede)."""
from fastapi.testclient import TestClient

import app.routes.produtor as prod
from app.main import app
from tests.conftest import FakeCol, make_db

client = TestClient(app)


def _db(monkeypatch, **kw):
    db = make_db(**kw)
    monkeypatch.setattr(prod, "get_db", lambda: db)
    return db


def test_signup_novo_201(monkeypatch):
    _db(monkeypatch, produtores=FakeCol())
    r = client.post("/api/produtor/signup", json={"telefone": "(16) 99999-0001", "nome": "Seu Ze"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["telefone"] == "16999990001"  # digitos apenas
    assert d["nome"] == "Seu Ze"
    assert d["onboardingConcluido"] is False
    assert d["lavouras"] == [] and d["hectares_total"] == 0.0


def test_signup_duplicado_409_e_normaliza(monkeypatch):
    _db(monkeypatch, produtores=FakeCol())
    r1 = client.post("/api/produtor/signup", json={"telefone": "(16) 99999-0002", "nome": "Maria"})
    assert r1.status_code == 201
    # mesmo numero sem mascara -> 409
    r2 = client.post("/api/produtor/signup", json={"telefone": "16999990002", "nome": "Maria 2"})
    assert r2.status_code == 409


def test_login_ok_e_404(monkeypatch):
    _db(monkeypatch, produtores=FakeCol())
    client.post("/api/produtor/signup", json={"telefone": "16999990003", "nome": "Joao"})
    rok = client.post("/api/produtor/login", json={"telefone": "(16) 99999-0003"})
    assert rok.status_code == 200, rok.text
    assert rok.json()["nome"] == "Joao"
    r404 = client.post("/api/produtor/login", json={"telefone": "16999990099"})
    assert r404.status_code == 404


def test_patch_nome_municipio_lavouras_hectares(monkeypatch):
    _db(monkeypatch, produtores=FakeCol())
    r = client.post("/api/produtor/signup", json={"telefone": "16999990004", "nome": "Ana"})
    pid = r.json()["id"]
    rp = client.patch(f"/api/produtor/{pid}", json={
        "nome": "Ana Silva",
        "municipio": "Araraquara",
        "uf": "SP",
        "lavouras": [
            {"cultura": "milho", "area_ha": 2.0},
            {"cultura": "feijao", "area_ha": 3.5},
        ],
    })
    assert rp.status_code == 200, rp.text
    d = rp.json()
    assert d["nome"] == "Ana Silva" and d["municipio"] == "Araraquara"
    assert d["hectares_total"] == 5.5
    # GET conta cheia
    rg = client.get(f"/api/produtor/{pid}")
    assert rg.status_code == 200
    g = rg.json()
    assert g["municipio"] == "Araraquara" and g["uf"] == "SP"
    assert g["hectares_total"] == 5.5 and len(g["lavouras"]) == 2


def test_patch_cod_ibge_recomputa_solo(monkeypatch):
    db = _db(monkeypatch,
             produtores=FakeCol(),
             zarc=FakeCol([{"cod_ibge": "3503208", "solo_canonico": "argiloso"}]))
    r = client.post("/api/produtor/signup", json={"telefone": "16999990005", "nome": "Bia"})
    pid = r.json()["id"]
    rp = client.patch(f"/api/produtor/{pid}", json={"cod_ibge": "3503208"})
    assert rp.status_code == 200, rp.text
    assert rp.json()["solo_inferido"] == "argiloso"
    assert db.produtores.docs[0]["telefone"] == "16999990005"
