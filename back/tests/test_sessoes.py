"""Sessoes/memorias CRUD + chat persiste turnos e injeta memoria (FakeDB, sem rede)."""
from fastapi.testclient import TestClient

import app.routes.chat as chat
import app.routes.sessoes as rot_ses
from app.main import app
from tests.conftest import make_db

client = TestClient(app)


def _patch_db(monkeypatch, db):
    monkeypatch.setattr(chat, "get_db", lambda: db)
    monkeypatch.setattr(rot_ses, "get_db", lambda: db)
    # sem LLM/tools: força fallback determinístico
    monkeypatch.setattr(chat, "responder_com_tools", lambda *a, **k: (None, []))
    monkeypatch.setattr(chat, "gerar_resposta", lambda *a, **k: None)


def test_sessoes_crud():
    db = make_db()
    import app.routes.sessoes as rs
    orig = rs.get_db
    rs.get_db = lambda: db
    try:
        c = TestClient(app)
        r = c.post("/api/sessoes", json={"produtor_id": "p1", "titulo": "Milho?"})
        assert r.status_code == 201
        sid = r.json()["id"]
        assert r.json()["titulo"] == "Milho?"
        r2 = c.get("/api/sessoes?produtor_id=p1")
        assert r2.status_code == 200 and len(r2.json()) == 1
        r3 = c.get(f"/api/sessoes/{sid}/mensagens")
        assert r3.status_code == 200 and r3.json() == []
        r4 = c.get("/api/memorias?produtor_id=p1")
        assert r4.status_code == 200 and r4.json() == []
        assert c.get("/api/sessoes/inexistente").status_code == 404
    finally:
        rs.get_db = orig


def test_sessoes_sem_db_503():
    import app.routes.sessoes as rs
    orig = rs.get_db
    rs.get_db = lambda: None
    try:
        assert TestClient(app).get("/api/sessoes?produtor_id=p1").status_code == 503
    finally:
        rs.get_db = orig


def test_chat_persiste_turnos_e_memoria(monkeypatch):
    db = make_db()
    _patch_db(monkeypatch, db)
    r = client.post("/api/chat", json={
        "produtor_id": "p1", "mensagem": "quando planto milho em 5 ha?"})
    assert r.status_code == 200
    d = r.json()
    assert d["intencao"] == "PLANEJAMENTO" and d.get("sessao_id")
    msgs = db.mensagens.docs
    assert len(msgs) == 2
    assert [m["autor"] for m in msgs] == ["usuario", "copiloto"]
    assert all(m["sessao_id"] == d["sessao_id"] for m in msgs)
    mems = db.memorias.docs
    assert any("milho" in m["texto"] for m in mems)  # cultura extraída sem LLM
    assert any("5 ha" in m["texto"] for m in mems)  # área extraída


def test_chat_reusa_sessao_id_e_injeta_memorias(monkeypatch):
    db = make_db()
    _patch_db(monkeypatch, db)
    vistos = {}

    def _fake_tools(mensagem, db=None, produtor_id=None, **k):
        vistos["ctx"] = k.get("contexto_extra", "")
        return (None, [])

    monkeypatch.setattr(chat, "responder_com_tools", _fake_tools)
    r1 = client.post("/api/chat", json={"produtor_id": "p1", "mensagem": "quando planto milho?"})
    sid = r1.json()["sessao_id"]
    r2 = client.post("/api/chat", json={
        "produtor_id": "p1", "sessao_id": sid, "mensagem": "minha uva está com míldio?"})
    assert r2.json()["sessao_id"] == sid  # reutiliza, não auto-cria
    assert len(db.sessoes.docs) == 1
    assert len(db.mensagens.docs) == 4
    assert "milho" in (vistos["ctx"] or "")  # 2º turno injeta memória do 1º
    hist = client.get(f"/api/sessoes/{sid}/mensagens")
    assert len(hist.json()) == 4


def test_extrair_memorias_sem_llm():
    from app.memoria import contexto_memorias, extrair_memorias, salvar_memoria
    assert extrair_memorias("oi, bom dia") == []
    fatos = extrair_memorias("minha uva tá com míldio em 3 ha")
    assert any("mildio" in f or "míldio" in f for f in fatos)
    db = make_db()
    salvar_memoria(db, "p", "planta milho", "chat", "s1")
    salvar_memoria(db, "p", "planta milho", "chat", "s1")  # dedup: não duplica
    assert len(db.memorias.docs) == 1
    assert "milho" in contexto_memorias(db, "p")
    assert contexto_memorias(make_db(), "sem-nada") == ""


def test_stream_persiste_turno(monkeypatch):
    db = make_db()
    _patch_db(monkeypatch, db)
    monkeypatch.setattr(chat, "responder_com_tools_stream", lambda *a, **k: iter([]))
    monkeypatch.setattr(
        chat, "gerar_resposta_stream", lambda *a, **k: iter(["resposta ", "final"]))
    r = client.post("/api/chat/stream",
                    json={"produtor_id": "p9", "mensagem": "quando planto feijao?"})
    assert r.status_code == 200 and "resposta " in r.text and "final" in r.text
    assert len(db.mensagens.docs) == 2  # user + copiloto salvos após done
