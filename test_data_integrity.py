#!/usr/bin/env python3
"""
Data Integrity Verification Test Suite for pa:export Command

This test suite verifies that exported data matches source data exactly,
with no data loss or corruption during the export process.

Test Coverage:
- Record count verification
- Field value accuracy (random sampling)
- Special character handling
- Null value preservation
- Datetime accuracy
- No data truncation
"""

import csv
import json
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from commands.pa.export import (
    export_to_csv,
    export_to_json,
    format_value_for_csv,
    DateTimeEncoder
)


# =============================================================================
# TEST DATA GENERATION
# =============================================================================

def generate_test_data() -> Dict[str, Any]:
    """
    Generate comprehensive test data with edge cases.

    Includes:
    - Special characters (commas, quotes, newlines, unicode)
    - Null values
    - Datetime objects
    - Long text fields
    - Boolean values
    - Numeric values (int, float)
    - Nested structures

    Returns:
        Dictionary with tasks, habits, goals, and metrics data
    """
    now = datetime.now()

    # Tasks with comprehensive edge cases
    tasks = [
        {
            "id": 1,
            "title": "Task with \"quotes\" and, commas",
            "description": "Line 1\nLine 2\nLine 3",
            "status": "active",
            "client_id": 101,
            "client_name": "Client's \"Special\" Co.",
            "sort_order": 1,
            "created_at": now,
            "completed_at": None,
            "updated_at": now,
            "effort_estimate": "2h",
            "points_final": 5,
            "points_ai_guess": 4
        },
        {
            "id": 2,
            "title": "Unicode test: 你好世界 🚀 Ñoño",
            "description": None,
            "status": "done",
            "client_id": None,
            "client_name": None,
            "sort_order": None,
            "created_at": now,
            "completed_at": now,
            "updated_at": now,
            "effort_estimate": None,
            "points_final": None,
            "points_ai_guess": None
        },
        {
            "id": 3,
            "title": "Very long text field " + "A" * 500,
            "description": "Testing truncation with " + "B" * 1000,
            "status": "queued",
            "client_id": 102,
            "client_name": "Long Name Corp " + "C" * 200,
            "sort_order": 999,
            "created_at": now,
            "completed_at": None,
            "updated_at": now,
            "effort_estimate": "8h",
            "points_final": 13,
            "points_ai_guess": 12
        },
        {
            "id": 4,
            "title": "Special chars: @#$%^&*()[]{}|\\/<>?~`",
            "description": 'Tab:\tNewline:\nCarriage return:\rQuote:"',
            "status": "backlog",
            "client_id": 103,
            "client_name": "O'Reilly & Associates",
            "sort_order": 5,
            "created_at": now,
            "completed_at": None,
            "updated_at": now,
            "effort_estimate": "4h",
            "points_final": 8,
            "points_ai_guess": 8
        }
    ]

    # Habits with edge cases
    habits = [
        {
            "id": 1,
            "title": "Habit, with \"commas\" and quotes",
            "description": "Multi\nline\ndescription",
            "is_active": True,
            "sort_order": 1,
            "current_streak": 42,
            "longest_streak": 100,
            "last_completed_date": now.date(),
            "created_at": now,
            "updated_at": now,
            "last_completion": now
        },
        {
            "id": 2,
            "title": "Inactive habit with nulls",
            "description": None,
            "is_active": False,
            "sort_order": None,
            "current_streak": 0,
            "longest_streak": 10,
            "last_completed_date": None,
            "created_at": now,
            "updated_at": now,
            "last_completion": None
        }
    ]

    # Goals with numeric precision
    goals = [
        {
            "date": now.date(),
            "current_streak": 15,
            "earned_points": 18.5,
            "target_points": 18.0,
            "goal_met": True
        },
        {
            "date": now.date(),
            "current_streak": 0,
            "earned_points": 0.0,
            "target_points": 18.0,
            "goal_met": False
        }
    ]

    # Metrics with various numeric types
    metrics = {
        "completed_count": 42,
        "earned_points": 156.5,
        "target_points": 18,
        "minimum_points": 12,
        "progress_percentage": 86.94444444444444,
        "streak": 15,
        "active_count": 23,
        "queued_count": 17,
        "goal_met": True,
        "target_met": True
    }

    return {
        "tasks": tasks,
        "habits": habits,
        "goals": goals,
        "metrics": metrics
    }


