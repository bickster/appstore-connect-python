# API Reference

This document provides detailed API reference for all classes and methods in `appstore-connect-client`.

## Core Classes

### AppStoreConnectAPI

The main client class for interacting with the Apple App Store Connect API.

#### Constructor

```python
AppStoreConnectAPI(
    key_id: str,
    issuer_id: str,
    private_key_path: Union[str, Path],
    vendor_number: str,
    app_ids: Optional[List[str]] = None
)
```

**Parameters:**
- `key_id`: Your App Store Connect API key ID
- `issuer_id`: Your App Store Connect API issuer ID
- `private_key_path`: Path to your .p8 private key file
- `vendor_number`: Your vendor number for sales reports
- `app_ids`: Optional list of app IDs to filter reports

**Raises:**
- `ValidationError`: If required parameters are missing or private key file doesn't exist

#### Sales Reporting Methods

##### get_sales_report()

```python
get_sales_report(
    report_date: Union[datetime, date],
    report_type: str = "SALES",
    report_subtype: str = "SUMMARY",
    frequency: str = "DAILY"
) -> pd.DataFrame
```

Fetch sales report for a specific date.

**Parameters:**
- `report_date`: Date for the report
- `report_type`: SALES, SUBSCRIPTION, SUBSCRIPTION_EVENT, or SUBSCRIBER
- `report_subtype`: SUMMARY or DETAILED
- `frequency`: DAILY, WEEKLY, MONTHLY, or YEARLY

**Returns:** DataFrame containing the report data

**Example:**
```python
from datetime import date
sales_df = api.get_sales_report(date.today())
```

##### get_subscription_report()

```python
get_subscription_report(report_date: Union[datetime, date]) -> pd.DataFrame
```

Fetch subscription report for a specific date.

##### get_subscription_event_report()

```python
get_subscription_event_report(report_date: Union[datetime, date]) -> pd.DataFrame
```

Fetch subscription event report for a specific date.

##### get_financial_report()

```python
get_financial_report(year: int, month: int, region: str = "ZZ") -> pd.DataFrame
```

Fetch financial report for a specific month.

##### fetch_multiple_days()

```python
fetch_multiple_days(
    days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, List[pd.DataFrame]]
```

Fetch reports for multiple days using optimized frequency selection.

**Returns:** Dictionary with keys 'sales', 'subscriptions', 'subscription_events'

#### App Metadata Methods

##### get_apps()

```python
get_apps() -> Optional[Dict]
```

Get all apps for the account.

##### get_app_info()

```python
get_app_info(app_id: str) -> Optional[Dict]
```

Get information about a specific app.

##### update_app_name()

```python
update_app_name(app_id: str, name: str, locale: str = "en-US") -> bool
```

Update app name for a specific locale (always available).

**Parameters:**
- `app_id`: App Store app ID
- `name`: New app name (max 30 characters)
- `locale`: Locale code (e.g., 'en-US')

**Returns:** True if successful, False otherwise

**Raises:**
- `ValidationError`: If name is too long
- `NotFoundError`: If app or localization not found

##### update_app_subtitle()

```python
update_app_subtitle(app_id: str, subtitle: str, locale: str = "en-US") -> bool
```

Update app subtitle for a specific locale (always available).

##### update_privacy_url()

```python
update_privacy_url(app_id: str, privacy_url: str, locale: str = "en-US") -> bool
```

Update privacy policy URL for a specific locale (always available).

##### update_app_description()

```python
update_app_description(app_id: str, description: str, locale: str = "en-US") -> bool
```

Update app description for a specific locale (requires editable version).

**Parameters:**
- `description`: New description (max 4000 characters)

**Raises:**
- `ValidationError`: If description is too long or no editable version found

##### update_app_keywords()

```python
update_app_keywords(app_id: str, keywords: str, locale: str = "en-US") -> bool
```

Update app keywords for a specific locale (requires editable version).

**Parameters:**
- `keywords`: Comma-separated keywords (max 100 characters)

