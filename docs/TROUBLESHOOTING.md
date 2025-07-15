# Troubleshooting Guide

This guide covers common issues and their solutions when using `appstore-connect-client`.

## Authentication Issues

### Error: "Authentication failed - check credentials"

**Symptoms:**
- `AuthenticationError` raised during API calls
- 401 HTTP status code

**Common Causes & Solutions:**

1. **Invalid Key ID or Issuer ID**
   ```python
   # ❌ Incorrect
   api = AppStoreConnectAPI(
       key_id='wrong_key',
       issuer_id='wrong_issuer',
       # ...
   )
   
   # ✅ Correct - verify these in App Store Connect
   api = AppStoreConnectAPI(
       key_id='ABCD1234EF',  # 10-character string
       issuer_id='12345678-1234-1234-1234-123456789012',  # UUID format
       # ...
   )
   ```

2. **Private Key File Issues**
   ```python
   # Check file exists and is readable
   import os
   key_path = '/path/to/AuthKey_XXXXXXXXXX.p8'
   
   if not os.path.exists(key_path):
       print(f"Key file not found: {key_path}")
   elif not os.access(key_path, os.R_OK):
       print(f"Key file not readable: {key_path}")
   else:
       print("Key file OK")
   ```

3. **Expired or Revoked API Key**
   - Check App Store Connect → Users and Access → Keys
   - Verify your key is still active
   - Regenerate if necessary

4. **Wrong Key Format**
   ```
   # ✅ Correct .p8 file format:
   -----BEGIN PRIVATE KEY-----
   MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQg...
   -----END PRIVATE KEY-----
   ```

### Error: "Failed to load private key"

**Solutions:**

1. **Check File Path**
   ```python
   from pathlib import Path
   
   key_path = Path('/path/to/AuthKey_XXXXXXXXXX.p8')
   print(f"Exists: {key_path.exists()}")
   print(f"Is file: {key_path.is_file()}")
   print(f"Size: {key_path.stat().st_size} bytes")
   ```

2. **File Permissions**
   ```bash
   # Set correct permissions
   chmod 600 /path/to/AuthKey_XXXXXXXXXX.p8
   ```

3. **File Format Issues**
   - Ensure file is in .p8 format (not .p12 or other)
   - Re-download from App Store Connect if corrupted

## Permission Issues

### Error: "Insufficient permissions for this operation"

**Symptoms:**
- `PermissionError` raised during metadata operations
- 403 HTTP status code

**Solutions:**

1. **Check API Key Permissions**
   - Sales Reports: Read access for sales data
   - App Metadata: Write access for app store listing management
   - Create separate keys if needed for different operations

2. **Operations by Permission Level**
   ```python
   # ✅ Read-only operations (Sales Reports permission)
   api.get_sales_report(date.today())
   api.get_apps()
   api.get_current_metadata('123456789')
   
   # ❌ Write operations (App Metadata permission required)
   api.update_app_name('123456789', 'New Name')
   api.create_app_store_version('123456789', '2.0.0')
   ```

3. **Team Role Permissions**
   - Verify your App Store Connect role has sufficient permissions
   - Contact your team admin if you need elevated access

## Data Issues

### Error: "No sales data found" or Empty DataFrames

**Common Causes:**

1. **Report Availability Timing**
   ```python
   # ❌ Today's report not available yet
   today_sales = api.get_sales_report(date.today())
   
   # ✅ Yesterday's report should be available
   yesterday = date.today() - timedelta(days=1)
   sales = api.get_sales_report(yesterday)
   ```

2. **Weekend/Holiday Reporting**
   - Sales reports may not be available on weekends
   - Check for multiple days if one day is empty

3. **App ID Filtering**
   ```python
   # If filtering to specific apps, ensure they exist
   api = AppStoreConnectAPI(
       # ...
       app_ids=['123456789', '987654321']  # Must be valid
   )
   ```

4. **Region/Country Filtering**
   - Some reports may be empty for specific regions
   - Try fetching without filters first

### Error: "Invalid date format"

**Solutions:**

1. **Use Correct Date Types**
   ```python
   from datetime import date, datetime
   
   # ✅ Correct
   api.get_sales_report(date(2023, 1, 15))
   api.get_sales_report(datetime(2023, 1, 15))
   api.get_sales_report("2023-01-15")
   
   # ❌ Incorrect
   api.get_sales_report("01/15/2023")  # Wrong format
   api.get_sales_report(1673740800)    # Timestamp
   ```

## Rate Limiting Issues

### Error: "Rate limit exceeded"

**Symptoms:**
- `RateLimitError` raised
- 429 HTTP status code

**Solutions:**

1. **Automatic Retry**
   ```python
   import time
   from appstore_connect.exceptions import RateLimitError
   
   def fetch_with_retry(api, date_obj, max_retries=3):
       for attempt in range(max_retries):
           try:
               return api.get_sales_report(date_obj)
           except RateLimitError:
               if attempt < max_retries - 1:
                   wait_time = 2 ** attempt * 60  # Exponential backoff
                   time.sleep(wait_time)
               else:
                   raise
   ```

2. **Optimize API Usage**
   ```python
   # ❌ Many individual calls
   for day in date_range:
       sales = api.get_sales_report(day)
   
   # ✅ Bulk fetch (automatically optimized)
   reports = api.fetch_multiple_days(days=30)
   ```

3. **Spread Requests Over Time**
   - Apple allows 50 requests per hour
   - Use bulk operations when possible
   - Cache results to avoid repeated calls

## Validation Errors

### Error: "App ID must be numeric"

```python
# ❌ Incorrect
api.update_app_name('com.example.app', 'Name')

# ✅ Correct - use App Store ID
api.update_app_name('123456789', 'Name')
```

### Error: "App name too long"

