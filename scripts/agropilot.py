"""AgroPilot — instalador/servidor local, Windows e Linux com o MESMO comando.

Por que Python e nao um .ps1 + um .sh?
    Porque o projeto ja exige Python (backend) e Node (front). Um CLI em Python
    roda igual nos dois sistemas, sem duplicar regra de instalacao em duas
    linguagens — que e como os dois scripts divergiram ate agora.

Comandos
--------
    python scripts/agropilot.py doctor      # o que falta na maquina
    python scripts/agropilot.py setup       # instala deps + cria .env + popula o banco
    python scripts/agropilot.py up          # sobe API (8000) e front (3000)
    python scripts/agropilot.py down        # derruba o que o script subiu
    python scripts/agropilot.py status      # o que esta de pe
    python scripts/agropilot.py seed        # (re)restaura o banco
    python scripts/agropilot.py seed --force
    python scripts/agropilot.py logs [-f]   # ultimas linhas dos dois logs
    python scripts/agropilot.py tudo        # setup + up  (o comando do dia a dia)

Variaveis de ambiente
---------------------
    AGROPILOT_PORTA_API=8000     AGROPILOT_PORTA_FRONT=3000
    AGROPILOT_MONGO=mongodb://localhost:27017
    AGROPILOT_SKIP_DOWNLOAD=1    nao tenta baixar o seed (usa o que esta em seed/)
    AGROPILOT_IGNORAR_HASH=1     restaura mesmo se o sha256 nao bater
    AGROPILOT_SEM_ROOT=1         nunca chama sudo; instala so no home do usuario
    SEED_URL / GH_TOKEN          origem alternativa do dump (repo privado)

Linux sem root
--------------
    Nem toda maquina de aluno tem sudo. Quando o gerenciador do SO falha (ou
    AGROPILOT_SEM_ROOT=1), o script instala MongoDB, mongosh, Database Tools e
    Node.js a partir dos tarballs oficiais, dentro de ~/.local/bin. Nada e
    escrito em /usr, nada precisa de senha.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------- constantes
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACK = os.path.join(RAIZ, "back")
FRONT = os.path.join(RAIZ, "front")
SEED_DIR = os.path.join(RAIZ, "seed")
SEED_ARQ = os.path.join(SEED_DIR, "agropilot.gz")
MANIFESTO = os.path.join(SEED_DIR, "manifest.json")
ENV_EXEMPLO = os.path.join(BACK, ".env.example")
ENV_ALVO = os.path.join(BACK, ".env")

REPO_GITHUB = "Thomaskynol/hackaton-dados-abertos-sql-injection"
TAG_RELEASE = "data"
URL_RELEASE = (
    f"https://github.com/{REPO_GITHUB}/releases/download/{TAG_RELEASE}/agropilot.gz"
)

PORTA_API = int(os.getenv("AGROPILOT_PORTA_API", "8000"))
PORTA_FRONT = int(os.getenv("AGROPILOT_PORTA_FRONT", "3000"))
MONGO_URL = os.getenv("AGROPILOT_MONGO", "mongodb://localhost:27017")

API_URL = f"http://127.0.0.1:{PORTA_API}"
FRONT_URL = f"http://localhost:{PORTA_FRONT}"

IS_WINDOWS = os.name == "nt"

# Onde o instalador sem root guarda os binarios. Entra no PATH do processo e de
# todos os subprocessos, para que `tem("mongod")` e o Popen do mongod achem o
# executavel que acabamos de instalar. Entra sempre, mesmo ainda nao existindo:
# o proprio instalador e quem cria a pasta.
LOCAL_BIN = os.path.join(os.path.expanduser("~"), ".local", "bin")
if not IS_WINDOWS:
    _parts = (os.environ.get("PATH") or "").split(os.pathsep)
    if LOCAL_BIN not in _parts:
        os.environ["PATH"] = LOCAL_BIN + os.pathsep + os.environ["PATH"]

VERSAO_DBT = "100.10.0"
VERSAO_MONGOSH = "2.5.5"
VERSAO_SERVIDOR_MONGODB = "8.0.4"
URL_FASTDL = "https://fastdl.mongodb.org"
URL_MONGOSH = "https://downloads.mongodb.com/compass"
URL_NODE_INDEX = "https://nodejs.org/dist/index.json"
# Logs e PIDs no temp do usuario: nao suja o repo.
TMP = os.path.join(
    os.environ.get("TEMP") or os.environ.get("TMPDIR") or "/tmp", "agropilot"
)
PID_API = os.path.join(TMP, "api.pid")
PID_FRONT = os.path.join(TMP, "front.pid")
LOG_API = os.path.join(TMP, "api.log")
LOG_API_ERR = os.path.join(TMP, "api.err.log")
LOG_FRONT = os.path.join(TMP, "front.log")
LOG_FRONT_ERR = os.path.join(TMP, "front.err.log")

VERDE, AMARELO, VERMELHO, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[0m"


# ----------------------------------------------------------------- utilidades
def say(msg: str = "") -> None:
    print(f"{VERDE}[agropilot]{RESET} {msg}", flush=True)


def aviso(msg: str) -> None:
    print(f"{AMARELO}[agropilot] AVISO:{RESET} {msg}", flush=True)


def erro(msg: str) -> None:
    print(f"{VERMELHO}[agropilot] ERRO:{RESET} {msg}", file=sys.stderr, flush=True)


def die(msg: str, codigo: int = 1) -> None:
    erro(msg)
    raise SystemExit(codigo)


def tem(comando: str) -> bool:
    return shutil.which(comando) is not None


def venv_python() -> str:
    if IS_WINDOWS:
        return os.path.join(BACK, ".venv", "Scripts", "python.exe")
    return os.path.join(BACK, ".venv", "bin", "python")


def rodar(cmd, **kw) -> subprocess.CompletedProcess:
    """Roda comando tolerando ruido no stderr (mongosh escreve avisos ali)."""
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("errors", "replace")
    return subprocess.run(cmd, **kw)


def ok(proc) -> bool:
    return proc is not None and proc.returncode == 0


def url_responde(url: str, timeout: float = 2.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status < 500
    except urllib.error.HTTPError as e:
        # 404 ainda significa "o servidor respondeu".
        return e.code < 500
    except Exception:
        return False


def aguardar(url: str, segundos: int) -> bool:
    fim = time.time() + segundos
    while time.time() < fim:
        if url_responde(url):
            return True
        time.sleep(1.0)
    return False


def porta_aberta(porta: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", porta)) == 0


def achar_mongo_tool(nome: str) -> str | None:
    """Acha mongosh/mongorestore/mongodump no PATH ou nos diretorios padrao."""
    achado = shutil.which(nome)
    if achado:
        return achado
    alvos = []
    if IS_WINDOWS:
        alvos += [
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                         "MongoDB", "Tools"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "mongosh"),
        ]
    else:
        alvos += ["/usr/bin", "/usr/local/bin", os.path.expanduser("~/.local/bin")]
    for base in alvos:
        if not base or not os.path.isdir(base):
            continue
        if not IS_WINDOWS:
            cand = os.path.join(base, nome)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        for raiz, _d, arquivos in os.walk(base):
            for arq in arquivos:
                if arq.lower() in (f"{nome}.exe", nome):
                    return os.path.join(raiz, arq)
    return None


# ----------------------------------------------------------- instalar deps
def como_instalar() -> str:
    """Nome do gerenciador de pacotes deste SO (vazio se nao houver)."""
    so = platform.system()
    if so == "Windows":
        if tem("winget"):
            return "winget"
        if tem("choco"):
            return "choco"
        return ""
    if so == "Darwin":
        return "brew" if tem("brew") else ""
    for g in ("apt-get", "dnf", "pacman"):
        if tem(g):
            return g
    return ""


def tem_sudo() -> bool:
    """Diz se da para instalar pelo gerenciador do SO (root de verdade ou sudo)."""
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return True
    return shutil.which("sudo") is not None


def sudo_sem_senha() -> bool:
    """sudo funciona sem digitar nada (util para saber se o script trava)."""
    if not tem_sudo():
        return False
    return ok(rodar(["sudo", "-n", "true"], timeout=10))


def sem_root_forcado() -> bool:
    """AGROPILOT_SEM_ROOT=1 manda nunca chamar sudo."""
    return os.getenv("AGROPILOT_SEM_ROOT", "").strip() not in ("", "0", "false")


def _os_release() -> tuple[str, str]:
    """(ID, VERSION_ID) do /etc/os-release. Mint devolve a versao do Ubuntu."""
    for caminho in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            with open(caminho, encoding="utf-8") as fh:
                dados = dict(
                    linha.split("=", 1) for linha in fh.read().splitlines()
                    if "=" in linha and not linha.startswith("#")
                )
        except OSError:
            continue
        limpado = {k: v.strip().strip('"') for k, v in dados.items()}
        id_ = limpado.get("ID", "")
        versao = limpado.get("VERSION_ID", "")
        if id_ == "linuxmint":
            versao = {"22": "24.04", "21": "22.04", "20": "20.04"}.get(
                versao.split(".")[0], versao)
            id_ = "ubuntu"
        if not versao:
            for caminho_up in ("/etc/upstream-release/lsb-release", "/etc/lsb-release"):
                try:
                    with open(caminho_up, encoding="utf-8") as fh:
                        for linha in fh.read().splitlines():
                            if linha.startswith("DISTRIB_RELEASE="):
                                versao = linha.split("=", 1)[1].strip().strip('"')
                except OSError:
                    pass
                if versao:
                    break
        return id_, versao
    return "", ""


ARQ_MONGODB = {
    "ubuntu2204": "ubuntu2204", "jammy": "ubuntu2204",
    "ubuntu2404": "ubuntu2404", "noble": "ubuntu2404",
    "ubuntu2004": "ubuntu2004", "focal": "ubuntu2004",
    "debian11": "debian11", "bullseye": "debian11",
    "debian12": "debian12", "bookworm": "debian12",
    "rhel80": "rhel80", "rhel90": "rhel90",
}
ARQUITETURA_MONGODB = {"x86_64": "x86_64", "amd64": "x86_64",
                       "aarch64": "aarch64", "arm64": "aarch64"}
# Ordem de tentativa quando a distro nao bate com nenhum nome conhecido.
FALLBACKS_MONGODB = ["ubuntu2404", "ubuntu2204", "debian12", "debian11",
                     "rhel90", "rhel80", "ubuntu2004"]


def _url_existe(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def build_mongodb() -> str | None:
    """Nome da build do MongoDB que serve nesta maquina (ubuntu2404, rhel90...)."""
    arch = ARQUITETURA_MONGODB.get(platform.machine())
    if not arch:
        return None
    _id, versao = _os_release()
    achado = ARQ_MONGODB.get(versao.replace(".", ""))
    candidatas = ([achado] if achado else []) + [
        c for c in FALLBACKS_MONGODB if c != achado]
    for build in candidatas:
        url = (f"{URL_FASTDL}/tools/db/mongodb-database-tools-"
               f"{build}-{arch}-{VERSAO_DBT}.tgz")
        if _url_existe(url):
            return build
    return None


def instalar_tarball(url: str, destino: str = LOCAL_BIN) -> list[str]:
    """Baixa um pacote .tgz/.tar.xz e copia o que esta em <pacote>/bin/ pro home.

    Devolve os nomes instalados. Levanta RuntimeError se o pacote nao tiver
    pasta bin/ ou se o download falhar.
    """
    import tarfile
    import tempfile

    if IS_WINDOWS:
        raise RuntimeError("instalar por tarball so funciona no Linux/macOS")

    os.makedirs(destino, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agropilot-") as tmp:
        say(f"baixando {url.rsplit('/', 1)[-1]} ...")
        pacote = os.path.join(tmp, "pacote.tar")
        if not _baixar(url, pacote, None):
            raise RuntimeError(f"download falhou: {url}")
        with tarfile.open(pacote) as tf:
            try:
                tf.extractall(tmp, filter="data")
            except TypeError:
                tf.extractall(tmp)

        achados: list[str] = []
        for raiz, _dirs, arquivos in os.walk(tmp):
            if os.path.basename(raiz) == "bin":
                achados = [os.path.join(raiz, a) for a in arquivos]
                break
        if not achados:
            raise RuntimeError(f"o pacote {url} nao tem pasta bin/")

        for caminho in achados:
            shutil.copy2(caminho, os.path.join(destino, os.path.basename(caminho)))
        nomes = [os.path.basename(c) for c in achados]

    for nome in nomes:
        alvo = os.path.join(destino, nome)
        if os.path.isfile(alvo) and not os.access(alvo, os.X_OK):
            os.chmod(alvo, 0o755)
    say(f"instalado em {destino}: " + ", ".join(nomes))
    return nomes


def instalar_dbt_sem_root() -> None:
    """MongoDB Database Tools (mongorestore, mongodump) no home do usuario."""
    build = build_mongodb()
    if not build:
        raise RuntimeError(
            "distro sem build conhecida do MongoDB; instale manualmente em "
            "https://www.mongodb.com/try/download/database-tools")
    arch = ARQUITETURA_MONGODB[platform.machine()]
    instalar_tarball(f"{URL_FASTDL}/tools/db/mongodb-database-tools-"
                     f"{build}-{arch}-{VERSAO_DBT}.tgz")


def instalar_mongosh_sem_root() -> None:
    """mongosh no home do usuario."""
    arch = {"x86_64": "x64", "amd64": "x64",
            "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine())
    if not arch:
        raise RuntimeError("arquitetura sem build oficial do mongosh")
    instalar_tarball(f"{URL_MONGOSH}/mongosh-{VERSAO_MONGOSH}-linux-{arch}.tgz")


def instalar_mongod_sem_root() -> None:
    """Servidor mongod no home do usuario (para rodar local, sem systemd)."""
    build = build_mongodb()
    if not build:
        raise RuntimeError(
            "distro sem build conhecida do MongoDB; instale manualmente em "
            "https://www.mongodb.com/try/download/community")
    arch = ARQUITETURA_MONGODB[platform.machine()]
    instalar_tarball(f"{URL_FASTDL}/linux/mongodb-linux-{arch}-{build}-"
                     f"{VERSAO_SERVIDOR_MONGODB}.tgz")


def instalar_node_sem_root() -> None:
    """Node.js LTS no home do usuario. npm precisa da pasta lib/ junto, entao o
    pacote vai inteiro para ~/.local/lib/node/<versao> e o bin/ e linkado."""
    import tarfile
    import tempfile

    arch = {"x86_64": "x64", "amd64": "x64",
            "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine())
    if not arch:
        raise RuntimeError("arquitetura sem build oficial do Node.js")
    with urllib.request.urlopen(URL_NODE_INDEX, timeout=60) as r:
        versoes = json.loads(r.read().decode("utf-8"))
    alvo = next((v for v in versoes
                 if v.get("lts") and f"linux-{arch}" in v.get("files", [])), None)
    if not alvo:
        raise RuntimeError("nodejs.org/dist/index.json sem LTS para linux")

    # O index.json ja traz o "v" em `version` (ex.: "v24.21.0").
    tag = alvo["version"] if alvo["version"].startswith("v") else f"v{alvo['version']}"
    base = os.path.join(os.path.expanduser("~"), ".local", "lib", "node",
                        tag.lstrip("v"))
    if os.path.exists(os.path.join(base, "bin", "node")):
        say(f"Node.js {alvo['lts']} ja esta em {base}")
    else:
        url = f"https://nodejs.org/dist/{tag}/node-{tag}-linux-{arch}.tar.xz"
        with tempfile.TemporaryDirectory(prefix="agropilot-") as tmp:
            say(f"baixando Node.js {alvo['lts']} ({tag}) ...")
            pacote = os.path.join(tmp, "node.tar.xz")
            if not _baixar(url, pacote, None):
                raise RuntimeError(f"download falhou: {url}")
            with tarfile.open(pacote) as tf:
                try:
                    tf.extractall(tmp, filter="data")
                except TypeError:
                    tf.extractall(tmp)
            extraido = os.path.join(tmp, f"node-{tag}-linux-{arch}")
            os.makedirs(os.path.dirname(base), exist_ok=True)
            if os.path.exists(base):
                shutil.rmtree(base)
            shutil.move(extraido, base)

    os.makedirs(LOCAL_BIN, exist_ok=True)
    for nome in ("node", "npm", "npx"):
        origem = os.path.join(base, "bin", nome)
        if not os.path.exists(origem):
            continue
        destino = os.path.join(LOCAL_BIN, nome)
        if os.path.islink(destino) or os.path.exists(destino):
            os.remove(destino)
        os.symlink(origem, destino)
    say(f"Node.js {alvo['lts']} instalado; linkado em {LOCAL_BIN}")


def _sem_root(rotulo: str, verificacao, sem_root, motivo: str) -> bool:
    """Ultimo recurso: instala no home do usuario, sem pedir root."""
    if not sem_root:
        aviso(f"nao sei instalar {rotulo} automaticamente: {motivo}")
        if "Tools" in rotulo:
            aviso("  https://www.mongodb.com/try/download/database-tools")
        elif rotulo.lower().startswith("mongosh"):
            aviso("  https://www.mongodb.com/try/download/shell")
        elif rotulo.startswith("MongoDB"):
            aviso("  https://www.mongodb.com/try/download/community")
        elif rotulo.startswith("Node"):
            aviso("  https://nodejs.org/en/download")
        return False
    aviso(f"{motivo}; instalando {rotulo} no seu home (sem root) ...")
    try:
        sem_root()
    except Exception as e:
        erro(f"instalacao de {rotulo} sem root falhou: {e}")
        return False
    return bool(verificacao())


def instalar_sistema(rotulo: str, verificacao, winget_id: str | None = None,
                     linux_cmd: list[str] | None = None,
                     sem_root=None) -> bool:
    """Instala um pacote pelo gerenciador do SO. True se ficou pronto.

    `sem_root` e um callable alternativo, sem root, para instalar no home do
    usuario. Ele so entra quando o gerenciador do SO nao resolve (sem sudo, sem
    pacote, ou AGROPILOT_SEM_ROOT=1).
    """
    if verificacao():
        return True
    ger = como_instalar()
    if ger == "winget" and winget_id:
        say(f"instalando {rotulo} (winget) ...")
        rodar(["winget", "install", "--id", winget_id, "--source", "winget",
               "--accept-package-agreements", "--accept-source-agreements"],
              timeout=900)
        return bool(verificacao())
    if ger == "choco" and winget_id:
        say(f"instalando {rotulo} (choco) ...")
        rodar(["choco", "install", winget_id, "-y"], timeout=900)
        return bool(verificacao())
    if ger and linux_cmd and not sem_root_forcado():
        say(f"instalando {rotulo} ({ger}) — pode pedir senha ...")
        if ger == "apt-get":
            rodar(["sudo", "apt-get", "update", "-qq"], timeout=600)
        r = rodar(["sudo", ger, "install", "-y", *linux_cmd], timeout=1200)
        if ok(r) and verificacao():
            return True
        return _sem_root(rotulo, verificacao, sem_root,
                         "o gerenciador do SO nao deu conta")
    return _sem_root(rotulo, verificacao, sem_root,
                     "sem gerenciador de pacotes para root" if not sem_root_forcado()
                     else "AGROPILOT_SEM_ROOT=1")


def garantir_mongo() -> bool:
    """MongoDB de pe em 27017. Windows usa o servico; Linux, um mongod local."""
    if porta_aberta(27017):
        return True

    if IS_WINDOWS:
        def servico():
            p = rodar(["sc", "query", "MongoDB"])
            return (p.stdout or "") + (p.stderr or "")

        if "MongoDB" not in servico():
            if not instalar_sistema("MongoDB Server",
                                    lambda: "MongoDB" in servico(),
                                    winget_id="MongoDB.Server"):
                return False
        say("iniciando o servico MongoDB ...")
        r = rodar(["net", "start", "MongoDB"])
        if not ok(r) and not porta_aberta(27017):
            aviso("nao consegui iniciar o servico. Se faltar permissao, abra")
            aviso("o PowerShell como Administrador e rode:  net start MongoDB")
    else:
        if not tem("mongod"):
            if not instalar_sistema("MongoDB", lambda: tem("mongod"),
                                    linux_cmd=["mongodb-org"],
                                    sem_root=instalar_mongod_sem_root):
                return False
        say("subindo o mongod ...")
        dbpath = os.path.join(os.path.expanduser("~"), ".agropilot", "mongo-data")
        os.makedirs(dbpath, exist_ok=True)
        # `--fork` nao: sem root o mongod nao pode escrever pid em /var.
        subprocess.Popen(["mongod", "--dbpath", dbpath, "--bind_ip", "127.0.0.1",
                          "--port", "27017", "--quiet"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

    for _ in range(40):
        if porta_aberta(27017):
            say("MongoDB no ar (27017)")
            return True
        time.sleep(1.0)
    erro("MongoDB nao respondeu na porta 27017")
    return False


# ------------------------------------------------------------- venv / front
def garantir_env() -> None:
    """Cria `back/.env` a partir do exemplo, sem sobrescrever o que existe."""
    if os.path.exists(ENV_ALVO):
        return
    if not os.path.exists(ENV_EXEMPLO):
        aviso(f"{ENV_EXEMPLO} ausente; seguindo sem .env (valores padrao)")
        return
    os.makedirs(BACK, exist_ok=True)
    shutil.copyfile(ENV_EXEMPLO, ENV_ALVO)
    say("criei back/.env a partir do .env.example")
    aviso("a IA fica desligada sem OPENROUTER_API_KEY. Para ligar, edite back/.env")


def garantir_venv() -> bool:
    """Cria back/.venv e instala requirements.txt (idempotente)."""
    py = venv_python()
    reqs = os.path.join(BACK, "requirements.txt")

    def tem_deps():
        if not os.path.exists(py):
            return False
        return ok(rodar([py, "-c", "import fastapi, uvicorn, pymongo"]))

    if tem_deps():
        return True
    if not os.path.exists(py):
        base = shutil.which("python3") or shutil.which("python")
        if not base:
            die("python nao encontrado no PATH (instale Python 3.11+)")
        say("criando o ambiente virtual ...")
        r = rodar([base, "-m", "venv", os.path.join(BACK, ".venv")], timeout=300)
        if not os.path.exists(py):
            die(f"falha ao criar o venv: {(r.stderr or '').strip()[:300]}")
    say("instalando as dependencias do backend ...")
    rodar([py, "-m", "pip", "install", "--upgrade", "pip"], timeout=600, cwd=BACK)
    rodar([py, "-m", "pip", "install", "-r", reqs], timeout=1800, cwd=BACK)
    if not tem_deps():
        die(f"venv sem fastapi/uvicorn/pymongo — rode manualmente:\n"
            f"  {py} -m pip install -r {reqs}")
    say("backend pronto (venv + dependencias)")
    return True


def garantir_front() -> bool:
    """npm install em front/ (idempotente)."""
    if not tem("npm"):
        instalar_sistema("Node.js LTS", lambda: tem("npm"),
                         winget_id="OpenJS.NodeJS.LTS",
                         linux_cmd=["nodejs", "npm"],
                         sem_root=instalar_node_sem_root)
    if not tem("npm"):
        die("npm nao encontrado — instale Node.js LTS: https://nodejs.org")
    mods = os.path.join(FRONT, "node_modules")
    if os.path.isdir(mods) and os.listdir(mods):
        return True
    say("instalando as dependencias do front (npm install) ...")
    r = rodar(["npm", "install"], timeout=2400, cwd=FRONT)
    if not os.path.isdir(mods):
        die(f"npm install falhou: {(r.stderr or r.stdout or '').strip()[:400]}")
    say("front pronto (node_modules)")
    return True


# ------------------------------------------------------------------- seed
def sha256(caminho: str) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_manifesto() -> dict:
    try:
        with open(MANIFESTO, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _baixar(url: str, destino: str, token: str | None = None) -> bool:
    """Baixa com progresso simples. True se deu certo."""
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/octet-stream")
    tmp = destino + ".parcial"
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, \
                open(tmp, "wb") as fh:
            total = int(resp.headers.get("Content-Length") or 0)
            lido = 0
            while True:
                bloco = resp.read(262144)
                if not bloco:
                    break
                fh.write(bloco)
                lido += len(bloco)
                if total:
                    print(f"\r    {lido * 100 // total:3d}%  "
                          f"{lido / 1048576:.1f}/{total / 1048576:.1f} MB",
                          end="", flush=True)
        print()
        os.replace(tmp, destino)
        return True
    except Exception as e:
        if os.path.exists(tmp):
            os.remove(tmp)
        aviso(f"falha ao baixar: {e}")
        return False


def contar_documentos(mongosh: str | None) -> int:
    """Total de documentos na base `agropilot` (0 se nao existir, -1 sem mongosh)."""
    if not mongosh:
        return -1
    js = ("try { print('CONTAGEM=' + "
          "db.getSiblingDB('agropilot').stats().objects) } "
          "catch (e) { print('CONTAGEM=0') }")
    saida = rodar([mongosh, "--quiet", MONGO_URL, "--eval", js]).stdout or ""
    for linha in saida.splitlines():
        if linha.startswith("CONTAGEM="):
            try:
                return int(linha.split("=", 1)[1])
            except ValueError:
                return 0
    return 0


def garantir_seed() -> str | None:
    """Garante `seed/agropilot.gz`.

    Ordem: arquivo local, GitHub CLI autenticado, token do env, URL publica.
    O repositorio e PRIVADO: sem autenticacao a resposta e 404, e o erro final
    diz exatamente o que fazer em vez de falhar em silencio.
    """
    if os.path.exists(SEED_ARQ) and os.path.getsize(SEED_ARQ) > 1024:
        return SEED_ARQ
    if os.getenv("AGROPILOT_SKIP_DOWNLOAD") == "1":
        aviso("AGROPILOT_SKIP_DOWNLOAD=1 e nao ha seed local em", SEED_ARQ)
        return None

    os.makedirs(SEED_DIR, exist_ok=True)
    say("baixando a base de dados (seed) ...")

    if tem("gh"):
        say("  tentando via GitHub CLI ...")
        r = rodar(["gh", "release", "download", TAG_RELEASE,
                   "--repo", REPO_GITHUB, "--pattern", "agropilot.gz",
                   "--dir", SEED_DIR, "--clobber"], timeout=900)
        if ok(r) and os.path.exists(SEED_ARQ):
            say("  baixado pela release")
            return SEED_ARQ

    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    url = os.getenv("SEED_URL") or URL_RELEASE
    if token:
        say(f"  tentando com token em {url} ...")
        if _baixar(url, SEED_ARQ, token):
            return SEED_ARQ
    else:
        say(f"  tentando sem token em {url} ...")
        if _baixar(url, SEED_ARQ, None):
            return SEED_ARQ

    erro("nao consegui baixar a base de dados.")
    erro(f"O repositorio {REPO_GITHUB} e privado. Escolha uma:")
    erro(f"  1) ja tem o arquivo: copie para {SEED_ARQ}")
    erro("  2) tem GitHub CLI logado: gh auth login")
    erro('  3) tem um token: export GH_TOKEN=ghp_xxx')
    erro("  4) tem a URL aberta: export SEED_URL=https://.../agropilot.gz")
    return None


def restaurar(force: bool = False) -> bool:
    """Restaura o dump no Mongo. Idempotente: so restaura se estiver vazio."""
    mongorestore = achar_mongo_tool("mongorestore")
    if not mongorestore:
        erro("mongorestore nao encontrado. Instale as MongoDB Database Tools:")
        erro("  winget install --id MongoDB.DatabaseTools")
        erro("  brew install mongodb-database-tools")
        erro("  ou, sem root:  python scripts/agropilot.py setup")
        return False

    mongosh = achar_mongo_tool("mongosh")
    atual = contar_documentos(mongosh)
    if not force and atual > 0:
        say(f"o banco ja tem {atual} documentos; seed ignorado (--force repoe)")
        return True

    arq = garantir_seed()
    if not arq:
        return False

    # Um download pela metade viraria "banco corrompido" horas depois.
    esperado = ler_manifesto().get("sha256")
    if esperado:
        obtido = sha256(arq)
        if obtido != esperado:
            aviso("sha256 do seed difere do manifest.json (pode estar parcial).")
            if not os.getenv("AGROPILOT_IGNORAR_HASH"):
                erro(f"  esperado {esperado[:16]}...  obtido {obtido[:16]}...")
                erro("cancelei. Use AGROPILOT_IGNORAR_HASH=1 para forcar.")
                return False
        else:
            say("seed confere com o manifesto")

    say(f"restaurando {os.path.basename(arq)} (pode demorar) ...")
    # A connection string e o PRIMEIRO ARGUMENTO POSICIONAL: e a unica forma
    # que funciona igual no Windows (que usa `/uri:`) e no Linux (`--uri=`).
    # Sem ela o mongorestore cairia no localhost:27017 padrao e popularia o
    # banco errado em quem aponta AGROPILOT_MONGO para outro lugar.
    # As opcoes usam `--opt=valor`: com espaco, o mongorestore do Windows trata
    # o valor como positional e falha.
    cmd = [mongorestore, MONGO_URL, "--gzip", f"--archive={arq}",
           "--nsInclude=agropilot.*"]
    if force:
        cmd.append("--drop")
    r = rodar(cmd, timeout=1800)
    if not ok(r):
        erro("mongorestore falhou:")
        erro((r.stderr or r.stdout or "").strip()[:600])
        return False
    final = contar_documentos(mongosh)
    if final <= 0:
        aviso("o restore rodou, mas a contagem continua 0")
        return False
    say(f"banco populado: {final} documentos")
    return True


# ---------------------------------------------------------------- processos
def ler_pid(arquivo: str):
    try:
        with open(arquivo) as fh:
            return int(fh.read().strip())
    except Exception:
        return None


def salvar_pid(arquivo: str, pid: int) -> None:
    os.makedirs(TMP, exist_ok=True)
    with open(arquivo, "w") as fh:
        fh.write(str(pid))


def vivo(pid) -> bool:
    if not pid:
        return False
    if IS_WINDOWS:
        r = rodar(["tasklist", "/FI", f"PID eq {pid}", "/NH"])
        return str(pid) in (r.stdout or "")
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _spawn(cmd, cwd, saida, erro_log) -> int:
    """Sobe em background e desacoplado do terminal.

    No Windows usa DETACHED_PROCESS (nao abre janela e nao morre com o
    terminal); no Linux usa start_new_session para sobreviver ao Ctrl+C.
    """
    kwargs = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = 0x08000000 | 0x00000200  # DETACHED + NEW_GROUP
    else:
        kwargs["start_new_session"] = True
    os.makedirs(TMP, exist_ok=True)
    with open(saida, "a", encoding="utf-8") as so, \
            open(erro_log, "a", encoding="utf-8") as se:
        proc = subprocess.Popen(cmd, cwd=cwd, stdout=so, stderr=se, **kwargs)
    return proc.pid


def subir_api() -> None:
    pid = ler_pid(PID_API)
    if vivo(pid):
        say(f"API ja no ar (pid {pid})")
        return
    if url_responde(f"{API_URL}/api/health"):
        aviso(f"ja ha uma API em {API_URL} (fora deste script)")
        return
    say(f"subindo a API em {API_URL} ...")
    pid = _spawn([venv_python(), "-m", "uvicorn", "app.main:app",
                  "--host", "127.0.0.1", "--port", str(PORTA_API)],
                 BACK, LOG_API, LOG_API_ERR)
    salvar_pid(PID_API, pid)
    if aguardar(f"{API_URL}/api/health", 90):
        say("API respondendo em /api/health")
    else:
        aviso(f"API nao respondeu em 90s. Log: {LOG_API_ERR}")


def subir_front() -> None:
    pid = ler_pid(PID_FRONT)
    if vivo(pid):
        say(f"front ja no ar (pid {pid})")
        return
    if url_responde(FRONT_URL):
        aviso(f"ja ha algo em {FRONT_URL} (fora deste script)")
        return
    say(f"subindo o front em {FRONT_URL} (npm run dev) ...")
    # npm e um .cmd no Windows: precisa passar por cmd /c.
    cmd = ["cmd", "/c", "npm", "run", "dev"] if IS_WINDOWS else ["npm", "run", "dev"]
    pid = _spawn(cmd, FRONT, LOG_FRONT, LOG_FRONT_ERR)
    salvar_pid(PID_FRONT, pid)
    if aguardar(FRONT_URL, 180):
        say("front respondendo")
    else:
        aviso(f"front nao respondeu em 180s. Log: {LOG_FRONT}")


def derrubar(rotulo: str, arquivo_pid: str) -> None:
    pid = ler_pid(arquivo_pid)
    if not pid:
        say(f"{rotulo}: nada registrado para parar")
        return
    if not vivo(pid):
        say(f"{rotulo}: processo {pid} ja encerrado")
        return
    say(f"parando {rotulo} (pid {pid}) ...")
    if IS_WINDOWS:
        # /T derruba os filhos (node/npm deixados pelo cmd.exe).
        rodar(["taskkill", "/PID", str(pid), "/T", "/F"])
    else:
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except Exception:
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        time.sleep(1.0)
        if vivo(pid):
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                pass
    try:
        os.remove(arquivo_pid)
    except OSError:
        pass


# --------------------------------------------------------------------- acoes
def status() -> None:
    print()
    say("status")
    print(f"  MongoDB : {'no ar (27017)' if porta_aberta(27017) else 'FORA do ar (27017)'}")
    docs = contar_documentos(achar_mongo_tool("mongosh"))
    print("  banco   : " + (f"{docs} documentos" if docs >= 0 else "mongosh ausente"))
    print(f"  API     : {'no ar' if url_responde(f'{API_URL}/api/health') else 'fora do ar'}"
          f"  {API_URL}/api/health")
    print(f"  front   : {'no ar' if url_responde(FRONT_URL) else 'fora do ar'}  {FRONT_URL}")
    if os.path.exists(SEED_ARQ):
        print(f"  seed    : {os.path.getsize(SEED_ARQ) / 1048576:.1f} MB")
    else:
        print("  seed    : ausente (rode: python scripts/agropilot.py seed)")
    man = ler_manifesto()
    if man:
        print(f"  manifesto: {man.get('total_documentos')} docs, "
              f"gerado em {str(man.get('gerado_em'))[:10]}")
    print()


def doctor() -> int:
    """Lista o que falta. Sai != 0 se algo obrigatorio estiver faltando."""
    print()
    say(f"diagnostico — {platform.system()} {platform.release()} ({platform.machine()})")
    print()
    faltando = []

    def linha(nome, ok_, como="", obrigatorio=True):
        marca = f"{VERDE}OK  {RESET}" if ok_ else f"{VERMELHO}FALTA{RESET}"
        sufixo = como or ("obrigatorio" if obrigatorio else "opcional")
        print(f"  [{marca}] {nome:<24} {sufixo}")
        if not ok_ and obrigatorio:
            faltando.append(nome)

    linha("Python", bool(shutil.which("python3") or shutil.which("python")),
          sys.version.split()[0])
    linha("Node.js / npm", tem("npm"))
    linha("MongoDB (27017)", porta_aberta(27017))
    linha("mongosh", bool(achar_mongo_tool("mongosh")))
    linha("mongorestore", bool(achar_mongo_tool("mongorestore")), "(Database Tools)")
    linha("venv do backend", os.path.exists(venv_python()))
    linha("node_modules do front", os.path.isdir(os.path.join(FRONT, "node_modules")))
    linha("back/.env", os.path.exists(ENV_ALVO))
    linha("seed/agropilot.gz", os.path.exists(SEED_ARQ))
    linha("docker", tem("docker"), "docker compose up", obrigatorio=False)
    linha("GitHub CLI", tem("gh"), "baixar o seed privado", obrigatorio=False)
    if IS_WINDOWS or como_instalar() == "brew":
        print("\n  instalacao: pelo gerenciador do SO")
    elif sudo_sem_senha():
        print("\n  instalacao: gerenciador do SO (root); se faltar pacote, "
              f"cai no home ({LOCAL_BIN})")
    elif tem_sudo():
        print(f"\n  instalacao: gerenciador do SO, pode pedir senha; se negar, "
              f"cai no home ({LOCAL_BIN})")
    else:
        print(f"\n  instalacao: SEM ROOT — tudo vai para {LOCAL_BIN}")
    docs = contar_documentos(achar_mongo_tool("mongosh"))
    print("\n  banco agropilot: " + (f"{docs} documentos" if docs >= 0
                                     else "mongosh ausente"))
    print()
    if faltando:
        aviso("falta: " + ", ".join(faltando))
        say("rode:  python scripts/agropilot.py setup")
        return 1
    say("tudo pronto. Suba com:  python scripts/agropilot.py up")
    return 0


def setup() -> bool:
    say("fase 1: dependencias")
    if not garantir_mongo():
        return False
    if not achar_mongo_tool("mongosh"):
        instalar_sistema("mongosh", lambda: bool(achar_mongo_tool("mongosh")),
                         winget_id="MongoDB.Shell",
                         sem_root=instalar_mongosh_sem_root)
    if not achar_mongo_tool("mongorestore"):
        instalar_sistema("MongoDB Database Tools",
                         lambda: bool(achar_mongo_tool("mongorestore")),
                         winget_id="MongoDB.DatabaseTools",
                         linux_cmd=["mongodb-database-tools"],
                         sem_root=instalar_dbt_sem_root)
    garantir_env()
    garantir_venv()
    garantir_front()
    say("fase 2: base de dados")
    return restaurar(force=False)


def logs(seguir: bool) -> None:
    """Ultimas linhas dos logs, ou acompanhamento em tempo real."""
    arquivos = [(LOG_API, "api"), (LOG_FRONT, "front"),
                (LOG_API_ERR, "api.err"), (LOG_FRONT_ERR, "front.err")]
    if not seguir:
        for caminho, nome in arquivos:
            if not os.path.exists(caminho):
                continue
            say(f"--- {nome} (ultimas 15 linhas) ---")
            with open(caminho, encoding="utf-8", errors="replace") as fh:
                for l in fh.readlines()[-15:]:
                    print("   ", l.rstrip())
            print()
        return
    say("acompanhando logs (Ctrl+C para sair) ...")
    handles = []
    try:
        for caminho, nome in arquivos:
            if not os.path.exists(caminho):
                continue
            fh = open(caminho, encoding="utf-8", errors="replace")
            fh.seek(0, os.SEEK_END)
            handles.append((fh, nome))
        while True:
            mudou = False
            for fh, nome in handles:
                linha = fh.readline()
                if linha:
                    mudou = True
                    print(f"[{nome}] {linha.rstrip()}")
            if not mudou:
                time.sleep(0.4)
    except KeyboardInterrupt:
        print()
    finally:
        for fh, _ in handles:
            try:
                fh.close()
            except Exception:
                pass


def resumo_final() -> None:
    print()
    say("pronto")
    print(f"  front     : {FRONT_URL}")
    print(f"  swagger   : {API_URL}/docs")
    print(f"  health    : {API_URL}/api/health")
    print()
    print(f"  logs api  : {LOG_API}")
    print(f"  logs front: {LOG_FRONT}")
    print("  parar     : python scripts/agropilot.py down")
    print("  ver estado: python scripts/agropilot.py status")
    print()


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="agropilot",
        description="Instala, popula e roda o AgroPilot (Windows e Linux).")
    ap.add_argument("comando", nargs="?", default="tudo",
                    choices=["doctor", "setup", "up", "down", "status",
                             "seed", "logs", "tudo"],
                    help="acao (padrao: tudo = setup + up)")
    ap.add_argument("--force", action="store_true",
                    help="com seed: re-restaurar mesmo com o banco cheio")
    ap.add_argument("-f", "--seguir", action="store_true",
                    help="com logs: acompanhar em tempo real")
    args = ap.parse_args()
    print()

    cmd = args.comando
    if cmd == "doctor":
        return doctor()
    if cmd == "status":
        status()
        return 0
    if cmd == "down":
        derrubar("API", PID_API)
        derrubar("front", PID_FRONT)
        say("o MongoDB continua no ar (o banco nao se perde ao parar)")
        return 0
    if cmd == "seed":
        return 0 if restaurar(force=args.force) else 1
    if cmd == "logs":
        logs(args.seguir)
        return 0
    if cmd == "setup":
        return 0 if setup() else 1
    if cmd == "up":
        subir_api()
        subir_front()
        resumo_final()
        return 0

    # "tudo": o caminho do primeiro uso.
    say(" AgroPilot — preparando tudo (1a vez)")
    if not setup():
        return 1
    say("subindo a aplicacao")
    subir_api()
    subir_front()
    resumo_final()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())