"""
Tests for the AppStoreConnectAPI client.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime
from pathlib import Path

from appstore_connect import AppStoreConnectAPI
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
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
    def test_load_private_key_success(self, mock_open, api_client, mock_private_key):
        """Test successful private key loading."""
        mock_open.return_value.__enter__.return_value.read.return_value = mock_private_key
        
        result = api_client._load_private_key()
        assert result == mock_private_key
    
    @patch('builtins.open', side_effect=IOError("File not found"))
    def test_load_private_key_failure(self, mock_open, api_client):
        """Test private key loading failure."""
        with pytest.raises(AuthenticationError):
            api_client._load_private_key()
    
    @patch.object(AppStoreConnectAPI, '_load_private_key')
    @patch('jwt.encode')
    def test_generate_token_success(self, mock_jwt_encode, mock_load_key, api_client, mock_private_key):
        """Test successful JWT token generation."""
        mock_load_key.return_value = mock_private_key
        mock_jwt_encode.return_value = "test_token"
        
        token = api_client._generate_token()
        assert token == "test_token"
        assert api_client._token == "test_token"
    
    @patch.object(AppStoreConnectAPI, '_load_private_key', side_effect=Exception("Key error"))
    def test_generate_token_key_failure(self, mock_load_key, api_client):
        """Test token generation with key loading failure."""
        with pytest.raises(AuthenticationError):
            api_client._generate_token()
    
    @patch.object(AppStoreConnectAPI, '_load_private_key')
    @patch('jwt.encode', side_effect=Exception("JWT error"))
    def test_generate_token_jwt_failure(self, mock_jwt_encode, mock_load_key, api_client, mock_private_key):
        """Test token generation with JWT encoding failure."""
        mock_load_key.return_value = mock_private_key
        
        with pytest.raises(AuthenticationError):
            api_client._generate_token()


class TestSalesReporting:
    """Test sales reporting methods."""
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    def test_get_sales_report_success(self, mock_request, api_client):
        """Test successful sales report retrieval."""
        # Mock successful response with gzipped TSV data
        mock_response = Mock()
        mock_response.status_code = 200
        
        # Create sample TSV data
        tsv_data = "Provider\\tProvider Country\\tUnits\\n"
        tsv_data += "APPLE\\tUS\\t10\\n"
        
        # Compress the data
        import gzip
        import io
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='wb') as f:
            f.write(tsv_data.encode('utf-8'))
        mock_response.content = buffer.getvalue()
        
        mock_request.return_value = mock_response
        
        result = api_client.get_sales_report(date.today())
        
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert 'Units' in result.columns
        assert result['Units'].iloc[0] == 10
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    def test_get_sales_report_empty(self, mock_request, api_client):
        """Test sales report with no data."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        result = api_client.get_sales_report(date.today())
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
    
    def test_get_subscription_report(self, api_client):
        """Test subscription report retrieval."""
        with patch.object(api_client, 'get_sales_report') as mock_get_sales:
            mock_get_sales.return_value = pd.DataFrame()
            
            result = api_client.get_subscription_report(date.today())
            
            mock_get_sales.assert_called_once_with(
                report_date=date.today(),
                report_type="SUBSCRIPTION",
                report_subtype="SUMMARY",
                frequency="DAILY"
            )


class TestMetadataManagement:
    """Test metadata management methods."""
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    def test_get_apps_success(self, mock_request, api_client):
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
        
        result = api_client.get_apps()
        
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 1
        assert result["data"][0]["attributes"]["name"] == "Test App"
    
    @patch.object(AppStoreConnectAPI, '_make_request')
    def test_get_apps_failure(self, mock_request, api_client):
        """Test apps retrieval failure."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        result = api_client.get_apps()
        assert result is None
    
    def test_update_app_name_validation(self, api_client):
        """Test app name update with validation."""
        with pytest.raises(ValidationError, match="App name too long"):
            api_client.update_app_name("123", "a" * 31)  # Too long
    
    def test_update_app_subtitle_validation(self, api_client):
        """Test app subtitle update with validation."""
        with pytest.raises(ValidationError, match="App subtitle too long"):
            api_client.update_app_subtitle("123", "a" * 31)  # Too long
    
    def test_update_app_description_validation(self, api_client):
        """Test app description update with validation."""
        with pytest.raises(ValidationError, match="Description too long"):
            api_client.update_app_description("123", "a" * 4001)  # Too long
    
    def test_update_app_keywords_validation(self, api_client):
        """Test app keywords update with validation.""" 
        with pytest.raises(ValidationError, match="Keywords too long"):
            api_client.update_app_keywords("123", "a" * 101)  # Too long


class TestErrorHandling:
    """Test error handling."""
    
    @patch('requests.request')
    def test_request_timeout(self, mock_request, api_client):
        """Test request timeout handling."""
        mock_request.side_effect = requests.exceptions.Timeout()
        
        with pytest.raises(AppStoreConnectError, match="Request failed"):
            api_client._make_request(endpoint="/test")
    
    @patch('requests.request')
    def test_authentication_error(self, mock_request, api_client):
        """Test 401 authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        
        with pytest.raises(AuthenticationError):
            api_client._make_request(endpoint="/test")
    
    @patch('requests.request')
    def test_permission_error(self, mock_request, api_client):
        """Test 403 permission error."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_request.return_value = mock_response
        
        with pytest.raises(PermissionError):
            api_client._make_request(endpoint="/test")
    
    @patch('requests.request')
    def test_not_found_error(self, mock_request, api_client):
        """Test 404 not found error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        with pytest.raises(NotFoundError):
            api_client._make_request(endpoint="/test")