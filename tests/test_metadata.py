"""
Tests for metadata management functionality.
"""

import pytest
from unittest.mock import Mock, patch

from appstore_connect.metadata import MetadataManager, create_metadata_manager
from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import ValidationError


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    api = Mock(spec=AppStoreConnectAPI)
    return api


@pytest.fixture
def metadata_manager(mock_api):
    """Create a MetadataManager with mock API."""
    return MetadataManager(mock_api)


@pytest.fixture
def sample_portfolio_data():
    """Create sample portfolio data."""
    return {
        "123456789": {
            "basic_info": {
                "name": "Test App A",
                "bundle_id": "com.test.appa",
                "sku": "APPA123",
                "primary_locale": "en-US",
            },
            "metadata": {
                "app_localizations": {
                    "en-US": {
                        "name": "Test App A",
                        "subtitle": "Amazing App",
                        "privacyPolicyUrl": "https://test.com/privacy",
                    }
                },
                "version_localizations": {
                    "en-US": {
                        "description": "This is a test app",
                        "keywords": "test,app,productivity",
                        "promotionalText": "Try it now!",
                    }
                },
                "app_info": {"name": "Test App A", "bundleId": "com.test.appa"},
                "version_info": {
                    "versionString": "1.0.0",
                    "appStoreState": "READY_FOR_SALE",
                },
            },
            "editable_version": None,
            "last_updated": "2023-01-01T00:00:00",
        },
        "987654321": {
            "basic_info": {
                "name": "Test App B",
                "bundle_id": "com.test.appb",
                "sku": "APPB456",
                "primary_locale": "en-US",
            },
            "metadata": {
                "app_localizations": {
                    "en-US": {
                        "name": "Test App B",
                        "subtitle": None,
                        "privacyPolicyUrl": "https://test.com/privacy",
                    }
                },
                "version_localizations": {},
                "app_info": {"name": "Test App B", "bundleId": "com.test.appb"},
                "version_info": {
                    "versionString": "1.1.0",
                    "appStoreState": "PREPARE_FOR_SUBMISSION",
                },
            },
            "editable_version": {
                "id": "version_123",
                "attributes": {
                    "versionString": "1.1.0",
                    "appStoreState": "PREPARE_FOR_SUBMISSION",
                },
            },
            "last_updated": "2023-01-01T00:00:00",
        },
    }


