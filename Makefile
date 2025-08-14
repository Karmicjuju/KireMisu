# KireMisu Development Makefile
# Provides commands for testing, coverage, and development workflows

.PHONY: help test test-coverage-unit test-coverage-integration test-coverage-api test-coverage-security test-coverage-all test-coverage-compare clean

# Default target
help:
	@echo "KireMisu Development Commands"
	@echo ""
	@echo "Testing and Coverage:"
	@echo "  test                     - Run all tests"
	@echo "  test-coverage-unit       - Run unit tests with coverage → htmlcov/unit/"
	@echo "  test-coverage-integration - Run integration tests with coverage → htmlcov/integration/"
	@echo "  test-coverage-api        - Run API tests with coverage → htmlcov/api/"
	@echo "  test-coverage-security   - Run security tests with coverage → htmlcov/security/"
	@echo "  test-coverage-all        - Run all tests with coverage → htmlcov/combined/"
	@echo "  test-coverage-compare    - Generate comparison report → htmlcov/comparison/"
	@echo ""
	@echo "Cleanup:"
	@echo "  clean                    - Clean coverage reports and build artifacts"
	@echo ""

# Environment variables for development testing
export SECRET_KEY ?= kiremisu-dev-secret-key-12345-very-long-key-for-testing-purposes
export DATABASE_URL ?= postgresql://kiremisu:kiremisu@localhost:5432/kiremisu_dev

# Run all tests
test:
	uv run pytest

# Unit tests coverage
test-coverage-unit:
	@echo "Running unit tests with coverage..."
	COVERAGE_CONTEXT=unit uv run pytest -m "unit" --cov=kiremisu --cov-report=html --cov-report=term-missing
	@echo "Unit test coverage report generated in htmlcov/unit/"

# Integration tests coverage  
test-coverage-integration:
	@echo "Running integration tests with coverage..."
	COVERAGE_CONTEXT=integration uv run pytest -m "integration" --cov=kiremisu --cov-report=html --cov-report=term-missing
	@echo "Integration test coverage report generated in htmlcov/integration/"

# API tests coverage
test-coverage-api:
	@echo "Running API tests with coverage..."
	COVERAGE_CONTEXT=api uv run pytest -m "api" --cov=kiremisu --cov-report=html --cov-report=term-missing
	@echo "API test coverage report generated in htmlcov/api/"

# Security tests coverage
test-coverage-security:
	@echo "Running security tests with coverage..."  
	COVERAGE_CONTEXT=security uv run pytest -m "security" --cov=kiremisu --cov-report=html --cov-report=term-missing
	@echo "Security test coverage report generated in htmlcov/security/"

# All tests coverage (existing behavior)
test-coverage-all:
	@echo "Running all tests with coverage..."
	COVERAGE_CONTEXT=combined uv run pytest --cov=kiremisu --cov-report=html --cov-report=term-missing
	@echo "Combined test coverage report generated in htmlcov/combined/"

# Generate comparison report (depends on having some coverage data)
test-coverage-compare:
	@echo "Generating coverage comparison report..."
	@mkdir -p htmlcov/comparison
	@echo "Checking for coverage dependencies..."
	@if ! command -v python3 >/dev/null 2>&1; then \
		echo "Error: Python 3 not found. Please install Python 3."; \
		exit 1; \
	fi
	@if ! python3 -c "import coverage" >/dev/null 2>&1; then \
		echo "Error: coverage package not found. Please install with: pip install coverage"; \
		exit 1; \
	fi
	@if ! ls .coverage.* >/dev/null 2>&1; then \
		echo "Error: No coverage files found. Please run one of the following first:"; \
		echo "  make test-coverage-unit"; \
		echo "  make test-coverage-integration"; \
		echo "  make test-coverage-api"; \
		echo "  make test-coverage-security"; \
		echo "  make test-coverage-all"; \
		exit 1; \
	fi
	python3 scripts/compare_coverage.py
	@echo "Coverage comparison report generated in htmlcov/comparison/"

# Clean coverage reports and build artifacts
clean:
	@echo "Cleaning coverage reports and build artifacts..."
	rm -rf htmlcov/
	rm -rf .coverage*
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleanup complete"