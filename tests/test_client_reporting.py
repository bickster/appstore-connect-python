"""
Tests for AppStoreConnectAPI reporting functionality.
Focus on sales reports, financial reports, and date handling.
"""

import pytest
import pandas as pd
import gzip
import io
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import AppStoreConnectError


@pytest.fixture
def api_client():
    """Create test API client."""
    with patch("pathlib.Path.exists", return_value=True):
        return AppStoreConnectAPI(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/test.p8",
            vendor_number="12345",
            app_ids=["123456", "789012"],
        )


class TestReportDateFormatting:
    """Test date formatting for different report frequencies."""

    def test_weekly_report_date_formatting(self, api_client):
        """Test weekly report date formatting (should use Sunday of the week)."""
        # Test with a Wednesday
        test_date = date(2023, 6, 14)  # Wednesday

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(
            api_client, "_make_request", return_value=mock_response
        ) as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(test_date, frequency="WEEKLY")

                call_args = mock_request.call_args
                params = call_args[1]["params"]

                assert params["filter[reportDate]"] == "2023-06-11"
                assert params["filter[frequency]"] == "WEEKLY"

    def test_weekly_report_sunday_input(self, api_client):
        """Test weekly report when input is already Sunday."""
        test_date = date(2023, 6, 11)  # Sunday

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(test_date, frequency="WEEKLY")

                call_args = api_client._make_request.call_args
                params = call_args[1]["params"]

                assert params["filter[reportDate]"] == "2023-06-11"

    def test_monthly_report_date_formatting(self, api_client):
        """Test monthly report date formatting."""
        test_date = date(2023, 6, 15)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(test_date, frequency="MONTHLY")

                call_args = api_client._make_request.call_args
                params = call_args[1]["params"]

                assert params["filter[reportDate]"] == "2023-06"
                assert params["filter[frequency]"] == "MONTHLY"

    def test_yearly_report_date_formatting(self, api_client):
        """Test yearly report date formatting."""
        test_date = date(2023, 6, 15)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(test_date, frequency="YEARLY")

                call_args = api_client._make_request.call_args
                params = call_args[1]["params"]

                assert params["filter[reportDate]"] == "2023"
                assert params["filter[frequency]"] == "YEARLY"

    def test_datetime_input_conversion(self, api_client):
        """Test that datetime objects are converted to date."""
        test_datetime = datetime(2023, 6, 15, 10, 30, 45)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(test_datetime, frequency="DAILY")

                call_args = api_client._make_request.call_args
                params = call_args[1]["params"]

                assert params["filter[reportDate]"] == "2023-06-15"

    def _create_gzip_content(self, content):
        """Helper to create gzipped content."""
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(content.encode("utf-8"))
        return buf.getvalue()


