"""
Report processing and analysis utilities for appstore-connect-client.

This module provides high-level functions for processing and analyzing
App Store Connect reports with common business logic.
"""

import pandas as pd
from datetime import date, timedelta
from typing import Dict, List, Optional, Any
from .client import AppStoreConnectAPI
from .utils import (
    combine_dataframes,
    calculate_summary_metrics,
    format_currency,
)
from .exceptions import ValidationError


class ReportProcessor:
    """
    High-level report processor for App Store Connect data.

    This class provides convenient methods for fetching and processing
    multiple types of reports with built-in analytics.
    """

    def __init__(self, api: AppStoreConnectAPI):
        """Initialize with an API client."""
        self.api = api

    def get_sales_summary(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get a comprehensive sales summary for the specified period.

        Args:
            days: Number of days to analyze (if start/end dates not provided)
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dictionary containing sales summary and metrics
        """
        # Fetch sales data
        reports = self.api.fetch_multiple_days(days, start_date, end_date)
        sales_df = combine_dataframes(reports.get("sales", []), sort_by="report_date")

        if sales_df.empty:
            return {
                "summary": calculate_summary_metrics(pd.DataFrame()),
                "by_app": {},
                "by_country": {},
                "by_date": {},
                "top_performers": {},
            }

        # Calculate overall metrics
        summary = calculate_summary_metrics(sales_df)

        # Break down by app
        by_app = {}
        if "Apple Identifier" in sales_df.columns:
            app_groups = sales_df.groupby("Apple Identifier")
            for app_id, group in app_groups:
                app_name = group["Title"].iloc[0] if "Title" in group.columns else f"App {app_id}"
                by_app[str(app_id)] = {
                    "name": app_name,
                    "units": int(group["Units"].sum()),
                    "revenue": (
                        float(group["Developer Proceeds"].sum())
                        if "Developer Proceeds" in group.columns
                        else 0.0
                    ),
                    "countries": (
                        group["Country Code"].nunique() if "Country Code" in group.columns else 0
                    ),
                }

        # Break down by country
        by_country = {}
        if "Country Code" in sales_df.columns:
            country_groups = sales_df.groupby("Country Code")
            for country, group in country_groups:
                by_country[country] = {
                    "units": int(group["Units"].sum()),
                    "revenue": (
                        float(group["Developer Proceeds"].sum())
                        if "Developer Proceeds" in group.columns
                        else 0.0
                    ),
                    "apps": (
                        group["Apple Identifier"].nunique()
                        if "Apple Identifier" in group.columns
                        else 0
                    ),
                }

        # Break down by date
        by_date = {}
        if "report_date" in sales_df.columns:
            date_groups = sales_df.groupby("report_date")
            for report_date, group in date_groups:
                date_str = (
                    report_date.strftime("%Y-%m-%d")
                    if hasattr(report_date, "strftime")
                    else str(report_date)
                )
                by_date[date_str] = {
                    "units": int(group["Units"].sum()),
                    "revenue": (
                        float(group["Developer Proceeds"].sum())
                        if "Developer Proceeds" in group.columns
                        else 0.0
                    ),
                    "transactions": len(group),
                }

        # Top performers
        top_performers = {}
        if by_app:
            # Top apps by revenue
            top_by_revenue = sorted(by_app.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]
            top_performers["by_revenue"] = [
                {"app_id": app_id, "name": data["name"], "revenue": data["revenue"]}
                for app_id, data in top_by_revenue
            ]

            # Top apps by units
            top_by_units = sorted(by_app.items(), key=lambda x: x[1]["units"], reverse=True)[:5]
            top_performers["by_units"] = [
                {"app_id": app_id, "name": data["name"], "units": data["units"]}
                for app_id, data in top_by_units
            ]

        if by_country:
            # Top countries by revenue
            top_countries = sorted(by_country.items(), key=lambda x: x[1]["revenue"], reverse=True)[
                :5
            ]
            top_performers["by_country"] = [
                {"country": country, "revenue": data["revenue"], "units": data["units"]}
                for country, data in top_countries
            ]

        return {
            "summary": summary,
            "by_app": by_app,
            "by_country": by_country,
            "by_date": by_date,
            "top_performers": top_performers,
        }

    def get_subscription_analysis(
        self,
        days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Get subscription-specific analysis for the specified period.

        Args:
            days: Number of days to analyze
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            Dictionary containing subscription metrics and analysis
        """
        # Fetch subscription data
        reports = self.api.fetch_multiple_days(days, start_date, end_date)

        # Combine subscription reports
        sub_df = combine_dataframes(reports.get("subscriptions", []), sort_by="report_date")
        event_df = combine_dataframes(reports.get("subscription_events", []), sort_by="report_date")

        analysis: Dict[str, Any] = {
            "subscription_summary": {},
            "event_summary": {},
            "by_app": {},
            "trends": {},
        }

        # Subscription summary
        if not sub_df.empty:
            analysis["subscription_summary"] = self._analyze_subscription_data(sub_df)

        # Event summary
        if not event_df.empty:
            analysis["event_summary"] = self._analyze_subscription_events(event_df)

        # Per-app analysis
        if not sub_df.empty and "App Apple ID" in sub_df.columns:
            app_groups = sub_df.groupby("App Apple ID")
            for app_id, group in app_groups:
                app_name = (
                    group["App Name"].iloc[0] if "App Name" in group.columns else f"App {app_id}"
                )
                analysis["by_app"][str(app_id)] = {
                    "name": app_name,
                    "active_subscriptions": (
                        int(group["Active Subscriptions"].sum())
                        if "Active Subscriptions" in group.columns
                        else 0
                    ),
                    "total_revenue": (
                        float(group["Proceeds"].sum()) if "Proceeds" in group.columns else 0.0
                    ),
                }

        return analysis

    def _analyze_subscription_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze subscription DataFrame and return metrics."""
        metrics: Dict[str, Any] = {}

        if "Active Subscriptions" in df.columns:
            metrics["total_active"] = int(df["Active Subscriptions"].sum())
            metrics["avg_active_per_day"] = float(df["Active Subscriptions"].mean())

        if "Proceeds" in df.columns:
            metrics["total_revenue"] = float(df["Proceeds"].sum())
            metrics["avg_revenue_per_day"] = float(df["Proceeds"].mean())

        if "Subscription Name" in df.columns:
            metrics["unique_products"] = df["Subscription Name"].nunique()

        return metrics

    def _analyze_subscription_events(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze subscription events DataFrame and return metrics."""
        metrics: Dict[str, Any] = {}

        if "Event" in df.columns:
            event_counts = df["Event"].value_counts()
            metrics["events"] = event_counts.to_dict()

            # Calculate common ratios
            if "Subscribe" in event_counts and "Cancel" in event_counts:
                metrics["cancellation_rate"] = float(
                    event_counts["Cancel"] / event_counts["Subscribe"]
                )  # type: ignore[assignment]

        if "Quantity" in df.columns:
            metrics["total_events"] = int(df["Quantity"].sum())  # type: ignore[assignment]

        return metrics

    def compare_periods(
        self, current_days: int = 30, comparison_days: int = 30, gap_days: int = 0
    ) -> Dict[str, Any]:
        """
        Compare two time periods for sales performance.

        Args:
            current_days: Number of days in current period
            comparison_days: Number of days in comparison period
            gap_days: Gap between periods (default 0 for consecutive periods)

        Returns:
            Dictionary containing comparison metrics
        """
        today = date.today() - timedelta(days=1)  # Yesterday

        # Current period
        current_end = today
        current_start = current_end - timedelta(days=current_days - 1)

        # Comparison period
        comparison_end = current_start - timedelta(days=gap_days + 1)
        comparison_start = comparison_end - timedelta(days=comparison_days - 1)

        # Fetch data for both periods
        current_summary = self.get_sales_summary(start_date=current_start, end_date=current_end)
        comparison_summary = self.get_sales_summary(
            start_date=comparison_start, end_date=comparison_end
        )

        # Calculate changes
        current_metrics = current_summary["summary"]
        comparison_metrics = comparison_summary["summary"]

        changes = {}
        for metric in ["total_units", "total_revenue", "unique_apps"]:
            current_val = current_metrics.get(metric, 0)
            comparison_val = comparison_metrics.get(metric, 0)

            if comparison_val > 0:
                change_pct = ((current_val - comparison_val) / comparison_val) * 100
            else:
                change_pct = 100.0 if current_val > 0 else 0.0

            changes[metric] = {
                "current": current_val,
                "previous": comparison_val,
                "change": current_val - comparison_val,
                "change_percent": change_pct,
            }

        return {
            "periods": {
                "current": {
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat(),
                },
                "comparison": {
                    "start": comparison_start.isoformat(),
                    "end": comparison_end.isoformat(),
                },
            },
            "changes": changes,
            "current_summary": current_summary,
            "comparison_summary": comparison_summary,
        }

    def get_app_performance_ranking(
        self, days: int = 30, metric: str = "revenue"
    ) -> List[Dict[str, Any]]:
        """
        Get apps ranked by performance metric.

        Args:
            days: Number of days to analyze
            metric: Metric to rank by ('revenue', 'units', 'countries')

        Returns:
            List of apps ranked by the specified metric
        """
        summary = self.get_sales_summary(days=days)
        by_app = summary.get("by_app", {})

        if not by_app:
            return []

        # Map metric names to dictionary keys
        metric_map = {"revenue": "revenue", "units": "units", "countries": "countries"}

        if metric not in metric_map:
            raise ValidationError(f"Invalid metric. Must be one of: {list(metric_map.keys())}")

        metric_key = metric_map[metric]

        # Sort apps by metric
        ranked_apps = sorted(by_app.items(), key=lambda x: x[1].get(metric_key, 0), reverse=True)

        # Format results
        results = []
        for rank, (app_id, data) in enumerate(ranked_apps, 1):
            results.append(
                {
                    "rank": rank,
                    "app_id": app_id,
                    "name": data["name"],
                    "value": data.get(metric_key, 0),
                    "revenue": data.get("revenue", 0),
                    "units": data.get("units", 0),
                    "countries": data.get("countries", 0),
                }
            )

        return results

    def export_summary_report(
        self, output_path: str, days: int = 30, include_details: bool = True
    ) -> None:
        """
        Export a comprehensive summary report to CSV.

        Args:
            output_path: Path to save the CSV file
            days: Number of days to analyze
            include_details: Whether to include detailed breakdowns
        """
        summary = self.get_sales_summary(days=days)

        # Create summary DataFrame
        summary_data = []

        # Overall metrics
        overall = summary["summary"]
        summary_data.append(
            {
                "Category": "Overall",
                "Metric": "Total Units",
                "Value": overall.get("total_units", 0),
                "Details": "",
            }
        )
        summary_data.append(
            {
                "Category": "Overall",
                "Metric": "Total Revenue",
                "Value": overall.get("total_revenue", 0),
                "Details": format_currency(overall.get("total_revenue", 0)),
            }
        )
        summary_data.append(
            {
                "Category": "Overall",
                "Metric": "Unique Apps",
                "Value": overall.get("unique_apps", 0),
                "Details": "",
            }
        )
        summary_data.append(
            {
                "Category": "Overall",
                "Metric": "Countries",
                "Value": overall.get("countries", 0),
                "Details": "",
            }
        )

        # Top performers
        if include_details:
            top_performers = summary.get("top_performers", {})

            # Top apps by revenue
            for i, app in enumerate(top_performers.get("by_revenue", [])[:3], 1):
                summary_data.append(
                    {
                        "Category": f"Top App #{i} (Revenue)",
                        "Metric": app["name"],
                        "Value": app["revenue"],
                        "Details": format_currency(app["revenue"]),
                    }
                )

            # Top countries
            for i, country in enumerate(top_performers.get("by_country", [])[:3], 1):
                summary_data.append(
                    {
                        "Category": f"Top Country #{i}",
                        "Metric": country["country"],
                        "Value": country["revenue"],
                        "Details": format_currency(country["revenue"]),
                    }
                )

        # Save to CSV
        df = pd.DataFrame(summary_data)
        df.to_csv(output_path, index=False)

    def _aggregate_by_app(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate sales data by app.

        Args:
            df: Sales DataFrame to aggregate

        Returns:
            DataFrame grouped by Apple Identifier with aggregated metrics
        """
        if df.empty or "Apple Identifier" not in df.columns:
            return pd.DataFrame()

        # Group by app and aggregate
        aggregated = (
            df.groupby("Apple Identifier")
            .agg(
                {
                    "Units": "sum",
                    "Developer Proceeds": (
                        "sum" if "Developer Proceeds" in df.columns else lambda x: 0
                    ),
                    "Title": "first" if "Title" in df.columns else lambda x: "",
                }
            )
            .reset_index()
        )

        return aggregated

    def _aggregate_by_country(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate sales data by country.

        Args:
            df: Sales DataFrame to aggregate

        Returns:
            DataFrame grouped by Country Code with aggregated metrics
        """
        if df.empty or "Country Code" not in df.columns:
            return pd.DataFrame()

        # Group by country and aggregate
        aggregated = (
            df.groupby("Country Code")
            .agg(
                {
                    "Units": "sum",
                    "Developer Proceeds": (
                        "sum" if "Developer Proceeds" in df.columns else lambda x: 0
                    ),
                }
            )
            .reset_index()
        )

        return aggregated

    def _aggregate_by_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate sales data by date.

        Args:
            df: Sales DataFrame to aggregate

        Returns:
            DataFrame grouped by report_date with aggregated metrics
        """
        if df.empty or "report_date" not in df.columns:
            return pd.DataFrame()

        # Group by date and aggregate
        aggregated = (
            df.groupby("report_date")
            .agg(
                {
                    "Units": "sum",
                    "Developer Proceeds": (
                        "sum" if "Developer Proceeds" in df.columns else lambda x: 0
                    ),
                }
            )
            .reset_index()
        )

        return aggregated


def create_report_processor(
    key_id: str,
    issuer_id: str,
    private_key_path: str,
    vendor_number: str,
    app_ids: Optional[List[str]] = None,
) -> ReportProcessor:
    """
    Convenience function to create a ReportProcessor with API client.

    Args:
        key_id: App Store Connect API key ID
        issuer_id: App Store Connect API issuer ID
        private_key_path: Path to private key file
        vendor_number: Vendor number
        app_ids: Optional list of app IDs to filter

    Returns:
        Configured ReportProcessor instance
    """
    api = AppStoreConnectAPI(
        key_id=key_id,
        issuer_id=issuer_id,
        private_key_path=private_key_path,
        vendor_number=vendor_number,
        app_ids=app_ids,
    )

    return ReportProcessor(api)
