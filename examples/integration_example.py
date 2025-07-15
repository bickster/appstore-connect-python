#!/usr/bin/env python3
"""
Integration example showing how to use appstore-connect-client
as a replacement for or alongside existing App Store Connect integrations.

This example demonstrates:
1. Drop-in replacement for existing API calls
2. Enhanced functionality with new features
3. Migration path from custom implementations
4. Integration with existing data processing pipelines
"""

import os
import pandas as pd
from datetime import date, timedelta
from appstore_connect import (
    AppStoreConnectAPI,
    ReportProcessor,
    MetadataManager,
    create_report_processor,
    create_metadata_manager
)
from appstore_connect.exceptions import AppStoreConnectError


def legacy_api_example():
    """Example showing legacy-style API usage (backward compatible)."""
    print("🔄 Legacy API Usage (Backward Compatible)")
    print("-" * 45)
    
    # Initialize exactly like the original BicksterAppStoreSales implementation
    api = AppStoreConnectAPI(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER'),
        app_ids=['1134998522', '1240275160', '1046178667']  # Bickster apps
    )
    
    try:
        # This works exactly like the original implementation
        yesterday = date.today() - timedelta(days=1)
        
        # Get sales report (same method signature)
        sales_df = api.get_sales_report(yesterday)
        print(f"✅ Sales data: {len(sales_df)} records")
        
        # Get subscription report (same method signature)
        subscription_df = api.get_subscription_report(yesterday)
        print(f"✅ Subscription data: {len(subscription_df)} records")
        
        # Multi-day fetch (enhanced but compatible)
        reports = api.fetch_multiple_days(days=7)
        sales_data = reports.get('sales', [])
        print(f"✅ 7-day sales: {len(sales_data)} report chunks")
        
        # NEW: Enhanced metadata capabilities (not in original)
        apps = api.get_apps()
        if apps and 'data' in apps:
            print(f"✅ Account has {len(apps['data'])} apps")
        
    except AppStoreConnectError as e:
        print(f"❌ API Error: {e}")


def enhanced_reporting_example():
    """Example showing enhanced reporting capabilities."""
    print("\n📊 Enhanced Reporting Features")
    print("-" * 35)
    
    # Use the enhanced ReportProcessor
    processor = create_report_processor(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER'),
        app_ids=['1134998522', '1240275160', '1046178667']
    )
    
    try:
        # Get comprehensive analytics (NEW)
        summary = processor.get_sales_summary(days=30)
        overall = summary['summary']
        
        print(f"📈 30-Day Performance:")
        print(f"  • Revenue: ${overall['total_revenue']:,.2f}")
        print(f"  • Units: {overall['total_units']:,}")
        print(f"  • Apps: {overall['unique_apps']}")
        print(f"  • Countries: {overall['countries']}")
        
        # App ranking (NEW)
        ranking = processor.get_app_performance_ranking(days=30, metric='revenue')
        print(f"\n🏆 Top Apps by Revenue:")
        for app in ranking[:3]:
            print(f"  #{app['rank']}: {app['name']} - ${app['revenue']:,.2f}")
        
        # Period comparison (NEW)
        comparison = processor.compare_periods(current_days=30, comparison_days=30)
        revenue_change = comparison['changes']['total_revenue']['change_percent']
        direction = "📈" if revenue_change > 0 else "📉" if revenue_change < 0 else "➡️"
        print(f"\n{direction} Revenue Change: {revenue_change:+.1f}%")
        
    except AppStoreConnectError as e:
        print(f"❌ Error: {e}")


def metadata_management_example():
    """Example showing metadata management capabilities."""
    print("\n🎯 Metadata Management Features")
    print("-" * 35)
    
    # Use the MetadataManager (completely NEW functionality)
    manager = create_metadata_manager(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
    )
    
    try:
        # Get portfolio overview
        portfolio = manager.get_app_portfolio()
        print(f"📱 Portfolio: {len(portfolio)} apps")
        
        # Show app details
        for app_id, info in list(portfolio.items())[:2]:  # First 2 apps
            basic_info = info['basic_info']
            print(f"\n  • {basic_info['name']}")
            print(f"    Bundle ID: {basic_info['bundle_id']}")
            
            # Check for optimization opportunities
            metadata = info['metadata']
            app_localizations = metadata.get('app_localizations', {})
            en_us = app_localizations.get('en-US', {})
            
            if not en_us.get('subtitle'):
                print(f"    ⚠️ Missing subtitle - optimization opportunity")
            
            if info['editable_version']:
                version = info['editable_version']['attributes']['versionString']
                print(f"    ✏️ Editable version: v{version}")
            else:
                print(f"    🔒 No editable version")
        
        # Localization analysis
        localization_status = manager.get_localization_status()
        apps_needing_localization = [
            info for info in localization_status.values()
            if 'error' not in info and info['total_locales'] < 3
        ]
        
        if apps_needing_localization:
            print(f"\n🌍 {len(apps_needing_localization)} apps could benefit from more localizations")
        
    except AppStoreConnectError as e:
        print(f"❌ Error: {e}")


