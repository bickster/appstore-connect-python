"""
Tests for AppStoreConnectAPI metadata management functionality.
Focus on app info, localizations, versions, and update methods.
"""

import pytest
from unittest.mock import Mock, patch

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import (
    ValidationError,
    NotFoundError,
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


@pytest.fixture
def mock_success_response():
    """Mock successful API response."""
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"data": []}
    return response


class TestAppInfoMethods:
    """Test app info retrieval methods."""

    def test_get_app_info_success(self, api_client, mock_success_response):
        """Test successful app info retrieval."""
        app_data = {
            "data": {
                "id": "123456",
                "type": "apps",
                "attributes": {"name": "Test App", "bundleId": "com.test.app"},
            }
        }
        mock_success_response.json.return_value = app_data

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_app_info("123456")

                assert result == app_data
                api_client._make_request.assert_called_with(method="GET", endpoint="/apps/123456")

    def test_get_app_info_not_found(self, api_client):
        """Test app info when app doesn't exist."""
        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_app_info("nonexistent")

                assert result is None

    def test_get_app_infos(self, api_client, mock_success_response):
        """Test getting app info objects."""
        app_infos_data = {
            "data": [
                {
                    "id": "info123",
                    "type": "appInfos",
                    "attributes": {"appStoreState": "READY_FOR_SALE"},
                }
            ]
        }
        mock_success_response.json.return_value = app_infos_data

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_app_infos("123456")

                assert result == app_infos_data
                api_client._make_request.assert_called_with(
                    method="GET", endpoint="/apps/123456/appInfos"
                )

    def test_get_app_info_localizations(self, api_client, mock_success_response):
        """Test getting app info localizations."""
        localizations_data = {
            "data": [
                {
                    "id": "loc1",
                    "type": "appInfoLocalizations",
                    "attributes": {
                        "locale": "en-US",
                        "name": "Test App",
                        "subtitle": "Test Subtitle",
                    },
                }
            ]
        }
        mock_success_response.json.return_value = localizations_data

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_app_info_localizations("info123")

                assert result == localizations_data
                api_client._make_request.assert_called_with(
                    method="GET", endpoint="/appInfos/info123/appInfoLocalizations"
                )


class TestAppInfoUpdates:
    """Test app info update methods."""

    def test_update_app_info_localization_success(self, api_client, mock_success_response):
        """Test successful app info localization update."""
        update_data = {"name": "New App Name"}

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.update_app_info_localization("loc123", update_data)

                assert result is True

                # Check the request
                call_args = api_client._make_request.call_args
                assert call_args[1]["method"] == "PATCH"
                assert call_args[1]["endpoint"] == "/appInfoLocalizations/loc123"

                # Check request data structure
                sent_data = call_args[1]["data"]
                assert sent_data["data"]["type"] == "appInfoLocalizations"
                assert sent_data["data"]["id"] == "loc123"
                assert sent_data["data"]["attributes"] == update_data

    def test_update_app_info_localization_failure(self, api_client):
        """Test failed app info localization update."""
        mock_response = Mock()
        mock_response.status_code = 400

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.update_app_info_localization("loc123", {"name": "New"})

                assert result is False


