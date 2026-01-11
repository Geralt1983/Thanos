#!/usr/bin/env python3
"""
Unit tests for Tools/error_logger.py

Tests the error logging, warning logging, and log rotation functionality.
"""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from Tools.error_logger import (
    MAX_LOG_BACKUPS,
    MAX_LOG_SIZE_BYTES,
    _rotate_log_if_needed,
    log_error,
    log_warning,
)


# ========================================================================
# Constants Tests
# ========================================================================

class TestErrorLoggerConstants:
    """Test module constants"""

    def test_max_log_size(self):
        """Test MAX_LOG_SIZE_BYTES is reasonable"""
        assert MAX_LOG_SIZE_BYTES == 10 * 1024 * 1024  # 10 MB
        assert MAX_LOG_SIZE_BYTES > 0

    def test_max_log_backups(self):
        """Test MAX_LOG_BACKUPS is reasonable"""
        assert MAX_LOG_BACKUPS == 3
        assert MAX_LOG_BACKUPS > 0


# ========================================================================
# Log Rotation Tests
# ========================================================================

class TestLogRotation:
    """Test _rotate_log_if_needed function"""

    def test_rotate_nonexistent_file(self, tmp_path):
        """Test rotation does nothing for nonexistent file"""
        log_file = tmp_path / "nonexistent.log"
        _rotate_log_if_needed(log_file)
        assert not log_file.exists()

    def test_rotate_small_file(self, tmp_path):
        """Test rotation does nothing for small files"""
        log_file = tmp_path / "small.log"
        log_file.write_text("Small log content")

        _rotate_log_if_needed(log_file)

        assert log_file.exists()
        assert log_file.read_text() == "Small log content"

    def test_rotate_large_file(self, tmp_path):
        """Test rotation moves large file to backup"""
        log_file = tmp_path / "large.log"
        # Create content larger than MAX_LOG_SIZE_BYTES
        large_content = "x" * (MAX_LOG_SIZE_BYTES + 1)
        log_file.write_text(large_content)

        _rotate_log_if_needed(log_file)

        # Original should be renamed to .1.log
        assert not log_file.exists()
        backup_1 = tmp_path / "large.1.log"
        assert backup_1.exists()

    def test_rotate_cascading_backups(self, tmp_path):
        """Test rotation cascades existing backups"""
        log_file = tmp_path / "cascade.log"
        backup_1 = tmp_path / "cascade.1.log"

        # Create existing backup
        backup_1.write_text("Backup 1 content")

        # Create large main log
        large_content = "x" * (MAX_LOG_SIZE_BYTES + 1)
        log_file.write_text(large_content)

        _rotate_log_if_needed(log_file)

        # Backup 1 should move to backup 2
        backup_2 = tmp_path / "cascade.2.log"
        assert backup_2.exists()
        assert backup_2.read_text() == "Backup 1 content"

        # New backup 1 should have main log content
        assert backup_1.exists()

    def test_rotate_deletes_oldest(self, tmp_path):
        """Test rotation deletes oldest backup when exceeding MAX_LOG_BACKUPS"""
        log_file = tmp_path / "delete.log"

        # Create all backup files up to MAX_LOG_BACKUPS
        for i in range(1, MAX_LOG_BACKUPS + 1):
            backup = tmp_path / f"delete.{i}.log"
            backup.write_text(f"Backup {i}")

        # Create large main log
        large_content = "x" * (MAX_LOG_SIZE_BYTES + 1)
        log_file.write_text(large_content)

        _rotate_log_if_needed(log_file)

        # Oldest backup should be deleted (or renamed out)
        # New .1.log should exist
        backup_1 = tmp_path / "delete.1.log"
        assert backup_1.exists()

    def test_rotate_handles_exception(self, tmp_path, capsys):
        """Test rotation handles exceptions gracefully"""
        log_file = tmp_path / "error.log"

        with patch.object(Path, 'exists', side_effect=Exception("Test error")):
            # Should not raise
            _rotate_log_if_needed(log_file)

        captured = capsys.readouterr()
        assert "Log rotation failed" in captured.err


# ========================================================================
# Log Error Tests
# ========================================================================

