"""Síntese narrativa: template determinístico + LLM opcional validado.

Regras (ver PROMPT_SINTESE.md): sem número inventado, com fonte/período,
com incerteza declarada, sem receita agronômica, sem promessa financeira.
"""

import os
import re

FONTE = "MAPA/SISSER 2016–2024"
INCERTEZA = ("cobertura por apólice não é cobertura por produtor: "
             "um produtor pode ter várias apólices e nem toda lavoura "
             "segurada aparece no PSR.")


def _int_pt(n):
    try:
        return f"{int(round(float(n))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "0"


def _pct1(x):
    try:
        return f"{float(x):.1f}".replace(".", ",")
    except (TypeError, ValueError):
        return "—"


def _reais(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "R$ 0"
    if v >= 1_000_000:
        return f"R$ {v / 1_000_000:.1f}".replace(".", ",") + " milhões"
    return "R$ " + _int_pt(v)


def _cultura_titulo(cultura):
    return str(cultura or "").replace("_", " ").replace("-", " ").title()


def frase_top10(ent):
    """Uma frase determinística por entrada, estilo spec §6.4b."""
    return (f"**#{ent.get('rank')} {ent.get('municipio')}/{ent.get('uf')} · "
            f"{_cultura_titulo(ent.get('cultura'))}** — "
            f"{_int_pt(ent.get('area_pequena_ha'))} ha de lavoura em apólices "
            f"de pequena propriedade, com apenas "
            f"{_pct1(ent.get('cobertura_pct'))}% da área segurada coberta. "
            f"{_int_pt(ent.get('apolices'))} apólices, "
            f"{_int_pt(ent.get('sinistros'))} sinistros, "
            f"{_reais(ent.get('pago_reais'))} pagos.")


def _agregar(linhas, chave):
    grupos = {}
    for lin in linhas:
        g = grupos.setdefault(lin.get(chave, ""), {
            "pares": 0, "area_pequena_ha": 0.0, "area_total_ha": 0.0,
            "apolices": 0, "sinistros": 0, "pago_reais": 0.0})
        g["pares"] += 1
        g["area_pequena_ha"] += float(lin.get("area_pequena_ha") or 0.0)
        g["area_total_ha"] += float(lin.get("area_total_ha") or 0.0)
        g["apolices"] += int(lin.get("apolices") or 0)
        g["sinistros"] += int(lin.get("sinistros") or 0)
        g["pago_reais"] += float(lin.get("pago_reais") or 0.0)
    saida = []
    for nome, g in grupos.items():
        tot = g["area_total_ha"]
        saida.append({chave: nome, **g,
                      "cobertura_pct": (round(g["area_pequena_ha"] / tot * 100, 2)
                                        if tot > 0 else None)})
    return sorted(saida, key=lambda g: -g["area_pequena_ha"])


def resumo_por_cultura(linhas):
    """Agregado por cultura, ordenado por área pequena desc."""
    return _agregar(linhas, "cultura")


def resumo_por_uf(linhas):
    """Agregado por UF, ordenado por área pequena desc."""
    return _agregar(linhas, "uf")


def _template(linhas):
    if not linhas:
        return ("Sem dados suficientes para priorizar a lacuna de cobertura "
                f"(fonte: {FONTE}). Nenhum par município × cultura com área "
                "de apólice pequena foi encontrado.")
    top = linhas[0]
    cults = resumo_por_cultura(linhas)
    ufs = resumo_por_uf(linhas)
    p1 = (f"A maior lacuna está em {top.get('municipio')}/{top.get('uf')} "
          f"· {_cultura_titulo(top.get('cultura'))}: "
          f"{_int_pt(top.get('area_pequena_ha'))} ha em apólices pequenas com "
          f"cobertura de {_pct1(top.get('cobertura_pct'))}% da área. "
          f"Por cultura, {_cultura_titulo(cults[0]['cultura'])} concentra "
          f"{_int_pt(cults[0]['area_pequena_ha'])} ha expostos; por UF, "
          f"{ufs[0]['uf']} lidera com {_int_pt(ufs[0]['area_pequena_ha'])} ha. "
          f"(fonte: {FONTE}).")
    p2 = (f"Isso importa porque a taxa de sinistro no topo é de "
          f"{_pct1(top.get('taxa_sinistro_pct'))}% "
          f"({_int_pt(top.get('sinistros'))} sinistros, "
          f"{_reais(top.get('pago_reais'))} pagos): muita lavoura pequena "
          "exposta onde o risco já se materializou em indenização.")
    p3 = (f"O gestor deveria começar pelos {min(10, len(linhas))} primeiros "
          "do ranking, verificando assistência técnica e acesso a apólice "
          "nesses municípios. Limite desta análise: " + INCERTEZA +
          " É análise de cobertura, não previsão de resultado financeiro.")
    return "\n\n".join([p1, p2, p3])


def _numeros_validos(texto, tabela):
    """Todo número citado precisa existir na tabela recebida."""
    digitos = lambda s: re.sub(r"\D", "", s or "")
    base = digitos(tabela)
    for num in re.findall(r"\d[\d.,]*", texto):
        if digitos(num) not in base:
            return False
    return True


def sintese_narrativa(linhas, llm_call=None):
    """Template determinístico; LLM só se llm_call(resposta) válida e fiel."""
    base = _template(linhas)
    if llm_call is None:
        return base
    try:
        from .ranking import to_csv
        tabela = to_csv(linhas)
        prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "PROMPT_SINTESE.md")
        with open(prompt_path, encoding="utf-8") as fh:
            prompt = fh.read()
        resp = llm_call(prompt + "\n\n## TABELA\n\n" + tabela)
    except Exception:
        return base
    if not resp or not isinstance(resp, str):
        return base
    try:
        if not _numeros_validos(resp, tabela):
            return base
    except Exception:
        return base
    return resp
