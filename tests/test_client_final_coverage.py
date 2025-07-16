"""
Final tests to achieve 100% coverage in client.py.
"""

import pytest
import pandas as pd
from datetime import date
from unittest.mock import Mock, patch

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import (
    AppStoreConnectError,
)


@pytest.fixture
def api_client():
    """Create test API client."""
    with patch("pathlib.Path.exists", return_value=True):
        return AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test.p8",
            vendor_number="12345",
        )


class TestRemainingClientCoverage:
    """Test the final uncovered lines in client.py."""

    def test_fetch_multiple_days_with_dates_override(self, api_client):
        """Test line 335: Both start_date and end_date provided."""
        start = date(2023, 6, 1)
        end = date(2023, 6, 3)

        # Create mock response
        mock_df = pd.DataFrame({"Units": [10]})
        expected_results = {
            "sales": [mock_df],
            "subscriptions": [],
            "subscription_events": [],
        }

        with patch.object(
            api_client, "_fetch_date_range", return_value=expected_results
        ) as mock_fetch:
            # Call with all three parameters
            results = api_client.fetch_multiple_days(
                days=99,  # This should be completely ignored
                start_date=start,
                end_date=end,
            )

            # Should call _fetch_date_range, not _fetch_multiple_days_optimized
            mock_fetch.assert_called_once_with(start, end)
            assert results == expected_results

    def test_fetch_date_range_with_non_404_errors(self, api_client):
        """Test lines 353-355: Logging non-404 errors in _fetch_date_range."""
        start_date = date(2023, 6, 1)
        end_date = date(2023, 6, 1)

        # Create a mock that raises AppStoreConnectError with non-404 message
        def mock_get_sales_report(report_date, report_type="SALES", *args, **kwargs):
            if report_type == "SUBSCRIPTION":
                # Simulate a 500 error
                raise AppStoreConnectError("API Error 500: Internal Server Error")
            else:
                return pd.DataFrame({"Units": [5]})

        with patch.object(api_client, "get_sales_report", side_effect=mock_get_sales_report):
            with patch("logging.warning") as mock_warning:
                results = api_client._fetch_date_range(start_date, end_date)

                # Should have some results (SALES worked)
                assert len(results["sales"]) == 1

                # Should log the 500 error
                assert mock_warning.called
                # Check that we logged the non-404 error
                logged = False
                for call in mock_warning.call_args_list:
                    msg = str(call[0][0])
                    if "Error fetching SUBSCRIPTION" in msg and "500" in msg:
                        logged = True
                        break
                assert logged, "500 error was not logged"

    def test_fetch_multiple_days_optimized_weekly_errors(self, api_client):
        """Test lines 424-425: Weekly fetch error logging."""
        # Need to trigger weekly fetching (days > 7)
        # Mock current date to control the date range
        with patch("appstore_connect.client.datetime") as mock_datetime:
            # Set current date
            from datetime import timezone, datetime

            mock_now = datetime(2023, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = mock_now
            mock_datetime.datetime = datetime

            # Daily calls counter
            daily_call_count = 0

            def mock_get_sales_report(
                report_date,
                report_type="SALES",
                report_subtype="SUMMARY",
                frequency="DAILY",
            ):
                nonlocal daily_call_count

                if frequency == "DAILY":
                    daily_call_count += 1
                    # Return data for daily calls
                    return pd.DataFrame(
                        {
                            "Units": [10],
                            "report_date": [report_date],
                            "frequency": ["DAILY"],
                        }
                    )
                elif frequency == "WEEKLY":
                    # Fail on weekly calls
                    raise Exception("Weekly API is down")

                return pd.DataFrame()

            with patch.object(api_client, "get_sales_report", side_effect=mock_get_sales_report):
                with patch("logging.warning") as mock_warning:
                    # Request 14 days to trigger both daily and weekly fetching
                    results = api_client._fetch_multiple_days_optimized(days=14)

                    # Should have daily results
                    assert len(results["sales"]) > 0

                    # Should have logged weekly error
                    weekly_error_logged = False
                    for call in mock_warning.call_args_list:
                        msg = str(call[0][0])
                        if "Error fetching weekly data" in msg and "Weekly API is down" in msg:
                            weekly_error_logged = True
                            break

                    assert weekly_error_logged, "Weekly error was not logged"

    def test_get_current_metadata_permission_errors_in_app_info(self, api_client):
        """Test lines 741-742: PermissionError handling in app info section."""
        # First call succeeds (get_app_info)
        app_info_response = Mock()
        app_info_response.status_code = 200
        app_info_response.json.return_value = {
            "data": {"attributes": {"name": "Test App", "bundleId": "com.test.app"}}
        }

        # Second call raises PermissionError (get_app_localizations)
        app_infos_error = Mock()
        app_infos_error.status_code = 403

        # Third call succeeds (get_app_store_versions)
        versions_response = Mock()
        versions_response.status_code = 200
        versions_response.json.return_value = {
            "data": [{"id": "version123", "attributes": {"versionString": "1.0.0"}}]
        }

        # Fourth call succeeds (get_app_store_version_localizations)
        version_localizations_response = Mock()
        version_localizations_response.status_code = 200
        version_localizations_response.json.return_value = {
            "data": [{"attributes": {"locale": "en-US", "description": "Test description"}}]
        }

        responses = [
            app_info_response,
            app_infos_error,
            versions_response,
            version_localizations_response,
        ]

        with patch.object(api_client, "_make_request", side_effect=responses):
            metadata = api_client.get_current_metadata("123456")

            # Should have partial data
            assert metadata["app_info"]["name"] == "Test App"
            # Should have empty localizations due to permission error
            assert metadata["app_localizations"] == {}
            # Should have version info
            assert metadata["version_info"]["versionString"] == "1.0.0"
            # Should have version localizations
            assert "en-US" in metadata["version_localizations"]

    def test_get_current_metadata_not_found_in_versions(self, api_client):
        """Test lines 759-760: NotFoundError handling in version section."""
        # Set up successful responses until versions
        responses = [
            # get_app_info succeeds
            Mock(status_code=200, json=lambda: {"data": {"attributes": {"name": "App"}}}),
            # get_app_infos succeeds
            Mock(status_code=200, json=lambda: {"data": [{"id": "info123"}]}),
            # get_app_info_localizations succeeds
            Mock(
                status_code=200,
                json=lambda: {"data": [{"attributes": {"locale": "en-US", "name": "App Name"}}]},
            ),
            # get_app_store_versions succeeds with data
            Mock(
                status_code=200,
                json=lambda: {"data": [{"id": "ver123", "attributes": {"versionString": "1.0"}}]},
            ),
            # get_app_store_version_localizations raises NotFoundError
            Mock(status_code=404),
        ]

        with patch.object(api_client, "_make_request", side_effect=responses):
            metadata = api_client.get_current_metadata("123456")

            # Should have app data and version info
            assert metadata["app_info"]["name"] == "App"
            assert "en-US" in metadata["app_localizations"]
            assert metadata["version_info"]["versionString"] == "1.0"
            # But version localizations should be empty due to 404
            assert metadata["version_localizations"] == {}

    def test_get_current_metadata_permission_error_in_versions(self, api_client):
        """Test line 759: PermissionError in version fetching."""
        responses = [
            # get_app_info succeeds
            Mock(
                status_code=200,
                json=lambda: {"data": {"attributes": {"sku": "APP123"}}},
            ),
            # get_app_infos succeeds
            Mock(status_code=200, json=lambda: {"data": [{"id": "info123"}]}),
            # get_app_info_localizations succeeds
            Mock(status_code=200, json=lambda: {"data": []}),
            # get_app_store_versions fails with permission error
            Mock(status_code=403),
        ]

        with patch.object(api_client, "_make_request", side_effect=responses):
            metadata = api_client.get_current_metadata("123456")

            # Should have app info but no version data
            assert metadata["app_info"]["sku"] == "APP123"
            assert metadata["version_info"] == {}
            assert metadata["version_localizations"] == {}


class TestReportsAlternativeColumns:
    """Test alternative column handling in reports/utils."""

    def test_calculate_summary_metrics_with_proceeds_column(self):
        """Test lines 339-340: Using 'Proceeds' instead of 'Developer Proceeds'."""
        from appstore_connect.utils import calculate_summary_metrics

        # Create DataFrame with 'Proceeds' column (alternative to 'Developer Proceeds')
        df = pd.DataFrame(
            {
                "Units": [50, 100],
                "Proceeds": [350.0, 700.0],  # Alternative column name
                "Country Code": ["US", "GB"],
            }
        )

        metrics = calculate_summary_metrics(df)

        # Should use the alternative column
        assert metrics["total_revenue"] == 1050.0
        assert metrics["total_units"] == 150
        assert metrics["countries"] == 2

    def test_calculate_summary_metrics_with_app_apple_id(self):
        """Test lines 345-346: Using 'App Apple ID' instead of 'Apple Identifier'."""
        from appstore_connect.utils import calculate_summary_metrics

        # Create DataFrame with 'App Apple ID' (alternative to 'Apple Identifier')
        df = pd.DataFrame(
            {
                "App Apple ID": ["123456", "123456", "789012"],  # Alternative column
                "Units": [10, 20, 30],
            }
        )

        metrics = calculate_summary_metrics(df)

        # Should count unique apps using alternative column
        assert metrics["unique_apps"] == 2  # Two unique app IDs
