"""Tabela priorizada: colapso (município, cultura) + gerar() (sem rede/Mongo real)."""
from app.lacuna.ranking import COLUNAS_CSV, to_csv
from app.lacuna.tabela import colapsar_por_municipio_cultura, gerar
from tests.conftest import FakeCol, make_db


def _doc(**kw):
    d = {"cod_ibge": "3550100", "municipio": "Toledo", "uf": "PR",
         "cultura_canonica": "soja", "ano": 2023, "total_apolices": 100,
         "total_apolices_pequenas": 60, "area_pequena_ha": 1000.0,
         "area_total_ha": 4000.0, "total_sinistros": 20,
         "total_pago_reais": 50000.0}
    d.update(kw)
    return d


def test_colapsa_soma_anos_e_ignora_2025():
    grupos = colapsar_por_municipio_cultura(
        [_doc(ano=2023), _doc(ano=2024, total_apolices=50,
                              total_apolices_pequenas=30,
                              area_pequena_ha=500.0, area_total_ha=2000.0,
                              total_sinistros=10, total_pago_reais=25000.0),
         _doc(ano=2025, total_apolices=999, area_pequena_ha=999.0,
              area_total_ha=999.0)])
    assert len(grupos) == 1
    g = grupos[0]["grupo"]
    assert (g["apolices"], g["apolices_pequenas"]) == (150, 90)
    assert (g["area_pequena"], g["area_total"]) == (1500.0, 6000.0)
    assert (g["sinistros"], g["pago"]) == (30, 75000.0)
    assert grupos[0]["ano_max"] == 2024


def test_colapsa_ignora_sem_area_e_sem_ano_conta():
    grupos = colapsar_por_municipio_cultura(
        [_doc(cod_ibge="9999999", municipio="Vazio",
              cultura_canonica="milho", total_apolices=10,
              total_sinistros=0, area_pequena_ha=0.0, area_total_ha=0.0),
         _doc(ano=None)])
    assert [v["meta"]["cod_ibge"] for v in grupos] == ["3550100"]


def test_gerar_rank_1_e_top_n_e_vazio():
    db = make_db(psr_agregado=FakeCol([_doc(), _doc(
        cod_ibge="3550101", municipio="Assis", cultura_canonica="milho",
        area_pequena_ha=500.0, area_total_ha=1000.0)]))
    linhas = gerar(db)
    assert [r["rank"] for r in linhas] == [1, 2]
    assert all(r["escore_lacuna"] > 0 for r in linhas)
    assert len(gerar(db, top_n=1)) == 1
    vazio = make_db(psr_agregado=FakeCol(
        [{"cod_ibge": "x", "ano": 2025, "total_apolices": 5}]))
    assert gerar(vazio) == []
    assert to_csv([]).splitlines()[0] == ",".join(COLUNAS_CSV)
