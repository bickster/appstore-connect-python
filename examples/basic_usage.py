#!/usr/bin/env python3
"""
Basic usage examples for appstore-connect-client.

This example demonstrates how to:
1. Initialize the API client
2. Fetch sales reports  
3. Manage app metadata
4. Handle errors appropriately
"""

import os
from datetime import date, timedelta
from appstore_connect import AppStoreConnectAPI
from appstore_connect.exceptions import AppStoreConnectError, AuthenticationError

def main():
    """Demonstrate basic usage of the AppStoreConnectAPI."""
    
    # Initialize API client with credentials
    # In production, load these from environment variables or config file
    api = AppStoreConnectAPI(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER'),
        app_ids=['123456789', '987654321']  # Optional: filter to specific apps
    )
    
    try:
        # Example 1: Get sales data for yesterday
        print("📊 Fetching sales data...")
        yesterday = date.today() - timedelta(days=1)
        sales_df = api.get_sales_report(yesterday)
        
        if not sales_df.empty:
            print(f"✅ Found {len(sales_df)} sales records")
            print(f"Total units sold: {sales_df['Units'].sum()}")
            print(f"Total revenue: ${sales_df['Developer Proceeds'].sum():.2f}")
        else:
            print("No sales data found for yesterday")
            
        # Example 2: Get subscription data
        print("\n📊 Fetching subscription data...")
        subscription_df = api.get_subscription_report(yesterday)
        
        if not subscription_df.empty:
            print(f"✅ Found {len(subscription_df)} subscription records")
        else:
            print("No subscription data found")
            
        # Example 3: List all apps
        print("\n📱 Listing all apps...")
        apps = api.get_apps()
        
        if apps and 'data' in apps:
            print(f"✅ Found {len(apps['data'])} apps in account:")
            for app in apps['data'][:3]:  # Show first 3 apps
                print(f"  - {app['attributes']['name']} (ID: {app['id']})")
        else:
            print("No apps found")
            
        # Example 4: Get metadata for first app
        if apps and 'data' in apps and apps['data']:
            app_id = apps['data'][0]['id']
            app_name = apps['data'][0]['attributes']['name']
            
            print(f"\n📋 Getting metadata for {app_name}...")
            metadata = api.get_current_metadata(app_id)
            
            print(f"✅ App metadata retrieved:")
            print(f"  - App info fields: {len(metadata['app_info'])}")
            print(f"  - App localizations: {len(metadata['app_localizations'])}")
            print(f"  - Version info fields: {len(metadata['version_info'])}")
            print(f"  - Version localizations: {len(metadata['version_localizations'])}")
            
            # Example 5: Check for editable version
            editable_version = api.get_editable_version(app_id)
            if editable_version:
                version_string = editable_version['attributes']['versionString']
                state = editable_version['attributes']['appStoreState']
                print(f"✅ Found editable version: v{version_string} ({state})")
            else:
                print("ℹ️ No editable version found (all versions are live)")
        
        print("\n🎉 All examples completed successfully!")
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("Please check your API credentials")
    except AppStoreConnectError as e:
        print(f"❌ API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()