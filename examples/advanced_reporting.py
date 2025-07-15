#!/usr/bin/env python3
"""
Advanced reporting examples for appstore-connect-client.

This example demonstrates how to:
1. Use the ReportProcessor for comprehensive analytics
2. Compare performance across time periods
3. Generate ranking reports
4. Export summary data
"""

import os
from datetime import date, timedelta
from appstore_connect import create_report_processor
from appstore_connect.exceptions import AppStoreConnectError

def main():
    """Demonstrate advanced reporting capabilities."""
    
    # Create report processor
    processor = create_report_processor(
        key_id=os.getenv('APP_STORE_KEY_ID'),
        issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
        private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER'),
        app_ids=['123456789', '987654321']  # Optional: filter to specific apps
    )
    
    try:
        print("📊 Advanced App Store Analytics Demo")
        print("=" * 50)
        
        # Example 1: Comprehensive sales summary
        print("\n📈 Getting 30-day sales summary...")
        summary = processor.get_sales_summary(days=30)
        
        overall = summary['summary']
        print(f"✅ Overall Performance (Last 30 Days):")
        print(f"  • Total Units: {overall['total_units']:,}")
        print(f"  • Total Revenue: ${overall['total_revenue']:,.2f}")
        print(f"  • Unique Apps: {overall['unique_apps']}")
        print(f"  • Countries: {overall['countries']}")
        
        # Show top performers
        top_performers = summary.get('top_performers', {})
        if 'by_revenue' in top_performers:
            print(f"\n🏆 Top Apps by Revenue:")
            for i, app in enumerate(top_performers['by_revenue'][:3], 1):
                print(f"  {i}. {app['name']}: ${app['revenue']:,.2f}")
        
        if 'by_country' in top_performers:
            print(f"\n🌍 Top Countries by Revenue:")
            for i, country in enumerate(top_performers['by_country'][:3], 1):
                print(f"  {i}. {country['country']}: ${country['revenue']:,.2f}")
        
        # Example 2: Period comparison
        print(f"\n📊 Comparing Current vs Previous 30 Days...")
        comparison = processor.compare_periods(
            current_days=30,
            comparison_days=30
        )
        
        changes = comparison['changes']
        for metric, data in changes.items():
            change_pct = data['change_percent']
            direction = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
            print(f"  {metric}: {direction} {change_pct:+.1f}% ({data['current']:,} vs {data['previous']:,})")
        
        # Example 3: App performance ranking
        print(f"\n🏆 App Performance Ranking by Revenue...")
        ranking = processor.get_app_performance_ranking(days=30, metric='revenue')
        
        for app in ranking[:5]:  # Top 5 apps
            print(f"  #{app['rank']}: {app['name']}")
            print(f"    Revenue: ${app['revenue']:,.2f}")
            print(f"    Units: {app['units']:,}")
            print(f"    Countries: {app['countries']}")
            print()
        
        # Example 4: Subscription analysis
        print(f"\n📱 Subscription Analysis...")
        try:
            sub_analysis = processor.get_subscription_analysis(days=30)
            
            sub_summary = sub_analysis.get('subscription_summary', {})
            if sub_summary:
                print(f"✅ Subscription Metrics:")
                print(f"  • Total Active: {sub_summary.get('total_active', 0):,}")
                print(f"  • Total Revenue: ${sub_summary.get('total_revenue', 0):,.2f}")
                print(f"  • Unique Products: {sub_summary.get('unique_products', 0)}")
            
            event_summary = sub_analysis.get('event_summary', {})
            if 'events' in event_summary:
                print(f"\n📅 Subscription Events:")
                for event, count in event_summary['events'].items():
                    print(f"  • {event}: {count:,}")
                
                if 'cancellation_rate' in event_summary:
                    rate = event_summary['cancellation_rate'] * 100
                    print(f"  • Cancellation Rate: {rate:.1f}%")
            
        except Exception as e:
            print(f"ℹ️ Subscription data not available: {e}")
        
        # Example 5: Export comprehensive report
        print(f"\n💾 Exporting summary report...")
        export_path = "/tmp/app_store_summary.csv"
        processor.export_summary_report(
            output_path=export_path,
            days=30,
            include_details=True
        )
        print(f"✅ Report exported to: {export_path}")
        
        # Example 6: Weekly trend analysis
        print(f"\n📅 Weekly Trend Analysis...")
        weekly_data = {}
        
        # Get data for each of the last 4 weeks
        for week in range(4):
            end_date = date.today() - timedelta(days=1 + (week * 7))
            start_date = end_date - timedelta(days=6)
            
            weekly_summary = processor.get_sales_summary(
                start_date=start_date,
                end_date=end_date
            )
            
            week_label = f"Week {4-week}"
            weekly_data[week_label] = weekly_summary['summary']
            
            print(f"  {week_label} ({start_date} to {end_date}):")
            print(f"    Units: {weekly_summary['summary']['total_units']:,}")
            print(f"    Revenue: ${weekly_summary['summary']['total_revenue']:,.2f}")
        
        # Calculate week-over-week growth
        weeks = list(weekly_data.keys())
        if len(weeks) >= 2:
            current_week = weekly_data[weeks[0]]
            previous_week = weekly_data[weeks[1]]
            
            if previous_week['total_revenue'] > 0:
                revenue_growth = ((current_week['total_revenue'] - previous_week['total_revenue']) / 
                                previous_week['total_revenue']) * 100
                print(f"\n📈 Week-over-Week Revenue Growth: {revenue_growth:+.1f}%")
        
        print(f"\n🎉 Advanced reporting demo completed!")
        
    except AppStoreConnectError as e:
        print(f"❌ API error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()