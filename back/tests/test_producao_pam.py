"""Produção real (IBGE PAM) e card do Cepea — dados, escopo e honestidade.

Regressões cobertas aqui:
  * o card de produção NÃO pode mais vir do SIGEF (que mede semente);
  * a produção real precisa declarar ano, fonte e a limitação da cobertura;
  * o card do Cepea nunca mostra o número do dia, mas entrega o histórico
    real do IBGE e diz por que o valor de hoje é um link.
"""

import app.precos_dados as pd
from app.precos_dados import bloco_cepea, producao_uf, resumo_tendencia, serie_historica
from tests.conftest import FakeCol, make_db

# Série real: SP 2025 (IBGE PAM) — soja 4.731.554 t, milho 4.231.182 t.
SERIE_SP = [
    {"tipo": "serie_produtor", "uf": "SP", "ano": 2024, "cultura_canonica": "soja",
     "quantidade_t": 4_000_000.0, "valor_ton": 1900.0, "valor": 114.0, "unidade": "R$/60kg"},
    {"tipo": "serie_produtor", "uf": "SP", "ano": 2025, "cultura_canonica": "soja",
     "quantidade_t": 4_731_554.0, "valor_ton": 2057.93, "valor": 123.48, "unidade": "R$/60kg"},
    {"tipo": "serie_produtor", "uf": "SP", "ano": 2025, "cultura_canonica": "milho",
     "quantidade_t": 4_231_182.0, "valor_ton": 1085.89, "valor": 65.15, "unidade": "R$/60kg"},
    {"tipo": "serie_produtor", "uf": "SP", "ano": 2025, "cultura_canonica": "feijao",
     "quantidade_t": 159_635.0, "valor_ton": 4014.94, "valor": 240.90, "unidade": "R$/60kg"},
    # Ruído que NÃO pode contaminar: outra UF e linha de Cepea.
    {"tipo": "serie_produtor", "uf": "MS", "ano": 2025, "cultura_canonica": "soja",
     "quantidade_t": 99_000_000.0, "valor_ton": 2000.0, "valor": 120.0, "unidade": "R$/60kg"},
    {"tipo": "cepea_link", "uf": "SP", "ano": 2025, "cultura_canonica": "soja",
     "valor": None},
]


def _db():
    return make_db(precos_conab=FakeCol(SERIE_SP))


# --------------------------------------------------------------------------
# Produção real (IBGE PAM)
# --------------------------------------------------------------------------

def test_producao_usa_ano_mais_recente_e_nao_mixa_uf():
    r = producao_uf(_db(), "SP")
    assert r["ano"] == 2025
    assert r["culturaTopo"] == "soja"
    # 99 milhões são de MS e não podem entrar no total de SP.
    assert r["quantidadeTopoT"] == 4_731_554.0
    assert r["totalT"] == 4_731_554.0 + 4_231_182.0 + 159_635.0


def test_producao_ordena_ranking_por_quantidade():
    r = producao_uf(_db(), "SP")
    ordem = [c["cultura"] for c in r["culturas"]]
    assert ordem == ["soja", "milho", "feijao"]


def test_producao_declara_a_limitacao_de_cobertura():
    r = producao_uf(_db(), "SP")
    # A PAM cobre 5 culturas: a resposta NÃO pode virar "a cultura que mais se
    # planta no estado" sem essa ressalva, porque cana e café ficam de fora.
    assert "cana" not in r["cobertura"].lower()
    assert len(r["culturas"]) == 3


def test_producao_uf_sem_dado_devolve_none_e_nao_explode():
    assert producao_uf(_db(), "AP") is None
    assert producao_uf(None, "SP") is None


def test_producao_ignora_ano_sem_quantidade():
    db = make_db(precos_conab=FakeCol([
        {"tipo": "serie_produtor", "uf": "SP", "ano": 2025, "cultura_canonica": "soja",
         "quantidade_t": 0.0, "valor": 0.0, "unidade": "R$/60kg"},
    ]))
    assert producao_uf(db, "SP") is None


# --------------------------------------------------------------------------
# Card do Cepea
# --------------------------------------------------------------------------

