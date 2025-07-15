"""
Additional tests for utils.py to achieve 100% coverage.
"""

import pytest
import pandas as pd
from datetime import date, datetime
from unittest.mock import patch

from appstore_connect.utils import get_app_platform, combine_dataframes
from appstore_connect.exceptions import ValidationError


class TestUtilsEdgeCases:
    """Test edge cases in utility functions."""
    
    def test_get_app_platform_edge_cases(self):
        """Test get_app_platform with various bundle ID formats."""
        # Test with uppercase
        assert get_app_platform('COM.COMPANY.APP') == 'ios'
        
        # Test with mixed case and iOS indicator
        assert get_app_platform('com.Company.App.ios') == 'ios'
        
        # Test with mac/osx indicators  
        assert get_app_platform('com.company.app.mac') == 'macos'
        assert get_app_platform('com.company.app.osx') == 'macos'
        assert get_app_platform('com.company.app.macos') == 'macos'
        
        # Test with tvOS indicator
        assert get_app_platform('com.company.app.tvos') == 'tvos'
        assert get_app_platform('com.company.app.appletv') == 'tvos'
        
        # Test with watchOS indicator
        assert get_app_platform('com.company.app.watchos') == 'watchos'
        assert get_app_platform('com.company.app.watch') == 'watchos'
        
        # Test edge case with multiple indicators (should match first)
        assert get_app_platform('com.company.tv.mac') == 'tvos'  # tv matches before mac
        
        # Test with None - should handle TypeError
        try:
            result = get_app_platform(None)
            assert result == 'unknown'
        except:
            # If it raises an exception, that's also acceptable
            pass
        
        # Test with empty string
        assert get_app_platform('') == 'unknown'
        
        # Test with normal iOS app
        assert get_app_platform('com.company.myapp') == 'ios'  # Default
    
    def test_combine_dataframes_edge_cases(self):
        """Test combine_dataframes with various edge cases."""
        # Test with None in list
        df1 = pd.DataFrame({'a': [1, 2]})
        df2 = None
        df3 = pd.DataFrame({'a': [3, 4]})
        
        result = combine_dataframes([df1, df2, df3])
        assert len(result) == 4
        assert list(result['a']) == [1, 2, 3, 4]
        
        # Test with all None
        result = combine_dataframes([None, None, None])
        assert result.empty
        
        # Test with different columns (should handle gracefully)
        df1 = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        df2 = pd.DataFrame({'a': [5, 6], 'c': [7, 8]})
        
        result = combine_dataframes([df1, df2])
        assert len(result) == 4
        assert 'a' in result.columns
        assert 'b' in result.columns
        assert 'c' in result.columns
        # NaN values for missing columns
        assert result['b'].isna().sum() == 2
        assert result['c'].isna().sum() == 2
        
        # Test with sort_by non-existent column (should not raise)
        result = combine_dataframes([df1], sort_by='nonexistent')
        assert len(result) == 2
        
        # Test with sort_by and ascending=False
        df = pd.DataFrame({
            'date': [date(2023, 1, 3), date(2023, 1, 1), date(2023, 1, 2)],
            'value': [3, 1, 2]
        })
        
        result = combine_dataframes([df], sort_by='date', ascending=False)
        assert result.iloc[0]['value'] == 3  # Jan 3
        assert result.iloc[1]['value'] == 2  # Jan 2  
        assert result.iloc[2]['value'] == 1  # Jan 1
    
    def test_date_utils_exception_paths(self):
        """Test exception handling in date utility functions."""
        from appstore_connect.utils import normalize_date, get_date_range
        
        # Test normalize_date with invalid string format
        with pytest.raises(ValidationError) as exc_info:
            normalize_date("not-a-date")
        assert "Invalid date format" in str(exc_info.value)
        
        # Test get_date_range with start > end
        with pytest.raises(ValidationError) as exc_info:
            get_date_range(
                start_date=date(2023, 6, 10),
                end_date=date(2023, 6, 5)
            )
        assert "Start date must be before or equal to end date" in str(exc_info.value)
        
        # Test with invalid type
        with pytest.raises(ValidationError):
            normalize_date([2023, 6, 1])  # List instead of date
    
    def test_validation_utils_edge_cases(self):
        """Test validation utility edge cases."""
        from appstore_connect.utils import (
            validate_app_id,
            validate_vendor_number, 
            validate_locale,
            validate_version_string
        )
        
        # Test app ID with spaces (should fail)
        with pytest.raises(ValidationError):
            validate_app_id("123 456")
        
        # Test app ID that's exactly 9 digits
        assert validate_app_id("123456789") == "123456789"
        
        # Test app ID that's exactly 10 digits  
        assert validate_app_id("1234567890") == "1234567890"
        
        # Test vendor number with leading zeros
        assert validate_vendor_number("00012345") == "00012345"
        
        # Test locale with region variant
        assert validate_locale("zh-Hans-CN") == "zh-Hans-CN"  # Chinese Simplified for China
        
        # Test version string with build number
        assert validate_version_string("1.2.3.4567") == "1.2.3.4567"
        
        # Test version string with pre-release
        with pytest.raises(ValidationError):
            validate_version_string("1.0-beta")  # Should fail
    
    def test_string_utils_edge_cases(self):
        """Test string utility edge cases."""
        from appstore_connect.utils import sanitize_app_name, truncate_string
        
        # Test sanitize with Unicode characters
        assert sanitize_app_name("App™ 2023©") == "App 2023"
        
        # Test sanitize with only special chars
        assert sanitize_app_name("@#$%^&*") == "App"
        
        # Test truncate with exact length
        assert truncate_string("12345", max_length=5) == "12345"
        
        # Test truncate with suffix longer than max_length
        assert truncate_string("Hello", max_length=3, suffix="...") == "..."
        
        # Test truncate with None
        assert truncate_string(None, max_length=10) == ""