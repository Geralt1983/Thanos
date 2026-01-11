"""
Unit tests for spinner utilities.

Tests cover:
- TTY detection and behavior
- Context manager lifecycle (__enter__/__exit__)
- Error handling during spinner operations
- Success/failure indicators
- Manual start/stop control
- Text update functionality
- Factory functions for different spinner types
- Graceful fallback when yaspin unavailable
"""

import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

# Mock yaspin module before importing spinner
mock_yaspin_module = MagicMock()
mock_spinners = MagicMock()
mock_spinners.dots = "dots"
mock_yaspin_module.yaspin = MagicMock()
mock_yaspin_module.spinners = MagicMock()
mock_yaspin_module.spinners.Spinners = mock_spinners

sys.modules['yaspin'] = mock_yaspin_module
sys.modules['yaspin.spinners'] = mock_yaspin_module.spinners

from Tools.spinner import (
    ThanosSpinner,
    command_spinner,
    chat_spinner,
    routing_spinner,
    SPINNER_AVAILABLE,
)


@pytest.mark.unit
class TestSpinnerInitialization:
    """Test ThanosSpinner initialization."""

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters."""
        spinner = ThanosSpinner()
        assert spinner.text == "Processing..."
        assert spinner.color == "cyan"
        assert spinner.spinner_type == "dots"
        assert spinner._spinner is None
        assert not spinner._fallback_printed

    def test_initialization_with_custom_params(self):
        """Test initialization with custom parameters."""
        spinner = ThanosSpinner(
            text="Custom message",
            color="magenta",
            spinner_type="line"
        )
        assert spinner.text == "Custom message"
        assert spinner.color == "magenta"
        assert spinner.spinner_type == "line"

    @patch("sys.stdout.isatty")
    def test_tty_detection_true(self, mock_isatty):
        """Test TTY detection when stdout is a TTY."""
        mock_isatty.return_value = True
        spinner = ThanosSpinner()
        assert spinner._is_tty is True

    @patch("sys.stdout.isatty")
    def test_tty_detection_false(self, mock_isatty):
        """Test TTY detection when stdout is not a TTY."""
        mock_isatty.return_value = False
        spinner = ThanosSpinner()
        assert spinner._is_tty is False


@pytest.mark.unit
class TestSpinnerContextManager:
    """Test ThanosSpinner context manager functionality."""

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_context_manager_success(self, mock_yaspin, mock_isatty):
        """Test context manager with successful operation."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")

        with spinner as s:
            assert s is spinner
            mock_spinner_instance.start.assert_called_once()

        # On successful exit, ok() should be called
        mock_spinner_instance.ok.assert_called_once()

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_context_manager_with_exception(self, mock_yaspin, mock_isatty):
        """Test context manager with exception during operation."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")

        try:
            with spinner:
                raise ValueError("Test error")
        except ValueError:
            pass

        # On exception, fail() should be called
        mock_spinner_instance.fail.assert_called_once()

    @patch("sys.stdout.isatty")
    def test_context_manager_non_tty(self, mock_isatty):
        """Test context manager in non-TTY environment."""
        mock_isatty.return_value = False

        spinner = ThanosSpinner("Test")

        with spinner as s:
            assert s is spinner
            # Should not create yaspin instance in non-TTY
            assert spinner._spinner is None


@pytest.mark.unit
class TestSpinnerManualControl:
    """Test manual start/stop control methods."""

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_manual_start(self, mock_yaspin, mock_isatty):
        """Test manual start method."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()

        mock_yaspin.assert_called_once()
        mock_spinner_instance.start.assert_called_once()

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_manual_stop(self, mock_yaspin, mock_isatty):
        """Test manual stop method."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.stop()

        mock_spinner_instance.stop.assert_called_once()
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_ok_with_default_symbol(self, mock_yaspin, mock_isatty):
        """Test ok() method with default success symbol."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.ok()

        mock_spinner_instance.ok.assert_called_once_with("✓")
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_ok_with_custom_symbol(self, mock_yaspin, mock_isatty):
        """Test ok() method with custom success symbol."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.ok("✅")

        mock_spinner_instance.ok.assert_called_once_with("✅")

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_fail_with_default_symbol(self, mock_yaspin, mock_isatty):
        """Test fail() method with default failure symbol."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.fail()

        mock_spinner_instance.fail.assert_called_once_with("✗")
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_fail_with_custom_symbol(self, mock_yaspin, mock_isatty):
        """Test fail() method with custom failure symbol."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.fail("❌")

        mock_spinner_instance.fail.assert_called_once_with("❌")


@pytest.mark.unit
class TestSpinnerTextUpdate:
    """Test spinner text update functionality."""

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_update_text(self, mock_yaspin, mock_isatty):
        """Test updating spinner text while running."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Initial text")
        spinner.start()
        spinner.update_text("Updated text")

        assert spinner.text == "Updated text"
        assert mock_spinner_instance.text == "Updated text"

    @patch("sys.stdout.isatty")
    def test_update_text_non_tty(self, mock_isatty):
        """Test updating text in non-TTY environment (should not error)."""
        mock_isatty.return_value = False

        spinner = ThanosSpinner("Initial text")
        spinner.start()
        spinner.update_text("Updated text")

        # Should update internal text even in non-TTY
        assert spinner.text == "Updated text"


