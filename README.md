# Тестовая СПА продажа — продажа подарочных сертификатов

Демо-сервис: пул номеров, резерв при заказе, оплата (mock / ЮKassa), PDF на email, админка.

Репозиторий: https://github.com/ipeffer/sert_lending

## Тестовая MVP-сборка (отправить тестировщику)

```bash
git clone https://github.com/ipeffer/sert_lending.git
cd sert_lending
make test-up
```

Откройте **http://localhost:3000** — подробный сценарий в **[TESTING.md](TESTING.md)**.

Учётка админки: `admin` / `K8test-2026` (из `.env.test`).

## Быстрый старт (разработка)

```bash
cp .env.example .env
# отредактируйте пароли

docker compose up -d --build
# или без Docker:
./scripts/dev.sh
```

- Витрина: http://localhost:3000
- API: http://localhost:8000/health
- Админка UI: http://localhost:3000/admin (запросит Basic Auth)
- Импорт примеров: см. ниже

### Импорт тестовых сертификатов

```bash
curl -u admin:change-me-admin -F file=@samples/certificates.sample.csv \
  http://localhost:8000/admin/import
```

### Тестовая покупка (mock)

1. Откройте http://localhost:3000
2. Заполните форму → «Перейти к оплате»
3. Mock оплата вызовет webhook и отправит PDF (если настроен SMTP)

## Документация

- [Подключение Tilda / iframe](docs/integration-tilda.md)
- [Формат CSV](docs/csv-format.md)
- [Платёжка и чек](docs/payment-setup.md)
- [Caddy для cert.k8.ru](infra/caddy/Caddyfile.example)

## Разработка без Docker

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export DATABASE_URL=postgresql+asyncpg://k8cert:change-me@localhost:5432/k8certificates
uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

## Безопасность

- Публичный API **не** отдаёт списки кодов
- Админка: HTTP Basic + опционально `ADMIN_IP_ALLOWLIST`
- Полная выгрузка CSV только с заголовком `X-Export-Full: 1` (логируется)