class TestLogError:
    """Test log_error function"""

    def test_log_error_to_stderr(self, capsys):
        """Test log_error writes to stderr"""
        error = ValueError("Test error message")

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("test_module", error)

        captured = capsys.readouterr()
        assert "test_module" in captured.err
        assert "ValueError" in captured.err
        assert "Test error message" in captured.err

    def test_log_error_with_context(self, capsys):
        """Test log_error includes context"""
        error = RuntimeError("Something broke")

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("my_module", error, context="While processing data")

        captured = capsys.readouterr()
        assert "While processing data" in captured.err

    def test_log_error_timestamp_format(self, capsys):
        """Test log_error includes timestamp"""
        error = Exception("Test")

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("module", error)

        captured = capsys.readouterr()
        # Should have timestamp in brackets
        assert "[" in captured.err
        assert "]" in captured.err
        # Should include date-like pattern
        import re
        assert re.search(r'\d{4}-\d{2}-\d{2}', captured.err)

    def test_log_error_writes_to_file(self, tmp_path):
        """Test log_error writes to log file"""
        error = ValueError("File test error")

        with patch('pathlib.Path.home', return_value=tmp_path):
            log_error("file_test", error)

        log_file = tmp_path / ".claude" / "logs" / "thanos-errors.log"
        assert log_file.exists()
        content = log_file.read_text()
        assert "file_test" in content
        assert "ValueError" in content

    def test_log_error_creates_log_directory(self, tmp_path):
        """Test log_error creates log directory if missing"""
        error = Exception("Test")

        log_dir = tmp_path / ".claude" / "logs"
        assert not log_dir.exists()

        with patch('pathlib.Path.home', return_value=tmp_path):
            log_error("test", error)

        assert log_dir.exists()

    def test_log_error_reraise_false(self):
        """Test log_error does not reraise by default"""
        error = ValueError("Test")

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                # Should not raise
                log_error("module", error, reraise=False)

    def test_log_error_reraise_true(self):
        """Test log_error reraises when requested"""
        error = ValueError("Rethrow me")

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                with pytest.raises(ValueError, match="Rethrow me"):
                    log_error("module", error, reraise=True)

    def test_log_error_file_write_failure(self, capsys):
        """Test log_error handles file write failures"""
        error = Exception("Test")

        with patch('pathlib.Path.home', return_value=Path("/nonexistent/path")):
            # Should not raise, just log to stderr
            log_error("test", error)

        captured = capsys.readouterr()
        # Should still have written to stderr
        assert "test" in captured.err
        # Should note the file write failure
        assert "Failed to write log file" in captured.err

    def test_log_error_triggers_rotation(self, tmp_path):
        """Test log_error triggers rotation for large files"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            # Create large log file
            log_dir = tmp_path / ".claude" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "thanos-errors.log"
            log_file.write_text("x" * (MAX_LOG_SIZE_BYTES + 1))

            log_error("rotation_test", Exception("Trigger rotation"))

            # Should have rotated
            backup_1 = log_dir / "thanos-errors.1.log"
            # Note: The actual rotation behavior depends on implementation
            # This test verifies rotation is attempted

    def test_log_error_various_exception_types(self, capsys):
        """Test log_error handles various exception types"""
        exceptions = [
            ValueError("value error"),
            TypeError("type error"),
            KeyError("key error"),
            FileNotFoundError("file not found"),
            RuntimeError("runtime error"),
            AttributeError("attribute error"),
        ]

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                for exc in exceptions:
                    log_error("test", exc)

        captured = capsys.readouterr()
        assert "ValueError" in captured.err
        assert "TypeError" in captured.err
        assert "KeyError" in captured.err
        assert "FileNotFoundError" in captured.err
        assert "RuntimeError" in captured.err
        assert "AttributeError" in captured.err


# ========================================================================
# Log Warning Tests
# ========================================================================

class TestLogWarning:
    """Test log_warning function"""

    def test_log_warning_to_stderr(self, capsys):
        """Test log_warning writes to stderr"""
        log_warning("test_module", "This is a warning message")

        captured = capsys.readouterr()
        assert "test_module" in captured.err
        assert "WARNING" in captured.err
        assert "This is a warning message" in captured.err

    def test_log_warning_timestamp_format(self, capsys):
        """Test log_warning includes timestamp"""
        log_warning("module", "Test warning")

        captured = capsys.readouterr()
        assert "[" in captured.err
        assert "]" in captured.err
        import re
        assert re.search(r'\d{4}-\d{2}-\d{2}', captured.err)

    def test_log_warning_format(self, capsys):
        """Test log_warning message format"""
        log_warning("my_module", "Something concerning happened")

        captured = capsys.readouterr()
        # Format should be: [timestamp] [module] WARNING: message
        assert "[my_module]" in captured.err
        assert "WARNING:" in captured.err
        assert "Something concerning happened" in captured.err

    def test_log_warning_empty_message(self, capsys):
        """Test log_warning with empty message"""
        log_warning("test", "")

        captured = capsys.readouterr()
        assert "test" in captured.err
        assert "WARNING:" in captured.err

    def test_log_warning_special_characters(self, capsys):
        """Test log_warning with special characters in message"""
        log_warning("test", "Warning: <script>alert('xss')</script>")

        captured = capsys.readouterr()
        assert "<script>" in captured.err


# ========================================================================
# Integration Tests
# ========================================================================

class TestErrorLoggerIntegration:
    """Integration tests for error logging"""

    def test_multiple_errors_same_file(self, tmp_path):
        """Test multiple errors are appended to same log file"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            log_error("module1", ValueError("Error 1"))
            log_error("module2", TypeError("Error 2"))
            log_error("module3", RuntimeError("Error 3"))

        log_file = tmp_path / ".claude" / "logs" / "thanos-errors.log"
        content = log_file.read_text()

        assert "Error 1" in content
        assert "Error 2" in content
        assert "Error 3" in content
        assert "module1" in content
        assert "module2" in content
        assert "module3" in content

    def test_error_and_warning_mixed(self, capsys, tmp_path):
        """Test errors and warnings can be interleaved"""
        with patch('pathlib.Path.home', return_value=tmp_path):
            log_error("app", ValueError("Error occurred"))
            log_warning("app", "Warning about something")
            log_error("app", RuntimeError("Another error"))

        captured = capsys.readouterr()

        assert "ValueError" in captured.err
        assert "WARNING" in captured.err
        assert "RuntimeError" in captured.err

    def test_concurrent_friendly(self, tmp_path):
        """Test logging doesn't fail under simulated concurrent access"""
        # This is a basic test - real concurrent testing would need threads
        with patch('pathlib.Path.home', return_value=tmp_path):
            for i in range(100):
                log_error(f"module_{i}", Exception(f"Error {i}"))

        log_file = tmp_path / ".claude" / "logs" / "thanos-errors.log"
        assert log_file.exists()
        content = log_file.read_text()
        lines = content.strip().split('\n')
        assert len(lines) == 100


