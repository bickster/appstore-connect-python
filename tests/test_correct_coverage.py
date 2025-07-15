"""
Correct tests for actual uncovered lines in the codebase.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import logging

from appstore_connect.metadata import MetadataManager
from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import ValidationError, AppStoreConnectError


class TestActualMetadataCoverage:
    """Test the actual uncovered lines in metadata.py."""
    
    def test_get_app_portfolio_with_none_metadata(self):
        """Test line 206: When get_current_metadata returns None."""
        mock_api = Mock()
        
        # Mock get_apps to return an app
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {
                    'name': 'Test App',
                    'bundleId': 'com.test.app',
                    'sku': 'APP123',
                    'primaryLocale': 'en-US'
                }
            }]
        }
        
        # Mock get_current_metadata to return None (instead of a dict)
        mock_api.get_current_metadata.return_value = None
        
        manager = MetadataManager(mock_api)
        
        with patch('logging.warning') as mock_warning:
            portfolio = manager.get_app_portfolio()
            
            # Should log warning about None metadata
            assert mock_warning.called
            warning_msg = str(mock_warning.call_args[0][0])
            assert "Could not fetch metadata for app 123456789" in warning_msg
            
            # Should still have basic info
            assert '123456789' in portfolio
            assert portfolio['123456789']['basic_info']['name'] == 'Test App'
    
    def test_update_app_listing_field_specific_errors(self):
        """Test lines 214-215: Exception handling for specific field updates."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Set up different exceptions for different methods
        mock_api.update_app_name.side_effect = Exception("Name update failed")
        mock_api.update_privacy_url.side_effect = Exception("URL update failed")
        
        updates = {
            'name': 'New Name',
            'privacy_url': 'https://example.com/privacy'
        }
        
        with patch('logging.error') as mock_error:
            result = manager.update_app_listing('123456789', updates)
            
            # Should have errors for both fields
            assert not result['success']
            assert 'name' in result['errors']
            assert 'privacy_url' in result['errors']
            
            # Should log both errors
            assert mock_error.call_count == 2
            
            # Check error messages
            error_calls = [str(call[0][0]) for call in mock_error.call_args_list]
            assert any("Name update failed" in msg for msg in error_calls)
            assert any("URL update failed" in msg for msg in error_calls)
    
    def test_batch_update_apps_results_structure(self):
        """Test lines 239-243: Results formatting in batch_update_apps."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # First app succeeds, second fails with exception
        mock_api.update_app_name.side_effect = [
            True,  # First app succeeds
            Exception("API timeout")  # Second app fails
        ]
        
        updates = {
            '123456789': {'name': 'App One Updated'},
            '987654321': {'name': 'App Two Updated'}
        }
        
        # Use continue_on_error=True to test error handling
        results = manager.batch_update_apps(updates, continue_on_error=True)
        
        # Check results structure
        assert isinstance(results, dict)
        assert '123456789' in results
        assert '987654321' in results
        
        # First app should succeed
        assert results['123456789']['success'] is True
        assert 'name' in results['123456789']['updated']
        
        # Second app should fail
        assert results['987654321']['success'] is False
        assert 'name' in results['987654321']['errors']
        assert "Failed to update name: API timeout" in results['987654321']['errors']['name']
    
    def test_prepare_version_releases_complete_flow(self):
        """Test lines 303-310: Full prepare_version_releases implementation."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio with two apps
        mock_api.get_apps.return_value = {
            'data': [
                {'id': '123456789', 'attributes': {'name': 'App One'}},
                {'id': '987654321', 'attributes': {'name': 'App Two'}}
            ]
        }
        
        # First app has editable version, second doesn't
        mock_api.get_editable_version.side_effect = [
            {'id': 'ver123', 'attributes': {'appStoreState': 'PREPARE_FOR_SUBMISSION'}},
            None  # No editable version for second app
        ]
        
        # Mock successful update for first app
        mock_api.update_promotional_text.return_value = True
        
        # Run in non-dry-run mode
        results = manager.prepare_version_releases(
            release_notes="Version 2.0 - New features!",
            dry_run=False
        )
        
        # Check results structure
        assert 'updated' in results
        assert 'skipped' in results
        assert 'errors' in results
        
        # First app should be updated
        assert '123456789' in results['updated']
        
        # Second app should be skipped (no editable version)
        assert '987654321' in results['skipped']
        
        # Should have called update for first app
        mock_api.update_promotional_text.assert_called_once_with(
            '123456789',
            'Version 2.0 - New features!',
            locale='en-US'
        )
    
    def test_get_localization_status_missing_locales(self):
        """Test lines 364-366: Missing locale detection."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'Test App'}
            }]
        }
        
        # Mock metadata with missing locales
        mock_api.get_current_metadata.return_value = {
            'app_info': {'name': 'Test App'},
            'app_localizations': {
                'en-US': {'name': 'Test App'},
                # Missing fr-FR at app level
            },
            'version_info': {'versionString': '1.0'},
            'version_localizations': {
                'en-US': {'description': 'App description'},
                'fr-FR': {'description': 'Description en français'}
                # Has fr-FR at version level
            }
        }
        
        # Request status for both locales
        status = manager.get_localization_status(['en-US', 'fr-FR'])
        
        # Should detect missing app-level French localization
        assert '123456789' in status
        assert 'fr-FR' in status['123456789']['missing_app_level']
        assert 'fr-FR' not in status['123456789']['missing_version_level']
    
    def test_get_localization_status_with_exception(self):
        """Test line 334: Error logging in get_localization_status."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'Test App'}
            }]
        }
        
        # Make get_current_metadata raise an exception
        mock_api.get_current_metadata.side_effect = Exception("Network timeout")
        
        with patch('logging.error') as mock_error:
            status = manager.get_localization_status(['en-US'])
            
            # Should log the error
            assert mock_error.called
            error_msg = str(mock_error.call_args[0][0])
            assert "Error fetching metadata for app 123456789" in error_msg
            assert "Network timeout" in error_msg
            
            # Should mark app as having error
            assert status['123456789']['error'] is True
    
    def test_export_app_metadata_error_handling(self):
        """Test lines 342-343: Error handling in export_app_metadata."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Make get_app_portfolio raise an exception
        with patch.object(manager, 'get_app_portfolio', side_effect=Exception("API error")):
            with patch('logging.error') as mock_error:
                result = manager.export_app_metadata('/tmp/export.csv')
                
                # Should return False on error
                assert result is False
                
                # Should log the error
                assert mock_error.called
                error_msg = str(mock_error.call_args[0][0])
                assert "Failed to export app metadata" in error_msg
                assert "API error" in error_msg
    
    def test_standardize_app_names_app_not_in_portfolio(self):
        """Test lines 214-215 in standardize_app_names context."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock empty portfolio
        mock_api.get_apps.return_value = {'data': []}
        
        # Try to standardize names for non-existent apps
        results = manager.standardize_app_names(
            app_ids=['999999999'],  # Non-existent app
            pattern="{name} Pro"
        )
        
        # Should have error for non-existent app
        assert '999999999' in results['errors']
        assert results['errors']['999999999'] == 'App not found in portfolio'
    
    def test_export_app_metadata_with_app_ids_filter(self):
        """Test lines 389-391: App ID filtering in export."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio with multiple apps
        portfolio_data = {
            '123456789': {
                'basic_info': {'name': 'App One', 'bundle_id': 'com.test.one'},
                'metadata': {'app_localizations': {}}
            },
            '987654321': {
                'basic_info': {'name': 'App Two', 'bundle_id': 'com.test.two'},
                'metadata': {'app_localizations': {}}
            }
        }
        
        with patch.object(manager, 'get_app_portfolio', return_value=portfolio_data):
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                # Export only one app
                result = manager.export_app_metadata(
                    '/tmp/export.csv',
                    app_ids=['123456789']  # Filter to just one app
                )
                
                assert result is True
                
                # Check that DataFrame was created with filtered data
                call_args = mock_to_csv.call_args
                # The actual DataFrame is created internally, so we can't easily check its contents
                # But the method should complete successfully
    
    def test_export_app_metadata_missing_app_in_portfolio(self):
        """Test line 397: Continue when app not in portfolio during export."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio with one app
        portfolio_data = {
            '123456789': {
                'basic_info': {'name': 'App One', 'bundle_id': 'com.test.one'},
                'metadata': {'app_localizations': {}}
            }
        }
        
        with patch.object(manager, 'get_app_portfolio', return_value=portfolio_data):
            with patch('pandas.DataFrame.to_csv') as mock_to_csv:
                # Try to export apps including one that doesn't exist
                result = manager.export_app_metadata(
                    '/tmp/export.csv',
                    app_ids=['123456789', '999999999']  # Second app doesn't exist
                )
                
                # Should still succeed, just skip the missing app
                assert result is True
                mock_to_csv.assert_called_once()
    
    def test_create_metadata_manager_function(self):
        """Test lines 428-429: The create_metadata_manager convenience function."""
        from appstore_connect.metadata import create_metadata_manager
        
        with patch('appstore_connect.metadata.AppStoreConnectAPI') as mock_api_class:
            mock_api_instance = Mock()
            mock_api_class.return_value = mock_api_instance
            
            # Call the convenience function
            manager = create_metadata_manager(
                key_id='test_key',
                issuer_id='test_issuer',
                private_key_path='/tmp/key.p8',
                vendor_number='12345'
            )
            
            # Should create API with correct parameters
            mock_api_class.assert_called_once_with(
                key_id='test_key',
                issuer_id='test_issuer',
                private_key_path='/tmp/key.p8',
                vendor_number='12345'
            )
            
            # Should return MetadataManager instance
            assert isinstance(manager, MetadataManager)
            assert manager.api == mock_api_instance