def test_cepea_nunca_exibe_o_numero_do_dia():
    c = bloco_cepea(_db(), "feijao", "SP")
    assert c["valor"] is None
    assert c["estado"] == "link_externo"


def test_cepea_traz_historico_real_com_ano_e_uf():
    c = bloco_cepea(_db(), "feijao", "SP")
    ref = c["referencia_ibge"]
    assert ref is not None
    assert ref["ano"] == 2025
    assert ref["valor"] == 240.90
    assert "SP" in c["aviso"]
    assert "2025" in c["aviso"]


def test_cepea_explica_por_que_e_link_e_de_onde_vem_o_historico():
    c = bloco_cepea(_db(), "feijao", "SP")
    notas = " ".join(c["fonte"]["limitacoes"]).lower()
    assert "cepea" in notas
    # O histórico tem que se dizer QUE É, senão vira número sem origem.
    assert "ibge" in notas


def test_cepea_sem_cultura_usa_a_maior_do_estado_e_declara():
    c = bloco_cepea(_db(), None, "SP")
    assert c["referencia_ibge"] is not None
    assert "maior cultura" in c["cultura"].lower()
    assert "maior cultura" in c["aviso"].lower()


def test_cepea_sem_db_ainda_explica_o_link():
    """Sem Mongo, o card nunca quebra: ou usa o arquivo local, ou explica."""
    c = bloco_cepea(None, "feijao", "SP")
    assert c["valor"] is None
    assert c["estado"] == "link_externo"
    assert c["aviso"]  # sempre diz por que é link


def test_bloco_cepea_nunca_levanta_com_db_none():
    c = bloco_cepea(None, "feijao", "SP")
    assert c["estado"] == "link_externo"


# --------------------------------------------------------------------------
# Tendência: o selo tem que refletir o ÚLTIMO ano, não a reta nominal
# --------------------------------------------------------------------------
# Série real do IBGE (SP): o feijão SUBIU por anos e depois CAIU 19,4% em 2025
# (298,80 -> 240,90). A inclinação da reta de 8 anos continua POSITIVA porque
# preço nominal sobe com a inflação — então o selo antigo ("subindo") mandava o
# produtor tomar a decisão de venda ao contrário.
SERIE_TENDENCIA = [
    {"tipo": "serie_produtor", "uf": "SP", "cultura_canonica": "feijao", "ano": ano,
     "quantidade_t": 100000.0, "valor_ton": v * 1000 / 60.0,
     "valor": v, "unidade": "R$/60kg"}
    for ano, v in [(2018, 122.99), (2019, 180.83), (2020, 246.18), (2021, 262.59),
                   (2022, 290.83), (2023, 272.72), (2024, 298.80), (2025, 240.90)]
]


def _db_tendencia():
    return make_db(precos_conab=FakeCol(SERIE_TENDENCIA))


def test_selo_reflete_a_queda_do_ultimo_ano_nao_a_reta_nominal(monkeypatch):
    monkeypatch.setattr(pd, "prever_preco_ia", lambda *a, **k: None, raising=False)
    import app.llm as llm
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: None, raising=False)
    t = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    assert t["estado"] == "disponivel"
    # O dado oficial caiu 19,4%. O selo NÃO pode dizer "subindo".
    assert t["variacao_ultimo_ano"] == -19.4
    assert t["direcao"] == "caindo"


def test_tendencia_nominal_vai_separada_e_nao_manda_no_selo(monkeypatch):
    monkeypatch.setattr(pd, "prever_preco_ia", lambda *a, **k: None, raising=False)
    import app.llm as llm
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: None, raising=False)
    t = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    # A reta longa é positiva (inflação), mas é campo separado e declarado
    # como nominal. Se voltar a mandar no selo, o bug volta.
    assert t["variacao_media_anual"] > 0
    assert t["direcao"] == "caindo"


def test_tendencia_declara_que_e_dado_anual_do_ibge(monkeypatch):
    monkeypatch.setattr(pd, "prever_preco_ia", lambda *a, **k: None, raising=False)
    import app.llm as llm
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: None, raising=False)
    t = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    assert "ANUAL" in (t["periodicidade"] or "").upper()
    assert "1612" in (t["fonte"] or "")


