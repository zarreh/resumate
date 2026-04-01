.PHONY: help up down build restart logs logs-backend logs-frontend logs-db \
       ps clean clean-volumes \
       backend-shell db-shell frontend-shell \
       migrate migrate-create \
       backend-test backend-lint backend-format backend-typecheck \
       frontend-lint frontend-build \
       dev dev-backend dev-frontend

COMPOSE = docker compose

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Docker Compose
# ---------------------------------------------------------------------------

up: ## Start all services in detached mode
	$(COMPOSE) up -d

down: ## Stop all services
	$(COMPOSE) down

build: ## Build all images
	$(COMPOSE) build

rebuild: ## Rebuild and restart all services (no cache)
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

restart: ## Restart all services
	$(COMPOSE) restart

ps: ## Show running containers
	$(COMPOSE) ps

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

logs-backend: ## Tail backend logs
	$(COMPOSE) logs -f backend

logs-frontend: ## Tail frontend logs
	$(COMPOSE) logs -f frontend

logs-db: ## Tail postgres logs
	$(COMPOSE) logs -f postgres

clean: ## Stop services and remove containers/networks
	$(COMPOSE) down --remove-orphans

clean-volumes: ## Stop services and remove volumes (deletes DB data!)
	$(COMPOSE) down -v --remove-orphans

# ---------------------------------------------------------------------------
# Shell access
# ---------------------------------------------------------------------------

backend-shell: ## Open a shell in the backend container
	$(COMPOSE) exec backend bash

db-shell: ## Open psql in the postgres container
	$(COMPOSE) exec postgres psql -U resumate -d resumate

frontend-shell: ## Open a shell in the frontend container
	$(COMPOSE) exec frontend sh

# ---------------------------------------------------------------------------
# Backend (runs inside container)
# ---------------------------------------------------------------------------

migrate: ## Run database migrations
	$(COMPOSE) exec backend alembic upgrade head

migrate-create: ## Create a new migration (usage: make migrate-create message="add users table")
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(message)"

backend-test: ## Run backend tests
	$(COMPOSE) exec backend pytest --cov=src --cov-report=term-missing

backend-lint: ## Lint backend code
	$(COMPOSE) exec backend ruff check src tests

backend-format: ## Format backend code
	$(COMPOSE) exec backend ruff format src tests

backend-typecheck: ## Run mypy on backend
	$(COMPOSE) exec backend mypy src

# ---------------------------------------------------------------------------
# Frontend (runs inside container)
# ---------------------------------------------------------------------------

frontend-lint: ## Lint frontend code
	$(COMPOSE) exec frontend npx eslint

frontend-build: ## Build frontend for production
	$(COMPOSE) exec frontend npm run build

# ---------------------------------------------------------------------------
# Local dev (without Docker)
# ---------------------------------------------------------------------------

dev: ## Start backend and frontend locally (requires tmux or two terminals)
	@echo "Run 'make dev-backend' and 'make dev-frontend' in separate terminals"

dev-backend: ## Start backend locally with hot reload
	cd backend && poetry run uvicorn src.main:app --reload --port 8000

dev-frontend: ## Start frontend locally with hot reload
	cd frontend && npm run dev
