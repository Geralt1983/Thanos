"""
Personal Assistant: Data Export Command

Exports tasks, habits, goals, and metrics to CSV or JSON format for analysis and backup.

Usage:
    python -m commands.pa.export [--format FORMAT] [--type TYPE] [--output DIR]

Arguments:
    --format    Output format: csv or json (default: csv)
    --type      Data type: tasks, habits, goals, metrics, or all (default: all)
    --output    Output directory (default: History/Exports/)

Examples:
    python -m commands.pa.export --format csv --type tasks
    python -m commands.pa.export --format json --type all
    python -m commands.pa.export --output ./my-exports

Model: Direct data export (no LLM required)
"""

import argparse
import asyncio
import csv
import json
from datetime import datetime
from pathlib import Path
import sys
from typing import Optional, List, Dict, Any, Tuple


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.adapters.workos import WorkOSAdapter


# System prompt for potential LLM-based summary generation
SYSTEM_PROMPT = """You are Jeremy's data export assistant.

Your role:
- Export productivity data for analysis and backup
- Present data in clear, structured formats
- Ensure data integrity and completeness
- Provide helpful summaries of exported data

Context:
- Data comes from WorkOS/Neon PostgreSQL database
- Includes tasks, habits, daily goals, and metrics
- Used for backup, analysis, and reporting
"""


# =============================================================================
# DATA RETRIEVAL FUNCTIONS
# =============================================================================


async def retrieve_tasks(adapter: WorkOSAdapter) -> List[Dict[str, Any]]:
    """
    Retrieve all tasks from the WorkOS database.

    Fetches tasks across all statuses (active, queued, backlog, done) with
    client information joined.

    Args:
        adapter: WorkOSAdapter instance

    Returns:
        List of task dictionaries with all task fields plus client_name
    """
    pool = await adapter._get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT t.*, c.name as client_name
            FROM tasks t
            LEFT JOIN clients c ON t.client_id = c.id
            ORDER BY
                CASE t.status
                    WHEN 'active' THEN 1
                    WHEN 'queued' THEN 2
                    WHEN 'backlog' THEN 3
                    WHEN 'done' THEN 4
                END,
                t.sort_order ASC NULLS LAST,
                t.created_at DESC
            """
        )
        return [adapter._row_to_dict(r) for r in rows]


async def retrieve_habits(adapter: WorkOSAdapter) -> List[Dict[str, Any]]:
    """
    Retrieve all habits with completion data.

    Fetches both active and inactive habits with their streak information
    and last completion date.

    Args:
        adapter: WorkOSAdapter instance

    Returns:
        List of habit dictionaries with completion metadata
    """
    pool = await adapter._get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT h.*,
                   (SELECT MAX(completed_at) FROM habit_completions
                    WHERE habit_id = h.id) as last_completion
            FROM habits h
            ORDER BY h.sort_order ASC NULLS LAST, h.created_at DESC
            """
        )
        return [adapter._row_to_dict(r) for r in rows]