def test_tendencia_avisa_que_o_ano_estimado_ja_esta_em_andamento(monkeypatch):
    """Hoje o último oficial é 2025 e projetamos 2026 — o ano corrente.
    O aviso tem que dizer isso; antes só aparecia com 2+ anos de defasagem,
    ou seja NUNCA."""
    import datetime as _dt
    monkeypatch.setattr(pd, "prever_preco_ia", lambda *a, **k: None, raising=False)
    import app.llm as llm
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: None, raising=False)
    t = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    p = t.get("projecao") or {}
    if p.get("ano") == _dt.date.today().year:
        assert "andamento" in t["aviso"] or "já passou" in t["aviso"]
    assert "não garantia de preço" in t["aviso"]


def test_trocar_de_cultura_devolve_da_do_cultura_certa():
    """Feijão -> arroz: a série tem que ser a da cultura pedida, com a
    unidade certa (arroz é saca de 50 kg, feijão 60 kg)."""
    db = make_db(precos_conab=FakeCol(SERIE_TENDENCIA + [
        {"tipo": "serie_produtor", "uf": "SP", "cultura_canonica": "arroz", "ano": 2024,
         "quantidade_t": 50000.0, "valor_ton": 1737.25, "valor": 86.86, "unidade": "R$/50kg"},
        {"tipo": "serie_produtor", "uf": "SP", "cultura_canonica": "arroz", "ano": 2025,
         "quantidade_t": 52914.0, "valor_ton": 1737.25, "valor": 86.86, "unidade": "R$/50kg"},
    ]))
    f = serie_historica(db, "feijao", "SP")
    a = serie_historica(db, "arroz", "SP")
    assert f[-1]["valor"] == 240.90 and f[-1]["unidade"] == "R$/60kg"
    assert a[-1]["valor"] == 86.86 and a[-1]["unidade"] == "R$/50kg"
    # Nenhuma das duas pode vazar dado da outra.
    assert all(p["unidade"] == "R$/60kg" for p in f)
    assert all(p["unidade"] == "R$/50kg" for p in a)


# --------------------------------------------------------------------------
# Passo 1 + 2: determinismo da previsão e ano-alvo (próxima safra)
# --------------------------------------------------------------------------

def _sem_ia(monkeypatch):
    """Desliga a IA para testar só a regressão (determinística por natureza)."""
    monkeypatch.setenv("PRECO_PREVISAO_IA", "0")


def test_regressao_e_deterministica_por_natureza(monkeypatch):
    """Duas chamadas seguidas têm que devolver o MESMO número.

    Bug original: o número vinha de uma chamada de LLM sem cache e sem
    temperature 0 — a mesma pergunta devolvia R$ 265 numa hora e R$ 321 na
    outra. A regressão não sofre disso, e é ela que fica na tela."""
    _sem_ia(monkeypatch)
    a = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    b = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    assert a["projecao"] == b["projecao"]
    assert a["projecao"]["valor_estimado"] == b["projecao"]["valor_estimado"]


def test_chave_de_cache_muda_quando_a_serie_muda():
    """Se o IBGE publica um ano novo, a chave tem que mudar — senão o cache
    serviria previsão feita sobre a série antiga como se fosse atual."""
    import app.llm as llm
    s1 = [{"ano": 2024, "valor": 100.0}, {"ano": 2025, "valor": 110.0}]
    s2 = s1 + [{"ano": 2026, "valor": 120.0}]
    c1 = llm._chave_previsao("Feijao", "SP", "R$/60kg", s1, 2027)
    c2 = llm._chave_previsao("Feijao", "SP", "R$/60kg", s2, 2027)
    assert c1 != c2
    # Mesma entrada -> mesma chave (é o que segura o determinismo).
    assert c1 == llm._chave_previsao("Feijao", "SP", "R$/60kg", s1, 2027)
    # Cultura/UF/unidade/ano diferentes -> chaves diferentes.
    assert c1 != llm._chave_previsao("Arroz", "SP", "R$/50kg", s1, 2027)
    assert c1 != llm._chave_previsao("Feijao", "MS", "R$/60kg", s1, 2027)
    assert c1 != llm._chave_previsao("Feijao", "SP", "R$/60kg", s1, 2028)


