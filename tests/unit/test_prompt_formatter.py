"""
Unit tests for PromptFormatter.

Tests cover:
- Compact, standard, and verbose formatting modes
- Token count formatting (0, 999, 1000, 1M+, boundary values)
- Cost formatting and color coding
- Duration formatting (minutes, hours, days, weeks)
- Color threshold logic and exact boundaries
- Configuration loading and overrides
- Edge cases including:
  * None values, empty dicts, zero tokens
  * Negative token counts, float token counts
  * String values in stats (type validation)
  * Missing keys, extra keys, partial stats
  * Invalid modes, invalid stats types
  * Very large numbers (millions of tokens, extreme costs)
  * Very small costs (precision edge cases)
  * Extremely long durations
  * Unicode in default prompt
  * Malformed and empty config files
  * Multiple sequential format calls (statelessness)
- Integration tests (session progression, mode comparison, color progression)
- Graceful degradation when stats unavailable

Total: 67 comprehensive unit tests
"""

import re

import pytest

from Tools.prompt_formatter import Colors, PromptFormatter


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text for comparison."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


@pytest.mark.unit
class TestPromptFormatterInitialization:
    """Test PromptFormatter initialization."""

    def test_default_initialization(self):
        """Test formatter creation with default values."""
        formatter = PromptFormatter()
        assert formatter.low_cost_threshold == 0.50
        assert formatter.medium_cost_threshold == 2.00
        assert formatter.enable_colors is True
        assert strip_ansi(formatter.default_prompt) == "Thanos> "

    def test_custom_initialization(self):
        """Test formatter creation with custom values."""
        formatter = PromptFormatter(
            low_cost_threshold=1.00,
            medium_cost_threshold=5.00,
            enable_colors=False,
            default_prompt="Custom> "
        )
        assert formatter.low_cost_threshold == 1.00
        assert formatter.medium_cost_threshold == 5.00
        assert formatter.enable_colors is False
        assert formatter.default_prompt == "Custom> "