##### update_promotional_text()

```python
update_promotional_text(app_id: str, promo_text: str, locale: str = "en-US") -> bool
```

Update promotional text for a specific locale (requires editable version).

**Parameters:**
- `promo_text`: Promotional text (max 170 characters)

##### create_app_store_version()

```python
create_app_store_version(
    app_id: str,
    version_string: str,
    platform: str = "IOS"
) -> Optional[Dict]
```

Create a new App Store version.

##### get_current_metadata()

```python
get_current_metadata(app_id: str) -> Dict
```

Get comprehensive metadata for an app including both app-level and version-level info.

**Returns:** Dictionary with keys: 'app_info', 'app_localizations', 'version_info', 'version_localizations'

---

### ReportProcessor

High-level report processor for comprehensive analytics.

#### Constructor

```python
ReportProcessor(api: AppStoreConnectAPI)
```

#### Methods

##### get_sales_summary()

```python
get_sales_summary(
    days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]
```

Get a comprehensive sales summary for the specified period.

**Returns:** Dictionary containing:
- `summary`: Overall metrics (total_units, total_revenue, unique_apps, countries)
- `by_app`: Breakdown by app ID
- `by_country`: Breakdown by country
- `by_date`: Daily breakdown
- `top_performers`: Top apps and countries by various metrics

**Example:**
```python
processor = ReportProcessor(api)
summary = processor.get_sales_summary(days=30)
print(f"Total revenue: ${summary['summary']['total_revenue']:.2f}")
```

##### get_subscription_analysis()

```python
get_subscription_analysis(
    days: int = 30,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Dict[str, Any]
```

Get subscription-specific analysis for the specified period.

##### compare_periods()

```python
compare_periods(
    current_days: int = 30,
    comparison_days: int = 30,
    gap_days: int = 0
) -> Dict[str, Any]
```

Compare two time periods for sales performance.

**Returns:** Dictionary with period definitions, changes (absolute and percentage), and full summaries

##### get_app_performance_ranking()

```python
get_app_performance_ranking(
    days: int = 30,
    metric: str = 'revenue'
) -> List[Dict[str, Any]]
```

Get apps ranked by performance metric.

**Parameters:**
- `metric`: 'revenue', 'units', or 'countries'

**Returns:** List of apps with rank, app_id, name, and metric values

##### export_summary_report()

```python
export_summary_report(
    output_path: str,
    days: int = 30,
    include_details: bool = True
) -> None
```

Export a comprehensive summary report to CSV.

---

### MetadataManager

High-level metadata manager for App Store Connect apps.

#### Constructor

```python
MetadataManager(api: AppStoreConnectAPI)
```

#### Methods

##### get_app_portfolio()

```python
get_app_portfolio(refresh_cache: bool = False) -> Dict[str, Dict[str, Any]]
```

Get comprehensive information about all apps in the account.

**Returns:** Dictionary mapping app IDs to app information including basic_info, metadata, editable_version

##### update_app_listing()

```python
update_app_listing(
    app_id: str,
    updates: Dict[str, Any],
    locale: str = "en-US",
    validate: bool = True
) -> Dict[str, bool]
```

Update app store listing with multiple fields.

**Parameters:**
- `updates`: Dictionary of field updates (name, subtitle, privacy_url, description, keywords, promotional_text)
- `validate`: Whether to validate inputs

**Returns:** Dictionary showing success/failure for each update

**Example:**
```python
manager = MetadataManager(api)
results = manager.update_app_listing(
    app_id='123456789',
    updates={
        'name': 'New App Name',
        'subtitle': 'Amazing App',
        'description': 'This app is incredible...'
    }
)
```

##### batch_update_apps()

```python
batch_update_apps(
    updates: Dict[str, Dict[str, Any]],
    locale: str = "en-US",
    continue_on_error: bool = True
) -> Dict[str, Dict[str, bool]]
```

Update multiple apps with different field updates.

##### standardize_app_names()

