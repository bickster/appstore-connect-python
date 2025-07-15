# appstore-connect-client

[![PyPI version](https://badge.fury.io/py/appstore-connect-client.svg)](https://badge.fury.io/py/appstore-connect-client)
[![Python versions](https://img.shields.io/pypi/pyversions/appstore-connect-client.svg)](https://pypi.org/project/appstore-connect-client/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Test Coverage](https://img.shields.io/badge/coverage-80%25-green.svg)](https://github.com/chrisbick/appstore-connect-client)

A comprehensive Python client for the Apple App Store Connect API, providing simple and intuitive interfaces for sales reporting, app metadata management, and advanced analytics.

## Features

- 📊 **Sales & Financial Reporting** - Daily, weekly, monthly sales and revenue data
- 🎯 **App Metadata Management** - Update app listings, descriptions, and keywords
- 📈 **Advanced Analytics** - Period comparisons, performance ranking, trend analysis
- 💳 **Subscription Analytics** - Active subscriptions, events, and lifecycle metrics
- 🌍 **Localization Support** - Multi-language content management
- 🚀 **Batch Operations** - Update multiple apps simultaneously
- 🔐 **Secure Authentication** - JWT ES256 token-based auth
- ⚡ **Smart Rate Limiting** - Automatic handling of API limits (50 requests/hour)
- 🐼 **Pandas Integration** - DataFrames for easy data manipulation
- ✅ **Type Hints** - Full type support for better IDE experience

## Installation

```bash
pip install appstore-connect-client
```

For development:
```bash
pip install appstore-connect-client[dev]
```

## Quick Start

```python
from appstore_connect import AppStoreConnectAPI
from datetime import date, timedelta

# Initialize the client
client = AppStoreConnectAPI(
    key_id="your_key_id",
    issuer_id="your_issuer_id",
    private_key_path="/path/to/AuthKey_XXXXXX.p8",
    vendor_number="your_vendor_number"
)

# Get yesterday's sales data
yesterday = date.today() - timedelta(days=1)
sales_df = client.get_sales_report(yesterday)
print(f"Revenue: ${sales_df['proceeds'].sum():,.2f}")
```

## Authentication

### Prerequisites

1. Apple Developer Account with App Store Connect access
2. App Store Connect API Key ([generate here](https://appstoreconnect.apple.com/access/api))
3. Private key file (.p8) downloaded from App Store Connect
4. Vendor number from your App Store Connect account

### Setting up credentials

You can provide credentials in three ways:

#### 1. Direct parameters (recommended)
```python
client = AppStoreConnectAPI(
    key_id="your_key_id",
    issuer_id="your_issuer_id",
    private_key_path="/path/to/private_key.p8",
    vendor_number="your_vendor_number"
)
```

#### 2. Environment variables
```bash
export APP_STORE_KEY_ID="your_key_id"
export APP_STORE_ISSUER_ID="your_issuer_id"
export APP_STORE_PRIVATE_KEY_PATH="/path/to/private_key.p8"
export APP_STORE_VENDOR_NUMBER="your_vendor_number"
```

```python
import os
client = AppStoreConnectAPI(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)
```

#### 3. Using .env file
Create a `.env` file based on `.env.example` and the client will load it automatically in development.

## Usage Examples

### Sales Reporting
```python
# Get comprehensive 30-day analytics
from appstore_connect import create_report_processor

processor = create_report_processor(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

summary = processor.get_sales_summary(days=30)
print(f"Total Revenue: ${summary['summary']['total_revenue']:,.2f}")
print(f"Total Units: {summary['summary']['total_units']:,}")

# Compare performance periods
comparison = processor.compare_periods(current_days=30, comparison_days=30)
revenue_change = comparison['changes']['total_revenue']['change_percent']
print(f"Revenue Change: {revenue_change:+.1f}%")
```

### App Metadata Management
```python
from appstore_connect import create_metadata_manager

manager = create_metadata_manager(
    key_id=os.getenv('APP_STORE_KEY_ID'),
    issuer_id=os.getenv('APP_STORE_ISSUER_ID'),
    private_key_path=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
    vendor_number=os.getenv('APP_STORE_VENDOR_NUMBER')
)

# Update app listing
results = manager.update_app_listing(
    app_id='123456789',
    updates={
        'name': 'My Awesome App',
        'subtitle': 'The Best App Ever',
        'description': 'This app will change your life...',
        'keywords': 'productivity,utility,business'
    }
)

# Batch update multiple apps
batch_updates = {
    '123456789': {'subtitle': 'Productivity Booster'},
    '987654321': {'subtitle': 'Entertainment Hub'}
}
results = manager.batch_update_apps(batch_updates)
```

### DataFrame Operations
```python
# Get sales data and calculate weekly totals
import pandas as pd

# Fetch multiple days efficiently
reports = client.fetch_multiple_days(days=90)  # Automatically optimizes API calls

# Calculate weekly revenue
reports['week'] = pd.to_datetime(reports['begin_date']).dt.isocalendar().week
weekly_revenue = reports.groupby('week')['proceeds'].sum()

# Get top performing apps
top_apps = reports.groupby('app_name')['units'].sum().nlargest(10)
```

## API Reference

See [API Documentation](docs/API_REFERENCE.md) for complete reference.

### Core Components

- **AppStoreConnectAPI** - Main client for direct API access
- **ReportProcessor** - High-level analytics with advanced reporting
- **MetadataManager** - Portfolio management with batch operations

## Error Handling

```python
from appstore_connect.exceptions import (
    AuthenticationError,
    RateLimitError,
    ValidationError,
    PermissionError
)

try:
    sales_df = client.get_sales_report(date.today())
except AuthenticationError:
    print("Check your API credentials")
except RateLimitError:
    print("Rate limit exceeded - wait before retrying")
except PermissionError:
    print("Insufficient API key permissions")
except ValidationError as e:
    print(f"Invalid input: {e}")
```

## Best Practices

1. **Reuse client instances** - Create once and reuse for multiple requests
2. **Use smart fetching** - Let the client optimize API calls for date ranges
3. **Handle rate limits** - Built-in retry logic, but be mindful of usage
4. **Leverage DataFrames** - Use pandas operations for data analysis
5. **Secure credentials** - Never commit credentials to version control

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=appstore_connect --cov-report=term-missing

# Run specific test file
pytest tests/test_client.py
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Install development dependencies: `pip install -e .[dev]`
4. Make your changes and add tests
5. Run tests: `pytest`
6. Check formatting: `black --check src/appstore_connect tests`
7. Format code: `black src/appstore_connect tests`
8. Commit your changes (`git commit -m 'Add amazing feature'`)
9. Push to the branch (`git push origin feature/amazing-feature`)
10. Open a Pull Request

See [CLAUDE.md](CLAUDE.md) for detailed development commands.

## Documentation

- 📚 [Getting Started](docs/GETTING_STARTED.md) - Setup and basic usage
- 🔧 [API Reference](docs/API_REFERENCE.md) - Complete API documentation
- 🚑 [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions
- 💡 [Examples](examples/) - Comprehensive usage examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 🐛 **Issues**: [GitHub Issues](https://github.com/chrisbick/appstore-connect-client/issues)
- 📖 **Documentation**: [Read the Docs](https://appstore-connect-client.readthedocs.io/)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/chrisbick/appstore-connect-client/discussions)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and changes.

---

**Made with ❤️ for iOS developers and app analytics teams**