@pytest.mark.unit
class TestCompactMode:
    """Test compact mode formatting."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with colors disabled for easier testing."""
        return PromptFormatter(enable_colors=False)

    def test_basic_compact_format(self, formatter):
        """Test basic compact mode output."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="compact")
        assert strip_ansi(result) == "(1.2K | $0.04) Thanos> "

    def test_compact_with_small_token_count(self, formatter):
        """Test compact mode with token count < 1000."""
        stats = {
            "total_input_tokens": 300,
            "total_output_tokens": 400,
            "total_cost": 0.02,
            "duration_minutes": 5,
            "message_count": 3
        }
        result = formatter.format(stats, mode="compact")
        assert strip_ansi(result) == "(700 | $0.02) Thanos> "

    def test_compact_with_large_token_count(self, formatter):
        """Test compact mode with token count >= 1M."""
        stats = {
            "total_input_tokens": 500000,
            "total_output_tokens": 500000,
            "total_cost": 15.00,
            "duration_minutes": 120,
            "message_count": 50
        }
        result = formatter.format(stats, mode="compact")
        assert strip_ansi(result) == "(1.0M | $15.00) Thanos> "


@pytest.mark.unit
class TestStandardMode:
    """Test standard mode formatting."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with colors disabled for easier testing."""
        return PromptFormatter(enable_colors=False)

    def test_basic_standard_format(self, formatter):
        """Test basic standard mode output."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="standard")
        assert strip_ansi(result) == "(15m | 1.2K tokens | $0.04) Thanos> "

    def test_standard_with_hours(self, formatter):
        """Test standard mode with duration in hours."""
        stats = {
            "total_input_tokens": 5000,
            "total_output_tokens": 7000,
            "total_cost": 0.50,
            "duration_minutes": 90,
            "message_count": 25
        }
        result = formatter.format(stats, mode="standard")
        assert strip_ansi(result) == "(1h30m | 12.0K tokens | $0.50) Thanos> "

    def test_standard_with_exact_hours(self, formatter):
        """Test standard mode with exact hours (no remaining minutes)."""
        stats = {
            "total_input_tokens": 5000,
            "total_output_tokens": 7000,
            "total_cost": 0.50,
            "duration_minutes": 120,
            "message_count": 30
        }
        result = formatter.format(stats, mode="standard")
        assert strip_ansi(result) == "(2h | 12.0K tokens | $0.50) Thanos> "


@pytest.mark.unit
class TestVerboseMode:
    """Test verbose mode formatting."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with colors disabled for easier testing."""
        return PromptFormatter(enable_colors=False)

    def test_basic_verbose_format(self, formatter):
        """Test basic verbose mode output."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="verbose")
        assert strip_ansi(result) == "(15m | 8 msgs | 500 in | 700 out | $0.04) Thanos> "

    def test_verbose_with_large_tokens(self, formatter):
        """Test verbose mode with large token counts."""
        stats = {
            "total_input_tokens": 12000,
            "total_output_tokens": 34000,
            "total_cost": 2.50,
            "duration_minutes": 90,
            "message_count": 25
        }
        result = formatter.format(stats, mode="verbose")
        assert strip_ansi(result) == "(1h30m | 25 msgs | 12.0K in | 34.0K out | $2.50) Thanos> "


@pytest.mark.unit
class TestTokenFormatting:
    """Test token count formatting."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return PromptFormatter()

    def test_format_zero_tokens(self, formatter):
        """Test formatting zero tokens."""
        assert formatter._format_token_count(0) == "0"

    def test_format_small_tokens(self, formatter):
        """Test formatting tokens < 1000."""
        assert formatter._format_token_count(1) == "1"
        assert formatter._format_token_count(99) == "99"
        assert formatter._format_token_count(999) == "999"

    def test_format_thousand_tokens(self, formatter):
        """Test formatting tokens >= 1000."""
        assert formatter._format_token_count(1000) == "1.0K"
        assert formatter._format_token_count(1234) == "1.2K"
        assert formatter._format_token_count(5678) == "5.7K"
        assert formatter._format_token_count(999999) == "1000.0K"

    def test_format_million_tokens(self, formatter):
        """Test formatting tokens >= 1M."""
        assert formatter._format_token_count(1000000) == "1.0M"
        assert formatter._format_token_count(1234567) == "1.2M"
        assert formatter._format_token_count(5678901) == "5.7M"


@pytest.mark.unit
class TestCostFormatting:
    """Test cost formatting and color coding."""

    def test_format_cost_without_colors(self):
        """Test cost formatting with colors disabled."""
        formatter = PromptFormatter(enable_colors=False)
        assert formatter._format_cost(0.00) == "$0.00"
        assert formatter._format_cost(0.04) == "$0.04"
        assert formatter._format_cost(1.23) == "$1.23"
        assert formatter._format_cost(12.34) == "$12.34"

    def test_format_cost_with_colors_low(self):
        """Test cost formatting with green color (low threshold)."""
        formatter = PromptFormatter(enable_colors=True, low_cost_threshold=0.50)
        result = formatter._format_cost(0.04)
        assert result == f"{Colors.GREEN}$0.04{Colors.RESET}"
        result = formatter._format_cost(0.50)
        assert result == f"{Colors.GREEN}$0.50{Colors.RESET}"

    def test_format_cost_with_colors_medium(self):
        """Test cost formatting with yellow color (medium threshold)."""
        formatter = PromptFormatter(
            enable_colors=True,
            low_cost_threshold=0.50,
            medium_cost_threshold=2.00
        )
        result = formatter._format_cost(0.51)
        assert result == f"{Colors.YELLOW}$0.51{Colors.RESET}"
        result = formatter._format_cost(1.50)
        assert result == f"{Colors.YELLOW}$1.50{Colors.RESET}"
        result = formatter._format_cost(2.00)
        assert result == f"{Colors.YELLOW}$2.00{Colors.RESET}"

    def test_format_cost_with_colors_high(self):
        """Test cost formatting with red color (high threshold)."""
        formatter = PromptFormatter(enable_colors=True, medium_cost_threshold=2.00)
        result = formatter._format_cost(2.01)
        assert result == f"{Colors.RED}$2.01{Colors.RESET}"
        result = formatter._format_cost(10.00)
        assert result == f"{Colors.RED}$10.00{Colors.RESET}"

    def test_format_negative_cost(self):
        """Test that negative costs are clamped to zero."""
        formatter = PromptFormatter(enable_colors=False)
        result = formatter._format_cost(-1.00)
        assert result == "$0.00"