async def retrieve_goals(adapter: WorkOSAdapter) -> List[Dict[str, Any]]:
    """
    Retrieve daily goals data.

    Fetches all daily goal records including date, streak, points earned,
    target points, and goal achievement status.

    Args:
        adapter: WorkOSAdapter instance

    Returns:
        List of daily goal dictionaries ordered by date descending
    """
    pool = await adapter._get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT date, current_streak, earned_points, target_points, goal_met
            FROM daily_goals
            ORDER BY date DESC
            """
        )
        return [adapter._row_to_dict(r) for r in rows]


async def retrieve_metrics(adapter: WorkOSAdapter) -> Dict[str, Any]:
    """
    Retrieve calculated productivity metrics.

    Uses the WorkOSAdapter's get_today_metrics method to get current
    productivity metrics including points earned, streak, task counts,
    and goal achievement status.

    Args:
        adapter: WorkOSAdapter instance

    Returns:
        Dictionary with metrics fields (completed_count, earned_points,
        target_points, progress_percentage, streak, active_count,
        queued_count, goal_met, target_met)
    """
    result = await adapter.call_tool("get_today_metrics", {})
    if result.success:
        return result.data
    else:
        # Return empty metrics on error
        return {
            "completed_count": 0,
            "earned_points": 0,
            "target_points": 18,
            "minimum_points": 12,
            "progress_percentage": 0,
            "streak": 0,
            "active_count": 0,
            "queued_count": 0,
            "goal_met": False,
            "target_met": False,
            "error": result.error,
        }


async def retrieve_all_data(data_type: str) -> Dict[str, Any]:
    """
    Retrieve data from WorkOS database based on data type.

    Handles async connection, data retrieval, and proper cleanup.
    Provides streaming progress updates during retrieval.

    Args:
        data_type: Type of data to retrieve (tasks/habits/goals/metrics/all)

    Returns:
        Dictionary with retrieved data organized by type

    Raises:
        ValueError: If database connection fails
        Exception: For other errors during data retrieval
    """
    adapter = WorkOSAdapter()
    data = {}

    try:
        print("🔌 Connecting to database...", flush=True)

        # Retrieve requested data type(s)
        if data_type in ["tasks", "all"]:
            print("📥 Retrieving tasks...", flush=True)
            data["tasks"] = await retrieve_tasks(adapter)
            print(f"   ✓ Retrieved {len(data['tasks'])} tasks", flush=True)

        if data_type in ["habits", "all"]:
            print("📥 Retrieving habits...", flush=True)
            data["habits"] = await retrieve_habits(adapter)
            print(f"   ✓ Retrieved {len(data['habits'])} habits", flush=True)

        if data_type in ["goals", "all"]:
            print("📥 Retrieving goals...", flush=True)
            data["goals"] = await retrieve_goals(adapter)
            print(f"   ✓ Retrieved {len(data['goals'])} daily goals", flush=True)

        if data_type in ["metrics", "all"]:
            print("📥 Retrieving metrics...", flush=True)
            data["metrics"] = await retrieve_metrics(adapter)
            print(f"   ✓ Retrieved current metrics", flush=True)

        return data

    except ValueError as e:
        # Database connection error
        raise ValueError(f"Database connection failed: {e}")
    except Exception as e:
        # Other errors during retrieval
        raise Exception(f"Error retrieving data: {e}")
    finally:
        # Always close the adapter
        await adapter.close()
        print("🔌 Database connection closed", flush=True)


# =============================================================================
# CSV EXPORT FUNCTIONS
# =============================================================================


def format_value_for_csv(value: Any) -> str:
    """
    Format a value for CSV export.

    Handles various data types including:
    - datetime objects (convert to ISO format)
    - None values (convert to empty string)
    - Nested structures like dicts/lists (JSON-encode)
    - Other types (convert to string)

    Args:
        value: The value to format

    Returns:
        String representation suitable for CSV
    """
    if value is None:
        return ""
    elif isinstance(value, datetime):
        # Convert datetime to ISO format string
        return value.isoformat()
    elif isinstance(value, (dict, list)):
        # JSON-encode complex structures
        return json.dumps(value)
    elif isinstance(value, bool):
        # Convert boolean to string
        return str(value)
    else:
        # Convert to string
        return str(value)


def export_to_csv(
    data: Dict[str, Any],
    data_type: str,
    output_dir: Path
) -> List[Tuple[str, Path]]:
    """
    Export data to CSV format.

    Creates separate CSV files for each data type with proper headers.
    Handles nested data structures by JSON-encoding them and converts
    timestamps to ISO format strings.

    Args:
        data: Dictionary containing data to export, organized by type
        data_type: Type of data being exported (tasks/habits/goals/metrics/all)
        output_dir: Path to output directory

    Returns:
        List of tuples containing (data_type, file_path) for each created file

    Example:
        >>> data = {"tasks": [...], "habits": [...]}
        >>> files = export_to_csv(data, "all", Path("./exports"))
        >>> # Returns: [("tasks", Path("./exports/tasks.csv")), ...]
    """
    exported_files = []

    print("📝 Exporting to CSV format...")
    print()

    for data_key, records in data.items():
        # Handle metrics (single dict) vs other data types (list of dicts)
        if data_key == "metrics":
            # Metrics is a single dictionary, convert to list with one item
            if not isinstance(records, list):
                records = [records]

        # Skip if no records
        if not records or len(records) == 0:
            print(f"   ⚠️  Skipping {data_key} (no data)")
            continue

        # Create filename
        filename = f"{data_key}.csv"
        filepath = output_dir / filename

        try:
            # Get all unique keys from all records to create comprehensive headers
            all_keys = set()
            for record in records:
                if isinstance(record, dict):
                    all_keys.update(record.keys())

            # Sort keys for consistent column order
            fieldnames = sorted(all_keys)

            # Write CSV file
            with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                # Write header
                writer.writeheader()

                # Write data rows
                for record in records:
                    # Format all values for CSV
                    formatted_record = {
                        key: format_value_for_csv(record.get(key))
                        for key in fieldnames
                    }
                    writer.writerow(formatted_record)

            # Get file size
            file_size = filepath.stat().st_size

            print(f"   ✓ {data_key}.csv - {len(records)} records ({format_file_size(file_size)})")
            exported_files.append((data_key, filepath))

        except Exception as e:
            print(f"   ❌ Error exporting {data_key}: {e}")
            continue

    print()
    return exported_files


# =============================================================================
# ARGUMENT PARSING
# =============================================================================


def parse_arguments(args_string: Optional[str] = None) -> argparse.Namespace:
    """
    Parse command line arguments for the export command.

    Args:
        args_string: Optional string of arguments (for programmatic use)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Export productivity data to CSV or JSON format",
        prog="pa:export"
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["csv", "json"],
        default="csv",
        help="Output format: csv or json (default: csv)"
    )

    parser.add_argument(
        "--type",
        "-t",
        choices=["tasks", "habits", "goals", "metrics", "all"],
        default="all",
        help="Data type to export: tasks, habits, goals, metrics, or all (default: all)"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output directory (default: History/Exports/)"
    )

    # Parse arguments
    if args_string:
        # Split the string respecting quotes
        import shlex
        args_list = shlex.split(args_string)
        return parser.parse_args(args_list)
    else:
        return parser.parse_args()


