# Everything CI runs, runnable locally. `make test` = all layers except e2e; `make e2e` needs Docker.
.PHONY: test backend-check backend-test api-client api-check frontend-install frontend-check frontend-test build image e2e

test: backend-check backend-test api-check frontend-check frontend-test

backend-check:
	uv run ruff check src tests scripts
	uv run ruff format --check src tests scripts
	uv run pyright

backend-test:
	uv run pytest --cov

# regenerate openapi.json + the frontend's typed client after changing the API
api-client:
	uv run python scripts/export_openapi.py openapi.json
	cd frontend && npm run -s api:generate

# fails when the committed client doesn't match the backend (someone changed the API without regenerating)
api-check: api-client
	git diff --exit-code -- openapi.json frontend/src/lib/api/schema.d.ts

frontend-install:
	cd frontend && npm ci --no-fund --no-audit

frontend-check:
	cd frontend && npm run -s check

frontend-test:
	cd frontend && npm run -s test

build:
	cd frontend && npm run -s build

image:
	docker build -t language-maxxer:dev .

# end-to-end: the real image, fresh data, a real browser
e2e: image
	-docker rm -f lmx-e2e >/dev/null 2>&1
	docker run -d --name lmx-e2e -p 8011:8000 language-maxxer:dev
	for i in $$(seq 60); do curl -sf http://127.0.0.1:8011/api/health >/dev/null && break; sleep 1; done
	cd frontend && LMX_URL=http://127.0.0.1:8011 npx playwright test; status=$$?; docker rm -f lmx-e2e >/dev/null; exit $$status
