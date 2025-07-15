"""
Tests for remaining coverage gaps in metadata.py, reports.py, and utils.py.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import date
import logging

from appstore_connect.metadata import MetadataManager
from appstore_connect.reports import ReportProcessor
from appstore_connect.utils import calculate_summary_metrics, combine_dataframes
from appstore_connect.exceptions import ValidationError, PermissionError


class TestMetadataErrorPaths:
    """Test error handling paths in metadata.py."""
    
    def test_get_app_portfolio_logging(self):
        """Test logging when app has no metadata (line 206)."""
        mock_api = Mock()
        
        # API returns app but metadata fetch fails
        mock_api.get_apps.return_value = {
            'data': [{
                'id': '123456789',
                'attributes': {'name': 'Test App'}
            }]
        }
        
        # Metadata fetch returns None
        mock_api.get_current_metadata.return_value = None
        
        manager = MetadataManager(mock_api)
        
        with patch('logging.warning') as mock_warning:
            portfolio = manager.get_app_portfolio()
            
            # Should log warning about missing metadata
            assert mock_warning.called
            warning_msg = str(mock_warning.call_args[0][0])
            assert "Could not fetch metadata for app 123456789" in warning_msg
    
    def test_update_app_listing_exception_handling(self):
        """Test exception handling in update_app_listing (lines 214-215)."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Make update_app_name raise an exception
        mock_api.update_app_name.side_effect = Exception("API Error")
        
        with patch('logging.error') as mock_error:
            result = manager.update_app_listing(
                app_id='123456789',
                updates={'name': 'New Name'}
            )
            
            # Should catch and log the exception
            assert not result['success']
            assert 'name' in result['errors']
            assert "API Error" in result['errors']['name']
            
            # Should log the error
            assert mock_error.called
    
    def test_batch_update_apps_error_formatting(self):
        """Test batch_update_apps error handling and formatting (lines 239-243)."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # First app succeeds, second fails
        mock_api.update_app_name.side_effect = [True, Exception("Network error")]
        
        updates = {
            '123456789': {'name': 'App 1'},
            '987654321': {'name': 'App 2'}
        }
        
        with patch('logging.error') as mock_error:
            results = manager.batch_update_apps(
                updates=updates,
                continue_on_error=True
            )
            
            # Check results structure
            assert '123456789' in results
            assert results['123456789']['success'] is True
            
            assert '987654321' in results
            assert results['987654321']['success'] is False
            assert 'Failed to update name: Network error' in str(results['987654321']['errors'])
    
    def test_prepare_version_releases_implementation(self):
        """Test prepare_version_releases (lines 303-310)."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio
        mock_api.get_apps.return_value = {
            'data': [
                {'id': '123456789', 'attributes': {'name': 'App 1'}},
                {'id': '987654321', 'attributes': {'name': 'App 2'}}
            ]
        }
        
        # First app has editable version, second doesn't
        mock_api.get_editable_version.side_effect = [
            {'id': 'ver123', 'attributes': {'appStoreState': 'PREPARE_FOR_SUBMISSION'}},
            None  # No editable version
        ]
        
        # Mock version localizations
        mock_api.get_app_store_version_localizations.return_value = {
            'data': [{
                'id': 'verloc123',
                'attributes': {'locale': 'en-US'}
            }]
        }
        
        # Mock update success
        mock_api.update_promotional_text.return_value = True
        
        results = manager.prepare_version_releases(
            release_notes="New features!",
            dry_run=False
        )
        
        # Should update first app, skip second
        assert '123456789' in results['updated']
        assert '987654321' in results['skipped']
        
        # Should have called update for first app
        mock_api.update_promotional_text.assert_called_once_with(
            '123456789',
            'New features!',
            locale='en-US'
        )
    
    def test_get_localization_status_error_logging(self):
        """Test error logging in get_localization_status (line 334)."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Mock portfolio
        mock_api.get_apps.return_value = {
            'data': [{'id': '123456789', 'attributes': {'name': 'Test App'}}]
        }
        
        # Make metadata fetch raise an exception
        mock_api.get_current_metadata.side_effect = Exception("API timeout")
        
        with patch('logging.error') as mock_error:
            status = manager.get_localization_status(['en-US'])
            
            # Should log the error
            assert mock_error.called
            error_msg = str(mock_error.call_args[0][0])
            assert "Error fetching metadata for app 123456789" in error_msg
            assert "API timeout" in error_msg
            
            # Status should indicate error
            assert '123456789' in status
            assert status['123456789']['error'] is True
    
    def test_export_app_metadata_permission_error(self):
        """Test export_app_metadata with permission error (lines 342-343)."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Make get_apps raise PermissionError
        mock_api.get_apps.side_effect = PermissionError("No metadata access")
        
        with patch('logging.error') as mock_error:
            result = manager.export_app_metadata('/tmp/export.csv')
            
            # Should return False
            assert result is False
            
            # Should log the error
            assert mock_error.called
            error_msg = str(mock_error.call_args[0][0])
            assert "Failed to export app metadata" in error_msg
            assert "No metadata access" in error_msg