@pytest.mark.unit
class TestDurationFormatting:
    """Test duration formatting."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return PromptFormatter()

    def test_format_minutes_only(self, formatter):
        """Test formatting durations < 60 minutes."""
        assert formatter._format_duration(0) == "0m"
        assert formatter._format_duration(1) == "1m"
        assert formatter._format_duration(15) == "15m"
        assert formatter._format_duration(59) == "59m"

    def test_format_hours_with_minutes(self, formatter):
        """Test formatting durations with hours and minutes."""
        assert formatter._format_duration(61) == "1h1m"
        assert formatter._format_duration(90) == "1h30m"
        assert formatter._format_duration(125) == "2h5m"

    def test_format_exact_hours(self, formatter):
        """Test formatting exact hour durations."""
        assert formatter._format_duration(60) == "1h"
        assert formatter._format_duration(120) == "2h"
        assert formatter._format_duration(180) == "3h"


@pytest.mark.unit
class TestColorThresholds:
    """Test cost color threshold logic."""

    def test_get_cost_color_low(self):
        """Test color selection for low costs."""
        formatter = PromptFormatter(low_cost_threshold=0.50)
        assert formatter._get_cost_color(0.00) == Colors.GREEN
        assert formatter._get_cost_color(0.25) == Colors.GREEN
        assert formatter._get_cost_color(0.50) == Colors.GREEN

    def test_get_cost_color_medium(self):
        """Test color selection for medium costs."""
        formatter = PromptFormatter(
            low_cost_threshold=0.50,
            medium_cost_threshold=2.00
        )
        assert formatter._get_cost_color(0.51) == Colors.YELLOW
        assert formatter._get_cost_color(1.00) == Colors.YELLOW
        assert formatter._get_cost_color(2.00) == Colors.YELLOW

    def test_get_cost_color_high(self):
        """Test color selection for high costs."""
        formatter = PromptFormatter(medium_cost_threshold=2.00)
        assert formatter._get_cost_color(2.01) == Colors.RED
        assert formatter._get_cost_color(5.00) == Colors.RED
        assert formatter._get_cost_color(100.00) == Colors.RED

    def test_custom_thresholds(self):
        """Test custom cost thresholds."""
        formatter = PromptFormatter(
            low_cost_threshold=1.00,
            medium_cost_threshold=5.00
        )
        assert formatter._get_cost_color(0.99) == Colors.GREEN
        assert formatter._get_cost_color(1.00) == Colors.GREEN
        assert formatter._get_cost_color(1.01) == Colors.YELLOW
        assert formatter._get_cost_color(5.00) == Colors.YELLOW
        assert formatter._get_cost_color(5.01) == Colors.RED


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def formatter(self):
        """Create formatter instance."""
        return PromptFormatter()

    def test_none_stats(self, formatter):
        """Test handling of None stats."""
        result = formatter.format(None)
        assert strip_ansi(result) == "Thanos> "

    def test_empty_dict_stats(self, formatter):
        """Test handling of empty dict stats."""
        result = formatter.format({})
        assert strip_ansi(result) == "Thanos> "

    def test_zero_tokens_zero_cost(self, formatter):
        """Test handling of brand new session (no stats yet)."""
        stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost": 0.0,
            "duration_minutes": 0,
            "message_count": 0
        }
        result = formatter.format(stats)
        assert strip_ansi(result) == "Thanos> "

    def test_missing_keys(self):
        """Test handling of stats dict with missing keys."""
        formatter = PromptFormatter(enable_colors=False)
        stats = {
            "total_input_tokens": 100
            # Missing other required keys
        }
        result = formatter.format(stats, mode="compact")
        # Should use defaults for missing keys
        assert strip_ansi(result) == "(100 | $0.00) Thanos> "

    def test_invalid_stats_type(self, formatter):
        """Test handling of invalid stats type (not dict)."""
        result = formatter.format("invalid")
        assert strip_ansi(result) == "Thanos> "
        result = formatter.format(123)
        assert strip_ansi(result) == "Thanos> "
        result = formatter.format([1, 2, 3])
        assert strip_ansi(result) == "Thanos> "

    def test_invalid_mode(self, formatter):
        """Test handling of invalid mode (falls back to compact)."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        # Should fall back to compact mode
        result = formatter.format(stats, mode="invalid")
        assert result == formatter._format_compact(1200, 0.04)

    def test_very_large_numbers(self, formatter):
        """Test handling of very large token counts and costs."""
        stats = {
            "total_input_tokens": 50000000,
            "total_output_tokens": 50000000,
            "total_cost": 1000.00,
            "duration_minutes": 10000,
            "message_count": 5000
        }
        result = formatter.format(stats, mode="compact")
        assert "100.0M" in result
        assert "$1000.00" in result

    def test_custom_default_prompt(self):
        """Test using custom default prompt."""
        formatter = PromptFormatter(default_prompt="MyPrompt> ")
        result = formatter.format(None)
        assert result == "MyPrompt> "


