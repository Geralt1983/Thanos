#!/usr/bin/env python3
"""
Prompt Formatter - Formats interactive prompt with session stats (tokens, cost, duration).

This module provides utilities for formatting the Thanos interactive prompt to display
real-time session statistics including token usage, estimated costs, and session duration.
Supports multiple display modes (compact, standard, verbose) and color-coded cost thresholds
to help users monitor their API spend during interactive sessions.

Key Features:
    - Multiple display modes for different verbosity levels
    - Color-coded cost indicators (green/yellow/red thresholds)
    - Human-readable token formatting (K for thousands, M for millions)
    - Session duration formatting (minutes and hours)
    - Configurable cost thresholds for color coding
    - Graceful degradation when stats are unavailable
    - Configuration loading from config/api.json

Key Classes:
    PromptFormatter: Main class for formatting interactive prompts

Usage:
    from Tools.prompt_formatter import PromptFormatter

    # Initialize formatter with default settings
    formatter = PromptFormatter()

    # Format prompt with session stats
    stats = session.get_stats()
    prompt = formatter.format(stats, mode="compact")
    # Output: "(1.2K | $0.04) Thanos> "

    # Use different modes
    prompt = formatter.format(stats, mode="standard")
    # Output: "(45m | 1.2K tokens | $0.04) Thanos> "

    prompt = formatter.format(stats, mode="verbose")
    # Output: "(45m | 12 msgs | 1.2K in | 3.4K out | $0.04) Thanos> "

Configuration:
    The formatter loads configuration from config/api.json under the
    "interactive_prompt" key. Users can customize:
    - Enable/disable prompt display
    - Display mode (compact/standard/verbose)
    - Color coding thresholds
    - Show/hide duration and message count

    Example config/api.json:
    {
      "interactive_prompt": {
        "enabled": true,
        "mode": "compact",
        "color_coding": {
          "enabled": true,
          "thresholds": {
            "low": 0.50,
            "medium": 2.00
          }
        }
      }
    }

Display Modes:
    - compact: Shows tokens and cost only (default)
    - standard: Adds session duration
    - verbose: Shows duration, message count, and separate input/output tokens

Color Coding:
    - GREEN ($0.00 - $0.50): Low cost, safe to continue
    - YELLOW ($0.51 - $2.00): Medium cost, monitor usage
    - RED ($2.01+): High cost, attention needed

See Also:
    - Tools.command_handlers.state_handler: /usage command implementation
    - SESSION_STATS_VERIFICATION.md: Session stats integration details
    - PROMPT_DESIGN.md: Complete design specification
"""

import json
from pathlib import Path
from typing import Dict, Optional


