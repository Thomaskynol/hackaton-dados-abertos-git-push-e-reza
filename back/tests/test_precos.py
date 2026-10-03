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
    """Trigo não tem PGPM oficial na base -> pendente honesto + link Cepea."""
    r = client.get("/api/precos?uf=PR&cultura=trigo")
    d = r.json()
    pgpm = next(p for p in d["precos"] if p["tipo"] == "pgpm")
    assert pgpm["estado"] == "pendente" and pgpm["valor"] is None
    cepea = next(p for p in d["precos"] if p["tipo"] == "cepea")
    assert cepea["valor"] is None and cepea["url"]


def test_pgpm_soja_tem_valor_oficial():
    """Soja tem PGPM oficial (R$ 71,04) desde a Portaria 812/2025."""
    r = client.get("/api/precos?uf=PR&cultura=soja")
    pgpm = next(p for p in r.json()["precos"] if p["tipo"] == "pgpm")
    assert pgpm["estado"] == "disponivel"
    assert pgpm["valor"] == 71.04


def test_pgpm_milho_varia_por_regiao():
    """Milho é REGIONAL: MS (CO) ≠ SP (SE) ≠ RS (Sul). Regressão do bug
    que mostrava o mesmo valor nacional para todos os estados."""
    valores = {}
    for uf in ("MS", "SP", "RS", "BA"):
        r = client.get(f"/api/precos?uf={uf}&cultura=milho")
        pgpm = next(p for p in r.json()["precos"] if p["tipo"] == "pgpm")
        valores[uf] = pgpm["valor"]
        assert pgpm["estado"] == "disponivel"
    # Sul > Sudeste > Centro-Oeste na tabela oficial
    assert valores["RS"] == 55.64
    assert valores["SP"] == 51.03
    assert valores["MS"] == 38.28
    assert valores["BA"] == 63.08
    assert len(set(valores.values())) == 4, "milho não pode ser igual em todo estado"


def test_pgpm_feijao_usa_cores_e_nao_preto():
    """Regressão: 181,23 é o feijão PRETO. O padrão é CORES = 152,91."""
    r = client.get("/api/precos?uf=SP&cultura=feijao")
    pgpm = next(p for p in r.json()["precos"] if p["tipo"] == "pgpm")
    assert pgpm["valor"] == 152.91
    assert "181.23" not in str(pgpm["valor"])


def test_pgpm_nacional_nao_diz_no_seu_estado():
    """Piso nacional não pode ser anunciado como se fosse da UF."""
    r = client.get("/api/precos?uf=MS&cultura=feijao")
    mercado = next(p for p in r.json()["precos"] if p["tipo"] == "conab_mercado")
    aviso = mercado["aviso"].lower()
    assert "no seu estado" not in aviso
    assert "todo o brasil" in aviso


def test_pgpm_regional_diz_no_seu_estado():
    """Milho (regional) pode — e deve — dizer 'no seu estado'."""
    r = client.get("/api/precos?uf=MS&cultura=milho")
    mercado = next(p for p in r.json()["precos"] if p["tipo"] == "conab_mercado")
    assert "no seu estado (ms)" in mercado["aviso"].lower()


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
    from datetime import date
    t = resumo_tendencia(_db_serie(), "feijao", "SP")
    assert t["estado"] == "disponivel"
    assert t["direcao"] == "subindo"
    proj = t["projecao"]
    # projeta 1 ano à frente do último dado real, nunca no passado
    assert proj["ano"] >= max(2024, date.today().year)
    assert proj["faixa_min"] <= proj["valor_estimado"] <= proj["faixa_max"]
    # série sobe -> projeção acima do último valor real (180)
    assert proj["valor_estimado"] >= 180.0


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


# --- Previsão: ano futuro, fallback regressão e caminho IA ---
from datetime import date


def test_projecao_e_para_ano_futuro():
    """A projeção deve mirar o futuro próximo e nunca um ano já passado/no último dado."""
    t = resumo_tendencia(_db_serie(), "feijao", "SP")
    assert t["projecao"]["ano"] > t["ultimo"]["ano"]
    assert t["projecao"]["ano"] >= date.today().year


def test_projecao_fallback_regressao_sem_ia(monkeypatch):
    """Sem IA (prever_preco_ia -> None), projeção vem da regressão (origem tendencia)."""
    import app.llm as llm
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: None)
    t = resumo_tendencia(_db_serie(), "feijao", "SP")
    assert t["projecao"]["origem"] == "tendencia"


def test_projecao_usa_ia_quando_disponivel(monkeypatch):
    """Com IA respondendo, a projeção vem do modelo (origem ia + racional)."""
    monkeypatch.setenv("PRECO_PREVISAO_IA", "1")  # religa a IA (fixture desliga por padrão)
    import app.llm as llm
    fake = {
        "ano": date.today().year + 1, "valor_estimado": 199.9,
        "faixa_min": 180.0, "faixa_max": 220.0, "unidade": "R$/60kg",
        "origem": "ia", "racional": "A série vem subindo de forma constante.",
    }
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: fake)
    t = resumo_tendencia(_db_serie(), "feijao", "SP")
    assert t["projecao"]["origem"] == "ia"
    assert t["projecao"]["valor_estimado"] == 199.9
    assert t["projecao"]["racional"]


def test_prever_preco_ia_sem_chave(monkeypatch):
    """Sem OPENROUTER_API_KEY, prever_preco_ia devolve None (nunca inventa)."""
    import app.llm as llm
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    serie = [{"ano": 2020, "valor": 100.0}, {"ano": 2021, "valor": 110.0},
             {"ano": 2022, "valor": 120.0}]
    assert llm.prever_preco_ia("Feijão", "SP", "R$/60kg", serie, 2027) is None
