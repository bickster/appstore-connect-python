"""
Apple App Store Connect API client.

This module provides a comprehensive client for interacting with the
Apple App Store Connect API, supporting both sales reporting and
metadata management operations.
"""

import jwt
import time
import requests
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from typing import Dict, List, Optional, Union
import gzip
import io
import pandas as pd
from ratelimit import limits, sleep_and_retry
import logging

from .exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    PermissionError,
)


class AppStoreConnectAPI:
    """
    Apple App Store Connect API client.

    Provides comprehensive access to sales reporting and metadata management
    functionality through Apple's App Store Connect API.

    Args:
        key_id: Your App Store Connect API key ID
        issuer_id: Your App Store Connect API issuer ID
        private_key_path: Path to your .p8 private key file
        vendor_number: Your vendor number for sales reports
        app_ids: Optional list of app IDs to filter reports
    """

    BASE_URL = "https://api.appstoreconnect.apple.com/v1"
    REPORT_URL = "https://api.appstoreconnect.apple.com/v1/salesReports"

    def __init__(
        self,
        key_id: str,
        issuer_id: str,
        private_key_path: Union[str, Path],
        vendor_number: str,
        app_ids: Optional[List[str]] = None,
    ):
        """Initialize the App Store Connect API client."""
        self.key_id = key_id
        self.issuer_id = issuer_id
        self.private_key_path = Path(private_key_path)
        self.vendor_number = vendor_number
        self.app_ids = app_ids or []
        self._token: Optional[str] = None
        self._token_expiry: Optional[int] = None

        # Validate required parameters
        if not all([key_id, issuer_id, private_key_path, vendor_number]):
            raise ValidationError("Missing required authentication parameters")

        if not self.private_key_path.exists():
            raise ValidationError(f"Private key file not found: {private_key_path}")

    def _load_private_key(self) -> str:
        """Load the private key from file."""
        try:
            with open(self.private_key_path, "r") as f:
                return f.read()
        except IOError as e:
            raise AuthenticationError(f"Failed to load private key: {e}")

    def _generate_token(self) -> str:
        """Generate a JWT token for App Store Connect API."""
        current_time = int(datetime.now(timezone.utc).timestamp())

        if self._token and self._token_expiry and current_time < self._token_expiry:
            return self._token

        try:
            private_key = self._load_private_key()
        except Exception as e:
            raise AuthenticationError(f"Failed to load private key: {e}")

        # Token expires in 20 minutes (max allowed by Apple)
        expiry = current_time + 1200

        payload = {
            "iss": self.issuer_id,
            "exp": expiry,
            "aud": "appstoreconnect-v1",
        }

        headers = {"alg": "ES256", "kid": self.key_id, "typ": "JWT"}

        try:
            self._token = jwt.encode(
                payload, private_key, algorithm="ES256", headers=headers
            )
        except Exception as e:
            raise AuthenticationError(f"Failed to generate JWT token: {e}")

        self._token_expiry = expiry - 60  # Refresh 1 minute before expiry
        return self._token

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info("_get_headers: Generating token...")
        token = self._generate_token()
        logger.info(
            f"_get_headers: Token generated, " f"length={len(token) if token else 0}"
        )
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _make_request_raw(
        self,
        method: str = "GET",
        url: Optional[str] = None,
        endpoint: Optional[str] = None,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None,
    ) -> requests.Response:
        """Make a rate-limited request to the API."""
        logger = logging.getLogger(__name__)

        logger.info("_make_request: Starting request (rate limit check)")

        # Handle both direct URL and endpoint patterns for
        # backward compatibility
        if url is None and endpoint is not None:
            url = f"{self.BASE_URL}{endpoint}"
        elif url is None:
            raise ValidationError("Either url or endpoint must be provided")

        headers = self._get_headers()

        logger.info(f"_make_request: {method} {url}")
        if params:
            logger.info(f"_make_request: params={params}")

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30,
            )
            logger.info(
                f"_make_request: Response received - " f"status={response.status_code}"
            )
        except requests.exceptions.Timeout as e:
            logger.error(f"_make_request: Request timed out after 30s: {e}")
            raise AppStoreConnectError(f"Request failed: {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"_make_request: Request failed: {e}")
            raise AppStoreConnectError(f"Request failed: {e}")

        # Handle different HTTP status codes
        if response.status_code == 401:
            raise AuthenticationError("Authentication failed - check credentials")
        elif response.status_code == 403:
            raise PermissionError("Insufficient permissions for this operation")
        elif response.status_code == 404:
            raise NotFoundError("Requested resource not found")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code >= 400:
            try:
                error_data = response.json()
                error_msg = error_data.get("errors", [{}])[0].get(
                    "detail", response.text
                )
            except Exception:
                error_msg = response.text
            logging.error(f"API Error {response.status_code}: {error_msg}")
            raise AppStoreConnectError(f"API Error {response.status_code}: {error_msg}")

        return response

    @sleep_and_retry
    @limits(calls=3500, period=3600)  # Apple's rate limit
    def _make_request(self, *args, **kwargs) -> requests.Response:
        """Rate-limited wrapper for _make_request_raw."""
        return self._make_request_raw(*args, **kwargs)

    # ===== SALES REPORTING METHODS =====

    def get_sales_report(
        self,
        report_date: Union[datetime, date],
        report_type: str = "SALES",
        report_subtype: str = "SUMMARY",
        frequency: str = "DAILY",
    ) -> pd.DataFrame:
        """
        Fetch sales report for a specific date.

        Args:
            report_date: Date for the report
            report_type: SALES, SUBSCRIPTION, SUBSCRIPTION_EVENT, or SUBSCRIBER
            report_subtype: SUMMARY or DETAILED
            frequency: DAILY, WEEKLY, MONTHLY, or YEARLY

        Returns:
            DataFrame containing the report data

        Note:
            Apple expects dates in YYYY-MM-DD format in UTC.
            Reports are generated based on Pacific Time but accessed via UTC dates.
        """
        # Different report types have different version numbers
        version_map = {
            "SALES": "1_1",
            "SUBSCRIPTION": "1_4",
            "SUBSCRIPTION_EVENT": "1_4",
            "SUBSCRIBER": "1_4",
        }

        # Format date based on frequency
        if hasattr(report_date, "date"):
            report_date = report_date.date()

        if frequency == "DAILY":
            date_str = report_date.strftime("%Y-%m-%d")
        elif frequency == "WEEKLY":
            # For weekly reports, Apple expects the date of the Sunday that starts the week
            days_since_sunday = (
                report_date.weekday() + 1 if report_date.weekday() != 6 else 0
            )
            sunday = report_date - timedelta(days=days_since_sunday)
            date_str = sunday.strftime("%Y-%m-%d")
        elif frequency == "MONTHLY":
            date_str = report_date.strftime("%Y-%m")
        elif frequency == "YEARLY":
            date_str = report_date.strftime("%Y")
        else:
            date_str = report_date.strftime("%Y-%m-%d")

        params = {
            "filter[frequency]": frequency,
            "filter[reportDate]": date_str,
            "filter[reportSubType]": report_subtype,
            "filter[reportType]": report_type,
            "filter[vendorNumber]": self.vendor_number,
            "filter[version]": version_map.get(report_type, "1_1"),
        }

        response = self._make_request(url=self.REPORT_URL, params=params)

        if response.status_code != 200:
            return pd.DataFrame()

        # Apple returns gzipped TSV data
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
                df = pd.read_csv(gz, sep="\t", engine="python")
        except Exception as e:
            raise AppStoreConnectError(f"Failed to parse report data: {e}")

        # Add report_date column if not present
        if "report_date" not in df.columns:
            df["report_date"] = report_date

        # Filter by app IDs if specified
        if self.app_ids and not df.empty:
            if report_type == "SALES":
                if "Apple Identifier" in df.columns:
                    df = df[df["Apple Identifier"].astype(str).isin(self.app_ids)]
            else:  # SUBSCRIPTION, SUBSCRIPTION_EVENT, SUBSCRIBER reports
                if "App Apple ID" in df.columns:
                    df = df[df["App Apple ID"].astype(str).isin(self.app_ids)]

        return df

    def get_financial_report(
        self, year: int, month: int, region: str = "ZZ"
    ) -> pd.DataFrame:
        """
        Fetch financial report for a specific month.

        Args:
            year: Year of the report
            month: Month of the report (1-12)
            region: Region code (ZZ for all regions)

        Returns:
            DataFrame containing financial data
        """
        params = {
            "filter[regionCode]": region,
            "filter[reportDate]": f"{year}-{month:02d}",
            "filter[reportType]": "FINANCIAL",
            "filter[vendorNumber]": self.vendor_number,
        }

        response = self._make_request(url=self.REPORT_URL, params=params)

        if response.status_code != 200:
            return pd.DataFrame()

        try:
            with gzip.GzipFile(fileobj=io.BytesIO(response.content)) as gz:
                df = pd.read_csv(gz, sep="\t", engine="python")
            return df
        except Exception as e:
            raise AppStoreConnectError(f"Failed to parse financial report: {e}")

    def get_subscription_report(
        self, report_date: Union[datetime, date]
    ) -> pd.DataFrame:
        """Fetch subscription report for a specific date."""
        return self.get_sales_report(
            report_date=report_date,
            report_type="SUBSCRIPTION",
            report_subtype="SUMMARY",
            frequency="DAILY",
        )

    def get_subscription_event_report(
        self, report_date: Union[datetime, date]
    ) -> pd.DataFrame:
        """Fetch subscription event report for a specific date."""
        return self.get_sales_report(
            report_date=report_date,
            report_type="SUBSCRIPTION_EVENT",
            report_subtype="SUMMARY",
            frequency="DAILY",
        )

    def fetch_multiple_days(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, List[pd.DataFrame]]:
        """
        Fetch reports for multiple days using optimized frequency selection.

        Args:
            days: Number of days to fetch (counting backwards from today)
            start_date: Optional start date (overrides days if both dates provided)
            end_date: Optional end date (overrides days if both dates provided)

        Returns:
            Dictionary with report types as keys and lists of DataFrames as values
        """
        if start_date and end_date:
            return self._fetch_date_range(start_date, end_date)
        return self._fetch_multiple_days_optimized(days)

    def _fetch_date_range(
        self, start_date: date, end_date: date
    ) -> Dict[str, List[pd.DataFrame]]:
        """Fetch reports for a specific date range."""
        results: Dict[str, List[pd.DataFrame]] = {
            "sales": [],
            "subscriptions": [],
            "subscription_events": [],
        }

        current_date = start_date
        while current_date <= end_date:
            for report_type in ["SALES", "SUBSCRIPTION", "SUBSCRIPTION_EVENT"]:
                try:
                    df = self.get_sales_report(
                        current_date, report_type, "SUMMARY", "DAILY"
                    )
                    if df is not None and not df.empty:
                        key = {
                            "SALES": "sales",
                            "SUBSCRIPTION": "subscriptions",
                            "SUBSCRIPTION_EVENT": "subscription_events",
                        }[report_type]
                        results[key].append(df)
                except Exception as e:
                    if "404" not in str(e):
                        logging.warning(
                            f"Error fetching {report_type} for {current_date}: {e}"
                        )

            current_date += timedelta(days=1)

        return results

    def _fetch_multiple_days_optimized(
        self, days: int = 30
    ) -> Dict[str, List[pd.DataFrame]]:
        """Fetch reports using smart frequency selection to minimize API calls."""
        results: Dict[str, List[pd.DataFrame]] = {
            "sales": [],
            "subscriptions": [],
            "subscription_events": [],
        }

        # Apple reports are available the next day at 5 AM Pacific Time
        utc_now = datetime.now(timezone.utc)
        pacific_offset = timedelta(hours=8)
        pacific_now = utc_now - pacific_offset

        end_date = pacific_now.date() - timedelta(days=1)
        start_date = end_date - timedelta(days=days - 1)

        # Use daily reports for the last 7 days
        daily_end = end_date
        daily_start = max(start_date, end_date - timedelta(days=6))

        if daily_start <= daily_end:
            current_date = daily_start
            while current_date <= daily_end:
                try:
                    for report_type, result_key in [
                        ("SALES", "sales"),
                        ("SUBSCRIPTION", "subscriptions"),
                        ("SUBSCRIPTION_EVENT", "subscription_events"),
                    ]:
                        df = self.get_sales_report(
                            current_date, report_type=report_type, frequency="DAILY"
                        )
                        if not df.empty:
                            df["report_date"] = current_date
                            df["frequency"] = "DAILY"
                            results[result_key].append(df)
                except Exception as e:
                    logging.warning(
                        f"Error fetching daily data for {current_date}: {e}"
                    )

                current_date += timedelta(days=1)

        # Use weekly reports for older data if applicable
        if days > 7:
            weekly_end = daily_start - timedelta(days=1)
            weekly_start = max(start_date, end_date - timedelta(days=30))

            if weekly_start <= weekly_end:
                current_sunday = weekly_start - timedelta(
                    days=(weekly_start.weekday() + 1) % 7
                )

                while current_sunday <= weekly_end:
                    try:
                        for report_type, result_key in [
                            ("SALES", "sales"),
                            ("SUBSCRIPTION", "subscriptions"),
                            ("SUBSCRIPTION_EVENT", "subscription_events"),
                        ]:
                            df = self.get_sales_report(
                                current_sunday,
                                report_type=report_type,
                                frequency="WEEKLY",
                            )
                            if not df.empty:
                                df["report_date"] = current_sunday
                                df["frequency"] = "WEEKLY"
                                results[result_key].append(df)
                    except Exception as e:
                        logging.warning(
                            f"Error fetching weekly data for week of {current_sunday}: {e}"
                        )

                    current_sunday += timedelta(days=7)

        return results

    # ===== APP METADATA MANAGEMENT METHODS =====

    def get_apps(self) -> Optional[Dict]:
        """Get all apps for the account."""
        try:
            response = self._make_request(method="GET", endpoint="/apps")
            if response.status_code == 200:
                return response.json()
        except PermissionError:
            # API key doesn't have metadata permissions
            return None
        return None

    def get_app_info(self, app_id: str) -> Optional[Dict]:
        """Get information about a specific app."""
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"get_app_info: Making request for app_id={app_id}")
        response = self._make_request(method="GET", endpoint=f"/apps/{app_id}")
        logger.info(f"get_app_info: Response status={response.status_code}")
        if response.status_code == 200:
            return response.json()
        return None

    def get_app_infos(self, app_id: str) -> Optional[Dict]:
        """Get app info objects for an app (contains localization references)."""
        response = self._make_request(method="GET", endpoint=f"/apps/{app_id}/appInfos")
        if response.status_code == 200:
            return response.json()
        return None

    def get_app_info_localizations(self, app_info_id: str) -> Optional[Dict]:
        """Get app info localizations (name, subtitle, etc.)."""
        response = self._make_request(
            method="GET", endpoint=f"/appInfos/{app_info_id}/appInfoLocalizations"
        )
        if response.status_code == 200:
            return response.json()
        return None

    def update_app_info_localization(self, localization_id: str, data: Dict) -> bool:
        """Update app info localization (name, subtitle, privacy policy, etc.)."""
        update_data = {
            "data": {
                "type": "appInfoLocalizations",
                "id": localization_id,
                "attributes": data,
            }
        }
        response = self._make_request(
            method="PATCH",
            endpoint=f"/appInfoLocalizations/{localization_id}",
            data=update_data,
        )
        return response.status_code == 200

    # App Store Version Methods

    def create_app_store_version(
        self, app_id: str, version_string: str, platform: str = "IOS"
    ) -> Optional[Dict]:
        """Create a new App Store version."""
        data = {
            "data": {
                "type": "appStoreVersions",
                "attributes": {
                    "platform": platform,
                    "versionString": version_string,
                },
                "relationships": {"app": {"data": {"type": "apps", "id": app_id}}},
            }
        }
        response = self._make_request(
            method="POST", endpoint="/appStoreVersions", data=data
        )
        if response.status_code == 201:
            return response.json()
        return None

    def get_app_store_versions(self, app_id: str) -> Optional[Dict]:
        """Get all App Store versions for an app."""
        import logging

        logger = logging.getLogger(__name__)

        params = {"filter[app]": app_id, "include": "appStoreVersionLocalizations"}
        logger.info(f"get_app_store_versions: Getting versions for app_id={app_id}")
        logger.info(f"get_app_store_versions: Request params={params}")

        try:
            logger.info("get_app_store_versions: About to call _make_request")
            response = self._make_request(
                method="GET", endpoint="/appStoreVersions", params=params
            )
            logger.info(
                f"get_app_store_versions: Received response "
                f"status={response.status_code}"
            )
        except PermissionError as e:
            logger.error(f"get_app_store_versions: PermissionError: {e}")
            raise  # Re-raise to be caught by caller
        except Exception as e:
            logger.error(
                f"get_app_store_versions: Exception during request: "
                f"{type(e).__name__}: {e}"
            )
            raise

        if response.status_code == 200:
            return response.json()
        return None

    def get_app_store_version_localizations(self, version_id: str) -> Optional[Dict]:
        """Get localizations for an App Store version."""
        response = self._make_request(
            method="GET",
            endpoint=f"/appStoreVersions/{version_id}/appStoreVersionLocalizations",
        )
        if response.status_code == 200:
            return response.json()
        return None

    def update_app_store_version_localization(
        self, localization_id: str, data: Dict
    ) -> bool:
        """Update App Store version localization (description, keywords, etc.)."""
        update_data = {
            "data": {
                "type": "appStoreVersionLocalizations",
                "id": localization_id,
                "attributes": data,
            }
        }
        response = self._make_request(
            method="PATCH",
            endpoint=f"/appStoreVersionLocalizations/{localization_id}",
            data=update_data,
        )
        return response.status_code == 200

    # High-level helper methods

    def update_app_name(self, app_id: str, name: str, locale: str = "en-US") -> bool:
        """Update app name for a specific locale."""
        if len(name) > 30:
            raise ValidationError(
                f"App name too long ({len(name)} chars). " f"Maximum is 30 characters."
            )

        # Get app info ID
        app_infos = self.get_app_infos(app_id)
        if not app_infos or "data" not in app_infos or not app_infos["data"]:
            raise NotFoundError(f"Could not fetch app info for app {app_id}")

        app_info_id = app_infos["data"][0]["id"]

        # Get localizations
        localizations = self.get_app_info_localizations(app_info_id)
        if not localizations or "data" not in localizations:
            raise NotFoundError(f"Could not fetch localizations for app {app_id}")

        # Find the right localization
        for loc in localizations["data"]:
            if loc["attributes"]["locale"] == locale:
                return self.update_app_info_localization(loc["id"], {"name": name})

        raise NotFoundError(f"Localization {locale} not found for app {app_id}")

    def update_app_subtitle(
        self, app_id: str, subtitle: str, locale: str = "en-US"
    ) -> bool:
        """Update app subtitle for a specific locale."""
        if len(subtitle) > 30:
            raise ValidationError(
                f"App subtitle too long ({len(subtitle)} chars). Maximum is 30 characters."
            )

        # Get app info ID
        app_infos = self.get_app_infos(app_id)
        if not app_infos or "data" not in app_infos or not app_infos["data"]:
            raise NotFoundError(f"Could not fetch app info for app {app_id}")

        app_info_id = app_infos["data"][0]["id"]

        # Get localizations
        localizations = self.get_app_info_localizations(app_info_id)
        if not localizations or "data" not in localizations:
            raise NotFoundError(f"Could not fetch localizations for app {app_id}")

        # Find the right localization
        for loc in localizations["data"]:
            if loc["attributes"]["locale"] == locale:
                return self.update_app_info_localization(
                    loc["id"], {"subtitle": subtitle}
                )

        raise NotFoundError(f"Localization {locale} not found for app {app_id}")

    def update_privacy_url(
        self, app_id: str, privacy_url: str, locale: str = "en-US"
    ) -> bool:
        """Update privacy policy URL for a specific locale."""
        # Get app info ID
        app_infos = self.get_app_infos(app_id)
        if not app_infos or "data" not in app_infos or not app_infos["data"]:
            raise NotFoundError(f"Could not fetch app info for app {app_id}")

        app_info_id = app_infos["data"][0]["id"]

        # Get localizations
        localizations = self.get_app_info_localizations(app_info_id)
        if not localizations or "data" not in localizations:
            raise NotFoundError(f"Could not fetch localizations for app {app_id}")

        # Find the right localization
        for loc in localizations["data"]:
            if loc["attributes"]["locale"] == locale:
                return self.update_app_info_localization(
                    loc["id"], {"privacyPolicyUrl": privacy_url}
                )

        raise NotFoundError(f"Localization {locale} not found for app {app_id}")

    def get_editable_version(self, app_id: str) -> Optional[Dict]:
        """Get the first editable version for an app (not in READY_FOR_SALE state)."""
        versions = self.get_app_store_versions(app_id)
        if not versions or "data" not in versions:
            return None

        # Find the first editable version
        for version in versions["data"]:
            state = version["attributes"]["appStoreState"]
            if state in [
                "PREPARE_FOR_SUBMISSION",
                "WAITING_FOR_REVIEW",
                "IN_REVIEW",
                "DEVELOPER_REJECTED",
                "REJECTED",
            ]:
                return version

        return None

    def update_app_description(
        self, app_id: str, description: str, locale: str = "en-US"
    ) -> bool:
        """Update app description for a specific locale (requires editable version)."""
        if len(description) > 4000:
            raise ValidationError(
                f"Description too long ({len(description)} chars). Maximum is 4000 characters."
            )

        # Get editable version
        version = self.get_editable_version(app_id)
        if not version:
            raise ValidationError(
                f"No editable version found for app {app_id}. "
                "Versions must be in preparation or review state."
            )

        version_id = version["id"]

        # Get localizations
        localizations = self.get_app_store_version_localizations(version_id)
        if not localizations or "data" not in localizations:
            raise NotFoundError(
                f"Could not fetch version localizations for app {app_id}"
            )

        # Find the right localization
        for loc in localizations["data"]:
            if loc["attributes"]["locale"] == locale:
                return self.update_app_store_version_localization(
                    loc["id"], {"description": description}
                )

        raise NotFoundError(f"Version localization {locale} not found for app {app_id}")

    def update_app_keywords(
        self, app_id: str, keywords: str, locale: str = "en-US"
    ) -> bool:
        """Update app keywords for a specific locale (requires editable version)."""
        if len(keywords) > 100:
            raise ValidationError(
                f"Keywords too long ({len(keywords)} chars). Maximum is 100 characters."
            )

        # Get editable version
        version = self.get_editable_version(app_id)
        if not version:
            raise ValidationError(
                f"No editable version found for app {app_id}. "
                "Versions must be in preparation or review state."
            )

        version_id = version["id"]

        # Get localizations
        localizations = self.get_app_store_version_localizations(version_id)
        if not localizations or "data" not in localizations:
            raise NotFoundError(
                f"Could not fetch version localizations for app {app_id}"
            )

        # Find the right localization
        for loc in localizations["data"]:
            if loc["attributes"]["locale"] == locale:
                return self.update_app_store_version_localization(
                    loc["id"], {"keywords": keywords}
                )

        raise NotFoundError(f"Version localization {locale} not found for app {app_id}")

    def update_promotional_text(
        self, app_id: str, promo_text: str, locale: str = "en-US"
    ) -> bool:
        """Update promotional text for a specific locale (requires editable version)."""
        if len(promo_text) > 170:
            raise ValidationError(
                f"Promotional text too long ({len(promo_text)} chars). Maximum is 170 characters."
            )

        # Get editable version
        version = self.get_editable_version(app_id)
        if not version:
            raise ValidationError(
                f"No editable version found for app {app_id}. "
                "Versions must be in preparation or review state."
            )

        version_id = version["id"]

        # Get localizations
        localizations = self.get_app_store_version_localizations(version_id)
        if not localizations or "data" not in localizations:
            raise NotFoundError(
                f"Could not fetch version localizations for app {app_id}"
            )

        # Find the right localization
        for loc in localizations["data"]:
            if loc["attributes"]["locale"] == locale:
                return self.update_app_store_version_localization(
                    loc["id"], {"promotionalText": promo_text}
                )

        raise NotFoundError(f"Version localization {locale} not found for app {app_id}")

    def get_current_metadata(self, app_id: str) -> Dict:
        """Get comprehensive metadata for an app including both app-level and version-level info."""  # noqa: E501

        logger = logging.getLogger(__name__)
        logger.info(f"get_current_metadata: Starting for app_id={app_id}")

        metadata: Dict[str, Any] = {
            "app_info": {},
            "app_localizations": {},
            "version_info": {},
            "version_localizations": {},
        }

        try:
            # Get basic app info
            logger.info(f"get_current_metadata: Step 1 - Getting app info for {app_id}")
            start = time.time()
            app_info = self.get_app_info(app_id)
            logger.info(
                f"get_current_metadata: Step 1 completed in {time.time() - start:.2f}s"
            )
            if app_info and "data" in app_info:
                metadata["app_info"] = app_info["data"]["attributes"]
                logger.info("get_current_metadata: app_info retrieved successfully")
            else:
                logger.info("get_current_metadata: app_info is None or missing data")
        except (PermissionError, NotFoundError) as e:
            # Return empty metadata if no permissions
            logger.info(f"get_current_metadata: No permissions for app info: {e}")
            return metadata
        except Exception as e:
            logger.error(
                f"get_current_metadata: Unexpected error in step 1: {type(e).__name__}: {e}"
            )
            return metadata

        # Get app info localizations (name, subtitle, privacy policy)
        try:
            logger.info(
                f"get_current_metadata: Step 2 - Getting app infos for {app_id}"
            )
            start = time.time()
            app_infos = self.get_app_infos(app_id)
            logger.info(
                f"get_current_metadata: Step 2 completed in {time.time() - start:.2f}s"
            )
            if app_infos and "data" in app_infos and app_infos["data"]:
                app_info_id = app_infos["data"][0]["id"]
                logger.info(
                    f"get_current_metadata: Step 3 - Getting localizations for "
                    f"app_info_id {app_info_id}"
                )
                start = time.time()
                localizations = self.get_app_info_localizations(app_info_id)
                logger.info(
                    f"get_current_metadata: Step 3 completed in {time.time() - start:.2f}s"
                )
                if localizations and "data" in localizations:
                    for loc in localizations["data"]:
                        locale = loc["attributes"]["locale"]
                        metadata["app_localizations"][locale] = loc["attributes"]
                    logger.info(
                        f"get_current_metadata: Found {len(localizations['data'])} localizations"
                    )
                else:
                    logger.info("get_current_metadata: No localizations found")
            else:
                logger.info("get_current_metadata: No app_infos data found")
        except (PermissionError, NotFoundError) as e:
            logger.info(f"get_current_metadata: Error getting app localizations: {e}")
            pass
        except Exception as e:
            logger.error(
                f"get_current_metadata: Unexpected error in steps 2-3: {type(e).__name__}: {e}"
            )
            pass

        # Get version info
        try:
            logger.info(
                f"get_current_metadata: Step 4 - Getting app store versions for {app_id}"
            )
            start = time.time()
            versions = self.get_app_store_versions(app_id)
            logger.info(
                f"get_current_metadata: Step 4 completed in {time.time() - start:.2f}s"
            )
            if versions and "data" in versions:
                # Get the most recent version
                if versions["data"]:
                    latest_version = versions["data"][0]
                    metadata["version_info"] = latest_version["attributes"]
                    logger.info(
                        f"get_current_metadata: Found version "
                        f"{latest_version['attributes'].get('versionString', 'unknown')}"
                    )

                    # Get version localizations
                    logger.info(
                        f"get_current_metadata: Step 5 - Getting version localizations "
                        f"for {latest_version['id']}"
                    )
                    start = time.time()
                    version_localizations = self.get_app_store_version_localizations(
                        latest_version["id"]
                    )
                    logger.info(
                        f"get_current_metadata: Step 5 completed in {time.time() - start:.2f}s"
                    )
                    if version_localizations and "data" in version_localizations:
                        for loc in version_localizations["data"]:
                            locale = loc["attributes"]["locale"]
                            metadata["version_localizations"][locale] = loc[
                                "attributes"
                            ]
                        logger.info(
                            f"get_current_metadata: Found "
                            f"{len(version_localizations['data'])} version localizations"
                        )
                    else:
                        logger.info(
                            "get_current_metadata: No version localizations found"
                        )
                else:
                    logger.info("get_current_metadata: No version data found")
            else:
                logger.info("get_current_metadata: No versions response or data")
        except PermissionError as e:
            logger.info(
                f"get_current_metadata: PermissionError getting version info: {e}"
            )
            # Re-raise if it's a 403 on app store versions
            if "appStoreVersions" in str(e):
                raise
        except NotFoundError as e:
            logger.info(
                f"get_current_metadata: NotFoundError getting version info: {e}"
            )
            pass
        except Exception as e:
            logger.error(
                f"get_current_metadata: Unexpected error in steps 4-5: {type(e).__name__}: {e}"
            )
            pass

        logger.info("get_current_metadata: Completed successfully")
        return metadata