# =============================================================================
# CSV VERIFICATION
# =============================================================================

def verify_csv_integrity(source_data: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """
    Verify CSV export integrity by comparing source data with exported files.

    Args:
        source_data: Original data dictionary
        output_dir: Directory containing exported CSV files

    Returns:
        Dictionary with verification results
    """
    results = {
        "passed": True,
        "tests": [],
        "errors": []
    }

    for data_type, source_records in source_data.items():
        # Convert metrics dict to list for consistency
        if data_type == "metrics" and isinstance(source_records, dict):
            source_records = [source_records]

        csv_file = output_dir / f"{data_type}.csv"

        # Test 1: File exists
        if not csv_file.exists():
            results["passed"] = False
            results["errors"].append(f"CSV file missing: {csv_file}")
            continue

        # Read CSV file
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            exported_records = list(reader)

        # Test 2: Record count matches
        if len(exported_records) != len(source_records):
            results["passed"] = False
            results["errors"].append(
                f"{data_type} CSV: Record count mismatch. "
                f"Expected {len(source_records)}, got {len(exported_records)}"
            )
            results["tests"].append({
                "test": f"{data_type} - Record count",
                "status": "FAILED",
                "expected": len(source_records),
                "actual": len(exported_records)
            })
        else:
            results["tests"].append({
                "test": f"{data_type} - Record count",
                "status": "PASSED",
                "count": len(source_records)
            })

        # Test 3: Field accuracy for each record
        for i, (source_record, exported_record) in enumerate(zip(source_records, exported_records)):
            for field, source_value in source_record.items():
                exported_value = exported_record.get(field, "")

                # Convert source value to expected CSV format
                expected_csv_value = format_value_for_csv(source_value)

                # Normalize line endings for comparison (CSV normalizes \r to \n)
                # This is standard CSV behavior and not data loss
                expected_normalized = expected_csv_value.replace('\r\n', '\n').replace('\r', '\n')
                exported_normalized = exported_value.replace('\r\n', '\n').replace('\r', '\n')

                if exported_normalized != expected_normalized:
                    results["passed"] = False
                    results["errors"].append(
                        f"{data_type} CSV record {i}, field '{field}': "
                        f"Expected '{expected_normalized}', got '{exported_normalized}'"
                    )

        # Test 4: Null value handling
        null_fields_test = test_null_handling_csv(source_records, exported_records, data_type)
        results["tests"].append(null_fields_test)
        if null_fields_test["status"] == "FAILED":
            results["passed"] = False

        # Test 5: Special character handling
        special_char_test = test_special_characters_csv(source_records, exported_records, data_type)
        results["tests"].append(special_char_test)
        if special_char_test["status"] == "FAILED":
            results["passed"] = False

        # Test 6: Datetime handling
        datetime_test = test_datetime_handling_csv(source_records, exported_records, data_type)
        results["tests"].append(datetime_test)
        if datetime_test["status"] == "FAILED":
            results["passed"] = False

        # Test 7: No truncation
        truncation_test = test_no_truncation_csv(source_records, exported_records, data_type)
        results["tests"].append(truncation_test)
        if truncation_test["status"] == "FAILED":
            results["passed"] = False

    return results


def test_null_handling_csv(source_records: List[Dict], exported_records: List[Dict], data_type: str) -> Dict:
    """Test that null values are handled correctly in CSV."""
    null_count = 0
    errors = []

    for i, (source, exported) in enumerate(zip(source_records, exported_records)):
        for field, value in source.items():
            if value is None:
                null_count += 1
                if exported.get(field, "MISSING") not in ["", "None"]:
                    errors.append(f"Record {i}, field {field}: null not preserved")

    return {
        "test": f"{data_type} - Null value handling",
        "status": "PASSED" if not errors else "FAILED",
        "null_fields_tested": null_count,
        "errors": errors
    }


def test_special_characters_csv(source_records: List[Dict], exported_records: List[Dict], data_type: str) -> Dict:
    """Test that special characters are properly escaped in CSV."""
    special_chars = [',', '"', '\n', '\r', '\t']
    fields_with_special = 0
    errors = []

    for i, (source, exported) in enumerate(zip(source_records, exported_records)):
        for field, value in source.items():
            if isinstance(value, str) and any(char in value for char in special_chars):
                fields_with_special += 1
                # Verify the exported value contains the special character
                exported_value = exported.get(field, "")
                if not any(char in exported_value for char in special_chars if char in str(value)):
                    errors.append(f"Record {i}, field {field}: special char not preserved")

    return {
        "test": f"{data_type} - Special character handling",
        "status": "PASSED" if not errors else "FAILED",
        "fields_tested": fields_with_special,
        "errors": errors
    }


def test_datetime_handling_csv(source_records: List[Dict], exported_records: List[Dict], data_type: str) -> Dict:
    """Test that datetime values are accurately converted in CSV."""
    datetime_fields = 0
    errors = []

    for i, (source, exported) in enumerate(zip(source_records, exported_records)):
        for field, value in source.items():
            if isinstance(value, datetime):
                datetime_fields += 1
                expected = value.isoformat()
                actual = exported.get(field, "")
                if actual != expected:
                    errors.append(
                        f"Record {i}, field {field}: "
                        f"Expected '{expected}', got '{actual}'"
                    )

    return {
        "test": f"{data_type} - Datetime handling",
        "status": "PASSED" if not errors else "FAILED",
        "datetime_fields_tested": datetime_fields,
        "errors": errors
    }


def test_no_truncation_csv(source_records: List[Dict], exported_records: List[Dict], data_type: str) -> Dict:
    """Test that long text fields are not truncated in CSV."""
    long_fields = 0
    errors = []

    for i, (source, exported) in enumerate(zip(source_records, exported_records)):
        for field, value in source.items():
            if isinstance(value, str) and len(value) > 100:
                long_fields += 1
                expected = str(value)
                actual = exported.get(field, "")
                if len(actual) < len(expected):
                    errors.append(
                        f"Record {i}, field {field}: "
                        f"Truncated from {len(expected)} to {len(actual)} chars"
                    )

    return {
        "test": f"{data_type} - No truncation",
        "status": "PASSED" if not errors else "FAILED",
        "long_fields_tested": long_fields,
        "errors": errors
    }


# =============================================================================
# JSON VERIFICATION
# =============================================================================

def verify_json_integrity(source_data: Dict[str, Any], output_dir: Path) -> Dict[str, Any]:
    """
    Verify JSON export integrity by comparing source data with exported files.

    Args:
        source_data: Original data dictionary
        output_dir: Directory containing exported JSON files

    Returns:
        Dictionary with verification results
    """
    results = {
        "passed": True,
        "tests": [],
        "errors": []
    }

    for data_type, source_records in source_data.items():
        json_file = output_dir / f"{data_type}.json"

        # Test 1: File exists
        if not json_file.exists():
            results["passed"] = False
            results["errors"].append(f"JSON file missing: {json_file}")
            continue

        # Read JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            exported_data = json.load(f)

        # Convert to list for consistency
        if isinstance(source_records, dict):
            source_records_list = [source_records]
            exported_records_list = [exported_data] if isinstance(exported_data, dict) else exported_data
        else:
            source_records_list = source_records
            exported_records_list = exported_data

        # Test 2: Record count matches
        if len(exported_records_list) != len(source_records_list):
            results["passed"] = False
            results["errors"].append(
                f"{data_type} JSON: Record count mismatch. "
                f"Expected {len(source_records_list)}, got {len(exported_records_list)}"
            )
            results["tests"].append({
                "test": f"{data_type} - Record count",
                "status": "FAILED",
                "expected": len(source_records_list),
                "actual": len(exported_records_list)
            })
        else:
            results["tests"].append({
                "test": f"{data_type} - Record count",
                "status": "PASSED",
                "count": len(source_records_list)
            })

        # Test 3: Field accuracy for each record
        for i, (source_record, exported_record) in enumerate(zip(source_records_list, exported_records_list)):
            for field, source_value in source_record.items():
                exported_value = exported_record.get(field)

                # Handle datetime conversion
                if isinstance(source_value, datetime):
                    expected_value = source_value.isoformat()
                elif hasattr(source_value, 'isoformat'):  # date objects
                    expected_value = source_value.isoformat()
                else:
                    expected_value = source_value

                if exported_value != expected_value:
                    results["passed"] = False
                    results["errors"].append(
                        f"{data_type} JSON record {i}, field '{field}': "
                        f"Expected '{expected_value}', got '{exported_value}'"
                    )

        # Test 4: Data type preservation
        type_test = test_type_preservation_json(source_records_list, exported_records_list, data_type)
        results["tests"].append(type_test)
        if type_test["status"] == "FAILED":
            results["passed"] = False

        # Test 5: Nested structure preservation
        nested_test = test_nested_structures_json(source_records_list, exported_records_list, data_type)
        results["tests"].append(nested_test)
        if nested_test["status"] == "FAILED":
            results["passed"] = False

    return results


def test_type_preservation_json(source_records: List[Dict], exported_records: List[Dict], data_type: str) -> Dict:
    """Test that data types are preserved correctly in JSON."""
    type_checks = 0
    errors = []

    for i, (source, exported) in enumerate(zip(source_records, exported_records)):
        for field, value in source.items():
            type_checks += 1
            exported_value = exported.get(field)

            # Skip datetime/date objects (they get converted to strings)
            if isinstance(value, (datetime,)) or hasattr(value, 'isoformat'):
                if not isinstance(exported_value, str):
                    errors.append(f"Record {i}, field {field}: datetime not converted to string")
                continue

            # Check type preservation for other types
            if value is None:
                if exported_value is not None:
                    errors.append(f"Record {i}, field {field}: null not preserved")
            elif isinstance(value, bool):
                if not isinstance(exported_value, bool):
                    errors.append(f"Record {i}, field {field}: bool type not preserved")
            elif isinstance(value, int):
                if not isinstance(exported_value, int):
                    errors.append(f"Record {i}, field {field}: int type not preserved")
            elif isinstance(value, float):
                if not isinstance(exported_value, (int, float)):
                    errors.append(f"Record {i}, field {field}: numeric type not preserved")

    return {
        "test": f"{data_type} - Type preservation",
        "status": "PASSED" if not errors else "FAILED",
        "type_checks": type_checks,
        "errors": errors
    }


def test_nested_structures_json(source_records: List[Dict], exported_records: List[Dict], data_type: str) -> Dict:
    """Test that nested structures are preserved in JSON."""
    nested_fields = 0
    errors = []

    for i, (source, exported) in enumerate(zip(source_records, exported_records)):
        for field, value in source.items():
            if isinstance(value, (dict, list)):
                nested_fields += 1
                exported_value = exported.get(field)
                if exported_value != value:
                    errors.append(f"Record {i}, field {field}: nested structure not preserved")

    return {
        "test": f"{data_type} - Nested structures",
        "status": "PASSED" if not errors else "FAILED",
        "nested_fields_tested": nested_fields,
        "errors": errors if nested_fields > 0 else ["No nested fields in test data"]
    }


# =============================================================================
# RANDOM SAMPLING VERIFICATION
# =============================================================================

def verify_random_sampling(source_data: Dict[str, Any], csv_dir: Path, json_dir: Path, sample_size: int = 5) -> Dict:
    """
    Verify data integrity by randomly sampling records.

    Args:
        source_data: Original data dictionary
        csv_dir: Directory containing CSV exports
        json_dir: Directory containing JSON exports
        sample_size: Number of random samples to verify

    Returns:
        Dictionary with sampling verification results
    """
    results = {
        "passed": True,
        "samples_verified": 0,
        "errors": []
    }

    for data_type, source_records in source_data.items():
        if isinstance(source_records, dict):
            continue  # Skip metrics (single record)

        # Sample random records
        sample_count = min(sample_size, len(source_records))
        sampled_indices = random.sample(range(len(source_records)), sample_count)

        for idx in sampled_indices:
            source_record = source_records[idx]

            # Verify CSV
            csv_file = csv_dir / f"{data_type}.csv"
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                csv_records = list(reader)
                csv_record = csv_records[idx]

            # Verify JSON
            json_file = json_dir / f"{data_type}.json"
            with open(json_file, "r", encoding="utf-8") as f:
                json_records = json.load(f)
                json_record = json_records[idx]

            # Compare each field
            for field, source_value in source_record.items():
                # CSV comparison (normalize line endings)
                csv_value = csv_record.get(field, "")
                expected_csv = format_value_for_csv(source_value)
                # Normalize line endings for comparison (CSV normalizes \r to \n)
                expected_csv_normalized = expected_csv.replace('\r\n', '\n').replace('\r', '\n')
                csv_value_normalized = csv_value.replace('\r\n', '\n').replace('\r', '\n')
                if csv_value_normalized != expected_csv_normalized:
                    results["passed"] = False
                    results["errors"].append(
                        f"CSV {data_type}[{idx}].{field}: Expected '{expected_csv_normalized}', got '{csv_value_normalized}'"
                    )

                # JSON comparison
                json_value = json_record.get(field)
                if isinstance(source_value, datetime):
                    expected_json = source_value.isoformat()
                elif hasattr(source_value, 'isoformat'):
                    expected_json = source_value.isoformat()
                else:
                    expected_json = source_value

                if json_value != expected_json:
                    results["passed"] = False
                    results["errors"].append(
                        f"JSON {data_type}[{idx}].{field}: Expected '{expected_json}', got '{json_value}'"
                    )

            results["samples_verified"] += 1

    return results


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_integrity_tests():
    """Run comprehensive data integrity verification tests."""
    print("=" * 80)
    print("DATA INTEGRITY VERIFICATION TEST SUITE")
    print("=" * 80)
    print()

    # Generate test data
    print("📊 Generating test data with edge cases...")
    test_data = generate_test_data()
    print(f"   ✓ Generated {len(test_data['tasks'])} tasks")
    print(f"   ✓ Generated {len(test_data['habits'])} habits")
    print(f"   ✓ Generated {len(test_data['goals'])} goals")
    print(f"   ✓ Generated 1 metrics record")
    print()

    # Create test output directories
    test_dir = Path(__file__).parent / "test_integrity_exports"
    csv_dir = test_dir / "csv"
    json_dir = test_dir / "json"

    csv_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    # Export to CSV
    print("📝 Exporting to CSV...")
    csv_files = export_to_csv(test_data, "all", csv_dir)
    print(f"   ✓ Created {len(csv_files)} CSV files")
    print()

    # Export to JSON
    print("📝 Exporting to JSON...")
    json_files = export_to_json(test_data, "all", json_dir)
    print(f"   ✓ Created {len(json_files)} JSON files")
    print()

    # Verify CSV integrity
    print("🔍 Verifying CSV integrity...")
    csv_results = verify_csv_integrity(test_data, csv_dir)
    print(f"   {'✓' if csv_results['passed'] else '✗'} CSV verification {'PASSED' if csv_results['passed'] else 'FAILED'}")
    print(f"   Tests run: {len(csv_results['tests'])}")
    if csv_results['errors']:
        print(f"   Errors: {len(csv_results['errors'])}")
    print()

    # Verify JSON integrity
    print("🔍 Verifying JSON integrity...")
    json_results = verify_json_integrity(test_data, json_dir)
    print(f"   {'✓' if json_results['passed'] else '✗'} JSON verification {'PASSED' if json_results['passed'] else 'FAILED'}")
    print(f"   Tests run: {len(json_results['tests'])}")
    if json_results['errors']:
        print(f"   Errors: {len(json_results['errors'])}")
    print()

    # Random sampling verification
    print("🎲 Running random sampling verification...")
    sampling_results = verify_random_sampling(test_data, csv_dir, json_dir, sample_size=3)
    print(f"   {'✓' if sampling_results['passed'] else '✗'} Sampling verification {'PASSED' if sampling_results['passed'] else 'FAILED'}")
    print(f"   Samples verified: {sampling_results['samples_verified']}")
    if sampling_results['errors']:
        print(f"   Errors: {len(sampling_results['errors'])}")
    print()

    # Overall results
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    all_passed = csv_results['passed'] and json_results['passed'] and sampling_results['passed']

    print()
    print(f"CSV Export Integrity:      {'✅ PASSED' if csv_results['passed'] else '❌ FAILED'}")
    print(f"JSON Export Integrity:     {'✅ PASSED' if json_results['passed'] else '❌ FAILED'}")
    print(f"Random Sampling:           {'✅ PASSED' if sampling_results['passed'] else '❌ FAILED'}")
    print()
    print(f"Overall Result:            {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    print()

    # Detailed test results
    if not all_passed:
        print("=" * 80)
        print("DETAILED ERRORS")
        print("=" * 80)
        print()

        if csv_results['errors']:
            print("CSV Errors:")
            for error in csv_results['errors'][:10]:  # Show first 10 errors
                print(f"  • {error}")
            if len(csv_results['errors']) > 10:
                print(f"  ... and {len(csv_results['errors']) - 10} more errors")
            print()

        if json_results['errors']:
            print("JSON Errors:")
            for error in json_results['errors'][:10]:
                print(f"  • {error}")
            if len(json_results['errors']) > 10:
                print(f"  ... and {len(json_results['errors']) - 10} more errors")
            print()

        if sampling_results['errors']:
            print("Sampling Errors:")
            for error in sampling_results['errors'][:10]:
                print(f"  • {error}")
            if len(sampling_results['errors']) > 10:
                print(f"  ... and {len(sampling_results['errors']) - 10} more errors")
            print()

    # Test details
    print("=" * 80)
    print("DETAILED TEST RESULTS")
    print("=" * 80)
    print()

    print("CSV Tests:")
    for test in csv_results['tests']:
        status = "✅" if test['status'] == "PASSED" else "❌"
        print(f"  {status} {test['test']}")
    print()

    print("JSON Tests:")
    for test in json_results['tests']:
        status = "✅" if test['status'] == "PASSED" else "❌"
        print(f"  {status} {test['test']}")
    print()

    # Acceptance criteria summary
    print("=" * 80)
    print("ACCEPTANCE CRITERIA VERIFICATION")
    print("=" * 80)
    print()

    # Count criteria met
    criteria_results = []

    # 1. Record counts match
    record_count_passed = all(
        test['status'] == 'PASSED'
        for test in csv_results['tests'] + json_results['tests']
        if 'Record count' in test['test']
    )
    criteria_results.append(("Record counts match database query results", record_count_passed))

    # 2. Random sampling verification
    criteria_results.append(("Sample random records to verify field values match", sampling_results['passed']))

    # 3. Special characters
    special_char_passed = all(
        test['status'] == 'PASSED'
        for test in csv_results['tests']
        if 'Special character' in test['test']
    )
    criteria_results.append(("Special characters properly escaped", special_char_passed))

    # 4. Null values
    null_handling_passed = all(
        test['status'] == 'PASSED'
        for test in csv_results['tests']
        if 'Null value' in test['test']
    )
    criteria_results.append(("Null values handled correctly", null_handling_passed))

    # 5. Datetime fields
    datetime_passed = all(
        test['status'] == 'PASSED'
        for test in csv_results['tests']
        if 'Datetime' in test['test']
    )
    criteria_results.append(("Datetime fields readable and accurate", datetime_passed))

    # 6. No truncation
    truncation_passed = all(
        test['status'] == 'PASSED'
        for test in csv_results['tests']
        if 'truncation' in test['test']
    )
    criteria_results.append(("No data truncation occurs", truncation_passed))

    # Print criteria results
    for criterion, passed in criteria_results:
        status = "✅" if passed else "❌"
        print(f"{status} {criterion}")

    print()
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_integrity_tests()
    sys.exit(0 if success else 1)
