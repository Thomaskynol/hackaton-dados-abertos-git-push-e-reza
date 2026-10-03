from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_chat_praga():
    res = client.post("/api/chat", json={"produtor_id": "abc123", "mensagem": "minha uva tá com míldio"})
    assert res.status_code == 200
    data = res.json()
    assert data["intencao"] == "PRAGA"
    assert "Agrofit" in data["fonte"]
    assert "dados" in data


def test_chat_planejamento():
    res = client.post("/api/chat", json={"produtor_id": "abc123", "mensagem": "quando planto feijao?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intencao"] == "PLANEJAMENTO"
    assert "ZARC" in data["fonte"]


def test_chat_fallback(monkeypatch):
    import app.routes.chat as chat
    monkeypatch.setattr(chat, "responder_com_tools", lambda *a, **k: (None, []))
    monkeypatch.setattr(chat, "gerar_resposta", lambda *a, **k: None)
    res = client.post("/api/chat", json={"produtor_id": "abc123", "mensagem": "xyz123"})
    assert res.status_code == 200
    data = res.json()
    assert data["erro"] == "NAO_ENTENDI"
    assert len(data["sugestoes"]) > 0


def test_onboarding():
    res = client.post("/api/onboarding", json={"telefone": "+5519999999999", "etapa": 1, "resposta": "Antônio"})
    assert res.status_code == 200
    data = res.json()
    assert data["proximo_passo"] == 2
    assert "Antônio" in data["pergunta"]


def test_get_produtor():
    res = client.get("/api/produtor/abc123")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "abc123"
    assert data["nome"] == "Antônio"
    assert len(data["lavouras"]) > 0


def test_post_produtor():
    payload = {
        "nome": "Antônio",
        "telefone": "+5519999999999",
        "codigo_ibge": "3503307",
        "municipio": "Araraquara",
        "uf": "SP",
        "lavouras": [{"cultura": "uva", "area_ha": 5.0, "solo": 1, "irrigacao": False}],
    }
    res = client.post("/api/produtor", json=payload)
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_get_alertas():
    # endpoint real: alertas calculados do ZARC/PSR; estrutura sempre presente,
    # lista pode vir vazia honestamente quando não há aviso para o filtro.
    res = client.get("/api/alertas?uf=SP&ibge=3503208&cultura=feijao")
    assert res.status_code == 200
    data = res.json()
    assert "alertas" in data and isinstance(data["alertas"], list)
    assert "vazio_ok" in data


def test_get_alertas_legado_vazio():
    # rota antiga por id (compat): responde 200 com lista (sem produtor real -> vazia).
    res = client.get("/api/alertas/abc123")
    assert res.status_code == 200
    assert "alertas" in res.json()


def test_simular_alerta():
    res = client.post("/api/alertas/simular", json={"produtor_id": "abc123", "tipo": "geada"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["alerta"]["tipo"] == "geada"