@pytest.mark.unit
class TestSpinnerNonTTYBehavior:
    """Test spinner behavior in non-TTY environments."""

    @patch("sys.stdout.isatty")
    def test_start_in_non_tty(self, mock_isatty):
        """Test that spinner does not start in non-TTY environment."""
        mock_isatty.return_value = False

        spinner = ThanosSpinner("Test")
        spinner.start()

        assert spinner._spinner is None
        assert not spinner._fallback_printed

    @patch("sys.stdout.isatty")
    def test_stop_in_non_tty(self, mock_isatty):
        """Test stop in non-TTY environment (should not error)."""
        mock_isatty.return_value = False

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.stop()

        # Should complete without error
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    def test_ok_in_non_tty(self, mock_isatty):
        """Test ok() in non-TTY environment (should not error)."""
        mock_isatty.return_value = False

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.ok()

        # Should complete without error
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    def test_fail_in_non_tty(self, mock_isatty):
        """Test fail() in non-TTY environment (should not error)."""
        mock_isatty.return_value = False

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.fail()

        # Should complete without error
        assert spinner._spinner is None


@pytest.mark.unit
class TestSpinnerFallbackBehavior:
    """Test spinner fallback when yaspin is unavailable."""

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", False)
    @patch("builtins.print")
    def test_fallback_to_print_in_tty(self, mock_print, mock_isatty):
        """Test fallback to simple print when yaspin unavailable in TTY."""
        mock_isatty.return_value = True

        spinner = ThanosSpinner("Loading...")
        spinner.start()

        # Should print fallback message
        mock_print.assert_called_once_with("Loading...", end="", flush=True)
        assert spinner._fallback_printed is True

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", False)
    @patch("builtins.print")
    def test_fallback_ok(self, mock_print, mock_isatty):
        """Test fallback ok() method."""
        mock_isatty.return_value = True

        spinner = ThanosSpinner("Loading...")
        spinner.start()
        mock_print.reset_mock()
        spinner.ok()

        # Should clear and show success symbol
        mock_print.assert_called_once_with("\r✓", flush=True)
        assert not spinner._fallback_printed

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", False)
    @patch("builtins.print")
    def test_fallback_fail(self, mock_print, mock_isatty):
        """Test fallback fail() method."""
        mock_isatty.return_value = True

        spinner = ThanosSpinner("Loading...")
        spinner.start()
        mock_print.reset_mock()
        spinner.fail()

        # Should clear and show failure symbol
        mock_print.assert_called_once_with("\r✗", flush=True)
        assert not spinner._fallback_printed

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", False)
    @patch("builtins.print")
    def test_fallback_stop(self, mock_print, mock_isatty):
        """Test fallback stop() method."""
        mock_isatty.return_value = True

        spinner = ThanosSpinner("Loading...")
        spinner.start()
        mock_print.reset_mock()
        spinner.stop()

        # Should clear the fallback text
        assert mock_print.called
        assert not spinner._fallback_printed


