"""Lacuna-seguro: métricas, escore, ranking, síntese e privacidade (sem rede/Mongo)."""
import pytest

from app.lacuna import (canonizar, cobertura_pct, escore_lacuna, frase_top10,
                        linha_resultado, normalizar_por_cultura, parse_area,
                        rankear, resumo_por_cultura, resumo_por_uf,
                        sintese_narrativa, taxa_sinistro_pct, to_csv,
                        to_markdown)
from app.lacuna.metricas import resumir_grupo


def _grupo(**kw):
    g = {"apolices": 100, "apolices_pequenas": 60, "area_pequena": 1000.0,
         "area_total": 4000.0, "sinistros": 20, "pago": 50000.0}
    g.update(kw)
    return g


def _linha(**kw):
    lin = {"cod_ibge": "3550100", "municipio": "Toledo", "uf": "PR",
           "cultura": "soja", "area_pequena_ha": 105170.0,
           "area_total_ha": 244000.0, "cobertura_pct": 43.1, "apolices": 5780,
           "apolices_pequenas": 4000, "sinistros": 1854,
           "taxa_sinistro_pct": 32.0, "pago_reais": 140700000.0,
           "escore_lacuna": 210.5}
    lin.update(kw)
    return lin


# --- métricas ---
def test_cobertura_faixa():
    assert cobertura_pct(105170.0, 244000.0) == pytest.approx(43.1, abs=0.05)
    assert cobertura_pct(0, 0) is None
    assert cobertura_pct(10, -5) is None
    assert cobertura_pct("lixo", 10) is None


def test_taxa_sinistro():
    assert taxa_sinistro_pct(20, 100) == 20.0
    assert taxa_sinistro_pct(0, 0) is None


def test_resumir_grupo_aceita_dois_namings():
    r = resumir_grupo(_grupo())
    assert r["cobertura_pct"] == 25.0 and r["taxa_sinistro_pct"] == 20.0
    r2 = resumir_grupo({"total_apolices": 100, "total_apolices_pequenas": 60,
                        "area_pequena_ha": 1000.0, "area_total_ha": 4000.0,
                        "total_sinistros": 20, "total_pago_reais": 50000.0})
    assert r2 == r


# --- encoding / regras PSR (reuso correlacao.canon) ---
def test_mojibake():
    assert canonizar("Cana-de-açúcar") == "cana-de-acucar"


def test_mojibake_latin1():
    assert canonizar("Cana-de-aÃ§Ãºcar") == "cana-de-acucar"


def test_safra_distinta():
    assert canonizar("Milho 1ª") != canonizar("Milho 2ª")


def test_area_virgula():
    assert parse_area("12,5") == 12.5


def test_area_vazia():
    assert parse_area("") is None


# --- escore ---
def test_escore_finito_e_zero_sem_dado():
    assert escore_lacuna(105170.0, 32.0, 43.1) > 0
    assert escore_lacuna(0, 0, 0) == 0.0
    assert escore_lacuna(None, None, None) == 0.0
    assert escore_lacuna(100.0, 10.0, 150.0) == 0.0  # cobertura inválida


def test_escore_deterministico():
    args = (105170.0, 32.0, 43.1)
    assert [escore_lacuna(*args) for _ in range(100)] == [escore_lacuna(*args)] * 100


def test_normalizacao_preserva_ordem_e_faixa():
    lins = [_linha(cultura="soja", escore_lacuna=v) for v in (10.0, 30.0, 20.0)]
    lins += [_linha(cultura="milho", escore_lacuna=999.0)]
    out = normalizar_por_cultura(lins)
    soja = sorted([o for o in out if o["cultura"] == "soja"],
                  key=lambda o: o["escore_lacuna"])
    norms = [o["escore_norm"] for o in soja]
    assert norms == [0.0, 0.5, 1.0]
    assert all(0.0 <= o["escore_norm"] <= 1.0 for o in out)
    assert [o for o in out if o["cultura"] == "milho"][0]["escore_norm"] == 0.5


# --- ranking / saídas ---
def test_ranking_deterministico_e_desempate():
    a = _linha(cod_ibge="1111111", escore_norm=0.9, area_pequena_ha=50.0)
    b = _linha(cod_ibge="2222222", escore_norm=0.9, area_pequena_ha=60.0)
    c = _linha(cod_ibge="0000001", escore_norm=0.9, area_pequena_ha=60.0)
    r = rankear([a, b, c])
    assert [x["cod_ibge"] for x in r] == ["0000001", "2222222", "1111111"]
    assert [x["rank"] for x in r] == [1, 2, 3]
    assert rankear([a, b, c]) == rankear([c, a, b])


def test_linha_resultado_completa():
    lin = linha_resultado({"cod_ibge": "3550100", "municipio": "Toledo",
                           "uf": "PR", "cultura": "soja"}, _grupo())
    assert lin["cobertura_pct"] == 25.0
    assert lin["escore_lacuna"] > 0
    assert "NM_SEGURADO" not in str(lin)


def test_csv_header_exato():
    header = ("rank,cod_ibge,municipio,uf,cultura,area_pequena_ha,"
              "area_total_ha,cobertura_pct,apolices,apolices_pequenas,"
              "sinistros,taxa_sinistro_pct,pago_reais,escore_lacuna")
    csv = to_csv(rankear([_linha(escore_norm=1.0)]))
    assert csv.splitlines()[0] == header
    assert "Toledo" in csv


def test_markdown_tabela():
    md = to_markdown(rankear([_linha(escore_norm=1.0)]))
    assert md.startswith("| rank |") and "escore_norm" in md


def test_frase_top10_contem_numeros():
    f = frase_top10({**_linha(), "rank": 1})
    assert f.startswith("**#1 Toledo/PR · Soja**")
    assert "105.170" in f and "43,1%" in f


def test_resumos_agregam():
    lins = [_linha(), _linha(cultura="milho", area_pequena_ha=10.0)]
    assert resumo_por_cultura(lins)[0]["cultura"] == "soja"
    assert resumo_por_uf(lins)[0]["uf"] == "PR"


def test_sintese_template_sem_llm():
    txt = sintese_narrativa(rankear([_linha(escore_norm=1.0)]))
    assert "MAPA/SISSER 2016–2024" in txt
    assert "cobertura por apólice não é cobertura por produtor" in txt
    assert "agrotóxico" not in txt.lower() or "receituário" in txt


def test_sintese_llm_invalida_cai_no_template():
    base = sintese_narrativa(rankear([_linha(escore_norm=1.0)]))
    assert sintese_narrativa(rankear([_linha(escore_norm=1.0)]),
                             llm_call=lambda p: None) == base
    assert sintese_narrativa(rankear([_linha(escore_norm=1.0)]),
                             llm_call=lambda p: "lacuna de R$ 999.999.999") == base


def test_sem_pii():
    sujo = _linha(NM_SEGURADO="FULANO", NR_DOCUMENTO_SEGURADO="123",
                  CPF="1", CNPJ="2", LATITUDE="-23", LONGITUDE="-48")
    for saida in (to_csv(rankear([sujo])), to_markdown(rankear([sujo])),
                  frase_top10({**sujo, "rank": 1}),
                  sintese_narrativa(rankear([sujo]))):
        for chave in ("FULANO", "NM_SEGURADO", "NR_DOCUMENTO_SEGURADO"):
            assert chave not in saida
