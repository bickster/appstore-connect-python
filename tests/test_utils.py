"""
Tests for utility functions.
"""

import pytest
import pandas as pd
from datetime import date, datetime, timedelta

from appstore_connect.utils import (
    validate_app_id,
    validate_vendor_number,
    validate_locale,
    validate_version_string,
    normalize_date,
    get_date_range,
    validate_report_frequency,
    validate_report_type,
    validate_report_subtype,
    sanitize_app_name,
    combine_dataframes,
    calculate_summary_metrics,
    format_currency,
    truncate_string,
    chunk_list,
    get_app_platform
)
from appstore_connect.exceptions import ValidationError


class TestValidation:
    """Test validation functions."""
    
    def test_validate_app_id_valid(self):
        """Test valid app ID validation."""
        assert validate_app_id("123456789") == "123456789"
        assert validate_app_id("1234567890") == "1234567890"
        assert validate_app_id(123456789) == "123456789"
    
    def test_validate_app_id_invalid(self):
        """Test invalid app ID validation."""
        with pytest.raises(ValidationError):
            validate_app_id("")
        with pytest.raises(ValidationError):
            validate_app_id("12345678")  # Too short
        with pytest.raises(ValidationError):
            validate_app_id("12345678901")  # Too long
        with pytest.raises(ValidationError):
            validate_app_id("abcdefghi")  # Non-numeric
    
    def test_validate_vendor_number_valid(self):
        """Test valid vendor number validation."""
        assert validate_vendor_number("12345678") == "12345678"
        assert validate_vendor_number("123456789") == "123456789"
        assert validate_vendor_number(12345678) == "12345678"
    
    def test_validate_vendor_number_invalid(self):
        """Test invalid vendor number validation."""
        with pytest.raises(ValidationError):
            validate_vendor_number("")
        with pytest.raises(ValidationError):
            validate_vendor_number("1234567")  # Too short
        with pytest.raises(ValidationError):
            validate_vendor_number("1234567890")  # Too long
        with pytest.raises(ValidationError):
            validate_vendor_number("abcdefgh")  # Non-numeric
    
    def test_validate_locale_valid(self):
        """Test valid locale validation."""
        assert validate_locale("en-US") == "en-US"
        assert validate_locale("fr-FR") == "fr-FR"
        assert validate_locale("ja-JP") == "ja-JP"
    
    def test_validate_locale_invalid(self):
        """Test invalid locale validation."""
        with pytest.raises(ValidationError):
            validate_locale("")
        with pytest.raises(ValidationError):
            validate_locale("en")  # Missing country
        with pytest.raises(ValidationError):
            validate_locale("en_US")  # Wrong separator
        with pytest.raises(ValidationError):
            validate_locale("eng-US")  # Wrong language length
    
    def test_validate_version_string_valid(self):
        """Test valid version string validation."""
        assert validate_version_string("1.0.0") == "1.0.0"
        assert validate_version_string("2.1") == "2.1"
        assert validate_version_string("10.15.7") == "10.15.7"
    
    def test_validate_version_string_invalid(self):
        """Test invalid version string validation."""
        with pytest.raises(ValidationError):
            validate_version_string("")
        with pytest.raises(ValidationError):
            validate_version_string("1")  # Too simple
        with pytest.raises(ValidationError):
            validate_version_string("1.0.0.1")  # Too complex
        with pytest.raises(ValidationError):
            validate_version_string("v1.0.0")  # Has prefix
    
    def test_validate_report_frequency_valid(self):
        """Test valid report frequency validation."""
        assert validate_report_frequency("DAILY") == "DAILY"
        assert validate_report_frequency("weekly") == "WEEKLY"
        assert validate_report_frequency(" MONTHLY ") == "MONTHLY"
    
    def test_validate_report_frequency_invalid(self):
        """Test invalid report frequency validation."""
        with pytest.raises(ValidationError):
            validate_report_frequency("")
        with pytest.raises(ValidationError):
            validate_report_frequency("HOURLY")
    
    def test_validate_report_type_valid(self):
        """Test valid report type validation."""
        assert validate_report_type("SALES") == "SALES"
        assert validate_report_type("subscription") == "SUBSCRIPTION"
    
    def test_validate_report_type_invalid(self):
        """Test invalid report type validation."""
        with pytest.raises(ValidationError):
            validate_report_type("")
        with pytest.raises(ValidationError):
            validate_report_type("INVALID")
    
    def test_validate_report_subtype_valid(self):
        """Test valid report subtype validation."""
        assert validate_report_subtype("SUMMARY") == "SUMMARY"
        assert validate_report_subtype("detailed") == "DETAILED"
    
    def test_validate_report_subtype_invalid(self):
        """Test invalid report subtype validation."""
        with pytest.raises(ValidationError):
            validate_report_subtype("")
        with pytest.raises(ValidationError):
            validate_report_subtype("INVALID")