```python
standardize_app_names(
    app_ids: Optional[List[str]] = None,
    name_pattern: str = "{original_name}",
    locale: str = "en-US",
    dry_run: bool = True
) -> Dict[str, Dict[str, Any]]
```

Standardize app names across the portfolio.

**Parameters:**
- `name_pattern`: Pattern for new names (supports {original_name}, {bundle_id}, {app_id})
- `dry_run`: If True, only show what would be changed

##### prepare_version_releases()

```python
prepare_version_releases(
    app_versions: Dict[str, str],
    dry_run: bool = True
) -> Dict[str, Dict[str, Any]]
```

Prepare new versions for multiple apps.

##### get_localization_status()

```python
get_localization_status(
    app_ids: Optional[List[str]] = None
) -> Dict[str, Dict[str, Any]]
```

Get localization status for apps.

##### export_app_metadata()

```python
export_app_metadata(
    output_path: str,
    app_ids: Optional[List[str]] = None,
    include_versions: bool = True
) -> None
```

Export app metadata to CSV for analysis or backup.

---

## Utility Functions

### Validation Functions

All validation functions are available in the `utils` module:

```python
from appstore_connect.utils import (
    validate_app_id,
    validate_vendor_number,
    validate_locale,
    validate_version_string,
    normalize_date,
    get_date_range
)
```

### Data Processing Functions

```python
from appstore_connect.utils import (
    combine_dataframes,
    calculate_summary_metrics,
    format_currency,
    sanitize_app_name,
    chunk_list
)
```

---

## Exception Classes

### AppStoreConnectError
Base exception class for all App Store Connect API errors.

### AuthenticationError
Raised when authentication fails (401 status code).

### PermissionError
Raised when insufficient permissions for operation (403 status code).

### NotFoundError
Raised when requested resource is not found (404 status code).

### RateLimitError
Raised when rate limits are exceeded (429 status code).

### ValidationError
Raised when request validation fails.

---

## Convenience Functions

### create_report_processor()

```python
create_report_processor(
    key_id: str,
    issuer_id: str,
    private_key_path: str,
    vendor_number: str,
    app_ids: Optional[List[str]] = None
) -> ReportProcessor
```

Create a ReportProcessor with API client in one step.

### create_metadata_manager()

```python
create_metadata_manager(
    key_id: str,
    issuer_id: str,
    private_key_path: str,
    vendor_number: str
) -> MetadataManager
```

Create a MetadataManager with API client in one step.

---

## Constants and Enums

### Report Types
- `SALES`: Sales and download reports
- `SUBSCRIPTION`: Subscription status reports
- `SUBSCRIPTION_EVENT`: Subscription event reports
- `SUBSCRIBER`: Subscriber reports
- `FINANCIAL`: Financial reports

### Report Frequencies
- `DAILY`: Daily reports
- `WEEKLY`: Weekly reports (Sunday start)
- `MONTHLY`: Monthly reports
- `YEARLY`: Yearly reports

### Report Subtypes
- `SUMMARY`: Summary reports
- `DETAILED`: Detailed reports

### App Store States (Version)
- `PREPARE_FOR_SUBMISSION`: Version being prepared
- `WAITING_FOR_REVIEW`: Waiting for App Store review
- `IN_REVIEW`: Currently under review
- `READY_FOR_SALE`: Live on App Store
- `DEVELOPER_REJECTED`: Rejected by developer
- `REJECTED`: Rejected by Apple

States that allow editing: `PREPARE_FOR_SUBMISSION`, `WAITING_FOR_REVIEW`, `IN_REVIEW`, `DEVELOPER_REJECTED`, `REJECTED`

---

## Rate Limiting

The client automatically handles Apple's rate limiting (50 requests per hour) using exponential backoff. All API methods are decorated with rate limiting to ensure compliance.

## Error Handling

All methods include comprehensive error handling:
- Network errors are wrapped in `AppStoreConnectError`
- HTTP status codes are mapped to specific exception types
- Validation errors are caught before API calls when possible
- Detailed error messages include context and suggestions