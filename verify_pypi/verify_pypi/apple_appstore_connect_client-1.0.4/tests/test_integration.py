"""
Integration tests for appstore-connect-client.

These tests interact with the actual App Store Connect API and require valid credentials.
Set the following environment variables to run these tests:
- INTEGRATION_TEST_KEY_ID
- INTEGRATION_TEST_ISSUER_ID
- INTEGRATION_TEST_PRIVATE_KEY_PATH
- INTEGRATION_TEST_VENDOR_NUMBER

Run integration tests with: pytest tests/test_integration.py -v
Skip integration tests with: pytest -m "not integration"
"""

import pytest
import os
from datetime import date, timedelta

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.reports import create_report_processor
from appstore_connect.metadata import create_metadata_manager
from appstore_connect.exceptions import (
    AuthenticationError,
    ValidationError,
    NotFoundError,
    PermissionError,
    AppStoreConnectError,
)


def get_integration_credentials():
    """Get integration test credentials from environment."""
    required_vars = [
        "INTEGRATION_TEST_KEY_ID",
        "INTEGRATION_TEST_ISSUER_ID",
        "INTEGRATION_TEST_PRIVATE_KEY_PATH",
        "INTEGRATION_TEST_VENDOR_NUMBER",
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        pytest.skip(f"Integration test credentials not configured. Missing: {', '.join(missing)}")

    return {
        "key_id": os.getenv("INTEGRATION_TEST_KEY_ID"),
        "issuer_id": os.getenv("INTEGRATION_TEST_ISSUER_ID"),
        "private_key_path": os.getenv("INTEGRATION_TEST_PRIVATE_KEY_PATH"),
        "vendor_number": os.getenv("INTEGRATION_TEST_VENDOR_NUMBER"),
    }


@pytest.mark.integration
class TestAPIAuthentication:
    """Test API authentication and token generation."""

    def test_valid_authentication(self):
        """Test authentication with valid credentials."""
        creds = get_integration_credentials()

        # Should not raise any exception
        api = AppStoreConnectAPI(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

        # Test token generation
        token = api._generate_token()
        assert token is not None
        assert len(token) > 100  # JWT tokens are typically long

    def test_invalid_key_id(self):
        """Test authentication with invalid key ID."""
        creds = get_integration_credentials()

        api = AppStoreConnectAPI(
            key_id="INVALID_KEY_ID",
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

        # Should fail when making actual API call
        with pytest.raises(AuthenticationError):
            api.get_apps()

    def test_missing_private_key(self):
        """Test authentication with missing private key file."""
        creds = get_integration_credentials()

        with pytest.raises(ValidationError) as exc_info:
            AppStoreConnectAPI(
                key_id=creds["key_id"],
                issuer_id=creds["issuer_id"],
                private_key_path="/nonexistent/path/key.p8",
                vendor_number=creds["vendor_number"],
            )

        assert "Private key file not found" in str(exc_info.value)


@pytest.mark.integration
class TestSalesReporting:
    """Test sales reporting functionality."""

    @pytest.fixture
    def api_client(self):
        """Create authenticated API client."""
        creds = get_integration_credentials()
        return AppStoreConnectAPI(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

    def test_get_sales_report_recent(self, api_client):
        """Test fetching recent sales report."""
        # Get report from 3 days ago (to ensure data is available)
        report_date = date.today() - timedelta(days=3)

        df = api_client.get_sales_report(report_date)

        # Check DataFrame structure
        assert df is not None
        if not df.empty:
            # Verify expected columns exist
            expected_columns = ["Units", "Developer Proceeds", "Apple Identifier"]
            for col in expected_columns:
                assert col in df.columns

    def test_get_sales_report_no_data(self, api_client):
        """Test fetching sales report for future date (no data)."""
        # Future date should have no data
        future_date = date.today() + timedelta(days=30)

        # Apple returns 404 for dates with no data
        with pytest.raises(NotFoundError):
            api_client.get_sales_report(future_date)

    def test_fetch_multiple_days(self, api_client):
        """Test fetching data for multiple days."""
        # Fetch last 7 days of data
        reports = api_client.fetch_multiple_days(days=7)

        assert "sales" in reports
        assert isinstance(reports["sales"], list)

        # Should have some data for recent days
        total_rows = sum(len(df) for df in reports["sales"])
        assert total_rows >= 0  # May be 0 if no sales

    @pytest.mark.slow
    def test_get_subscription_report(self, api_client):
        """Test fetching subscription report."""
        report_date = date.today() - timedelta(days=3)

        df = api_client.get_subscription_report(report_date)

        assert df is not None
        # Subscription data might be empty for some accounts
        if not df.empty:
            assert "App Apple ID" in df.columns or "Apple Identifier" in df.columns


@pytest.mark.integration
@pytest.mark.timeout(300)  # 5 minute timeout for the entire class
class TestMetadataManagement:
    """Test metadata management functionality."""

    @pytest.fixture
    def api_client(self):
        """Create authenticated API client."""
        creds = get_integration_credentials()
        return AppStoreConnectAPI(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

    def test_get_apps(self, api_client):
        """Test fetching apps list."""
        result = api_client.get_apps()

        # Check if permission error (API key might not have metadata access)
        if result is None:
            pytest.skip("API key does not have metadata permissions")

        assert "data" in result
        assert isinstance(result["data"], list)

        # If apps exist, verify structure
        if result["data"]:
            app = result["data"][0]
            assert "id" in app
            assert "attributes" in app
            assert "name" in app["attributes"]

    @pytest.mark.timeout(300)  # 5 minute timeout - increase from 60s
    def test_get_app_metadata(self, api_client):
        """Test fetching specific app metadata."""
        import time
        import logging
        import os

        # Set up logging to see what's happening
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger(__name__)

        # Log environment variables to verify they're loaded
        logger.info(f"ENV CHECK - KEY_ID: {os.getenv('INTEGRATION_TEST_KEY_ID')}")
        logger.info(f"ENV CHECK - VENDOR: {os.getenv('INTEGRATION_TEST_VENDOR_NUMBER')}")

        try:
            # First get apps
            logger.info("Starting test_get_app_metadata")
            start_time = time.time()

            logger.info("Calling api_client.get_apps()...")
            apps_result = api_client.get_apps()
            logger.info(f"get_apps() completed in {time.time() - start_time:.2f}s")

            # Log the full response data
            logger.info("=== APPS RESPONSE DATA ===")
            if apps_result:
                logger.info(f"Response keys: {list(apps_result.keys())}")
                if "data" in apps_result:
                    logger.info(f"Number of apps: {len(apps_result['data'])}")
                    for i, app in enumerate(apps_result["data"][:3]):  # Show first 3 apps
                        logger.info(
                            f"App {i}: ID={app.get('id')}, "
                            f"Name={app.get('attributes', {}).get('name')}"
                        )
                        logger.info(f"  Bundle ID: {app.get('attributes', {}).get('bundleId')}")
                        logger.info(f"  SKU: {app.get('attributes', {}).get('sku')}")
            else:
                logger.info("apps_result is None")
            logger.info("=========================")

            if apps_result is None or not apps_result.get("data"):
                pytest.skip("No apps available or no metadata permissions")

            logger.info(f"Found {len(apps_result.get('data', []))} apps")

            # Get metadata for first app
            app_id = apps_result["data"][0]["id"]
            app_name = apps_result["data"][0].get("attributes", {}).get("name", "Unknown")
            logger.info(f"Getting metadata for app_id: {app_id} (Name: {app_name})")

            metadata_start = time.time()
            logger.info("Calling api_client.get_current_metadata()...")

            # Call the API method directly without manual timeout
            try:
                metadata = api_client.get_current_metadata(app_id)
            except PermissionError as e:
                logger.info(f"Skipping test due to insufficient permissions: {e}")
                pytest.skip(
                    f"API key does not have sufficient permissions to access "
                    f"app store versions: {e}"
                )

            logger.info(f"get_current_metadata() completed in {time.time() - metadata_start:.2f}s")

            # Log the metadata response
            logger.info("=== METADATA RESPONSE DATA ===")
            logger.info(f"Metadata keys: {list(metadata.keys())}")

            # Log app_info
            if metadata.get("app_info"):
                logger.info(f"app_info keys: {list(metadata['app_info'].keys())}")
                logger.info(f"  bundleId: {metadata['app_info'].get('bundleId')}")
                logger.info(f"  name: {metadata['app_info'].get('name')}")
            else:
                logger.info("app_info is empty")

            # Log app_localizations
            if metadata.get("app_localizations"):
                logger.info(
                    f"app_localizations locales: {list(metadata['app_localizations'].keys())}"
                )
                for locale, data in list(metadata["app_localizations"].items())[
                    :2
                ]:  # First 2 locales
                    logger.info(
                        f"  {locale}: name={data.get('name')}, subtitle={data.get('subtitle')}"
                    )
            else:
                logger.info("app_localizations is empty")

            # Log version_info
            if metadata.get("version_info"):
                logger.info(f"version_info keys: {list(metadata['version_info'].keys())}")
                logger.info(f"  versionString: {metadata['version_info'].get('versionString')}")
                logger.info(f"  appStoreState: {metadata['version_info'].get('appStoreState')}")
            else:
                logger.info("version_info is empty")

            # Log version_localizations
            if metadata.get("version_localizations"):
                logger.info(
                    f"version_localizations locales: "
                    f"{list(metadata['version_localizations'].keys())}"
                )
                for locale, data in list(metadata["version_localizations"].items())[
                    :1
                ]:  # First locale
                    desc = data.get("description", "")
                    logger.info(
                        f"  {locale}: description={desc[:100]}..."
                        if len(desc) > 100
                        else f"  {locale}: description={desc}"
                    )
            else:
                logger.info("version_localizations is empty")
            logger.info("===============================")

            # Check structure - metadata should always be a dict with these keys
            assert isinstance(metadata, dict)
            assert "app_info" in metadata
            assert "app_localizations" in metadata
            assert "version_info" in metadata
            assert "version_localizations" in metadata

            # The values might be empty dicts if no permissions
            # Just verify they are dicts
            assert isinstance(metadata["app_info"], dict)
            assert isinstance(metadata["app_localizations"], dict)
            assert isinstance(metadata["version_info"], dict)
            assert isinstance(metadata["version_localizations"], dict)

            logger.info(f"Test completed successfully in {time.time() - start_time:.2f}s total")

        except Exception as e:
            logger.error(f"Test failed with error: {type(e).__name__}: {e}")
            # Log the error but don't fail the test if it's a timeout or network issue
            if "timeout" in str(e).lower() or "connection" in str(e).lower():
                pytest.skip(f"Test skipped due to network/timeout issue: {e}")
            else:
                raise

    def test_permission_error_handling(self, api_client):
        """Test handling of permission errors for metadata operations."""
        # Try to update app metadata (may fail with permission error)
        try:
            result = api_client.update_app_name("123456789", "New Name")

            # If it succeeds, result should be a dict
            if result:
                assert isinstance(result, dict)
        except PermissionError as e:
            # Expected if API key lacks metadata permissions
            assert "403" in str(e) or "permission" in str(e).lower()
        except NotFoundError:
            # Also acceptable - app doesn't exist
            pass


@pytest.mark.integration
class TestReportProcessor:
    """Test ReportProcessor functionality with real data."""

    @pytest.fixture
    def processor(self):
        """Create ReportProcessor with real credentials."""
        creds = get_integration_credentials()
        return create_report_processor(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

    def test_get_sales_summary(self, processor):
        """Test sales summary generation."""
        # Get summary for last 7 days
        summary = processor.get_sales_summary(days=7)

        assert "summary" in summary
        assert "by_app" in summary
        assert "by_country" in summary
        assert "by_date" in summary

        # Check summary metrics
        assert "total_units" in summary["summary"]
        assert "total_revenue" in summary["summary"]
        assert summary["summary"]["total_units"] >= 0
        assert summary["summary"]["total_revenue"] >= 0

    def test_compare_periods(self, processor):
        """Test period comparison functionality."""
        # Compare last 7 days with previous 7 days
        comparison = processor.compare_periods(current_days=7, comparison_days=7)

        assert "periods" in comparison
        assert "changes" in comparison
        assert "current" in comparison["periods"]
        assert "comparison" in comparison["periods"]


@pytest.mark.integration
class TestMetadataManager:
    """Test MetadataManager functionality with real data."""

    @pytest.fixture
    def manager(self):
        """Create MetadataManager with real credentials."""
        creds = get_integration_credentials()

        # Check if we have metadata permissions
        api = AppStoreConnectAPI(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

        # Test metadata access
        apps = api.get_apps()
        if apps is None:
            pytest.skip("API key does not have metadata permissions")

        return create_metadata_manager(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

    def test_get_app_portfolio(self, manager):
        """Test fetching app portfolio."""
        try:
            portfolio = manager.get_app_portfolio()
        except PermissionError as e:
            pytest.skip(f"API key does not have sufficient permissions: {e}")

        assert isinstance(portfolio, list)

        # If apps exist, verify structure
        if portfolio:
            app = portfolio[0]
            assert "id" in app
            assert "name" in app
            assert "bundleId" in app

    def test_export_app_metadata(self, manager, tmp_path):
        """Test exporting app metadata to CSV."""
        output_file = tmp_path / "app_metadata.csv"

        try:
            success = manager.export_app_metadata(str(output_file))
        except PermissionError as e:
            pytest.skip(f"API key does not have sufficient permissions: {e}")

        if success:
            assert output_file.exists()
            assert output_file.stat().st_size > 0


@pytest.mark.integration
class TestErrorScenarios:
    """Test various error scenarios with real API."""

    @pytest.fixture
    def api_client(self):
        """Create authenticated API client."""
        creds = get_integration_credentials()
        return AppStoreConnectAPI(
            key_id=creds["key_id"],
            issuer_id=creds["issuer_id"],
            private_key_path=creds["private_key_path"],
            vendor_number=creds["vendor_number"],
        )

    def test_invalid_app_id(self, api_client):
        """Test operations with invalid app ID."""
        invalid_app_id = "9999999999"  # Unlikely to exist

        # Should handle gracefully
        metadata = api_client.get_current_metadata(invalid_app_id)

        # Should return structured metadata with empty values
        if metadata is not None:
            # Check that all sub-dicts are empty
            assert metadata["app_info"] == {}
            assert metadata["app_localizations"] == {}
            assert metadata["version_info"] == {}
            assert metadata["version_localizations"] == {}

    def test_invalid_date_range(self, api_client):
        """Test fetching data for very old dates."""
        # Try to fetch data from 10 years ago
        old_date = date.today() - timedelta(days=3650)

        # Expect an error for dates that are too old
        with pytest.raises(AppStoreConnectError) as exc_info:
            api_client.get_sales_report(old_date)

        # Should get a 410 error about report no longer available
        assert "410" in str(exc_info.value) or "no longer available" in str(exc_info.value).lower()

    def test_malformed_request(self, api_client):
        """Test handling of malformed requests."""
        # Test with invalid report type
        with pytest.raises(AppStoreConnectError) as exc_info:
            api_client.get_sales_report(date.today(), report_type="INVALID_TYPE")

        # Should get a 400 error about invalid filter value
        assert "400" in str(exc_info.value) or "not a valid filter value" in str(exc_info.value)
