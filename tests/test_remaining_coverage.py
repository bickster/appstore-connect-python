"""
Tests for remaining coverage gaps in metadata.py, reports.py, and utils.py.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from datetime import date

from appstore_connect.metadata import MetadataManager
from appstore_connect.reports import ReportProcessor
from appstore_connect.utils import calculate_summary_metrics, combine_dataframes
from appstore_connect.exceptions import ValidationError


class TestMetadataErrorPaths:
    """Test error handling paths in metadata.py."""

    def test_get_app_portfolio_with_none_metadata(self):
        """Test when metadata fetch returns None."""
        mock_api = Mock()

        # API returns app but metadata fetch returns None
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "Test App",
                        "bundleId": "com.test.app",
                        "sku": "APP123",
                        "primaryLocale": "en-US",
                    },
                }
            ]
        }

        # Metadata fetch returns None
        mock_api.get_current_metadata.return_value = None
        mock_api.get_editable_version.return_value = None

        manager = MetadataManager(mock_api)
        portfolio = manager.get_app_portfolio()

        # Should still return the app with None metadata
        assert len(portfolio) == 1
        assert portfolio[0]["id"] == "123456789"
        assert portfolio[0]["metadata"] is None

    def test_update_app_listing_exception_handling(self):
        """Test exception handling in update_app_listing."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Make update_app_name raise an exception
        mock_api.update_app_name.side_effect = Exception("API Error")

        result = manager.update_app_listing(
            app_id="123456789", updates={"name": "New Name"}
        )

        # Should catch and handle the exception
        assert result["success"] is False
        assert "name" in result["errors"]
        assert result["errors"]["name"] == "Update failed"

    def test_batch_update_apps_error_formatting(self):
        """Test batch_update_apps error handling and formatting (lines 239-243)."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # First app succeeds, second fails
        mock_api.update_app_name.side_effect = [True, Exception("Network error")]

        updates = {"123456789": {"name": "App 1"}, "987654321": {"name": "App 2"}}

        with patch("logging.error") as mock_error:
            results = manager.batch_update_apps(updates=updates, continue_on_error=True)

            # Verify error logging was called
            assert mock_error.called
            # Check that error message contains app ID
            error_msg = str(mock_error.call_args[0][0])
            assert "987654321" in error_msg

            # Check results structure
            assert "results" in results
            assert "123456789" in results["results"]
            assert results["results"]["123456789"]["success"] is True

            assert "987654321" in results["results"]
            assert results["results"]["987654321"]["success"] is False
            assert "name" in results["results"]["987654321"]["errors"]

    def test_prepare_version_releases_with_release_notes(self):
        """Test prepare_version_releases with release notes parameter."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Mock get_apps to return apps
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "App 1",
                        "bundleId": "com.test.app1",
                        "sku": "APP1",
                        "primaryLocale": "en-US",
                    },
                },
                {
                    "id": "987654321",
                    "attributes": {
                        "name": "App 2",
                        "bundleId": "com.test.app2",
                        "sku": "APP2",
                        "primaryLocale": "en-US",
                    },
                },
            ]
        }
        mock_api.get_current_metadata.return_value = {}

        # First app has editable version, second doesn't
        mock_api.get_editable_version.side_effect = [
            {
                "id": "ver123",
                "attributes": {
                    "versionString": "1.0",
                    "appStoreState": "PREPARE_FOR_SUBMISSION",
                },
            },
            None,  # For second app in portfolio
            {
                "id": "ver123",
                "attributes": {
                    "versionString": "1.0",
                    "appStoreState": "PREPARE_FOR_SUBMISSION",
                },
            },  # For version check
            None,  # For second app version check
        ]

        # Mock get_app_store_versions to return empty (no existing versions)
        mock_api.get_app_store_versions.return_value = {"data": []}

        # Mock version creation
        mock_api.create_app_store_version.return_value = {
            "data": {"id": "new_version_123"}
        }

        # Test with no app_versions provided (should auto-generate)
        results = manager.prepare_version_releases(
            release_notes="New features!", dry_run=False
        )

        # Should have one app updated and one skipped
        assert len(results["updated"]) == 1
        assert len(results["skipped"]) == 1
        assert "123456789" in results["updated"]
        assert "987654321" in results["skipped"]

    def test_get_localization_status_with_missing_locales(self):
        """Test get_localization_status correctly identifies missing localizations."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Mock portfolio
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "Test App",
                        "bundleId": "com.test.app",
                        "sku": "APP123",
                        "primaryLocale": "en-US",
                    },
                }
            ]
        }

        # Mock metadata with localizations
        mock_api.get_current_metadata.return_value = {
            "app_localizations": {
                "en-US": {"name": "Test App"},
                "fr-FR": {"name": "App Test"},
            },
            "version_localizations": {"en-US": {"description": "Test"}},
        }
        mock_api.get_editable_version.return_value = None

        # Pass app IDs
        status = manager.get_localization_status(["123456789"])

        # Should return status for the app
        assert "123456789" in status
        assert set(status["123456789"]["app_level_locales"]) == {"en-US", "fr-FR"}
        assert status["123456789"]["version_level_locales"] == ["en-US"]
        assert "fr-FR" in status["123456789"]["missing_version_level"]

    def test_export_app_metadata_general_error(self):
        """Test export_app_metadata with general error."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Make get_apps raise a general exception
        mock_api.get_apps.side_effect = Exception("API error")

        # Should return False and log error
        with patch("logging.error") as mock_error:
            result = manager.export_app_metadata("/tmp/export.csv")

        assert result is False
        assert mock_error.called


