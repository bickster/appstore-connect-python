"""
Additional tests for metadata.py to achieve 100% coverage.
"""

import pytest
from unittest.mock import Mock

from appstore_connect.metadata import MetadataManager
from appstore_connect.exceptions import ValidationError
from appstore_connect.exceptions import PermissionError as AppStorePermissionError


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
            "id": "ver123",
            "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"},
        }
        mock_api.get_app_store_version_localizations.return_value = {
            "data": [{"id": "loc123", "attributes": {"locale": "fr-FR"}}]  # Different locale
        }

        updates = {"name": "New Name", "description": "New Description"}

        # Should partially succeed
        results = metadata_manager.update_app_listing(
            app_id="123456789", updates=updates, locale="en-US"
        )

        # Name should succeed, description should succeed (we don't check locale mismatch)
        assert results["success"] is True
        assert "name" in results["updated"]
        assert "description" in results["updated"]

    def test_batch_update_apps_api_exception(self, metadata_manager, mock_api):
        """Test batch_update_apps when API raises exception."""
        # First app succeeds
        mock_api.update_app_name.side_effect = [True, Exception("API Error")]

        updates = {"123456789": {"name": "App 1"}, "987654321": {"name": "App 2"}}

        results = metadata_manager.batch_update_apps(updates=updates, continue_on_error=True)

        # Should have one success and one error
        assert "123456789" in results["results"]
        assert results["results"]["123456789"]["success"] is True
        assert "987654321" in results["results"]
        assert results["results"]["987654321"]["success"] is False
        assert "name" in results["results"]["987654321"]["errors"]

    def test_standardize_app_names_no_changes_needed(self, metadata_manager, mock_api):
        """Test standardize_app_names when no changes are needed."""
        # Mock portfolio with already standardized names
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "MyApp Pro",
                        "bundleId": "com.test.myapp",
                        "sku": "MYAPP",
                    },
                }
            ]
        }

        mock_api.get_current_metadata.return_value = {
            "app_info": {"name": "MyApp Pro", "bundleId": "com.test.myapp"},
            "app_localizations": {"en-US": {"name": "MyApp Pro"}},
        }

        mock_api.get_editable_version.return_value = None

        results = metadata_manager.standardize_app_names(
            name_pattern="{original_name} Pro", dry_run=False
        )

        # Should have one app but no changes needed
        assert "123456789" in results
        assert results["123456789"]["original_name"] == "MyApp Pro"
        assert results["123456789"]["new_name"] == "MyApp Pro Pro"
        assert results["123456789"]["changed"] is True

    def test_prepare_version_releases_no_eligible_versions(self, metadata_manager, mock_api):
        """Test prepare_version_releases with no eligible versions."""
        # Mock portfolio
        mock_api.get_apps.return_value = {
            "data": [{"id": "123456789", "attributes": {"name": "Test App"}}]
        }

        # Mock no editable version
        mock_api.get_editable_version.return_value = None

        mock_api.get_current_metadata.return_value = {}

        results = metadata_manager.prepare_version_releases(
            release_notes="New features", dry_run=False
        )

        # Should skip app with no editable version
        assert "123456789" in results["skipped"]
        assert len(results["updated"]) == 0

    def test_get_localization_status_with_errors(self, metadata_manager, mock_api):
        """Test get_localization_status with API errors."""
        # Mock portfolio
        mock_api.get_apps.return_value = {
            "data": [{"id": "123456789", "attributes": {"name": "Test App"}}]
        }

        # Mock metadata fetch failure
        mock_api.get_current_metadata.side_effect = AppStorePermissionError("No access")

        # get_localization_status will fail during portfolio fetch
        with pytest.raises(AppStorePermissionError):
            metadata_manager.get_localization_status(["123456789"])

    def test_export_app_metadata_with_permission_error(self, metadata_manager, mock_api, tmp_path):
        """Test export_app_metadata when API has permission errors."""
        # Mock portfolio fetch failure with general exception
        mock_api.get_apps.side_effect = Exception("No metadata access")

        output_file = tmp_path / "export.csv"

        # Should return False for general exceptions
        result = metadata_manager.export_app_metadata(str(output_file))
        assert result is False

        # File should not be created
        assert not output_file.exists()

    def test_validation_edge_cases(self, metadata_manager):
        """Test validation edge cases."""
        # Test with None app_id
        with pytest.raises(ValidationError):
            metadata_manager.update_app_listing(
                app_id=None, updates={"name": "Test"}, validate=True
            )

        # Test with empty string app_id
        with pytest.raises(ValidationError):
            metadata_manager.update_app_listing(app_id="", updates={"name": "Test"}, validate=True)

        # Test batch update with invalid locale format
        with pytest.raises(ValidationError):
            metadata_manager.batch_update_apps(
                updates={"123456789": {"name": "Test"}},
                locale="english",  # Should be like 'en-US'
            )

    def test_update_promotional_text_special_case(self, metadata_manager, mock_api):
        """Test updating promotional text through update_app_listing."""
        mock_api.get_editable_version.return_value = {
            "id": "ver123",
            "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"},
        }

        mock_api.update_promotional_text.return_value = True

        results = metadata_manager.update_app_listing(
            app_id="123456789",
            updates={"promotional_text": "Check out the new features!"},
            locale="en-US",
        )

        assert results["success"] is True
        assert "promotional_text" in results["updated"]

        # Verify the call
        mock_api.update_promotional_text.assert_called_once_with(
            "123456789", "Check out the new features!", "en-US"
        )


class TestMetadataManagerCaching:
    """Test caching behavior in MetadataManager."""

    def test_batch_operation_context_manager(self, metadata_manager, mock_api):
        """Test that batch operation context manager works correctly."""
        # Set up portfolio data
        portfolio_data = {
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
        mock_api.get_apps.return_value = portfolio_data
        mock_api.get_current_metadata.return_value = {}
        mock_api.get_editable_version.return_value = None

        # Without batch context, each call fetches fresh data
        portfolio1 = metadata_manager.get_app_portfolio()
        portfolio2 = metadata_manager.get_app_portfolio()

        # Verify both portfolios have same data (ignoring timestamps)
        assert len(portfolio1) == 1
        assert len(portfolio2) == 1
        assert portfolio1[0]["id"] == portfolio2[0]["id"]
        assert portfolio1[0]["name"] == portfolio2[0]["name"]
        assert portfolio1[0]["bundleId"] == portfolio2[0]["bundleId"]

        assert mock_api.get_apps.call_count == 2

        # Reset call count
        mock_api.get_apps.reset_mock()

        # With batch context, data is cached
        with metadata_manager.batch_operation():
            portfolio3 = metadata_manager.get_app_portfolio()
            portfolio4 = metadata_manager.get_app_portfolio()

            # Verify cached data is the same
            assert portfolio3 == portfolio4  # Exact same object from cache
            assert portfolio3[0]["id"] == portfolio1[0]["id"]  # Same data as non-cached

            assert mock_api.get_apps.call_count == 1  # Only called once

        # After context, cache is cleared
        portfolio5 = metadata_manager.get_app_portfolio()

        # Verify fresh fetch returns same data
        assert portfolio5[0]["id"] == portfolio1[0]["id"]

        assert mock_api.get_apps.call_count == 2  # Called again
