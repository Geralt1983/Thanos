"""
Spinner utilities for Thanos CLI.

Provides a context manager for showing animated loading spinners
during long-running operations, with TTY detection for safe use
in pipes and redirects.
"""

import sys
from typing import Optional

# Try to import yaspin with graceful fallback
try:
    from yaspin import yaspin
    from yaspin.spinners import Spinners
    SPINNER_AVAILABLE = True
except ImportError:
    SPINNER_AVAILABLE = False


class ThanosSpinner:
    """
    Wrapper around yaspin for Thanos CLI operations.

    Features:
    - TTY detection (no spinner in pipes/redirects)
    - Consistent styling across CLI
    - Context manager for clean lifecycle
    - Success/failure indicators
    - Graceful fallback if yaspin unavailable
    """

    def __init__(self, text: str = "Processing...",
                 color: str = "cyan",
                 spinner_type: str = "dots"):
        """
        Initialize spinner.

        Args:
            text: Spinner message
            color: Spinner color (cyan, magenta, yellow, green)
            spinner_type: Spinner animation (dots, line, arc, etc.)
        """
        self.text = text
        self.color = color
        self.spinner_type = spinner_type
        self._spinner = None
        self._is_tty = sys.stdout.isatty()
        self._fallback_printed = False

    def __enter__(self):
        """Start spinner on context enter."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner on context exit."""
        if exc_type:
            self.fail()
        else:
            self.ok()
        return False

    def start(self):
        """Start the spinner (only if TTY and yaspin available)."""
        if not self._is_tty:
            return

        if not SPINNER_AVAILABLE:
            # Fallback to simple print for non-TTY or missing yaspin
            if not self._fallback_printed:
                print(f"{self.text}", end="", flush=True)
                self._fallback_printed = True
            return

        try:
            self._spinner = yaspin(
                text=self.text,
                color=self.color,
                spinner=getattr(Spinners, self.spinner_type, Spinners.dots)
            )
            self._spinner.start()
        except Exception as e:
            # If spinner fails to start, log warning but don't break execution
            # Spinner is visual-only, not critical
            print(f"\nWarning: Spinner error: {e}", file=sys.stderr)
            self._spinner = None

    def stop(self):
        """Stop the spinner without status symbol."""
        if self._spinner:
            try:
                self._spinner.stop()
            except Exception:
                # If stop fails, ignore - spinner is non-critical
                pass
            self._spinner = None
        elif self._fallback_printed:
            # Clear fallback text
            print("\r" + " " * (len(self.text) + 5) + "\r", end="", flush=True)
            self._fallback_printed = False

    def ok(self, text: str = "✓"):
        """Stop spinner with success symbol."""
        if self._spinner:
            try:
                self._spinner.ok(text)
            except Exception:
                # If ok fails, just stop
                self.stop()
            self._spinner = None
        elif self._fallback_printed:
            # Clear and show success
            print(f"\r{text}", flush=True)
            self._fallback_printed = False

    def fail(self, text: str = "✗"):
        """Stop spinner with failure symbol."""
        if self._spinner:
            try:
                self._spinner.fail(text)
            except Exception:
                # If fail fails, just stop
                self.stop()
            self._spinner = None
        elif self._fallback_printed:
            # Clear and show failure
            print(f"\r{text}", flush=True)
            self._fallback_printed = False

    def update_text(self, text: str):
        """Update spinner text while running."""
        self.text = text
        if self._spinner:
            try:
                self._spinner.text = text
            except Exception:
                # If update fails, ignore - spinner will continue with old text
                pass


# Convenience factory functions
def command_spinner(command_name: str) -> ThanosSpinner:
    """Create spinner for command execution.

    Args:
        command_name: Name of the command being executed

    Returns:
        ThanosSpinner configured for command operations
    """
    return ThanosSpinner(
        text=f"Executing {command_name}...",
        color="cyan",
        spinner_type="dots"
    )


def chat_spinner(agent_name: Optional[str] = None) -> ThanosSpinner:
    """Create spinner for chat operations.

    Args:
        agent_name: Optional name of the agent being consulted

    Returns:
        ThanosSpinner configured for chat operations
    """
    text = f"Thinking as {agent_name}..." if agent_name else "Thinking..."
    return ThanosSpinner(
        text=text,
        color="magenta",
        spinner_type="dots"
    )


def routing_spinner() -> ThanosSpinner:
    """Create spinner for routing operations (rarely used).

    Returns:
        ThanosSpinner configured for routing operations
    """
    return ThanosSpinner(
        text="Routing...",
        color="yellow",
        spinner_type="dots"
    )
