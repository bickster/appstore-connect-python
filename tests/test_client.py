"""
Tests for the AppStoreConnectAPI client.
"""

import pytest
import pandas as pd
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from pathlib import Path

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    PermissionError,
)


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
def mock_private_key():
    """Mock private key content."""
    return """-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgExample...
-----END PRIVATE KEY-----"""


class TestInitialization:
    """Test API client initialization."""
    
    def test_init_valid_params(self):
        """Test initialization with valid parameters."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="key123",
                issuer_id="issuer123", 
                private_key_path="/path/to/key.p8",
                vendor_number="12345"
            )
            assert api.key_id == "key123"
            assert api.issuer_id == "issuer123"
            assert api.vendor_number == "12345"
            assert api.app_ids == []
    
    def test_init_with_app_ids(self):
        """Test initialization with app IDs filter."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="key123",
                issuer_id="issuer123",
                private_key_path="/path/to/key.p8", 
                vendor_number="12345",
                app_ids=["123", "456"]
            )
            assert api.app_ids == ["123", "456"]
    
    def test_init_missing_params(self):
        """Test initialization with missing parameters."""
        with pytest.raises(ValidationError):
            AppStoreConnectAPI(
                key_id="",
                issuer_id="issuer123",
                private_key_path="/path/to/key.p8",
                vendor_number="12345"
            )
    
    def test_init_missing_private_key(self):
        """Test initialization with missing private key file."""
        with patch('pathlib.Path.exists', return_value=False):
            with pytest.raises(ValidationError):
                AppStoreConnectAPI(
                    key_id="key123",
                    issuer_id="issuer123",
                    private_key_path="/nonexistent/key.p8",
                    vendor_number="12345"
                )


class TestAuthentication:
    """Test authentication methods."""
    
    @patch('builtins.open', create=True)
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_private_key_success(self, mock_exists, mock_open, mock_private_key):
        """Test successful private key loading."""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_private_key
        
        # Create API client with mocked file existence
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        result = api._load_private_key()
        assert result == mock_private_key
    
    @patch('builtins.open', side_effect=IOError("File not found"))
    @patch('pathlib.Path.exists', return_value=True)
    def test_load_private_key_failure(self, mock_exists, mock_open):
        """Test private key loading failure."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(AuthenticationError):
            api._load_private_key()
    
    @patch('jwt.encode')
    @patch('builtins.open', create=True)
    @patch('pathlib.Path.exists', return_value=True)
    def test_generate_token_success(self, mock_exists, mock_open, mock_jwt_encode, mock_private_key):
        """Test successful JWT token generation."""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_private_key
        mock_jwt_encode.return_value = "test_token"
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        token = api._generate_token()
        assert token == "test_token"
        assert api._token == "test_token"
    
    @patch('builtins.open', side_effect=Exception("Key error"))
    @patch('pathlib.Path.exists', return_value=True)
    def test_generate_token_key_failure(self, mock_exists, mock_open):
        """Test token generation with key loading failure."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(AuthenticationError):
            api._generate_token()
    
    @patch('jwt.encode', side_effect=Exception("JWT error"))
    @patch('builtins.open', create=True)
    @patch('pathlib.Path.exists', return_value=True)
    def test_generate_token_jwt_failure(self, mock_exists, mock_open, mock_jwt_encode, mock_private_key):
        """Test token generation with JWT encoding failure."""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_private_key
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(AuthenticationError):
            api._generate_token()