def get_output_directory(custom_path: Optional[str] = None) -> Path:
    """
    Get or create the output directory for exports.

    Args:
        custom_path: Optional custom output directory path

    Returns:
        Path object for the output directory

    Raises:
        ValueError: If directory cannot be created
    """
    project_root = Path(__file__).parent.parent.parent

    if custom_path:
        output_dir = Path(custom_path)
    else:
        # Default: History/Exports/YYYY-MM-DD/
        timestamp = datetime.now()
        output_dir = project_root / "History" / "Exports" / timestamp.strftime("%Y-%m-%d")

    # Create directory if it doesn't exist
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create output directory '{output_dir}': {e}")

    return output_dir


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted string (e.g., "1.5 KB", "2.3 MB")
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def save_export_summary(output_dir: Path, summary: str):
    """
    Save export summary to the History directory.

    Args:
        output_dir: Directory where exports were saved
        summary: Summary text to save
    """
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "Exports"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"export_summary_{timestamp.strftime('%Y-%m-%d_%H%M%S')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Data Export Summary\n\n")
        f.write(f"**Date:** {timestamp.strftime('%B %d, %Y at %I:%M %p')}\n\n")
        f.write(f"**Output Directory:** `{output_dir}`\n\n")
        f.write("---\n\n")
        f.write(summary)


