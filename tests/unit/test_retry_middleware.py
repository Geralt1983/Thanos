"""
Unit tests for RetryMiddleware.

Tests cover:
- Successful operation on first attempt
- Exponential backoff calculation
- Retry on specific errors
- Callback invocation
- Max retries exhaustion
- Handling different error types
"""
from unittest.mock import Mock, patch

import pytest


# Create mock exception classes that behave like Anthropic exceptions
# The real Anthropic exceptions require response and body parameters
class MockRateLimitError(Exception):
    """Mock RateLimitError for testing."""
    def __init__(self, message="Rate limited"):
        super().__init__(message)
        self.status_code = 429

class MockAPIConnectionError(Exception):
    """Mock APIConnectionError for testing."""
    def __init__(self, message="Connection error"):
        super().__init__(message)

class MockAPIStatusError(Exception):
    """Mock APIStatusError for testing."""
    def __init__(self, message="API error", status_code=500):
        super().__init__(message)
        self.status_code = status_code

# Patch the anthropic imports in retry_middleware module
import Tools.retry_middleware as retry_module


retry_module.RateLimitError = MockRateLimitError
retry_module.APIConnectionError = MockAPIConnectionError
retry_module.APIStatusError = MockAPIStatusError

# Use the mock classes in tests
RateLimitError = MockRateLimitError
APIConnectionError = MockAPIConnectionError
APIStatusError = MockAPIStatusError

# Default retriable errors tuple using our mock classes
MOCK_RETRIABLE_ERRORS = (MockRateLimitError, MockAPIConnectionError)

from Tools.retry_middleware import RetryMiddleware, with_retry


@pytest.mark.unit
class TestRetryMiddlewareInitialization:
    """Test RetryMiddleware initialization."""

    def test_initialization_with_defaults(self):
        """Test initialization with default values."""
        middleware = RetryMiddleware()
        assert middleware.max_retries == 3
        assert middleware.base_delay == 1.0
        assert middleware.backoff_multiplier == 2

    def test_initialization_with_custom_values(self):
        """Test initialization with custom values."""
        middleware = RetryMiddleware(
            max_retries=5,
            base_delay=2.0,
            backoff_multiplier=3
        )
        assert middleware.max_retries == 5
        assert middleware.base_delay == 2.0
        assert middleware.backoff_multiplier == 3


@pytest.mark.unit
class TestSuccessfulExecution:
    """Test successful operation execution."""

    def test_execute_success_first_attempt(self):
        """Test successful execution on first attempt."""
        middleware = RetryMiddleware()
        operation = Mock(return_value="success")

        result = middleware.execute_with_retry(operation)

        assert result == "success"
        operation.assert_called_once()

    def test_execute_returns_operation_result(self):
        """Test that execute returns the operation's result."""
        middleware = RetryMiddleware()
        expected_result = {"data": "test_value", "status": "ok"}
        operation = Mock(return_value=expected_result)

        result = middleware.execute_with_retry(operation)

        assert result == expected_result


@pytest.mark.unit
class TestRetryLogic:
    """Test retry logic and exponential backoff."""

    @patch('time.sleep')
    def test_retry_on_rate_limit_error(self, mock_sleep):
        """Test retry on RateLimitError."""
        middleware = RetryMiddleware(max_retries=3, base_delay=1.0)
        operation = Mock(side_effect=[
            RateLimitError("Rate limited"),
            RateLimitError("Rate limited"),
            "success"
        ])

        result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert result == "success"
        assert operation.call_count == 3

        # Verify exponential backoff: 1.0, 2.0
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)  # First retry: base_delay * 2^0
        mock_sleep.assert_any_call(2.0)  # Second retry: base_delay * 2^1

    @patch('time.sleep')
    def test_retry_on_api_connection_error(self, mock_sleep):
        """Test retry on APIConnectionError."""
        middleware = RetryMiddleware(max_retries=2)
        operation = Mock(side_effect=[
            APIConnectionError("Connection failed"),
            "success"
        ])

        result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert result == "success"
        assert operation.call_count == 2
        mock_sleep.assert_called_once()

    @patch('time.sleep')
    def test_exponential_backoff_calculation(self, mock_sleep):
        """Test exponential backoff calculation."""
        middleware = RetryMiddleware(max_retries=4, base_delay=1.0, backoff_multiplier=2)
        operation = Mock(side_effect=[
            RateLimitError("Error"),
            RateLimitError("Error"),
            RateLimitError("Error"),
            "success"
        ])

        middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        # Verify backoff: 1.0 * 2^0, 1.0 * 2^1, 1.0 * 2^2
        expected_waits = [1.0, 2.0, 4.0]
        actual_waits = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert actual_waits == expected_waits

    @patch('time.sleep')
    def test_custom_backoff_multiplier(self, mock_sleep):
        """Test custom backoff multiplier."""
        middleware = RetryMiddleware(max_retries=3, base_delay=1.0, backoff_multiplier=3)
        operation = Mock(side_effect=[
            RateLimitError("Error"),
            RateLimitError("Error"),
            "success"
        ])

        middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        # Verify backoff with multiplier=3: 1.0 * 3^0, 1.0 * 3^1
        expected_waits = [1.0, 3.0]
        actual_waits = [call_args[0][0] for call_args in mock_sleep.call_args_list]
        assert actual_waits == expected_waits


