"""
App metadata management utilities for appstore-connect-client.

This module provides high-level functions for managing app store listings,
including batch operations, validation, and convenient wrapper methods.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from contextlib import contextmanager
from .client import AppStoreConnectAPI
from .utils import (
    validate_app_id,
    validate_locale,
    validate_version_string,
    sanitize_app_name,
    truncate_string,
)
from .exceptions import ValidationError


class MetadataManager:
    """
    High-level metadata manager for App Store Connect apps.

    This class provides convenient methods for managing app metadata
    with built-in validation, error handling, and batch operations.
    """

    def __init__(self, api: AppStoreConnectAPI):
        """Initialize with an API client."""
        self.api = api
        self._temp_cache = None
        self._in_batch_mode = False

    @contextmanager
    def batch_operation(self):
        """
        Context manager for batch operations that enables temporary caching.

        Usage:
            with manager.batch_operation():
                manager.standardize_app_names()
                manager.prepare_version_releases()

        The cache is automatically cleared when exiting the context.
        """
        self._in_batch_mode = True
        self._temp_cache = {}
        try:
            yield
        finally:
            self._in_batch_mode = False
            self._temp_cache = None

    def get_app_portfolio(self, refresh_cache: bool = False) -> List[Dict[str, Any]]:
        """
        Get comprehensive information about all apps in the account.

        Args:
            refresh_cache: Whether to refresh the cached app data

        Returns:
            List of app information dictionaries
        """
        # Check if we should use cache
        if not refresh_cache and self._in_batch_mode and self._temp_cache is not None:
            # Return cached data if available
            if self._temp_cache:
                return list(self._temp_cache.values())

        apps_response = self.api.get_apps()
        if not apps_response or "data" not in apps_response:
            return []

        portfolio = []
        portfolio_dict = {}
        for app in apps_response["data"]:
            app_id = app["id"]
            attributes = app["attributes"]

            # Get additional metadata
            metadata = self.api.get_current_metadata(app_id)

            app_info = {
                "id": app_id,
                "name": attributes.get("name"),
                "bundleId": attributes.get("bundleId"),
                "sku": attributes.get("sku"),
                "primary_locale": attributes.get("primaryLocale"),
                "metadata": metadata,
                "editable_version": self.api.get_editable_version(app_id),
                "last_updated": datetime.now().isoformat(),
            }

            portfolio.append(app_info)
            portfolio_dict[app_id] = app_info

        # Only cache if in batch mode
        if self._in_batch_mode:
            self._temp_cache = portfolio_dict

        return portfolio

    def update_app_listing(
        self,
        app_id: str,
        updates: Dict[str, Any],
        locale: str = "en-US",
        validate: bool = True,
    ) -> Dict[str, bool]:
        """
        Update app store listing with multiple fields.

        Args:
            app_id: The app ID to update
            updates: Dictionary of field updates
            locale: Locale to update
            validate: Whether to validate inputs

        Returns:
            Dictionary showing success/failure for each update
        """
        if validate:
            app_id = validate_app_id(app_id)
            locale = validate_locale(locale)

        results = {}

        # Handle app-level updates (always available)
        app_level_fields = ["name", "subtitle", "privacy_url"]
        for field in app_level_fields:
            if field in updates:
                value = updates[field]
                try:
                    if field == "name":
                        if validate and len(value) > 30:
                            raise ValidationError(
                                f"App name too long: {len(value)} chars (max 30)"
                            )
                        results[field] = self.api.update_app_name(app_id, value, locale)
                    elif field == "subtitle":
                        if validate and len(value) > 30:
                            raise ValidationError(
                                f"App subtitle too long: {len(value)} chars (max 30)"
                            )
                        results[field] = self.api.update_app_subtitle(
                            app_id, value, locale
                        )
                    elif field == "privacy_url":
                        results[field] = self.api.update_privacy_url(
                            app_id, value, locale
                        )
                except Exception as e:
                    results[field] = False
                    print(f"Failed to update {field}: {e}")

        # Handle version-level updates (requires editable version)
        version_level_fields = ["description", "keywords", "promotional_text"]
        version_updates = {
            k: v for k, v in updates.items() if k in version_level_fields
        }

        if version_updates:
            # Check for editable version
            editable_version = self.api.get_editable_version(app_id)
            if not editable_version:
                for field in version_updates:
                    results[field] = False
                print(
                    f"No editable version found for app {app_id}. "
                    f"Cannot update version-level fields."
                )
            else:
                for field, value in version_updates.items():
                    try:
                        if field == "description":
                            if validate and len(value) > 4000:
                                raise ValidationError(
                                    f"Description too long: {len(value)} chars (max 4000)"
                                )
                            results[field] = self.api.update_app_description(
                                app_id, value, locale
                            )
                        elif field == "keywords":
                            if validate and len(value) > 100:
                                raise ValidationError(
                                    f"Keywords too long: {len(value)} chars (max 100)"
                                )
                            results[field] = self.api.update_app_keywords(
                                app_id, value, locale
                            )
                        elif field == "promotional_text":
                            if validate and len(value) > 170:
                                raise ValidationError(
                                    f"Promotional text too long: {len(value)} chars (max 170)"
                                )
                            results[field] = self.api.update_promotional_text(
                                app_id, value, locale
                            )
                    except Exception as e:
                        results[field] = False
                        print(f"Failed to update {field}: {e}")

        # Format return value to match expected structure
        updated = [field for field, success in results.items() if success]
        errors = {
            field: "Update failed" for field, success in results.items() if not success
        }

        return {
            "success": all(results.values()) if results else True,
            "updated": updated,
            "errors": errors,
        }

    def batch_update_apps(
        self,
        updates: Dict[str, Dict[str, Any]],
        locale: str = "en-US",
        continue_on_error: bool = True,
    ) -> Dict[str, Dict[str, bool]]:
        """
        Update multiple apps with different field updates.

        Args:
            updates: Dictionary mapping app IDs to their updates
            locale: Locale to update
            continue_on_error: Whether to continue if one app fails

        Returns:
            Dictionary mapping app IDs to their update results
        """
        locale = validate_locale(locale)
        results = {}

        for app_id, app_updates in updates.items():
            try:
                app_id = validate_app_id(app_id)
                results[app_id] = self.update_app_listing(app_id, app_updates, locale)
            except Exception as e:
                results[app_id] = {"error": str(e)}
                if not continue_on_error:
                    break
                print(f"Error updating app {app_id}: {e}")

        return {"results": results}

    def standardize_app_names(
        self,
        app_ids: Optional[List[str]] = None,
        name_pattern: str = "{original_name}",
        locale: str = "en-US",
        dry_run: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Standardize app names across the portfolio.

        Args:
            app_ids: List of app IDs to update (all apps if None)
            name_pattern: Pattern for new names (supports {original_name}, {bundle_id})
            locale: Locale to update
            dry_run: If True, only show what would be changed

        Returns:
            Dictionary showing proposed/actual changes
        """
        # Use batch operation context for caching
        with self.batch_operation():
            portfolio = self.get_app_portfolio()
            portfolio_dict = {app["id"]: app for app in portfolio}

            if app_ids is None:
                app_ids = [app["id"] for app in portfolio]
            else:
                app_ids = [validate_app_id(app_id) for app_id in app_ids]

            results = {}

            for app_id in app_ids:
                if app_id not in portfolio_dict:
                    results[app_id] = {"error": "App not found in portfolio"}
                    continue

                app_info = portfolio_dict[app_id]
                original_name = app_info["name"]
                bundle_id = app_info["bundleId"]

                # Generate new name
                new_name = name_pattern.format(
                    original_name=original_name, bundle_id=bundle_id, app_id=app_id
                )

                # Validate length
                if len(new_name) > 30:
                    new_name = truncate_string(new_name, 30, "")

                results[app_id] = {
                    "original_name": original_name,
                    "new_name": new_name,
                    "changed": original_name != new_name,
                }

                if not dry_run and original_name != new_name:
                    try:
                        success = self.api.update_app_name(app_id, new_name, locale)
                        results[app_id]["updated"] = success
                    except Exception as e:
                        results[app_id]["error"] = str(e)

            return results

    def prepare_version_releases(
        self,
        app_versions: Optional[Dict[str, str]] = None,
        release_notes: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Prepare new versions for multiple apps.

        Args:
            app_versions: Dictionary mapping app IDs to version strings
            dry_run: If True, only validate without creating

        Returns:
            Dictionary showing creation results or validation
        """
        # Use batch operation context for caching
        with self.batch_operation():
            results = {"updated": [], "skipped": [], "errors": {}}

            # If no app_versions provided, get all apps from portfolio
            if app_versions is None:
                portfolio = self.get_app_portfolio()
                app_versions = {}
                for app in portfolio:
                    # Check if app has editable version
                    editable_version = self.api.get_editable_version(app["id"])
                    if not editable_version:
                        results["skipped"].append(app["id"])
                    else:
                        # Generate next version (simple increment)
                        current_version = editable_version["attributes"].get(
                            "versionString", "1.0"
                        )
                        # Simple version increment logic (you may want to customize)
                        parts = current_version.split(".")
                        if len(parts) >= 2:
                            parts[-1] = str(int(parts[-1]) + 1)
                            app_versions[app["id"]] = ".".join(parts)
                        else:
                            app_versions[app["id"]] = current_version + ".1"

            for app_id, version_string in app_versions.items():
                try:
                    app_id = validate_app_id(app_id)
                    version_string = validate_version_string(version_string)

                    # Check if version already exists
                    existing_versions = self.api.get_app_store_versions(app_id)
                    existing_version_strings = []
                    if existing_versions and "data" in existing_versions:
                        existing_version_strings = [
                            v["attributes"]["versionString"]
                            for v in existing_versions["data"]
                        ]

                    if version_string in existing_version_strings:
                        results["skipped"].append(app_id)
                        results["errors"][
                            app_id
                        ] = f"Version {version_string} already exists"
                        continue

                    if dry_run:
                        # Would be updated
                        results["updated"].append(app_id)
                    else:
                        # Create the version
                        new_version = self.api.create_app_store_version(
                            app_id, version_string
                        )
                        if new_version:
                            results["updated"].append(app_id)
                        else:
                            results["errors"][
                                app_id
                            ] = f"Failed to create version {version_string}"

                except Exception as e:
                    results["errors"][app_id] = str(e)

            return results

    def get_localization_status(
        self, app_ids: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get localization status for apps.

        Args:
            app_ids: List of app IDs to check (all apps if None)

        Returns:
            Dictionary showing localization status for each app
        """
        try:
            # Use batch operation context for caching
            with self.batch_operation():
                portfolio = self.get_app_portfolio()
                portfolio_dict = {app["id"]: app for app in portfolio}

                if app_ids is None:
                    app_ids = [app["id"] for app in portfolio]
                else:
                    app_ids = [validate_app_id(app_id) for app_id in app_ids]

                results = {}

                for app_id in app_ids:
                    if app_id not in portfolio_dict:
                        results[app_id] = {"error": "App not found"}
                        continue

                    app_data = portfolio_dict[app_id]
                    metadata = app_data.get("metadata", {})

                    # Analyze app-level localizations
                    app_localizations = metadata.get("app_localizations", {})
                    version_localizations = metadata.get("version_localizations", {})

                    results[app_id] = {
                        "app_name": app_data["name"],
                        "app_level_locales": list(app_localizations.keys()),
                        "version_level_locales": list(version_localizations.keys()),
                        "total_locales": len(
                            set(app_localizations.keys())
                            | set(version_localizations.keys())
                        ),
                        "missing_app_level": [],
                        "missing_version_level": [],
                    }

                    # Check for missing localizations
                    all_locales = set(app_localizations.keys()) | set(
                        version_localizations.keys()
                    )
                    for locale in all_locales:
                        if locale not in app_localizations:
                            results[app_id]["missing_app_level"].append(locale)
                        if locale not in version_localizations:
                            results[app_id]["missing_version_level"].append(locale)

                return results
        except Exception as e:
            # Log error and re-raise
            import logging

            logging.error(f"Error in get_localization_status: {e}")
            raise

    def export_app_metadata(
        self,
        output_path: str,
        app_ids: Optional[List[str]] = None,
        include_versions: bool = True,
    ) -> bool:
        """
        Export app metadata to CSV for analysis or backup.

        Args:
            output_path: Path to save CSV file
            app_ids: List of app IDs to export (all if None)
            include_versions: Whether to include version information

        Returns:
            True if export successful, False otherwise
        """
        try:
            import pandas as pd

            # Use batch operation context for caching
            with self.batch_operation():
                portfolio = self.get_app_portfolio()
                portfolio_dict = {app["id"]: app for app in portfolio}

                if app_ids is None:
                    app_ids = [app["id"] for app in portfolio]
                else:
                    app_ids = [validate_app_id(app_id) for app_id in app_ids]

                export_data = []

                for app_id in app_ids:
                    if app_id not in portfolio_dict:
                        continue

                    app_data = portfolio_dict[app_id]
                    metadata = app_data.get("metadata", {})

                    # Basic app information
                    row = {
                        "app_id": app_id,
                        "name": app_data.get("name", ""),
                        "bundle_id": app_data.get("bundleId", ""),
                        "sku": app_data.get("sku", ""),
                        "primary_locale": app_data.get("primary_locale", ""),
                    }

                    # App-level localizations
                    app_localizations = metadata.get("app_localizations", {})
                    for locale, data in app_localizations.items():
                        row[f"name_{locale}"] = data.get("name")
                        row[f"subtitle_{locale}"] = data.get("subtitle")
                        row[f"privacy_url_{locale}"] = data.get("privacyPolicyUrl")

                    # Version information
                    if include_versions:
                        version_info = metadata.get("version_info", {})
                        row["current_version"] = version_info.get("versionString")
                        row["version_state"] = version_info.get("appStoreState")

                        # Check for editable version
                        editable_version = app_data.get("editable_version")
                        if editable_version and isinstance(editable_version, dict):
                            row["editable_version"] = editable_version.get(
                                "attributes", {}
                            ).get("versionString")
                            row["editable_state"] = editable_version.get(
                                "attributes", {}
                            ).get("appStoreState")

                        # Version-level localizations
                        version_localizations = metadata.get(
                            "version_localizations", {}
                        )
                        for locale, data in version_localizations.items():
                            row[f"description_{locale}"] = truncate_string(
                                data.get("description", ""), 100
                            )
                            row[f"keywords_{locale}"] = data.get("keywords")
                            row[f"promo_text_{locale}"] = data.get("promotionalText")

                    export_data.append(row)

                # Create DataFrame and export
                df = pd.DataFrame(export_data)
                df.to_csv(output_path, index=False)
                return True

        except PermissionError:
            # Re-raise permission errors as-is
            raise
        except Exception as e:
            import logging

            logging.error(f"Error exporting metadata: {e}")
            return False

    def _validate_app_name(self, name: str) -> str:
        """
        Validate and sanitize app name.

        Args:
            name: App name to validate

        Returns:
            Validated app name

        Raises:
            ValidationError: If name is invalid
        """
        if not name:
            raise ValidationError("App name cannot be empty")
        if len(name) > 30:
            raise ValidationError(
                f"App name too long ({len(name)} chars). Maximum is 30 characters."
            )
        return sanitize_app_name(name)

    def _validate_promotional_text(self, text: str) -> str:
        """
        Validate promotional text.

        Args:
            text: Promotional text to validate

        Returns:
            Validated text

        Raises:
            ValidationError: If text is invalid
        """
        if len(text) > 170:
            raise ValidationError(
                f"Promotional text too long ({len(text)} chars). Maximum is 170 characters."
            )
        return text

    def _format_for_export(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format data for CSV export.

        Args:
            data: Data to format

        Returns:
            Formatted data suitable for CSV export
        """
        formatted = {}
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                formatted[key] = str(value)
            elif isinstance(value, bool):
                formatted[key] = "Yes" if value else "No"
            elif value is None:
                formatted[key] = ""
            else:
                formatted[key] = value
        return formatted


def create_metadata_manager(
    key_id: str, issuer_id: str, private_key_path: str, vendor_number: str
) -> MetadataManager:
    """
    Convenience function to create a MetadataManager with API client.

    Args:
        key_id: App Store Connect API key ID
        issuer_id: App Store Connect API issuer ID
        private_key_path: Path to private key file
        vendor_number: Vendor number

    Returns:
        Configured MetadataManager instance
    """
    api = AppStoreConnectAPI(
        key_id=key_id,
        issuer_id=issuer_id,
        private_key_path=private_key_path,
        vendor_number=vendor_number,
    )

    return MetadataManager(api)
