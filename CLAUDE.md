# CLAUDE.md

This file provides guidance to Claude AI when working with code in this repository.

## Project Overview

`appstore-connect-client` is a Python library for interacting with Apple's App Store Connect API. It provides:
- Sales and financial reporting
- App metadata management
- Subscription analytics
- Portfolio-wide operations

## Key Design Principles

1. **Backward Compatibility**: The library maintains compatibility with existing implementations while adding new features
2. **Clear Error Handling**: All API errors are mapped to specific exception types
3. **Rate Limiting**: Built-in rate limiting (3500 requests/hour) with exponential backoff
4. **Type Safety**: Comprehensive type hints throughout the codebase

## Code Style Guidelines

- Use type hints for all function parameters and return values
- Follow PEP 8 style guide
- Document all public methods with comprehensive docstrings
- Maintain test coverage above 80%

## Testing

- Run tests with: `pytest`
- Check coverage with: `pytest --cov=appstore_connect`
- Run type checking with: `mypy src/appstore_connect`
- Format code with: `black src/appstore_connect tests`

## Common Tasks

### Adding New API Endpoints
1. Add method to `AppStoreConnectAPI` class in `client.py`
2. Include proper error handling and rate limiting decorators
3. Add corresponding tests in `test_client.py`
4. Update documentation in `docs/API_REFERENCE.md`

### Updating Documentation
- API reference: `docs/API_REFERENCE.md`
- User guide: `docs/GETTING_STARTED.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`
- Changelog: `CHANGELOG.md`

## Important Notes

- Private keys should never be committed to the repository
- All API credentials should be loaded from environment variables or files
- Integration tests require valid API credentials (see `TESTING.md`)
- Examples should use placeholder values for sensitive data

## Release Process

1. Update version in `setup.py` and `__init__.py`
2. Update `CHANGELOG.md` with release notes
3. Create git tag: `git tag v0.1.0`
4. Push tag: `git push origin v0.1.0`
5. GitHub Actions will automatically publish to PyPI

## Helpful Commands

```bash
# Install development dependencies
pip install -e .[dev]

# Run all tests
pytest

# Run tests with verbose output
pytest -v --tb=long

# Run specific test file
pytest tests/test_client.py

# Check code coverage
pytest --cov=appstore_connect --cov-report=html --cov-report=term

# Format code
black src/appstore_connect tests

# Check formatting without making changes
black --check src/appstore_connect tests

# Run linting checks (matching GitHub Actions)
flake8 src/appstore_connect tests --max-line-length=100 --extend-ignore=E203,W503

# Type checking
mypy src/appstore_connect

# Build package
python -m build

# Clean build artifacts
rm -rf build/ dist/ *.egg-info/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Run all checks (lint + type-check + tests) - matching GitHub Actions
black --check src/appstore_connect tests && \
flake8 src/appstore_connect tests --max-line-length=100 --extend-ignore=E203,W503 && \
mypy src/appstore_connect && \
pytest

# Or use the build script which runs all checks
./build_and_upload.sh

# Publish to PyPI (requires API token)
python -m build
python -m twine upload dist/*

# Publish to Test PyPI
python -m build
python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
```