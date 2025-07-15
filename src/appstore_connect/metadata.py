"""
App metadata management utilities for appstore-connect-client.

This module provides high-level functions for managing app store listings,
including batch operations, validation, and convenient wrapper methods.
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from .client import AppStoreConnectAPI
from .utils import (
    validate_app_id,
    validate_locale,
    validate_version_string,
    sanitize_app_name,
    truncate_string
)
from .exceptions import ValidationError, NotFoundError


class MetadataManager:
    """
    High-level metadata manager for App Store Connect apps.
    
    This class provides convenient methods for managing app metadata
    with built-in validation, error handling, and batch operations.
    """
    
    def __init__(self, api: AppStoreConnectAPI):
        """Initialize with an API client."""
        self.api = api
        self._app_cache = {}
        self._version_cache = {}
    
    def get_app_portfolio(self, refresh_cache: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get comprehensive information about all apps in the account.
        
        Args:
            refresh_cache: Whether to refresh the cached app data
            
        Returns:
            Dictionary mapping app IDs to app information
        """
        if not refresh_cache and self._app_cache:
            return self._app_cache
        
        apps_response = self.api.get_apps()
        if not apps_response or 'data' not in apps_response:
            return {}
        
        portfolio = {}
        for app in apps_response['data']:
            app_id = app['id']
            attributes = app['attributes']
            
            # Get additional metadata
            metadata = self.api.get_current_metadata(app_id)
            
            portfolio[app_id] = {
                'basic_info': {
                    'name': attributes.get('name'),
                    'bundle_id': attributes.get('bundleId'),
                    'sku': attributes.get('sku'),
                    'primary_locale': attributes.get('primaryLocale')
                },
                'metadata': metadata,
                'editable_version': self.api.get_editable_version(app_id),
                'last_updated': datetime.now().isoformat()
            }
        
        self._app_cache = portfolio
        return portfolio
    
    def update_app_listing(
        self,
        app_id: str,
        updates: Dict[str, Any],
        locale: str = "en-US",
        validate: bool = True
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
        app_level_fields = ['name', 'subtitle', 'privacy_url']
        for field in app_level_fields:
            if field in updates:
                value = updates[field]
                try:
                    if field == 'name':
                        if validate and len(value) > 30:
                            raise ValidationError(f"App name too long: {len(value)} chars (max 30)")
                        results[field] = self.api.update_app_name(app_id, value, locale)
                    elif field == 'subtitle':
                        if validate and len(value) > 30:
                            raise ValidationError(f"App subtitle too long: {len(value)} chars (max 30)")
                        results[field] = self.api.update_app_subtitle(app_id, value, locale)
                    elif field == 'privacy_url':
                        results[field] = self.api.update_privacy_url(app_id, value, locale)
                except Exception as e:
                    results[field] = False
                    print(f"Failed to update {field}: {e}")
        
        # Handle version-level updates (requires editable version)
        version_level_fields = ['description', 'keywords', 'promotional_text']
        version_updates = {k: v for k, v in updates.items() if k in version_level_fields}
        
        if version_updates:
            # Check for editable version
            editable_version = self.api.get_editable_version(app_id)
            if not editable_version:
                for field in version_updates:
                    results[field] = False
                print(f"No editable version found for app {app_id}. Cannot update version-level fields.")
            else:
                for field, value in version_updates.items():
                    try:
                        if field == 'description':
                            if validate and len(value) > 4000:
                                raise ValidationError(f"Description too long: {len(value)} chars (max 4000)")
                            results[field] = self.api.update_app_description(app_id, value, locale)
                        elif field == 'keywords':
                            if validate and len(value) > 100:
                                raise ValidationError(f"Keywords too long: {len(value)} chars (max 100)")
                            results[field] = self.api.update_app_keywords(app_id, value, locale)
                        elif field == 'promotional_text':
                            if validate and len(value) > 170:
                                raise ValidationError(f"Promotional text too long: {len(value)} chars (max 170)")
                            results[field] = self.api.update_promotional_text(app_id, value, locale)
                    except Exception as e:
                        results[field] = False
                        print(f"Failed to update {field}: {e}")
        
        return results
    
    def batch_update_apps(
        self,
        updates: Dict[str, Dict[str, Any]],
        locale: str = "en-US",
        continue_on_error: bool = True
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
                results[app_id] = {'error': str(e)}
                if not continue_on_error:
                    break
                print(f"Error updating app {app_id}: {e}")
        
        return results
    
    def standardize_app_names(
        self,
        app_ids: Optional[List[str]] = None,
        name_pattern: str = "{original_name}",
        locale: str = "en-US",
        dry_run: bool = True
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
        portfolio = self.get_app_portfolio()
        
        if app_ids is None:
            app_ids = list(portfolio.keys())
        else:
            app_ids = [validate_app_id(app_id) for app_id in app_ids]
        
        results = {}
        
        for app_id in app_ids:
            if app_id not in portfolio:
                results[app_id] = {'error': 'App not found in portfolio'}
                continue
            
            app_info = portfolio[app_id]
            original_name = app_info['basic_info']['name']
            bundle_id = app_info['basic_info']['bundle_id']
            
            # Generate new name
            new_name = name_pattern.format(
                original_name=original_name,
                bundle_id=bundle_id,
                app_id=app_id
            )
            
            # Validate length
            if len(new_name) > 30:
                new_name = truncate_string(new_name, 30, "")
            
            results[app_id] = {
                'original_name': original_name,
                'new_name': new_name,
                'changed': original_name != new_name
            }
            
            if not dry_run and original_name != new_name:
                try:
                    success = self.api.update_app_name(app_id, new_name, locale)
                    results[app_id]['updated'] = success
                except Exception as e:
                    results[app_id]['error'] = str(e)
        
        return results
    
    def prepare_version_releases(
        self,
        app_versions: Dict[str, str],
        dry_run: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Prepare new versions for multiple apps.
        
        Args:
            app_versions: Dictionary mapping app IDs to version strings
            dry_run: If True, only validate without creating
            
        Returns:
            Dictionary showing creation results or validation
        """
        results = {}
        
        for app_id, version_string in app_versions.items():
            try:
                app_id = validate_app_id(app_id)
                version_string = validate_version_string(version_string)
                
                # Check if version already exists
                existing_versions = self.api.get_app_store_versions(app_id)
                existing_version_strings = []
                if existing_versions and 'data' in existing_versions:
                    existing_version_strings = [
                        v['attributes']['versionString'] 
                        for v in existing_versions['data']
                    ]
                
                if version_string in existing_version_strings:
                    results[app_id] = {
                        'version': version_string,
                        'status': 'exists',
                        'message': f"Version {version_string} already exists"
                    }
                    continue
                
                if dry_run:
                    results[app_id] = {
                        'version': version_string,
                        'status': 'ready',
                        'message': f"Ready to create version {version_string}"
                    }
                else:
                    # Create the version
                    new_version = self.api.create_app_store_version(app_id, version_string)
                    if new_version:
                        results[app_id] = {
                            'version': version_string,
                            'status': 'created',
                            'version_id': new_version['data']['id'],
                            'message': f"Successfully created version {version_string}"
                        }
                    else:
                        results[app_id] = {
                            'version': version_string,
                            'status': 'failed',
                            'message': f"Failed to create version {version_string}"
                        }
                        
            except Exception as e:
                results[app_id] = {
                    'version': app_versions.get(app_id, 'unknown'),
                    'status': 'error',
                    'message': str(e)
                }
        
        return results
    
    def get_localization_status(
        self, 
        app_ids: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get localization status for apps.
        
        Args:
            app_ids: List of app IDs to check (all apps if None)
            
        Returns:
            Dictionary showing localization status for each app
        """
        portfolio = self.get_app_portfolio()
        
        if app_ids is None:
            app_ids = list(portfolio.keys())
        else:
            app_ids = [validate_app_id(app_id) for app_id in app_ids]
        
        results = {}
        
        for app_id in app_ids:
            if app_id not in portfolio:
                results[app_id] = {'error': 'App not found'}
                continue
            
            metadata = portfolio[app_id]['metadata']
            
            # Analyze app-level localizations
            app_localizations = metadata.get('app_localizations', {})
            version_localizations = metadata.get('version_localizations', {})
            
            results[app_id] = {
                'app_name': portfolio[app_id]['basic_info']['name'],
                'app_level_locales': list(app_localizations.keys()),
                'version_level_locales': list(version_localizations.keys()),
                'total_locales': len(set(app_localizations.keys()) | set(version_localizations.keys())),
                'missing_app_level': [],
                'missing_version_level': []
            }
            
            # Check for missing localizations
            all_locales = set(app_localizations.keys()) | set(version_localizations.keys())
            for locale in all_locales:
                if locale not in app_localizations:
                    results[app_id]['missing_app_level'].append(locale)
                if locale not in version_localizations:
                    results[app_id]['missing_version_level'].append(locale)
        
        return results
    
    def export_app_metadata(
        self, 
        output_path: str,
        app_ids: Optional[List[str]] = None,
        include_versions: bool = True
    ) -> None:
        """
        Export app metadata to CSV for analysis or backup.
        
        Args:
            output_path: Path to save CSV file
            app_ids: List of app IDs to export (all if None)
            include_versions: Whether to include version information
        """
        import pandas as pd
        
        portfolio = self.get_app_portfolio()
        
        if app_ids is None:
            app_ids = list(portfolio.keys())
        else:
            app_ids = [validate_app_id(app_id) for app_id in app_ids]
        
        export_data = []
        
        for app_id in app_ids:
            if app_id not in portfolio:
                continue
            
            app_info = portfolio[app_id]
            basic_info = app_info['basic_info']
            metadata = app_info['metadata']
            
            # Basic app information
            row = {
                'app_id': app_id,
                'name': basic_info['name'],
                'bundle_id': basic_info['bundle_id'],
                'sku': basic_info['sku'],
                'primary_locale': basic_info['primary_locale']
            }
            
            # App-level localizations
            app_localizations = metadata.get('app_localizations', {})
            for locale, data in app_localizations.items():
                row[f'name_{locale}'] = data.get('name')
                row[f'subtitle_{locale}'] = data.get('subtitle')
                row[f'privacy_url_{locale}'] = data.get('privacyPolicyUrl')
            
            # Version information
            if include_versions:
                version_info = metadata.get('version_info', {})
                row['current_version'] = version_info.get('versionString')
                row['version_state'] = version_info.get('appStoreState')
                
                # Check for editable version
                editable_version = app_info['editable_version']
                if editable_version:
                    row['editable_version'] = editable_version['attributes']['versionString']
                    row['editable_state'] = editable_version['attributes']['appStoreState']
                
                # Version-level localizations
                version_localizations = metadata.get('version_localizations', {})
                for locale, data in version_localizations.items():
                    row[f'description_{locale}'] = truncate_string(data.get('description', ''), 100)
                    row[f'keywords_{locale}'] = data.get('keywords')
                    row[f'promo_text_{locale}'] = data.get('promotionalText')
            
            export_data.append(row)
        
        # Create DataFrame and export
        df = pd.DataFrame(export_data)
        df.to_csv(output_path, index=False)


def create_metadata_manager(
    key_id: str,
    issuer_id: str,
    private_key_path: str,
    vendor_number: str
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
        vendor_number=vendor_number
    )
    
    return MetadataManager(api)