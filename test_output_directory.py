#!/usr/bin/env python3
"""
Test script for pa:export output directory handling.

Tests:
1. Default output directory (History/Exports/YYYY-MM-DD/)
2. Custom relative path directory
3. Custom absolute path directory
4. Directory creation when it doesn't exist
5. Files written to correct location
6. File overwrite behavior
7. Invalid directory path handling
"""

import sys
import os
import shutil
from pathlib import Path
from datetime import datetime
import asyncio

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock data for testing
MOCK_TASKS = [
    {
        "id": 1,
        "title": "Test Task 1",
        "description": "Test description",
        "status": "active",
        "client_id": None,
        "client_name": None,
        "sort_order": 1,
        "created_at": datetime.now(),
        "completed_at": None,
        "updated_at": datetime.now(),
        "effort_estimate": 3,
        "points_final": 3,
        "points_ai_guess": 3,
    }
]

MOCK_HABITS = [
    {
        "id": 1,
        "title": "Test Habit",
        "description": "Test habit description",
        "is_active": True,
        "sort_order": 1,
        "current_streak": 5,
        "longest_streak": 10,
        "last_completed_date": datetime.now().date(),
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "last_completion": datetime.now(),
    }
]


def print_test_header(test_name):
    """Print formatted test header."""
    print("\n" + "=" * 70)
    print(f"TEST: {test_name}")
    print("=" * 70)


def print_test_result(passed, message):
    """Print formatted test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")


def cleanup_test_directory(path):
    """Clean up test directory after test."""
    if path.exists() and path.is_dir():
        try:
            shutil.rmtree(path)
            print(f"   🧹 Cleaned up: {path}")
        except Exception as e:
            print(f"   ⚠️  Warning: Could not clean up {path}: {e}")


def test_default_output_directory():
    """Test 1: Default output directory is History/Exports/YYYY-MM-DD/"""
    print_test_header("Default Output Directory")

    from commands.pa.export import get_output_directory

    try:
        output_dir = get_output_directory(None)

        # Check that it's under History/Exports/
        expected_parent = Path(__file__).parent / "History" / "Exports"

        # Check structure
        is_correct_parent = expected_parent in output_dir.parents or output_dir.parent == expected_parent
        has_date_subdirectory = output_dir.name == datetime.now().strftime("%Y-%m-%d")

        print(f"   Output directory: {output_dir}")
        print(f"   Expected parent: {expected_parent}")
        print(f"   Date subdirectory: {output_dir.name}")

        if is_correct_parent and has_date_subdirectory:
            print_test_result(True, f"Default directory correct: {output_dir}")
            return True
        else:
            print_test_result(False, f"Directory structure incorrect")
            return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        return False


def test_custom_relative_path():
    """Test 2: Custom output directory with relative path"""
    print_test_header("Custom Relative Path")

    from commands.pa.export import get_output_directory

    test_dir = "./test_exports_relative"

    try:
        output_dir = get_output_directory(test_dir)

        # Check directory was created
        exists = output_dir.exists()
        is_dir = output_dir.is_dir()

        print(f"   Output directory: {output_dir}")
        print(f"   Exists: {exists}")
        print(f"   Is directory: {is_dir}")

        if exists and is_dir:
            print_test_result(True, f"Relative path works: {output_dir}")
            cleanup_test_directory(output_dir)
            return True
        else:
            print_test_result(False, "Directory not created properly")
            return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        return False


def test_custom_absolute_path():
    """Test 3: Custom output directory with absolute path"""
    print_test_header("Custom Absolute Path")

    from commands.pa.export import get_output_directory

    test_dir = Path(__file__).parent / "test_exports_absolute"
    test_dir_str = str(test_dir.absolute())

    try:
        output_dir = get_output_directory(test_dir_str)

        # Check directory was created
        exists = output_dir.exists()
        is_dir = output_dir.is_dir()
        is_absolute = output_dir.is_absolute()

        print(f"   Output directory: {output_dir}")
        print(f"   Exists: {exists}")
        print(f"   Is directory: {is_dir}")
        print(f"   Is absolute: {is_absolute}")

        if exists and is_dir:
            print_test_result(True, f"Absolute path works: {output_dir}")
            cleanup_test_directory(output_dir)
            return True
        else:
            print_test_result(False, "Directory not created properly")
            return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        return False


def test_nested_directory_creation():
    """Test 4: Directory creation when nested path doesn't exist"""
    print_test_header("Nested Directory Creation")

    from commands.pa.export import get_output_directory

    test_dir = "./test_exports/nested/deep/path"

    try:
        output_dir = get_output_directory(test_dir)

        # Check directory was created
        exists = output_dir.exists()
        is_dir = output_dir.is_dir()

        print(f"   Output directory: {output_dir}")
        print(f"   Exists: {exists}")
        print(f"   Is directory: {is_dir}")

        if exists and is_dir:
            print_test_result(True, f"Nested path created: {output_dir}")
            # Clean up the root test directory
            cleanup_test_directory(Path("./test_exports"))
            return True
        else:
            print_test_result(False, "Nested directory not created")
            return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        return False


