"""
Pytest configuration and shared fixtures for appstore-connect-client tests.
"""

import pytest
import pandas as pd
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch
import os
import tempfile
from dotenv import load_dotenv

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.reports import ReportProcessor
from appstore_connect.metadata import MetadataManager

# Load environment variables from .env file
# Find the .env file relative to this conftest.py file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try current directory as fallback
    load_dotenv()


# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture
def api_credentials():
    """Provide test API credentials."""
    return {
        "key_id": "TEST_KEY_ID",
        "issuer_id": "TEST_ISSUER_ID",
        "private_key_path": "/tmp/test_key.p8",
        "vendor_number": "12345678",
        "app_ids": ["123456789", "987654321"],
    }


@pytest.fixture
def private_key_content():
    """Provide sample private key content for testing."""
    return """-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgExamplePrivateKey
Content1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
-----END PRIVATE KEY-----"""


@pytest.fixture
def api_client(api_credentials, private_key_content):
    """Create a mocked API client for testing."""
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                private_key_content
            )

            client = AppStoreConnectAPI(
                key_id=api_credentials["key_id"],
                issuer_id=api_credentials["issuer_id"],
                private_key_path=api_credentials["private_key_path"],
                vendor_number=api_credentials["vendor_number"],
                app_ids=api_credentials["app_ids"],
            )

            # Mock the token generation to avoid JWT issues in tests
            with patch.object(client, "_generate_token", return_value="test_token"):
                yield client


@pytest.fixture
def report_processor(api_client):
    """Create a ReportProcessor instance."""
    return ReportProcessor(api_client)


@pytest.fixture
def metadata_manager(api_client):
    """Create a MetadataManager instance."""
    return MetadataManager(api_client)


@pytest.fixture
def sample_sales_data():
    """Create sample sales DataFrame for testing."""
    return pd.DataFrame(
        {
            "Apple Identifier": ["123456789", "987654321", "123456789", "987654321"],
            "Title": ["App One", "App Two", "App One", "App Two"],
            "Units": [10, 20, 15, 25],
            "Developer Proceeds": [7.0, 14.0, 10.5, 17.5],
            "Customer Price": [9.99, 19.99, 14.99, 24.99],
            "Country Code": ["US", "US", "GB", "GB"],
            "Product Type Identifier": ["1", "1", "1", "1"],
            "report_date": [
                date(2023, 6, 1),
                date(2023, 6, 1),
                date(2023, 6, 2),
                date(2023, 6, 2),
            ],
        }
    )


@pytest.fixture
def sample_subscription_data():
    """Create sample subscription DataFrame for testing."""
    return pd.DataFrame(
        {
            "App Apple ID": ["123456789", "987654321"],
            "App Name": ["App One", "App Two"],
            "Subscription Name": ["Premium Monthly", "Pro Annual"],
            "Active Subscriptions": [500, 300],
            "New Subscriptions": [50, 30],
            "Cancelled Subscriptions": [20, 10],
            "Proceeds": [2500.0, 9000.0],
            "report_date": [date(2023, 6, 1), date(2023, 6, 1)],
        }
    )


@pytest.fixture
def sample_subscription_events():
    """Create sample subscription events DataFrame for testing."""
    return pd.DataFrame(
        {
            "Event": ["Subscribe", "Cancel", "Subscribe", "Renew", "Renew"],
            "App Apple ID": [
                "123456789",
                "123456789",
                "987654321",
                "123456789",
                "987654321",
            ],
            "Subscription Name": [
                "Premium Monthly",
                "Premium Monthly",
                "Pro Annual",
                "Premium Monthly",
                "Pro Annual",
            ],
            "Quantity": [1, 1, 1, 1, 1],
            "report_date": [
                date(2023, 6, 1),
                date(2023, 6, 1),
                date(2023, 6, 1),
                date(2023, 6, 2),
                date(2023, 6, 2),
            ],
        }
    )


@pytest.fixture
def sample_app_metadata():
    """Create sample app metadata for testing."""
    return {
        "data": [
            {
                "id": "123456789",
                "type": "apps",
                "attributes": {
                    "name": "App One",
                    "bundleId": "com.example.appone",
                    "sku": "APPONE",
                    "primaryLocale": "en-US",
                },
                "relationships": {
                    "appInfos": {"data": [{"id": "info123", "type": "appInfos"}]},
                    "appStoreVersions": {
                        "data": [{"id": "ver123", "type": "appStoreVersions"}]
                    },
                },
            },
            {
                "id": "987654321",
                "type": "apps",
                "attributes": {
                    "name": "App Two",
                    "bundleId": "com.example.apptwo",
                    "sku": "APPTWO",
                    "primaryLocale": "en-US",
                },
                "relationships": {
                    "appInfos": {"data": [{"id": "info987", "type": "appInfos"}]},
                    "appStoreVersions": {
                        "data": [{"id": "ver987", "type": "appStoreVersions"}]
                    },
                },
            },
        ]
    }


@pytest.fixture
def temp_private_key():
    """Create a temporary private key file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".p8", delete=False) as f:
        f.write(
            """-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgExamplePrivateKey
Content1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz
-----END PRIVATE KEY-----"""
        )
        temp_path = f.name

    yield temp_path

    # Cleanup
    try:
        os.unlink(temp_path)
    except Exception:
        pass


@pytest.fixture
def mock_jwt_token():
    """Mock JWT token generation."""
    with patch("jwt.encode", return_value="mocked_jwt_token"):
        yield "mocked_jwt_token"


@pytest.fixture
def mock_api_response():
    """Create a mock API response."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": []}
    mock_response.content = b"test content"
    return mock_response


@pytest.fixture
def mock_requests(mock_api_response):
    """Mock requests library."""
    with patch("requests.request", return_value=mock_api_response) as mock:
        yield mock


@pytest.mark.integration
def integration_test_credentials():
    """
    Check if integration test credentials are available.

    Integration tests are skipped if credentials are not configured.
    Set these environment variables to run integration tests:
    - INTEGRATION_TEST_KEY_ID
    - INTEGRATION_TEST_ISSUER_ID
    - INTEGRATION_TEST_PRIVATE_KEY_PATH
    - INTEGRATION_TEST_VENDOR_NUMBER
    """
    required_vars = [
        "INTEGRATION_TEST_KEY_ID",
        "INTEGRATION_TEST_ISSUER_ID",
        "INTEGRATION_TEST_PRIVATE_KEY_PATH",
        "INTEGRATION_TEST_VENDOR_NUMBER",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        pytest.skip(
            f"Integration test credentials not configured. Missing: {', '.join(missing)}"
        )

    return {
        "key_id": os.getenv("INTEGRATION_TEST_KEY_ID"),
        "issuer_id": os.getenv("INTEGRATION_TEST_ISSUER_ID"),
        "private_key_path": os.getenv("INTEGRATION_TEST_PRIVATE_KEY_PATH"),
        "vendor_number": os.getenv("INTEGRATION_TEST_VENDOR_NUMBER"),
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test requiring API credentials",
    )
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add integration marker to tests in test_integration.py
        if "test_integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Add slow marker to certain tests
        if "test_large_dataset" in item.name or "test_bulk_" in item.name:
            item.add_marker(pytest.mark.slow)
