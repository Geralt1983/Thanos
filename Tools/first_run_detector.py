import os
from pathlib import Path

# Define marker file location
THANOS_DIR = Path.home() / ".thanos"
SETUP_MARKER = THANOS_DIR / "setup_complete"

class FirstRunDetector:
    """Detects if Thanos setup has been completed."""

    def __init__(self):
        """Initialize the detector."""
        self.marker_path = SETUP_MARKER
        self.thanos_dir = THANOS_DIR

    def is_first_run(self) -> bool:
        """
        Check if this is the first run (setup not completed).

        Returns:
            bool: True if setup has not been completed, False otherwise
        """
        return not self.marker_path.exists()

    def mark_setup_complete(self) -> bool:
        """
        Mark setup as complete by creating the marker file.

        Returns:
            bool: True if successful, False if error occurred
        """
        try:
            # Ensure .thanos directory exists
            self.thanos_dir.mkdir(parents=True, exist_ok=True)

            # Create marker file
            self.marker_path.touch()
            return True

        except Exception as e:
            print(f"[FirstRunDetector] Error marking setup complete: {e}")
            return False

    def reset(self) -> bool:
        """
        Reset first-run state by removing the marker file.
        Useful for testing or re-running setup.

        Returns:
            bool: True if successful, False if error occurred
        """
        try:
            if self.marker_path.exists():
                self.marker_path.unlink()
            return True

        except Exception as e:
            print(f"[FirstRunDetector] Error resetting first-run state: {e}")
            return False

if __name__ == "__main__":
    import sys

    detector = FirstRunDetector()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "check":
            if detector.is_first_run():
                print("First run: YES (setup not completed)")
            else:
                print("First run: NO (setup already completed)")

        elif command == "mark":
            if detector.mark_setup_complete():
                print("Setup marked as complete.")
            else:
                print("Error marking setup complete.")

        elif command == "reset":
            if detector.reset():
                print("First-run state reset.")
            else:
                print("Error resetting first-run state.")

        else:
            print(f"Unknown command: {command}")
            print("Usage: python3 first_run_detector.py [check|mark|reset]")

    else:
        print("FirstRunDetector - Detect if Thanos setup has been completed")
        print("Usage: python3 first_run_detector.py [check|mark|reset]")
        print("  check  - Check if this is first run")
        print("  mark   - Mark setup as complete")
        print("  reset  - Reset first-run state")
