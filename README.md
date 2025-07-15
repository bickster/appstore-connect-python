# appstore-connect-client

[![PyPI version](https://badge.fury.io/py/appstore-connect-client.svg)](https://badge.fury.io/py/appstore-connect-client)
[![Python versions](https://img.shields.io/pypi/pyversions/appstore-connect-client.svg)](https://pypi.org/project/appstore-connect-client/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A comprehensive Python client for the Apple App Store Connect API, supporting both sales reporting and metadata management with advanced analytics capabilities.

## ✨ Features

### 📊 Sales & Analytics
- **Sales Reports**: Daily, weekly, monthly sales and download data
- **Subscription Analytics**: Active subscriptions, events, and lifecycle metrics
- **Financial Reports**: Revenue and financial data with currency conversion
- **Advanced Analytics**: Period comparisons, performance ranking, trend analysis
- **Smart Data Fetching**: Optimized API usage with automatic frequency selection

### 🎯 App Store Management
- **Metadata Updates**: App names, descriptions, keywords, promotional text
- **Batch Operations**: Update multiple apps simultaneously
- **Localization Management**: Multi-language content management
- **Version Control**: Create and manage app versions
- **Portfolio Analysis**: Comprehensive app portfolio insights

### 🛡️ Enterprise Ready
- **Rate Limiting**: Automatic handling of Apple's API limits (50 requests/hour)
- **Error Handling**: Comprehensive exception handling with specific error types
- **Authentication**: Secure JWT ES256 token-based authentication
- **Validation**: Input validation and data integrity checks
- **Logging**: Detailed logging for debugging and monitoring

## 🚀 Installation

```bash
pip install appstore-connect-client
```

For development or additional features:
```bash
pip install appstore-connect-client[dev]
```

## 📋 Prerequisites

1. **Apple Developer Account** with App Store Connect access
2. **App Store Connect API Key** ([generate here](https://appstoreconnect.apple.com/access/api))
3. **Private Key File** (.p8 format) downloaded from App Store Connect
4. **Vendor Number** from your App Store Connect account

## ⚡ Quick Start

### Basic Setup

```python
import os
from datetime import date, timedelta
from appstore_connect import AppStoreConnectAPI

# Initialize the API client
api = AppStoreConnectAPI(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

# Get yesterday's sales data
yesterday = date.today() - timedelta(days=1)
sales_df = api.get_sales_report(yesterday)
print(f"Found {len(sales_df)} sales records")

# Get subscription data
subscription_df = api.get_subscription_report(yesterday)
print(f"Found {len(subscription_df)} subscription records")
```

### Advanced Analytics

```python
from appstore_connect import create_report_processor

# Create enhanced report processor
processor = create_report_processor(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

# Get comprehensive 30-day analytics
summary = processor.get_sales_summary(days=30)
print(f"Total Revenue: ${summary['summary']['total_revenue']:,.2f}")
print(f"Total Units: {summary['summary']['total_units']:,}")

# Compare performance periods
comparison = processor.compare_periods(current_days=30, comparison_days=30)
revenue_change = comparison['changes']['total_revenue']['change_percent']
print(f"Revenue Change: {revenue_change:+.1f}%")

# Get app performance ranking
ranking = processor.get_app_performance_ranking(days=30, metric='revenue')
for app in ranking[:3]:
    print(f"#{app['rank']}: {app['name']} - ${app['revenue']:,.2f}")
```

### App Metadata Management

```python
from appstore_connect import create_metadata_manager

# Create metadata manager
manager = create_metadata_manager(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

# Update app store listing
results = manager.update_app_listing(
    app_id='123456789',
    updates={
        'name': 'My Awesome App',
        'subtitle': 'The Best App Ever',
        'description': 'This app will change your life...',
        'keywords': 'productivity,utility,business,efficiency'
    }
)

# Batch update multiple apps
batch_updates = {
    '123456789': {'subtitle': 'Productivity Booster'},
    '987654321': {'subtitle': 'Entertainment Hub'}
}
results = manager.batch_update_apps(batch_updates)
```

## 📚 Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** - Setup and basic usage
- **[API Reference](docs/API_REFERENCE.md)** - Complete API documentation
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Examples](examples/)** - Comprehensive usage examples

## 🔧 Core Components

### AppStoreConnectAPI
The main client for direct API access with all sales reporting and metadata management methods.

### ReportProcessor  
High-level analytics processor with advanced reporting capabilities:
- Sales summaries with breakdowns by app, country, and date
- Period comparisons and trend analysis
- Performance ranking and top performer identification
- Subscription analytics with event tracking

### MetadataManager
Portfolio management with batch operations:
- App metadata updates across multiple apps
- Localization status analysis
- Version management and preparation
- Portfolio optimization insights

## 🛠️ Advanced Features

### Smart Data Fetching
```python
# Automatically optimizes API calls based on date range
# - Last 7 days: Daily reports
# - 8-30 days: Weekly reports  
# - 30+ days: Monthly reports
reports = api.fetch_multiple_days(days=90)  # Efficient for large ranges
```

### Batch Metadata Operations
```python
# Update multiple apps with different changes
batch_updates = {
    'app1': {'name': 'New Name 1', 'subtitle': 'New Subtitle 1'},
    'app2': {'description': 'New Description 2', 'keywords': 'new,keywords'},
    'app3': {'promotional_text': 'Try it now!'}
}
results = manager.batch_update_apps(batch_updates, continue_on_error=True)
```

### Portfolio Analysis
```python
# Get comprehensive portfolio insights
portfolio = manager.get_app_portfolio()
localization_status = manager.get_localization_status()

# Export for analysis
manager.export_app_metadata('portfolio_analysis.csv', include_versions=True)
```

## 🔒 Security Best Practices

- Store credentials as environment variables
- Use minimum required API permissions
- Rotate API keys regularly
- Never commit credentials to version control

```bash
# Environment variables
export APP_STORE_KEY_ID="your_key_id"
export APP_STORE_ISSUER_ID="your_issuer_id" 
export APP_STORE_PRIVATE_KEY_PATH="/secure/path/to/AuthKey_XXXXXXXXXX.p8"
export APP_STORE_VENDOR_NUMBER="your_vendor_number"
```

## 🚦 Error Handling

```python
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    PermissionError,
    RateLimitError,
    ValidationError
)

try:
    sales_df = api.get_sales_report(date.today())
except AuthenticationError:
    print("Check your API credentials")
except PermissionError:
    print("Insufficient API key permissions")
except RateLimitError:
    print("Rate limit exceeded - wait before retrying")
except ValidationError as e:
    print(f"Invalid input: {e}")
except AppStoreConnectError as e:
    print(f"API error: {e}")
```

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=appstore_connect

# Run specific test file
pytest tests/test_client.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Run the test suite (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on the official Apple App Store Connect API
- Inspired by the need for comprehensive app store analytics
- Thanks to the open source community for their contributions

## 📞 Support

- **Documentation**: [Getting Started Guide](docs/GETTING_STARTED.md)
- **Issues**: [GitHub Issues](https://github.com/chrisbick/appstore-connect-client/issues)  
- **API Reference**: [Complete Documentation](docs/API_REFERENCE.md)
- **Examples**: [Example Scripts](examples/)

---

**Made with ❤️ for iOS developers and app analytics teams**
