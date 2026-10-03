"""GET /api/precos — consultor comercial: preços de referência + canais + análise.

Serve dados REAIS de preço mínimo (CONAB/PGPM) via precos_dados (Mongo com
fallback de arquivo), os canais de escoamento por categoria (PAA/PNAE/
cooperativa/cerealista/feira) e uma ANÁLISE comercial gerada por IA quando há
chave LLM — senão uma análise heurística honesta construída dos próprios dados.

Nunca raise: qualquer falha vira estado honesto. Nunca "venda agora".
"""
import logging

from fastapi import APIRouter, Query

from ..db import get_db
from ..precos_dados import precos_da_uf, rotulo_cultura, canon_cultura, resumo_tendencia
from ..llm import gerar_analise_comercial

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Precos"])

UFS_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins",
}


def _canais(uf: str) -> dict:
    """Canais de escoamento por categoria. Nunca nome de empresa — só categorias oficiais."""
    nome_uf = UFS_NOME.get(uf, uf)
    return {
        "uf": uf, "estado": "disponivel",
        "programas": ["PAA — Programa de Aquisição de Alimentos",
                      "PNAE — Alimentação Escolar"],
        "canais": [
            {"id": "pnae", "categoria": "PNAE — merenda escolar",
             "destaque": "paga prêmio sobre o mercado",
             "descricao": "As escolas públicas são obrigadas por lei a comprar da agricultura familiar. Costumam pagar acima do preço de mercado. Procure a Secretaria de Educação do município."},
            {"id": "paa", "categoria": "PAA — compras públicas",
             "destaque": "venda garantida por chamada",
             "descricao": "O governo compra a sua produção por chamada pública, com preço de referência. Procure a Secretaria de Agricultura ou a CONAB."},
            {"id": "cooperativas", "categoria": "Cooperativas",
             "destaque": "mais força na negociação",
             "descricao": "Entregando junto com outros produtores, você vende em escala e negocia melhor. As regras variam de cooperativa para cooperativa."},
            {"id": "feiras", "categoria": "Feiras e venda direta",
             "destaque": "melhor margem, sem atravessador",
             "descricao": "Vender direto ao consumidor na feira ou na porteira elimina o intermediário e melhora a sua margem."},
            {"id": "cerealistas", "categoria": "Cerealistas e armazéns",
             "destaque": "pagamento rápido",
             "descricao": "Compra local com pagamento rápido; as condições mudam por praça e época do ano. Compare sempre com o preço do dia."},
        ],
        "detalhe": f"Em {nome_uf}, os canais públicos (PAA e PNAE) são o caminho mais vantajoso para a agricultura familiar: compram por chamada pública e costumam pagar um prêmio sobre o mercado. Compare sempre com o preço do dia antes de fechar.",
        "fonte": {
            "nome": "PAA / PNAE — programas federais da agricultura familiar",
            "periodo": "vigente",
            "url": "https://www.gov.br/conab/pt-br/atuacao/abastecimento-social",
            "limitacoes": ["Sem lista de compradores: as chamadas e editais variam por município.",
                           "Regras e prazos mudam por edital — confirme na secretaria local."],
        },
    }


def _frase_tendencia(cultura_label: str, tendencia: dict) -> str:
    """Frase humana sobre a tendência/projeção real (IBGE), ou vazia."""
    if not tendencia or tendencia.get("estado") != "disponivel":
        return ""
    ult = tendencia.get("ultimo") or {}
    proj = tendencia.get("projecao") or {}
    direcao = tendencia.get("direcao")
    verbo = {"subindo": "vem subindo", "caindo": "vem caindo"}.get(direcao, "tem se mantido estável")
    base = (
        f"Olhando os últimos anos, o preço do {cultura_label.lower()} na sua região {verbo} "
        f"(no último dado, cerca de R$ {ult.get('valor')} a saca)."
    )
    if proj and proj.get("valor_estimado"):
        base += (
            f" Seguindo essa tendência, para {proj.get('ano')} a conta aponta algo perto de "
            f"R$ {proj.get('valor_estimado')} a saca — é só uma estimativa para você se planejar, não uma promessa."
        )
    return base


