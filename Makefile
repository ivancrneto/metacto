.PHONY: help install api web fmt lint typecheck check test cov build docker-build docker-run deploy clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}'

install: ## Install backend (uv) + frontend (npm) dependencies
	uv sync
	cd frontend && npm install

api: ## Run the FastAPI dev server on :8000 (auto-reload)
	uv run uvicorn app.main:app --reload --app-dir backend --port 8000

web: ## Run the Vite dev server on :5173 (proxies /api -> :8000)
	cd frontend && npm run dev

fmt: ## Auto-format and auto-fix (ruff)
	uv run ruff format backend
	uv run ruff check --fix backend

lint: ## Lint without modifying files (ruff)
	uv run ruff check backend
	uv run ruff format --check backend

typecheck: ## Static type-check (mypy, strict)
	uv run mypy

check: lint typecheck ## Run all static checks

test: ## Run the test suite (pytest)
	uv run pytest

cov: ## Run tests with a coverage report
	uv run pytest --cov=app --cov-report=term-missing

build: ## Build the frontend for production (-> frontend/dist)
	cd frontend && npm run build

docker-build: ## Build the production Docker image
	docker build -t feature-request-board .

docker-run: ## Run the production image on :8000
	docker run --rm -e APP_SECRET_KEY=local-docker-secret -p 8000:8000 feature-request-board

deploy: ## Deploy to Fly.io (requires an authenticated flyctl)
	flyctl deploy

clean: ## Remove caches, build output, and the local SQLite DB
	rm -rf .pytest_cache .mypy_cache .ruff_cache frontend/dist app.db
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