def data_pipeline_integration_example():
    """Example showing integration with data processing pipelines."""
    print("\n🔄 Data Pipeline Integration")
    print("-" * 30)
    
    try:
        # This mimics how you might integrate with existing data processing
        # like the BicksterAppStoreSales aggregation system
        
        api = AppStoreConnectAPI(
            key_id=os.getenv('APP_STORE_KEY_ID'),
            issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
            private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
            vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
        )
        
        # Fetch data for a week (like weekly master file updates)
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=6)
        
        reports = api.fetch_multiple_days(start_date=start_date, end_date=end_date)
        
        # Process like BicksterAppStoreSales would
        all_sales_data = []
        for sales_df in reports.get('sales', []):
            if not sales_df.empty:
                # Add any processing that matches existing pipeline
                sales_df['processed_date'] = pd.Timestamp.now()
                all_sales_data.append(sales_df)
        
        if all_sales_data:
            combined_df = pd.concat(all_sales_data, ignore_index=True)
            print(f"✅ Processed {len(combined_df)} sales records for the week")
            
            # Calculate metrics that might go into master files
            by_app = combined_df.groupby('Apple Identifier').agg({
                'Units': 'sum',
                'Developer Proceeds': 'sum'
            }).reset_index()
            
            print(f"📊 Weekly summary by app:")
            for _, row in by_app.iterrows():
                print(f"  App {row['Apple Identifier']}: {row['Units']} units, ${row['Developer Proceeds']:.2f}")
        
        # This data could then be fed into existing aggregation systems
        # or replace the existing App Store Connect integration entirely
        
    except AppStoreConnectError as e:
        print(f"❌ Error: {e}")


def migration_guide_example():
    """Example showing migration from existing implementations."""
    print("\n🚀 Migration Guide")
    print("-" * 18)
    
    print("Migration from BicksterAppStoreSales AppStoreConnectAPI:")
    print()
    print("BEFORE (BicksterAppStoreSales):")
    print("  from src.connectors.app_store_connect import AppStoreConnectAPI")
    print("  api = AppStoreConnectAPI()")
    print("  sales_df = api.get_sales_report(date.today())")
    print()
    print("AFTER (appstore-connect-client):")
    print("  from appstore_connect import AppStoreConnectAPI")
    print("  api = AppStoreConnectAPI(key_id, issuer_id, private_key_path, vendor_number)")
    print("  sales_df = api.get_sales_report(date.today())  # Same method!")
    print()
    print("✅ Key benefits of migration:")
    print("  • No dependency on BicksterAppStoreSales settings module")
    print("  • Enhanced error handling and validation")
    print("  • Additional metadata management capabilities")
    print("  • Better testing and documentation")
    print("  • Can be used in other projects")
    print("  • Same familiar API methods")
    print()
    print("🔧 Migration steps:")
    print("  1. Install: pip install appstore-connect-client")
    print("  2. Update imports")
    print("  3. Pass credentials directly instead of using settings")
    print("  4. Optionally use enhanced ReportProcessor and MetadataManager")
    print("  5. Tests should continue to pass with minimal changes")


def main():
    """Run all integration examples."""
    print("🔗 appstore-connect-client Integration Examples")
    print("=" * 55)
    
    # Check if credentials are available
    required_env_vars = [
        'APP_STORE_KEY_ID',
        'APP_STORE_ISSUER_ID', 
        'APP_STORE_PRIVATE_KEY_PATH',
        'APP_STORE_VENDOR_NUMBER'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print(f"⚠️ Missing environment variables: {', '.join(missing_vars)}")
        print("Set these variables to run the live examples.")
        print()
        migration_guide_example()  # This doesn't need credentials
        return
    
    # Run examples that need credentials
    legacy_api_example()
    enhanced_reporting_example()
    metadata_management_example()
    data_pipeline_integration_example()
    migration_guide_example()
    
    print(f"\n🎉 Integration examples completed!")
    print(f"This package can serve as a drop-in replacement for existing")
    print(f"App Store Connect integrations while providing enhanced functionality.")


if __name__ == "__main__":
    main()