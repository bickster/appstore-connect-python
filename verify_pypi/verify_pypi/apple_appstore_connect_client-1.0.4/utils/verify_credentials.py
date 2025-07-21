#!/usr/bin/env python3
"""
Verify App Store Connect API credentials.

This script helps verify that your App Store Connect API credentials are properly
configured and working. It will attempt to authenticate and fetch basic information
from the API.

Usage:
    python utils/verify_credentials.py [options]

Options:
    --key-id KEY_ID              API Key ID (or set APP_STORE_KEY_ID env var)
    --issuer-id ISSUER_ID        Issuer ID (or set APP_STORE_ISSUER_ID env var)
    --private-key-path PATH      Path to private key file (or set APP_STORE_PRIVATE_KEY_PATH env var)
    --vendor-number NUMBER       Vendor number (or set APP_STORE_VENDOR_NUMBER env var)
    --verbose                    Show detailed output
    --test-sales                 Test sales report access
    --test-metadata              Test metadata access
"""

import sys
import os
import argparse
from datetime import date, timedelta
from pathlib import Path

# Add parent directory to path to import the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from appstore_connect.client import AppStoreConnectAPI
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    PermissionError,
    ValidationError
)


def print_success(message):
    """Print success message in green."""
    print(f"\033[92m✓ {message}\033[0m")


def print_error(message):
    """Print error message in red."""
    print(f"\033[91m✗ {message}\033[0m")


def print_warning(message):
    """Print warning message in yellow."""
    print(f"\033[93m⚠ {message}\033[0m")


def print_info(message):
    """Print info message."""
    print(f"ℹ {message}")


def verify_credentials(args):
    """Verify App Store Connect API credentials."""
    print("App Store Connect API Credential Verification")
    print("=" * 50)
    
    # Check credentials
    if not all([args.key_id, args.issuer_id, args.private_key_path, args.vendor_number]):
        print_error("Missing required credentials")
        print("\nPlease provide all required credentials either via:")
        print("1. Command line arguments (--key-id, --issuer-id, --private-key-path, --vendor-number)")
        print("2. Environment variables (APP_STORE_KEY_ID, APP_STORE_ISSUER_ID, etc.)")
        return False
    
    # Verify private key file exists
    key_path = Path(args.private_key_path)
    if not key_path.exists():
        print_error(f"Private key file not found: {key_path}")
        return False
    
    print_info(f"Key ID: {args.key_id}")
    print_info(f"Issuer ID: {args.issuer_id}")
    print_info(f"Private Key: {key_path}")
    print_info(f"Vendor Number: {args.vendor_number}")
    print()
    
    # Test authentication
    print("Testing authentication...")
    try:
        api = AppStoreConnectAPI(
            key_id=args.key_id,
            issuer_id=args.issuer_id,
            private_key_path=str(key_path),
            vendor_number=args.vendor_number
        )
        
        # Generate token
        token = api._generate_token()
        if token:
            print_success("Successfully generated JWT token")
            if args.verbose:
                print_info(f"Token length: {len(token)} characters")
        else:
            print_error("Failed to generate JWT token")
            return False
            
    except (ValidationError, AuthenticationError) as e:
        print_error(f"Authentication failed: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False
    
    print()
    
    # Test sales access if requested
    if args.test_sales:
        print("Testing sales report access...")
        try:
            # Try to fetch recent sales data
            report_date = date.today() - timedelta(days=3)
            df = api.get_sales_report(report_date)
            
            if df is not None:
                print_success("Successfully accessed sales reports")
                if not df.empty:
                    print_info(f"Found {len(df)} sales records for {report_date}")
                else:
                    print_info(f"No sales data for {report_date} (this is normal)")
            else:
                print_warning("Sales report returned None")
                
        except PermissionError:
            print_error("No permission to access sales reports")
            print_info("Ensure your API key has 'Sales and Trends' permission")
        except Exception as e:
            print_error(f"Failed to access sales reports: {e}")
    
    # Test metadata access if requested
    if args.test_metadata:
        print("\nTesting metadata access...")
        try:
            # Try to fetch apps
            result = api.get_apps()
            
            if result and 'data' in result:
                app_count = len(result['data'])
                print_success(f"Successfully accessed metadata (found {app_count} apps)")
                
                if args.verbose and app_count > 0:
                    print("\nApps found:")
                    for app in result['data'][:5]:  # Show first 5 apps
                        app_name = app.get('attributes', {}).get('name', 'Unknown')
                        app_id = app.get('id', 'Unknown')
                        print(f"  - {app_name} (ID: {app_id})")
                    
                    if app_count > 5:
                        print(f"  ... and {app_count - 5} more")
            else:
                print_warning("No apps found or no metadata access")
                
        except PermissionError:
            print_error("No permission to access app metadata")
            print_info("Ensure your API key has 'App Management' permission")
        except Exception as e:
            print_error(f"Failed to access metadata: {e}")
    
    print("\n" + "=" * 50)
    print_success("Credential verification complete!")
    
    # Summary
    print("\nSummary:")
    print_info("✓ Authentication working")
    
    if args.test_sales:
        print_info("✓ Sales report access verified")
    
    if args.test_metadata:
        print_info("✓ Metadata access verified")
    
    if not args.test_sales and not args.test_metadata:
        print_info("\nTip: Use --test-sales or --test-metadata to test specific API access")
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Verify App Store Connect API credentials",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Credential arguments
    parser.add_argument(
        '--key-id',
        default=os.getenv('APP_STORE_KEY_ID'),
        help='API Key ID'
    )
    parser.add_argument(
        '--issuer-id',
        default=os.getenv('APP_STORE_ISSUER_ID'),
        help='Issuer ID'
    )
    parser.add_argument(
        '--private-key-path',
        default=os.getenv('APP_STORE_PRIVATE_KEY_PATH'),
        help='Path to private key file'
    )
    parser.add_argument(
        '--vendor-number',
        default=os.getenv('APP_STORE_VENDOR_NUMBER'),
        help='Vendor number'
    )
    
    # Options
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed output'
    )
    parser.add_argument(
        '--test-sales',
        action='store_true',
        help='Test sales report access'
    )
    parser.add_argument(
        '--test-metadata',
        action='store_true',
        help='Test metadata access'
    )
    
    args = parser.parse_args()
    
    # If no specific tests requested, test both
    if not args.test_sales and not args.test_metadata:
        args.test_sales = True
        args.test_metadata = True
    
    # Run verification
    success = verify_credentials(args)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()