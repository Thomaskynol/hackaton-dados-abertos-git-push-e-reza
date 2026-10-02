"""Produtor upsert/get Mongo + solo_inferido + indexes (FakeDB)."""
from fastapi.testclient import TestClient

import app.routes.produtor as prod
from app.main import app
from tests.conftest import FakeCol, make_db

client = TestClient(app)

PAYLOAD = {
    "nome": "Maria", "telefone": "+5519888888888",
    "codigo_ibge": "3503208", "municipio": "Araraquara", "uf": "SP",
    "lavouras": [{"cultura": "milho", "area_ha": 2.0, "solo": 1, "irrigacao": False}],
}


def test_upsert_cria_e_atualiza_mesmo_telefone(monkeypatch):
    db = make_db(
        produtores=FakeCol(),
        zarc=FakeCol([{"cod_ibge": "3503208", "solo_canonico": "argiloso"}]),
    )
    monkeypatch.setattr(prod, "get_db", lambda: db)
    r1 = client.post("/api/produtor", json=PAYLOAD)
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["ok"] is True and d1["solo_inferido"] == "argiloso"
    assert d1["codigo_ibge"] == "3503208" and d1["cod_ibge"] == "3503208"
    r2 = client.post("/api/produtor", json={**PAYLOAD, "nome": "Maria Silva"})
    d2 = r2.json()
    assert d2["id"] == d1["id"]  # upsert por telefone, não duplica
    assert d2["nome"] == "Maria Silva"
    assert len(db.produtores.docs) == 1
    # GET por id lê do Mongo
    r3 = client.get(f"/api/produtor/{d1['id']}")
    assert r3.status_code == 200 and r3.json()["nome"] == "Maria Silva"


def test_upsert_preserva_solo_front_e_sem_zarc(monkeypatch):
    db = make_db(produtores=FakeCol())
    monkeypatch.setattr(prod, "get_db", lambda: db)
    r = client.post("/api/produtor", json={**PAYLOAD, "solo_inferido": "media"})
    assert r.json()["solo_inferido"] == "media"  # front manda → não sobrescreve
    db2 = make_db(produtores=FakeCol())  # sem zarc → sem solo, mas cria igual
    monkeypatch.setattr(prod, "get_db", lambda: db2)
    r2 = client.post("/api/produtor", json={**PAYLOAD, "telefone": "+5519777777777"})
    assert r2.status_code == 200 and "solo_inferido" not in r2.json()


def test_sem_db_fallback_nao_db_path(monkeypatch):
    monkeypatch.setattr(prod, "get_db", lambda: None)
    r = client.post("/api/produtor", json=PAYLOAD)
    assert r.status_code == 200 and r.json()["ok"] is True and r.json()["id"]
    r2 = client.get("/api/produtor/qualquer-id")
    assert r2.status_code == 200 and r2.json()["id"] == "qualquer-id"


def test_indexes_novas_colecoes():
    from app.memoria import ensure_indexes_sessoes
    db = make_db()
    prod._ensure_indexes(db)
    ensure_indexes_sessoes(db)
    idx = {c: [k for k, _ in getattr(db, c).indexes] for c in
           ("produtores", "sessoes", "mensagens", "memorias")}
    assert "telefone" in idx["produtores"] and "id" in idx["produtores"]
    assert "produtor_id" in idx["sessoes"]
    assert "sessao_id" in idx["mensagens"]
    assert "produtor_id" in idx["memorias"]