def _analise_heuristica(cultura_label: str, pgpm: dict, canais: dict, tendencia: dict | None = None) -> dict:
    """Análise honesta montada dos próprios dados quando não há IA."""
    frase_tend = _frase_tendencia(cultura_label, tendencia or {})
    piso = pgpm.get("valor")
    if piso is not None:
        unidade = pgpm.get("unidade", "R$/60kg")
        valor_fmt = f"R$ {piso:.2f}".replace(".", ",")
        texto = (
            f"O piso oficial do {cultura_label.lower()} hoje é {valor_fmt} por {unidade.replace('R$/', '')} "
            f"(preço mínimo da CONAB) — a sua rede de proteção, o mínimo que o governo ajuda a garantir. "
        )
        if frase_tend:
            texto += frase_tend + " "
        texto += (
            "Antes de fechar negócio, confira o preço do dia no Cepea e compare com os canais ao lado — "
            "a merenda escolar (PNAE) e o PAA costumam pagar acima do mercado para a agricultura familiar. "
            "Próximo passo: procure a secretaria de agricultura do seu município e pergunte das chamadas públicas abertas."
        )
        fonte = "Fonte: IBGE/PAM + CONAB/PGPM"
    else:
        texto = ""
        if frase_tend:
            texto += frase_tend + " "
        texto += (
            f"Ainda não temos o piso oficial do {cultura_label.lower()} publicado, então use o indicador diário "
            f"do Cepea para o preço do dia e compare com os canais ao lado. A merenda escolar (PNAE) e o PAA "
            f"costumam pagar um prêmio sobre o mercado para a agricultura familiar. Próximo passo: procure a "
            f"secretaria de agricultura do município e pergunte das chamadas públicas abertas."
        )
        fonte = "Fonte: IBGE/PAM + PAA/PNAE"
    return {"texto": texto.strip(), "origem": "heuristica", "fonte": fonte}


def _contexto_llm(cultura_label: str, uf: str, pgpm: dict, mercado: dict,
                  canais: dict, tendencia: dict) -> str:
    piso = pgpm.get("valor")
    linhas = [
        f"Produtor da agricultura familiar quer vender melhor a cultura: {cultura_label} no estado {uf}.",
        f"Preço mínimo oficial (piso PGPM/CONAB): {('R$ %.2f por %s' % (piso, pgpm.get('unidade','R$/60kg'))) if piso is not None else 'ainda não publicado na base'}"
        + (f", safra {pgpm.get('data')}" if pgpm.get("data") else "") + ".",
    ]
    # Série histórica real (IBGE) — base para a IA falar de tendência/projeção.
    if tendencia.get("estado") == "disponivel":
        ult = tendencia.get("ultimo") or {}
        proj = tendencia.get("projecao") or {}
        linhas.append(
            f"Histórico do preço recebido pelo produtor (IBGE, média anual do estado): "
            f"em {ult.get('ano')} ficou em R$ {ult.get('valor')}/{tendencia.get('unidade')}; "
            f"média dos últimos anos R$ {tendencia.get('media_recente')}; "
            f"tendência {tendencia.get('direcao')}."
        )
        if proj:
            linhas.append(
                f"Projeção simples para {proj.get('ano')}: cerca de R$ {proj.get('valor_estimado')} "
                f"(entre R$ {proj.get('faixa_min')} e R$ {proj.get('faixa_max')}). "
                f"É estimativa de tendência, não garantia."
            )
    linhas.append("Indicador do dia: disponível no site do Cepea/ESALQ (não temos o número aqui).")
    linhas.append("Canais de escoamento disponíveis (por categoria, sem nome de empresa):")
    for c in canais.get("canais", []):
        linhas.append(f"- {c['categoria']}: {c.get('destaque','')}. {c['descricao']}")
    linhas.append("Gere uma orientação curta para ajudar o produtor a planejar a venda, "
                  "citando a tendência de preço quando houver. Nunca mande vender agora nem esperar.")
    return "\n".join(linhas)


@router.get("/precos")
def get_precos(uf: str = Query(...), cultura: str | None = None):
    uf = (uf or "").strip().upper()
    if uf not in UFS_NOME:
        uf = "SP"
    cult_canon = canon_cultura(cultura) if cultura else None
    cultura_label = rotulo_cultura(cult_canon)

    try:
        db = get_db()
    except Exception as e:
        log.warning("get_db falhou em /precos: %r", e)
        db = None

    precos = precos_da_uf(db, cultura, uf)
    pgpm, mercado, _cepea = precos[0], precos[1], precos[2]
    canais = _canais(uf)

    # Série histórica real (IBGE) + tendência/projeção — base para a predição.
    try:
        tendencia = resumo_tendencia(db, cultura, uf) if cultura else {"estado": "insuficiente"}
    except Exception as e:
        log.warning("tendencia falhou: %r", e)
        tendencia = {"estado": "insuficiente"}

    # Análise comercial: IA quando houver chave; senão heurística honesta.
    analise = None
    try:
        ctx = _contexto_llm(cultura_label, uf, pgpm, mercado, canais, tendencia)
        texto_ia = gerar_analise_comercial(ctx)
        if texto_ia:
            analise = {"texto": texto_ia, "origem": "ia",
                       "fonte": "Fonte: IBGE/PAM + CONAB/PGPM + canais PAA/PNAE"}
    except Exception as e:
        log.warning("analise IA falhou: %r", e)
    if analise is None:
        analise = _analise_heuristica(cultura_label, pgpm, canais, tendencia)

    return {
        "uf": {"sigla": uf, "nome": UFS_NOME.get(uf, uf)},
        "cultura": cultura_label,
        "precos": precos,
        "canais": canais,
        "tendencia": tendencia,
        "analise": analise,
    }
