#!/usr/bin/env python3
"""
Batch metadata operations examples for appstore-connect-client.

This example demonstrates how to:
1. Use the MetadataManager for portfolio management
2. Perform batch updates across multiple apps
3. Standardize app names and descriptions
4. Manage localization across apps
5. Prepare version releases
"""

import os
from appstore_connect import create_metadata_manager
from appstore_connect.exceptions import AppStoreConnectError, PermissionError

def main():
    """Demonstrate batch metadata management capabilities."""
    
    # Create metadata manager
    manager = create_metadata_manager(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
    )
    
    try:
        print("🎯 Batch Metadata Management Demo")
        print("=" * 40)
        
        # Example 1: Get app portfolio overview
        print("\n📱 Getting app portfolio overview...")
        portfolio = manager.get_app_portfolio()
        
        print(f"✅ Found {len(portfolio)} apps in portfolio:")
        for app_id, info in list(portfolio.items())[:3]:  # Show first 3
            basic_info = info['basic_info']
            print(f"  • {basic_info['name']} (ID: {app_id})")
            print(f"    Bundle ID: {basic_info['bundle_id']}")
            
            # Check if version is editable
            if info['editable_version']:
                version = info['editable_version']['attributes']['versionString']
                state = info['editable_version']['attributes']['appStoreState']
                print(f"    ✏️ Editable version: v{version} ({state})")
            else:
                print(f"    🔒 No editable version")
            print()
        
        # Example 2: Batch update multiple apps
        print(f"\n🔄 Performing batch updates...")
        
        # Get first few app IDs for demo
        demo_app_ids = list(portfolio.keys())[:2]
        
        batch_updates = {}
        for i, app_id in enumerate(demo_app_ids):
            batch_updates[app_id] = {
                'subtitle': f"Updated Subtitle {i+1}",
                'privacy_url': f"https://example.com/privacy-{i+1}",
                # These require editable versions:
                'keywords': f"productivity,utility,business,tool{i+1}",
                'promotional_text': f"Amazing app #{i+1} - Download now!"
            }
        
        print(f"Updating {len(batch_updates)} apps...")
        try:
            results = manager.batch_update_apps(
                updates=batch_updates,
                locale="en-US",
                continue_on_error=True
            )
            
            for app_id, app_results in results.items():
                app_name = portfolio[app_id]['basic_info']['name']
                print(f"\n  📱 {app_name} (ID: {app_id}):")
                
                if 'error' in app_results:
                    print(f"    ❌ Error: {app_results['error']}")
                else:
                    for field, success in app_results.items():
                        status = "✅" if success else "❌"
                        print(f"    {status} {field}")
        
        except PermissionError as e:
            print(f"ℹ️ Permission error (expected with read-only credentials): {e}")
        
        # Example 3: Standardize app names (dry run)
        print(f"\n📝 Standardizing app names (dry run)...")
        
        standardization_results = manager.standardize_app_names(
            app_ids=demo_app_ids,
            name_pattern="Bickster {original_name}",
            dry_run=True  # Safe - won't make changes
        )
        
        for app_id, result in standardization_results.items():
            if result['changed']:
                print(f"  📱 {result['original_name']} → {result['new_name']}")
            else:
                print(f"  📱 {result['original_name']} (no change needed)")
        
        # Example 4: Prepare version releases (dry run)
        print(f"\n📦 Preparing version releases (dry run)...")
        
        version_plans = {}
        for i, app_id in enumerate(demo_app_ids):
            # Increment minor version for demo
            current_version = portfolio[app_id]['metadata']['version_info'].get('versionString', '1.0.0')
            # Simple version increment logic for demo
            try:
                major, minor, patch = current_version.split('.')
                new_version = f"{major}.{int(minor)+1}.0"
                version_plans[app_id] = new_version
            except:
                version_plans[app_id] = "2.0.0"  # Fallback
        
        version_results = manager.prepare_version_releases(
            app_versions=version_plans,
            dry_run=True  # Safe - won't create versions
        )
        
        for app_id, result in version_results.items():
            app_name = portfolio[app_id]['basic_info']['name']
            print(f"  📱 {app_name}: {result['status']} - {result['message']}")
        
        # Example 5: Localization analysis
        print(f"\n🌍 Localization status analysis...")
        
        localization_status = manager.get_localization_status(app_ids=demo_app_ids)
        
        for app_id, status in localization_status.items():
            if 'error' in status:
                continue
                
            print(f"\n  📱 {status['app_name']}:")
            print(f"    Total locales: {status['total_locales']}")
            print(f"    App-level locales: {len(status['app_level_locales'])}")
            print(f"    Version-level locales: {len(status['version_level_locales'])}")
            
            if status['missing_app_level']:
                print(f"    ⚠️ Missing app-level: {', '.join(status['missing_app_level'])}")
            if status['missing_version_level']:
                print(f"    ⚠️ Missing version-level: {', '.join(status['missing_version_level'])}")
        
        # Example 6: Export metadata for analysis
        print(f"\n💾 Exporting app metadata...")
        export_path = "/tmp/app_metadata_export.csv"
        
        manager.export_app_metadata(
            output_path=export_path,
            app_ids=demo_app_ids,
            include_versions=True
        )
        print(f"✅ Metadata exported to: {export_path}")
        
        # Example 7: Advanced batch operations
        print(f"\n🚀 Advanced batch operations...")
        
        # Simulate A/B testing subtitle variations
        subtitle_variations = {
            demo_app_ids[0]: "Boost Your Productivity",
            demo_app_ids[1]: "Get More Done Daily"
        }
        
        print(f"A/B testing subtitle variations:")
        for app_id, subtitle in subtitle_variations.items():
            app_name = portfolio[app_id]['basic_info']['name']
            print(f"  📱 {app_name}: '{subtitle}'")
        
        # In a real scenario, you would:
        # 1. Apply variations with manager.batch_update_apps()
        # 2. Monitor performance metrics
        # 3. Choose winning variations
        # 4. Apply winners to all similar apps
        
        print(f"\n🎯 Portfolio optimization opportunities:")
        
        # Analyze for optimization opportunities
        apps_without_subtitles = []
        apps_with_old_versions = []
        
        for app_id, info in portfolio.items():
            # Check for missing subtitles
            app_localizations = info['metadata'].get('app_localizations', {})
            en_us_locale = app_localizations.get('en-US', {})
            if not en_us_locale.get('subtitle'):
                apps_without_subtitles.append(info['basic_info']['name'])
            
            # Check for potentially old versions
            version_info = info['metadata'].get('version_info', {})
            version_string = version_info.get('versionString', '')
            if version_string and version_string.startswith('1.0'):
                apps_with_old_versions.append(info['basic_info']['name'])
        
        if apps_without_subtitles:
            print(f"  📝 Apps missing subtitles: {len(apps_without_subtitles)}")
            for name in apps_without_subtitles[:3]:
                print(f"    • {name}")
        
        if apps_with_old_versions:
            print(f"  📦 Apps with v1.0.x versions: {len(apps_with_old_versions)}")
            for name in apps_with_old_versions[:3]:
                print(f"    • {name}")
        
        print(f"\n🎉 Batch metadata management demo completed!")
        print(f"\nThis demo showed read-only operations and dry runs.")
        print(f"To perform actual updates, ensure you have API keys with write permissions.")
        
    except AppStoreConnectError as e:
        print(f"❌ API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()