@pytest.mark.unit
class TestSpinnerErrorHandling:
    """Test error handling in spinner operations."""

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    @patch("builtins.print")
    def test_start_error_handling(self, mock_print, mock_yaspin, mock_isatty):
        """Test error handling when yaspin.start() fails."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_spinner_instance.start.side_effect = Exception("Spinner error")
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()

        # Should print warning to stderr but not crash
        assert mock_print.called
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_stop_error_handling(self, mock_yaspin, mock_isatty):
        """Test error handling when yaspin.stop() fails."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_spinner_instance.stop.side_effect = Exception("Stop error")
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()

        # stop() should handle exception gracefully
        spinner.stop()
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_ok_error_handling(self, mock_yaspin, mock_isatty):
        """Test error handling when yaspin.ok() fails."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_spinner_instance.ok.side_effect = Exception("Ok error")
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()

        # ok() should fall back to stop()
        spinner.ok()
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_fail_error_handling(self, mock_yaspin, mock_isatty):
        """Test error handling when yaspin.fail() fails."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_spinner_instance.fail.side_effect = Exception("Fail error")
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()

        # fail() should fall back to stop()
        spinner.fail()
        assert spinner._spinner is None

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_update_text_error_handling(self, mock_yaspin, mock_isatty):
        """Test error handling when updating text fails."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        # Make text property raise exception
        type(mock_spinner_instance).text = property(
            lambda self: None,
            lambda self, value: (_ for _ in ()).throw(Exception("Update error"))
        )
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()

        # update_text() should handle exception gracefully
        spinner.update_text("New text")
        # Text should still be updated internally
        assert spinner.text == "New text"


@pytest.mark.unit
class TestFactoryFunctions:
    """Test convenience factory functions."""

    def test_command_spinner_creation(self):
        """Test command_spinner factory function."""
        spinner = command_spinner("daily")

        assert isinstance(spinner, ThanosSpinner)
        assert spinner.text == "Executing daily..."
        assert spinner.color == "cyan"
        assert spinner.spinner_type == "dots"

    def test_chat_spinner_without_agent(self):
        """Test chat_spinner factory without agent name."""
        spinner = chat_spinner()

        assert isinstance(spinner, ThanosSpinner)
        assert spinner.text == "Thinking..."
        assert spinner.color == "magenta"
        assert spinner.spinner_type == "dots"

    def test_chat_spinner_with_agent(self):
        """Test chat_spinner factory with agent name."""
        spinner = chat_spinner("Claude")

        assert isinstance(spinner, ThanosSpinner)
        assert spinner.text == "Thinking as Claude..."
        assert spinner.color == "magenta"
        assert spinner.spinner_type == "dots"

    def test_routing_spinner_creation(self):
        """Test routing_spinner factory function."""
        spinner = routing_spinner()

        assert isinstance(spinner, ThanosSpinner)
        assert spinner.text == "Routing..."
        assert spinner.color == "yellow"
        assert spinner.spinner_type == "dots"


@pytest.mark.unit
class TestSpinnerLifecycle:
    """Test complete spinner lifecycle scenarios."""

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_full_lifecycle_start_stop(self, mock_yaspin, mock_isatty):
        """Test full lifecycle: start -> stop."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Processing")
        spinner.start()
        spinner.stop()

        mock_spinner_instance.start.assert_called_once()
        mock_spinner_instance.stop.assert_called_once()

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_full_lifecycle_start_ok(self, mock_yaspin, mock_isatty):
        """Test full lifecycle: start -> ok."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Processing")
        spinner.start()
        spinner.ok()

        mock_spinner_instance.start.assert_called_once()
        mock_spinner_instance.ok.assert_called_once()

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_full_lifecycle_start_fail(self, mock_yaspin, mock_isatty):
        """Test full lifecycle: start -> fail."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Processing")
        spinner.start()
        spinner.fail()

        mock_spinner_instance.start.assert_called_once()
        mock_spinner_instance.fail.assert_called_once()

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_full_lifecycle_with_text_update(self, mock_yaspin, mock_isatty):
        """Test full lifecycle with text updates."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Initial")
        spinner.start()
        spinner.update_text("Updated")
        spinner.update_text("Final")
        spinner.ok()

        assert spinner.text == "Final"
        mock_spinner_instance.start.assert_called_once()
        mock_spinner_instance.ok.assert_called_once()

    @patch("sys.stdout.isatty")
    @patch("Tools.spinner.SPINNER_AVAILABLE", True)
    @patch("Tools.spinner.yaspin")
    def test_multiple_stop_calls_safe(self, mock_yaspin, mock_isatty):
        """Test that multiple stop calls are safe."""
        mock_isatty.return_value = True
        mock_spinner_instance = MagicMock()
        mock_yaspin.return_value = mock_spinner_instance

        spinner = ThanosSpinner("Test")
        spinner.start()
        spinner.stop()
        spinner.stop()  # Second stop should be safe

        # stop() should only be called once on the yaspin instance
        mock_spinner_instance.stop.assert_called_once()

    @patch("sys.stdout.isatty")
    def test_stop_without_start_safe(self, mock_isatty):
        """Test that stop without start is safe."""
        mock_isatty.return_value = True

        spinner = ThanosSpinner("Test")
        # Stop without starting - should not crash
        spinner.stop()
        spinner.ok()
        spinner.fail()
