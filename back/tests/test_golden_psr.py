"""Golden numbers PSR 2016–2024 (spec §4.2) + trava 2025 sem sinistro.

Sem os CSVs 2016–2024 (Rota B pendente, ver docs/05-descoberta.md §6) o teste
de leitura faz SKIP — nunca XFAIL silencioso, nunca número ajustado.
Roda com: cd back && pytest tests/test_golden_psr.py -v
"""
import pytest

GOLDEN = {
    "pares": 16_428,
    "apolices_pequenas": 684_997,
    "area_pequena_ha": 12_985_903,
    "seca": 157_350,
    "granizo": 44_467,
    "geada": 30_972,
    "soma_eventos": 301_498,
    "linhas_csv": 1_048_565,
}

ANOS_REAIS = list(range(2016, 2025))


def _db_ou_skip():
    from app.db import get_db
    try:
        db = get_db()
        if db is None:
            pytest.skip("sem Mongo (get_db None)")
        db.psr_agregado.count_documents({})
    except Exception as exc:  # noqa: BLE001 - skip honesto sem Mongo
        pytest.skip(f"Mongo indisponível: {exc}")
    return db


def _tem_serie_real(db):
    try:
        anos = sorted(a for a in db.psr_agregado.distinct("ano") if a)
    except Exception:  # noqa: BLE001 - sem série = skip, não erro
        return False
    return all(a in anos for a in ANOS_REAIS)


def test_apolice_2025_sem_sinistro():
    """Medido na ingestão e no Mongo local: 2025 tem 0 sinistros. Trava viva."""
    db = _db_ou_skip()
    docs = list(db.psr_agregado.find({"ano": 2025}, {"_id": 0}))
    if not docs:
        pytest.skip("sem docs 2025 no Mongo local")
    assert sum(d.get("total_sinistros", 0) for d in docs) == 0
    assert sum(d.get("total_pago_reais", 0.0) for d in docs) == 0.0


def test_golden_leitura_real():
    """Valida a leitura inteira quando a série existir. Hoje: SKIP honesto."""
    db = _db_ou_skip()
    if not _tem_serie_real(db):
        pytest.skip("série 2016–2024 ausente (Rota B pendente); "
                    "goldens §4.2 não verificáveis ainda")
    docs = list(db.psr_agregado.find(
        {"ano": {"$gte": 2016, "$lte": 2024}}, {"_id": 0}))
    assert len(docs) == GOLDEN["pares"], "pares (município, cultura)"
    assert (sum(d.get("total_apolices_pequenas", 0) for d in docs)
            == GOLDEN["apolices_pequenas"])
    assert (round(sum(d.get("area_pequena_ha", 0.0) for d in docs))
            == GOLDEN["area_pequena_ha"])
    from collections import Counter
    ev = Counter()
    for d in docs:
        for e in d.get("por_evento", []):
            ev[e["evento"]] += e["apolices"]
    assert ev.get("SECA", 0) == GOLDEN["seca"]
    assert ev.get("GRANIZO", 0) == GOLDEN["granizo"]
    assert ev.get("GEADA", 0) == GOLDEN["geada"]
    assert sum(ev.values()) == GOLDEN["soma_eventos"]
