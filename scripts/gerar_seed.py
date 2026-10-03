"""Gera o seed `seed/agropilot.gz` a partir do Mongo local — LIMPO e REPRODUZÍVEL.

Por que este script existe
--------------------------
O dump anterior foi gerado na mao e tinha tres problemas:
  1. **Levava dado pessoal e de teste**: `produtores` com telefone, `pin_hash`,
     `pin_salt` e um cadastro "Teste PIN"; `sessoes` com `produtor_id: 'abc123'`;
     `mensagens` e `memorias` de teste. Isso foi para o GitHub Release, que
     qualquer pessoa do time baixa.
  2. **Estava velho**: sem `precos_previsao`, `geo_municipios` e o hub
     `municipios`, que a ingestion deriva do ZARC.
  3. **Sem manifesto**: ninguem sabia o que tinha dentro nem se o arquivo
     baixado estava integro.

O que este script faz
--------------------
  * Exporta APENAS as colecoes de referencia (dados publicos).
  * Zera as colecoes de usuario: sao de uso pessoal e nao pertencem a um dump
    distribuivel.
  * Recria o hub `municipios` a partir do ZARC (e o que o `buscar_municipio`
    usa para trocar "Araraquara" pelo codigo 3503208).
  * Grava `seed/manifest.json` com contagem, data e sha256 — assim o instalador
    valida o download e diz o que ha dentro.

Uso
---
    python scripts/gerar_seed.py
    python scripts/gerar_seed.py --saida-dir X
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

# --- o que entra no dump -----------------------------------------------
# Referencia publica: sem dado pessoal. E isso que faz o sistema funcionar.
COLECOES_REFERENCIA = [
    "zarc",              # zoneamento agricola (janela de plantio) — a maior
    "municipios",        # hub cod_ibge -> nome/UF, derivado do ZARC
    "psr_agregado",      # seguro rural (sinistros por evento)
    "sigef_agregado",    # producao de sementes (area/producao por municipio)
    "agrofit",           # catalogo de defensivos registrados
    "ana_atlas",         # atlas de irrigacao (ANA/SNIRH)
    "precos_conab",      # PAM/IBGE + PGPM/CONAB
    "precos_meta",       # controle de revalidacao do IBGE
    "precos_previsao",   # cache da previsao (deterministico)
    "geo_municipios",    # lat/lon para o clima
    "clima_cache",       # previsao em cache
]

# NUNCA entram no dump: sao de uso pessoal do produtor.
COLECOES_USUARIO = [
    "produtores", "sessoes", "sessoes_auth", "mensagens", "memorias",
]

DB_PADRAO = "agropilot"
MONGO_URL_PADRAO = "mongodb://localhost:27017"


def log(msg: str) -> None:
    print(f"[seed] {msg}", flush=True)


def err(msg: str) -> None:
    print(f"[seed] ERRO: {msg}", file=sys.stderr, flush=True)


def mongo_url(mongo_url: str | None) -> str:
    if mongo_url:
        return mongo_url
    return os.getenv("MONGO_URL") or MONGO_URL_PADRAO


def achar_tool(nome: str) -> str | None:
    """Acha um binario do MongoDB no PATH ou nos diretorios padrao."""
    achado = shutil.which(nome)
    if achado:
        return achado
    candidatos = [
        os.path.join(os.getenv("ProgramFiles", r"C:\Program Files"), "MongoDB", "Tools"),
        os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "mongosh"),
    ]
    for base in candidatos:
        if not base or not os.path.isdir(base):
            continue
        for raiz, _dirs, arquivos in os.walk(base):
            for arq in arquivos:
                if arq.lower() == f"{nome}.exe":
                    return os.path.join(raiz, arq)
    return None


def _rodar_mongo(tool: str, url: str, js: str) -> str:
    """Roda um trecho de JS no mongosh e devolve stdout+stderr combinado.

    A connection string vai como ARGUMENTO POSICIONAL: no Windows o mongosh
    tambem usa `/uri:`, entao `--uri valor` vira flag desconhecida e o script
    inteiro falha em silencio.
    """
    proc = subprocess.run([tool, "--quiet", url, "--eval", js],
                          capture_output=True, text=True, errors="replace")
    return (proc.stdout or "") + (proc.stderr or "")


def _limpar_usuario(mongosh: str, url: str, db: str) -> None:
    """Zera as colecoes de usuario ANTES do dump, para o arquivo sair limpo."""
    js = (
        f"const d = db.getSiblingDB('{db}');"
        "const u = ['produtores','sessoes','sessoes_auth','mensagens','memorias'];"
        "for (const c of u) { if (d.getCollectionNames().includes(c)) "
        "{ const n = d.getCollection(c).deleteMany({}).deletedCount;"
        " print('ZERADO ' + c + ' ' + n); } }"
    )
    saida = _rodar_mongo(mongosh, url, js)
    achou = [l for l in saida.splitlines() if l.startswith("ZERADO")]
    if achou:
        for linha in achou:
            log(f"higiene: {linha.strip()}")
    else:
        log("higiene: nada a limpar (ou sem permissao)")


def _reconstruir_municipios(url: str, db: str) -> None:
    """Recria o hub `municipios` (cod_ibge -> nome/UF) a partir do ZARC.

    Sem ele o `buscar_municipio` cai na API do IBGE a cada chamada e some
    quando nao ha rede.
    """
    try:
        from pymongo import MongoClient
    except ImportError:
        log("pymongo ausente: hub municipios nao foi reconstruido")
        return
    try:
        base = MongoClient(url, serverSelectionTimeoutMS=8000)[db]
        if "zarc" not in base.list_collection_names():
            err("colecao zarc nao existe; hub municipios nao pode ser derivado")
            return
        pipeline = [
            {"$group": {
                "_id": "$cod_ibge",
                "nome": {"$first": "$municipio"},
                "uf": {"$first": "$UF"},
                "municipio": {"$first": "$municipio"},
            }},
            {"$match": {"_id": {"$nin": [None, ""]}}},
        ]
        docs = list(base.zarc.aggregate(pipeline))
        base.municipios.delete_many({})
        if docs:
            base.municipios.insert_many(docs)
        try:
            base.municipios.create_index([("cod_ibge", 1)], unique=True,
                                         name="municipios_cod_ibge")
        except Exception:
            pass
        log(f"hub municipios: {len(docs)} municipios a partir do ZARC")
    except Exception as e:
        err(f"hub municipios falhou: {e!r}")


def _contar(mongosh: str | None, url: str, db: str) -> dict:
    contagens: dict[str, int] = {}
    if not mongosh:
        return contagens
    cols = ",".join(f"'{c}'" for c in COLECOES_REFERENCIA)
    js = (
        f"const d = db.getSiblingDB('{db}');"
        f"const cols = [{cols}];"
        "for (const c of cols) { if (d.getCollectionNames().includes(c)) "
        "{ print('CONTAGEM ' + c + ' ' + d.getCollection(c).countDocuments({})); } }"
    )
    for linha in _rodar_mongo(mongosh, url, js).splitlines():
        if linha.startswith("CONTAGEM "):
            partes = linha.split()
            if len(partes) >= 3:
                try:
                    contagens[partes[1]] = int(partes[2])
                except ValueError:
                    pass
    return contagens


def _sha256(caminho: str) -> str:
    """Hash do arquivo, lido em blocos (o dump tem ~35 MB)."""
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Gera o seed limpo do AgroPilot")
    ap.add_argument("--saida-dir", default=None, help="onde gravar (padrao: seed/)")
    ap.add_argument("--db", default=DB_PADRAO)
    ap.add_argument("--mongo-url", default=None)
    ap.add_argument("--somente-manifesto", action="store_true",
                    help="nao gera o dump; so reescreve o manifesto com o que ha no banco")
    args = ap.parse_args()

    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    saida_dir = args.saida_dir or os.path.join(raiz, "seed")
    os.makedirs(saida_dir, exist_ok=True)
    arquivo = os.path.join(saida_dir, "agropilot.gz")

    url = mongo_url(args.mongo_url)
    log(f"banco: {url}")

    mongosh = achar_tool("mongosh")

    if not args.somente_manifesto:
        mongodump = achar_tool("mongodump")
        if not mongodump:
            err("mongodump nao encontrado. Instale as MongoDB Database Tools "
                "(winget install --id MongoDB.DatabaseTools "
                "| brew install mongodb-database-tools | apt install mongodb-database-tools)")
            return 1

        # 0) higiene: sem dado de usuario no dump distribuivel
        if mongosh:
            _limpar_usuario(mongosh, url, args.db)
        else:
            log("mongosh ausente: colecoes de usuario nao foram limpas")

        # 1) hub municipios derivado do ZARC
        _reconstruir_municipios(url, args.db)

        # 2) dump propriamente dito
        if os.path.exists(arquivo):
            os.remove(arquivo)
        # Duas regras que quebram em Windows se ignoradas:
        #  1) a connection string e ARGUMENTO POSICIONAL (o Windows usa /uri:);
        #  2) toda opcao e `--opt=valor` (com espaco, o mongodump trata o valor
        #     como segundo positional e reclama de "two connection strings").
        cmd = [mongodump, url, f"--db={args.db}", "--gzip",
               f"--archive={arquivo}", "--numParallelCollections=4"]
        for col in COLECOES_USUARIO:
            cmd.append(f"--excludeCollection={col}")

        log("gerando dump (pode levar alguns minutos) ...")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            err(f"mongodump falhou: {(proc.stderr or '').strip()[:500]}")
            return 1
    else:
        log("somente manifesto: dump nao foi regerado")

    contagens = _contar(mongosh, url, args.db)
    manifesto = {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "db": args.db,
        "colecoes": contagens,
        "total_documentos": sum(contagens.values()),
        "tamanho_bytes": os.path.getsize(arquivo) if os.path.exists(arquivo) else 0,
        "sha256": _sha256(arquivo) if os.path.exists(arquivo) else "",
        "observacao": (
            "Dump limpo: so dados publicos de referencia. Produtores, sessoes, "
            "mensagens e memorias NAO vao no seed."
        ),
    }
    with open(os.path.join(saida_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifesto, fh, ensure_ascii=False, indent=2)

    log(f"pronto: {arquivo} ({manifesto['tamanho_bytes'] / 1048576:.1f} MB)")
    log(f"documentos no banco: {manifesto['total_documentos']}")
    for nome, qtd in sorted(contagens.items()):
        log(f"  {nome:<18} {qtd:>9}")
    log(f"manifesto: {os.path.join(saida_dir, 'manifest.json')}")
    log("")
    log("para publicar: gh release upload data seed/agropilot.gz --clobber")
    return 0
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()
if __name__ == "__main__":
    raise SystemExit(main())