#!/usr/bin/env python3
"""
Manual test script for Thanos CLI spinner functionality.

This script demonstrates all spinner features:
1. Context manager (auto-start/stop with success)
2. Manual control (start/stop/ok/fail)
3. Different colors and spinner types
4. TTY detection behavior
5. Error handling

Run in a TTY terminal to see animated spinners.
Run with pipe/redirect to verify silent operation: python3 test_spinners_manual.py | cat
"""

import sys
import time
from Tools.spinner import ThanosSpinner, command_spinner, chat_spinner


def test_context_manager():
    """Test spinner with context manager (auto-start/stop)."""
    print("\n=== Test 1: Context Manager (Auto Success) ===")
    print("Expected: Spinner animates for 2s, then shows ✓")

    with ThanosSpinner("Processing with context manager...", color="cyan"):
        time.sleep(2)

    print("✅ Context manager test completed\n")


def test_manual_control_success():
    """Test spinner with manual start/stop and success."""
    print("\n=== Test 2: Manual Control (Success) ===")
    print("Expected: Spinner animates for 2s, then shows ✓")

    spinner = ThanosSpinner("Processing with manual control...", color="magenta")
    spinner.start()
    time.sleep(2)
    spinner.ok("✓ Done")

    print("✅ Manual success test completed\n")


def test_manual_control_failure():
    """Test spinner with manual start/stop and failure."""
    print("\n=== Test 3: Manual Control (Failure) ===")
    print("Expected: Spinner animates for 2s, then shows ✗")

    spinner = ThanosSpinner("Simulating failed operation...", color="yellow")
    spinner.start()
    time.sleep(2)
    spinner.fail("✗ Failed")

    print("✅ Manual failure test completed\n")


def test_spinner_types():
    """Test different spinner animation types."""
    print("\n=== Test 4: Different Spinner Types ===")

    spinner_types = [
        ("dots", "cyan", "Default dots spinner"),
        ("line", "magenta", "Line spinner"),
        ("arc", "yellow", "Arc spinner"),
    ]

    for spinner_type, color, description in spinner_types:
        print(f"Testing: {description}")
        spinner = ThanosSpinner(
            f"{description}...",
            color=color,
            spinner_type=spinner_type
        )
        spinner.start()
        time.sleep(1.5)
        spinner.ok()

    print("✅ Spinner types test completed\n")


def test_update_text():
    """Test updating spinner text while running."""
    print("\n=== Test 5: Update Spinner Text ===")
    print("Expected: Text changes every second")

    spinner = ThanosSpinner("Step 1: Starting...", color="cyan")
    spinner.start()

    for i in range(2, 5):
        time.sleep(1)
        spinner.update_text(f"Step {i}: Processing...")

    spinner.ok("✓ All steps completed")
    print("✅ Update text test completed\n")


def test_context_manager_with_exception():
    """Test context manager with exception (should show failure)."""
    print("\n=== Test 6: Context Manager with Exception ===")
    print("Expected: Spinner shows for 1s, then ✗ on exception")

    try:
        with ThanosSpinner("This will fail...", color="yellow"):
            time.sleep(1)
            raise ValueError("Simulated error")
    except ValueError:
        pass  # Expected exception

    print("✅ Exception handling test completed\n")


def test_convenience_functions():
    """Test the convenience wrapper functions."""
    print("\n=== Test 7: Convenience Functions ===")

    print("Testing command_spinner():")
    with command_spinner("pa:daily"):
        time.sleep(1.5)

    print("\nTesting chat_spinner() - no agent:")
    with chat_spinner():
        time.sleep(1.5)

    print("\nTesting chat_spinner() - with agent:")
    with chat_spinner("Ops"):
        time.sleep(1.5)

    print("✅ Convenience functions test completed\n")


def test_tty_detection():
    """Test TTY detection behavior."""
    print("\n=== Test 8: TTY Detection ===")

    is_tty = sys.stdout.isatty()
    print(f"sys.stdout.isatty(): {is_tty}")

    if is_tty:
        print("✅ Running in TTY - spinners should animate")
        print("   To test non-TTY: python3 test_spinners_manual.py | cat")
    else:
        print("✅ Running in non-TTY - spinners should be silent")
        print("   No ANSI codes should appear in output")

    print("\nTesting spinner in current mode:")
    spinner = ThanosSpinner("TTY detection test...", color="green")
    spinner.start()
    time.sleep(2)
    spinner.ok()

    print("✅ TTY detection test completed\n")


def test_streaming_mode_pattern():
    """Test the streaming mode pattern (manual stop before output)."""
    print("\n=== Test 9: Streaming Mode Pattern ===")
    print("Expected: Spinner stops before output starts streaming")

    spinner = ThanosSpinner("Waiting for stream...", color="cyan")
    spinner.start()
    time.sleep(1)

    # CRITICAL: Stop spinner before printing output
    spinner.stop()

    # Simulate streaming output
    for i in range(5):
        print(f"Stream chunk {i+1}")
        time.sleep(0.3)

    print("✅ Streaming mode test completed\n")


def main():
    """Run all spinner tests."""
    print("=" * 60)
    print("Thanos CLI Spinner - Manual Test Suite")
    print("=" * 60)
    print(f"\nTTY Status: {'✅ Interactive Terminal' if sys.stdout.isatty() else '⚠️  Non-TTY (pipe/redirect)'}")
    print("\nThis script will run through all spinner test scenarios.")
    print("Watch for animated spinners in TTY mode.")
    print("\n" + "=" * 60)

    try:
        # Run all tests
        test_context_manager()
        test_manual_control_success()
        test_manual_control_failure()
        test_spinner_types()
        test_update_text()
        test_context_manager_with_exception()
        test_convenience_functions()
        test_tty_detection()
        test_streaming_mode_pattern()

        # Summary
        print("=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("\nVerification Checklist:")
        print("  [ ] Spinners animated smoothly in TTY mode")
        print("  [ ] Success symbols (✓) displayed correctly")
        print("  [ ] Failure symbols (✗) displayed correctly")
        print("  [ ] Different colors (cyan, magenta, yellow) were visible")
        print("  [ ] Text updates worked during animation")
        print("  [ ] No output interference in pipe mode (test with | cat)")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
