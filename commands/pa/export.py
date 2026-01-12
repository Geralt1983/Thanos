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
from datetime import datetime
from pathlib import Path
import sys
from typing import Optional


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

        # Placeholder for data retrieval and export
        # This will be implemented in subsequent subtasks (1.2, 1.3, 1.4, 1.5)
        print("⚠️  Export functionality not yet implemented.")
        print()
        print("This command will export:")
        if parsed_args.type == "all":
            print("  • Tasks (active, queued, backlog, done)")
            print("  • Habits (with completion data)")
            print("  • Goals (daily goals and streaks)")
            print("  • Metrics (calculated productivity metrics)")
        else:
            print(f"  • {parsed_args.type.title()}")
        print()
        print(f"To: {output_dir}")
        print(f"As: {parsed_args.format.upper()} files")
        print()

        summary = f"""## Export Configuration

**Format:** {parsed_args.format.upper()}
**Data Type:** {parsed_args.type}
**Output Directory:** {output_dir}

## Status

⚠️ Export functionality is being implemented. This is the command structure only.

## Next Steps

The following will be implemented in subsequent phases:
1. Data retrieval from WorkOS database
2. CSV export functionality
3. JSON export functionality
4. Progress streaming and history saving
"""

        # Save summary
        save_export_summary(output_dir, summary)

        print("-" * 60)
        print("✅ Export command structure ready")
        print(f"📁 Summary saved to History/Exports/")
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
