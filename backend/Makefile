# Makefile for CISO Assistant DDD Development

.PHONY: help install test test-ddd test-coverage migrate clean lint format type-check setup-dev

help:
	@echo "Available commands:"
	@echo "  make install          - Install dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-ddd         - Run DDD infrastructure tests"
	@echo "  make test-coverage    - Run tests with coverage"
	@echo "  make migrate          - Run database migrations"
	@echo "  make clean            - Clean temporary files"
	@echo "  make lint             - Run linters"
	@echo "  make format           - Format code"
	@echo "  make type-check       - Run type checker"
	@echo "  make setup-dev        - Set up development environment"

install:
	poetry install

test:
	poetry run pytest -v

test-ddd:
	poetry run pytest core/domain/tests/ -c pytest_ddd.ini -v

test-coverage:
	poetry run pytest core/domain/tests/ -c pytest_ddd.ini --cov=core.domain --cov-report=term-missing --cov-report=html

migrate:
	poetry run python manage.py migrate
	poetry run python manage.py migrate core.domain

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name "htmlcov" -exec rm -r {} +
	rm -f .coverage coverage.xml junit.xml

lint:
	poetry run ruff check .
	poetry run mypy core/domain --config-file mypy.ini

format:
	poetry run ruff format .
	poetry run black core/domain

type-check:
	poetry run mypy core/domain --config-file mypy.ini

setup-dev:
	@echo "Setting up development environment..."
	poetry install
	poetry run python manage.py migrate
	poetry run python manage.py migrate core.domain
	@echo "Development environment ready!"

verify-phase0:
	@echo "Verifying Phase 0 completion..."
	@echo "Running DDD tests..."
	poetry run pytest core/domain/tests/ -c pytest_ddd.ini -v
	@echo "Checking migrations..."
	poetry run python manage.py showmigrations core.domain
	@echo "Phase 0 verification complete!"