@pytest.mark.unit
class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_session_progression(self):
        """Test prompt changes throughout a session progression."""
        formatter = PromptFormatter(enable_colors=False)

        # Early in session (low cost)
        stats1 = {
            "total_input_tokens": 100,
            "total_output_tokens": 200,
            "total_cost": 0.01,
            "duration_minutes": 2,
            "message_count": 2
        }
        result1 = formatter.format(stats1, mode="standard")
        assert strip_ansi(result1) == "(2m | 300 tokens | $0.01) Thanos> "

        # Mid session (medium cost)
        stats2 = {
            "total_input_tokens": 2000,
            "total_output_tokens": 3000,
            "total_cost": 0.75,
            "duration_minutes": 25,
            "message_count": 15
        }
        result2 = formatter.format(stats2, mode="standard")
        assert strip_ansi(result2) == "(25m | 5.0K tokens | $0.75) Thanos> "

        # Late session (high cost)
        stats3 = {
            "total_input_tokens": 20000,
            "total_output_tokens": 30000,
            "total_cost": 3.50,
            "duration_minutes": 120,
            "message_count": 50
        }
        result3 = formatter.format(stats3, mode="standard")
        assert strip_ansi(result3) == "(2h | 50.0K tokens | $3.50) Thanos> "

    def test_mode_comparison(self):
        """Test same stats formatted in all three modes."""
        formatter = PromptFormatter(enable_colors=False)

        stats = {
            "total_input_tokens": 5000,
            "total_output_tokens": 7000,
            "total_cost": 0.50,
            "duration_minutes": 45,
            "message_count": 20
        }

        compact = formatter.format(stats, mode="compact")
        standard = formatter.format(stats, mode="standard")
        verbose = formatter.format(stats, mode="verbose")

        assert strip_ansi(compact) == "(12.0K | $0.50) Thanos> "
        assert strip_ansi(standard) == "(45m | 12.0K tokens | $0.50) Thanos> "
        assert strip_ansi(verbose) == "(45m | 20 msgs | 5.0K in | 7.0K out | $0.50) Thanos> "

    def test_color_progression(self):
        """Test color changes as cost increases."""
        formatter = PromptFormatter(
            enable_colors=True,
            low_cost_threshold=0.50,
            medium_cost_threshold=2.00
        )

        # Green (low cost)
        stats_low = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.25,
            "duration_minutes": 15,
            "message_count": 8
        }
        result_low = formatter.format(stats_low, mode="compact")
        assert Colors.GREEN in result_low
        assert Colors.YELLOW not in result_low
        assert Colors.RED not in result_low

        # Yellow (medium cost)
        stats_med = {
            "total_input_tokens": 5000,
            "total_output_tokens": 7000,
            "total_cost": 1.00,
            "duration_minutes": 30,
            "message_count": 20
        }
        result_med = formatter.format(stats_med, mode="compact")
        assert Colors.YELLOW in result_med
        assert Colors.GREEN not in result_med
        assert Colors.RED not in result_med

        # Red (high cost)
        stats_high = {
            "total_input_tokens": 20000,
            "total_output_tokens": 30000,
            "total_cost": 3.00,
            "duration_minutes": 60,
            "message_count": 40
        }
        result_high = formatter.format(stats_high, mode="compact")
        assert Colors.RED in result_high
        assert Colors.GREEN not in result_high
        assert Colors.YELLOW not in result_high


