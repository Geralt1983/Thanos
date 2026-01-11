"""
Error logging utility for Thanos.

Provides simple error logging to file without disrupting execution.
"""
import sys
from pathlib import Path
from datetime import datetime


def log_error(component: str, error: Exception, context: str = ""):
    """Log an error to the error log file.

    Args:
        component: Component name where error occurred
        error: The exception that was caught
        context: Additional context about the error
    """
    try:
        log_dir = Path.home() / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "errors.log"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = f"[{timestamp}] [{component}] {context}: {type(error).__name__}: {error}\n"

        with open(log_file, 'a') as f:
            f.write(error_msg)

    except Exception as e:
        # If logging fails, write to stderr but don't break execution
        print(f"[error_logger] Failed to log error: {e}", file=sys.stderr)
