#!/usr/bin/env python3
"""
App metadata management examples for appstore-connect-client.

This example demonstrates how to:
1. Update app names and subtitles
2. Update descriptions and keywords (requires editable version)
3. Create new app versions
4. Handle different locales
"""

import os
from appstore_connect import AppStoreConnectAPI
from appstore_connect.exceptions import AppStoreConnectError, ValidationError, PermissionError

def main():
    """Demonstrate app metadata management."""
    
    # Initialize API client
    api = AppStoreConnectAPI(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
    )
    
    # Replace with your actual app ID
    app_id = "123456789"
    
    try:
        print(f"🔍 Working with app ID: {app_id}")
        
        # Get current metadata to see what we're working with
        print("\n📋 Getting current metadata...")
        metadata = api.get_current_metadata(app_id)
        
        # Show current app name and subtitle
        if metadata['app_localizations']:
            for locale, data in metadata['app_localizations'].items():
                print(f"  {locale}:")
                print(f"    Name: {data.get('name', 'N/A')}")
                print(f"    Subtitle: {data.get('subtitle', 'N/A')}")
        
        # Example 1: Update app name (always available)
        print("\n✏️ Updating app name...")
        try:
            success = api.update_app_name(
                app_id=app_id,
                name="My Awesome App Updated",
                locale="en-US"
            )
            if success:
                print("✅ App name updated successfully!")
            else:
                print("❌ Failed to update app name")
        except ValidationError as e:
            print(f"❌ Validation error: {e}")
        except PermissionError as e:
            print(f"❌ Permission error: {e}")
            print("This requires an API key with app management permissions")
        
        # Example 2: Update app subtitle (always available)
        print("\n✏️ Updating app subtitle...")
        try:
            success = api.update_app_subtitle(
                app_id=app_id,
                subtitle="The best app ever made",
                locale="en-US"
            )
            if success:
                print("✅ App subtitle updated successfully!")
            else:
                print("❌ Failed to update app subtitle")
        except ValidationError as e:
            print(f"❌ Validation error: {e}")
        except PermissionError as e:
            print(f"❌ Permission error: {e}")
        
        # Example 3: Check for editable version
        print("\n🔍 Checking for editable version...")
        editable_version = api.get_editable_version(app_id)
        
        if editable_version:
            version_string = editable_version['attributes']['versionString']
            state = editable_version['attributes']['appStoreState']
            print(f"✅ Found editable version: v{version_string} ({state})")
            
            # Example 4: Update description (requires editable version)
            print("\n✏️ Updating app description...")
            try:
                new_description = \"\"\"
                This is an amazing app that does incredible things!
                
                Features:
                • Feature 1: Does something awesome
                • Feature 2: Makes your life better
                • Feature 3: Saves you time and money
                
                Download now and experience the difference!
                \"\"\"
                
                success = api.update_app_description(
                    app_id=app_id,
                    description=new_description.strip(),
                    locale="en-US"
                )
                if success:
                    print("✅ App description updated successfully!")
                else:
                    print("❌ Failed to update app description")
            except ValidationError as e:
                print(f"❌ Validation error: {e}")
            except PermissionError as e:
                print(f"❌ Permission error: {e}")
            
            # Example 5: Update keywords (requires editable version)
            print("\n✏️ Updating app keywords...")
            try:
                success = api.update_app_keywords(
                    app_id=app_id,
                    keywords="productivity,utility,business,efficiency,tool",
                    locale="en-US"
                )
                if success:
                    print("✅ App keywords updated successfully!")
                else:
                    print("❌ Failed to update app keywords")
            except ValidationError as e:
                print(f"❌ Validation error: {e}")
            except PermissionError as e:
                print(f"❌ Permission error: {e}")
            
        else:
            print("ℹ️ No editable version found")
            print("To update description/keywords, create a new version first")
            
            # Example 6: Create new version
            print("\n📦 Creating new app version...")
            try:
                new_version = api.create_app_store_version(
                    app_id=app_id,
                    version_string="1.1.0"
                )
                if new_version:
                    print("✅ New version created successfully!")
                    print(f"Version ID: {new_version['data']['id']}")
                else:
                    print("❌ Failed to create new version")
            except ValidationError as e:
                print(f"❌ Validation error: {e}")
            except PermissionError as e:
                print(f"❌ Permission error: {e}")
        
        # Example 7: Multi-locale updates
        print("\n🌍 Updating metadata for multiple locales...")
        locales = ["en-US", "es-ES", "fr-FR"]
        
        for locale in locales:
            try:
                # Update privacy policy URL for each locale
                success = api.update_privacy_url(
                    app_id=app_id,
                    privacy_url=f"https://myapp.com/privacy-{locale.lower()}",
                    locale=locale
                )
                if success:
                    print(f"✅ Privacy URL updated for {locale}")
                else:
                    print(f"❌ Failed to update privacy URL for {locale}")
            except Exception as e:
                print(f"❌ Error updating {locale}: {e}")
        
        print("\n🎉 Metadata management examples completed!")
        
    except AppStoreConnectError as e:
        print(f"❌ API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()