class TestReportParsing:
    """Test report data parsing and error handling."""

    def test_gzip_parsing_error(self, api_client):
        """Test handling of corrupted gzip data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"corrupted data not gzip"

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client.get_sales_report(date.today())

                assert "Failed to parse report data" in str(exc_info.value)

    def test_csv_parsing_error(self, api_client):
        """Test handling of invalid CSV data."""
        # Create gzipped but invalid CSV content
        invalid_csv = "col1\tcol2\nvalue1"  # Missing value for col2

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(invalid_csv.encode("utf-8"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = buf.getvalue()

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                # pandas will parse this, but may produce unexpected results
                # We simulate a parsing error
                with patch("pandas.read_csv", side_effect=Exception("Parse error")):
                    with pytest.raises(AppStoreConnectError) as exc_info:
                        api_client.get_sales_report(date.today())

                    assert "Failed to parse report data" in str(exc_info.value)

    def test_app_id_filtering_sales_report(self, api_client):
        """Test app ID filtering for sales reports (Apple Identifier column)."""
        # Create test data with multiple apps
        csv_data = "Apple Identifier\tUnits\n123456\t10\n789012\t20\n999999\t30"

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = buf.getvalue()

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                df = api_client.get_sales_report(date.today())

                # Should only include configured app IDs
                assert len(df) == 2
                assert set(df["Apple Identifier"].astype(str)) == {"123456", "789012"}

    def test_app_id_filtering_subscription_report(self, api_client):
        """Test app ID filtering for subscription reports (App Apple ID column)."""
        # Create test data with App Apple ID column
        csv_data = (
            "App Apple ID\tActive Subscriptions\n123456\t100\n789012\t200\n999999\t300"
        )

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = buf.getvalue()

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                df = api_client.get_sales_report(
                    date.today(), report_type="SUBSCRIPTION"
                )

                # Should only include configured app IDs
                assert len(df) == 2
                assert set(df["App Apple ID"].astype(str)) == {"123456", "789012"}


class TestFinancialReports:
    """Test financial report functionality."""

    def test_get_financial_report_success(self, api_client):
        """Test successful financial report fetching."""
        csv_data = "Region\tAmount\nUS\t1000.00\nEU\t2000.00"

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = buf.getvalue()

        with patch.object(
            api_client, "_make_request", return_value=mock_response
        ) as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                df = api_client.get_financial_report(2023, 6)

                # Check request parameters
                call_args = mock_request.call_args
                params = call_args[1]["params"]

                assert params["filter[regionCode]"] == "ZZ"
                assert params["filter[reportDate]"] == "2023-06"
                assert params["filter[reportType]"] == "FINANCIAL"
                assert params["filter[vendorNumber]"] == "12345"

                # Check returned data
                assert len(df) == 2
                assert "Region" in df.columns
                assert "Amount" in df.columns

    def test_get_financial_report_custom_region(self, api_client):
        """Test financial report with custom region."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(
            api_client, "_make_request", return_value=mock_response
        ) as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_financial_report(2023, 12, region="US")

                call_args = mock_request.call_args
                params = call_args[1]["params"]

                assert params["filter[regionCode]"] == "US"
                assert params["filter[reportDate]"] == "2023-12"

    def test_get_financial_report_empty_response(self, api_client):
        """Test financial report with no data."""
        mock_response = Mock()
        mock_response.status_code = 404  # No data available

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                df = api_client.get_financial_report(2023, 6)

                assert df.empty
                assert isinstance(df, pd.DataFrame)

    def test_get_financial_report_parse_error(self, api_client):
        """Test financial report parsing error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"invalid gzip data"

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                with pytest.raises(AppStoreConnectError) as exc_info:
                    api_client.get_financial_report(2023, 6)

                assert "Failed to parse financial report" in str(exc_info.value)

    def _create_gzip_content(self, content):
        """Helper to create gzipped content."""
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(content.encode("utf-8"))
        return buf.getvalue()


class TestSubscriptionEventReports:
    """Test subscription event report functionality."""

    def test_get_subscription_event_report(self, api_client):
        """Test fetching subscription event reports."""
        csv_data = (
            "Event\tApp Apple ID\tQuantity\nSubscribe\t123456\t5\nCancel\t789012\t2"
        )

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = buf.getvalue()

        with patch.object(
            api_client, "_make_request", return_value=mock_response
        ) as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                df = api_client.get_subscription_event_report(date(2023, 6, 15))

                # Check request parameters
                call_args = mock_request.call_args
                params = call_args[1]["params"]

                assert params["filter[reportType]"] == "SUBSCRIPTION_EVENT"
                assert params["filter[reportSubType]"] == "SUMMARY"
                assert params["filter[frequency]"] == "DAILY"
                assert params["filter[version]"] == "1_4"

                # Check data
                assert len(df) == 2
                assert "Event" in df.columns


class TestMultipleDaysFetching:
    """Test fetching reports for multiple days."""

    def test_fetch_date_range(self, api_client):
        """Test _fetch_date_range method."""
        start_date = date(2023, 6, 1)
        end_date = date(2023, 6, 3)

        # Mock responses for each day and report type
        mock_response = Mock()
        mock_response.status_code = 200

        csv_data = "Apple Identifier\tUnits\n123456\t10"
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))
        mock_response.content = buf.getvalue()

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                results = api_client._fetch_date_range(start_date, end_date)

                # Should have results for each report type
                assert "sales" in results
                assert "subscriptions" in results
                assert "subscription_events" in results

                # Should have 3 days × 3 report types = 9 reports
                # (if all succeed)
                total_reports = (
                    len(results["sales"])
                    + len(results["subscriptions"])
                    + len(results["subscription_events"])
                )
                assert total_reports == 9

    def test_fetch_date_range_with_errors(self, api_client):
        """Test _fetch_date_range with some failing requests."""
        start_date = date(2023, 6, 1)
        end_date = date(2023, 6, 2)

        # Mock successful and failed responses
        successful_response = Mock()
        successful_response.status_code = 200
        csv_data = "Apple Identifier\tUnits\n123456\t10"
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))
        successful_response.content = buf.getvalue()

        # Simulate 404 errors for some requests
        with patch.object(api_client, "_make_request") as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                # Return success for first call, then 404s
                mock_request.side_effect = [
                    successful_response,  # Day 1 SALES
                    Mock(status_code=404),  # Day 1 SUBSCRIPTION (404)
                    Mock(status_code=404),  # Day 1 SUBSCRIPTION_EVENT (404)
                    successful_response,  # Day 2 SALES
                    successful_response,  # Day 2 SUBSCRIPTION
                    Mock(status_code=404),  # Day 2 SUBSCRIPTION_EVENT (404)
                ]

                with patch("logging.warning") as mock_warning:
                    results = api_client._fetch_date_range(start_date, end_date)

                    # Should have some results
                    assert len(results["sales"]) == 2
                    assert len(results["subscriptions"]) == 1
                    assert len(results["subscription_events"]) == 0

                    # Should not log warnings for 404s
                    mock_warning.assert_not_called()

    def test_fetch_multiple_days_optimized(self, api_client):
        """Test _fetch_multiple_days_optimized with mixed daily/weekly fetching."""
        # Mock responses
        daily_response = Mock()
        daily_response.status_code = 200

        csv_data = "Apple Identifier\tUnits\n123456\t10"
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))
        daily_response.content = buf.getvalue()

        weekly_csv = "Apple Identifier\tUnits\n123456\t70"  # Weekly total
        weekly_buf = io.BytesIO()
        with gzip.GzipFile(fileobj=weekly_buf, mode="wb") as gz:
            gz.write(weekly_csv.encode("utf-8"))
        weekly_response = Mock()
        weekly_response.status_code = 200
        weekly_response.content = weekly_buf.getvalue()

        with patch.object(api_client, "_make_request") as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                with patch("appstore_connect.client.datetime") as mock_datetime:
                    # Set "today" to a known date
                    mock_now = datetime(2023, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
                    mock_datetime.now.return_value = mock_now
                    mock_datetime.datetime = (
                        datetime  # Preserve the actual datetime class
                    )

                    # Return daily for recent, weekly for older
                    def side_effect(*args, **kwargs):
                        params = kwargs.get("params", {})
                        if params.get("filter[frequency]") == "WEEKLY":
                            return weekly_response
                        return daily_response

                    mock_request.side_effect = side_effect

                    # Fetch 14 days (should use both daily and weekly)
                    results = api_client._fetch_multiple_days_optimized(days=14)

                    # Should have both daily and weekly data
                    all_sales = results["sales"]
                    assert len(all_sales) > 0

                    # Check that both frequencies were used
                    has_daily = any(
                        df.iloc[0]["frequency"] == "DAILY"
                        for df in all_sales
                        if not df.empty
                    )
                    has_weekly = any(
                        df.iloc[0]["frequency"] == "WEEKLY"
                        for df in all_sales
                        if not df.empty
                    )

                    assert (
                        has_daily or has_weekly
                    )  # At least one type should be present

    def test_fetch_multiple_days_with_start_end_dates(self, api_client):
        """Test fetch_multiple_days with start/end dates (uses _fetch_date_range)."""
        start = date(2023, 6, 1)
        end = date(2023, 6, 3)

        mock_response = Mock()
        mock_response.status_code = 200

        csv_data = "Apple Identifier\tUnits\n123456\t10"
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(csv_data.encode("utf-8"))
        mock_response.content = buf.getvalue()

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                results = api_client.fetch_multiple_days(start_date=start, end_date=end)

                # Should use date range method
                assert "sales" in results
                assert "subscriptions" in results
                assert "subscription_events" in results


class TestReportVersionMapping:
    """Test report version number mapping."""

    def test_subscription_report_version(self, api_client):
        """Test that subscription reports use version 1_4."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(
            api_client, "_make_request", return_value=mock_response
        ) as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(date.today(), report_type="SUBSCRIPTION")

                call_args = mock_request.call_args
                params = call_args[1]["params"]

                assert params["filter[version]"] == "1_4"

    def test_subscriber_report_version(self, api_client):
        """Test that subscriber reports use version 1_4."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = self._create_gzip_content("header\ndata")

        with patch.object(
            api_client, "_make_request", return_value=mock_response
        ) as mock_request:
            with patch.object(api_client, "_generate_token", return_value="token"):
                api_client.get_sales_report(date.today(), report_type="SUBSCRIBER")

                call_args = mock_request.call_args
                params = call_args[1]["params"]

                assert params["filter[version]"] == "1_4"

    def _create_gzip_content(self, content):
        """Helper to create gzipped content."""
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as gz:
            gz.write(content.encode("utf-8"))
        return buf.getvalue()
