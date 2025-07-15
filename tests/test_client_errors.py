"""
Tests for AppStoreConnectAPI error handling.
Focus on HTTP status codes, malformed responses, and edge cases.
"""

import pytest
import requests
import json
import pandas as pd
from unittest.mock import Mock, patch

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    PermissionError,
)


@pytest.fixture
def api_client():
    """Create test API client."""
    with patch('pathlib.Path.exists', return_value=True):
        return AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test.p8",
            vendor_number="12345"
        )


class TestRequestHandling:
    """Test _make_request method edge cases."""
    
    def test_make_request_with_url_parameter(self, api_client):
        """Test using direct URL instead of endpoint."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        
        with patch('requests.request', return_value=mock_response) as mock_request:
            with patch.object(api_client, '_generate_token', return_value='token'):
                response = api_client._make_request(
                    method="GET",
                    url="https://api.example.com/v1/test"  # Direct URL
                )
                
                # Should use the provided URL
                call_args = mock_request.call_args
                assert call_args[1]['url'] == "https://api.example.com/v1/test"
                assert response == mock_response
    
    def test_make_request_missing_url_and_endpoint(self, api_client):
        """Test error when neither URL nor endpoint provided."""
        with pytest.raises(ValidationError) as exc_info:
            api_client._make_request(method="GET")
        
        assert "Either url or endpoint must be provided" in str(exc_info.value)
    
    def test_make_request_timeout(self, api_client):
        """Test request timeout handling."""
        with patch('requests.request', side_effect=requests.exceptions.Timeout):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "Request failed" in str(exc_info.value)
    
    def test_make_request_connection_error(self, api_client):
        """Test connection error handling."""
        with patch('requests.request', side_effect=requests.exceptions.ConnectionError):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "Request failed" in str(exc_info.value)


class TestHTTPStatusHandling:
    """Test handling of different HTTP status codes."""
    
    def test_rate_limit_error(self, api_client):
        """Test 429 rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "errors": [{"detail": "Rate limit exceeded"}]
        }
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(RateLimitError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "Rate limit exceeded" in str(exc_info.value)
    
    def test_generic_error_with_json_response(self, api_client):
        """Test generic error with well-formed JSON error response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": [{"detail": "Invalid request parameters"}]
        }
        mock_response.text = "Raw response text"
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "API Error 400: Invalid request parameters" in str(exc_info.value)
    
    def test_generic_error_with_malformed_json(self, api_client):
        """Test generic error when JSON parsing fails."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
        mock_response.text = "Internal Server Error"
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "API Error 500: Internal Server Error" in str(exc_info.value)
    
    def test_generic_error_with_empty_errors_array(self, api_client):
        """Test generic error with empty errors array in response."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"errors": []}
        mock_response.text = "Bad Request"
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "API Error 400: Bad Request" in str(exc_info.value)
    
    def test_generic_error_with_no_detail_field(self, api_client):
        """Test generic error when detail field is missing."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "errors": [{"code": "INVALID_INPUT"}]  # No 'detail' field
        }
        mock_response.text = "Bad Request"
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client._make_request(endpoint="/test")
                
                assert "API Error 400: Bad Request" in str(exc_info.value)
    
    def test_error_logging(self, api_client):
        """Test that errors are logged."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {
            "errors": [{"detail": "Server error occurred"}]
        }
        mock_response.text = "Internal Server Error"
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                with patch('logging.error') as mock_log_error:
                    with pytest.raises(AppStoreConnectError):
                        api_client._make_request(endpoint="/test")
                    
                    # Check that error was logged
                    mock_log_error.assert_called_once()
                    log_message = mock_log_error.call_args[0][0]
                    assert "API Error 500: Server error occurred" in log_message


class TestMetadataPermissionErrors:
    """Test permission error handling in metadata methods."""
    
    def test_get_apps_permission_error(self, api_client):
        """Test get_apps handling permission errors gracefully."""
        mock_response = Mock()
        mock_response.status_code = 403
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                # Should return None instead of raising
                result = api_client.get_apps()
                assert result is None
    
    def test_get_current_metadata_permission_error(self, api_client):
        """Test get_current_metadata with permission errors."""
        # Mock 403 for all metadata calls
        mock_response = Mock()
        mock_response.status_code = 403
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                # Should return empty structure
                metadata = api_client.get_current_metadata("123456")
                
                assert metadata == {
                    'app_info': {},
                    'app_localizations': {},
                    'version_info': {},
                    'version_localizations': {}
                }
    
    def test_get_current_metadata_not_found(self, api_client):
        """Test get_current_metadata when app not found."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        
        with patch('requests.request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                # Should return empty structure
                metadata = api_client.get_current_metadata("nonexistent")
                
                assert metadata == {
                    'app_info': {},
                    'app_localizations': {},
                    'version_info': {},
                    'version_localizations': {}
                }


class TestReportStatusCodes:
    """Test non-200 status codes in report fetching."""
    
    def test_sales_report_non_200_status(self, api_client):
        """Test sales report with non-200 status returns empty DataFrame."""
        from datetime import date
        
        mock_response = Mock()
        mock_response.status_code = 404  # No data for this date
        
        with patch.object(api_client, '_make_request', return_value=mock_response):
            with patch.object(api_client, '_generate_token', return_value='token'):
                df = api_client.get_sales_report(date.today())
                
                assert df.empty
                assert isinstance(df, pd.DataFrame)


class TestEdgeCases:
    """Test various edge cases."""
    
    def test_make_request_with_data_parameter(self, api_client):
        """Test making request with JSON data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        
        test_data = {"key": "value"}
        
        with patch('requests.request', return_value=mock_response) as mock_request:
            with patch.object(api_client, '_generate_token', return_value='token'):
                api_client._make_request(
                    method="POST",
                    endpoint="/test",
                    data=test_data
                )
                
                # Check that JSON data was passed
                call_args = mock_request.call_args
                assert call_args[1]['json'] == test_data
    
    def test_make_request_with_params(self, api_client):
        """Test making request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        
        test_params = {"filter": "active", "limit": 100}
        
        with patch('requests.request', return_value=mock_response) as mock_request:
            with patch.object(api_client, '_generate_token', return_value='token'):
                api_client._make_request(
                    method="GET",
                    endpoint="/test",
                    params=test_params
                )
                
                # Check that params were passed
                call_args = mock_request.call_args
                assert call_args[1]['params'] == test_params