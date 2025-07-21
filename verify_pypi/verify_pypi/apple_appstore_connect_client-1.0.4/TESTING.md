# Testing Guide

This document describes how to test the appstore-connect-client library.

## Table of Contents
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Integration Testing](#integration-testing)
- [Coverage Requirements](#coverage-requirements)
- [Continuous Integration](#continuous-integration)

## Running Tests

### Prerequisites

Install development dependencies:
```bash
pip install -e .[dev]
```

### Basic Test Execution

Run all tests:
```bash
pytest
```

Run tests with verbose output:
```bash
pytest -v
```

Run a specific test file:
```bash
pytest tests/test_client.py
```

Run a specific test class:
```bash
pytest tests/test_client.py::TestAuthentication
```

Run a specific test method:
```bash
pytest tests/test_client.py::TestAuthentication::test_generate_token_success
```

### Coverage Reports

Generate coverage report:
```bash
pytest --cov=appstore_connect
```

Generate HTML coverage report:
```bash
pytest --cov=appstore_connect --cov-report=html
open htmlcov/index.html
```

Generate detailed terminal report:
```bash
pytest --cov=appstore_connect --cov-report=term-missing
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures and configuration
├── test_client.py       # Tests for AppStoreConnectAPI class
├── test_exceptions.py   # Tests for custom exceptions
├── test_integration.py  # Integration tests (require credentials)
├── test_metadata.py     # Tests for MetadataManager
├── test_reports.py      # Tests for ReportProcessor
└── test_utils.py        # Tests for utility functions
```

### Test Categories

1. **Unit Tests**: Test individual methods and functions in isolation
2. **Integration Tests**: Test interaction with actual App Store Connect API
3. **Mock Tests**: Test behavior using mocked API responses

## Writing Tests

### Basic Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from appstore_connect import AppStoreConnectAPI
from appstore_connect.exceptions import ValidationError

class TestFeatureName:
    """Test suite for specific feature."""
    
    def test_success_case(self):
        """Test successful operation."""
        # Arrange
        api = Mock(spec=AppStoreConnectAPI)
        
        # Act
        result = some_function(api)
        
        # Assert
        assert result == expected_value
    
    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValidationError):
            some_function_that_should_fail()
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
@pytest.fixture
def api_client():
    """Create a test API client instance."""
    with patch('pathlib.Path.exists', return_value=True):
        return AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )

@pytest.fixture
def sample_sales_data():
    """Create sample sales DataFrame."""
    return pd.DataFrame({
        'Units': [10, 20, 30],
        'Developer Proceeds': [1.0, 2.0, 3.0]
    })
```

### Mocking Best Practices

1. **Mock External Dependencies**:
```python
@patch('requests.request')
def test_api_call(mock_request):
    mock_request.return_value.status_code = 200
    mock_request.return_value.json.return_value = {"data": []}
```

2. **Mock File System**:
```python
@patch('builtins.open', create=True)
@patch('pathlib.Path.exists', return_value=True)
def test_file_operations(mock_exists, mock_open):
    mock_open.return_value.__enter__.return_value.read.return_value = "content"
```

3. **Mock JWT Token Generation**:
```python
@patch('jwt.encode')
def test_token_generation(mock_jwt):
    mock_jwt.return_value = "test_token"
```

## Integration Testing

Integration tests interact with the actual App Store Connect API and require valid credentials.

### Setup

1. Create a `.env.test` file with test credentials:
```bash
APP_STORE_KEY_ID=your_test_key_id
APP_STORE_ISSUER_ID=your_test_issuer_id
APP_STORE_PRIVATE_KEY_PATH=/path/to/test/key.p8
APP_STORE_VENDOR_NUMBER=your_test_vendor_number
```

2. Run integration tests:
```bash
pytest tests/test_integration.py -v
```

### Integration Test Markers

Integration tests are marked with `@pytest.mark.integration`:

```python
@pytest.mark.integration
def test_real_api_call():
    """Test actual API interaction."""
    # This test will be skipped unless credentials are available
```

Skip integration tests:
```bash
pytest -m "not integration"
```

Run only integration tests:
```bash
pytest -m integration
```

## Coverage Requirements

- Minimum overall coverage: 80%
- New features must include tests
- Bug fixes should include regression tests

### Coverage Guidelines

1. **Test all public methods**
2. **Test error conditions and edge cases**
3. **Test validation logic**
4. **Mock external dependencies**

### Checking Coverage Locally

Before submitting a PR, ensure coverage meets requirements:

```bash
pytest --cov=appstore_connect --cov-fail-under=80
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Multiple Python versions (3.7, 3.8, 3.9, 3.10, 3.11)

### CI Test Matrix

- **Operating Systems**: Ubuntu (latest)
- **Python Versions**: 3.7, 3.8, 3.9, 3.10, 3.11
- **Test Types**: Unit tests, linting, type checking

### Pre-commit Hooks

Install pre-commit hooks to catch issues before committing:

```bash
pip install pre-commit
pre-commit install
```

This will run:
- Black (code formatting)
- Flake8 (linting)
- MyPy (type checking)

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure package is installed with `pip install -e .`
2. **Missing Dependencies**: Install dev dependencies with `pip install -e .[dev]`
3. **Failed Mocks**: Check that all file/network operations are properly mocked
4. **Integration Test Failures**: Verify API credentials are valid and have necessary permissions

### Debugging Tests

Run tests with debugging output:
```bash
pytest -vv -s
```

Use pytest's built-in debugger:
```bash
pytest --pdb
```

Run specific test with print statements:
```bash
pytest -s tests/test_client.py::test_specific_function
```