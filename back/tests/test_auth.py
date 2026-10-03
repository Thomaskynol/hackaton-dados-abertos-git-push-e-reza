"""Testes de autenticação (PIN + token) e extração do cadastro por chat."""
import importlib
import random

from fastapi.testclient import TestClient

from app.main import app
from app import auth, extracao

client = TestClient(app)


def _tel():
    return "11" + "".join(str(random.randint(0, 9)) for _ in range(9))


# --------------------------------------------------------------- PIN / hash

def test_pin_valido():
    assert auth.pin_valido("1234")
    assert auth.pin_valido("123456")
    assert not auth.pin_valido("123")       # curto
    assert not auth.pin_valido("1234567")   # longo
    assert not auth.pin_valido("12ab")      # não numérico


def test_hash_e_verifica_pin():
    salt, h = auth.hash_pin("4321")
    assert auth.verificar_pin("4321", salt, h)
    assert not auth.verificar_pin("0000", salt, h)
    # salt novo a cada chamada -> hashes diferentes para o mesmo PIN
    salt2, h2 = auth.hash_pin("4321")
    assert h != h2


# --------------------------------------------------------------- signup/login

def test_signup_com_pin_devolve_token_sem_vazar_hash():
    tel = _tel()
    r = client.post("/api/produtor/signup", json={"telefone": tel, "nome": "Zé", "pin": "1234"})
    assert r.status_code == 201
    j = r.json()
    assert j.get("token")
    assert j.get("tem_pin") is True
    assert "pin_hash" not in j and "pin_salt" not in j


def test_signup_pin_invalido_422():
    tel = _tel()
    r = client.post("/api/produtor/signup", json={"telefone": tel, "nome": "Zé", "pin": "12"})
    assert r.status_code == 422


def test_login_pin_errado_e_certo():
    tel = _tel()
    client.post("/api/produtor/signup", json={"telefone": tel, "nome": "Ana", "pin": "9988"})
    # sem PIN numa conta com PIN -> 422
    assert client.post("/api/produtor/login", json={"telefone": tel}).status_code == 422
    # PIN errado -> 401
    assert client.post("/api/produtor/login", json={"telefone": tel, "pin": "0000"}).status_code == 401
    # PIN certo -> 200 + token
    ok = client.post("/api/produtor/login", json={"telefone": tel, "pin": "9988"})
    assert ok.status_code == 200 and ok.json().get("token")


def test_me_e_logout():
    tel = _tel()
    r = client.post("/api/produtor/signup", json={"telefone": tel, "nome": "Beto", "pin": "4567"})
    tok = r.json()["token"]
    pid = r.json()["id"]
    me = client.get("/api/produtor/me", headers={"Authorization": f"Bearer {tok}"})
    assert me.status_code == 200 and me.json()["id"] == pid
    # sem token -> 401
    assert client.get("/api/produtor/me").status_code == 401
    # logout revoga
    client.post("/api/produtor/logout", headers={"Authorization": f"Bearer {tok}"})
    assert client.get("/api/produtor/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


# --------------------------------------------------------------- extração chat

def test_separar_cidade_uf():
    assert extracao.separar_cidade_uf("Araraquara - SP") == ("Araraquara", "SP")
    assert extracao.separar_cidade_uf("Rio Verde GO") == ("Rio Verde", "GO")
    cidade, uf = extracao.separar_cidade_uf("Uberlândia Minas Gerais")
    assert uf == "MG"


def test_extrair_culturas_e_area():
    assert set(extracao.extrair_culturas("planto feijão e milho")) == {"feijao", "milho"}
    assert extracao.extrair_culturas("não sei") == []
    assert extracao.extrair_area("uns 10,5 hectares") == 10.5
    assert extracao.extrair_area("sem número") is None


def test_onboarding_etapa1_compat():
    r = client.post("/api/onboarding", json={"telefone": "+5519999999999", "etapa": 1, "resposta": "Antônio"})
    assert r.status_code == 200
    j = r.json()
    assert j["proximo_passo"] == 2
    assert "Antônio" in j["pergunta"]


# --------------------------------------------------------------- proteção de rota

def test_auth_obrigatoria_protege_conta(monkeypatch):
    """Com AUTH_OBRIGATORIA=1, GET/PATCH /produtor/{id} exige o dono do token."""
    monkeypatch.setenv("AUTH_OBRIGATORIA", "1")

    tel_a = _tel()
    ra = client.post("/api/produtor/signup", json={"telefone": tel_a, "nome": "Dono", "pin": "1111"})
    tok_a, id_a = ra.json()["token"], ra.json()["id"]

    tel_b = _tel()
    rb = client.post("/api/produtor/signup", json={"telefone": tel_b, "nome": "Outro", "pin": "2222"})
    tok_b = rb.json()["token"]

    # sem token -> 401
    assert client.get(f"/api/produtor/{id_a}").status_code == 401
    # token de outro -> 403
    assert client.get(f"/api/produtor/{id_a}",
                      headers={"Authorization": f"Bearer {tok_b}"}).status_code == 403
    # dono -> 200
    assert client.get(f"/api/produtor/{id_a}",
                      headers={"Authorization": f"Bearer {tok_a}"}).status_code == 200
    # PATCH sem token -> 401
    assert client.patch(f"/api/produtor/{id_a}", json={"nome": "x"}).status_code == 401
    # PATCH dono -> 200
    assert client.patch(f"/api/produtor/{id_a}", json={"nome": "Dono 2"},
                        headers={"Authorization": f"Bearer {tok_a}"}).status_code == 200
