# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-15

### Changed
- **BREAKING**: Fixed Apple API rate limit from 50/hour to actual 3500/hour
- Optimized batch operations with new context manager for temporary caching
- Improved integration test handling with proper timeout management
- Enhanced error handling for permission errors (403) in tests

### Fixed
- Fixed integration test timeouts by correcting rate limiter configuration
- Fixed all flake8 linting issues across the codebase
- Fixed unused imports and variables
- Fixed f-strings without placeholders
- Fixed bare except statements
- Fixed None comparison issues
- Removed backward compatibility code from tests
- Updated test assertions to match actual implementation behavior

### Added
- Batch operation context manager for MetadataManager to optimize API calls
- Automatic cache invalidation after batch operations
- pytest-timeout for better test timeout management
- Comprehensive test coverage improvements

### Improved
- Code quality with complete flake8 compliance
- Test reliability with proper error handling
- Performance for batch metadata operations
- Documentation in CLAUDE.md with helpful commands

## [0.2.0] - 2025-01-15

### Changed
- **BREAKING**: Renamed package from `appstore-connect-client` to `apple-appstore-connect-client` for PyPI uniqueness
- Major project restructuring to use src/ directory layout
- Modernized project structure following Python best practices

### Added
- Comprehensive integration tests
- Test fixtures and conftest.py for better test organization
- Additional test coverage for edge cases

### Fixed
- StopIteration error in metadata permission tests
- Various test assertion failures
- Release script to use python3 -m for all commands

## [0.1.0] - 2025-01-15

### Added

#### Core API Client
- `AppStoreConnectAPI` class for direct App Store Connect API access
- JWT ES256 authentication with automatic token refresh
- Built-in rate limiting (50 requests/hour) with exponential backoff
- Comprehensive error handling with specific exception types

#### Sales Reporting
- `get_sales_report()` - Fetch daily, weekly, monthly, yearly sales reports
- `get_subscription_report()` - Subscription status and metrics
- `get_subscription_event_report()` - Subscription lifecycle events
- `get_financial_report()` - Financial and revenue data
- `fetch_multiple_days()` - Optimized bulk data fetching with smart frequency selection

#### App Metadata Management
- `get_apps()` - List all apps in account
- `get_current_metadata()` - Comprehensive app metadata retrieval
- `update_app_name()` - Update app store name (always available)
- `update_app_subtitle()` - Update app subtitle (always available)
- `update_privacy_url()` - Update privacy policy URL (always available)
- `update_app_description()` - Update app description (requires editable version)
- `update_app_keywords()` - Update keywords (requires editable version)
- `update_promotional_text()` - Update promotional text (requires editable version)
- `create_app_store_version()` - Create new app versions
- `get_editable_version()` - Find versions available for editing

#### Advanced Analytics (ReportProcessor)
- `get_sales_summary()` - Comprehensive sales analytics with breakdowns
- `get_subscription_analysis()` - Subscription metrics and event analysis
- `compare_periods()` - Period-over-period performance comparison
- `get_app_performance_ranking()` - App ranking by revenue, units, or countries
- `export_summary_report()` - Export analytics to CSV

#### Portfolio Management (MetadataManager)
- `get_app_portfolio()` - Complete portfolio overview with caching
- `update_app_listing()` - Multi-field app store listing updates
- `batch_update_apps()` - Update multiple apps simultaneously
- `standardize_app_names()` - Bulk app name standardization
- `prepare_version_releases()` - Batch version creation
- `get_localization_status()` - Localization analysis across portfolio
- `export_app_metadata()` - Portfolio data export to CSV

#### Utility Functions
- Comprehensive validation functions for all input types
- Date handling and normalization utilities
- String sanitization and formatting helpers
- DataFrame combination and processing utilities
- Currency formatting and display functions

#### Exception Handling
- `AppStoreConnectError` - Base exception for all API errors
- `AuthenticationError` - Authentication failures (401)
- `PermissionError` - Insufficient permissions (403)
- `NotFoundError` - Resource not found (404)
- `RateLimitError` - Rate limit exceeded (429)
- `ValidationError` - Input validation failures

#### Testing & Quality
- Comprehensive test suite with 80%+ coverage
- Unit tests for all major components
- Mock-based testing for API interactions
- Validation and error handling tests
- pytest configuration with coverage reporting

#### Documentation
- Complete API reference documentation
- Getting started guide with examples
- Troubleshooting guide for common issues
- Multiple usage examples covering all features
- Integration examples showing migration paths

#### Developer Experience
- Convenient factory functions (`create_report_processor`, `create_metadata_manager`)
- Type hints throughout the codebase
- Detailed docstrings for all public methods
- Clear error messages with actionable suggestions
- Consistent naming conventions and patterns

### Features by Use Case

#### For App Store Analytics Teams
- Period comparison and trend analysis
- App performance ranking and benchmarking
- Revenue and subscription analytics
- Top performer identification
- Export capabilities for further analysis

#### For App Store Optimization Teams
- Batch metadata management across portfolios
- Localization status tracking
- App store listing optimization workflows
- Version management and release preparation
- Portfolio analysis and optimization insights

#### For Development Teams
- Direct API access with comprehensive error handling
- Backward compatibility with existing implementations
- Smart data fetching with optimized API usage
- Extensible architecture for custom workflows
- Integration examples and migration guides

### Technical Specifications

#### Requirements
- Python 3.7+
- pandas >= 2.0.0
- requests >= 2.31.0
- PyJWT >= 2.8.0
- cryptography >= 41.0.0
- python-dateutil >= 2.8.0
- ratelimit >= 2.2.1

#### API Compatibility
- App Store Connect API v1
- Sales Reports API versions 1_1 and 1_4
- Subscription Events API version 1_4
- Financial Reports API
- App Metadata Management API

#### Rate Limiting
- Automatic handling of Apple's 50 requests/hour limit
- Exponential backoff for rate limit errors
- Smart frequency selection to minimize API calls
- Bulk operations to reduce request count

### Installation Methods

#### Standard Installation
```bash
pip install appstore-connect-client
```

#### Development Installation
```bash
pip install appstore-connect-client[dev]
```

#### From Source
```bash
git clone https://github.com/chrisbick/appstore-connect-client.git
cd appstore-connect-client
pip install -e .[dev]
```

### Migration Support

#### From BicksterAppStoreSales
- Drop-in replacement for existing `AppStoreConnectAPI` usage
- Same method signatures for core reporting functions
- Enhanced functionality with additional features
- Migration guide and compatibility examples

#### From Custom Implementations
- Standard REST API patterns
- Comprehensive documentation for method mapping
- Examples showing equivalent functionality
- Gradual migration path with coexistence support

### Backward Compatibility

- All core sales reporting methods maintain same signatures
- Enhanced methods are additive, not breaking
- Optional parameters with sensible defaults
- Clear deprecation path for any future changes

### Performance Optimizations

- Smart frequency selection for date ranges
- Automatic DataFrame filtering and processing
- Memory-efficient data handling for large datasets
- Caching for metadata operations
- Batch operations to minimize API calls

### Security Features

- Secure JWT token handling with automatic refresh
- No credential storage in memory longer than necessary
- Input validation to prevent injection attacks
- HTTPS-only communication with Apple APIs
- Comprehensive error handling without credential leakage