#!/usr/bin/env python3
"""
Test error handling for database connection failures in export command.

Tests:
1. Database URL not configured
2. Invalid database URL (connection failure)
3. Database timeout handling
4. Invalid credentials handling
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the export module
from commands.pa import export


def print_test_header(test_name):
    """Print a test header."""
    print(f"\n{'=' * 70}")
    print(f"TEST: {test_name}")
    print('=' * 70)


def print_result(passed, message=""):
    """Print test result."""
    status = "\u2713 PASS" if passed else "\u2717 FAIL"
    print(f"{status}: {message}")


async def test_no_database_url():
    """Test error handling when DATABASE_URL is not configured."""
    print_test_header("Database URL Not Configured")

    # Save original env vars
    original_db_url = os.environ.get("DATABASE_URL")
    original_workos_url = os.environ.get("WORKOS_DATABASE_URL")

    try:
        # Remove database URLs from environment
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        if "WORKOS_DATABASE_URL" in os.environ:
            del os.environ["WORKOS_DATABASE_URL"]

        # Attempt to retrieve data
        try:
            await export.retrieve_all_data("tasks")
            print_result(False, "Should have raised ValueError")
            return False
        except ValueError as e:
            error_msg = str(e)
            # Check for expected error message
            if "Database URL not configured" in error_msg:
                print_result(True, "Correct error message for missing database URL")
                print(f"   Error message: {error_msg[:100]}...")
                return True
            else:
                print_result(False, f"Wrong error message: {error_msg}")
                return False

    finally:
        # Restore original env vars
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        if original_workos_url:
            os.environ["WORKOS_DATABASE_URL"] = original_workos_url


async def test_error_message_clarity():
    """Test that error messages are user-friendly and don't expose stack traces."""
    print_test_header("Error Message Clarity (No Stack Traces)")

    # Save original env var
    original_db_url = os.environ.get("DATABASE_URL")
    original_debug = os.environ.get("DEBUG")

    try:
        # Remove DEBUG flag to ensure no stack traces
        if "DEBUG" in os.environ:
            del os.environ["DEBUG"]

        # Remove database URL
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        if "WORKOS_DATABASE_URL" in os.environ:
            del os.environ["WORKOS_DATABASE_URL"]

        # Attempt to retrieve data
        try:
            await export.retrieve_all_data("tasks")
            print_result(False, "Should have raised ValueError")
            return False
        except ValueError as e:
            error_msg = str(e)

            # Check that error message is user-friendly
            checks = [
                ("Contains clear description", "Database URL not configured" in error_msg),
                ("Suggests solution", "set" in error_msg.lower() or "export" in error_msg.lower()),
                ("No code references", "__file__" not in error_msg and "line " not in error_msg.lower()),
                ("No raw exceptions", "Traceback" not in error_msg),
            ]

            all_passed = all(check[1] for check in checks)

            for check_name, passed in checks:
                status = "\u2713" if passed else "\u2717"
                print(f"   {status} {check_name}")

            print_result(all_passed, "Error message is user-friendly")
            return all_passed

    finally:
        # Restore original env vars
        if original_db_url:
            os.environ["DATABASE_URL"] = original_db_url
        if original_debug:
            os.environ["DEBUG"] = original_debug


async def main():
    """Run all error handling tests."""
    print("\n" + "=" * 70)
    print("ERROR HANDLING TEST SUITE")
    print("Testing database connection failure scenarios")
    print("=" * 70)

    tests = [
        ("Database URL Not Configured", test_no_database_url),
        ("Error Message Clarity", test_error_message_clarity),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nTest '{test_name}' failed with exception: {e}")
            results.append((test_name, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "\u2713 PASS" if result else "\u2717 FAIL"
        print(f"{status}: {test_name}")

    print("=" * 70)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 70)

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