```python
# ❌ Too long (> 30 characters)
api.update_app_name('123456789', 'This is a very long app name that exceeds the limit')

# ✅ Correct
api.update_app_name('123456789', 'Short App Name')
```

### Error: "Invalid locale format"

```python
# ❌ Incorrect formats
api.update_app_name('123456789', 'Name', 'en')     # Missing country
api.update_app_name('123456789', 'Name', 'en_US')  # Wrong separator

# ✅ Correct
api.update_app_name('123456789', 'Name', 'en-US')
```

## Network Issues

### Error: "Request failed: ConnectionError"

**Solutions:**

1. **Check Internet Connection**
   ```python
   import requests
   
   try:
       response = requests.get('https://api.appstoreconnect.apple.com', timeout=10)
       print(f"Apple API reachable: {response.status_code}")
   except requests.exceptions.ConnectionError:
       print("Network connection failed")
   ```

2. **Proxy Configuration**
   ```python
   import os
   
   # Set proxy if required
   os.environ['HTTPS_PROXY'] = 'http://proxy.company.com:8080'
   
   # Or configure in requests session
   import requests
   
   session = requests.Session()
   session.proxies.update({'https': 'http://proxy.company.com:8080'})
   ```

3. **Firewall Issues**
   - Ensure outbound HTTPS (443) access to `api.appstoreconnect.apple.com`
   - Check corporate firewall settings

### Error: "Request timeout"

```python
# Increase timeout for slow connections
api = AppStoreConnectAPI(
    # ... credentials ...
)

# The library uses 30-second timeouts by default
# For very slow connections, consider implementing retry logic
```

## Version and Environment Issues

### ImportError: "No module named 'appstore_connect'"

**Solutions:**

1. **Install Package**
   ```bash
   pip install appstore-connect-client
   ```

2. **Virtual Environment**
   ```bash
   # Ensure you're in the correct virtual environment
   which python
   pip list | grep appstore-connect
   ```

3. **Python Version**
   ```bash
   # Requires Python 3.7+
   python --version
   ```

### Error: "pandas not found" or Other Dependencies

```bash
# Install all dependencies
pip install appstore-connect-client[dev]

# Or install missing packages individually
pip install pandas>=2.0.0 requests>=2.31.0
```

## Data Processing Issues

### Empty DataFrames After Processing

```python
# Check data at each step
reports = api.fetch_multiple_days(days=7)
print(f"Sales reports: {len(reports.get('sales', []))}")

for i, df in enumerate(reports.get('sales', [])):
    print(f"Report {i}: {len(df)} rows")
    if not df.empty:
        print(f"Columns: {list(df.columns)}")
        print(f"Date range: {df['report_date'].min()} to {df['report_date'].max()}")
```

### Memory Issues with Large Datasets

```python
# Process data in chunks for large date ranges
from datetime import timedelta

def process_large_date_range(start_date, end_date, chunk_days=7):
    current_date = start_date
    all_data = []
    
    while current_date <= end_date:
        chunk_end = min(current_date + timedelta(days=chunk_days-1), end_date)
        
        reports = api.fetch_multiple_days(
            start_date=current_date,
            end_date=chunk_end
        )
        
        # Process chunk immediately
        for df in reports.get('sales', []):
            if not df.empty:
                # Process and store essential data only
                summary = df.groupby('Apple Identifier').agg({
                    'Units': 'sum',
                    'Developer Proceeds': 'sum'
                }).reset_index()
                all_data.append(summary)
        
        current_date = chunk_end + timedelta(days=1)
    
    return all_data
```

## Debugging Tips

### Enable Detailed Logging

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('appstore_connect')
logger.setLevel(logging.DEBUG)

# This will show API requests, responses, and errors
```

### Inspect API Responses

```python
# Use a proxy tool like mitmproxy to inspect HTTP traffic
# Or add debug prints in your code

import json

try:
    apps = api.get_apps()
    print(json.dumps(apps, indent=2))
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
```

### Validate Your Setup

```python
def validate_setup():
    """Validate API setup and credentials."""
    try:
        # Test basic connectivity
        apps = api.get_apps()
        if apps and 'data' in apps:
            print(f"✅ API connection successful: {len(apps['data'])} apps found")
        else:
            print("⚠️ API connected but no apps found")
        
        # Test sales data access
        yesterday = date.today() - timedelta(days=1)
        sales = api.get_sales_report(yesterday)
        print(f"✅ Sales data access: {len(sales)} records for {yesterday}")
        
        # Test metadata access (if you have write permissions)
        if apps and 'data' in apps:
            app_id = apps['data'][0]['id']
            metadata = api.get_current_metadata(app_id)
            print(f"✅ Metadata access: Retrieved data for app {app_id}")
        
    except AuthenticationError:
        print("❌ Authentication failed - check credentials")
    except PermissionError:
        print("❌ Permission denied - check API key scope")
    except Exception as e:
        print(f"❌ Setup validation failed: {e}")

validate_setup()
```

## Getting Additional Help

If you're still experiencing issues:

1. **Check the GitHub Issues**
   - Search [existing issues](https://github.com/chrisbick/appstore-connect-client/issues)
   - Look for similar problems and solutions

2. **Create a Detailed Bug Report**
   ```python
   # Include this information in your bug report:
   import appstore_connect
   import sys
   import platform
   
   print(f"appstore-connect-client version: {appstore_connect.__version__}")
   print(f"Python version: {sys.version}")
   print(f"Platform: {platform.platform()}")
   print(f"Error details: [include full traceback]")
   ```

3. **Apple Developer Support**
   - For App Store Connect API issues
   - For account or permission problems

4. **Security Note**
   - Never include your actual API keys or private keys in bug reports
   - Use placeholder values when sharing configuration examples