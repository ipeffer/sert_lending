.PHONY: up down logs seed import-sample test test-up test-down

up:
	docker compose up -d --build

test-up:
	cp -n .env.test .env 2>/dev/null || true
	./scripts/start-test.sh

test-down:
	docker compose down

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

import-sample:
	curl -s -u "$${ADMIN_USERNAME:-admin}:$${ADMIN_PASSWORD:-change-me-admin}" \
		-F file=@samples/certificates.sample.csv \
		http://localhost:8000/admin/import

test:
	cd backend && pip install -e ".[dev]" && pytest -q
