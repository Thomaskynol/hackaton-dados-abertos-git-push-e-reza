"""Série de preços VIVA: atualização automática a partir do IBGE (mockado)."""
import time

import app.precos_dados as pd
import app.precos_ibge as ibge
from tests.conftest import FakeCol, make_db


def _db_defasado():
    """Mongo com série de milho só até 2024 (faltando 2025)."""
    docs = []
    for ano in range(2015, 2025):  # 2015..2024
        docs.append({"cultura_canonica": "milho", "tipo": "serie_produtor",
                     "uf": "PR", "ano": ano, "valor": 40.0 + (ano - 2015),
                     "unidade": "R$/60kg"})
    return make_db(precos_conab=FakeCol(docs))


def test_fetcher_parse(monkeypatch):
    """buscar_serie converte o JSON do IBGE em docs R$/saca (sem rede real)."""
    fake = [
        {"id": "215", "resultados": [{"series": [
            {"localidade": {"id": "41"}, "serie": {"2025": "1000"}}]}]},   # valor mil R$
        {"id": "214", "resultados": [{"series": [
            {"localidade": {"id": "41"}, "serie": {"2025": "100"}}]}]},    # qtd t
    ]
    monkeypatch.setattr(ibge, "_get_json", lambda *a, **k: fake)
    docs = ibge.buscar_serie("milho", anos=[2025])
    assert len(docs) == 1
    d = docs[0]
    assert d["uf"] == "PR" and d["ano"] == 2025
    # 1000 mil R$ / 100 t = 10000 R$/t -> * 60/1000 = 600 R$/saca
    assert d["valor"] == 600.0


def test_atualizacao_viva_puxa_ano_novo(monkeypatch):
    """Mongo em 2024 + IBGE em 2025 -> atualização grava 2025."""
    monkeypatch.setattr(ibge, "ultimo_ano_disponivel", lambda *a, **k: 2025)
    monkeypatch.setattr(ibge, "buscar_serie", lambda cult, anos=None, **k: [
        {"cultura_canonica": "milho", "tipo": "serie_produtor", "uf": "PR",
         "ano": 2025, "valor": 55.0, "unidade": "R$/60kg"}])
    monkeypatch.setenv("IBGE_AUTO_UPDATE", "1")
    db = _db_defasado()
    assert pd._ano_mais_recente_no_db(db, "milho") == 2024
    pd.atualizar_serie_viva(db, "milho")
    assert pd._ano_mais_recente_no_db(db, "milho") == 2025


def test_ttl_evita_rechecar(monkeypatch):
    """Com meta recente (dentro do TTL), não chama o IBGE de novo."""
    chamou = {"n": 0}
    monkeypatch.setattr(ibge, "ultimo_ano_disponivel",
                        lambda *a, **k: (chamou.__setitem__("n", chamou["n"] + 1) or 2025))
    monkeypatch.setenv("IBGE_AUTO_UPDATE", "1")
    db = _db_defasado()
    db.precos_meta = FakeCol([{"_id": "serie:milho", "last_check_ts": int(time.time()),
                               "last_ok": True, "ultimo_ano": 2025}])
    pd.atualizar_serie_viva(db, "milho")
    assert chamou["n"] == 0  # TTL vigente -> nem consultou a API


def test_auto_update_desligado(monkeypatch):
    monkeypatch.setenv("IBGE_AUTO_UPDATE", "0")
    chamou = {"n": 0}
    monkeypatch.setattr(ibge, "ultimo_ano_disponivel",
                        lambda *a, **k: (chamou.__setitem__("n", chamou["n"] + 1) or 2025))
    pd.atualizar_serie_viva(_db_defasado(), "milho")
    assert chamou["n"] == 0


def test_offline_nao_quebra(monkeypatch):
    """IBGE fora do ar (None) -> não grava nada, não levanta erro."""
    monkeypatch.setattr(ibge, "ultimo_ano_disponivel", lambda *a, **k: None)
    monkeypatch.setenv("IBGE_AUTO_UPDATE", "1")
    db = _db_defasado()
    pd.atualizar_serie_viva(db, "milho")  # não deve levantar
    assert pd._ano_mais_recente_no_db(db, "milho") == 2024
