#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

# shellcheck disable=SC1091
set -a && source .env && set +a

if command -v docker &>/dev/null; then
  docker compose up -d postgres
  echo "Waiting for postgres..."
  sleep 3
fi

cd backend
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -e ".[dev]"
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://k8cert:change-me@localhost:5432/k8certificates}"

.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
NEXT_PUBLIC_API_URL="${API_BASE_URL:-http://localhost:8000}" npm run dev &
WEB_PID=$!

echo "API: http://localhost:8000  (pid $API_PID)"
echo "Web: http://localhost:3000  (pid $WEB_PID)"
echo "Import sample: make import-sample"
trap "kill $API_PID $WEB_PID 2>/dev/null" EXIT
wait
