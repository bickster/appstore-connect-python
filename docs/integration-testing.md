# Integration Testing Guide

This guide explains how to set up and run integration tests for the appstore-connect-client library.

## Overview

Integration tests verify that the library works correctly with the actual App Store Connect API. Unlike unit tests that use mocked responses, integration tests make real API calls and require valid credentials.

## Prerequisites

1. **Apple Developer Account**: You need an active Apple Developer account
2. **App Store Connect API Key**: Generate an API key with appropriate permissions
3. **Python Environment**: Python 3.7 or higher with the library installed

## Setting Up API Credentials

### Step 1: Generate API Key

1. Log in to [App Store Connect](https://appstoreconnect.apple.com/)
2. Navigate to **Users and Access** → **Keys**
3. Click the **+** button to create a new key
4. Select the required permissions:
   - **Sales and Trends** - For sales report testing
   - **App Management** - For metadata testing (optional)
5. Download the `.p8` private key file (you can only download it once!)
6. Note down:
   - **Key ID**: The identifier shown in the keys list
   - **Issuer ID**: Found at the top of the keys page
   - **Vendor Number**: Found in **Payments and Financial Reports**

### Step 2: Configure Environment Variables

Set the following environment variables for integration testing:

```bash
# Required for all integration tests
export INTEGRATION_TEST_KEY_ID="YOUR_KEY_ID"
export INTEGRATION_TEST_ISSUER_ID="YOUR_ISSUER_ID"
export INTEGRATION_TEST_PRIVATE_KEY_PATH="/path/to/AuthKey_YOUR_KEY_ID.p8"
export INTEGRATION_TEST_VENDOR_NUMBER="YOUR_VENDOR_NUMBER"
```

You can also create a `.env.test` file in the project root:

```bash
INTEGRATION_TEST_KEY_ID=YOUR_KEY_ID
INTEGRATION_TEST_ISSUER_ID=YOUR_ISSUER_ID
INTEGRATION_TEST_PRIVATE_KEY_PATH=/path/to/AuthKey_YOUR_KEY_ID.p8
INTEGRATION_TEST_VENDOR_NUMBER=YOUR_VENDOR_NUMBER
```

### Step 3: Verify Credentials

Use the included verification script to test your credentials:

```bash
python utils/verify_credentials.py \
    --key-id YOUR_KEY_ID \
    --issuer-id YOUR_ISSUER_ID \
    --private-key-path /path/to/key.p8 \
    --vendor-number YOUR_VENDOR_NUMBER \
    --test-sales \
    --test-metadata
```

## Running Integration Tests

### Run All Integration Tests

```bash
pytest tests/test_integration.py -v
```

### Run Specific Test Classes

```bash
# Test authentication only
pytest tests/test_integration.py::TestAPIAuthentication -v

# Test sales reporting
pytest tests/test_integration.py::TestSalesReporting -v

# Test metadata management
pytest tests/test_integration.py::TestMetadataManagement -v
```

### Skip Integration Tests

When running the full test suite, you can skip integration tests:

```bash
pytest -m "not integration"
```

### Run with Coverage

```bash
pytest tests/test_integration.py --cov=appstore_connect -v
```

## Writing Integration Tests

### Test Structure

Integration tests should be marked with the `@pytest.mark.integration` decorator:

```python
import pytest
from appstore_connect.client import AppStoreConnectAPI

@pytest.mark.integration
class TestNewFeature:
    def test_real_api_call(self):
        """Test that actually calls the API."""
        creds = get_integration_credentials()
        api = AppStoreConnectAPI(**creds)
        
        # Make real API call
        result = api.some_method()
        
        # Verify real response
        assert result is not None
```

### Best Practices

1. **Check for Credentials**: Always check if credentials are configured:
   ```python
   def get_integration_credentials():
       required = ['INTEGRATION_TEST_KEY_ID', ...]
       missing = [var for var in required if not os.getenv(var)]
       if missing:
           pytest.skip(f"Missing credentials: {missing}")
   ```

2. **Handle Permission Errors**: API keys might not have all permissions:
   ```python
   try:
       result = api.update_app_metadata(...)
   except PermissionError:
       pytest.skip("API key lacks metadata permissions")
   ```

3. **Use Recent Dates**: For sales data, use recent dates:
   ```python
   # Data might not be available for today
   report_date = date.today() - timedelta(days=3)
   ```

4. **Clean Up**: Don't modify production data in tests

5. **Rate Limiting**: Be mindful of API rate limits (50 requests/hour)

## Common Issues

### No Data Available

Sales and financial data may not be available for:
- Future dates
- Very recent dates (1-2 days delay)
- Dates with no sales activity

### Permission Errors

If you see 403 errors, check that your API key has the required permissions:
- Sales reports → "Sales and Trends" permission
- Metadata operations → "App Management" permission

### Rate Limiting

If you hit rate limits:
- Wait 1 hour before retrying
- Run fewer tests at once
- Use mock tests for development

### Authentication Failures

Common causes:
- Expired API key (regenerate in App Store Connect)
- Wrong private key file
- Incorrect key ID or issuer ID

## Continuous Integration

For CI/CD pipelines, you can:

1. **Store credentials securely**:
   - Use GitHub Secrets, GitLab CI/CD variables, etc.
   - Never commit credentials to the repository

2. **Run integration tests separately**:
   ```yaml
   - name: Run Unit Tests
     run: pytest -m "not integration"
   
   - name: Run Integration Tests
     if: github.event_name == 'push' && github.ref == 'refs/heads/main'
     env:
       INTEGRATION_TEST_KEY_ID: ${{ secrets.APPLE_KEY_ID }}
       # ... other secrets
     run: pytest -m integration
   ```

3. **Schedule regular runs**:
   - Run integration tests nightly or weekly
   - Monitor for API changes or issues

## Security Considerations

1. **Never commit credentials**: Use environment variables or secure vaults
2. **Limit key permissions**: Only grant necessary permissions
3. **Rotate keys regularly**: Regenerate API keys periodically
4. **Use separate keys**: Don't use production keys for testing
5. **Audit access**: Review API key usage in App Store Connect

## Troubleshooting

### Debug Mode

Enable verbose output for debugging:

```bash
pytest tests/test_integration.py -vvs
```

### Check API Status

Verify App Store Connect API is operational:
- Check [Apple System Status](https://developer.apple.com/system-status/)
- Try manual API calls with curl

### Validate Credentials

Use the verification script with verbose mode:

```bash
python utils/verify_credentials.py --verbose
```

### Contact Support

For API issues:
- [App Store Connect Support](https://developer.apple.com/contact/)
- [Developer Forums](https://developer.apple.com/forums/)

## Example Test Run

Here's what a successful integration test run looks like:

```
$ pytest tests/test_integration.py -v
========================= test session starts =========================
platform darwin -- Python 3.9.0, pytest-7.4.0
collected 15 items

tests/test_integration.py::TestAPIAuthentication::test_valid_authentication PASSED
tests/test_integration.py::TestAPIAuthentication::test_invalid_key_id PASSED
tests/test_integration.py::TestSalesReporting::test_get_sales_report_recent PASSED
tests/test_integration.py::TestSalesReporting::test_fetch_multiple_days PASSED
tests/test_integration.py::TestMetadataManagement::test_get_apps PASSED
...

========================= 15 passed in 12.34s =========================
```