class TestDateHandling:
    """Test date handling functions."""
    
    def test_normalize_date_from_date(self):
        """Test normalizing from date object."""
        test_date = date(2023, 1, 15)
        assert normalize_date(test_date) == test_date
    
    def test_normalize_date_from_datetime(self):
        """Test normalizing from datetime object."""
        test_datetime = datetime(2023, 1, 15, 10, 30, 0)
        expected_date = date(2023, 1, 15)
        result = normalize_date(test_datetime)
        assert result == expected_date
        # Check that it's a date object, not datetime
        assert isinstance(result, date) and not isinstance(result, datetime)
    
    def test_normalize_date_from_string_iso(self):
        """Test normalizing from ISO string."""
        assert normalize_date("2023-01-15") == date(2023, 1, 15)
    
    def test_normalize_date_from_string_slash(self):
        """Test normalizing from slash string."""
        assert normalize_date("01/15/2023") == date(2023, 1, 15)
    
    def test_normalize_date_invalid(self):
        """Test normalizing invalid date."""
        with pytest.raises(ValidationError):
            normalize_date("invalid")
        with pytest.raises(ValidationError):
            normalize_date(123)
    
    def test_get_date_range(self):
        """Test date range generation."""
        end_date = date(2023, 1, 15)
        start_date, actual_end = get_date_range(7, end_date)
        
        assert actual_end == end_date
        assert start_date == date(2023, 1, 9)  # 7 days back
    
    def test_get_date_range_default_end(self):
        """Test date range with default end date."""
        start_date, end_date = get_date_range(5)
        expected_end = date.today() - timedelta(days=1)
        expected_start = expected_end - timedelta(days=4)
        
        assert end_date == expected_end
        assert start_date == expected_start
    
    def test_get_date_range_invalid(self):
        """Test date range with invalid days."""
        with pytest.raises(ValidationError):
            get_date_range(0)
        with pytest.raises(ValidationError):
            get_date_range(-1)


class TestStringUtils:
    """Test string utility functions."""
    
    def test_sanitize_app_name_normal(self):
        """Test sanitizing normal app name."""
        assert sanitize_app_name("My Great App") == "My_Great_App"
        assert sanitize_app_name("Health & Fitness") == "Health_Fitness"
    
    def test_sanitize_app_name_special_chars(self):
        """Test sanitizing app name with special characters."""
        assert sanitize_app_name("App@#$%^&*()Name") == "AppName"
        assert sanitize_app_name("Multi   Space   App") == "Multi_Space_App"
    
    def test_sanitize_app_name_empty(self):
        """Test sanitizing empty app name."""
        assert sanitize_app_name("") == "unnamed_app"
        assert sanitize_app_name("   ") == "unnamed_app"
    
    def test_sanitize_app_name_long(self):
        """Test sanitizing very long app name."""
        long_name = "A" * 100
        result = sanitize_app_name(long_name)
        assert len(result) <= 50
        assert result == "A" * 50
    
    def test_format_currency_usd(self):
        """Test USD currency formatting."""
        assert format_currency(1234.56) == "$1,234.56"
        assert format_currency(0) == "$0.00"
    
    def test_format_currency_other(self):
        """Test other currency formatting."""
        assert format_currency(1234.56, "EUR") == "1,234.56 EUR"
        assert format_currency(1000, "JPY") == "1,000.00 JPY"
    
    def test_truncate_string_normal(self):
        """Test normal string truncation."""
        assert truncate_string("Hello World", 5) == "He..."
        assert truncate_string("Short", 10) == "Short"
    
    def test_truncate_string_custom_suffix(self):
        """Test truncation with custom suffix."""
        assert truncate_string("Hello World", 5, ">>") == "Hel>>"
    
    def test_truncate_string_empty(self):
        """Test truncating empty string."""
        assert truncate_string("", 5) == ""
        assert truncate_string(None, 5) == None


