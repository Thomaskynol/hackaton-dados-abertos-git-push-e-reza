"""Testes unitários para NLP léxico, intenções e consultas determinísticas."""
import pytest
from app.core.router_intencao import classificar_intencao
from app.schemas.intencoes import Intencao
from app.dados_reais import (
    extrair_cultura,
    extrair_alvo,
    produto_resumo,
    buscar_janelas,
    buscar_produtos,
)
from app.routes.chat import (
    _planejamento_fallback,
    _praga_fallback,
    _nao_entendi_base,
    _ctx_planejamento,
    _ctx_praga,
)


def test_classificar_intencao_saudacao():
    assert classificar_intencao("Oi, bom dia!") == Intencao.SAUDACAO
    assert classificar_intencao("Olá amigo") == Intencao.SAUDACAO
    assert classificar_intencao("opa tudo bem") == Intencao.SAUDACAO


def test_classificar_intencao_praga():
    assert classificar_intencao("minha uva está com míldio") == Intencao.PRAGA
    assert classificar_intencao("tem lagarta na folha") == Intencao.PRAGA
    assert classificar_intencao("qual veneno ou defensivo para fungo?") == Intencao.PRAGA


def test_classificar_intencao_planejamento():
    assert classificar_intencao("quando planto feijão?") == Intencao.PLANEJAMENTO
    assert classificar_intencao("qual a melhor janela de plantio do zarc?") == Intencao.PLANEJAMENTO
    assert classificar_intencao("época de colheita") == Intencao.PLANEJAMENTO


def test_classificar_intencao_clima():
    assert classificar_intencao("vai gear esta semana?") == Intencao.CLIMA
    assert classificar_intencao("previsão de chuva forte") == Intencao.CLIMA
    assert classificar_intencao("temperatura e seca") == Intencao.CLIMA


def test_classificar_intencao_venda():
    assert classificar_intencao("como posso vender pelo paa?") == Intencao.VENDA
    assert classificar_intencao("cotação do milho hoje") == Intencao.VENDA


def test_classificar_intencao_perfil():
    assert classificar_intencao("qual é o meu perfil cadastrado?") == Intencao.PERFIL
    assert classificar_intencao("dados da minha propriedade") == Intencao.PERFIL


def test_classificar_intencao_nao_entendi():
    assert classificar_intencao("xyz abcd 12345") == Intencao.NAO_ENTENDI


def test_extrair_cultura_normalizacao():
    assert extrair_cultura("quero plantar Feijão carioca") == "feijao"
    assert extrair_cultura("Café arábica de qualidade") == "cafe"
    assert extrair_cultura("minha lavoura de Milho safrinha") == "milho"
    assert extrair_cultura("uva niagara") == "uva"
    assert extrair_cultura("nenhuma planta mencionada") is None


def test_extrair_alvo_pragas_e_alias():
    assert extrair_alvo("minha planta tem míldio severo") == "míldio"
    assert extrair_alvo("apareceu lagarta do cartucho") == "lagarta"
    assert extrair_alvo("ferrugem asiática na soja") == "ferrugem"
    assert extrair_alvo("tudo saudável por aqui") is None


def test_produto_resumo_formatacao():
    doc1 = {
        "marca_comercial": "BioControl-X",
        "ingrediente_ativo": "Bacillus thuringiensis",
        "classe_toxicologica": 4,
        "organicos": "S",
    }
    r1 = produto_resumo(doc1)
    assert r1["nome"] == "BioControl-X"
    assert r1["classe"] == "IV"
    assert r1["organico"] is True

    doc2 = {
        "marca_comercial": None,
        "ingrediente_ativo": "Cobre Quelatado",
        "classe_toxicologica": 1,
        "organicos": "N",
    }
    r2 = produto_resumo(doc2)
    assert r2["nome"] == "Cobre Quelatado"
    assert r2["classe"] == "I"
    assert r2["organico"] is False


class _FakeQueryCursor:
    def __init__(self, data):
        self.data = list(data)

    def sort(self, *a, **k):
        return self

    def limit(self, n):
        return self.data[:n]


class _FakeDB:
    def __init__(self):
        self.zarc = self
        self.agrofit = self

    def find(self, query, projection=None):
        if "cultura_canonica" in query and query["cultura_canonica"] == "feijao":
            return _FakeQueryCursor([{"risco_min": 20, "solo_canonico": "ad1"}])
        if "cultura_canonica" in query and query["cultura_canonica"] == "uva":
            return _FakeQueryCursor([{"praga_nome_cientifico": "Plasmopara viticola", "marca_comercial": "Produto UV"}])
        return _FakeQueryCursor([])


def test_buscar_janelas_e_produtos_db_fake():
    db = _FakeDB()
    janelas = buscar_janelas(db, "feijao", "3503208")
    assert janelas is not None
    assert len(janelas) == 1
    assert janelas[0]["risco_min"] == 20

    produtos = buscar_produtos(db, "uva", alvo="mildio")
    assert produtos is not None
    assert len(produtos) == 1
    assert produtos[0]["marca_comercial"] == "Produto UV"

    vazio = buscar_produtos(db, "mandioca")
    assert vazio is None


def test_fallbacks_e_contexto_chat():
    plan_fb = _planejamento_fallback("quando planto feijão?")
    assert plan_fb["intencao"] == "PLANEJAMENTO"
    assert plan_fb["dados"]["cultura"] == "feijao"
    ctx_p = _ctx_planejamento(plan_fb)
    assert "feijao" in ctx_p

    praga_fb = _praga_fallback("uva com mildio")
    assert praga_fb["intencao"] == "PRAGA"
    assert praga_fb["dados"]["cultura"] == "uva"
    ctx_pr = _ctx_praga(praga_fb)
    assert "uva" in ctx_pr

    ne = _nao_entendi_base()
    assert ne["intencao"] == "NAO_ENTENDI"
