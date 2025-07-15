.PHONY: help install test lint format type-check build clean docs

help:
	@echo "Available commands:"
	@echo "  install      Install package in development mode"
	@echo "  test         Run test suite"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black"
	@echo "  type-check   Run type checking with mypy"
	@echo "  build        Build package for distribution"
	@echo "  clean        Clean build artifacts"
	@echo "  docs         Build documentation"
	@echo "  publish      Publish to PyPI (requires API token)"

install:
	pip install -e .[dev]

test:
	pytest

test-verbose:
	pytest -v --tb=long

test-coverage:
	pytest --cov=appstore_connect --cov-report=html --cov-report=term

lint:
	flake8 appstore_connect tests examples
	black --check appstore_connect tests examples

format:
	black appstore_connect tests examples

type-check:
	mypy appstore_connect

build:
	python -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:
	@echo "Documentation is in markdown format in docs/ directory"
	@echo "For HTML docs, install sphinx and run:"
	@echo "  pip install sphinx sphinx-rtd-theme"
	@echo "  sphinx-build -b html docs docs/_build"

publish:
	@echo "Building package..."
	python -m build
	@echo "Publishing to PyPI..."
	python -m twine upload dist/*

publish-test:
	@echo "Building package..."
	python -m build
	@echo "Publishing to Test PyPI..."
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*

check: lint type-check test
	@echo "All checks passed!"

all: clean install lint type-check test build
	@echo "Full build completed!"