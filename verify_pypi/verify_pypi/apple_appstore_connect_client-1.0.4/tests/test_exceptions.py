"""
Tests for custom exceptions in appstore-connect-client.
"""

import pytest
from appstore_connect.exceptions import (
    AppStoreConnectError,
    AuthenticationError,
    ValidationError,
    NotFoundError,
    PermissionError,
    RateLimitError,
    ServerError,
)


class TestExceptionHierarchy:
    """Test exception class hierarchy and inheritance."""

    def test_base_exception(self):
        """Test base AppStoreConnectError."""
        exc = AppStoreConnectError("Test error")
        assert str(exc) == "Test error"
        assert isinstance(exc, Exception)

    def test_authentication_error(self):
        """Test AuthenticationError inherits from base."""
        exc = AuthenticationError("Auth failed")
        assert str(exc) == "Auth failed"
        assert isinstance(exc, AppStoreConnectError)

    def test_validation_error(self):
        """Test ValidationError inherits from base."""
        exc = ValidationError("Invalid input")
        assert str(exc) == "Invalid input"
        assert isinstance(exc, AppStoreConnectError)

    def test_not_found_error(self):
        """Test NotFoundError inherits from base."""
        exc = NotFoundError("Resource not found")
        assert str(exc) == "Resource not found"
        assert isinstance(exc, AppStoreConnectError)

    def test_permission_error(self):
        """Test PermissionError inherits from base."""
        exc = PermissionError("Access denied")
        assert str(exc) == "Access denied"
        assert isinstance(exc, AppStoreConnectError)

    def test_rate_limit_error(self):
        """Test RateLimitError inherits from base."""
        exc = RateLimitError("Rate limit exceeded")
        assert str(exc) == "Rate limit exceeded"
        assert isinstance(exc, AppStoreConnectError)

    def test_server_error(self):
        """Test ServerError inherits from base."""
        exc = ServerError("Internal server error")
        assert str(exc) == "Internal server error"
        assert isinstance(exc, AppStoreConnectError)


class TestExceptionUsage:
    """Test exception usage patterns."""

    def test_raise_authentication_error(self):
        """Test raising AuthenticationError."""
        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Invalid API key")

        assert "Invalid API key" in str(exc_info.value)

    def test_raise_validation_error_with_details(self):
        """Test raising ValidationError with detailed message."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("App ID must be 9-10 digits, got: ABC123")

        assert "App ID must be 9-10 digits" in str(exc_info.value)
        assert "ABC123" in str(exc_info.value)

    def test_catch_specific_exception(self):
        """Test catching specific exception types."""
        try:
            raise NotFoundError("App 123456789 not found")
        except NotFoundError as e:
            assert "123456789" in str(e)
        except AppStoreConnectError:
            pytest.fail("Should catch NotFoundError specifically")

    def test_catch_base_exception(self):
        """Test catching base exception for any API error."""
        errors = [
            AuthenticationError("Auth error"),
            ValidationError("Validation error"),
            NotFoundError("Not found error"),
            PermissionError("Permission error"),
            RateLimitError("Rate limit error"),
            ServerError("Server error"),
        ]

        for error in errors:
            try:
                raise error
            except AppStoreConnectError as e:
                assert str(error) == str(e)
            else:
                pytest.fail(f"Failed to catch {type(error).__name__}")


class TestExceptionMessages:
    """Test exception message formatting."""

    def test_simple_message(self):
        """Test simple error message."""
        exc = AppStoreConnectError("Simple error message")
        assert str(exc) == "Simple error message"

    def test_formatted_message(self):
        """Test formatted error message."""
        app_id = "123456789"
        exc = NotFoundError(f"App {app_id} not found in account")
        assert "123456789" in str(exc)
        assert "not found" in str(exc).lower()

    def test_multiline_message(self):
        """Test multiline error message."""
        message = """Invalid request:
        - Missing required field: app_id
        - Invalid date format: use YYYY-MM-DD"""

        exc = ValidationError(message)
        assert "Missing required field" in str(exc)
        assert "Invalid date format" in str(exc)

    def test_empty_message(self):
        """Test exception with empty message."""
        exc = AppStoreConnectError("")
        assert str(exc) == ""

    def test_none_message(self):
        """Test exception with None message."""
        # This should work without error
        exc = AppStoreConnectError(None)
        assert str(exc) == "None"


class TestExceptionContext:
    """Test exceptions with additional context."""

    def test_authentication_context(self):
        """Test authentication error with context."""
        exc = AuthenticationError(
            "Authentication failed: Invalid private key format. "
            "Ensure your private key is in PEM format."
        )
        assert "Invalid private key format" in str(exc)
        assert "PEM format" in str(exc)

    def test_rate_limit_context(self):
        """Test rate limit error with retry information."""
        exc = RateLimitError("Rate limit exceeded (50 requests/hour). " "Retry after 3600 seconds.")
        assert "50 requests/hour" in str(exc)
        assert "3600 seconds" in str(exc)

    def test_validation_context(self):
        """Test validation error with field details."""
        exc = ValidationError(
            "Invalid app metadata: "
            "name too long (max 30 chars), "
            "keywords contain prohibited terms"
        )
        assert "name too long" in str(exc)
        assert "max 30 chars" in str(exc)
        assert "prohibited terms" in str(exc)


class TestExceptionChaining:
    """Test exception chaining and cause."""

    def test_exception_chaining(self):
        """Test raising exception from another exception."""
        try:
            try:
                # Simulate original error
                1 / 0
            except ZeroDivisionError as e:
                # Wrap in custom exception
                raise ServerError("Failed to process request") from e
        except ServerError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ZeroDivisionError)

    def test_preserve_traceback(self):
        """Test that traceback is preserved when re-raising."""

        def inner_function():
            raise ValidationError("Inner error")

        def outer_function():
            try:
                inner_function()
            except ValidationError:
                raise  # Re-raise preserves traceback

        with pytest.raises(ValidationError) as exc_info:
            outer_function()

        # Check that traceback includes both functions
        import traceback

        tb_str = "".join(traceback.format_tb(exc_info.tb))
        assert "inner_function" in tb_str
        assert "outer_function" in tb_str


class TestExceptionComparison:
    """Test exception comparison and equality."""

    def test_same_type_same_message(self):
        """Test exceptions with same type and message."""
        exc1 = ValidationError("Same message")
        exc2 = ValidationError("Same message")

        # They are different instances
        assert exc1 is not exc2
        # But have same string representation
        assert str(exc1) == str(exc2)

    def test_different_types(self):
        """Test different exception types."""
        exc1 = ValidationError("Error")
        exc2 = AuthenticationError("Error")

        assert type(exc1) is not type(exc2)
        assert not isinstance(exc1, AuthenticationError)
        assert not isinstance(exc2, ValidationError)

    def test_isinstance_checks(self):
        """Test isinstance with exception hierarchy."""
        exc = RateLimitError("Too many requests")

        assert isinstance(exc, RateLimitError)
        assert isinstance(exc, AppStoreConnectError)
        assert isinstance(exc, Exception)
        assert not isinstance(exc, ValidationError)