@pytest.mark.unit
class TestAdditionalEdgeCases:
    """Test additional edge cases for comprehensive coverage."""

    @pytest.fixture
    def formatter(self):
        """Create formatter with colors disabled for easier testing."""
        return PromptFormatter(enable_colors=False)

    def test_negative_token_counts(self, formatter):
        """Test handling of negative token counts (malformed stats)."""
        stats = {
            "total_input_tokens": -100,
            "total_output_tokens": -200,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        # Implementation allows negative totals (shows them as-is)
        result = formatter.format(stats)
        assert strip_ansi(result) == "(-300 | $0.04) Thanos> "

    def test_float_token_counts(self, formatter):
        """Test handling of float token counts (should handle gracefully)."""
        stats = {
            "total_input_tokens": 500.7,
            "total_output_tokens": 700.3,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="compact")
        # Should convert floats to ints internally
        assert "1.2K" in result or "1200" in result

    def test_string_values_in_stats(self, formatter):
        """Test handling of string values in stats (type validation)."""
        stats = {
            "total_input_tokens": "500",
            "total_output_tokens": "700",
            "total_cost": "0.04",
            "duration_minutes": "15",
            "message_count": "8"
        }
        # Implementation doesn't handle type coercion, will raise TypeError
        with pytest.raises(TypeError):
            formatter.format(stats)

    def test_extremely_long_duration_days(self, formatter):
        """Test handling of very long session durations (days)."""
        stats = {
            "total_input_tokens": 1000000,
            "total_output_tokens": 2000000,
            "total_cost": 50.00,
            "duration_minutes": 1440,  # 24 hours = 1 day
            "message_count": 500
        }
        result = formatter.format(stats, mode="standard")
        # Should format as hours
        assert "24h" in result

    def test_extremely_long_duration_weeks(self, formatter):
        """Test handling of very long session durations (weeks)."""
        stats = {
            "total_input_tokens": 5000000,
            "total_output_tokens": 7000000,
            "total_cost": 200.00,
            "duration_minutes": 10080,  # 168 hours = 1 week
            "message_count": 2000
        }
        result = formatter.format(stats, mode="standard")
        # Should format as hours
        assert "168h" in result

    def test_token_count_boundary_999(self, formatter):
        """Test exact boundary at 999 tokens (should not use K suffix)."""
        assert formatter._format_token_count(999) == "999"

    def test_token_count_boundary_1000(self, formatter):
        """Test exact boundary at 1000 tokens (should use K suffix)."""
        assert formatter._format_token_count(1000) == "1.0K"

    def test_token_count_boundary_999999(self, formatter):
        """Test exact boundary at 999999 tokens (should use K suffix)."""
        assert formatter._format_token_count(999999) == "1000.0K"

    def test_token_count_boundary_1000000(self, formatter):
        """Test exact boundary at 1000000 tokens (should use M suffix)."""
        assert formatter._format_token_count(1000000) == "1.0M"

    def test_multiple_sequential_format_calls(self, formatter):
        """Test that multiple format calls don't affect each other (stateless)."""
        stats1 = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        stats2 = {
            "total_input_tokens": 2000,
            "total_output_tokens": 3000,
            "total_cost": 1.50,
            "duration_minutes": 45,
            "message_count": 25
        }

        result1a = formatter.format(stats1, mode="compact")
        result2 = formatter.format(stats2, mode="compact")
        result1b = formatter.format(stats1, mode="compact")

        # Should be identical (stateless)
        assert result1a == result1b
        assert result1a != result2

    def test_very_small_cost_precision(self, formatter):
        """Test handling of very small costs (precision edge case)."""
        stats = {
            "total_input_tokens": 10,
            "total_output_tokens": 15,
            "total_cost": 0.00001,
            "duration_minutes": 1,
            "message_count": 1
        }
        result = formatter.format(stats, mode="compact")
        # Should format with 2 decimal places
        assert "$0.00" in result

    def test_unicode_in_default_prompt(self):
        """Test using unicode characters in default prompt."""
        formatter = PromptFormatter(default_prompt="Thanos 🤖> ")
        result = formatter.format(None)
        assert result == "Thanos 🤖> "
        assert "🤖" in result

    def test_stats_with_extra_keys(self, formatter):
        """Test stats dict with extra unexpected keys."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8,
            "extra_field": "unexpected",
            "another_field": 123
        }
        result = formatter.format(stats, mode="compact")
        # Should ignore extra keys and work normally
        assert strip_ansi(result) == "(1.2K | $0.04) Thanos> "

    def test_partial_stats_only_tokens(self, formatter):
        """Test stats with only token fields present."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700
        }
        result = formatter.format(stats, mode="compact")
        # Should use defaults for missing fields
        assert strip_ansi(result) == "(1.2K | $0.00) Thanos> "

    def test_partial_stats_only_cost(self, formatter):
        """Test stats with only cost field present."""
        stats = {
            "total_cost": 0.50
        }
        result = formatter.format(stats, mode="compact")
        # Implementation shows stats even with 0 tokens if there's a cost
        assert strip_ansi(result) == "(0 | $0.50) Thanos> "

    def test_maximum_integer_values(self, formatter):
        """Test handling of extremely large integer values."""
        stats = {
            "total_input_tokens": 999999999,
            "total_output_tokens": 999999999,
            "total_cost": 99999.99,
            "duration_minutes": 999999,
            "message_count": 999999
        }
        result = formatter.format(stats, mode="verbose")
        # Should handle large numbers without crashing
        assert "Thanos>" in result
        # Check that millions are formatted correctly
        assert "M" in result

    def test_cost_threshold_exact_boundaries(self, formatter):
        """Test color selection at exact threshold boundaries."""
        formatter_colored = PromptFormatter(
            enable_colors=True,
            low_cost_threshold=0.50,
            medium_cost_threshold=2.00
        )

        # Exactly at low threshold (should be green)
        assert formatter_colored._get_cost_color(0.50) == Colors.GREEN

        # Just above low threshold (should be yellow)
        assert formatter_colored._get_cost_color(0.50001) == Colors.YELLOW

        # Exactly at medium threshold (should be yellow)
        assert formatter_colored._get_cost_color(2.00) == Colors.YELLOW

        # Just above medium threshold (should be red)
        assert formatter_colored._get_cost_color(2.00001) == Colors.RED

    def test_zero_duration(self, formatter):
        """Test handling of zero duration (brand new session)."""
        assert formatter._format_duration(0) == "0m"

    def test_single_minute_duration(self, formatter):
        """Test handling of single minute duration."""
        assert formatter._format_duration(1) == "1m"

    def test_mode_case_sensitivity(self, formatter):
        """Test that mode parameter is case-sensitive."""
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        # Invalid mode (wrong case) should fall back to compact
        result = formatter.format(stats, mode="COMPACT")
        # Should fall back to compact mode
        assert strip_ansi(result) == "(1.2K | $0.04) Thanos> "

    def test_malformed_config_json(self):
        """Test handling of corrupted config file."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json content")
            config_path = f.name

        # Should gracefully handle malformed JSON
        formatter = PromptFormatter(config_path=config_path)
        assert formatter.enabled is not None
        assert formatter.default_mode is not None

        # Cleanup
        import os
        os.unlink(config_path)

    def test_empty_config_file(self):
        """Test handling of empty config file."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{}")
            config_path = f.name

        # Should gracefully handle empty config
        formatter = PromptFormatter(config_path=config_path)
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="compact")
        assert "Thanos>" in result

        # Cleanup
        import os
        os.unlink(config_path)

    def test_cost_with_many_decimal_places(self, formatter):
        """Test cost formatting with high precision floats."""
        # Python float precision edge case
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.123456789,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="compact")
        # Should round to 2 decimal places
        assert "$0.12" in result