def test_previsao_ia_usa_cache_e_devolve_o_mesmo_numero(monkeypatch):
    """Com o cache respondendo, NÃO pode chamar o modelo de novo."""
    import app.llm as llm
    serie = [{"ano": 2023, "valor": 100.0}, {"ano": 2024, "valor": 110.0},
             {"ano": 2025, "valor": 120.0}]
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    chamadas = []

    # O _chat real aceita (key, body, timeout=...) — o fake precisa bater.
    def _chat_falso(key, body, timeout=None):
        chamadas.append(body)
        return {"choices": [{"message": {"content":
            '{"valor_estimado": 130, "faixa_min": 120, "faixa_max": 140, "racional": "x"}'}}]}

    monkeypatch.setattr(llm, "_chat", _chat_falso)
    llm.limpar_cache_previsao()

    db = make_db(precos_previsao=FakeCol([]))
    a = llm.prever_preco_ia("Feijao", "SP", "R$/60kg", serie, 2027, db=db)
    assert a is not None, f"devolveu None; chamadas={chamadas}"
    assert a["valor_estimado"] == 130
    assert len(chamadas) == 1

    # Segunda chamada: tem que vir do cache, sem tocar no modelo.
    b = llm.prever_preco_ia("Feijao", "SP", "R$/60kg", serie, 2027, db=db)
    assert b == a
    assert len(chamadas) == 1, "cache não foi usado — a IA foi chamada de novo"

    # E o corpo enviado tem temperature 0 (sem isso o provedor usa 1.0).
    assert chamadas[0].get("temperature") == 0
    llm.limpar_cache_previsao()


def test_ano_alvo_mira_a_proxima_safra_nao_o_ano_corrente():
    """Bug corrigido: com último oficial 2025 e hoje em 2026, a estimativa ia
    para 2026 (ano quase acabando). Agora mira a PRÓXIMA safra."""
    from datetime import date
    import app.precos_dados as pd
    alvo = pd._ano_alvo_projecao(2025)
    assert alvo >= date.today().year + 1, "tem que mirar a próxima safra, não o ano corrente"
    assert alvo == 2027  # 2025 + offset default 2
    # Nunca projeta para o passado.
    assert pd._ano_alvo_projecao(2019) >= date.today().year + 1


def test_ano_alvo_respeita_o_env_e_contem_valor_absurdo(monkeypatch):
    import app.precos_dados as pd
    monkeypatch.setenv("PRECO_ANO_ALVO_OFFSET", "1")
    assert pd._ano_alvo_projecao(2030) == 2031
    monkeypatch.setenv("PRECO_ANO_ALVO_OFFSET", "99")
    assert pd._ano_alvo_projecao(2030) == 2033  # teto de 3 anos


def test_desligar_a_ia_mantem_o_numero_deterministico(monkeypatch):
    monkeypatch.setenv("PRECO_PREVISAO_IA", "0")
    t = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    assert t["projecao"]["origem"] == "tendencia"
    assert t["projecao"]["valor_estimado"] > 0


def test_regressao_vem_mesmo_com_a_ia_ligada(monkeypatch):
    """Passo 5: existe um número DETERMINÍSTICO mesmo quando a IA responde.

    Sem isso, desligar a IA deixaria o card sem número nenhum e a projeção
    viraria refém de um modelo que pode mudar entre versões."""
    import app.llm as llm
    monkeypatch.setenv("PRECO_PREVISAO_IA", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")
    monkeypatch.setattr(llm, "prever_preco_ia", lambda *a, **k: {
        "ano": 2027, "valor_estimado": 999.0, "faixa_min": 900.0,
        "faixa_max": 1050.0, "unidade": "R$/60kg", "origem": "ia",
        "racional": "teste"})
    llm.limpar_cache_previsao()
    t = resumo_tendencia(_db_tendencia(), "feijao", "SP")
    llm.limpar_cache_previsao()

    assert t["projecao"]["origem"] == "ia"
    reg = t["projecao_tendencia"]
    assert reg is not None, "regressão sumiu quando a IA respondeu"
    assert reg["valor_estimado"] != 999.0
    # A IA carrega a regressão junto, para o card poder comparar as duas.
    assert t["projecao"]["valor_tendencia"] == reg["valor_estimado"]