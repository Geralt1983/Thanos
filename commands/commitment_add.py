#!/usr/bin/env python3
"""
Commitment Add Command - Add new commitments with metadata.

This command allows users to add new commitments (habits, goals, or tasks)
with full metadata support including type, due date, recurrence patterns,
priority, domain, and tags.

Usage:
    python commitment_add.py [options]
    python commitment_add.py --title "Daily meditation" --type habit --recurrence daily
    python commitment_add.py --interactive

Examples:
    # Add a habit with recurrence
    python commitment_add.py --title "Morning workout" --type habit --recurrence daily --domain health --priority 1

    # Add a task with due date
    python commitment_add.py --title "Submit report" --type task --due "2026-01-15" --domain work

    # Add a goal
    python commitment_add.py --title "Learn Python" --type goal --domain learning --tags coding,skills

    # Interactive mode
    python commitment_add.py --interactive
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from Tools.commitment_tracker import (
        CommitmentTracker,
        CommitmentType,
        CommitmentStatus,
        RecurrencePattern,
        Commitment
    )
except ImportError:
    print("❌ Error: Could not import CommitmentTracker. Please ensure Tools/commitment_tracker.py exists.")
    sys.exit(1)


def parse_date(date_str: str) -> Optional[str]:
    """
    Parse various date formats and return ISO format.

    Supported formats:
    - ISO: 2026-01-15, 2026-01-15T10:00:00
    - Relative: today, tomorrow, +3d, +2w
    - Natural: Jan 15, January 15 2026

    Args:
        date_str: Date string to parse

    Returns:
        ISO format date string or None if invalid
    """
    if not date_str:
        return None

    date_str = date_str.strip().lower()

    try:
        # Relative dates
        if date_str == "today":
            return datetime.now().date().isoformat()
        elif date_str == "tomorrow":
            return (datetime.now() + timedelta(days=1)).date().isoformat()
        elif date_str.startswith("+"):
            # +3d, +2w format
            value = int(date_str[1:-1])
            unit = date_str[-1]
            if unit == 'd':
                return (datetime.now() + timedelta(days=value)).date().isoformat()
            elif unit == 'w':
                return (datetime.now() + timedelta(weeks=value)).date().isoformat()

        # Try ISO format
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.date().isoformat()
        except ValueError:
            pass

        # Try common formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%b %d", "%B %d", "%b %d %Y", "%B %d %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                # If year not specified, use current year
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt.date().isoformat()
            except ValueError:
                continue

        print(f"⚠️  Warning: Could not parse date '{date_str}'. Use format: YYYY-MM-DD, 'today', 'tomorrow', or '+3d'")
        return None

    except Exception as e:
        print(f"⚠️  Warning: Error parsing date: {e}")
        return None


def parse_tags(tags_str: Optional[str]) -> List[str]:
    """
    Parse comma-separated tags.

    Args:
        tags_str: Comma-separated tag string

    Returns:
        List of tags
    """
    if not tags_str:
        return []

    return [tag.strip() for tag in tags_str.split(",") if tag.strip()]


def validate_type(type_str: str) -> Optional[str]:
    """Validate and normalize commitment type."""
    type_str = type_str.lower()
    if type_str in ["habit", "h"]:
        return CommitmentType.HABIT
    elif type_str in ["goal", "g"]:
        return CommitmentType.GOAL
    elif type_str in ["task", "t"]:
        return CommitmentType.TASK
    return None


def validate_recurrence(recurrence_str: str) -> Optional[str]:
    """Validate and normalize recurrence pattern."""
    recurrence_str = recurrence_str.lower()
    mapping = {
        "daily": RecurrencePattern.DAILY,
        "d": RecurrencePattern.DAILY,
        "weekly": RecurrencePattern.WEEKLY,
        "w": RecurrencePattern.WEEKLY,
        "weekdays": RecurrencePattern.WEEKDAYS,
        "wd": RecurrencePattern.WEEKDAYS,
        "weekends": RecurrencePattern.WEEKENDS,
        "we": RecurrencePattern.WEEKENDS,
        "custom": RecurrencePattern.CUSTOM,
        "c": RecurrencePattern.CUSTOM,
        "none": RecurrencePattern.NONE,
        "n": RecurrencePattern.NONE,
    }
    return mapping.get(recurrence_str)


def validate_priority(priority: int) -> int:
    """Validate and clamp priority to 1-5 range."""
    try:
        p = int(priority)
        return max(1, min(5, p))
    except (ValueError, TypeError):
        return 3


def update_commitments_md(commitment: Commitment, state_dir: Path) -> bool:
    """
    Update Commitments.md with the new commitment.

    Adds the commitment to the appropriate section based on domain.
    Creates a simple checkbox entry for user-facing view.

    Args:
        commitment: The commitment to add
        state_dir: Path to State directory

    Returns:
        True if successful, False otherwise
    """
    md_file = state_dir / "Commitments.md"

    try:
        # Read existing content
        if md_file.exists():
            content = md_file.read_text()
            lines = content.split("\n")
        else:
            content = "# Commitments\n\n"
            lines = ["# Commitments", ""]

        # Determine section based on domain
        domain_sections = {
            "work": "## Work",
            "personal": "## Personal",
            "health": "## Health",
            "learning": "## Learning",
            "general": "## General"
        }

        section_header = domain_sections.get(commitment.domain.lower(), "## General")

        # Build the commitment line
        checkbox = "- [ ]"
        title = commitment.title

        # Add due date if present
        if commitment.due_date:
            try:
                due_date = datetime.fromisoformat(commitment.due_date).date()
                title += f" (due: {due_date.isoformat()})"
            except (ValueError, TypeError):
                pass

        # Add recurrence indicator for habits
        if commitment.is_recurring():
            recurrence_emoji = {
                RecurrencePattern.DAILY: "🔄 Daily",
                RecurrencePattern.WEEKLY: "📅 Weekly",
                RecurrencePattern.WEEKDAYS: "💼 Weekdays",
                RecurrencePattern.WEEKENDS: "🌴 Weekends",
            }
            indicator = recurrence_emoji.get(commitment.recurrence_pattern, "🔁 Recurring")
            title += f" [{indicator}]"

        # Add priority indicator for high priority items
        if commitment.priority == 1:
            checkbox = "- [ ] ⚡"

        commitment_line = f"{checkbox} {title}"

        # Find or create section
        section_idx = None
        for i, line in enumerate(lines):
            if line.strip() == section_header:
                section_idx = i
                break

        if section_idx is None:
            # Create new section at the end
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(section_header)
            lines.append(commitment_line)
        else:
            # Find where to insert (after section header, before next section or end)
            insert_idx = section_idx + 1

            # Skip existing items in this section
            while insert_idx < len(lines):
                line = lines[insert_idx].strip()
                # Stop at next section or empty line followed by section
                if line.startswith("##") or (not line and insert_idx + 1 < len(lines) and lines[insert_idx + 1].strip().startswith("##")):
                    break
                insert_idx += 1

            # Insert before next section
            lines.insert(insert_idx, commitment_line)

        # Write back
        md_file.write_text("\n".join(lines))
        return True

    except Exception as e:
        print(f"⚠️  Warning: Could not update Commitments.md: {e}")
        return False


def interactive_add(tracker: CommitmentTracker, state_dir: Path) -> bool:
    """
    Interactive mode for adding a commitment.

    Prompts user for all required information.

    Args:
        tracker: CommitmentTracker instance
        state_dir: Path to State directory

    Returns:
        True if commitment was created, False otherwise
    """
    print("\n📋 Add New Commitment (Interactive Mode)")
    print("=" * 60)

    # Title
    title = input("\n📝 Title (required): ").strip()
    if not title:
        print("❌ Title is required.")
        return False

    # Type
    print("\n🏷️  Type:")
    print("  1. Habit (recurring behavior)")
    print("  2. Goal (milestone to achieve)")
    print("  3. Task (one-time action)")
    type_input = input("Choose (1-3) or enter type: ").strip().lower()

    if type_input in ["1", "habit", "h"]:
        commitment_type = CommitmentType.HABIT
    elif type_input in ["2", "goal", "g"]:
        commitment_type = CommitmentType.GOAL
    elif type_input in ["3", "task", "t"]:
        commitment_type = CommitmentType.TASK
    else:
        print("❌ Invalid type.")
        return False

    # Recurrence (if habit)
    recurrence = RecurrencePattern.NONE
    if commitment_type == CommitmentType.HABIT:
        print("\n🔄 Recurrence:")
        print("  1. Daily")
        print("  2. Weekly")
        print("  3. Weekdays (Mon-Fri)")
        print("  4. Weekends (Sat-Sun)")
        print("  5. Custom")
        recurrence_input = input("Choose (1-5): ").strip()

        recurrence_map = {
            "1": RecurrencePattern.DAILY,
            "2": RecurrencePattern.WEEKLY,
            "3": RecurrencePattern.WEEKDAYS,
            "4": RecurrencePattern.WEEKENDS,
            "5": RecurrencePattern.CUSTOM,
        }
        recurrence = recurrence_map.get(recurrence_input, RecurrencePattern.DAILY)

    # Due date
    due_date = None
    if commitment_type in [CommitmentType.TASK, CommitmentType.GOAL]:
        due_input = input("\n📅 Due date (YYYY-MM-DD, 'today', 'tomorrow', '+3d', or leave blank): ").strip()
        if due_input:
            due_date = parse_date(due_input)

    # Domain
    print("\n🗂️  Domain:")
    print("  1. Work")
    print("  2. Personal")
    print("  3. Health")
    print("  4. Learning")
    print("  5. General")
    domain_input = input("Choose (1-5) or enter domain: ").strip().lower()

    domain_map = {
        "1": "work",
        "2": "personal",
        "3": "health",
        "4": "learning",
        "5": "general",
    }
    domain = domain_map.get(domain_input, domain_input if domain_input else "general")

    # Priority
    priority_input = input("\n⚡ Priority (1=highest, 5=lowest, default=3): ").strip()
    priority = validate_priority(priority_input if priority_input else 3)

    # Tags
    tags_input = input("\n🏷️  Tags (comma-separated, optional): ").strip()
    tags = parse_tags(tags_input)

    # Notes
    notes = input("\n📝 Notes (optional): ").strip()

    # Confirmation
    print("\n" + "=" * 60)
    print("📋 Commitment Summary:")
    print(f"  Title: {title}")
    print(f"  Type: {commitment_type}")
    if commitment_type == CommitmentType.HABIT:
        print(f"  Recurrence: {recurrence}")
    if due_date:
        print(f"  Due: {due_date}")
    print(f"  Domain: {domain}")
    print(f"  Priority: {priority}")
    if tags:
        print(f"  Tags: {', '.join(tags)}")
    if notes:
        print(f"  Notes: {notes}")
    print("=" * 60)

    confirm = input("\n✅ Create this commitment? (y/n): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled.")
        return False

    # Create commitment
    try:
        commitment = tracker.create_commitment(
            title=title,
            commitment_type=commitment_type,
            status=CommitmentStatus.PENDING,
            due_date=due_date,
            recurrence_pattern=recurrence,
            notes=notes,
            domain=domain,
            priority=priority,
            tags=tags
        )

        # Update Commitments.md
        update_commitments_md(commitment, state_dir)

        print(f"\n✅ Commitment created successfully!")
        print(f"   ID: {commitment.id}")
        print(f"   Type: {commitment.type}")
        if commitment.is_recurring():
            print(f"   Recurrence: {commitment.recurrence_pattern}")
        print(f"\n📁 Updated:")
        print(f"   - State/CommitmentData.json")
        print(f"   - State/Commitments.md")

        return True

    except Exception as e:
        print(f"\n❌ Error creating commitment: {e}")
        return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Add new commitments with metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --title "Daily meditation" --type habit --recurrence daily --domain health
  %(prog)s --title "Submit report" --type task --due "2026-01-15" --priority 1
  %(prog)s --title "Learn Python" --type goal --tags coding,skills
  %(prog)s --interactive

Supported date formats:
  - ISO: 2026-01-15
  - Relative: today, tomorrow, +3d, +2w
  - Natural: Jan 15, January 15 2026

Recurrence patterns (for habits):
  - daily, weekly, weekdays, weekends, custom, none
        """
    )

    # Mode
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode with prompts"
    )

    # Required commitment info
    parser.add_argument(
        "--title",
        type=str,
        help="Commitment title (required unless interactive)"
    )

    parser.add_argument(
        "--type", "-t",
        type=str,
        choices=["habit", "goal", "task", "h", "g", "t"],
        default="task",
        help="Commitment type (default: task)"
    )

    # Optional metadata
    parser.add_argument(
        "--due", "-d",
        type=str,
        help="Due date (YYYY-MM-DD, 'today', 'tomorrow', '+3d')"
    )

    parser.add_argument(
        "--recurrence", "-r",
        type=str,
        choices=["daily", "weekly", "weekdays", "weekends", "custom", "none"],
        help="Recurrence pattern (for habits)"
    )

    parser.add_argument(
        "--domain",
        type=str,
        default="general",
        help="Domain category (work, personal, health, learning, general)"
    )

    parser.add_argument(
        "--priority", "-p",
        type=int,
        default=3,
        help="Priority level (1=highest, 5=lowest, default=3)"
    )

    parser.add_argument(
        "--tags",
        type=str,
        help="Comma-separated tags"
    )

    parser.add_argument(
        "--notes", "-n",
        type=str,
        default="",
        help="Additional notes"
    )

    parser.add_argument(
        "--state-dir",
        type=str,
        help="Custom state directory path"
    )

    args = parser.parse_args()

    # Determine state directory
    if args.state_dir:
        state_dir = Path(args.state_dir)
    else:
        state_dir = Path(__file__).parent.parent / "State"

    # Initialize tracker
    try:
        tracker = CommitmentTracker(state_dir=state_dir)
    except Exception as e:
        print(f"❌ Error initializing CommitmentTracker: {e}")
        return 1

    # Interactive mode
    if args.interactive:
        success = interactive_add(tracker, state_dir)
        return 0 if success else 1

    # Validate required arguments
    if not args.title:
        print("❌ Error: --title is required (or use --interactive mode)")
        parser.print_help()
        return 1

    # Validate and normalize type
    commitment_type = validate_type(args.type)
    if not commitment_type:
        print(f"❌ Error: Invalid type '{args.type}'")
        return 1

    # Parse due date
    due_date = parse_date(args.due) if args.due else None

    # Validate and normalize recurrence
    recurrence = RecurrencePattern.NONE
    if args.recurrence:
        recurrence = validate_recurrence(args.recurrence)
        if not recurrence:
            print(f"❌ Error: Invalid recurrence pattern '{args.recurrence}'")
            return 1
    elif commitment_type == CommitmentType.HABIT:
        # Default to daily for habits if not specified
        recurrence = RecurrencePattern.DAILY

    # Parse tags
    tags = parse_tags(args.tags)

    # Validate priority
    priority = validate_priority(args.priority)

    # Create commitment
    try:
        print("\n📋 Creating commitment...")

        commitment = tracker.create_commitment(
            title=args.title,
            commitment_type=commitment_type,
            status=CommitmentStatus.PENDING,
            due_date=due_date,
            recurrence_pattern=recurrence,
            notes=args.notes,
            domain=args.domain.lower(),
            priority=priority,
            tags=tags
        )

        # Update Commitments.md
        md_updated = update_commitments_md(commitment, state_dir)

        # Success message
        print("\n✅ Commitment created successfully!")
        print("=" * 60)
        print(f"  ID: {commitment.id}")
        print(f"  Title: {commitment.title}")
        print(f"  Type: {commitment.type}")
        if commitment.is_recurring():
            print(f"  Recurrence: {commitment.recurrence_pattern}")
        if commitment.due_date:
            print(f"  Due: {commitment.due_date}")
        print(f"  Domain: {commitment.domain}")
        print(f"  Priority: {commitment.priority}")
        if commitment.tags:
            print(f"  Tags: {', '.join(commitment.tags)}")
        if commitment.notes:
            print(f"  Notes: {commitment.notes}")
        print("=" * 60)

        print(f"\n📁 Updated:")
        print(f"   ✓ State/CommitmentData.json")
        if md_updated:
            print(f"   ✓ State/Commitments.md")
        else:
            print(f"   ⚠ State/Commitments.md (update failed)")

        return 0

    except Exception as e:
        print(f"\n❌ Error creating commitment: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
