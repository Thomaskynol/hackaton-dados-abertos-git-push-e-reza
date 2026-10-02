"""Testes da camada LLM (sem rede: httpx mockado, sem chave real)."""
import httpx

import app.llm as llm
from app.llm import gerar_resposta


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_sem_chave_retorna_none(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert gerar_resposta("PRAGA", "mildio?", "fonte: Agrofit") is None


def test_contexto_vazio_retorna_none(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    assert gerar_resposta("PRAGA", "mildio?", "  ") is None


def test_sucesso_retorna_texto(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setattr(
        httpx, "post",
        lambda *a, **k: _Resp({"choices": [{"message": {"content": "  Olá, use X  "}}]}),
    )
    assert gerar_resposta("PRAGA", "mildio?", "fonte: Agrofit") == "Olá, use X"


def test_falha_http_retorna_none(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    def _boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", _boom)
    assert gerar_resposta("PRAGA", "mildio?", "fonte: Agrofit") is None


def test_timeout_retorna_none(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    def _boom(*a, **k):
        raise httpx.TimeoutException("slow")

    monkeypatch.setattr(httpx, "post", _boom)
    assert gerar_resposta("PLANEJAMENTO", "quando planto?", "fonte: ZARC") is None


def test_resposta_vazia_retorna_none(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: _Resp({"choices": []})
    )
    assert gerar_resposta("PRAGA", "mildio?", "fonte: Agrofit") is None


def test_chat_usa_llm_quando_disponivel(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setattr(llm, "gerar_resposta", lambda *a, **k: "texto LLM")
    # garante que rota lê o mock (chat importa função por nome: repatch no namespace da rota)
    import app.routes.chat as chat

    monkeypatch.setattr(chat, "gerar_resposta", lambda *a, **k: "texto LLM")
    res = TestClient(app).post(
        "/api/chat", json={"produtor_id": "abc123", "mensagem": "minha uva tá com míldio"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["resposta"] == "texto LLM"
    assert data["intencao"] == "PRAGA"
    assert "Agrofit" in data["fonte"]


def test_chat_fallback_sem_llm(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.routes.chat as chat

    monkeypatch.setattr(chat, "gerar_resposta", lambda *a, **k: None)
    res = TestClient(app).post(
        "/api/chat", json={"produtor_id": "abc123", "mensagem": "quando planto feijao?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intencao"] == "PLANEJAMENTO"
    assert "ZARC" in data["fonte"]
