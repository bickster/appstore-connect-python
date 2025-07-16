"""
Utility functions for appstore-connect-client.

This module provides helper functions for common operations like
date handling, data validation, and report processing.
"""

import re
from datetime import datetime, date, timedelta
from typing import Union, List, Dict, Any, Optional
import pandas as pd
from .exceptions import ValidationError


def validate_app_id(app_id: str) -> str:
    """
    Validate an App Store app ID.

    Args:
        app_id: The app ID to validate

    Returns:
        The validated app ID as a string

    Raises:
        ValidationError: If the app ID is invalid
    """
    if not app_id:
        raise ValidationError("App ID cannot be empty")

    # Convert to string and remove whitespace
    app_id_str = str(app_id).strip()

    # App IDs should be numeric and typically 9-10 digits
    if not app_id_str.isdigit():
        raise ValidationError(f"App ID must be numeric, got: {app_id_str}")

    if len(app_id_str) < 9 or len(app_id_str) > 10:
        raise ValidationError(
            f"App ID should be 9-10 digits, got {len(app_id_str)} digits: {app_id_str}"
        )

    return app_id_str


def validate_vendor_number(vendor_number: str) -> str:
    """
    Validate a vendor number.

    Args:
        vendor_number: The vendor number to validate

    Returns:
        The validated vendor number as a string

    Raises:
        ValidationError: If the vendor number is invalid
    """
    if not vendor_number:
        raise ValidationError("Vendor number cannot be empty")

    vendor_str = str(vendor_number).strip()

    # Vendor numbers are typically 8-9 digits
    if not vendor_str.isdigit():
        raise ValidationError(f"Vendor number must be numeric, got: {vendor_str}")

    if len(vendor_str) < 8 or len(vendor_str) > 9:
        raise ValidationError(
            f"Vendor number should be 8-9 digits, got {len(vendor_str)} digits: {vendor_str}"
        )

    return vendor_str


def validate_locale(locale: str) -> str:
    """
    Validate a locale string.

    Args:
        locale: The locale to validate (e.g., 'en-US', 'fr-FR', 'zh-Hans-CN')

    Returns:
        The validated locale string

    Raises:
        ValidationError: If the locale is invalid
    """
    if not locale:
        raise ValidationError("Locale cannot be empty")

    locale = locale.strip()

    # Support standard locales (en-US) and extended locales (zh-Hans-CN)
    if not re.match(r"^[a-z]{2}(-[A-Za-z]+)?-[A-Z]{2}$", locale):
        raise ValidationError(
            f"Invalid locale format. Expected format: 'en-US', got: {locale}"
        )

    return locale


def validate_version_string(version: str) -> str:
    """
    Validate an app version string.

    Args:
        version: The version string to validate

    Returns:
        The validated version string

    Raises:
        ValidationError: If the version string is invalid
    """
    if not version:
        raise ValidationError("Version string cannot be empty")

    version = version.strip()

    # Basic semantic versioning pattern: X.Y.Z
    if not re.match(r"^\d+\.\d+(\.\d+)?$", version):
        raise ValidationError(
            f"Invalid version format. Expected format: 'X.Y.Z', got: {version}"
        )

    return version


def normalize_date(date_input: Union[str, date, datetime]) -> date:
    """
    Normalize various date inputs to a date object.

    Args:
        date_input: Date as string, date, or datetime object

    Returns:
        Normalized date object

    Raises:
        ValidationError: If the date cannot be parsed
    """
    if isinstance(date_input, datetime):
        return date_input.date()
    elif isinstance(date_input, date):
        return date_input
    elif isinstance(date_input, str):
        try:
            # Try parsing ISO format: YYYY-MM-DD
            return datetime.strptime(date_input.strip(), "%Y-%m-%d").date()
        except ValueError:
            try:
                # Try parsing with slashes: MM/DD/YYYY
                return datetime.strptime(date_input.strip(), "%m/%d/%Y").date()
            except ValueError:
                raise ValidationError(
                    f"Invalid date format. Expected 'YYYY-MM-DD' or 'MM/DD/YYYY', got: {date_input}"
                )
    else:
        raise ValidationError(
            f"Invalid date type. Expected str, date, or datetime, got: {type(date_input)}"
        )


def get_date_range(days: int, end_date: Optional[date] = None) -> tuple:
    """
    Get a date range for the specified number of days.

    Args:
        days: Number of days to include in the range
        end_date: End date for the range (defaults to yesterday)

    Returns:
        Tuple of (start_date, end_date)
    """
    if days <= 0:
        raise ValidationError("Number of days must be positive")

    if end_date is None:
        end_date = date.today() - timedelta(days=1)  # Default to yesterday

    start_date = end_date - timedelta(days=days - 1)

    return start_date, end_date


def validate_report_frequency(frequency: str) -> str:
    """
    Validate a report frequency.

    Args:
        frequency: The frequency to validate

    Returns:
        The validated frequency string

    Raises:
        ValidationError: If the frequency is invalid
    """
    valid_frequencies = ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]

    if not frequency:
        raise ValidationError("Frequency cannot be empty")

    frequency = frequency.upper().strip()

    if frequency not in valid_frequencies:
        raise ValidationError(
            f"Invalid frequency. Must be one of: {valid_frequencies}, got: {frequency}"
        )

    return frequency