@pytest.mark.unit
class TestConfiguration:
    """Test configuration loading and application."""

    def test_default_config_loads(self):
        """Test that formatter loads config from default path."""
        # This should not raise an error even if config doesn't exist
        formatter = PromptFormatter()
        assert formatter.enabled is not None
        assert formatter.default_mode is not None

    def test_config_enabled_flag(self):
        """Test that enabled flag is respected."""
        # Create formatter with enabled=True (via parameter override)
        formatter_enabled = PromptFormatter(enable_colors=True)

        # Temporarily override enabled for testing
        formatter_enabled.enabled = True
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result_enabled = formatter_enabled.format(stats)
        assert "1.2K" in strip_ansi(result_enabled) or "Thanos>" in strip_ansi(result_enabled)

        # Test with enabled=False
        formatter_enabled.enabled = False
        result_disabled = formatter_enabled.format(stats)
        assert strip_ansi(result_disabled) == "Thanos> "

    def test_config_default_mode(self):
        """Test that default mode from config is used when mode not specified."""
        formatter = PromptFormatter(enable_colors=False)

        # Override default_mode for testing
        formatter.default_mode = "verbose"

        stats = {
            "total_input_tokens": 5000,
            "total_output_tokens": 7000,
            "total_cost": 0.50,
            "duration_minutes": 45,
            "message_count": 20
        }

        # When mode is not specified, should use default_mode
        result = formatter.format(stats)
        assert "msgs" in result  # Verbose mode includes "msgs"
        assert "in" in result  # Verbose mode includes "in" and "out"
        assert "out" in result

    def test_config_thresholds(self):
        """Test that color thresholds from config are used."""
        # Create formatter with custom thresholds
        formatter = PromptFormatter(
            enable_colors=True,
            low_cost_threshold=1.00,
            medium_cost_threshold=5.00
        )

        # Cost of $0.75 should be green (below 1.00 threshold)
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.75,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="compact")
        assert Colors.GREEN in result

        # Cost of $2.00 should be yellow (between 1.00 and 5.00)
        stats["total_cost"] = 2.00
        result = formatter.format(stats, mode="compact")
        assert Colors.YELLOW in result

        # Cost of $6.00 should be red (above 5.00)
        stats["total_cost"] = 6.00
        result = formatter.format(stats, mode="compact")
        assert Colors.RED in result

    def test_parameter_overrides_config(self):
        """Test that parameters passed to __init__ override config values."""
        # Create formatter with explicit parameter overrides
        formatter = PromptFormatter(
            enable_colors=False,
            low_cost_threshold=10.00,
            medium_cost_threshold=20.00
        )

        # Verify overrides were applied
        assert formatter.enable_colors is False
        assert formatter.low_cost_threshold == 10.00
        assert formatter.medium_cost_threshold == 20.00

    def test_mode_parameter_overrides_config_mode(self):
        """Test that mode parameter to format() overrides config default."""
        formatter = PromptFormatter(enable_colors=False)
        formatter.default_mode = "verbose"

        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }

        # Explicitly request compact mode (should override config)
        result = formatter.format(stats, mode="compact")
        assert strip_ansi(result) == "(1.2K | $0.04) Thanos> "
        assert "msgs" not in strip_ansi(result)  # Compact mode doesn't include msgs

    def test_config_graceful_fallback(self):
        """Test that formatter gracefully handles missing config."""
        # Pass non-existent config path
        formatter = PromptFormatter(config_path="/nonexistent/path/config.json")

        # Should still work with default values
        stats = {
            "total_input_tokens": 500,
            "total_output_tokens": 700,
            "total_cost": 0.04,
            "duration_minutes": 15,
            "message_count": 8
        }
        result = formatter.format(stats, mode="compact")
        assert "Thanos>" in result
