"""
Additional tests for metadata.py to achieve 100% coverage.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import csv

from appstore_connect.metadata import MetadataManager
from appstore_connect.exceptions import ValidationError, NotFoundError, PermissionError


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    api = Mock()
    return api


@pytest.fixture  
def metadata_manager(mock_api):
    """Create a MetadataManager with mock API."""
    return MetadataManager(mock_api)


class TestMetadataManagerEdgeCases:
    """Test edge cases and error handling in MetadataManager."""
    
    def test_get_app_portfolio_api_error(self, metadata_manager, mock_api):
        """Test get_app_portfolio when API call fails."""
        # API returns None (error case)
        mock_api.get_apps.return_value = None
        
        portfolio = metadata_manager.get_app_portfolio()
        
        # Should return empty list
        assert portfolio == []
    
    def test_update_app_listing_locale_not_found(self, metadata_manager, mock_api):
        """Test update_app_listing when locale doesn't exist."""
        # Mock successful responses for name update
        mock_api.update_app_name.return_value = True
        
        # But locale not found for description update
        mock_api.get_editable_version.return_value = {
            'id': 'ver123',
            'attributes': {'appStoreState': 'PREPARE_FOR_SUBMISSION'}
        }
        mock_api.get_app_store_version_localizations.return_value = {
            'data': [{
                'id': 'loc123',
                'attributes': {'locale': 'fr-FR'}  # Different locale
            }]
        }
        
        updates = {
            'name': 'New Name',
            'description': 'New Description'
        }
        
        # Should partially succeed
        results = metadata_manager.update_app_listing(
            app_id='123456789',
            updates=updates,
            locale='en-US'
        )
        
        # Name should succeed, description should fail
        assert results['success'] is False
        assert 'name' in results['updated']
        assert 'description' in results['errors']
    
    def test_batch_update_apps_api_exception(self, metadata_manager, mock_api):
        """Test batch_update_apps when API raises exception."""
        # First app succeeds
        mock_api.update_app_name.side_effect = [True, Exception("API Error")]
        
        updates = {
            '123456789': {'name': 'App 1'},
            '987654321': {'name': 'App 2'}
        }
        
        results = metadata_manager.batch_update_apps(
            updates=updates,
            continue_on_error=True
        )
        
        # Should have one success and one error
        assert '123456789' in results['results']
        assert results['results']['123456789']['success'] is True
        assert '987654321' in results['results']
        assert results['results']['987654321']['success'] is False
        assert "API Error" in str(results['results']['987654321']['errors'])
    
    def test_standardize_app_names_no_changes_needed(self, metadata_manager, mock_api):
        """Test standardize_app_names when no changes are needed."""
        # Mock portfolio with already standardized names
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {
                    'name': 'MyApp Pro',
                    'bundleId': 'com.test.myapp',
                    'sku': 'MYAPP'
                }
            }]
        }
        
        mock_api.get_current_metadata.return_value = {
            'app_info': {
                'name': 'MyApp Pro',
                'bundleId': 'com.test.myapp'
            },
            'app_localizations': {
                'en-US': {'name': 'MyApp Pro'}
            }
        }
        
        with patch('appstore_connect.utils.sanitize_app_name', return_value='MyApp Pro'):
            results = metadata_manager.standardize_app_names(
                pattern="{app_name} Pro",
                dry_run=False
            )
            
            # No updates should be made
            assert results['updated'] == []
            mock_api.update_app_name.assert_not_called()
    
    def test_prepare_version_releases_no_eligible_versions(self, metadata_manager, mock_api):
        """Test prepare_version_releases with no eligible versions."""
        # Mock portfolio
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'Test App'}
            }]
        }
        
        # Mock no editable version
        mock_api.get_editable_version.return_value = None
        
        results = metadata_manager.prepare_version_releases(
            release_notes="New features",
            dry_run=False
        )
        
        # Should skip app with no editable version
        assert results['skipped'] == ['123456789']
        assert results['updated'] == []
    
    def test_get_localization_status_with_errors(self, metadata_manager, mock_api):
        """Test get_localization_status with API errors."""
        # Mock portfolio
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'Test App'}
            }]
        }
        
        # Mock metadata fetch failure
        mock_api.get_current_metadata.side_effect = PermissionError("No access")
        
        with patch('logging.error') as mock_log:
            status = metadata_manager.get_localization_status(['en-US', 'fr-FR'])
            
            # Should handle error gracefully
            assert '123456789' in status
            assert status['123456789']['error'] is True
            mock_log.assert_called()
    
    def test_export_app_metadata_with_permission_error(self, metadata_manager, mock_api, tmp_path):
        """Test export_app_metadata when API has permission errors."""
        # Mock portfolio fetch failure
        mock_api.get_apps.side_effect = PermissionError("No metadata access")
        
        output_file = tmp_path / "export.csv"
        
        # Should return False
        result = metadata_manager.export_app_metadata(str(output_file))
        assert result is False
        
        # File should not be created
        assert not output_file.exists()
    
    def test_validation_edge_cases(self, metadata_manager):
        """Test validation edge cases."""
        # Test with None app_id
        with pytest.raises(ValidationError):
            metadata_manager.update_app_listing(
                app_id=None,
                updates={'name': 'Test'},
                validate=True
            )
        
        # Test with empty string app_id
        with pytest.raises(ValidationError):
            metadata_manager.update_app_listing(
                app_id='',
                updates={'name': 'Test'},
                validate=True
            )
        
        # Test batch update with invalid locale format
        with pytest.raises(ValidationError):
            metadata_manager.batch_update_apps(
                updates={'123456789': {'name': 'Test'}},
                locale='english'  # Should be like 'en-US'
            )
    
    def test_update_promotional_text_special_case(self, metadata_manager, mock_api):
        """Test updating promotional text through update_app_listing."""
        mock_api.get_editable_version.return_value = {
            'id': 'ver123',
            'attributes': {'appStoreState': 'PREPARE_FOR_SUBMISSION'}
        }
        
        mock_api.update_promotional_text.return_value = True
        
        results = metadata_manager.update_app_listing(
            app_id='123456789',
            updates={'promotional_text': 'Check out the new features!'},
            locale='en-US'
        )
        
        assert results['success'] is True
        assert 'promotional_text' in results['updated']
        
        # Verify the call
        mock_api.update_promotional_text.assert_called_once_with(
            '123456789',
            'Check out the new features!',
            locale='en-US'
        )


class TestMetadataManagerCaching:
    """Test caching behavior in MetadataManager."""
    
    def test_portfolio_cache_invalidation(self, metadata_manager, mock_api):
        """Test that portfolio cache is properly invalidated."""
        # Set up initial portfolio
        initial_data = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'Old Name'}
            }]
        }
        mock_api.get_apps.return_value = initial_data
        
        # First call - should fetch from API
        portfolio1 = metadata_manager.get_app_portfolio()
        assert len(portfolio1) == 1
        assert mock_api.get_apps.call_count == 1
        
        # Force cache refresh by setting _portfolio_cache to None
        metadata_manager._portfolio_cache = None
        
        # Update return value
        updated_data = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'New Name'}
            }]
        }
        mock_api.get_apps.return_value = updated_data
        
        # Second call - should fetch again
        portfolio2 = metadata_manager.get_app_portfolio(refresh=True)
        assert mock_api.get_apps.call_count == 2
        assert portfolio2[0]['name'] == 'New Name'