class Colors:
    """ANSI color codes for terminal output."""
    PURPLE = "\033[35m"
    BRIGHT_MAGENTA = "\033[95m"  # Bright purple for Thanos prompt
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class PromptFormatter:
    """
    Formats interactive prompts with session statistics.

    This class provides flexible prompt formatting with support for multiple
    display modes and color-coded cost indicators. It handles edge cases like
    zero tokens, missing data, and very large numbers gracefully.

    Configuration is loaded from config/api.json under "interactive_prompt" key.
    Users can customize display mode, color coding, and thresholds.

    Attributes:
        enabled (bool): Whether to show token/cost stats in prompt
        default_mode (str): Default display mode (compact/standard/verbose)
        low_cost_threshold (float): Cost threshold for green/yellow boundary (default: $0.50)
        medium_cost_threshold (float): Cost threshold for yellow/red boundary (default: $2.00)
        enable_colors (bool): Whether to use color coding (default: True)
        default_prompt (str): Fallback prompt when stats unavailable (default: "Thanos> ")
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        low_cost_threshold: Optional[float] = None,
        medium_cost_threshold: Optional[float] = None,
        enable_colors: Optional[bool] = None,
        default_prompt: Optional[str] = None
    ):
        """
        Initialize PromptFormatter with configuration.

        Configuration is loaded from config/api.json by default. Parameters passed
        to __init__ override the config file values.

        Args:
            config_path: Path to configuration file (default: config/api.json)
            low_cost_threshold: Dollar amount for green/yellow boundary (overrides config)
            medium_cost_threshold: Dollar amount for yellow/red boundary (overrides config)
            enable_colors: Enable color-coded cost indicators (overrides config)
            default_prompt: Fallback prompt when stats unavailable (default: colored "Thanos> ")
        """
        # Load configuration from file
        config = self._load_config(config_path)

        # Set defaults from config or fallback to hardcoded defaults
        self.enabled = config.get("enabled", True)
        self.default_mode = config.get("mode", "compact")

        # Color coding configuration
        color_config = config.get("color_coding", {})
        thresholds = color_config.get("thresholds", {})

        # Use parameter values if provided, otherwise use config, otherwise use defaults
        self.low_cost_threshold = (
            low_cost_threshold if low_cost_threshold is not None
            else thresholds.get("low", 0.50)
        )
        self.medium_cost_threshold = (
            medium_cost_threshold if medium_cost_threshold is not None
            else thresholds.get("medium", 2.00)
        )
        self.enable_colors = (
            enable_colors if enable_colors is not None
            else color_config.get("enabled", True)
        )

        # Default prompt with bright magenta "Thanos>"
        if default_prompt is not None:
            self.default_prompt = default_prompt
        else:
            self.default_prompt = f"{Colors.BRIGHT_MAGENTA}Thanos>{Colors.RESET} "

    def _load_config(self, config_path: Optional[str] = None) -> Dict:
        """
        Load configuration from config/api.json.

        Args:
            config_path: Optional path to config file

        Returns:
            Configuration dict with interactive_prompt settings
        """
        try:
            # Determine config file path
            if config_path is None:
                base_dir = Path(__file__).parent.parent
                config_path = base_dir / "config" / "api.json"
            else:
                config_path = Path(config_path)

            # Load config file
            if config_path.exists():
                full_config = json.loads(config_path.read_text())
                return full_config.get("interactive_prompt", {})
        except Exception:
            # Silently fall back to defaults if config fails to load
            pass

        # Return empty dict if config not found (will use defaults)
        return {}

    def format(self, stats: Optional[Dict] = None, mode: Optional[str] = None) -> str:
        """
        Format prompt with session statistics.

        Args:
            stats: Session stats dict with keys: total_input_tokens, total_output_tokens,
                   total_cost, duration_minutes, message_count. If None, returns default prompt.
            mode: Display mode - "compact", "standard", or "verbose". If None, uses config
                  default mode. (default: None, which uses configured mode)

        Returns:
            Formatted prompt string ready for display

        Examples:
            >>> formatter = PromptFormatter()
            >>> stats = {
            ...     "total_input_tokens": 500,
            ...     "total_output_tokens": 700,
            ...     "total_cost": 0.04,
            ...     "duration_minutes": 15,
            ...     "message_count": 8
            ... }
            >>> formatter.format(stats, mode="compact")
            '(1.2K | $0.04) Thanos> '
            >>> formatter.format(stats, mode="standard")
            '(15m | 1.2K tokens | $0.04) Thanos> '
        """
        # If disabled, always return default prompt
        if not self.enabled:
            return self.default_prompt

        # Handle missing or invalid stats
        if not stats or not isinstance(stats, dict):
            return self.default_prompt

        # Extract values with defaults for missing keys
        try:
            total_input_tokens = stats.get("total_input_tokens", 0)
            total_output_tokens = stats.get("total_output_tokens", 0)
            total_cost = stats.get("total_cost", 0.0)
            duration_minutes = stats.get("duration_minutes", 0)
            message_count = stats.get("message_count", 0)
            error_count = stats.get("error_count", 0)
        except (AttributeError, TypeError):
            return self.default_prompt

        # Don't show stats for brand new sessions (no tokens yet)
        total_tokens = total_input_tokens + total_output_tokens
        if total_tokens == 0 and total_cost == 0.0:
            return self.default_prompt

        # Use provided mode or fall back to configured default mode
        display_mode = mode if mode is not None else self.default_mode

        # Format based on mode
        if display_mode == "verbose":
            return self._format_verbose(
                total_input_tokens, total_output_tokens, total_cost,
                duration_minutes, message_count, error_count
            )
        elif display_mode == "standard":
            return self._format_standard(
                total_tokens, total_cost, duration_minutes, error_count
            )
        else:  # compact mode (default)
            return self._format_compact(total_tokens, total_cost, error_count)

    def _format_compact(self, total_tokens: int, cost: float, error_count: int = 0) -> str:
        """
        Format prompt in compact mode: (1.2K | $0.04) Thanos>

        Args:
            total_tokens: Combined input and output tokens
            cost: Estimated cost in USD
            error_count: Number of API errors in session

        Returns:
            Compact formatted prompt string
        """
        tokens_display = self._format_token_count(total_tokens)
        cost_display = self._format_cost(cost)
        error_display = self._format_error_count(error_count)
        thanos_prompt = f"{Colors.BRIGHT_MAGENTA}Thanos>{Colors.RESET}"
        return f"({tokens_display} | {cost_display}{error_display}) {thanos_prompt} "

    def _format_standard(self, total_tokens: int, cost: float, duration: int, error_count: int = 0) -> str:
        """
        Format prompt in standard mode: (45m | 1.2K tokens | $0.04) Thanos>

        Args:
            total_tokens: Combined input and output tokens
            cost: Estimated cost in USD
            duration: Session duration in minutes
            error_count: Number of API errors in session

        Returns:
            Standard formatted prompt string
        """
        duration_display = self._format_duration(duration)
        tokens_display = self._format_token_count(total_tokens)
        cost_display = self._format_cost(cost)
        error_display = self._format_error_count(error_count)
        thanos_prompt = f"{Colors.BRIGHT_MAGENTA}Thanos>{Colors.RESET}"
        return f"({duration_display} | {tokens_display} tokens | {cost_display}{error_display}) {thanos_prompt} "

    def _format_verbose(
        self,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        duration: int,
        message_count: int,
        error_count: int = 0
    ) -> str:
        """
        Format prompt in verbose mode: (45m | 12 msgs | 1.2K in | 3.4K out | $0.04) Thanos>

        Args:
            input_tokens: Input tokens only
            output_tokens: Output tokens only
            cost: Estimated cost in USD
            duration: Session duration in minutes
            message_count: Number of messages in session
            error_count: Number of API errors in session

        Returns:
            Verbose formatted prompt string
        """
        duration_display = self._format_duration(duration)
        input_display = self._format_token_count(input_tokens)
        output_display = self._format_token_count(output_tokens)
        cost_display = self._format_cost(cost)
        error_display = self._format_error_count(error_count)
        thanos_prompt = f"{Colors.BRIGHT_MAGENTA}Thanos>{Colors.RESET}"
        return f"({duration_display} | {message_count} msgs | {input_display} in | {output_display} out | {cost_display}{error_display}) {thanos_prompt} "

    def _format_token_count(self, tokens: int) -> str:
        """
        Format token count with appropriate suffix (K for thousands, M for millions).

        Args:
            tokens: Raw token count

        Returns:
            Formatted token string (e.g., "1.2K", "123", "1.5M")

        Examples:
            >>> formatter = PromptFormatter()
            >>> formatter._format_token_count(500)
            '500'
            >>> formatter._format_token_count(1234)
            '1.2K'
            >>> formatter._format_token_count(1500000)
            '1.5M'
        """
        if tokens >= 1_000_000:
            return f"{tokens / 1_000_000:.1f}M"
        elif tokens >= 1000:
            return f"{tokens / 1000:.1f}K"
        else:
            return str(tokens)

    def _format_cost(self, cost: float) -> str:
        """
        Format cost with color coding based on thresholds.

        Args:
            cost: Cost in USD

        Returns:
            Formatted cost string with optional color codes

        Examples:
            >>> formatter = PromptFormatter()
            >>> formatter._format_cost(0.04)  # Green
            '\\033[32m$0.04\\033[0m'
            >>> formatter._format_cost(1.50)  # Yellow
            '\\033[33m$1.50\\033[0m'
            >>> formatter._format_cost(3.00)  # Red
            '\\033[31m$3.00\\033[0m'
        """
        # Ensure non-negative cost
        cost = max(0.0, cost)

        # Format with appropriate decimal places
        if cost >= 10:
            cost_str = f"${cost:.2f}"
        elif cost > 0 and cost < 0.01:
            cost_str = f"${cost:.4f}"
        else:
            cost_str = f"${cost:.2f}"

        # Apply color coding if enabled
        if self.enable_colors:
            color = self._get_cost_color(cost)
            return f"{color}{cost_str}{Colors.RESET}"
        else:
            return cost_str

    def _get_cost_color(self, cost: float) -> str:
        """
        Determine color code based on cost thresholds.

        Args:
            cost: Cost in USD

        Returns:
            ANSI color code string

        Color Mapping:
            - GREEN: $0.00 - $0.50 (low cost, safe)
            - YELLOW: $0.51 - $2.00 (medium cost, monitor)
            - RED: $2.01+ (high cost, attention needed)
        """
        if cost <= self.low_cost_threshold:
            return Colors.GREEN
        elif cost <= self.medium_cost_threshold:
            return Colors.YELLOW
        else:
            return Colors.RED

    def _format_duration(self, minutes: int) -> str:
        """
        Format session duration in human-readable form.

        Args:
            minutes: Duration in minutes

        Returns:
            Formatted duration string (e.g., "15m", "1h30m", "2h")

        Examples:
            >>> formatter = PromptFormatter()
            >>> formatter._format_duration(15)
            '15m'
            >>> formatter._format_duration(90)
            '1h30m'
            >>> formatter._format_duration(120)
            '2h'
        """
        if minutes >= 60:
            hours = minutes // 60
            remaining_mins = minutes % 60
            if remaining_mins > 0:
                return f"{hours}h{remaining_mins}m"
            else:
                return f"{hours}h"
        else:
            return f"{minutes}m"

    def _format_error_count(self, error_count: int) -> str:
        """
        Format error count indicator for display in prompt.

        Only shows if error_count > 0 to avoid cluttering the prompt.

        Args:
            error_count: Number of API errors in session

        Returns:
            Formatted error indicator string (e.g., " | 2 errs" in red)

        Examples:
            >>> formatter = PromptFormatter()
            >>> formatter._format_error_count(0)
            ''
            >>> formatter._format_error_count(2)
            ' | \\033[31m2 errs\\033[0m'
        """
        if error_count <= 0:
            return ""

        # Format with red color if colors enabled
        if self.enable_colors:
            return f" | {Colors.RED}{error_count} err{'s' if error_count > 1 else ''}{Colors.RESET}"
        else:
            return f" | {error_count} err{'s' if error_count > 1 else ''}"