def execute(args: Optional[str] = None) -> str:
    """
    Execute the export command.

    This function orchestrates the data export process:
    1. Parse arguments (format, type, output directory)
    2. Retrieve data from WorkOS database
    3. Export to specified format (CSV or JSON)
    4. Generate and save summary

    Args:
        args: Command arguments as string (e.g., "--format json --type tasks")

    Returns:
        Summary of the export operation

    Example:
        >>> execute("--format csv --type tasks")
        "✅ Exported 42 tasks to tasks.csv (12.3 KB)"
    """
    try:
        # Parse arguments
        parsed_args = parse_arguments(args)

        # Get output directory
        output_dir = get_output_directory(parsed_args.output)

        # Print header
        print("📦 Data Export")
        print("=" * 60)
        print(f"Format: {parsed_args.format.upper()}")
        print(f"Type: {parsed_args.type}")
        print(f"Output: {output_dir}")
        print("=" * 60)
        print()

        # Retrieve data from database
        print("🔄 Starting data retrieval...")
        print()
        data = asyncio.run(retrieve_all_data(parsed_args.type))
        print()

        # Check if we got any data
        total_records = sum(
            len(v) if isinstance(v, list) else 1
            for v in data.values()
        )

        if total_records == 0:
            print("⚠️  No data found to export.")
            print()
            summary = f"""## Export Summary

**Format:** {parsed_args.format.upper()}
**Data Type:** {parsed_args.type}
**Output Directory:** {output_dir}

## Status

⚠️ No data found to export.

## Next Steps

The following will be implemented in subsequent phases:
1. CSV export functionality (Subtask 1.3)
2. JSON export functionality (Subtask 1.4)
3. Progress streaming and history saving (Subtask 1.5)
"""
            save_export_summary(output_dir, summary)
            return summary

        # Display data retrieval summary
        print("✅ Data retrieval complete!")
        print()
        print("📊 Retrieved data:")
        for data_type_name, records in data.items():
            if isinstance(records, list):
                print(f"   • {data_type_name.title()}: {len(records)} records")
            else:
                print(f"   • {data_type_name.title()}: 1 record")
        print()

        # Export data based on format
        exported_files = []
        if parsed_args.format == "csv":
            exported_files = export_to_csv(data, parsed_args.type, output_dir)
        else:
            # JSON export will be implemented in subtask 1.4
            print("⚠️  JSON export functionality not yet implemented.")
            print()

        # Generate summary
        summary = f"""## Export Summary

**Date:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
**Format:** {parsed_args.format.upper()}
**Data Type:** {parsed_args.type}
**Output Directory:** `{output_dir}`

## Data Retrieved

"""
        for data_type_name, records in data.items():
            if isinstance(records, list):
                summary += f"- **{data_type_name.title()}**: {len(records)} records\n"
            else:
                summary += f"- **{data_type_name.title()}**: 1 record\n"

        # Add exported files info
        if exported_files:
            summary += "\n## Exported Files\n\n"
            for data_type_name, filepath in exported_files:
                file_size = filepath.stat().st_size
                summary += f"- `{filepath.name}` - {format_file_size(file_size)}\n"
            summary += f"\n**Total Files:** {len(exported_files)}\n"

        summary += "\n## Status\n\n"
        if parsed_args.format == "csv":
            summary += "✅ CSV export complete\n"
        else:
            summary += "⚠️ JSON export functionality will be implemented in subtask 1.4\n"

        # Save summary
        save_export_summary(output_dir, summary)

        # Print final summary
        print("-" * 60)
        if exported_files:
            print(f"✅ Export complete! {len(exported_files)} file(s) created")
            print(f"📁 Location: {output_dir}")
        else:
            print("⚠️  No files exported")
        print(f"📄 Summary saved to History/Exports/")
        print("-" * 60)

        return summary

    except argparse.ArgumentError as e:
        error_msg = f"❌ Argument error: {e}\n\nUse --help for usage information."
        print(error_msg)
        return error_msg

    except ValueError as e:
        error_msg = f"❌ Error: {e}"
        print(error_msg)
        return error_msg

    except Exception as e:
        error_msg = f"❌ Unexpected error: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return error_msg


def main():
    """CLI entry point."""
    # Handle --help flag specially to show help
    if "--help" in sys.argv or "-h" in sys.argv:
        parse_arguments(None)
        return

    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