class TestReportsErrorPaths:
    """Test error handling paths in reports.py."""

    def test_aggregate_by_country_implementation(self):
        """Test _aggregate_by_country method (line 264)."""
        mock_api = Mock()
        processor = ReportProcessor(mock_api)

        # Create test data
        df = pd.DataFrame(
            {
                "Apple Identifier": ["123", "123", "456"],
                "Country Code": ["US", "GB", "US"],
                "Units": [10, 20, 30],
                "Developer Proceeds": [7.0, 14.0, 21.0],
            }
        )

        # Call the private method directly
        result = processor._aggregate_by_country(df)

        # Should aggregate by country
        assert len(result) == 2  # US and GB

        us_data = result[result["Country Code"] == "US"]
        assert us_data["Units"].iloc[0] == 40  # 10 + 30
        assert us_data["Developer Proceeds"].iloc[0] == 28.0  # 7 + 21

        gb_data = result[result["Country Code"] == "GB"]
        assert gb_data["Units"].iloc[0] == 20
        assert gb_data["Developer Proceeds"].iloc[0] == 14.0

    def test_export_summary_report_creates_csv(self):
        """Test export_summary_report creates CSV file."""
        mock_api = Mock()
        processor = ReportProcessor(mock_api)

        # Mock data fetch
        mock_api.fetch_multiple_days.return_value = {
            "sales": [
                pd.DataFrame(
                    {
                        "Apple Identifier": ["123"],
                        "Units": [100],
                        "Developer Proceeds": [700.0],
                        "Country Code": ["US"],
                        "report_date": [date.today()],
                    }
                )
            ],
            "subscriptions": [],
            "subscription_events": [],
        }

        # export_summary_report returns None (void)
        with patch("pandas.DataFrame.to_csv") as mock_to_csv:
            processor.export_summary_report("/tmp/test.csv", days=7)

            # Should have called to_csv
            mock_to_csv.assert_called_once()


class TestUtilsErrorPaths:
    """Test error handling paths in utils.py."""

    def test_calculate_summary_metrics_alternative_columns(self):
        """Test calculate_summary_metrics with alternative column names (lines 339-340, 345-346)."""
        # Test with 'Proceeds' instead of 'Developer Proceeds'
        df1 = pd.DataFrame(
            {
                "App Apple ID": ["123", "456"],  # Alternative to 'Apple Identifier'
                "Units": [50, 100],
                "Proceeds": [350.0, 700.0],  # Alternative to 'Developer Proceeds'
            }
        )

        metrics = calculate_summary_metrics(df1)

        # Should use alternative columns
        assert metrics["total_revenue"] == 1050.0  # 350 + 700
        assert metrics["unique_apps"] == 2

        # Test with no revenue columns
        df2 = pd.DataFrame({"Units": [50, 100]})

        metrics2 = calculate_summary_metrics(df2)

        # Should not have revenue metric
        assert "total_revenue" not in metrics2
        assert metrics2["total_units"] == 150

    def test_combine_dataframes_with_empty_dataframes(self):
        """Test combine_dataframes handling empty DataFrames."""
        # Create mix of valid and empty DataFrames
        df1 = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        df2 = pd.DataFrame()  # Empty DataFrame
        df3 = pd.DataFrame({"a": [5, 6], "b": [7, 8]})

        result = combine_dataframes([df1, df2, df3], sort_by="a")

        # Should skip empty and combine others
        assert len(result) == 4
        # Default sort is ascending
        assert result.iloc[0]["a"] == 1
        assert result.iloc[-1]["a"] == 6


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
        """Test _format_for_export method."""
        from appstore_connect.metadata import MetadataManager

        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Test with various data types
        data = {
            "name": "Test App",
            "is_active": True,
            "is_inactive": False,
            "tags": ["tag1", "tag2"],
            "metadata": {"key": "value"},
            "count": 42,
            "price": 9.99,
            "empty": None,
        }

        result = manager._format_for_export(data)

        # Check formatting
        assert result["name"] == "Test App"
        assert result["is_active"] == "Yes"  # Boolean True -> 'Yes'
        assert result["is_inactive"] == "No"  # Boolean False -> 'No'
        assert result["tags"] == "['tag1', 'tag2']"  # List -> string
        assert result["metadata"] == "{'key': 'value'}"  # Dict -> string
        assert result["count"] == 42  # Numbers stay as-is
        assert result["price"] == 9.99
        assert result["empty"] == ""  # None -> empty string
