#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  cp .env.test .env
  echo "Создан .env из .env.test"
fi

if ! command -v docker &>/dev/null; then
  echo "Ошибка: нужен Docker. Установите Docker Desktop."
  exit 1
fi

echo "Сборка и запуск (может занять несколько минут)..."
docker compose up -d --build

echo "Ожидание API..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

if ! curl -sf http://localhost:8000/health >/dev/null; then
  echo "API не ответил. Логи: docker compose logs api"
  exit 1
fi

echo ""
echo "=========================================="
echo "  Тестовая СПА продажа — стенд готов"
echo "=========================================="
echo "  Витрина:  http://localhost:3000"
echo "  Админка:  http://localhost:3000/admin"
echo "            логин admin / пароль K8test-2026"
echo "  API:      http://localhost:8000/docs"
echo ""
echo "  Инструкция: см. TESTING.md"
echo "=========================================="