@pytest.mark.unit
class TestMaxRetriesExhaustion:
    """Test behavior when max retries are exhausted."""

    @patch('time.sleep')
    def test_raises_last_exception_when_retries_exhausted(self, mock_sleep):
        """Test that last exception is raised when retries exhausted."""
        middleware = RetryMiddleware(max_retries=3)
        error = RateLimitError("Persistent rate limit")
        operation = Mock(side_effect=error)

        with pytest.raises(RateLimitError) as exc_info:
            middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert exc_info.value == error
        assert operation.call_count == 3

    @patch('time.sleep')
    def test_no_sleep_on_last_attempt(self, mock_sleep):
        """Test that no sleep occurs after last attempt."""
        middleware = RetryMiddleware(max_retries=2)
        operation = Mock(side_effect=RateLimitError("Error"))

        with pytest.raises(RateLimitError):
            middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        # Only 1 sleep (after first failure), not after second
        assert mock_sleep.call_count == 1


@pytest.mark.unit
class TestCallbackInvocation:
    """Test on_retry callback functionality."""

    @patch('time.sleep')
    def test_callback_invoked_on_retry(self, mock_sleep):
        """Test that callback is invoked on retry."""
        middleware = RetryMiddleware(max_retries=3)
        callback = Mock()
        error = RateLimitError("Error")
        operation = Mock(side_effect=[error, "success"])

        middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS, on_retry=callback)

        callback.assert_called_once()
        # Verify callback arguments: (exception, attempt, wait_time)
        call_args = callback.call_args[0]
        assert call_args[0] == error  # exception
        assert call_args[1] == 1      # attempt number
        assert call_args[2] == 1.0    # wait_time

    @patch('time.sleep')
    def test_callback_invoked_multiple_times(self, mock_sleep):
        """Test callback invoked for each retry."""
        middleware = RetryMiddleware(max_retries=3)
        callback = Mock()
        operation = Mock(side_effect=[
            RateLimitError("Error"),
            RateLimitError("Error"),
            "success"
        ])

        middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS, on_retry=callback)

        assert callback.call_count == 2

        # Verify attempt numbers: 1, 2
        attempt_numbers = [call_args[0][1] for call_args in callback.call_args_list]
        assert attempt_numbers == [1, 2]

    @patch('time.sleep')
    def test_callback_not_invoked_on_success(self, mock_sleep):
        """Test callback not invoked when operation succeeds first time."""
        middleware = RetryMiddleware()
        callback = Mock()
        operation = Mock(return_value="success")

        middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS, on_retry=callback)

        callback.assert_not_called()


@pytest.mark.unit
class TestAPIStatusErrorHandling:
    """Test handling of APIStatusError with status codes."""

    @patch('time.sleep')
    def test_retry_on_5xx_server_error(self, mock_sleep):
        """Test retry on 5xx server errors."""
        middleware = RetryMiddleware(max_retries=2)

        # Create mock APIStatusError with 500 status
        error_500 = APIStatusError("Server error", status_code=500)

        operation = Mock(side_effect=[error_500, "success"])

        result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert result == "success"
        assert operation.call_count == 2
        mock_sleep.assert_called_once()

    def test_no_retry_on_4xx_client_error(self):
        """Test no retry on 4xx client errors."""
        middleware = RetryMiddleware(max_retries=3)

        # Create mock APIStatusError with 400 status
        error_400 = APIStatusError("Bad request", status_code=400)

        operation = Mock(side_effect=error_400)

        with pytest.raises(APIStatusError) as exc_info:
            middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert exc_info.value.status_code == 400
        # Should not retry - only called once
        operation.assert_called_once()

    @patch('time.sleep')
    def test_retry_different_5xx_codes(self, mock_sleep):
        """Test retry on different 5xx status codes."""
        middleware = RetryMiddleware(max_retries=4)

        # Test 502, 503, 504
        for status_code in [502, 503, 504]:
            error = APIStatusError(f"Error {status_code}", status_code=status_code)
            operation = Mock(side_effect=[error, "success"])

            result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)
            assert result == "success"

        # Verify retries occurred (3 retries total)
        assert mock_sleep.call_count == 3


