"""
Spinner utilities for Thanos CLI.

Provides a context manager for showing animated loading spinners
during long-running operations, with TTY detection for safe use
in pipes and redirects.

INTEGRATION WITH THANOS:
-----------------------
This module is integrated into ThanosOrchestrator to provide visual feedback
during long-running API calls:

1. run_command() - Shows "Executing {command}..." spinner
2. chat() - Shows "Thinking..." or "Thinking as {agent}..." spinner
3. route() - No spinner (delegates to run_command/chat to avoid double spinners)

SPINNER LIFECYCLE:
-----------------
Two usage patterns depending on streaming mode:

1. NON-STREAMING MODE (context manager):
   ```python
   with command_spinner("pa:daily"):
       result = api_client.chat(...)  # Spinner shows during API call
   # Spinner automatically stopped with success symbol (✓)
   ```

2. STREAMING MODE (manual control):
   ```python
   spinner = chat_spinner("Ops")
   spinner.start()
   for chunk in api_client.chat_stream(...):
       if first_chunk:
           spinner.stop()  # CRITICAL: Stop before printing output
           first_chunk = False
       print(chunk)
   ```

WHY TTY DETECTION MATTERS:
-------------------------
Spinners use ANSI escape codes for animation. These work in terminals
but break pipes, redirects, and CI environments:

- Terminal (TTY): Shows animated spinner
- Pipe/Redirect: Silent (no output, no interference)
- CI/Non-TTY: Silent (no output, no interference)

This is tested with sys.stdout.isatty() before starting the spinner.

GRACEFUL DEGRADATION:
--------------------
Three levels of fallback ensure spinners never break the CLI:

1. If yaspin unavailable: No spinner, silent operation
2. If not TTY: No spinner output (pipes/redirects work cleanly)
3. If spinner fails to start/stop: Caught and ignored (non-critical)

ERROR HANDLING:
--------------
Spinners are visual-only enhancements. If they fail, execution continues:

- Start fails: Logged to stderr, execution continues
- Stop fails: Silently ignored
- Update fails: Silently ignored, spinner continues with old text

The __exit__ method calls fail() automatically on exceptions to show ✗ symbol.
"""

import contextlib
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

    def __init__(
        self, text: str = "Processing...", color: str = "cyan", spinner_type: str = "dots"
    ):
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
        """Start spinner on context enter.

        USAGE: Non-streaming mode in orchestrator
        Used by run_command() and chat() when stream=False.
        The spinner automatically starts and will be stopped by __exit__.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner on context exit.

        AUTOMATIC ERROR HANDLING:
        - If exception occurred (exc_type is set): Shows ✗ symbol
        - If successful completion: Shows ✓ symbol

        This ensures proper visual feedback without manual calls to ok()/fail().
        """
        if exc_type:
            self.fail()
        else:
            self.ok()
        return False

    def start(self):
        """Start the spinner (only if TTY and yaspin available).

        USAGE: Streaming mode in orchestrator
        Used by run_command() and chat() when stream=True.
        Must be manually stopped before printing output to avoid interference.

        SAFETY CHECKS:
        1. TTY detection: Only show spinner in interactive terminals
        2. Library check: Only show if yaspin is installed
        3. Exception handling: Catch any yaspin errors without breaking execution
        """
        # First safety check: Only show spinner in TTY (terminal)
        # Pipes, redirects, and CI environments return False
        if not self._is_tty:
            return

        # Second safety check: Only show if yaspin library is available
        if not SPINNER_AVAILABLE:
            # Fallback to simple print for non-TTY or missing yaspin
            if not self._fallback_printed:
                print(f"{self.text}", end="", flush=True)
                self._fallback_printed = True
            return

        # Third safety check: Catch any errors during spinner initialization
        try:
            self._spinner = yaspin(
                text=self.text,
                color=self.color,
                spinner=getattr(Spinners, self.spinner_type, Spinners.dots),
            )
            self._spinner.start()
        except Exception as e:
            # If spinner fails to start, log warning but don't break execution
            # Spinner is visual-only, not critical
            print(f"\nWarning: Spinner error: {e}", file=sys.stderr)
            self._spinner = None

    def stop(self):
        """Stop the spinner without status symbol.

        CRITICAL FOR STREAMING MODE:
        This MUST be called before printing output in streaming mode to avoid
        the spinner animation interfering with streamed text. Called in
        orchestrator's run_command() and chat() before first chunk.
        """
        if self._spinner:
            # If stop fails, ignore - spinner is non-critical
            with contextlib.suppress(Exception):
                self._spinner.stop()
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
            # If update fails, ignore - spinner will continue with old text
            with contextlib.suppress(Exception):
                self._spinner.text = text


# ========================================================================
# Convenience Factory Functions
# ========================================================================
# These factory functions ensure consistent spinner styling across Thanos CLI.
# They are used by ThanosOrchestrator.run_command() and .chat() methods.


def command_spinner(command_name: str) -> ThanosSpinner:
    """Create spinner for command execution.

    INTEGRATION POINT: ThanosOrchestrator.run_command()
    Used when executing commands like "pa:daily", "pa:email", etc.

    VISUAL DESIGN:
    - Color: Cyan (matches command theme)
    - Text: "Executing {command_name}..."
    - Animation: Dots spinner

    Args:
        command_name: Name of the command being executed

    Returns:
        ThanosSpinner configured for command operations

    Example:
        >>> spinner = command_spinner("pa:daily")
        >>> with spinner:
        ...     result = api_client.chat(...)
    """
    return ThanosSpinner(text=f"Executing {command_name}...", color="cyan", spinner_type="dots")


def chat_spinner(agent_name: Optional[str] = None) -> ThanosSpinner:
    """Create spinner for chat operations.

    INTEGRATION POINT: ThanosOrchestrator.chat()
    Used when chatting with agents like "Ops", "Coach", "Strategy", etc.

    VISUAL DESIGN:
    - Color: Magenta (matches chat/agent theme)
    - Text: "Thinking..." or "Thinking as {agent}..." if agent detected
    - Animation: Dots spinner

    AGENT PERSONALIZATION:
    If agent_name is provided, the spinner shows which agent is responding.
    This helps users understand which personality/role is being consulted.

    Args:
        agent_name: Optional name of the agent being consulted

    Returns:
        ThanosSpinner configured for chat operations

    Example:
        >>> spinner = chat_spinner("Ops")  # Shows "Thinking as Ops..."
        >>> spinner.start()
        >>> for chunk in api_client.chat_stream(...):
        ...     if first_chunk:
        ...         spinner.stop()  # Stop before output
        ...     print(chunk)
    """
    text = f"Thinking as {agent_name}..." if agent_name else "Thinking..."
    return ThanosSpinner(text=text, color="magenta", spinner_type="dots")


def routing_spinner() -> ThanosSpinner:
    """Create spinner for routing operations (rarely used).

    NOTE: Currently NOT used in ThanosOrchestrator.route()

    WHY NOT USED:
    - Routing is very fast (~12μs for agent detection)
    - route() delegates to run_command() or chat() which have their own spinners
    - Using a spinner here would create confusing double spinners
    - Users should only see one spinner at a time for clarity

    This function exists for potential future use if routing logic becomes
    more complex (e.g., multi-step intent detection, API-based routing).

    Returns:
        ThanosSpinner configured for routing operations
    """
    return ThanosSpinner(text="Routing...", color="yellow", spinner_type="dots")
