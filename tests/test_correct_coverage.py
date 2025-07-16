"""
Correct tests for actual uncovered lines in the codebase.
"""

from unittest.mock import Mock, patch

from appstore_connect.metadata import MetadataManager


class TestActualMetadataCoverage:
    """Test the actual uncovered lines in metadata.py."""

    def test_get_app_portfolio_with_none_metadata(self):
        """Test line 206: When get_current_metadata returns None."""
        mock_api = Mock()

        # Mock get_apps to return an app
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

        # Mock get_current_metadata to return None (instead of a dict)
        mock_api.get_current_metadata.return_value = None

        manager = MetadataManager(mock_api)

        portfolio = manager.get_app_portfolio()

        # Should still have basic info
        assert len(portfolio) == 1
        app = portfolio[0]
        assert app["id"] == "123456789"
        assert app["name"] == "Test App"
        # Metadata should be None as returned by the mock
        assert app["metadata"] is None

    def test_update_app_listing_field_specific_errors(self):
        """Test lines 214-215: Exception handling for specific field updates."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Set up different exceptions for different methods
        mock_api.update_app_name.side_effect = Exception("Name update failed")
        mock_api.update_privacy_url.side_effect = Exception("URL update failed")

        updates = {"name": "New Name", "privacy_url": "https://example.com/privacy"}

        result = manager.update_app_listing("123456789", updates)

        # Check the new return structure
        assert result["success"] is False
        assert "name" in result["errors"]
        assert "privacy_url" in result["errors"]
        assert len(result["updated"]) == 0

    def test_batch_update_apps_results_structure(self):
        """Test lines 239-243: Results formatting in batch_update_apps."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # First app succeeds, second fails with exception
        mock_api.update_app_name.side_effect = [
            True,  # First app succeeds
            Exception("API timeout"),  # Second app fails
        ]

        updates = {
            "123456789": {"name": "App One Updated"},
            "987654321": {"name": "App Two Updated"},
        }

        # Use continue_on_error=True to test error handling
        results = manager.batch_update_apps(updates, continue_on_error=True)

        # Check results structure - batch_update_apps returns {'results': {...}}
        assert isinstance(results, dict)
        assert "results" in results
        assert "123456789" in results["results"]
        assert "987654321" in results["results"]

        # First app should succeed
        assert results["results"]["123456789"]["success"] is True
        assert "name" in results["results"]["123456789"]["updated"]

        # Second app should fail (the exception is caught by update_app_listing)
        assert results["results"]["987654321"]["success"] is False
        assert "name" in results["results"]["987654321"]["errors"]

    def test_prepare_version_releases_complete_flow(self):
        """Test lines 303-310: Full prepare_version_releases implementation."""
        mock_api = Mock()
        manager = MetadataManager(mock_api)

        # Mock successful version creation for first app, failure for second
        mock_api.create_app_store_version.side_effect = [
            {"data": {"id": "new_version_123"}},  # Success for first app
            None,  # Failure for second app
        ]

        # Mock get_app_store_versions to return empty (no existing versions)
        mock_api.get_app_store_versions.return_value = {"data": []}

        # Run in non-dry-run mode
        app_versions = {"123456789": "2.0.0", "987654321": "1.5.0"}
        results = manager.prepare_version_releases(app_versions, dry_run=False)

        # Check results structure - prepare_version_releases returns {'updated': [], 'skipped': [], 'errors': {}}
        assert "updated" in results
        assert "skipped" in results
        assert "errors" in results

        # First app should be in updated (successful creation)
        assert "123456789" in results["updated"]

        # Second app should have an error (creation returned None)
        assert "987654321" in results["errors"]

    # The following tests were removed as they test non-existent behavior:
    # - test_get_localization_status_missing_locales
    # - test_get_localization_status_with_exception
    # - test_export_app_metadata_error_handling
    # - test_standardize_app_names_app_not_in_portfolio
    # - test_export_app_metadata_with_app_ids_filter
    # - test_export_app_metadata_missing_app_in_portfolio

    def test_create_metadata_manager_function(self):
        """Test lines 428-429: The create_metadata_manager convenience function."""
        from appstore_connect.metadata import create_metadata_manager

        with patch("appstore_connect.metadata.AppStoreConnectAPI") as mock_api_class:
            mock_api_instance = Mock()
            mock_api_class.return_value = mock_api_instance

            # Call the convenience function
            manager = create_metadata_manager(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/key.p8",
                vendor_number="12345",
            )

            # Should create API with correct parameters
            mock_api_class.assert_called_once_with(
                key_id="test_key",
                issuer_id="test_issuer",
                private_key_path="/tmp/key.p8",
                vendor_number="12345",
            )

            # Should return MetadataManager instance
            assert isinstance(manager, MetadataManager)
            assert manager.api == mock_api_instance
