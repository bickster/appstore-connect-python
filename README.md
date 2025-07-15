# appstore-connect-client

A comprehensive Python client for the Apple App Store Connect API, supporting both sales reporting and metadata management.

## Features

- **Sales & Subscription Reports**: Download daily, weekly, monthly sales data
- **Financial Reports**: Access revenue and financial data
- **App Metadata Management**: Update app names, descriptions, keywords, and more
- **Multi-locale Support**: Manage content across different languages and regions
- **Rate Limiting**: Built-in request throttling to respect Apple's API limits
- **JWT Authentication**: Secure ES256 token-based authentication

## Installation

```bash
pip install appstore-connect-client
```

## Quick Start

```python
from appstore_connect import AppStoreConnectAPI

# Initialize with your credentials
api = AppStoreConnectAPI(
    key_id='your-key-id',
    issuer_id='your-issuer-id',
    private_key_path='path/to/private-key.p8',
    vendor_number='your-vendor-number'
)

# Get sales data
sales_df = api.get_sales_report(date.today())

# List all apps
apps = api.get_apps()

# Update app metadata
api.update_app_name(app_id='123456789', name='New App Name')
```

## Documentation

For detailed documentation, examples, and API reference, visit [our documentation](https://appstore-connect-client.readthedocs.io/).

## Requirements

- Python 3.7+
- App Store Connect API credentials
- Appropriate permissions for your use case

## License

MIT License - see LICENSE file for details.