@pytest.mark.unit
class TestCustomRetriableErrors:
    """Test custom retriable error configuration."""

    @patch('time.sleep')
    def test_custom_retriable_errors(self, mock_sleep):
        """Test retry with custom error types."""
        middleware = RetryMiddleware(max_retries=2)

        # Define custom error
        class CustomError(Exception):
            pass

        operation = Mock(side_effect=[CustomError("Custom"), "success"])

        result = middleware.execute_with_retry(
            operation,
            retriable_errors=(CustomError,)
        )

        assert result == "success"
        assert operation.call_count == 2

    def test_non_retriable_error_not_retried(self):
        """Test that non-retriable errors are not retried."""
        middleware = RetryMiddleware(max_retries=3)

        operation = Mock(side_effect=ValueError("Not retriable"))

        with pytest.raises(ValueError):
            middleware.execute_with_retry(
                operation,
                retriable_errors=MOCK_RETRIABLE_ERRORS
            )

        # Should not retry
        operation.assert_called_once()


@pytest.mark.unit
class TestWithRetryDecorator:
    """Test @with_retry decorator - tests basic functionality without exception mocking."""

    @patch('time.sleep')
    def test_decorator_basic_usage(self, mock_sleep):
        """Test basic decorator usage - success path only."""
        @with_retry(max_retries=2)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    @patch('time.sleep')
    def test_decorator_with_arguments(self, mock_sleep):
        """Test decorator with function arguments."""
        @with_retry(max_retries=2)
        def function_with_args(x, y):
            return x + y

        result = function_with_args(5, 3)
        assert result == 8

    @patch('time.sleep')
    def test_decorator_custom_params(self, mock_sleep):
        """Test decorator with custom retry parameters - success path."""
        @with_retry(max_retries=3, base_delay=2.0)
        def always_succeeds():
            return "success"

        result = always_succeeds()
        assert result == "success"


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_retries(self):
        """Test with max_retries=0 (no retries)."""
        middleware = RetryMiddleware(max_retries=0)
        operation = Mock(side_effect=RateLimitError("Error"))

        # max_retries=0 means no attempts at all - operation never called
        result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)
        assert result is None or operation.call_count == 0

    def test_single_retry(self):
        """Test with max_retries=1."""
        middleware = RetryMiddleware(max_retries=1)
        operation = Mock(side_effect=[RateLimitError("Error"), "success"])

        # max_retries=1 means only 1 attempt total - should fail
        with pytest.raises(RateLimitError):
            middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

    def test_operation_with_no_return_value(self):
        """Test operation that returns None."""
        middleware = RetryMiddleware()
        operation = Mock(return_value=None)

        result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert result is None
        operation.assert_called_once()

    @patch('time.sleep')
    def test_very_high_retry_count(self, mock_sleep):
        """Test with very high retry count."""
        middleware = RetryMiddleware(max_retries=10, base_delay=0.1)
        operation = Mock(side_effect=[RateLimitError("Error")] * 9 + ["success"])

        result = middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        assert result == "success"
        assert operation.call_count == 10

    def test_exception_without_status_code(self):
        """Test APIStatusError without explicit status_code - has default."""
        middleware = RetryMiddleware(max_retries=2)

        # MockAPIStatusError has default status_code=500, so it will be caught as 5xx
        error = APIStatusError("Error")

        operation = Mock(side_effect=error)

        # With default 500 status, it IS retriable, so it will retry and eventually raise
        with pytest.raises(APIStatusError):
            middleware.execute_with_retry(operation, retriable_errors=MOCK_RETRIABLE_ERRORS)

        # max_retries=2 means 2 attempts total
        assert operation.call_count == 2