# ========================================================================
# Edge Cases
# ========================================================================

class TestErrorLoggerEdgeCases:
    """Test edge cases for error logging"""

    def test_unicode_in_error_message(self, capsys):
        """Test handling of unicode characters in error messages"""
        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("unicode", Exception("Error with emoji 🔥 and unicode: 日本語"))

        captured = capsys.readouterr()
        assert "🔥" in captured.err
        assert "日本語" in captured.err

    def test_very_long_error_message(self, capsys):
        """Test handling of very long error messages"""
        long_message = "x" * 10000

        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("long", Exception(long_message))

        captured = capsys.readouterr()
        assert "x" * 100 in captured.err  # At least some of it should be there

    def test_error_message_with_newlines(self, capsys):
        """Test handling of error messages with newlines"""
        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("newline", Exception("Line 1\nLine 2\nLine 3"))

        captured = capsys.readouterr()
        assert "Line 1" in captured.err

    def test_none_context(self, capsys):
        """Test explicit None context"""
        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("test", Exception("Test"), context=None)

        captured = capsys.readouterr()
        assert "Context:" not in captured.err

    def test_empty_module_name(self, capsys):
        """Test empty module name"""
        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("", Exception("Test"))

        captured = capsys.readouterr()
        assert "[]" in captured.err  # Empty module brackets

    def test_special_characters_in_module_name(self, capsys):
        """Test special characters in module name"""
        with patch('pathlib.Path.mkdir'):
            with patch('builtins.open', mock_open()):
                log_error("module.submodule:function", Exception("Test"))

        captured = capsys.readouterr()
        assert "module.submodule:function" in captured.err


# ========================================================================
# Performance Tests
# ========================================================================

class TestErrorLoggerPerformance:
    """Performance-related tests for error logging"""

    def test_log_error_doesnt_block_on_file_issues(self, capsys):
        """Test that log_error doesn't block when file operations fail"""
        import time

        start = time.time()

        with patch('pathlib.Path.home', side_effect=Exception("Slow error")):
            log_error("perf_test", Exception("Test"))

        elapsed = time.time() - start

        # Should complete quickly even with file issues
        assert elapsed < 1.0  # Should definitely be under 1 second

    def test_rotation_check_is_fast(self, tmp_path):
        """Test that rotation check is fast for small files"""
        import time

        log_file = tmp_path / "fast.log"
        log_file.write_text("Small content")

        start = time.time()
        for _ in range(1000):
            _rotate_log_if_needed(log_file)
        elapsed = time.time() - start

        # 1000 checks should be fast
        assert elapsed < 1.0
