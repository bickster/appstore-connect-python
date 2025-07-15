"""
Tests for AppStoreConnectAPI authentication and token management.
Focus on achieving 100% coverage of authentication-related code.
"""

import pytest
import jwt
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import AuthenticationError, ValidationError


class TestTokenManagement:
    """Test JWT token generation and management."""
    
    def test_token_reuse_when_valid(self):
        """Test that valid tokens are reused instead of regenerating."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer", 
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
            
            # Mock time to control token expiry
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            # Set up existing valid token
            api._token = "existing_valid_token"
            api._token_expiry = current_time + 600  # Valid for 10 more minutes
            
            with patch('builtins.open', mock_open(read_data="private_key")):
                with patch('jwt.encode', return_value="new_token") as mock_encode:
                    # Should reuse existing token
                    token = api._generate_token()
                    
                    assert token == "existing_valid_token"
                    # JWT encode should not be called
                    mock_encode.assert_not_called()
    
    def test_token_regeneration_when_expired(self):
        """Test that expired tokens are regenerated."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/test.p8", 
                vendor_number="12345"
            )
            
            current_time = int(datetime.now(timezone.utc).timestamp())
            
            # Set up expired token
            api._token = "expired_token"
            api._token_expiry = current_time - 100  # Expired 100 seconds ago
            
            with patch('builtins.open', mock_open(read_data="private_key")):
                with patch('jwt.encode', return_value="new_token") as mock_encode:
                    token = api._generate_token()
                    
                    assert token == "new_token"
                    # JWT encode should be called
                    mock_encode.assert_called_once()
    
    def test_token_generation_with_correct_claims(self):
        """Test JWT token is generated with correct claims."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key_id",
                issuer_id="test_issuer_id",
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
            
            private_key = "test_private_key"
            
            with patch('builtins.open', mock_open(read_data=private_key)):
                with patch('jwt.encode') as mock_encode:
                    mock_encode.return_value = "generated_token"
                    
                    token = api._generate_token()
                    
                    # Check the call arguments
                    call_args = mock_encode.call_args
                    payload = call_args[0][0]
                    key = call_args[0][1]
                    kwargs = call_args[1]
                    
                    # Verify payload
                    assert payload['iss'] == "test_issuer_id"
                    assert payload['aud'] == "appstoreconnect-v1"
                    assert 'exp' in payload
                    
                    # Verify key
                    assert key == private_key
                    
                    # Verify algorithm and headers
                    assert kwargs['algorithm'] == "ES256"
                    assert kwargs['headers']['alg'] == "ES256"
                    assert kwargs['headers']['kid'] == "test_key_id"
                    assert kwargs['headers']['typ'] == "JWT"
    
    def test_load_private_key_io_error(self):
        """Test handling of IO errors when loading private key."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
            
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with pytest.raises(AuthenticationError) as exc_info:
                    api._load_private_key()
                
                assert "Failed to load private key" in str(exc_info.value)
                assert "Permission denied" in str(exc_info.value)
    
    def test_token_generation_jwt_error(self):
        """Test handling of JWT encoding errors."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
            
            with patch('builtins.open', mock_open(read_data="private_key")):
                with patch('jwt.encode', side_effect=Exception("Invalid key format")):
                    with pytest.raises(AuthenticationError) as exc_info:
                        api._generate_token()
                    
                    assert "Failed to generate JWT token" in str(exc_info.value)
                    assert "Invalid key format" in str(exc_info.value)
    
    def test_token_expiry_timing(self):
        """Test that token expiry is set correctly (20 minutes minus buffer)."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
            
            with patch('builtins.open', mock_open(read_data="private_key")):
                with patch('jwt.encode', return_value="token"):
                    # Mock the datetime inside the module
                    with patch('appstore_connect.client.datetime') as mock_datetime:
                        # Create a mock datetime instance
                        mock_now = Mock()
                        mock_now.timestamp.return_value = 1000.0
                        mock_datetime.now.return_value = mock_now
                        
                        api._generate_token()
                        
                        # Token should expire in 19 minutes (20 min - 1 min buffer)
                        expected_expiry = 1000 + 1200 - 60  # current + 20min - 1min
                        assert api._token_expiry == expected_expiry


class TestInitializationEdgeCases:
    """Test edge cases in API client initialization."""
    
    def test_init_with_path_object(self):
        """Test initialization with Path object instead of string."""
        key_path = Path("/tmp/test.p8")
        
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path=key_path,  # Path object
                vendor_number="12345"
            )
            
            assert api.private_key_path == key_path
            assert isinstance(api.private_key_path, Path)
    
    def test_init_empty_vendor_number(self):
        """Test initialization with empty vendor number."""
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(ValidationError) as exc_info:
                AppStoreConnectAPI(
                    key_id="test_key",
                    issuer_id="test_issuer",
                    private_key_path="/tmp/test.p8",
                    vendor_number=""  # Empty vendor number
                )
            
            assert "Missing required authentication parameters" in str(exc_info.value)
    
    def test_init_none_parameters(self):
        """Test initialization with None parameters."""
        with pytest.raises(ValidationError) as exc_info:
            AppStoreConnectAPI(
                key_id=None,
                issuer_id="test_issuer", 
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
        
        assert "Missing required authentication parameters" in str(exc_info.value)


class TestHeaderGeneration:
    """Test request header generation."""
    
    def test_get_headers_format(self):
        """Test that headers are formatted correctly."""
        with patch('pathlib.Path.exists', return_value=True):
            api = AppStoreConnectAPI(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/test.p8",
                vendor_number="12345"
            )
            
            with patch.object(api, '_generate_token', return_value='test_token_value'):
                headers = api._get_headers()
                
                assert headers['Authorization'] == 'Bearer test_token_value'
                assert headers['Content-Type'] == 'application/json'
                assert len(headers) == 2