def validate_report_type(report_type: str) -> str:
    """
    Validate a report type.

    Args:
        report_type: The report type to validate

    Returns:
        The validated report type string

    Raises:
        ValidationError: If the report type is invalid
    """
    valid_types = [
        "SALES",
        "SUBSCRIPTION",
        "SUBSCRIPTION_EVENT",
        "SUBSCRIBER",
        "FINANCIAL",
    ]

    if not report_type:
        raise ValidationError("Report type cannot be empty")

    report_type = report_type.upper().strip()

    if report_type not in valid_types:
        raise ValidationError(
            f"Invalid report type. Must be one of: {valid_types}, got: {report_type}"
        )

    return report_type


def validate_report_subtype(report_subtype: str) -> str:
    """
    Validate a report subtype.

    Args:
        report_subtype: The report subtype to validate

    Returns:
        The validated report subtype string

    Raises:
        ValidationError: If the report subtype is invalid
    """
    valid_subtypes = ["SUMMARY", "DETAILED"]

    if not report_subtype:
        raise ValidationError("Report subtype cannot be empty")

    report_subtype = report_subtype.upper().strip()

    if report_subtype not in valid_subtypes:
        raise ValidationError(
            f"Invalid report subtype. Must be one of: {valid_subtypes}, got: {report_subtype}"
        )

    return report_subtype


def sanitize_app_name(name: str) -> str:
    """
    Sanitize an app name for safe usage in filenames and identifiers.

    Args:
        name: The app name to sanitize

    Returns:
        Sanitized app name
    """
    if not name:
        return "unnamed_app"

    # Remove/replace special characters, keep only alphanumeric, spaces, hyphens, underscores
    sanitized = re.sub(r"[^\w\s\-_]", "", name.strip())

    # Replace multiple spaces with single space
    sanitized = re.sub(r"\s+", " ", sanitized)

    # Don't replace spaces with underscores - keep spaces as is
    # This was the issue - the test expects "App 2023" not "App_2023"

    # Limit length
    if len(sanitized) > 50:
        sanitized = sanitized[:50]

    return sanitized or "unnamed_app"


def combine_dataframes(
    dfs: List[pd.DataFrame], sort_by: Optional[str] = None
) -> pd.DataFrame:
    """
    Combine multiple DataFrames into a single DataFrame.

    Args:
        dfs: List of DataFrames to combine
        sort_by: Optional column name to sort by

    Returns:
        Combined DataFrame
    """
    if not dfs:
        return pd.DataFrame()

    # Filter out empty DataFrames
    non_empty_dfs = [df for df in dfs if not df.empty]

    if not non_empty_dfs:
        return pd.DataFrame()

    # Combine all DataFrames
    combined_df = pd.concat(non_empty_dfs, ignore_index=True)

    # Sort if requested
    if sort_by and sort_by in combined_df.columns:
        combined_df = combined_df.sort_values(sort_by).reset_index(drop=True)

    return combined_df


def calculate_summary_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculate summary metrics from a sales DataFrame.

    Args:
        df: Sales DataFrame

    Returns:
        Dictionary of summary metrics
    """
    if df.empty:
        return {
            "total_units": 0,
            "total_revenue": 0.0,
            "unique_apps": 0,
            "date_range": None,
            "countries": 0,
        }

    metrics: Dict[str, Any] = {}

    # Basic counts
    if "Units" in df.columns:
        metrics["total_units"] = int(df["Units"].sum())

    if "Developer Proceeds" in df.columns:
        metrics["total_revenue"] = float(df["Developer Proceeds"].sum())
    elif "Proceeds" in df.columns:
        metrics["total_revenue"] = float(df["Proceeds"].sum())

    # App diversity
    if "Apple Identifier" in df.columns:
        metrics["unique_apps"] = df["Apple Identifier"].nunique()
    elif "App Apple ID" in df.columns:
        metrics["unique_apps"] = df["App Apple ID"].nunique()

    # Date range
    if "report_date" in df.columns:
        min_date = df["report_date"].min()
        max_date = df["report_date"].max()
        if pd.notna(min_date) and pd.notna(max_date):
            metrics["date_range"] = (min_date, max_date)

    # Geographic diversity
    if "Country Code" in df.columns:
        metrics["countries"] = df["Country Code"].nunique()

    return metrics


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format a currency amount for display.

    Args:
        amount: The amount to format
        currency: The currency code

    Returns:
        Formatted currency string
    """
    if currency.upper() == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to a maximum length.

    Args:
        text: The text to truncate
        max_length: Maximum length allowed
        suffix: Suffix to append if truncated

    Returns:
        Truncated string
    """
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunks
    """
    if chunk_size <= 0:
        raise ValidationError("Chunk size must be positive")

    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def get_app_platform(bundle_id: str) -> str:
    """
    Determine the likely platform from a bundle ID.

    Args:
        bundle_id: The app bundle ID

    Returns:
        Platform identifier ('ios', 'macos', 'tvos', 'watchos', 'unknown')
    """
    if not bundle_id:
        return "unknown"

    bundle_lower = bundle_id.lower()

    # These are heuristics based on common patterns
    if any(keyword in bundle_lower for keyword in ["macos", "mac", "osx"]):
        return "macos"
    elif any(keyword in bundle_lower for keyword in ["tvos", "appletv", "tv"]):
        return "tvos"
    elif any(keyword in bundle_lower for keyword in ["watchos", "watch"]):
        return "watchos"
    else:
        # Default to iOS for mobile apps
        return "ios"
