.PHONY: dev-up dev-down lint test format install clean help

# Default target
help: ## Show this help message
	@echo "Agential Researcher Makefile"
	@echo ""
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@awk -F ':.*## ' '/^[a-zA-Z0-9%\\._-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(word 1,$(MAKEFILE_LIST))

# Development environment
dev-up: ## Start development environment with docker-compose
	docker-compose up -d

dev-down: ## Stop development environment
	docker-compose down

dev-logs: ## Show logs from all services
	docker-compose logs -f

# Code quality
lint: ## Run linters
	docker-compose exec api ruff check src tests
	docker-compose exec api mypy src
	docker-compose exec api black --check src tests

format: ## Format code
	docker-compose exec api black src tests
	docker-compose exec api ruff check --fix src tests

# Testing
test: ## Run tests
	docker-compose exec api pytest tests/

test-cov: ## Run tests with coverage
	docker-compose exec api pytest tests/ --cov=src --cov-report=html

# Installation and setup
install: ## Install dependencies (run inside container)
	docker-compose exec api pip install -e .

deps-update: ## Update dependencies
	docker-compose exec api pip install --upgrade pip setuptools wheel
	docker-compose exec api pip install -e .

# Database
db-bootstrap: ## Bootstrap the database
	docker-compose exec api python bootstrap_db.py

db-shell: ## Open SQLite shell
	docker-compose exec api sqlite3 data/agential_researcher.db

# Services management
service-api: ## Start only the API service
	docker-compose up api

service-workers: ## Start only the worker services
	docker-compose up worker-hot worker-vlm-ocr worker-backfill

# Clean up
clean: ## Remove containers, networks, and volumes
	docker-compose down -v

clean-db: ## Remove database volumes only
	docker volume rm agential-researcher_sqlite_data agential-researcher_lancedb_data || true

# Utilities
shell-api: ## Open shell in API container
	docker-compose exec api bash

shell-worker: ## Open shell in worker container
	docker-compose exec worker-hot bash