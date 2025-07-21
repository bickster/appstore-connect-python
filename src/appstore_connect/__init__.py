"""
appstore-connect-client

A comprehensive Python client for the Apple App Store Connect API,
supporting both sales reporting and metadata management.
"""

from .client import AppStoreConnectAPI
from .reports import ReportProcessor, create_report_processor
from .metadata import MetadataManager, create_metadata_manager
from .exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    NotFoundError,
    PermissionError,
)
from . import utils

__version__ = "1.0.5"
__author__ = "Chris Bick"
__email__ = "chris@bickster.com"

__all__ = [
    "AppStoreConnectAPI",
    "ReportProcessor",
    "MetadataManager",
    "create_report_processor",
    "create_metadata_manager",
    "AppStoreConnectError",
    "AuthenticationError",
    "RateLimitError",
    "ValidationError",
    "NotFoundError",
    "PermissionError",
    "utils",
]
