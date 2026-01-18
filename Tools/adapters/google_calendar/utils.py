"""
Utilities for Google Calendar Adapter.
Handles error parsing and retry logic.
"""

import json
import random
import time
import logging
from typing import Any, Callable, Dict, Optional
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

logger = logging.getLogger(__name__)

# Retry configuration defaults
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 1.0
DEFAULT_MAX_BACKOFF = 32.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0
DEFAULT_JITTER_RANGE = 0.1


def parse_http_error(error: HttpError) -> Dict[str, Any]:
    """
    Parse HttpError to extract useful error information.

    Args:
        error: The HttpError exception

    Returns:
        Dictionary with status_code, reason, and message
    """
    status_code = error.resp.status
    error_content = {}

    try:
        error_content = json.loads(error.content.decode("utf-8"))
    except (json.JSONDecodeError, AttributeError):
        pass

    # Extract error details from the response
    error_info = error_content.get("error", {})
    # Google errors format: "errors": [{"reason": ...}]
    errors_list = error_info.get("errors", [{}])
    reason = errors_list[0].get("reason", "unknown") if errors_list else "unknown"
    message = error_info.get("message", str(error))

    return {
        "status_code": status_code,
        "reason": reason,
        "message": message,
    }


def calculate_backoff(
    base_backoff: float, 
    attempt: int, 
    jitter_range: float = DEFAULT_JITTER_RANGE
) -> float:
    """
    Calculate backoff time with exponential increase and random jitter.

    Args:
        base_backoff: Base backoff time in seconds
        attempt: Current retry attempt number (0-indexed)
        jitter_range: Jitter factor (default 0.1)

    Returns:
        Backoff time in seconds with jitter applied
    """
    # Add random jitter to prevent thundering herd
    jitter = base_backoff * jitter_range * (2 * random.random() - 1)
    return base_backoff + jitter


def execute_api_call_with_retry(
    api_call: Callable,
    operation_name: str = "API call",
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
    max_backoff: float = DEFAULT_MAX_BACKOFF,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    refresh_credentials_callback: Optional[Callable[[], bool]] = None,
) -> Any:
    """
    Execute a Google Calendar API call with retry logic and comprehensive error handling.

    Args:
        api_call: Callable executing the API request
        operation_name: Name for logging
        max_retries: Max attempts
        initial_backoff: Initial sleep time
        max_backoff: Max sleep time
        backoff_multiplier: Multiplier per attempt
        refresh_credentials_callback: Optional callback to refresh credentials on 401

    Returns:
        Result of api_call()
    """
    last_error = None
    backoff = initial_backoff

    logger.debug(f"Starting API call: {operation_name}")

    for attempt in range(max_retries):
        try:
            # Execute the API call
            result = api_call()

            # Log success
            if attempt > 0:
                logger.info(f"API call '{operation_name}' succeeded after {attempt + 1} attempts")
            else:
                logger.debug(f"API call '{operation_name}' succeeded")

            return result

        except HttpError as e:
            last_error = e
            error_details = parse_http_error(e)
            status_code = error_details["status_code"]
            error_reason = error_details["reason"]

            # Authentication errors (401)
            if status_code == 401:
                logger.warning(f"API call '{operation_name}' 401 Unauthorized, attempting refresh")
                if refresh_credentials_callback and refresh_credentials_callback():
                    logger.info("Credentials refreshed, retrying immediately")
                    continue
                else:
                    logger.error(f"API call '{operation_name}' failed: Auth failed/expired")
                    raise ValueError(
                        f"{operation_name} failed: Authentication expired. Re-auth required."
                    ) from e

            # Permission/Quota errors (403)
            elif status_code == 403:
                if error_reason in ["rateLimitExceeded", "quotaExceeded", "userRateLimitExceeded"]:
                    if attempt < max_retries - 1:
                        sleep_time = calculate_backoff(backoff, attempt)
                        logger.warning(
                            f"API call '{operation_name}' quota/rate limit ({error_reason}). "
                            f"Retrying in {sleep_time:.2f}s"
                        )
                        time.sleep(sleep_time)
                        backoff = min(backoff * backoff_multiplier, max_backoff)
                        continue
                    else:
                        raise RuntimeError(
                            f"{operation_name} failed: Quota/Rate limit ({error_reason})."
                        ) from e
                else:
                    raise ValueError(
                        f"{operation_name} failed: Permission denied ({error_reason})."
                    ) from e

            # Bad Request (400) or Not Found (404)
            elif status_code in [400, 404]:
                raise ValueError(
                    f"{operation_name} failed: {status_code} - {error_details['message']}"
                ) from e
            
            # Rate Limit (429) or Server Error (5xx)
            elif status_code == 429 or 500 <= status_code < 600:
                if attempt < max_retries - 1:
                    sleep_time = calculate_backoff(backoff, attempt)
                    logger.warning(
                        f"API call '{operation_name}' failed ({status_code}). "
                        f"Retrying in {sleep_time:.2f}s"
                    )
                    time.sleep(sleep_time)
                    backoff = min(backoff * backoff_multiplier, max_backoff)
                    continue
                else:
                    raise RuntimeError(
                        f"{operation_name} failed: Server error {status_code}."
                    ) from e

            else:
                raise RuntimeError(
                    f"{operation_name} failed: HTTP {status_code} - {error_details['message']}"
                ) from e

        except RefreshError as e:
            # Credential refresh failed
            raise ValueError(f"{operation_name} failed: Unable to refresh credentials.") from e

        except (ConnectionError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = calculate_backoff(backoff, attempt)
                logger.warning(
                    f"API call '{operation_name}' connection issue: {e}. Retrying in {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)
                backoff = min(backoff * backoff_multiplier, max_backoff)
                continue
            else:
                raise RuntimeError(f"{operation_name} failed: Network error: {e}") from e

        except Exception as e:
            logger.exception(f"API call '{operation_name}' unexpected error")
            raise RuntimeError(f"{operation_name} failed: {str(e)}") from e

    raise RuntimeError(f"{operation_name} failed after {max_retries} attempts.")