class TestMetadataManager:
    """Test MetadataManager functionality."""

    @patch("datetime.datetime")
    def test_get_app_portfolio_fresh(self, mock_datetime, metadata_manager, mock_api):
        """Test getting portfolio with fresh data."""
        mock_datetime.now.return_value.isoformat.return_value = "2023-01-01T00:00:00"

        # Mock API responses
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

        mock_api.get_current_metadata.return_value = {
            "app_localizations": {},
            "version_localizations": {},
            "app_info": {},
            "version_info": {},
        }

        mock_api.get_editable_version.return_value = None

        result = metadata_manager.get_app_portfolio(refresh_cache=True)

        assert len(result) == 1
        app = result[0]
        assert app["id"] == "123456789"
        assert app["name"] == "Test App"
        assert app["editable_version"] is None

        # Verify API calls
        mock_api.get_apps.assert_called_once()
        mock_api.get_current_metadata.assert_called_once_with("123456789")
        mock_api.get_editable_version.assert_called_once_with("123456789")

    def test_get_app_portfolio_empty(self, metadata_manager, mock_api):
        """Test getting portfolio with no apps."""
        mock_api.get_apps.return_value = None

        result = metadata_manager.get_app_portfolio()

        assert result == []

    def test_update_app_listing_app_level_fields(self, metadata_manager, mock_api):
        """Test updating app-level fields."""
        mock_api.update_app_name.return_value = True
        mock_api.update_app_subtitle.return_value = True
        mock_api.update_privacy_url.return_value = True

        updates = {
            "name": "New App Name",
            "subtitle": "New Subtitle",
            "privacy_url": "https://new.com/privacy",
        }

        result = metadata_manager.update_app_listing(
            app_id="123456789", updates=updates, locale="en-US"
        )

        assert result["success"] is True
        assert "name" in result["updated"]
        assert "subtitle" in result["updated"]
        assert "privacy_url" in result["updated"]

        # Verify API calls
        mock_api.update_app_name.assert_called_once_with(
            "123456789", "New App Name", "en-US"
        )
        mock_api.update_app_subtitle.assert_called_once_with(
            "123456789", "New Subtitle", "en-US"
        )
        mock_api.update_privacy_url.assert_called_once_with(
            "123456789", "https://new.com/privacy", "en-US"
        )

    def test_update_app_listing_version_level_fields_with_editable_version(
        self, metadata_manager, mock_api
    ):
        """Test updating version-level fields when editable version exists."""
        mock_api.get_editable_version.return_value = {
            "id": "version_123",
            "attributes": {
                "versionString": "1.1.0",
                "appStoreState": "PREPARE_FOR_SUBMISSION",
            },
        }
        mock_api.update_app_description.return_value = True
        mock_api.update_app_keywords.return_value = True

        updates = {"description": "New description", "keywords": "new,keywords"}

        result = metadata_manager.update_app_listing(
            app_id="123456789", updates=updates, locale="en-US"
        )

        assert result["success"] is True
        assert "description" in result["updated"]
        assert "keywords" in result["updated"]

        # Verify API calls
        mock_api.get_editable_version.assert_called_once_with("123456789")
        mock_api.update_app_description.assert_called_once_with(
            "123456789", "New description", "en-US"
        )
        mock_api.update_app_keywords.assert_called_once_with(
            "123456789", "new,keywords", "en-US"
        )

    def test_update_app_listing_version_level_fields_no_editable_version(
        self, metadata_manager, mock_api
    ):
        """Test updating version-level fields when no editable version exists."""
        mock_api.get_editable_version.return_value = None

        updates = {"description": "New description", "keywords": "new,keywords"}

        result = metadata_manager.update_app_listing(
            app_id="123456789", updates=updates, locale="en-US"
        )

        assert result["success"] is False
        assert "description" in result["errors"]
        assert "keywords" in result["errors"]

        # Verify editable version was checked
        mock_api.get_editable_version.assert_called_once_with("123456789")

    def test_update_app_listing_validation_errors(self, metadata_manager, mock_api):
        """Test validation errors during app listing updates."""
        updates = {
            "name": "A" * 31,  # Too long
            "subtitle": "B" * 31,  # Too long
            "description": "C" * 4001,  # Too long
            "keywords": "D" * 101,  # Too long
            "promotional_text": "E" * 171,  # Too long
        }

        result = metadata_manager.update_app_listing(
            app_id="123456789", updates=updates, locale="en-US", validate=True
        )

        # All should fail validation
        assert result["success"] is False
        assert "name" in result["errors"]
        assert "subtitle" in result["errors"]
        assert "description" in result["errors"]
        assert "keywords" in result["errors"]
        assert "promotional_text" in result["errors"]

    def test_batch_update_apps(self, metadata_manager):
        """Test batch updating multiple apps."""
        updates = {
            "123456789": {"name": "App A New", "subtitle": "Subtitle A"},
            "987654321": {"name": "App B New", "subtitle": "Subtitle B"},
        }

        with patch.object(metadata_manager, "update_app_listing") as mock_update:
            mock_update.return_value = {"name": True, "subtitle": True}

            result = metadata_manager.batch_update_apps(updates, locale="en-US")

        assert "results" in result
        assert "123456789" in result["results"]
        assert "987654321" in result["results"]
        assert result["results"]["123456789"]["name"] is True
        assert result["results"]["987654321"]["subtitle"] is True

        # Verify update_app_listing was called for each app
        assert mock_update.call_count == 2

    def test_batch_update_apps_with_error(self, metadata_manager):
        """Test batch updating with errors."""
        updates = {
            "123456789": {"name": "Valid App"},
            "invalid_id": {"name": "Invalid App"},
        }

        with patch.object(metadata_manager, "update_app_listing") as mock_update:
            mock_update.return_value = {"name": True}

            result = metadata_manager.batch_update_apps(
                updates, locale="en-US", continue_on_error=True
            )

        assert "results" in result
        assert "123456789" in result["results"]
        assert "invalid_id" in result["results"]
        assert result["results"]["123456789"]["name"] is True
        assert "error" in result["results"]["invalid_id"]

    def test_standardize_app_names_dry_run(self, metadata_manager, mock_api):
        """Test standardizing app names in dry run mode."""
        # Mock the API to return portfolio data
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "Test App A",
                        "bundleId": "com.test.appa",
                        "sku": "APPA123",
                        "primaryLocale": "en-US",
                    },
                },
                {
                    "id": "987654321",
                    "attributes": {
                        "name": "Test App B",
                        "bundleId": "com.test.appb",
                        "sku": "APPB456",
                        "primaryLocale": "en-US",
                    },
                },
            ]
        }
        mock_api.get_current_metadata.return_value = {
            "app_localizations": {},
            "version_localizations": {},
            "app_info": {},
            "version_info": {},
        }
        mock_api.get_editable_version.return_value = None

        result = metadata_manager.standardize_app_names(
            app_ids=["123456789", "987654321"],
            name_pattern="Prefix {original_name}",
            dry_run=True,
        )

        assert "123456789" in result
        assert "987654321" in result

        app1_result = result["123456789"]
        assert app1_result["original_name"] == "Test App A"
        assert app1_result["new_name"] == "Prefix Test App A"
        assert app1_result["changed"] is True
        assert "updated" not in app1_result  # Dry run, no actual update

    def test_standardize_app_names_with_truncation(self, metadata_manager, mock_api):
        """Test standardizing app names with truncation."""
        # Mock the API to return portfolio data
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "Test App A",
                        "bundleId": "com.test.appa",
                        "sku": "APPA123",
                        "primaryLocale": "en-US",
                    },
                }
            ]
        }
        mock_api.get_current_metadata.return_value = {
            "app_localizations": {},
            "version_localizations": {},
            "app_info": {},
            "version_info": {},
        }
        mock_api.get_editable_version.return_value = None

        # Use a pattern that will exceed 30 characters
        result = metadata_manager.standardize_app_names(
            app_ids=["123456789"],
            name_pattern="Very Long Prefix That Will Be Truncated {original_name}",
            dry_run=True,
        )

        new_name = result["123456789"]["new_name"]
        assert len(new_name) <= 30

    def test_prepare_version_releases_dry_run(self, metadata_manager, mock_api):
        """Test preparing version releases in dry run mode."""
        # Mock existing versions
        mock_api.get_app_store_versions.return_value = {
            "data": [
                {"attributes": {"versionString": "1.0.0"}},
                {"attributes": {"versionString": "1.1.0"}},
            ]
        }

        app_versions = {
            "123456789": "1.2.0",  # New version
            "987654321": "1.0.0",  # Existing version
        }

        result = metadata_manager.prepare_version_releases(app_versions, dry_run=True)

        assert "updated" in result
        assert "skipped" in result
        assert "errors" in result

        assert "123456789" in result["updated"]
        assert "987654321" in result["skipped"]

    def test_prepare_version_releases_actual(self, metadata_manager, mock_api):
        """Test actually creating version releases."""
        # Mock existing versions (empty)
        mock_api.get_app_store_versions.return_value = {"data": []}

        # Mock successful version creation for first app, failure for second
        mock_api.create_app_store_version.side_effect = [
            {"data": {"id": "new_version_123"}},  # Success for first app
            None,  # Failure for second app
        ]

        app_versions = {"123456789": "1.2.0", "987654321": "1.5.0"}

        result = metadata_manager.prepare_version_releases(app_versions, dry_run=False)

        # First app should be in updated (successful creation)
        assert "123456789" in result["updated"]

        # Second app should have an error (creation returned None)
        assert "987654321" in result["errors"]

        # Verify version creation was called
        assert mock_api.create_app_store_version.call_count == 2

    def test_get_localization_status(self, metadata_manager, mock_api):
        """Test getting localization status."""
        # Mock API to return portfolio data
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "Test App A",
                        "bundleId": "com.test.appa",
                        "sku": "APPA123",
                        "primaryLocale": "en-US",
                    },
                },
                {
                    "id": "987654321",
                    "attributes": {
                        "name": "Test App B",
                        "bundleId": "com.test.appb",
                        "sku": "APPB456",
                        "primaryLocale": "en-US",
                    },
                },
            ]
        }

        # Mock different metadata for each app
        def get_metadata_side_effect(app_id):
            if app_id == "123456789":
                return {
                    "app_localizations": {
                        "en-US": {
                            "name": "Test App A",
                            "subtitle": "Amazing App",
                            "privacyPolicyUrl": "https://test.com/privacy",
                        }
                    },
                    "version_localizations": {
                        "en-US": {
                            "description": "This is a test app",
                            "keywords": "test,app,productivity",
                            "promotionalText": "Try it now!",
                        }
                    },
                    "app_info": {"name": "Test App A", "bundleId": "com.test.appa"},
                    "version_info": {
                        "versionString": "1.0.0",
                        "appStoreState": "READY_FOR_SALE",
                    },
                }
            else:
                return {
                    "app_localizations": {
                        "en-US": {
                            "name": "Test App B",
                            "subtitle": None,
                            "privacyPolicyUrl": "https://test.com/privacy",
                        }
                    },
                    "version_localizations": {},
                    "app_info": {"name": "Test App B", "bundleId": "com.test.appb"},
                    "version_info": {
                        "versionString": "1.1.0",
                        "appStoreState": "PREPARE_FOR_SUBMISSION",
                    },
                }

        mock_api.get_current_metadata.side_effect = get_metadata_side_effect
        mock_api.get_editable_version.return_value = None

        result = metadata_manager.get_localization_status(["123456789", "987654321"])

        assert "123456789" in result
        assert "987654321" in result

        app1_status = result["123456789"]
        assert app1_status["app_name"] == "Test App A"
        assert app1_status["app_level_locales"] == ["en-US"]
        assert app1_status["version_level_locales"] == ["en-US"]
        assert app1_status["total_locales"] == 1

        app2_status = result["987654321"]
        assert app2_status["app_name"] == "Test App B"
        assert app2_status["total_locales"] == 1
        assert app2_status["missing_version_level"] == [
            "en-US"
        ]  # No version localizations

    @patch("pandas.DataFrame.to_csv")
    def test_export_app_metadata(self, mock_to_csv, metadata_manager, mock_api):
        """Test exporting app metadata to CSV."""
        # Mock API to return portfolio data
        mock_api.get_apps.return_value = {
            "data": [
                {
                    "id": "123456789",
                    "attributes": {
                        "name": "Test App A",
                        "bundleId": "com.test.appa",
                        "sku": "APPA123",
                        "primaryLocale": "en-US",
                    },
                }
            ]
        }

        mock_api.get_current_metadata.return_value = {
            "app_localizations": {
                "en-US": {
                    "name": "Test App A",
                    "subtitle": "Amazing App",
                    "privacyPolicyUrl": "https://test.com/privacy",
                }
            },
            "version_localizations": {
                "en-US": {
                    "description": "This is a test app",
                    "keywords": "test,app,productivity",
                    "promotionalText": "Try it now!",
                }
            },
            "app_info": {"name": "Test App A", "bundleId": "com.test.appa"},
            "version_info": {
                "versionString": "1.0.0",
                "appStoreState": "READY_FOR_SALE",
            },
        }

        mock_api.get_editable_version.return_value = None

        metadata_manager.export_app_metadata(
            output_path="/tmp/test_export.csv",
            app_ids=["123456789"],
            include_versions=True,
        )

        # Verify CSV export was called
        mock_to_csv.assert_called_once_with("/tmp/test_export.csv", index=False)

    def test_validation_functions(self, metadata_manager, mock_api):
        """Test that validation functions are called correctly."""
        with pytest.raises(ValidationError):
            metadata_manager.update_app_listing(
                app_id="invalid", updates={"name": "Test"}, validate=True  # Too short
            )

        with pytest.raises(ValidationError):
            metadata_manager.batch_update_apps(
                updates={"123456789": {"name": "Test"}},
                locale="invalid-locale",  # Wrong format
            )


