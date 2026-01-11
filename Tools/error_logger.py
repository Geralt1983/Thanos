#!/usr/bin/env python3
"""
Centralized error logging for Thanos.

Provides consistent error logging across all Thanos modules without
introducing heavy dependencies or breaking hook execution.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Growth protection constants
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_LOG_BACKUPS = 3


def _rotate_log_if_needed(log_file: Path) -> None:
    """Rotate log file if it exceeds MAX_LOG_SIZE_BYTES."""
    try:
        if not log_file.exists():
            return

        if log_file.stat().st_size < MAX_LOG_SIZE_BYTES:
            return

        # Rotate existing backups
        for i in range(MAX_LOG_BACKUPS - 1, 0, -1):
            old_backup = log_file.with_suffix(f".{i}.log")
            new_backup = log_file.with_suffix(f".{i + 1}.log")
            if old_backup.exists():
                if i + 1 > MAX_LOG_BACKUPS:
                    old_backup.unlink()  # Delete oldest
                else:
                    old_backup.rename(new_backup)

        # Move current log to .1.log
        backup_1 = log_file.with_suffix(".1.log")
        log_file.rename(backup_1)
    except Exception as e:
        # Don't let rotation errors break logging, but note them
        print(f"[error_logger] Log rotation failed: {e}", file=sys.stderr)


def log_error(module: str, error: Exception, context: Optional[str] = None,
              reraise: bool = False):
    """
    Log an error to stderr and optionally to file.

    Args:
        module: Module name (e.g., "state_reader", "thanos_interactive")
        error: The exception that occurred
        context: Additional context about what was being attempted
        reraise: Whether to re-raise the exception after logging

    Example:
        try:
            risky_operation()
        except FileNotFoundError as e:
            log_error("my_module", e, "Failed to load config file")
            # Handle gracefully or reraise
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error_type = type(error).__name__
    error_msg = str(error)

    # Build log message
    log_parts = [
        f"[{timestamp}]",
        f"[{module}]",
        f"{error_type}: {error_msg}"
    ]

    if context:
        log_parts.append(f"Context: {context}")

    log_message = " ".join(log_parts)

    # Always log to stderr so it's visible
    print(log_message, file=sys.stderr)

    # Try to log to file (but don't break if we can't)
    try:
        log_dir = Path.home() / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "thanos-errors.log"

        # Check for rotation before writing
        _rotate_log_if_needed(log_file)

        with open(log_file, 'a') as f:
            f.write(log_message + "\n")
    except Exception as e:
        # Can't log to file, already logged to stderr - note the file issue
        print(f"[error_logger] Failed to write log file: {e}", file=sys.stderr)

    if reraise:
        raise error


def log_warning(module: str, message: str):
    """
    Log a warning message.

    Args:
        module: Module name
        message: Warning message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] [{module}] WARNING: {message}"
    print(log_message, file=sys.stderr)
