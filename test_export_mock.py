#!/usr/bin/env python3
"""
Mock test for pa:export command CSV functionality
Tests the CSV export functions without requiring database connection
"""

import sys
import csv
import json
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import export functions
from commands.pa.export import (
    export_to_csv,
    export_to_json,
    format_value_for_csv,
    format_file_size,
)


def create_mock_data():
    """Create mock data for testing"""
    return {
        "tasks": [
            {
                "id": 1,
                "title": "Test Task 1",
                "description": "This is a test task",
                "status": "active",
                "client_id": 1,
                "client_name": "Test Client",
                "sort_order": 1,
                "created_at": datetime(2026, 1, 10, 10, 0, 0),
                "completed_at": None,
                "updated_at": datetime(2026, 1, 12, 10, 0, 0),
                "effort_estimate": "medium",
                "points_final": 3,
                "points_ai_guess": 3,
            },
            {
                "id": 2,
                "title": "Test Task 2",
                "description": "Another test task with special chars: commas, \"quotes\"",
                "status": "done",
                "client_id": 1,
                "client_name": "Test Client",
                "sort_order": 2,
                "created_at": datetime(2026, 1, 9, 10, 0, 0),
                "completed_at": datetime(2026, 1, 11, 15, 30, 0),
                "updated_at": datetime(2026, 1, 11, 15, 30, 0),
                "effort_estimate": "small",
                "points_final": 1,
                "points_ai_guess": 2,
            },
        ],
        "habits": [
            {
                "id": 1,
                "title": "Morning Exercise",
                "description": "30 min workout",
                "is_active": True,
                "sort_order": 1,
                "current_streak": 5,
                "longest_streak": 10,
                "last_completed_date": datetime(2026, 1, 12, 6, 0, 0),
                "created_at": datetime(2026, 1, 1, 10, 0, 0),
                "updated_at": datetime(2026, 1, 12, 6, 0, 0),
                "last_completion": datetime(2026, 1, 12, 6, 0, 0),
            },
            {
                "id": 2,
                "title": "Reading",
                "description": "Read 20 pages",
                "is_active": True,
                "sort_order": 2,
                "current_streak": 3,
                "longest_streak": 15,
                "last_completed_date": datetime(2026, 1, 11, 22, 0, 0),
                "created_at": datetime(2026, 1, 1, 10, 0, 0),
                "updated_at": datetime(2026, 1, 11, 22, 0, 0),
                "last_completion": datetime(2026, 1, 11, 22, 0, 0),
            },
        ],
        "goals": [
            {
                "date": datetime(2026, 1, 12, 0, 0, 0),
                "current_streak": 5,
                "earned_points": 15,
                "target_points": 18,
                "goal_met": False,
            },
            {
                "date": datetime(2026, 1, 11, 0, 0, 0),
                "current_streak": 4,
                "earned_points": 20,
                "target_points": 18,
                "goal_met": True,
            },
        ],
        "metrics": {
            "completed_count": 5,
            "earned_points": 15,
            "target_points": 18,
            "minimum_points": 12,
            "progress_percentage": 83.3,
            "streak": 5,
            "active_count": 3,
            "queued_count": 2,
            "goal_met": True,
            "target_met": False,
        },
    }