class TestCreateMetadataManager:
    """Test convenience function for creating MetadataManager."""

    @patch("appstore_connect.metadata.AppStoreConnectAPI")
    def test_create_metadata_manager(self, mock_api_class):
        """Test creating MetadataManager with convenience function."""
        mock_api_instance = Mock()
        mock_api_class.return_value = mock_api_instance

        manager = create_metadata_manager(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/key.p8",
            vendor_number="12345",
        )

        # Verify API was initialized correctly
        mock_api_class.assert_called_once_with(
            key_id="test_key",
            issuer_id="test_issuer",
            private_key_path="/tmp/key.p8",
            vendor_number="12345",
        )

        # Verify manager was created with the API
        assert isinstance(manager, MetadataManager)
        assert manager.api == mock_api_instance


class TestMetadataManagerErrorHandling:
    """Test error handling in MetadataManager."""

    def test_update_app_listing_api_errors(self, metadata_manager, mock_api):
        """Test handling of API errors during updates."""
        # Mock API methods to raise exceptions
        mock_api.update_app_name.side_effect = Exception("API Error")

        updates = {"name": "New Name"}

        result = metadata_manager.update_app_listing(
            app_id="123456789", updates=updates, locale="en-US"
        )

        # Should return False for failed update
        assert result["success"] is False
        assert "name" in result["errors"]

    def test_batch_update_continue_on_error(self, metadata_manager):
        """Test batch update with continue_on_error=True."""
        updates = {
            "123456789": {"name": "Valid App"},
            "invalid": {"name": "Invalid App"},
        }

        with patch.object(metadata_manager, "update_app_listing") as mock_update:
            mock_update.side_effect = [
                {"name": True},  # First app succeeds
                Exception("Validation error"),  # Second app fails
            ]

            result = metadata_manager.batch_update_apps(updates, continue_on_error=True)

        # First app should succeed, second should have error
        assert result["results"]["123456789"]["name"] is True
        assert "error" in result["results"]["invalid"]

    def test_batch_update_stop_on_error(self, metadata_manager):
        """Test batch update with continue_on_error=False."""
        updates = {
            "123456789": {"name": "Valid App"},
            "invalid": {"name": "Invalid App"},
        }

        with patch.object(metadata_manager, "update_app_listing") as mock_update:
            mock_update.side_effect = [
                {"name": True},  # First app succeeds
                Exception("Validation error"),  # Second app fails
            ]

            result = metadata_manager.batch_update_apps(
                updates, continue_on_error=False
            )

        # Should stop after first error
        assert "123456789" in result["results"]
        assert len(result["results"]) == 2  # Both apps processed, but second has error
