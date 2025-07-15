"""
Tests for report processing functionality.
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import date, timedelta

from appstore_connect.reports import ReportProcessor, create_report_processor
from appstore_connect.client import AppStoreConnectAPI


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    api = Mock(spec=AppStoreConnectAPI)
    return api


@pytest.fixture
def report_processor(mock_api):
    """Create a ReportProcessor with mock API."""
    return ReportProcessor(mock_api)


@pytest.fixture
def sample_sales_df():
    """Create sample sales DataFrame."""
    return pd.DataFrame({
        'Apple Identifier': ['123', '456', '123', '456'],
        'Title': ['App A', 'App B', 'App A', 'App B'],
        'Units': [10, 20, 15, 25],
        'Developer Proceeds': [1.0, 2.0, 1.5, 2.5],
        'Country Code': ['US', 'US', 'CA', 'CA'],
        'report_date': [date(2023, 1, 1), date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 2)]
    })


@pytest.fixture
def sample_subscription_df():
    """Create sample subscription DataFrame."""
    return pd.DataFrame({
        'App Apple ID': ['123', '456'],
        'App Name': ['App A', 'App B'],
        'Active Subscriptions': [100, 200],
        'Proceeds': [50.0, 100.0],
        'Subscription Name': ['Premium', 'Pro']
    })


@pytest.fixture
def sample_events_df():
    """Create sample subscription events DataFrame."""
    return pd.DataFrame({
        'Event': ['Subscribe', 'Cancel', 'Subscribe', 'Renew'],
        'Quantity': [1, 1, 1, 1],
        'App Apple ID': ['123', '123', '456', '456']
    })


class TestReportProcessor:
    """Test ReportProcessor functionality."""
    
    def test_get_sales_summary_empty_data(self, report_processor, mock_api):
        """Test sales summary with empty data."""
        mock_api.fetch_multiple_days.return_value = {'sales': []}
        
        result = report_processor.get_sales_summary(days=30)
        
        assert result['summary']['total_units'] == 0
        assert result['summary']['total_revenue'] == 0.0
        assert result['by_app'] == {}
        assert result['by_country'] == {}
    
    def test_get_sales_summary_with_data(self, report_processor, mock_api, sample_sales_df):
        """Test sales summary with actual data."""
        mock_api.fetch_multiple_days.return_value = {'sales': [sample_sales_df]}
        
        result = report_processor.get_sales_summary(days=30)
        
        # Check overall summary
        assert result['summary']['total_units'] == 70  # 10+20+15+25
        assert result['summary']['total_revenue'] == 7.0  # 1.0+2.0+1.5+2.5
        assert result['summary']['unique_apps'] == 2
        assert result['summary']['countries'] == 2
        
        # Check by_app breakdown
        assert '123' in result['by_app']
        assert result['by_app']['123']['name'] == 'App A'
        assert result['by_app']['123']['units'] == 25  # 10+15
        assert result['by_app']['123']['revenue'] == 2.5  # 1.0+1.5
        
        # Check by_country breakdown
        assert 'US' in result['by_country']
        assert result['by_country']['US']['units'] == 30  # 10+20
        assert result['by_country']['US']['revenue'] == 3.0  # 1.0+2.0
        
        # Check by_date breakdown
        assert '2023-01-01' in result['by_date']
        assert result['by_date']['2023-01-01']['units'] == 30  # 10+20
        
        # Check top performers
        assert 'by_revenue' in result['top_performers']
        assert 'by_units' in result['top_performers']
        assert 'by_country' in result['top_performers']
    
    def test_get_subscription_analysis_empty(self, report_processor, mock_api):
        """Test subscription analysis with empty data."""
        mock_api.fetch_multiple_days.return_value = {
            'subscriptions': [],
            'subscription_events': []
        }
        
        result = report_processor.get_subscription_analysis(days=30)
        
        assert result['subscription_summary'] == {}
        assert result['event_summary'] == {}
        assert result['by_app'] == {}
    
    def test_get_subscription_analysis_with_data(self, report_processor, mock_api, sample_subscription_df, sample_events_df):
        """Test subscription analysis with data."""
        mock_api.fetch_multiple_days.return_value = {
            'subscriptions': [sample_subscription_df],
            'subscription_events': [sample_events_df]
        }
        
        result = report_processor.get_subscription_analysis(days=30)
        
        # Check subscription summary
        sub_summary = result['subscription_summary']
        assert sub_summary['total_active'] == 300  # 100+200
        assert sub_summary['total_revenue'] == 150.0  # 50+100
        assert sub_summary['unique_products'] == 2
        
        # Check event summary
        event_summary = result['event_summary']
        assert 'events' in event_summary
        assert event_summary['events']['Subscribe'] == 2
        assert event_summary['events']['Cancel'] == 1
        assert event_summary['cancellation_rate'] == 0.5  # 1/2
        
        # Check by_app breakdown
        assert '123' in result['by_app']
        assert result['by_app']['123']['name'] == 'App A'
        assert result['by_app']['123']['active_subscriptions'] == 100
    
    def test_compare_periods(self, report_processor):
        """Test period comparison."""
        # Mock get_sales_summary to return different data for different periods
        def mock_get_sales_summary(start_date=None, end_date=None, **kwargs):
            if start_date and start_date.month == 1:  # Current period
                return {
                    'summary': {'total_units': 100, 'total_revenue': 50.0, 'unique_apps': 2}
                }
            else:  # Comparison period
                return {
                    'summary': {'total_units': 80, 'total_revenue': 40.0, 'unique_apps': 2}
                }
        
        with patch.object(report_processor, 'get_sales_summary', side_effect=mock_get_sales_summary):
            result = report_processor.compare_periods(current_days=30, comparison_days=30)
        
        # Check that periods are defined
        assert 'current' in result['periods']
        assert 'comparison' in result['periods']
        
        # Check changes
        changes = result['changes']
        assert changes['total_units']['current'] == 100
        assert changes['total_units']['previous'] == 80
        assert changes['total_units']['change'] == 20
        assert changes['total_units']['change_percent'] == 25.0  # (100-80)/80 * 100
        
        assert changes['total_revenue']['change_percent'] == 25.0  # (50-40)/40 * 100
    
    def test_get_app_performance_ranking(self, report_processor):
        """Test app performance ranking."""
        mock_summary = {
            'by_app': {
                '123': {'name': 'App A', 'revenue': 100.0, 'units': 50, 'countries': 3},
                '456': {'name': 'App B', 'revenue': 200.0, 'units': 75, 'countries': 5},
                '789': {'name': 'App C', 'revenue': 150.0, 'units': 100, 'countries': 2}
            }
        }
        
        with patch.object(report_processor, 'get_sales_summary', return_value=mock_summary):
            # Test ranking by revenue
            result = report_processor.get_app_performance_ranking(days=30, metric='revenue')
        
        assert len(result) == 3
        assert result[0]['rank'] == 1
        assert result[0]['app_id'] == '456'  # Highest revenue
        assert result[0]['name'] == 'App B'
        assert result[0]['value'] == 200.0
        
        assert result[1]['rank'] == 2
        assert result[1]['app_id'] == '789'  # Second highest revenue
        
        assert result[2]['rank'] == 3
        assert result[2]['app_id'] == '123'  # Lowest revenue
    
    def test_get_app_performance_ranking_by_units(self, report_processor):
        """Test app performance ranking by units."""
        mock_summary = {
            'by_app': {
                '123': {'name': 'App A', 'revenue': 100.0, 'units': 50, 'countries': 3},
                '456': {'name': 'App B', 'revenue': 200.0, 'units': 75, 'countries': 5},
                '789': {'name': 'App C', 'revenue': 150.0, 'units': 100, 'countries': 2}
            }
        }
        
        with patch.object(report_processor, 'get_sales_summary', return_value=mock_summary):
            result = report_processor.get_app_performance_ranking(days=30, metric='units')
        
        assert result[0]['app_id'] == '789'  # Highest units (100)
        assert result[1]['app_id'] == '456'  # Second highest units (75)
        assert result[2]['app_id'] == '123'  # Lowest units (50)
    
    def test_get_app_performance_ranking_invalid_metric(self, report_processor):
        """Test ranking with invalid metric."""
        from appstore_connect.exceptions import ValidationError
        
        with patch.object(report_processor, 'get_sales_summary', return_value={'by_app': {}}):
            with pytest.raises(ValidationError):
                report_processor.get_app_performance_ranking(days=30, metric='invalid')
    
    @patch('pandas.DataFrame.to_csv')
    def test_export_summary_report(self, mock_to_csv, report_processor):
        """Test exporting summary report."""
        mock_summary = {
            'summary': {
                'total_units': 100,
                'total_revenue': 50.0,
                'unique_apps': 2,
                'countries': 3
            },
            'top_performers': {
                'by_revenue': [
                    {'name': 'App A', 'revenue': 30.0},
                    {'name': 'App B', 'revenue': 20.0}
                ],
                'by_country': [
                    {'country': 'US', 'revenue': 40.0},
                    {'country': 'CA', 'revenue': 10.0}
                ]
            }
        }
        
        with patch.object(report_processor, 'get_sales_summary', return_value=mock_summary):
            report_processor.export_summary_report(
                output_path='/tmp/test.csv',
                days=30,
                include_details=True
            )
        
        # Verify CSV export was called
        mock_to_csv.assert_called_once_with('/tmp/test.csv', index=False)


class TestCreateReportProcessor:
    """Test convenience function for creating ReportProcessor."""
    
    @patch('appstore_connect.reports.AppStoreConnectAPI')
    def test_create_report_processor(self, mock_api_class):
        """Test creating ReportProcessor with convenience function."""
        mock_api_instance = Mock()
        mock_api_class.return_value = mock_api_instance
        
        processor = create_report_processor(
            key_id='test_key',
            issuer_id='test_issuer',
            private_key_path='/tmp/key.p8',
            vendor_number='12345',
            app_ids=['123', '456']
        )
        
        # Verify API was initialized correctly
        mock_api_class.assert_called_once_with(
            key_id='test_key',
            issuer_id='test_issuer',
            private_key_path='/tmp/key.p8',
            vendor_number='12345',
            app_ids=['123', '456']
        )
        
        # Verify processor was created with the API
        assert isinstance(processor, ReportProcessor)
        assert processor.api == mock_api_instance