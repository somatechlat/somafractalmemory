.PHONY: setup test lint api cli clean uv-install lock \
	db-upgrade db-current db-revision \
	help prereqs prereqs-docker \
    compose-build compose-up compose-down compose-down-v compose-logs compose-ps compose-restart compose-health \
	helm-install-local-dev helm-uninstall-local-dev \
	helm-install-prod-ha helm-uninstall-prod-ha

# Variables
API_PORT ?= 9595

help: ## Show this help
	@echo "Available targets:" && \
	awk 'BEGIN {FS = ":.*##"; printf "\n"} /^[a-zA-Z0-9_.-]+:.*?##/ { printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort

prereqs: prereqs-docker ## Check that required tools are installed

prereqs-docker: ## Check docker and docker compose
	@command -v docker >/dev/null 2>&1 || { echo "Error: docker not found in PATH"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "Error: docker compose not available"; exit 1; }
	@command -v curl >/dev/null 2>&1 || { echo "Error: curl not found in PATH"; exit 1; }

test-e2e: compose-health ## Run a simple end-to-end test against the running services
	@echo "→ [E2E] Running end-to-end test..."
	@API_URL="http://127.0.0.1:$(API_PORT)"; \
	SOMA_TOKEN=$$(grep SOMA_API_TOKEN .env | cut -d '=' -f2); \
	TEST_COORD="999.99,888.88"; \
	\
	echo "  - Storing a new memory at coord ($$TEST_COORD)..."; \
	STORE_RESPONSE=$$(curl -s -X POST $$API_URL/memories \
	  -H "Content-Type: application/json" \
	  -H "Authorization: Bearer $$SOMA_TOKEN" \
	  -d "{\"coord\": \"$$TEST_COORD\", \"payload\": {\"test_id\": \"e2e-test-$$RANDOM\", \"data\": \"This is a test memory.\"}}"); \
	echo "    Response: $$STORE_RESPONSE"; \
	if ! echo "$$STORE_RESPONSE" | grep -q '"ok":true'; then \
		echo "  ✗ [FAIL] Failed to store memory."; exit 1; \
	fi; \
	\
	echo "  - Retrieving the memory..."; \
	RETRIEVE_RESPONSE=$$(curl -s -X GET $$API_URL/memories/$$TEST_COORD \
	  -H "Authorization: Bearer $$SOMA_TOKEN"); \
	if ! echo "$$RETRIEVE_RESPONSE" | grep -q '"test_id"'; then \
		echo "  ✗ [FAIL] Failed to retrieve memory."; exit 1; \
	fi; \
	echo "    Successfully retrieved memory."; \
	\
	echo "  - Verifying infrastructure stats..."; \
	STATS_RESPONSE=$$(curl -s -X GET $$API_URL/stats \
	  -H "Authorization: Bearer $$SOMA_TOKEN"); \
	TOTAL_MEM=$$(echo $$STATS_RESPONSE | sed -n 's/.*"total_memories":\([0-9]*\).*/\1/p'); \
	if [ -z "$$TOTAL_MEM" ] || [ $$TOTAL_MEM -lt 1 ]; then \
		echo "  ✗ [FAIL] Total memory count in stats is not greater than 0."; exit 1; \
	fi; \
	echo "    Stats check passed. Total memories: $$TOTAL_MEM."; \
	\
	echo "✓ [SUCCESS] End-to-end test completed successfully."

compose-up: prereqs-docker ## Start the full stack in the background
	docker compose --profile core --profile consumer up -d
	@echo "→ API will be available at: http://127.0.0.1:$(API_PORT)"

ci-verify: prereqs-docker ## CI-style verify with Compose: up, health check, and tear down
	$(MAKE) -s compose-up
	$(MAKE) -s compose-health
	$(MAKE) -s compose-down

uv-install:
	@which uv >/dev/null 2>&1 || (curl -LsSf https://astral.sh/uv/install.sh | sh -s -- -y)
	@~/.local/bin/uv --version

setup: uv-install
	~/.local/bin/uv sync --extra api --extra events --extra dev

lock: uv-install
	~/.local/bin/uv lock

test:
	~/.local/bin/uv run pytest -q

lint:
	~/.local/bin/uv run mypy somafractalmemory

api:
	~/.local/bin/uv run uvicorn somafractalmemory.http_api:app --reload

cli:
	~/.local/bin/uv run soma -h

db-upgrade: ## Run Alembic migrations
	~/.local/bin/uv run alembic upgrade head

db-current: ## Show current Alembic revision
	~/.local/bin/uv run alembic current

db-revision: ## Generate a new Alembic migration
	@MSG=$${MSG:-"describe change"}; \
	~/.local/bin/uv run alembic revision -m "$$MSG"

clean:
	rm -rf .pytest_cache __pycache__ somafractalmemory.egg-info qdrant.db *.index audit_log.jsonl .ipynb_checkpoints

# ==============================================================================
# Docker Compose Workflows (for local development)
# ==============================================================================

compose-build: prereqs-docker ## Build images for Docker Compose
	docker compose build --progress=plain

compose-up: prereqs-docker ## Start the full stack in the background
	docker compose --profile core --profile consumer up -d
	@echo "→ API will be available at: http://127.0.0.1:$(API_PORT)"

compose-logs: prereqs-docker ## Tail API logs
	docker compose logs -f --tail=200 api

compose-ps: prereqs-docker ## Show container status
	docker compose ps

compose-restart: prereqs-docker ## Restart the API service
	docker compose restart api

compose-health: prereqs-docker ## Wait for API /healthz to return 200
	@echo "Waiting for API health at http://127.0.0.1:$(API_PORT)/healthz ..."; \
	for i in $$(seq 1 60); do \
	  if curl -fsS http://127.0.0.1:$(API_PORT)/healthz >/dev/null; then echo "✓ API healthy"; exit 0; fi; \
	  sleep 2; \
	done; \
	echo "✗ API did not become healthy in time"; exit 1

compose-down: prereqs-docker ## Stop all services (keep volumes)
	docker compose down

compose-down-v: prereqs-docker ## Stop all services and remove volumes (DANGEROUS)
	docker compose down -v

# ==============================================================================
# Kubernetes Workflows (via Helm)
# ==============================================================================

helm-install-local-dev: ## Install the Helm chart with local development values
	helm upgrade --install somafractalmemory-local-dev ./helm -f ./helm/values-local-dev.yaml --create-namespace -n somafractalmemory-local-dev

helm-uninstall-local-dev: ## Uninstall the local development Helm release
	helm uninstall somafractalmemory-local-dev -n somafractalmemory-local-dev

helm-install-prod-ha: ## Install the Helm chart with production HA values
	helm upgrade --install somafractalmemory-prod-ha ./helm -f ./helm/values-prod-ha.yaml --create-namespace -n somafractalmemory-prod-ha

helm-uninstall-prod-ha: ## Uninstall the production HA Helm release
	helm uninstall somafractalmemory-prod-ha -n somafractalmemory-prod-ha
