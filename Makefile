.PHONY: help lint audit test test-fast test-cov clean install install-dev sync build publish release tag tag-push

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
	rm -rf build/ dist/ *.egg-info .coverage htmlcov/ .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

build: clean  ## Build source and wheel distributions
	uv build --no-sources
	@echo "Built packages in dist/"
	@ls -la dist/

publish:  ## Publish to PyPI (requires UV_PUBLISH_TOKEN env var)
	@if [ -z "$$UV_PUBLISH_TOKEN" ]; then \
		echo "Error: UV_PUBLISH_TOKEN environment variable not set"; \
		echo "Get a token from https://pypi.org/manage/account/token/"; \
		exit 1; \
	fi
	uv publish

publish-test:  ## Publish to TestPyPI (requires UV_PUBLISH_TOKEN env var)
	@if [ -z "$$UV_PUBLISH_TOKEN" ]; then \
		echo "Error: UV_PUBLISH_TOKEN environment variable not set"; \
		echo "Get a token from https://test.pypi.org/manage/account/token/"; \
		exit 1; \
	fi
	uv publish --publish-url https://test.pypi.org/legacy/

release: test build publish tag  ## Run tests, build, publish to PyPI, and tag
	@echo "Released version $$(uv version --short)"

tag:  ## Create and push git tag for current version
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'); \
	echo "Creating tag v$$VERSION..."; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	echo "Tag v$$VERSION created. Push with: git push origin v$$VERSION"

tag-push:  ## Push the latest version tag to origin
	@VERSION=$$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/'); \
	git push origin "v$$VERSION"

version:  ## Show current version
	@uv version

version-bump-patch:  ## Bump patch version (0.0.X)
	uv version --bump patch

version-bump-minor:  ## Bump minor version (0.X.0)
	uv version --bump minor

version-bump-major:  ## Bump major version (X.0.0)
	uv version --bump major

# Convenience aliases
check: audit  ## Alias for audit
qa: lint test  ## Run all quality checks (lint + test)