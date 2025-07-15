"""
appstore-connect-client

A comprehensive Python client for the Apple App Store Connect API,
supporting both sales reporting and metadata management.
"""

from .client import AppStoreConnectAPI
from .exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
)

__version__ = "0.1.0"
__author__ = "Chris Bick"
__email__ = "chris@bickster.com"

__all__ = [
    "AppStoreConnectAPI",
    "AppStoreConnectError",
    "AuthenticationError", 
    "RateLimitError",
    "ValidationError",
]