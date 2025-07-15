# Getting Started

This guide will help you get up and running with `appstore-connect-client` quickly.

## Installation

Install the package using pip:

```bash
pip install appstore-connect-client
```

For development or additional features:

```bash
pip install appstore-connect-client[dev]
```

## Prerequisites

Before you can use this library, you need:

1. **Apple Developer Account** with App Store Connect access
2. **App Store Connect API Key** with appropriate permissions
3. **Private Key File** (.p8 format) downloaded from App Store Connect
4. **Vendor Number** from your sales reports

### Setting up App Store Connect API Access

1. **Generate API Key:**
   - Log in to [App Store Connect](https://appstoreconnect.apple.com/)
   - Go to Users and Access → Keys
   - Click the "+" button to generate a new key
   - Choose appropriate access level:
     - **Sales Reports**: Read access to sales data
     - **App Metadata**: Write access for app store listing management
   - Download the private key file (`.p8` format)
   - Note the Key ID and Issuer ID

2. **Find Your Vendor Number:**
   - Go to App Store Connect → Payments and Financial Reports
   - Your vendor number is displayed in the top section

## Quick Start

### Basic Setup

```python
import os
from appstore_connect import AppStoreConnectAPI

# Initialize the API client
api = AppStoreConnectAPI(
    key_id='YOUR_KEY_ID',
    issuer_id='YOUR_ISSUER_ID',
    private_key_path='/path/to/your/AuthKey_XXXXXXXXXX.p8',
    vendor_number='YOUR_VENDOR_NUMBER'
)

# Get sales data for yesterday
from datetime import date, timedelta
yesterday = date.today() - timedelta(days=1)
sales_df = api.get_sales_report(yesterday)

print(f"Found {len(sales_df)} sales records")
```

### Using Environment Variables

For security, store your credentials as environment variables:

```bash
export APP_STORE_KEY_ID="your_key_id"
export APP_STORE_ISSUER_ID="your_issuer_id"
export APP_STORE_PRIVATE_KEY_PATH="/path/to/AuthKey_XXXXXXXXXX.p8"
export APP_STORE_VENDOR_NUMBER="your_vendor_number"
```

Then in your code:

```python
import os
from appstore_connect import AppStoreConnectAPI

api = AppStoreConnectAPI(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)
```

## Core Workflows

### 1. Sales Reporting

#### Get Daily Sales

```python
from datetime import date, timedelta

# Yesterday's sales
yesterday = date.today() - timedelta(days=1)
sales_df = api.get_sales_report(yesterday)

# Process the data
if not sales_df.empty:
    total_units = sales_df['Units'].sum()
    total_revenue = sales_df['Developer Proceeds'].sum()
    print(f"Yesterday: {total_units} units, ${total_revenue:.2f} revenue")
```

#### Get Multiple Days of Data

```python
# Get last 30 days (automatically optimized)
reports = api.fetch_multiple_days(days=30)

# Process sales data
sales_dfs = reports.get('sales', [])
if sales_dfs:
    # Combine all DataFrames
    import pandas as pd
    all_sales = pd.concat(sales_dfs, ignore_index=True)
    print(f"30 days: {len(all_sales)} total records")
```

#### Get Subscription Data

```python
# Subscription status
subscription_df = api.get_subscription_report(yesterday)

# Subscription events (upgrades, cancellations, etc.)
events_df = api.get_subscription_event_report(yesterday)
```

### 2. Enhanced Analytics

Use the `ReportProcessor` for advanced analytics:

```python
from appstore_connect import create_report_processor

# Create processor
processor = create_report_processor(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

# Get comprehensive summary
summary = processor.get_sales_summary(days=30)

print("30-Day Performance:")
print(f"Revenue: ${summary['summary']['total_revenue']:,.2f}")
print(f"Units: {summary['summary']['total_units']:,}")
print(f"Apps: {summary['summary']['unique_apps']}")

# Top performing apps
top_apps = summary['top_performers']['by_revenue']
for app in top_apps[:3]:
    print(f"- {app['name']}: ${app['revenue']:,.2f}")
```

#### Compare Time Periods

```python
# Compare current 30 days vs previous 30 days
comparison = processor.compare_periods(
    current_days=30,
    comparison_days=30
)

# Show changes
for metric, data in comparison['changes'].items():
    change_pct = data['change_percent']
    direction = "📈" if change_pct > 0 else "📉"
    print(f"{metric}: {direction} {change_pct:+.1f}%")
```

### 3. App Metadata Management

Use the `MetadataManager` for app store listing management:

```python
from appstore_connect import create_metadata_manager

# Create metadata manager
manager = create_metadata_manager(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

# Get portfolio overview
portfolio = manager.get_app_portfolio()
print(f"Managing {len(portfolio)} apps")

# Update an app's metadata
results = manager.update_app_listing(
    app_id='123456789',
    updates={
        'name': 'My Awesome App',
        'subtitle': 'The Best App Ever',
        'description': 'This app will change your life...'
    }
)

for field, success in results.items():
    status = "✅" if success else "❌"
    print(f"{status} {field}")
```

#### Batch Operations

```python
# Update multiple apps at once
batch_updates = {
    '123456789': {
        'subtitle': 'Productivity Booster',
        'keywords': 'productivity,utility,business'
    },
    '987654321': {
        'subtitle': 'Entertainment Hub',
        'keywords': 'entertainment,fun,games'
    }
}

results = manager.batch_update_apps(batch_updates)
```

## Common Use Cases

### 1. Daily Revenue Monitoring

```python
import pandas as pd
from datetime import date, timedelta

def daily_revenue_check():
    yesterday = date.today() - timedelta(days=1)
    sales_df = api.get_sales_report(yesterday)
    
    if sales_df.empty:
        print("No sales data available")
        return
    
    # Calculate by app
    by_app = sales_df.groupby(['Apple Identifier', 'Title']).agg({
        'Units': 'sum',
        'Developer Proceeds': 'sum'
    }).reset_index()
    
    print(f"Revenue for {yesterday}:")
    for _, row in by_app.iterrows():
        print(f"- {row['Title']}: {row['Units']} units, ${row['Developer Proceeds']:.2f}")

daily_revenue_check()
```

### 2. App Store Optimization

```python
def analyze_app_portfolio():
    # Get portfolio
    portfolio = manager.get_app_portfolio()
    
    # Find optimization opportunities
    for app_id, info in portfolio.items():
        app_name = info['basic_info']['name']
        metadata = info['metadata']
        
        # Check for missing subtitles
        en_us = metadata['app_localizations'].get('en-US', {})
        if not en_us.get('subtitle'):
            print(f"⚠️ {app_name}: Missing subtitle")
        
        # Check for editable versions
        if info['editable_version']:
            version = info['editable_version']['attributes']['versionString']
            print(f"✏️ {app_name}: Version {version} is editable")

analyze_app_portfolio()
```

### 3. Weekly Performance Reports

```python
def weekly_report():
    # Get last 7 days
    processor = create_report_processor(...)
    summary = processor.get_sales_summary(days=7)
    
    # Export to CSV
    processor.export_summary_report(
        output_path='weekly_report.csv',
        days=7,
        include_details=True
    )
    
    print("Weekly report exported to weekly_report.csv")

weekly_report()
```

## Error Handling

Always wrap API calls in try-catch blocks:

```python
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    PermissionError,
    RateLimitError
)

try:
    sales_df = api.get_sales_report(date.today())
except AuthenticationError:
    print("Authentication failed - check your credentials")
except PermissionError:
    print("Insufficient permissions - check your API key scope")
except RateLimitError:
    print("Rate limit exceeded - wait before retrying")
except AppStoreConnectError as e:
    print(f"API error: {e}")
```

## Best Practices

### 1. Credentials Security
- Never hardcode credentials in your source code
- Use environment variables or secure credential stores
- Rotate API keys regularly
- Use the minimum required permissions

### 2. Rate Limiting
- The library handles rate limiting automatically
- Apple allows 50 requests per hour
- Use bulk operations when possible
- Cache data when appropriate

### 3. Data Processing
- Always check if DataFrames are empty before processing
- Handle missing or null values appropriately
- Use appropriate date ranges for your use case
- Filter to specific apps when possible to reduce data volume

### 4. Error Handling
- Always handle network and API errors
- Log errors appropriately for debugging
- Implement retry logic for transient failures
- Validate inputs before making API calls

## Next Steps

- Check out the [API Reference](API_REFERENCE.md) for detailed method documentation
- See the [examples/](../examples/) directory for more comprehensive examples
- Read about [advanced features](ADVANCED_USAGE.md) like custom authentication and enterprise usage
- Review the [troubleshooting guide](TROUBLESHOOTING.md) for common issues

## Getting Help

If you encounter issues:

1. Check the [troubleshooting guide](TROUBLESHOOTING.md)
2. Review your API key permissions in App Store Connect
3. Verify your credentials and file paths
4. Check the [GitHub issues](https://github.com/chrisbick/appstore-connect-client/issues) for known problems
5. Create a new issue with detailed error information