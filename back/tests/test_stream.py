"""SSE /api/chat/stream sem rede (sem chave real)."""
from fastapi.testclient import TestClient

from app.main import app


def _eventos(texto: str):
    evs = []
    for bloco in texto.strip().split("\n\n"):
        ev, data = "message", None
        for linha in bloco.split("\n"):
            if linha.startswith("event:"):
                ev = linha[6:].strip()
            elif linha.startswith("data:"):
                import json
                data = json.loads(linha[5:].strip())
        evs.append((ev, data))
    return evs


def test_stream_fallback_sem_chave(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    res = TestClient(app).post(
        "/api/chat/stream", json={"produtor_id": "t1", "mensagem": "quando planto feijao?"}
    )
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    evs = _eventos(res.text)
    nomes = [e for e, _ in evs]
    assert nomes[0] == "meta" and "delta" in nomes and nomes[-1] == "done"
    delta = next(d for e, d in evs if e == "delta")
    assert delta["texto"].strip()


def test_stream_mockado_meta_delta_done(monkeypatch):
    import app.routes.chat as chat

    monkeypatch.setattr(chat, "responder_com_tools_stream", lambda *a, **k: iter([]))
    monkeypatch.setattr(chat, "gerar_resposta_stream", lambda *a, **k: iter(["Olá ", "produtor"]))
    res = TestClient(app).post(
        "/api/chat/stream", json={"produtor_id": "t1", "mensagem": "minha uva tá com míldio"}
    )
    assert res.status_code == 200
    evs = _eventos(res.text)
    nomes = [e for e, _ in evs]
    assert nomes == ["meta", "delta", "delta", "done"]
    assert evs[0][1]["intencao"] == "PRAGA"
    assert "Agrofit" in evs[0][1]["fonte"]
    assert "".join(d["texto"] for e, d in evs if e == "delta") == "Olá produtor"


def test_stream_intent_nao_suportada(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    import app.routes.chat as chat
    monkeypatch.setattr(chat, "responder_com_tools_stream", lambda *a, **k: iter([]))
    monkeypatch.setattr(chat, "gerar_resposta_stream", lambda *a, **k: iter([]))
    res = TestClient(app).post(
        "/api/chat/stream", json={"produtor_id": "t1", "mensagem": "xyz123"}
    )
    assert res.status_code == 200
    evs = _eventos(res.text)
    assert evs[0][0] == "meta"
    assert evs[0][1]["intencao"] == "NAO_ENTENDI"
    assert evs[-1][0] == "done"