class TestSalesReporting:
    """Test sales reporting methods."""
    
    @patch('builtins.open', create=True)
    @patch('jwt.encode')
    @patch.object(AppStoreConnectAPI, '_make_request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_get_sales_report_success(self, mock_exists, mock_request, mock_jwt, mock_open):
        """Test successful sales report retrieval."""
        # Mock JWT and file reading
        mock_jwt.return_value = "test_token"
        mock_open.return_value.__enter__.return_value.read.return_value = "test_key"
        
        # Mock successful response with gzipped TSV data
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Create sample TSV data
        tsv_data = "Provider\tProvider Country\tUnits\n"
        tsv_data += "APPLE\tUS\t10\n"
        
        # Compress the data
        import gzip
        import io
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
            f.write(tsv_data.encode('utf-8'))
        mock_response.content = buffer.getvalue()
        
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        result = api.get_sales_report(date.today())
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert 'Units' in result.columns
        assert result['Units'].iloc[0] == 10
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_get_sales_report_empty(self, mock_exists, mock_request):
        """Test sales report with no data."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        result = api.get_sales_report(date.today())
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    @patch('pathlib.Path.exists', return_value=True)
    def test_get_subscription_report(self, mock_exists):
        """Test subscription report retrieval."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with patch.object(api, 'get_sales_report') as mock_get_sales:
            mock_get_sales.return_value = pd.DataFrame()
            
            result = api.get_subscription_report(date.today())
            
            mock_get_sales.assert_called_once_with(
                report_date=date.today(),
                report_type="SUBSCRIPTION",
                report_subtype="SUMMARY",
                frequency="DAILY"
            )


class TestMetadataManagement:
    """Test metadata management methods."""
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_get_apps_success(self, mock_exists, mock_request):
        """Test successful apps retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "123",
                    "attributes": {
                        "name": "Test App",
                        "bundleId": "com.test.app"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        result = api.get_apps()
        
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["attributes"]["name"] == "Test App"
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_get_apps_failure(self, mock_exists, mock_request):
        """Test apps retrieval failure."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        result = api.get_apps()
        assert result is None
    
    @patch('pathlib.Path.exists', return_value=True)
    def test_update_app_name_validation(self, mock_exists):
        """Test app name update with validation."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(ValidationError, match="App name too long"):
            api.update_app_name("123", "a" * 31)  # Too long
    
    @patch('pathlib.Path.exists', return_value=True)
    def test_update_app_subtitle_validation(self, mock_exists):
        """Test app subtitle update with validation."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(ValidationError, match="App subtitle too long"):
            api.update_app_subtitle("123", "a" * 31)  # Too long
    
    @patch('pathlib.Path.exists', return_value=True)
    def test_update_app_description_validation(self, mock_exists):
        """Test app description update with validation."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(ValidationError, match="Description too long"):
            api.update_app_description("123", "a" * 4001)  # Too long
    
    @patch('pathlib.Path.exists', return_value=True)
    def test_update_app_keywords_validation(self, mock_exists):
        """Test app keywords update with validation."""
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(ValidationError, match="Keywords too long"):
            api.update_app_keywords("123", "a" * 101)  # Too long


class TestErrorHandling:
    """Test error handling."""
    
    @patch('builtins.open', create=True)
    @patch('jwt.encode')
    @patch('requests.request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_request_timeout(self, mock_exists, mock_request, mock_jwt, mock_open):
        """Test request timeout handling."""
        mock_jwt.return_value = "test_token"
        mock_open.return_value.__enter__.return_value.read.return_value = "test_key"
        mock_request.side_effect = requests.exceptions.Timeout()
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(AppStoreConnectError, match="Request failed"):
            api._make_request(endpoint="/test")
    
    @patch('requests.request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_authentication_error(self, mock_exists, mock_request):
        """Test 401 authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(AuthenticationError):
            api._make_request(endpoint="/test")
    
    @patch('builtins.open', create=True)
    @patch('jwt.encode')
    @patch('requests.request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_permission_error(self, mock_exists, mock_request, mock_jwt, mock_open):
        """Test 403 permission error."""
        mock_jwt.return_value = "test_token"
        mock_open.return_value.__enter__.return_value.read.return_value = "test_key"
        mock_response = Mock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(PermissionError):
            api._make_request(endpoint="/test")
    
    @patch('builtins.open', create=True)
    @patch('jwt.encode')
    @patch('requests.request')
    @patch('pathlib.Path.exists', return_value=True)
    def test_not_found_error(self, mock_exists, mock_request, mock_jwt, mock_open):
        """Test 404 not found error."""
        mock_jwt.return_value = "test_token"
        mock_open.return_value.__enter__.return_value.read.return_value = "test_key"
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        api = AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test_key.p8",
            vendor_number="12345"
        )
        
        with pytest.raises(NotFoundError):
            api._make_request(endpoint="/test")