class TestAppStoreVersionMethods:
    """Test App Store version management methods."""

    def test_create_app_store_version_success(self, api_client):
        """Test creating a new App Store version."""
        mock_response = Mock()
        mock_response.status_code = 201
        created_data = {
            "data": {
                "id": "ver123",
                "type": "appStoreVersions",
                "attributes": {"versionString": "2.0"},
            }
        }
        mock_response.json.return_value = created_data

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.create_app_store_version(
                    app_id="123456", version_string="2.0", platform="IOS"
                )

                assert result == created_data

                # Check request data
                call_args = api_client._make_request.call_args
                sent_data = call_args[1]["data"]

                assert sent_data["data"]["type"] == "appStoreVersions"
                assert sent_data["data"]["attributes"]["versionString"] == "2.0"
                assert sent_data["data"]["attributes"]["platform"] == "IOS"
                assert sent_data["data"]["relationships"]["app"]["data"]["id"] == "123456"

    def test_create_app_store_version_failure(self, api_client):
        """Test failed version creation."""
        mock_response = Mock()
        mock_response.status_code = 400

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.create_app_store_version("123456", "2.0")

                assert result is None

    def test_get_app_store_versions(self, api_client, mock_success_response):
        """Test getting app store versions."""
        versions_data = {
            "data": [
                {
                    "id": "ver123",
                    "type": "appStoreVersions",
                    "attributes": {
                        "versionString": "1.0",
                        "appStoreState": "READY_FOR_SALE",
                    },
                }
            ]
        }
        mock_success_response.json.return_value = versions_data

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_app_store_versions("123456")

                assert result == versions_data

                # Check request params
                call_args = api_client._make_request.call_args
                assert call_args[1]["params"]["filter[app]"] == "123456"
                assert call_args[1]["params"]["include"] == "appStoreVersionLocalizations"

    def test_get_app_store_version_localizations(self, api_client, mock_success_response):
        """Test getting version localizations."""
        localizations_data = {
            "data": [
                {
                    "id": "verloc123",
                    "type": "appStoreVersionLocalizations",
                    "attributes": {"locale": "en-US", "description": "App description"},
                }
            ]
        }
        mock_success_response.json.return_value = localizations_data

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_app_store_version_localizations("ver123")

                assert result == localizations_data

    def test_update_app_store_version_localization(self, api_client, mock_success_response):
        """Test updating version localization."""
        update_data = {"description": "New description"}

        with patch.object(api_client, "_make_request", return_value=mock_success_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.update_app_store_version_localization("verloc123", update_data)

                assert result is True

                # Check request structure
                call_args = api_client._make_request.call_args
                sent_data = call_args[1]["data"]

                assert sent_data["data"]["type"] == "appStoreVersionLocalizations"
                assert sent_data["data"]["id"] == "verloc123"
                assert sent_data["data"]["attributes"] == update_data


class TestHighLevelUpdateMethods:
    """Test high-level update helper methods."""

    def test_update_app_name_success(self, api_client):
        """Test updating app name."""
        # Mock the chain of calls
        app_infos_response = Mock()
        app_infos_response.status_code = 200
        app_infos_response.json.return_value = {"data": [{"id": "info123"}]}

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "loc123", "attributes": {"locale": "en-US"}}]
        }

        update_response = Mock()
        update_response.status_code = 200

        responses = [app_infos_response, localizations_response, update_response]

        with patch.object(api_client, "_make_request", side_effect=responses):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.update_app_name("123456", "New Name")

                assert result is True

    def test_update_app_name_too_long(self, api_client):
        """Test validation for app name length."""
        with pytest.raises(ValidationError) as exc_info:
            api_client.update_app_name(
                "123456",
                "This app name is way too long and exceeds the maximum allowed characters",
            )

        assert "App name too long" in str(exc_info.value)
        assert "Maximum is 30 characters" in str(exc_info.value)

    def test_update_app_name_no_app_info(self, api_client):
        """Test error when app info not found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}  # Empty data

        with patch.object(api_client, "_make_request", return_value=mock_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                with pytest.raises(NotFoundError) as exc_info:
                    api_client.update_app_name("123456", "New Name")

                assert "Could not fetch app info" in str(exc_info.value)

    def test_update_app_name_locale_not_found(self, api_client):
        """Test error when locale not found."""
        app_infos_response = Mock()
        app_infos_response.status_code = 200
        app_infos_response.json.return_value = {"data": [{"id": "info123"}]}

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "loc123", "attributes": {"locale": "fr-FR"}}]  # Different locale
        }

        with patch.object(
            api_client,
            "_make_request",
            side_effect=[app_infos_response, localizations_response],
        ):
            with patch.object(api_client, "_generate_token", return_value="token"):
                with pytest.raises(NotFoundError) as exc_info:
                    api_client.update_app_name("123456", "New Name", locale="en-US")

                assert "Localization en-US not found" in str(exc_info.value)

    def test_update_app_subtitle(self, api_client):
        """Test updating app subtitle."""
        # Similar structure to app name
        app_infos_response = Mock()
        app_infos_response.status_code = 200
        app_infos_response.json.return_value = {"data": [{"id": "info123"}]}

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "loc123", "attributes": {"locale": "en-US"}}]
        }

        update_response = Mock()
        update_response.status_code = 200

        responses = [app_infos_response, localizations_response, update_response]

        with patch.object(api_client, "_make_request", side_effect=responses):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.update_app_subtitle("123456", "New Subtitle")

                assert result is True

    def test_update_app_subtitle_too_long(self, api_client):
        """Test validation for subtitle length."""
        with pytest.raises(ValidationError) as exc_info:
            api_client.update_app_subtitle(
                "123456", "This subtitle is also way too long and exceeds maximum"
            )

        assert "App subtitle too long" in str(exc_info.value)

    def test_update_privacy_url(self, api_client):
        """Test updating privacy URL."""
        app_infos_response = Mock()
        app_infos_response.status_code = 200
        app_infos_response.json.return_value = {"data": [{"id": "info123"}]}

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "loc123", "attributes": {"locale": "en-US"}}]
        }

        update_response = Mock()
        update_response.status_code = 200

        responses = [app_infos_response, localizations_response, update_response]

        with patch.object(api_client, "_make_request", side_effect=responses):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.update_privacy_url("123456", "https://example.com/privacy")

                assert result is True


class TestEditableVersionMethods:
    """Test methods requiring editable versions."""

    def test_get_editable_version_found(self, api_client):
        """Test finding an editable version."""
        versions_response = Mock()
        versions_response.status_code = 200
        versions_response.json.return_value = {
            "data": [
                {"id": "ver1", "attributes": {"appStoreState": "READY_FOR_SALE"}},
                {
                    "id": "ver2",
                    "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"},
                },
            ]
        }

        with patch.object(api_client, "_make_request", return_value=versions_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_editable_version("123456")

                assert result is not None
                assert result["id"] == "ver2"
                assert result["attributes"]["appStoreState"] == "PREPARE_FOR_SUBMISSION"

    def test_get_editable_version_not_found(self, api_client):
        """Test when no editable version exists."""
        versions_response = Mock()
        versions_response.status_code = 200
        versions_response.json.return_value = {
            "data": [{"id": "ver1", "attributes": {"appStoreState": "READY_FOR_SALE"}}]
        }

        with patch.object(api_client, "_make_request", return_value=versions_response):
            with patch.object(api_client, "_generate_token", return_value="token"):
                result = api_client.get_editable_version("123456")

                assert result is None

    def test_get_editable_version_all_states(self, api_client):
        """Test recognizing all editable states."""
        editable_states = [
            "PREPARE_FOR_SUBMISSION",
            "WAITING_FOR_REVIEW",
            "IN_REVIEW",
            "DEVELOPER_REJECTED",
            "REJECTED",
        ]

        for state in editable_states:
            versions_response = Mock()
            versions_response.status_code = 200
            versions_response.json.return_value = {
                "data": [{"id": f"ver_{state}", "attributes": {"appStoreState": state}}]
            }

            with patch.object(api_client, "_make_request", return_value=versions_response):
                with patch.object(api_client, "_generate_token", return_value="token"):
                    result = api_client.get_editable_version("123456")

                    assert result is not None
                    assert result["attributes"]["appStoreState"] == state

    def test_update_app_description(self, api_client):
        """Test updating app description."""
        # Mock editable version
        editable_version = {
            "id": "ver123",
            "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"},
        }

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "verloc123", "attributes": {"locale": "en-US"}}]
        }

        update_response = Mock()
        update_response.status_code = 200

        with patch.object(api_client, "get_editable_version", return_value=editable_version):
            with patch.object(
                api_client,
                "_make_request",
                side_effect=[localizations_response, update_response],
            ):
                with patch.object(api_client, "_generate_token", return_value="token"):
                    result = api_client.update_app_description("123456", "New app description")

                    assert result is True

    def test_update_app_description_too_long(self, api_client):
        """Test description length validation."""
        with pytest.raises(ValidationError) as exc_info:
            api_client.update_app_description("123456", "x" * 4001)  # Exceeds 4000 char limit

        assert "Description too long" in str(exc_info.value)
        assert "Maximum is 4000 characters" in str(exc_info.value)

    def test_update_app_description_no_editable_version(self, api_client):
        """Test error when no editable version exists."""
        with patch.object(api_client, "get_editable_version", return_value=None):
            with pytest.raises(ValidationError) as exc_info:
                api_client.update_app_description("123456", "New description")

            assert "No editable version found" in str(exc_info.value)

    def test_update_app_keywords(self, api_client):
        """Test updating app keywords."""
        editable_version = {
            "id": "ver123",
            "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"},
        }

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "verloc123", "attributes": {"locale": "en-US"}}]
        }

        update_response = Mock()
        update_response.status_code = 200

        with patch.object(api_client, "get_editable_version", return_value=editable_version):
            with patch.object(
                api_client,
                "_make_request",
                side_effect=[localizations_response, update_response],
            ):
                with patch.object(api_client, "_generate_token", return_value="token"):
                    result = api_client.update_app_keywords("123456", "keyword1,keyword2,keyword3")

                    assert result is True

    def test_update_app_keywords_too_long(self, api_client):
        """Test keywords length validation."""
        with pytest.raises(ValidationError) as exc_info:
            api_client.update_app_keywords("123456", "x" * 101)  # Exceeds 100 char limit

        assert "Keywords too long" in str(exc_info.value)

    def test_update_promotional_text(self, api_client):
        """Test updating promotional text."""
        editable_version = {
            "id": "ver123",
            "attributes": {"appStoreState": "PREPARE_FOR_SUBMISSION"},
        }

        localizations_response = Mock()
        localizations_response.status_code = 200
        localizations_response.json.return_value = {
            "data": [{"id": "verloc123", "attributes": {"locale": "en-US"}}]
        }

        update_response = Mock()
        update_response.status_code = 200

        with patch.object(api_client, "get_editable_version", return_value=editable_version):
            with patch.object(
                api_client,
                "_make_request",
                side_effect=[localizations_response, update_response],
            ):
                with patch.object(api_client, "_generate_token", return_value="token"):
                    result = api_client.update_promotional_text(
                        "123456", "Check out our latest features!"
                    )

                    assert result is True

    def test_update_promotional_text_too_long(self, api_client):
        """Test promotional text length validation."""
        with pytest.raises(ValidationError) as exc_info:
            api_client.update_promotional_text("123456", "x" * 171)  # Exceeds 170 char limit

        assert "Promotional text too long" in str(exc_info.value)


class TestGetCurrentMetadata:
    """Test comprehensive metadata retrieval."""

    def test_get_current_metadata_complete(self, api_client):
        """Test getting complete metadata for an app."""
        # Mock all the API calls
        app_info_response = Mock()
        app_info_response.status_code = 200
        app_info_response.json.return_value = {
            "data": {"attributes": {"name": "Test App", "bundleId": "com.test.app"}}
        }

        app_infos_response = Mock()
        app_infos_response.status_code = 200
        app_infos_response.json.return_value = {"data": [{"id": "info123"}]}

        app_localizations_response = Mock()
        app_localizations_response.status_code = 200
        app_localizations_response.json.return_value = {
            "data": [
                {
                    "attributes": {
                        "locale": "en-US",
                        "name": "Test App",
                        "subtitle": "Great App",
                    }
                }
            ]
        }

        versions_response = Mock()
        versions_response.status_code = 200
        versions_response.json.return_value = {
            "data": [
                {
                    "id": "ver123",
                    "attributes": {
                        "versionString": "1.0",
                        "appStoreState": "READY_FOR_SALE",
                    },
                }
            ]
        }

        version_localizations_response = Mock()
        version_localizations_response.status_code = 200
        version_localizations_response.json.return_value = {
            "data": [{"attributes": {"locale": "en-US", "description": "App description"}}]
        }

        responses = [
            app_info_response,
            app_infos_response,
            app_localizations_response,
            versions_response,
            version_localizations_response,
        ]

        with patch.object(api_client, "_make_request", side_effect=responses):
            with patch.object(api_client, "_generate_token", return_value="token"):
                metadata = api_client.get_current_metadata("123456")

                # Check structure
                assert "app_info" in metadata
                assert metadata["app_info"]["name"] == "Test App"

                assert "app_localizations" in metadata
                assert "en-US" in metadata["app_localizations"]

                assert "version_info" in metadata
                assert metadata["version_info"]["versionString"] == "1.0"

                assert "version_localizations" in metadata
                assert "en-US" in metadata["version_localizations"]

    def test_get_current_metadata_partial_data(self, api_client):
        """Test metadata retrieval with partial data available."""
        # App info succeeds
        app_info_response = Mock()
        app_info_response.status_code = 200
        app_info_response.json.return_value = {"data": {"attributes": {"name": "Test App"}}}

        # App infos fails (404)
        app_infos_response = Mock()
        app_infos_response.status_code = 404

        # Versions succeeds but empty
        versions_response = Mock()
        versions_response.status_code = 200
        versions_response.json.return_value = {"data": []}

        responses = [
            app_info_response,
            app_infos_response,  # Will raise NotFoundError
            versions_response,
        ]

        with patch.object(api_client, "_make_request", side_effect=responses):
            with patch.object(api_client, "_generate_token", return_value="token"):
                metadata = api_client.get_current_metadata("123456")

                # Should have partial data
                assert metadata["app_info"]["name"] == "Test App"
                assert metadata["app_localizations"] == {}
                assert metadata["version_info"] == {}
                assert metadata["version_localizations"] == {}