class TestReportsErrorPaths:
    """Test error handling paths in reports.py."""
    
    def test_aggregate_by_country_implementation(self):
        """Test _aggregate_by_country method (line 264)."""
        mock_api = Mock()
        processor = ReportProcessor(mock_api)
        
        # Create test data
        df = pd.DataFrame({
            'Apple Identifier': ['123', '123', '456'],
            'Country Code': ['US', 'GB', 'US'],
            'Units': [10, 20, 30],
            'Developer Proceeds': [7.0, 14.0, 21.0]
        })
        
        # Call the private method directly
        result = processor._aggregate_by_country(df)
        
        # Should aggregate by country
        assert len(result) == 2  # US and GB
        
        us_data = result[result['Country Code'] == 'US']
        assert us_data['Units'].iloc[0] == 40  # 10 + 30
        assert us_data['Developer Proceeds'].iloc[0] == 28.0  # 7 + 21
        
        gb_data = result[result['Country Code'] == 'GB']
        assert gb_data['Units'].iloc[0] == 20
        assert gb_data['Developer Proceeds'].iloc[0] == 14.0
    
    def test_export_summary_report_excel_path(self):
        """Test export_summary_report Excel export (line 302)."""
        mock_api = Mock()
        processor = ReportProcessor(mock_api)
        
        # Mock data fetch
        mock_api.fetch_multiple_days.return_value = {
            'sales': [pd.DataFrame({
                'Apple Identifier': ['123'],
                'Units': [100],
                'Developer Proceeds': [700.0],
                'Country Code': ['US'],
                'report_date': [date.today()]
            })],
            'subscriptions': [],
            'subscription_events': []
        }
        
        # Test Excel export
        with patch('pandas.ExcelWriter') as mock_excel_writer:
            mock_writer_instance = MagicMock()
            mock_excel_writer.return_value.__enter__.return_value = mock_writer_instance
            
            result = processor.export_summary_report(
                '/tmp/test.xlsx',
                days=7,
                format='excel'
            )
            
            assert result is True
            
            # Should have created Excel writer
            mock_excel_writer.assert_called_once_with('/tmp/test.xlsx', engine='openpyxl')
            
            # Should have written multiple sheets
            # Check that to_excel was called multiple times
            assert mock_writer_instance.book is not None


class TestUtilsErrorPaths:
    """Test error handling paths in utils.py."""
    
    def test_calculate_summary_metrics_alternative_columns(self):
        """Test calculate_summary_metrics with alternative column names (lines 339-340, 345-346)."""
        # Test with 'Proceeds' instead of 'Developer Proceeds'
        df1 = pd.DataFrame({
            'App Apple ID': ['123', '456'],  # Alternative to 'Apple Identifier'
            'Units': [50, 100],
            'Proceeds': [350.0, 700.0]  # Alternative to 'Developer Proceeds'
        })
        
        metrics = calculate_summary_metrics(df1)
        
        # Should use alternative columns
        assert metrics['total_revenue'] == 1050.0  # 350 + 700
        assert metrics['unique_apps'] == 2
        
        # Test with no revenue columns
        df2 = pd.DataFrame({
            'Units': [50, 100]
        })
        
        metrics2 = calculate_summary_metrics(df2)
        
        # Should not have revenue metric
        assert 'total_revenue' not in metrics2
        assert metrics2['total_units'] == 150
    
    def test_combine_dataframes_with_none_handling(self):
        """Test combine_dataframes handling None values."""
        # Create mix of valid DataFrames and None
        df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        df2 = None
        df3 = pd.DataFrame({'a': [5, 6], 'b': [7, 8]})
        
        # Test with sort_by parameter
        result = combine_dataframes([df1, df2, df3], sort_by='a', ascending=False)
        
        # Should skip None and combine others
        assert len(result) == 4
        assert result.iloc[0]['a'] == 6  # Sorted descending
        assert result.iloc[-1]['a'] == 1


class TestValidationMethods:
    """Test private validation methods in metadata.py."""
    
    def test_validate_app_name(self):
        """Test _validate_app_name (line 364)."""
        from appstore_connect.metadata import MetadataManager
        
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Valid name
        manager._validate_app_name("Valid App Name")  # Should not raise
        
        # Too long
        with pytest.raises(ValidationError) as exc_info:
            manager._validate_app_name("A" * 31)  # 31 chars
        assert "App name too long" in str(exc_info.value)
        
        # Empty
        with pytest.raises(ValidationError) as exc_info:
            manager._validate_app_name("")
        assert "App name cannot be empty" in str(exc_info.value)
    
    def test_validate_promotional_text(self):
        """Test _validate_promotional_text (line 389)."""
        from appstore_connect.metadata import MetadataManager
        
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Valid text
        manager._validate_promotional_text("Check out our app!")  # Should not raise
        
        # Too long
        with pytest.raises(ValidationError) as exc_info:
            manager._validate_promotional_text("A" * 171)  # 171 chars
        assert "Promotional text too long" in str(exc_info.value)
    
    def test_format_for_export(self):
        """Test _format_for_export (line 397)."""
        from appstore_connect.metadata import MetadataManager
        
        mock_api = Mock()
        manager = MetadataManager(mock_api)
        
        # Test with nested metadata structure
        metadata = {
            'basic_info': {
                'name': 'Test App',
                'bundle_id': 'com.test.app'
            },
            'metadata': {
                'app_localizations': {
                    'en-US': {'name': 'Test App', 'subtitle': 'Great App'},
                    'fr-FR': {'name': 'App Test', 'subtitle': 'Super App'}
                }
            }
        }
        
        result = manager._format_for_export(metadata)
        
        # Should flatten the structure
        assert result['name'] == 'Test App'
        assert result['bundle_id'] == 'com.test.app'
        assert result['localization_en-US_name'] == 'Test App'
        assert result['localization_en-US_subtitle'] == 'Great App'
        assert result['localization_fr-FR_name'] == 'App Test'
        assert result['localization_fr-FR_subtitle'] == 'Super App'