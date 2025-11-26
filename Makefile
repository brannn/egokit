.PHONY: help lint audit test test-fast test-cov clean install install-dev sync

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

sync:  ## Sync dependencies with UV (install all dev dependencies)
	uv sync --dev

install:  ## Install package in production mode (using UV)
	uv sync --no-dev

install-dev:  ## Install package with development dependencies (using UV)
	uv sync --dev

audit:  ## Run Ruff for code auditing (check-only, no fixes)
	@echo "Running Ruff audit (no auto-fixes)..."
	uv run ruff check src/ tests/ --no-fix --output-format=full
	@echo "Running Ruff format check (no changes)..."
	uv run ruff format src/ tests/ --check --diff

lint:  ## Run all linting checks (Ruff, mypy, black check)
	@echo "Running Ruff checks..."
	uv run ruff check src/ tests/ --no-fix
	@echo "Running Black format check..."
	uv run black --check src/ tests/
	@echo "Running isort check..."
	uv run isort --check-only src/ tests/
	@echo "Running mypy..."
	uv run mypy src/

test:  ## Run all tests with coverage
	uv run pytest tests/ -v --cov=egokit --cov-report=term-missing

test-fast:  ## Run tests without coverage
	uv run pytest tests/ -v

test-cov:  ## Run tests and generate HTML coverage report
	uv run pytest tests/ -v --cov=egokit --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

clean:  ## Clean up generated files and caches
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/ .venv/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Convenience aliases
check: audit  ## Alias for audit
qa: lint test  ## Run all quality checks (lint + test)