def test_csv_export():
    """Test CSV export functionality"""
    print("=" * 60)
    print("MOCK DATA CSV EXPORT TEST")
    print("=" * 60)
    print()

    # Create test output directory
    output_dir = Path("./test_exports")
    output_dir.mkdir(exist_ok=True)

    # Create mock data
    mock_data = create_mock_data()

    print("✓ Created mock data")
    print(f"  - {len(mock_data['tasks'])} tasks")
    print(f"  - {len(mock_data['habits'])} habits")
    print(f"  - {len(mock_data['goals'])} goals")
    print(f"  - 1 metrics record")
    print()

    # Test CSV export
    print("Testing CSV export...")
    exported_files = export_to_csv(mock_data, "all", output_dir)
    print()

    # Verify files were created
    print("Verification Results:")
    print("-" * 60)

    all_passed = True

    for data_type, filepath in exported_files:
        print(f"\n{data_type.upper()}.CSV:")

        # Check file exists
        if not filepath.exists():
            print(f"  ❌ File does not exist: {filepath}")
            all_passed = False
            continue

        # Get file size
        file_size = filepath.stat().st_size
        print(f"  ✓ File created: {format_file_size(file_size)}")

        # Read and validate CSV
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                print(f"  ✓ Valid CSV format")
                print(f"  ✓ {len(rows)} rows")
                print(f"  ✓ {len(reader.fieldnames)} columns: {', '.join(reader.fieldnames[:5])}...")

                # Check for required columns
                if data_type == "tasks":
                    required = ["id", "title", "status", "created_at"]
                    for col in required:
                        if col not in reader.fieldnames:
                            print(f"  ❌ Missing column: {col}")
                            all_passed = False
                        else:
                            print(f"  ✓ Has column: {col}")

                # Check datetime formatting
                if rows and "created_at" in rows[0]:
                    date_val = rows[0]["created_at"]
                    if "T" in date_val or "-" in date_val:
                        print(f"  ✓ Datetime formatted correctly: {date_val[:19]}")
                    else:
                        print(f"  ⚠️  Datetime format unexpected: {date_val}")

                # Check for data integrity
                if rows:
                    first_row = rows[0]
                    print(f"  ✓ Sample data: {first_row.get('title', first_row.get('date', 'N/A'))}")

        except Exception as e:
            print(f"  ❌ Error reading CSV: {e}")
            all_passed = False

    print()
    print("-" * 60)
    if all_passed:
        print("✅ All CSV export tests PASSED")
    else:
        print("❌ Some CSV export tests FAILED")
    print("-" * 60)

    return all_passed


def test_json_export():
    """Test JSON export functionality"""
    print()
    print("=" * 60)
    print("MOCK DATA JSON EXPORT TEST")
    print("=" * 60)
    print()

    # Create test output directory
    output_dir = Path("./test_exports")
    output_dir.mkdir(exist_ok=True)

    # Create mock data
    mock_data = create_mock_data()

    print("✓ Created mock data")
    print()

    # Test JSON export
    print("Testing JSON export...")
    exported_files = export_to_json(mock_data, "all", output_dir)
    print()

    # Verify files were created
    print("Verification Results:")
    print("-" * 60)

    all_passed = True

    for data_type, filepath in exported_files:
        print(f"\n{data_type.upper()}.JSON:")

        # Check file exists
        if not filepath.exists():
            print(f"  ❌ File does not exist: {filepath}")
            all_passed = False
            continue

        # Get file size
        file_size = filepath.stat().st_size
        print(f"  ✓ File created: {format_file_size(file_size)}")

        # Read and validate JSON
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

                print(f"  ✓ Valid JSON format")

                # Check data structure
                if isinstance(data, list):
                    print(f"  ✓ {len(data)} records")
                    if data:
                        first_item = data[0]
                        if isinstance(first_item, dict):
                            print(f"  ✓ {len(first_item)} fields: {', '.join(list(first_item.keys())[:5])}...")
                elif isinstance(data, dict):
                    print(f"  ✓ 1 record (dict)")
                    print(f"  ✓ {len(data)} fields: {', '.join(list(data.keys())[:5])}...")

                # Check datetime formatting
                if isinstance(data, list) and data:
                    first = data[0]
                    if isinstance(first, dict):
                        for key, val in first.items():
                            if "created_at" in key or "date" in key:
                                if isinstance(val, str) and "T" in val:
                                    print(f"  ✓ Datetime formatted correctly: {val[:19]}")
                                    break

        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON: {e}")
            all_passed = False
        except Exception as e:
            print(f"  ❌ Error reading JSON: {e}")
            all_passed = False

    print()
    print("-" * 60)
    if all_passed:
        print("✅ All JSON export tests PASSED")
    else:
        print("❌ Some JSON export tests FAILED")
    print("-" * 60)

    return all_passed


if __name__ == "__main__":
    print("\n🧪 Running Mock Data Export Tests\n")

    csv_passed = test_csv_export()
    json_passed = test_json_export()

    print("\n" + "=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    if csv_passed and json_passed:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
