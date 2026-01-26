"""
Unit tests for Tools/first_run_detector.py

Tests the FirstRunDetector class which detects if Thanos setup has been completed
by checking for a marker file at ~/.thanos/setup_complete.
"""

import pytest
import os
from pathlib import Path
from Tools.first_run_detector import FirstRunDetector, SETUP_MARKER, THANOS_DIR


class TestFirstRunDetector:
    """Test suite for FirstRunDetector class."""

    def test_is_first_run_when_marker_missing(self, tmp_path, monkeypatch):
        """Test is_first_run returns True when marker doesn't exist"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        # Ensure marker doesn't exist
        if test_marker.exists():
            test_marker.unlink()

        # Verify is_first_run() returns True
        detector = FirstRunDetector()
        assert detector.is_first_run() is True
        assert detector.marker_path == test_marker

    def test_is_first_run_when_marker_exists(self, tmp_path, monkeypatch):
        """Test is_first_run returns False when marker exists"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        # Create marker file
        test_thanos_dir.mkdir(parents=True, exist_ok=True)
        test_marker.touch()

        # Verify is_first_run() returns False
        detector = FirstRunDetector()
        assert detector.is_first_run() is False

    def test_mark_setup_complete(self, tmp_path, monkeypatch):
        """Test mark_setup_complete creates marker file"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        detector = FirstRunDetector()

        # Verify marker created
        result = detector.mark_setup_complete()
        assert result is True
        assert test_marker.exists()

        # Verify directory created if needed
        assert test_thanos_dir.exists()
        assert test_thanos_dir.is_dir()

        # Verify returns True on success
        assert detector.mark_setup_complete() is True  # Should succeed even if already exists

    def test_mark_setup_complete_handles_errors(self, tmp_path, monkeypatch):
        """Test error handling when marker creation fails"""
        # Mock THANOS_DIR to point to a read-only location
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        detector = FirstRunDetector()

        # Create directory but make it read-only
        test_thanos_dir.mkdir(parents=True, exist_ok=True)
        test_thanos_dir.chmod(0o444)  # Read-only

        try:
            # Attempt to create marker should fail gracefully
            result = detector.mark_setup_complete()
            # On some systems this might succeed, on others it will fail
            # Either way, verify no exception is raised and returns boolean
            assert isinstance(result, bool)
        finally:
            # Restore permissions for cleanup
            test_thanos_dir.chmod(0o755)

    def test_reset(self, tmp_path, monkeypatch):
        """Test reset removes marker file"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        detector = FirstRunDetector()

        # Create marker
        test_thanos_dir.mkdir(parents=True, exist_ok=True)
        test_marker.touch()
        assert test_marker.exists()

        # Call reset()
        result = detector.reset()

        # Verify marker removed
        assert result is True
        assert not test_marker.exists()

    def test_reset_when_marker_missing(self, tmp_path, monkeypatch):
        """Test reset handles missing marker gracefully"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        detector = FirstRunDetector()

        # Ensure marker doesn't exist
        if test_marker.exists():
            test_marker.unlink()

        # Call reset()
        result = detector.reset()

        # Verify returns True (no error)
        assert result is True

    def test_marker_file_location(self):
        """Test marker file is at ~/.thanos/setup_complete"""
        detector = FirstRunDetector()
        expected_path = Path.home() / ".thanos" / "setup_complete"
        assert detector.marker_path == expected_path

    def test_thanos_dir_location(self):
        """Test thanos directory is at ~/.thanos"""
        detector = FirstRunDetector()
        expected_dir = Path.home() / ".thanos"
        assert detector.thanos_dir == expected_dir

    def test_repeated_mark_complete_is_safe(self, tmp_path, monkeypatch):
        """Test calling mark_setup_complete multiple times is safe"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        detector = FirstRunDetector()

        # Call multiple times
        assert detector.mark_setup_complete() is True
        assert detector.mark_setup_complete() is True
        assert detector.mark_setup_complete() is True

        # Should still be marked as complete
        assert not detector.is_first_run()

    def test_reset_then_first_run(self, tmp_path, monkeypatch):
        """Test reset followed by is_first_run works correctly"""
        # Mock THANOS_DIR and SETUP_MARKER to use tmp_path
        test_thanos_dir = tmp_path / ".thanos"
        test_marker = test_thanos_dir / "setup_complete"

        monkeypatch.setattr('Tools.first_run_detector.THANOS_DIR', test_thanos_dir)
        monkeypatch.setattr('Tools.first_run_detector.SETUP_MARKER', test_marker)

        detector = FirstRunDetector()

        # Mark as complete
        detector.mark_setup_complete()
        assert not detector.is_first_run()

        # Reset
        detector.reset()
        assert detector.is_first_run()

        # Mark complete again
        detector.mark_setup_complete()
        assert not detector.is_first_run()
