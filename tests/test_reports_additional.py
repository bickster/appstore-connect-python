"""
Additional tests for reports.py to achieve 100% coverage.
"""

import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import Mock, patch

from appstore_connect.reports import ReportProcessor
from appstore_connect.exceptions import ValidationError


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    api = Mock()
    return api


@pytest.fixture
def report_processor(mock_api):
    """Create a ReportProcessor with mock API."""
    return ReportProcessor(mock_api)


class TestReportProcessorEdgeCases:
    """Test edge cases in ReportProcessor."""
    
    def test_get_sales_summary_with_subscription_events(self, report_processor, mock_api):
        """Test sales summary including subscription event data."""
        # Mock fetch_multiple_days to return all report types
        mock_api.fetch_multiple_days.return_value = {
            'sales': [
                pd.DataFrame({
                    'Apple Identifier': ['123', '456'],
                    'Units': [10, 20],
                    'Developer Proceeds': [70.0, 140.0],
                    'Product Type Identifier': ['1', '1']
                })
            ],
            'subscriptions': [
                pd.DataFrame({
                    'App Apple ID': ['123'],
                    'Active Subscriptions': [100],
                    'New Subscriptions': [10],
                    'Proceeds': [1000.0]
                })
            ],
            'subscription_events': [
                pd.DataFrame({
                    'Event': ['Subscribe', 'Cancel', 'Renew'],
                    'App Apple ID': ['123', '123', '456'],
                    'Quantity': [5, 2, 10]
                })
            ]
        }
        
        summary = report_processor.get_sales_summary(days=7)
        
        # Check that subscription events are included
        assert 'subscription_events' in summary
        assert 'by_event' in summary['subscription_events']
        
        # Verify event counts
        by_event = summary['subscription_events']['by_event']
        assert by_event['Subscribe'] == 5
        assert by_event['Cancel'] == 2
        assert by_event['Renew'] == 10
    
    def test_get_subscription_analysis_all_reports_present(self, report_processor, mock_api):
        """Test subscription analysis with both reports available."""
        # Mock data with matching app IDs
        subscriptions_df = pd.DataFrame({
            'App Apple ID': ['123', '456'],
            'App Name': ['App One', 'App Two'],
            'Active Subscriptions': [100, 200],
            'New Subscriptions': [10, 20],
            'Cancelled Subscriptions': [5, 10],
            'Proceeds': [1000.0, 2000.0]
        })
        
        events_df = pd.DataFrame({
            'Event': ['Subscribe', 'Cancel', 'Subscribe', 'Renew'],
            'App Apple ID': ['123', '123', '456', '456'],
            'Quantity': [10, 5, 20, 50]
        })
        
        mock_api.fetch_multiple_days.return_value = {
            'subscriptions': [subscriptions_df],
            'subscription_events': [events_df]
        }
        
        analysis = report_processor.get_subscription_analysis(days=7)
        
        # Verify merged data
        assert len(analysis['by_app']) == 2
        
        # Check App One metrics
        app_one = analysis['by_app'][analysis['by_app']['App Apple ID'] == '123'].iloc[0]
        assert app_one['subscribe_events'] == 10
        assert app_one['cancel_events'] == 5
        assert app_one['renew_events'] == 0  # No renew events for this app
        
        # Check App Two metrics  
        app_two = analysis['by_app'][analysis['by_app']['App Apple ID'] == '456'].iloc[0]
        assert app_two['subscribe_events'] == 20
        assert app_two['cancel_events'] == 0  # No cancel events for this app
        assert app_two['renew_events'] == 50
    
    def test_compare_periods_with_growth_metrics(self, report_processor, mock_api):
        """Test period comparison with calculated growth metrics."""
        # Current period data
        current_sales = pd.DataFrame({
            'Apple Identifier': ['123'],
            'Units': [100],
            'Developer Proceeds': [700.0]
        })
        
        # Previous period data (lower values)
        previous_sales = pd.DataFrame({
            'Apple Identifier': ['123'],
            'Units': [80],
            'Developer Proceeds': [560.0]
        })
        
        # Mock the two fetch calls
        mock_api.fetch_multiple_days.side_effect = [
            {'sales': [current_sales], 'subscriptions': [], 'subscription_events': []},
            {'sales': [previous_sales], 'subscriptions': [], 'subscription_events': []}
        ]
        
        comparison = report_processor.compare_periods(
            current_days=7,
            comparison_days=7
        )
        
        # Verify growth calculations
        assert 'changes' in comparison
        changes = comparison['changes']
        
        # Units growth: (100 - 80) / 80 * 100 = 25%
        assert changes['units_change'] == 25.0
        
        # Revenue growth: (700 - 560) / 560 * 100 = 25%  
        assert changes['revenue_change'] == 25.0
    
    def test_get_app_performance_ranking_invalid_period(self, report_processor, mock_api):
        """Test app performance ranking with period <= 0."""
        with pytest.raises(ValidationError) as exc_info:
            report_processor.get_app_performance_ranking(days=0)
        
        assert "Period must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError):
            report_processor.get_app_performance_ranking(days=-5)
    
    def test_export_summary_report_with_all_sections(self, report_processor, mock_api, tmp_path):
        """Test exporting comprehensive summary report."""
        # Mock complete data
        sales_df = pd.DataFrame({
            'Apple Identifier': ['123', '456'],
            'Title': ['App One', 'App Two'],
            'Units': [50, 100],
            'Developer Proceeds': [350.0, 700.0],
            'report_date': [date.today(), date.today()]
        })
        
        subscriptions_df = pd.DataFrame({
            'App Apple ID': ['123'],
            'App Name': ['App One'],
            'Active Subscriptions': [500],
            'Proceeds': [5000.0]
        })
        
        events_df = pd.DataFrame({
            'Event': ['Subscribe', 'Renew'],
            'App Apple ID': ['123', '123'],
            'Quantity': [50, 200]
        })
        
        mock_api.fetch_multiple_days.return_value = {
            'sales': [sales_df],
            'subscriptions': [subscriptions_df],
            'subscription_events': [events_df]
        }
        
        # Test both CSV and Excel formats
        for format_type in ['csv', 'excel']:
            output_file = tmp_path / f"summary.{format_type}"
            
            result = report_processor.export_summary_report(
                str(output_file),
                days=30,
                format=format_type
            )
            
            assert result is True
            assert output_file.exists()
            
            # For Excel, check multiple sheets were created
            if format_type == 'excel':
                df_check = pd.read_excel(output_file, sheet_name=None)
                assert 'Summary' in df_check
                assert 'By App' in df_check
                assert 'By Country' in df_check
                assert 'By Date' in df_check
    
    def test_internal_aggregation_methods(self, report_processor):
        """Test internal aggregation helper methods."""
        # Test _aggregate_by_app
        sales_df = pd.DataFrame({
            'Apple Identifier': ['123', '123', '456'],
            'Title': ['App One', 'App One', 'App Two'],
            'Units': [10, 20, 30],
            'Developer Proceeds': [70.0, 140.0, 210.0]
        })
        
        aggregated = report_processor._aggregate_by_app(sales_df)
        
        assert len(aggregated) == 2
        assert aggregated[aggregated['Apple Identifier'] == '123']['Units'].iloc[0] == 30
        assert aggregated[aggregated['Apple Identifier'] == '123']['Developer Proceeds'].iloc[0] == 210.0
        
        # Test _aggregate_by_country
        sales_df['Country Code'] = ['US', 'US', 'GB']
        by_country = report_processor._aggregate_by_country(sales_df)
        
        assert len(by_country) == 2
        assert by_country[by_country['Country Code'] == 'US']['Units'].iloc[0] == 30
        
        # Test _aggregate_by_date
        sales_df['report_date'] = [date.today(), date.today(), date.today() - timedelta(days=1)]
        by_date = report_processor._aggregate_by_date(sales_df)
        
        assert len(by_date) == 2