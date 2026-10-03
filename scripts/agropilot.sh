#!/usr/bin/env bash
# Atalho Linux/macOS para o CLI cross-platform (scripts/agropilot.py).
#
#   ./scripts/agropilot.sh            # setup + up (primeiro uso)
#   ./scripts/agropilot.sh doctor     # o que falta na maquina
#   ./scripts/agropilot.sh down       # derruba API e front
#   ./scripts/agropilot.sh seed --force
#
# Este arquivo so acha o interpretador certo e repassa o comando; toda a logica
# esta em scripts/agropilot.py, compartilhada com o Windows.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        if "$cand" -c 'import sys; sys.exit(0 if sys.version_info[0] >= 3 else 1)' 2>/dev/null; then
            PY="$cand"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo "[agropilot] ERRO: Python 3.11+ nao encontrado no PATH." >&2
    echo "  Ubuntu/Debian: sudo apt install -y python3 python3-venv"
    echo "  Fedora/RHEL  : sudo dnf install -y python3"
    echo "  macOS        : brew install python"
    exit 1
fi

exec "$PY" "$DIR/agropilot.py" "$@"