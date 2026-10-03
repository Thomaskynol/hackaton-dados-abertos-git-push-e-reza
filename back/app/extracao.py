"""Extração REAL do cadastro por chat (sem alucinar).

Interpreta o que o produtor digita em linguagem natural e casa com dado oficial:
  - "Araraquara SP" / "Rio Verde - GO" -> cod_ibge via municípios (Mongo) ou,
    se a coleção estiver vazia, via IBGE Localidades (API pública).
  - "feijão e milho" -> ["feijao", "milho"] (canônicas, só as do escopo real).
  - "uns 10 hectares" -> 10.0.

Nunca inventa cod_ibge: se não achar o município, devolve None e quem chama
pede de novo. Stdlib + as tools/urllib que o projeto já usa.
"""
import logging
import re
import unicodedata

log = logging.getLogger(__name__)

IBGE_MUNICIPIOS = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

UFS_VALIDAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
}

# nome de estado por extenso -> sigla (quando o produtor escreve o nome)
ESTADO_SIGLA = {
    "acre": "AC", "alagoas": "AL", "amazonas": "AM", "amapa": "AP",
    "bahia": "BA", "ceara": "CE", "distrito federal": "DF",
    "espirito santo": "ES", "goias": "GO", "maranhao": "MA",
    "minas gerais": "MG", "mato grosso do sul": "MS", "mato grosso": "MT",
    "para": "PA", "paraiba": "PB", "pernambuco": "PE", "piaui": "PI",
    "parana": "PR", "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rondonia": "RO", "roraima": "RR", "rio grande do sul": "RS",
    "santa catarina": "SC", "sergipe": "SE", "sao paulo": "SP",
    "tocantins": "TO",
}

# culturas do escopo com dado real no sistema (ZARC/PAM/PSR). Aliases incluídos.
CULTURAS_CONHECIDAS = {
    "milho": "milho", "soja": "soja", "feijao": "feijao", "feijão": "feijao",
    "arroz": "arroz", "trigo": "trigo", "cafe": "cafe", "café": "cafe",
    "cana": "cana_de_acucar", "cana-de-acucar": "cana_de_acucar",
    "algodao": "algodao", "algodão": "algodao", "sorgo": "sorgo",
    "amendoim": "amendoim", "uva": "uva", "tomate": "tomate",
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.strip().lower()


def _get_json(url, timeout=10):
    """GET JSON simples (reusa o robusto do clima quando possível)."""
    try:
        from .clima import _get_json as cj
        return cj(url, timeout=timeout)
    except Exception:
        pass
    try:
        import json
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "AgroPilot/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception as e:
        log.warning("extracao _get_json falhou: %r", e)
        return None


def separar_cidade_uf(texto: str) -> tuple[str, str | None]:
    """"Araraquara - SP" / "Rio Verde GO" / "Sao Paulo, Sao Paulo" -> (cidade, UF|None)."""
    t = (texto or "").strip()
    if not t:
        return "", None
    # separa por traço/vírgula primeiro: "cidade - uf"
    partes = re.split(r"\s*[-–,/]\s*", t)
    if len(partes) >= 2:
        cidade = partes[0].strip()
        cauda = partes[-1].strip()
        uf = _uf_de(cauda)
        if uf:
            return cidade, uf
    # senão: última palavra pode ser a sigla
    toks = t.split()
    if len(toks) >= 2:
        uf = _uf_de(toks[-1])
        if uf:
            return " ".join(toks[:-1]).strip(), uf
    # estado por extenso no fim (ex.: "Uberlândia Minas Gerais")
    nt = _norm(t)
    for nome, sigla in sorted(ESTADO_SIGLA.items(), key=lambda kv: -len(kv[0])):
        if nt.endswith(nome):
            cidade = t[: len(t) - len(nome)].strip(" -,/")
            return cidade, sigla
    return t, None


def _uf_de(token: str) -> str | None:
    tk = _norm(token)
    if tk.upper() in UFS_VALIDAS:
        return tk.upper()
    if len(tk) == 2 and tk.upper() in UFS_VALIDAS:
        return tk.upper()
    return ESTADO_SIGLA.get(tk)


def resolver_municipio(db, texto: str) -> dict | None:
    """Texto livre -> {cod_ibge, nome, uf} REAL. None se não achar (nunca inventa)."""
    cidade, uf = separar_cidade_uf(texto)
    if not cidade:
        return None

    # 1) coleção municípios (Mongo), se existir
    try:
        from .tools import dispatch
        r = dispatch(db, "buscar_municipio", {"nome": cidade, "uf": uf} if uf
                     else {"nome": cidade})
        if r and not r.get("erro") and r.get("cod_ibge"):
            return {"cod_ibge": str(r["cod_ibge"]), "nome": r.get("nome"), "uf": r.get("uf")}
    except Exception as e:
        log.warning("buscar_municipio falhou: %r", e)

    # 2) IBGE Localidades (API pública) por nome; filtra pela UF quando houver
    dados = _get_json(f"{IBGE_MUNICIPIOS}?orderBy=nome")
    if not isinstance(dados, list):
        return None
    alvo = _norm(cidade)
    candidatos = []
    for m in dados:
        try:
            if _norm(m.get("nome")) != alvo:
                continue
            sigla = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
            candidatos.append({"cod_ibge": str(m.get("id")), "nome": m.get("nome"), "uf": sigla})
        except Exception:
            continue
    if not candidatos:
        return None
    if uf:
        for c in candidatos:
            if c["uf"] == uf:
                return c
        # cidade existe mas não nessa UF -> não arrisca
        return None
    # sem UF e nome único -> aceita; nome ambíguo -> pede UF (None)
    return candidatos[0] if len(candidatos) == 1 else None


def extrair_culturas(texto: str) -> list[str]:
    """"planto feijão e um pouco de milho" -> ['feijao','milho'] (canônicas)."""
    t = _norm(texto)
    achadas = []
    for chave, canon in CULTURAS_CONHECIDAS.items():
        if re.search(rf"\b{re.escape(_norm(chave))}\b", t):
            if canon not in achadas:
                achadas.append(canon)
    return achadas


def extrair_area(texto: str) -> float | None:
    """"uns 10,5 hectares" / "5 ha" / "20" -> float. None se não houver número."""
    t = (texto or "").replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if not m:
        return None
    try:
        v = float(m.group(1))
        return v if v > 0 else None
    except ValueError:
        return None