class TestDataProcessing:
    """Test data processing functions."""
    
    def test_combine_dataframes_empty(self):
        """Test combining empty DataFrames."""
        result = combine_dataframes([])
        assert result.empty
        
        result = combine_dataframes([pd.DataFrame(), pd.DataFrame()])
        assert result.empty
    
    def test_combine_dataframes_normal(self):
        """Test combining normal DataFrames."""
        df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})
        
        result = combine_dataframes([df1, df2])
        
        assert len(result) == 4
        assert list(result['A']) == [1, 2, 5, 6]
    
    def test_combine_dataframes_with_sort(self):
        """Test combining DataFrames with sorting."""
        df1 = pd.DataFrame({'A': [2, 1], 'B': [4, 3]})
        df2 = pd.DataFrame({'A': [4, 3], 'B': [8, 7]})
        
        result = combine_dataframes([df1, df2], sort_by='A')
        
        assert len(result) == 4
        assert list(result['A']) == [1, 2, 3, 4]
    
    def test_calculate_summary_metrics_empty(self):
        """Test calculating metrics from empty DataFrame."""
        result = calculate_summary_metrics(pd.DataFrame())
        
        assert result['total_units'] == 0
        assert result['total_revenue'] == 0.0
        assert result['unique_apps'] == 0
    
    def test_calculate_summary_metrics_sales_data(self):
        """Test calculating metrics from sales DataFrame."""
        df = pd.DataFrame({
            'Units': [10, 20, 30],
            'Developer Proceeds': [1.0, 2.0, 3.0],
            'Apple Identifier': ['123', '456', '123'],
            'Country Code': ['US', 'US', 'CA']
        })
        
        result = calculate_summary_metrics(df)
        
        assert result['total_units'] == 60
        assert result['total_revenue'] == 6.0
        assert result['unique_apps'] == 2
        assert result['countries'] == 2
    
    def test_chunk_list_normal(self):
        """Test normal list chunking."""
        items = [1, 2, 3, 4, 5, 6, 7]
        chunks = chunk_list(items, 3)
        
        assert chunks == [[1, 2, 3], [4, 5, 6], [7]]
    
    def test_chunk_list_exact_division(self):
        """Test chunking with exact division."""
        items = [1, 2, 3, 4, 5, 6]
        chunks = chunk_list(items, 2)
        
        assert chunks == [[1, 2], [3, 4], [5, 6]]
    
    def test_chunk_list_invalid_size(self):
        """Test chunking with invalid size."""
        with pytest.raises(ValidationError):
            chunk_list([1, 2, 3], 0)
        with pytest.raises(ValidationError):
            chunk_list([1, 2, 3], -1)
    
    def test_get_app_platform(self):
        """Test platform detection from bundle ID."""
        assert get_app_platform("com.example.myapp") == "ios"
        assert get_app_platform("com.example.mac.myapp") == "macos"
        assert get_app_platform("com.example.tv.myapp") == "tvos"
        assert get_app_platform("com.example.watch.myapp") == "watchos"
        assert get_app_platform("") == "unknown"