def test_files_written_to_correct_location():
    """Test 5: Files are written to the correct location"""
    print_test_header("Files Written to Correct Location")

    from commands.pa.export import export_to_csv, export_to_json

    test_dir = Path("./test_exports_location")

    try:
        # Create test directory
        test_dir.mkdir(parents=True, exist_ok=True)

        # Prepare mock data
        data = {"tasks": MOCK_TASKS, "habits": MOCK_HABITS}

        # Export CSV
        csv_files = export_to_csv(data, "all", test_dir)

        # Export JSON
        json_files = export_to_json(data, "all", test_dir)

        # Check all files exist in the correct location
        all_correct = True
        for data_type, filepath in csv_files + json_files:
            file_exists = filepath.exists()
            in_correct_dir = filepath.parent == test_dir

            print(f"   File: {filepath.name}")
            print(f"      Exists: {file_exists}")
            print(f"      In correct dir: {in_correct_dir}")

            if not (file_exists and in_correct_dir):
                all_correct = False

        if all_correct and len(csv_files) > 0 and len(json_files) > 0:
            print_test_result(True, f"All files written to {test_dir}")
            cleanup_test_directory(test_dir)
            return True
        else:
            print_test_result(False, "Some files not in correct location")
            cleanup_test_directory(test_dir)
            return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        import traceback
        traceback.print_exc()
        cleanup_test_directory(test_dir)
        return False


def test_file_overwrite_behavior():
    """Test 6: File overwrite behavior (or warning)"""
    print_test_header("File Overwrite Behavior")

    from commands.pa.export import export_to_csv

    test_dir = Path("./test_exports_overwrite")

    try:
        # Create test directory
        test_dir.mkdir(parents=True, exist_ok=True)

        # Prepare mock data
        data = {"tasks": MOCK_TASKS}

        # First export
        print("   First export...")
        files1 = export_to_csv(data, "tasks", test_dir)
        filepath1 = files1[0][1]
        mtime1 = filepath1.stat().st_mtime
        size1 = filepath1.stat().st_size

        print(f"      Created: {filepath1.name}")
        print(f"      Size: {size1} bytes")
        print(f"      Modified: {mtime1}")

        # Wait a moment
        import time
        time.sleep(0.1)

        # Second export (should overwrite)
        print("   Second export...")
        files2 = export_to_csv(data, "tasks", test_dir)
        filepath2 = files2[0][1]
        mtime2 = filepath2.stat().st_mtime
        size2 = filepath2.stat().st_size

        print(f"      Created: {filepath2.name}")
        print(f"      Size: {size2} bytes")
        print(f"      Modified: {mtime2}")

        # Check if file was overwritten (modification time should be different)
        was_overwritten = mtime2 > mtime1

        if was_overwritten:
            print_test_result(True, "Files are overwritten without warning (current behavior)")
            print("   ⚠️  Note: No warning is given before overwrite")
            cleanup_test_directory(test_dir)
            return True
        else:
            print_test_result(False, "File modification time unchanged")
            cleanup_test_directory(test_dir)
            return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        cleanup_test_directory(test_dir)
        return False


def test_invalid_directory_path():
    """Test 7: Proper error message for invalid directory path"""
    print_test_header("Invalid Directory Path Error Handling")

    from commands.pa.export import get_output_directory

    # Test with a path that should fail (e.g., file path instead of directory)
    # Create a file first, then try to use it as a directory
    test_file = Path("./test_file.txt")

    try:
        # Create a file
        test_file.write_text("test")

        # Try to use file path as directory (should fail)
        try:
            output_dir = get_output_directory(str(test_file))
            # If we got here, it means it didn't fail as expected
            print_test_result(False, "Should have raised ValueError for file path")
            test_file.unlink()  # Clean up
            return False
        except ValueError as e:
            error_msg = str(e)
            print(f"   Caught ValueError: {error_msg}")
            has_helpful_msg = "Cannot create output directory" in error_msg

            if has_helpful_msg:
                print_test_result(True, "Proper error message for invalid path")
                test_file.unlink()  # Clean up
                return True
            else:
                print_test_result(False, f"Error message not helpful: {error_msg}")
                test_file.unlink()  # Clean up
                return False

    except Exception as e:
        print_test_result(False, f"Unexpected exception: {e}")
        if test_file.exists():
            test_file.unlink()
        return False


def test_execute_with_custom_output():
    """Test 8: Full execute() with custom output directory"""
    print_test_header("Full Execute with Custom Output")

    from commands.pa.export import execute

    test_dir = "./test_exports_execute"

    # Note: This test may fail if database is not available
    # We'll mock the data retrieval by patching
    try:
        # Import for mocking
        from unittest.mock import patch, AsyncMock

        # Mock retrieve_all_data to return test data
        async def mock_retrieve_all_data(data_type):
            return {"tasks": MOCK_TASKS, "habits": MOCK_HABITS}

        with patch('commands.pa.export.retrieve_all_data', new=mock_retrieve_all_data):
            result = execute(f"--format csv --type all --output {test_dir}")

            # Check if directory was created and contains files
            output_path = Path(test_dir)
            exists = output_path.exists()
            has_files = len(list(output_path.glob("*.csv"))) > 0 if exists else False

            print(f"   Output directory: {output_path}")
            print(f"   Exists: {exists}")
            print(f"   Has CSV files: {has_files}")

            if exists and has_files:
                print_test_result(True, "Execute with custom output works")
                cleanup_test_directory(output_path)
                return True
            else:
                print_test_result(False, "Execute did not create files in custom directory")
                cleanup_test_directory(output_path)
                return False

    except Exception as e:
        print_test_result(False, f"Exception: {e}")
        import traceback
        traceback.print_exc()
        cleanup_test_directory(Path(test_dir))
        return False


def run_all_tests():
    """Run all output directory tests."""
    print("\n" + "=" * 70)
    print("OUTPUT DIRECTORY HANDLING TEST SUITE")
    print("=" * 70)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tests = [
        test_default_output_directory,
        test_custom_relative_path,
        test_custom_absolute_path,
        test_nested_directory_creation,
        test_files_written_to_correct_location,
        test_file_overwrite_behavior,
        test_invalid_directory_path,
        test_execute_with_custom_output,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n❌ TEST CRASHED: {test.__name__}")
            print(f"   Exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test.__name__, False))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print("\n" + "-" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

    print("=" * 70 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
