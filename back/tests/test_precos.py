"""GET /api/precos + camada precos_dados: preços reais honestos (sem Mongo)."""
from fastapi.testclient import TestClient

from app.main import app
from app.precos_dados import bloco_pgpm, bloco_cepea, precos_da_uf

client = TestClient(app)


def test_precos_feijao_tem_piso_real():
    """Feijão tem PGPM oficial (lido do arquivo quando sem Mongo)."""
    r = client.get("/api/precos?uf=SP&cultura=feijao")
    assert r.status_code == 200
    d = r.json()
    assert d["uf"]["sigla"] == "SP"
    pgpm = next(p for p in d["precos"] if p["tipo"] == "pgpm")
    assert pgpm["estado"] == "disponivel"
    assert isinstance(pgpm["valor"], (int, float)) and pgpm["valor"] > 0
    assert pgpm["unidade"] == "R$/60kg"


def test_precos_tem_canais_e_analise():
    r = client.get("/api/precos?uf=SP&cultura=feijao")
    d = r.json()
    ids = {c["id"] for c in d["canais"]["canais"]}
    assert {"pnae", "paa", "cooperativas"} <= ids
    assert d["analise"]["texto"]
    assert d["analise"]["origem"] in ("ia", "heuristica")
    # nunca mandar vender agora
    assert "venda agora" not in d["analise"]["texto"].lower()


def test_precos_cultura_sem_pgpm_fica_pendente():
    """Soja não tem PGPM embutido -> pendente honesto + link Cepea."""
    r = client.get("/api/precos?uf=PR&cultura=soja")
    d = r.json()
    pgpm = next(p for p in d["precos"] if p["tipo"] == "pgpm")
    assert pgpm["estado"] == "pendente" and pgpm["valor"] is None
    cepea = next(p for p in d["precos"] if p["tipo"] == "cepea")
    assert cepea["valor"] is None and cepea["url"]


def test_precos_uf_invalida_cai_para_sp():
    r = client.get("/api/precos?uf=ZZ&cultura=feijao")
    assert r.status_code == 200
    assert r.json()["uf"]["sigla"] == "SP"


def test_camada_cepea_nunca_tem_numero():
    """Regra de ouro: Cepea é só link, nunca valor embutido."""
    for cult in ("feijao", "milho", "soja", "cafe"):
        c = bloco_cepea(None, cult, "SP")
        assert c["valor"] is None and c["estado"] == "link_externo" and c["url"]


def test_camada_tres_blocos_ordem():
    blocos = precos_da_uf(None, "feijao", "SP")
    assert [b["tipo"] for b in blocos] == ["pgpm", "conab_mercado", "cepea"]


# --- Série histórica e predição (IBGE/PAM) ---
from app.precos_dados import serie_historica, resumo_tendencia
from tests.conftest import FakeCol, make_db


def _db_serie():
    """FakeDB com uma série anual sintética crescente de feijão em SP."""
    docs = []
    for i, ano in enumerate(range(2015, 2024)):
        docs.append({
            "cultura_canonica": "feijao", "tipo": "serie_produtor",
            "uf": "SP", "regiao": "Sudeste", "ano": ano,
            "valor": 100.0 + i * 10, "unidade": "R$/60kg",
        })
    return make_db(precos_conab=FakeCol(docs))


def test_serie_historica_ordenada():
    serie = serie_historica(_db_serie(), "feijao", "SP")
    assert len(serie) == 9
    assert serie[0]["ano"] == 2015 and serie[-1]["ano"] == 2023
    assert serie[-1]["valor"] == 180.0


def test_tendencia_detecta_subida_e_projeta():
    t = resumo_tendencia(_db_serie(), "feijao", "SP")
    assert t["estado"] == "disponivel"
    assert t["direcao"] == "subindo"
    proj = t["projecao"]
    assert proj["ano"] == 2024
    # série sobe R$10/ano -> projeção ~190, dentro de uma faixa
    assert proj["faixa_min"] <= proj["valor_estimado"] <= proj["faixa_max"]
    assert proj["valor_estimado"] > 180.0


def test_tendencia_serie_curta_insuficiente():
    db = make_db(precos_conab=FakeCol([
        {"cultura_canonica": "feijao", "tipo": "serie_produtor", "uf": "SP",
         "ano": 2023, "valor": 180.0, "unidade": "R$/60kg"},
    ]))
    t = resumo_tendencia(db, "feijao", "SP")
    assert t["estado"] == "insuficiente"


def test_endpoint_precos_inclui_tendencia():
    r = client.get("/api/precos?uf=SP&cultura=feijao")
    assert r.status_code == 200
    assert "tendencia" in r.json()
