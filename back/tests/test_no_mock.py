"""LLM-first: nenhum intent retorna mock fixo (sem rede: LLM monkeypatchado)."""
import json

from fastapi.testclient import TestClient

from app.main import app
import app.routes.chat as chat


def _eventos(texto: str):
    evs = []
    for bloco in texto.strip().split("\n\n"):
        ev, data = "message", None
        for linha in bloco.split("\n"):
            if linha.startswith("event:"):
                ev = linha[6:].strip()
            elif linha.startswith("data:"):
                data = json.loads(linha[5:].strip())
        evs.append((ev, data))
    return evs


def _msgs_perfil():
    # mensagens classificadas como PERFIL pelo router de intenção
    return ["meu perfil", "minhas lavouras", "meu cadastro"]


def test_perfil_sem_collection_nao_contem_antonio(monkeypatch):
    monkeypatch.setattr(chat, "responder_com_tools",
                        lambda *a, **k: ("resposta LLM perfil",
                                         [{"name": "buscar_municipio", "args": {}, "result_resumo": {}}]))
    res = TestClient(app).post(
        "/api/chat", json={"produtor_id": "x", "mensagem": _msgs_perfil()[0]}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intencao"] == "PERFIL"
    assert data["resposta"] == "resposta LLM perfil"
    assert "Antônio" not in data["resposta"]


def test_clima_passa_pelo_llm(monkeypatch):
    chamadas = []

    def _fake_tools(mensagem, db=None, produtor_id=None, **k):
        chamadas.append(mensagem)
        return ("resposta LLM clima",
                [{"name": "buscar_janelas_zarc", "args": {}, "result_resumo": {}}])

    monkeypatch.setattr(chat, "responder_com_tools", _fake_tools)
    res = TestClient(app).post(
        "/api/chat", json={"produtor_id": "x", "mensagem": "vai gear?"}
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intencao"] == "CLIMA"
    assert data["resposta"] == "resposta LLM clima"
    assert chamadas and "gear" in chamadas[0]


def test_nao_entendi_chama_llm(monkeypatch):
    chamadas = []

    def _fake_tools(mensagem, db=None, produtor_id=None, **k):
        chamadas.append(mensagem)
        return ("pode reformular? tente X", [])

    monkeypatch.setattr(chat, "responder_com_tools", _fake_tools)
    import app.llm as _llm
    monkeypatch.setattr(_llm, "gerar_resposta", lambda *a, **k: "pode reformular? tente X")
    res = TestClient(app).post(
        "/api/chat", json={"produtor_id": "x", "mensagem": "xyz123"}
    )
    assert res.status_code == 200
    data = res.json()
    assert chamadas, "NAO_ENTENDI deve chamar gerar_resposta"
    assert data["resposta"] == "pode reformular? tente X"


def test_stream_perfil_emite_meta_delta_done(monkeypatch):
    def _gen(*a, **k):
        yield ("tool", {"name": "buscar_municipio", "args": {}})
        yield ("delta", "olá ")
        yield ("delta", "perfil")

    monkeypatch.setattr(chat, "responder_com_tools_stream", _gen)
    res = TestClient(app).post(
        "/api/chat/stream", json={"produtor_id": "x", "mensagem": _msgs_perfil()[0]}
    )
    assert res.status_code == 200
    evs = _eventos(res.text)
    nomes = [e for e, _ in evs]
    assert nomes[0] == "meta" and "delta" in nomes and nomes[-1] == "done"
    assert evs[0][1]["intencao"] == "PERFIL"
    assert "".join(d["texto"] for e, d in evs if e == "delta") == (
        "🔍 consultando buscar_municipio...olá perfil")
