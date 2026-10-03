"""Tools + loop agentico sem rede (httpx + db fake)."""
import httpx

import app.llm as llm
import app.tools as tools
from app.tools import TOOLS_SCHEMA, dispatch


class _FakeCol:
    def __init__(self, docs=None, one=None):
        self._docs = docs or []
        self._one = one

    def find_one(self, query=None, *a, **k):
        return self._one

    def find(self, query=None, *a, **k):
        return _FakeCur(self._docs)


class _FakeCur:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *a, **k):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(self._docs)

    def __len__(self):
        return len(self._docs)


class _DB:
    def __init__(self):
        self.municipios = _FakeCol(one={"cod_ibge": "3503208", "nome": "Araraquara", "uf": "SP"})
        self.zarc = _FakeCol(docs=[{
            "solo_canonico": "ad1", "manejo_canonico": "irrigado",
            "ciclo_grupo": "grupo_i", "Portaria": "Port.1",
            "abertos": [1, 2], "risco_min": 20, "risco_max": 20,
            "dec": {"1": 20, "2": 20}}])
        self.agrofit = _FakeCol(docs=[{
            "marca_comercial": "X", "ingrediente_ativo": "Y",
            "praga_nome_cientifico": "Plasmopara viticola",
            "classe_toxicologica": 4, "organicos": "N"}])
        self.psr_agregado = _FakeCol(docs=[{
            "ano": 2025, "total_apolices": 10, "total_sinistros": 1,
            "taxa_sinistro_pct": 10.0, "total_pago_reais": 100.0, "por_evento": []}])
        self.sigef_agregado = _FakeCol(docs=[{
            "cultura_canonica": "feijao", "cod_ibge": "3503208",
            "municipio_norm": "araraquara", "uf": "SP",
            "area_total_ha": 5.0, "producao_bruta_t": 1.0,
            "producao_estimada_t": 2.0}])
        self.ana_atlas = _FakeCol(one={
            "cod_ibge": "3503208", "municipio": "Araraquara", "uf": "SP",
            "grupo_predominante": "G", "sistema_predominante": "S",
            "aai": {"potencial_total": 1}, "projecao_2030": {}, "projecao_2040": {}})


def _db_fake():
    return _DB()


class _Resp:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_schema_tem_7_tools():
    names = sorted(t["function"]["name"] for t in TOOLS_SCHEMA)
    assert names == ["buscar_area_sigef", "buscar_irrigacao_ana", "buscar_janelas_zarc",
                     "buscar_municipio", "buscar_preco_conab", "buscar_produtos_agrofit",
                     "buscar_risco_psr"]


def test_dispatch_db_fake():
    db = _db_fake()
    assert dispatch(db, "buscar_municipio", {"ibge": "35032080"})["cod_ibge"] == "3503208"
    z = dispatch(db, "buscar_janelas_zarc", {"cultura": "Feijão", "ibge": "3503208"})
    j0 = z["janelas"][0]  # type: ignore[index]
    assert j0["risco_min"] == 20  # type: ignore[index]
    assert j0["portaria"] == "Port.1"  # type: ignore[index]
    p = dispatch(db, "buscar_produtos_agrofit", {"cultura": "uva", "alvo": "mildio"})
    p0 = p["produtos"][0]  # type: ignore[index]
    assert p0["nome"] == "X"  # type: ignore[index]
    r = dispatch(db, "buscar_risco_psr", {"cod_ibge": "3503208"})
    r0 = r["riscos"][0]  # type: ignore[index]
    assert r0["ano"] == 2025  # type: ignore[index]
    a = dispatch(db, "buscar_area_sigef", {"cod_ibge": "3503208"})
    a0 = a["areas"][0]  # type: ignore[index]
    assert a0["cultura"] == "feijao"  # type: ignore[index]
    n = dispatch(db, "buscar_irrigacao_ana", {"cod_ibge": "3503208"})
    assert n["grupo"] == "G"
    assert dispatch(db, "invalida", {})["erro"]
    assert dispatch(None, "buscar_municipio", {"ibge": "3503208"})["erro"]


def test_loop_1_tool_call_retorna_texto(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    chamadas = {"n": 0}

    def _fake_post(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return _Resp({"choices": [{"message": {"role": "assistant", "content": None,
                                                  "tool_calls": [{
                                                      "id": "c1", "type": "function",
                                                      "function": {"name": "buscar_municipio",
                                                                   "arguments": '{"ibge":"3503208"}'}}]}}]})
        return _Resp({"choices": [{"message": {"role": "assistant",
                                               "content": "Araraquara/SP, fonte municipios."}}]})

    monkeypatch.setattr(httpx, "post", _fake_post)
    texto, usadas = llm.responder_com_tools("onde moro?", _db_fake(), "x")
    assert texto and "Araraquara" in texto
    assert usadas and usadas[0]["name"] == "buscar_municipio"
    assert usadas[0]["result_resumo"]["cod_ibge"] == "3503208"


def test_sem_chave_retorna_none(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    texto, usadas = llm.responder_com_tools("oi?", _db_fake(), "x")
    assert texto is None and usadas == []
    assert list(llm.responder_com_tools_stream("oi?", _db_fake(), "x")) == []


def test_stream_emite_tool_depois_delta(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    chamadas = {"n": 0}

    def _fake_post(*a, **k):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            return _Resp({"choices": [{"message": {"role": "assistant", "content": None,
                                                  "tool_calls": [{
                                                      "id": "c1", "type": "function",
                                                      "function": {"name": "buscar_municipio",
                                                                   "arguments": '{"ibge":"3503208"}'}}]}}]})
        return _Resp({"choices": [{"message": {"role": "assistant",
                                               "content": "Araraquara/SP."}}]})

    monkeypatch.setattr(httpx, "post", _fake_post)
    evs = list(llm.responder_com_tools_stream("onde moro?", _db_fake(), "x"))
    assert evs[0][0] == "tool" and evs[0][1]["name"] == "buscar_municipio"
    assert evs[-1][0] == "delta" and "Araraquara" in evs[-1][1]


def test_chat_agentico_usa_tools(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    import app.routes.chat as chat

    monkeypatch.setattr(
        chat, "responder_com_tools",
        lambda *a, **k: ("texto agente", [{"name": "buscar_municipio", "args": {}, "result_resumo": {}}]))
    res = TestClient(app).post(
        "/api/chat", json={"produtor_id": "x", "mensagem": "quais terras tenho e onde moro?"})
    assert res.status_code == 200
    data = res.json()
    assert data["resposta"] == "texto agente"
    assert "via tools" in data["fonte"]
    assert data["dados"]["ferramentas_usadas"][0]["name"] == "buscar_municipio"


def test_stream_agentico_tool_event(monkeypatch):
    import json as _json
    from fastapi.testclient import TestClient
    from app.main import app
    import app.routes.chat as chat

    def _gen(*a, **k):
        yield ("tool", {"name": "buscar_janelas_zarc", "args": {"cultura": "feijao"}})
        yield ("delta", "final")

    monkeypatch.setattr(chat, "responder_com_tools_stream", _gen)
    res = TestClient(app).post(
        "/api/chat/stream", json={"produtor_id": "x", "mensagem": "quando planto feijao?"})
    assert res.status_code == 200
    assert "consultando buscar_janelas_zarc" in res.text
    assert res.text.count("event: delta") >= 2
    assert "event: meta" in res.text and "event: done" in res.text
