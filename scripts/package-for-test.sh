#!/usr/bin/env bash
# Архив для отправки тестировщику (без node_modules, .venv, .next)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NAME="test-spa-sales-mvp"
OUT="${ROOT}/../${NAME}.tar.gz"

cd "$ROOT/.."
tar czf "$OUT" \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='.env' \
  --exclude='pg_data' \
  -C "$(dirname "$ROOT")" "$(basename "$ROOT")"

echo "Архив: $OUT"
echo "Тестировщику: распаковать, cp .env.test .env, make test-up, см. TESTING.md"
