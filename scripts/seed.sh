#!/usr/bin/env bash
# Restaura o dump do Mongo `agropilot` a partir do GitHub Release.
# Uso:
#   ./scripts/seed.sh              # restaura somente se `agropilot` estiver vazio
#   ./scripts/seed.sh --force      # re-restaura com --drop
#   SEED_URL=<url> ./scripts/seed.sh
set -euo pipefail

SEED_URL="${SEED_URL:-https://github.com/Thomaskynol/hackaton-dados-abertos-sql-injection/releases/download/dados-v1/agropilot.gz}"
FILE="seed/agropilot.gz"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

mkdir -p seed
if [ ! -s "$FILE" ]; then
  echo "Downloading $SEED_URL -> $FILE"
  curl -fL -o "$FILE" "$SEED_URL"
fi

COUNT="$(docker exec agropilot-mongo mongosh --quiet --eval 'try { print(db.getSiblingDB("agropilot").stats().objects) } catch (e) { print(0) }' | tr -cd '0-9')"
COUNT="${COUNT:-0}"

if [ "$FORCE" -eq 0 ] && [ "$COUNT" -gt 0 ]; then
  echo "SKIP: agropilot already has $COUNT objects; use --force to re-restore"
  exit 0
fi

# ponytail: copia via docker cp em vez de montar volume — script roda no host
docker cp "$FILE" agropilot-mongo:/tmp/agropilot-seed.gz
if [ "$FORCE" -eq 1 ]; then
  docker exec agropilot-mongo mongorestore --gzip --archive=/tmp/agropilot-seed.gz --drop
else
  docker exec agropilot-mongo mongorestore --gzip --archive=/tmp/agropilot-seed.gz
fi
echo "RESTORED agropilot from $FILE"
