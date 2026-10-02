"""GET /api/regiao agrega tools existentes; estados honestos (FakeDB)."""
from fastapi.testclient import TestClient

import app.routes.regiao as regiao
from app.main import app
from tests.conftest import FakeCol, make_db

IBGE = "3503208"
client = TestClient(app)


def _db_cheio():
    return make_db(
        municipios=FakeCol([{"cod_ibge": IBGE, "nome": "Araraquara", "uf": "SP"}]),
        zarc=FakeCol([
            {"cod_ibge": IBGE, "cultura_canonica": "milho", "solo_canonico": "ad1"},
            {"cod_ibge": IBGE, "cultura_canonica": "milho", "solo_canonico": "ad1"},
            {"cod_ibge": IBGE, "cultura_canonica": "milho", "solo_canonico": "argiloso"},
        ]),
        sigef_agregado=FakeCol([{
            "cultura_canonica": "milho", "cod_ibge": IBGE,
            "municipio_norm": "araraquara", "uf": "SP",
            "area_total_ha": 10.0, "producao_bruta_t": 5.0,
            "producao_estimada_t": 6.0}]),
        psr_agregado=FakeCol([{
            "cod_ibge": IBGE, "cultura_canonica": "milho", "ano": 2024,
            "total_apolices": 7, "total_sinistros": 1,
            "taxa_sinistro_pct": 14.0, "total_pago_reais": 100.0,
            "por_evento": [{"evento": "seca", "apolices": 1, "valor": 100.0}]}]),
        ana_atlas=FakeCol([{
            "cod_ibge": IBGE, "municipio": "Araraquara", "uf": "SP",
            "grupo_predominante": "G", "sistema_predominante": "S",
            "aai": {}, "projecao_2030": {}, "projecao_2040": {}}]),
    )


def test_regiao_cheio_disponivel(monkeypatch):
    monkeypatch.setattr(regiao, "get_db", lambda: _db_cheio())
    # zarc p/ oportunidade usa buscar_janelas real — monkeypatch só ela
    import app.tools as tools
    real = tools._t_buscar_janelas_zarc
    monkeypatch.setattr(
        tools, "_t_buscar_janelas_zarc",
        lambda db, args: {"janelas": [{"cultura": "milho"}]}
        if (db is not None and args.get("ibge") == IBGE) else real(db, args))
    res = client.get(f"/api/regiao?uf=SP&ibge={IBGE}&cultura=milho")
    assert res.status_code == 200
    d = res.json()
    assert d["uf"] == {"sigla": "SP", "nome": "São Paulo", "regiao": "Sudeste"}
    assert d["ibge"] == IBGE and d["municipio"] == "Araraquara"
    assert d["solo"]["estado"] == "disponivel" and d["solo"]["soloId"] == "arenoso"
    assert d["producao"]["estado"] == "disponivel" and d["producao"]["areaHa"] == 10.0
    assert d["seguro"]["estado"] == "disponivel" and d["seguro"]["apolices"] == 7
    assert d["irrigacao"]["estado"] == "disponivel"
    assert len(d["precos"]) == 3 and all(p["valor"] is None for p in d["precos"])
    assert d["oportunidade"]["estado"] == "disponivel"
    assert "via tools" in d["fonte"] and d["data_extracao"]


def test_regiao_vazio_sem_dado(monkeypatch):
    monkeypatch.setattr(regiao, "get_db", lambda: make_db())
    res = client.get("/api/regiao?uf=SP&ibge=9999999&cultura=milho")
    assert res.status_code == 200
    d = res.json()
    for k in ("producao", "solo", "seguro", "irrigacao"):
        assert d[k]["estado"] == "sem_dado", k
    assert d["oportunidade"]["estado"] == "pendente"
    assert len(d["precos"]) == 3  # preços sempre honestos, nunca número


def test_regiao_sem_db_nao_quebra(monkeypatch):
    monkeypatch.setattr(regiao, "get_db", lambda: None)
    res = client.get("/api/regiao?uf=SP&cultura=milho")
    assert res.status_code == 200
    d = res.json()
    assert d["uf"]["sigla"] == "SP"
    assert d["solo"]["estado"] == "sem_dado"


def test_solo_majority_e_mapa_ad(monkeypatch):
    db = make_db(zarc=FakeCol([
        {"cod_ibge": IBGE, "solo_canonico": "ad3"},
        {"cod_ibge": IBGE, "solo_canonico": "ad3"},
        {"cod_ibge": IBGE, "solo_canonico": "ad5"},
    ]))
    assert regiao.solo_inferido_para(db, IBGE) == "media"
    assert regiao.solo_inferido_para(make_db(), IBGE) is None
    assert regiao.solo_inferido_para(None, IBGE) is None
