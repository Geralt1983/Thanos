#!/usr/bin/env python3
"""
Commitment Update Command - Mark commitments as complete, update status, or modify details.

This command allows users to update existing commitments including:
- Marking as complete or missed
- Updating status (pending, in_progress, completed, missed, cancelled)
- Modifying details (title, due date, priority, domain, tags, notes)
- Rescheduling or postponing commitments
- Deleting commitments

Usage:
    python commitment_update.py <commitment_id> [options]
    python commitment_update.py <commitment_id> --complete
    python commitment_update.py <commitment_id> --status completed
    python commitment_update.py <commitment_id> --reschedule "+3d"
    python commitment_update.py <commitment_id> --interactive

Examples:
    # Mark as complete
    python commitment_update.py abc123 --complete
    python commitment_update.py abc123 --complete --notes "Great session!"

    # Mark as missed
    python commitment_update.py abc123 --missed --notes "Overslept"

    # Update status
    python commitment_update.py abc123 --status in_progress

    # Reschedule (postpone by 3 days)
    python commitment_update.py abc123 --reschedule "+3d"

    # Update multiple fields
    python commitment_update.py abc123 --title "Updated title" --priority 1 --domain work

    # Cancel commitment
    python commitment_update.py abc123 --cancel

    # Delete commitment
    python commitment_update.py abc123 --delete

    # Interactive mode
    python commitment_update.py abc123 --interactive
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

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


def validate_status(status_str: str) -> Optional[str]:
    """Validate and normalize commitment status."""
    status_str = status_str.lower()
    mapping = {
        "pending": CommitmentStatus.PENDING,
        "p": CommitmentStatus.PENDING,
        "in_progress": CommitmentStatus.IN_PROGRESS,
        "in-progress": CommitmentStatus.IN_PROGRESS,
        "inprogress": CommitmentStatus.IN_PROGRESS,
        "ip": CommitmentStatus.IN_PROGRESS,
        "completed": CommitmentStatus.COMPLETED,
        "complete": CommitmentStatus.COMPLETED,
        "done": CommitmentStatus.COMPLETED,
        "c": CommitmentStatus.COMPLETED,
        "missed": CommitmentStatus.MISSED,
        "m": CommitmentStatus.MISSED,
        "cancelled": CommitmentStatus.CANCELLED,
        "canceled": CommitmentStatus.CANCELLED,
        "cancel": CommitmentStatus.CANCELLED,
        "x": CommitmentStatus.CANCELLED,
    }
    return mapping.get(status_str)


def validate_priority(priority: int) -> int:
    """Validate and clamp priority to 1-5 range."""
    try:
        p = int(priority)
        return max(1, min(5, p))
    except (ValueError, TypeError):
        return 3


def update_commitments_md_status(
    commitment: Commitment,
    old_commitment: Commitment,
    state_dir: Path
) -> bool:
    """
    Update Commitments.md to reflect commitment changes.

    Updates the checkbox status and details for the commitment in Commitments.md.

    Args:
        commitment: Updated commitment
        old_commitment: Original commitment (for finding the line)
        state_dir: Path to State directory

    Returns:
        True if successful, False otherwise
    """
    md_file = state_dir / "Commitments.md"

    if not md_file.exists():
        return False

    try:
        lines = md_file.read_text().split("\n")

        # Find the commitment line by searching for the title
        # This is a simple approach - may need refinement for duplicate titles
        for i, line in enumerate(lines):
            if old_commitment.title in line and line.strip().startswith("- ["):
                # Build new line
                checkbox = "- [x]" if commitment.status == CommitmentStatus.COMPLETED else "- [ ]"
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
                    checkbox = "- [x] ⚡" if commitment.status == CommitmentStatus.COMPLETED else "- [ ] ⚡"

                lines[i] = f"{checkbox} {title}"

                # Write back
                md_file.write_text("\n".join(lines))
                return True

        return False

    except Exception as e:
        print(f"⚠️  Warning: Could not update Commitments.md: {e}")
        return False


def remove_from_commitments_md(commitment: Commitment, state_dir: Path) -> bool:
    """
    Remove a commitment from Commitments.md.

    Args:
        commitment: Commitment to remove
        state_dir: Path to State directory

    Returns:
        True if successful, False otherwise
    """
    md_file = state_dir / "Commitments.md"

    if not md_file.exists():
        return False

    try:
        lines = md_file.read_text().split("\n")

        # Find and remove the commitment line
        new_lines = []
        for line in lines:
            if commitment.title in line and line.strip().startswith("- ["):
                continue  # Skip this line
            new_lines.append(line)

        md_file.write_text("\n".join(new_lines))
        return True

    except Exception as e:
        print(f"⚠️  Warning: Could not update Commitments.md: {e}")
        return False


def interactive_update(
    tracker: CommitmentTracker,
    commitment_id: str,
    state_dir: Path
) -> bool:
    """
    Interactive mode for updating a commitment.

    Prompts user for what to update.

    Args:
        tracker: CommitmentTracker instance
        commitment_id: ID of commitment to update
        state_dir: Path to State directory

    Returns:
        True if commitment was updated, False otherwise
    """
    # Get existing commitment
    commitment = tracker.get_commitment(commitment_id)
    if not commitment:
        print(f"❌ Commitment not found: {commitment_id}")
        return False

    # Keep copy for Commitments.md update
    old_commitment = Commitment.from_dict(commitment.to_dict())

    print(f"\n📋 Update Commitment: {commitment.title}")
    print("=" * 60)
    print(f"  ID: {commitment.id}")
    print(f"  Type: {commitment.type}")
    print(f"  Status: {commitment.status}")
    if commitment.due_date:
        print(f"  Due: {commitment.due_date}")
    print(f"  Domain: {commitment.domain}")
    print(f"  Priority: {commitment.priority}")
    if commitment.tags:
        print(f"  Tags: {', '.join(commitment.tags)}")
    print("=" * 60)

    print("\n🔧 What would you like to do?")
    print("  1. Mark as complete")
    print("  2. Mark as missed")
    print("  3. Update status")
    print("  4. Reschedule (change due date)")
    print("  5. Modify details (title, priority, etc.)")
    print("  6. Cancel commitment")
    print("  7. Delete commitment")
    print("  0. Exit without changes")

    choice = input("\nChoose (0-7): ").strip()

    if choice == "0":
        print("❌ Cancelled.")
        return False

    elif choice == "1":
        # Mark as complete
        notes = input("Completion notes (optional): ").strip()
        tracker.mark_completed(commitment_id, notes=notes if notes else None)
        commitment = tracker.get_commitment(commitment_id)
        update_commitments_md_status(commitment, old_commitment, state_dir)
        print(f"\n✅ Marked '{commitment.title}' as complete!")
        if commitment.is_recurring():
            print(f"   🔥 Streak: {commitment.streak_count} days")
        return True

    elif choice == "2":
        # Mark as missed
        notes = input("Why was it missed? (optional): ").strip()
        tracker.mark_missed(commitment_id, notes=notes if notes else None)
        commitment = tracker.get_commitment(commitment_id)
        update_commitments_md_status(commitment, old_commitment, state_dir)
        print(f"\n📝 Marked '{commitment.title}' as missed")
        return True

    elif choice == "3":
        # Update status
        print("\n📊 Status:")
        print("  1. Pending")
        print("  2. In Progress")
        print("  3. Completed")
        print("  4. Missed")
        print("  5. Cancelled")
        status_input = input("Choose (1-5): ").strip()

        status_map = {
            "1": CommitmentStatus.PENDING,
            "2": CommitmentStatus.IN_PROGRESS,
            "3": CommitmentStatus.COMPLETED,
            "4": CommitmentStatus.MISSED,
            "5": CommitmentStatus.CANCELLED,
        }

        if status_input in status_map:
            new_status = status_map[status_input]
            # Use .value to ensure we get the string value, not the enum
            status_value = new_status.value if hasattr(new_status, 'value') else new_status
            tracker.update_commitment(commitment_id, status=status_value)
            commitment = tracker.get_commitment(commitment_id)
            update_commitments_md_status(commitment, old_commitment, state_dir)
            print(f"\n✅ Updated status to: {commitment.status}")
            return True
        else:
            print("❌ Invalid status.")
            return False

    elif choice == "4":
        # Reschedule
        current = commitment.due_date or "not set"
        new_due = input(f"New due date (current: {current}, format: YYYY-MM-DD, +3d): ").strip()
        if new_due:
            parsed_date = parse_date(new_due)
            if parsed_date:
                tracker.update_commitment(commitment_id, due_date=parsed_date)
                commitment = tracker.get_commitment(commitment_id)
                update_commitments_md_status(commitment, old_commitment, state_dir)
                print(f"\n✅ Rescheduled to: {parsed_date}")
                return True
        print("❌ Invalid date or cancelled.")
        return False

    elif choice == "5":
        # Modify details
        updates = {}

        title = input(f"Title (current: '{commitment.title}', press Enter to keep): ").strip()
        if title:
            updates['title'] = title

        priority = input(f"Priority (current: {commitment.priority}, 1-5, press Enter to keep): ").strip()
        if priority:
            updates['priority'] = validate_priority(priority)

        domain = input(f"Domain (current: {commitment.domain}, press Enter to keep): ").strip()
        if domain:
            updates['domain'] = domain.lower()

        tags_input = input(f"Tags (current: {', '.join(commitment.tags)}, comma-separated, press Enter to keep): ").strip()
        if tags_input:
            updates['tags'] = parse_tags(tags_input)

        notes = input(f"Notes (current: '{commitment.notes}', press Enter to keep): ").strip()
        if notes:
            updates['notes'] = notes

        if updates:
            tracker.update_commitment(commitment_id, **updates)
            commitment = tracker.get_commitment(commitment_id)
            update_commitments_md_status(commitment, old_commitment, state_dir)
            print(f"\n✅ Updated {len(updates)} field(s)")
            return True
        else:
            print("❌ No changes made.")
            return False

    elif choice == "6":
        # Cancel commitment
        confirm = input(f"Cancel '{commitment.title}'? (y/n): ").strip().lower()
        if confirm == 'y':
            tracker.update_commitment(commitment_id, status=CommitmentStatus.CANCELLED)
            commitment = tracker.get_commitment(commitment_id)
            update_commitments_md_status(commitment, old_commitment, state_dir)
            print(f"\n✅ Cancelled '{commitment.title}'")
            return True
        else:
            print("❌ Cancelled.")
            return False

    elif choice == "7":
        # Delete commitment
        confirm = input(f"⚠️  DELETE '{commitment.title}' permanently? This cannot be undone. (yes/no): ").strip().lower()
        if confirm == 'yes':
            tracker.delete_commitment(commitment_id)
            remove_from_commitments_md(commitment, state_dir)
            print(f"\n✅ Deleted '{commitment.title}' permanently")
            return True
        else:
            print("❌ Cancelled.")
            return False

    else:
        print("❌ Invalid choice.")
        return False


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Update commitments: mark as complete, update status, or modify details",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s abc123 --complete
  %(prog)s abc123 --complete --notes "Great session!"
  %(prog)s abc123 --missed --notes "Overslept"
  %(prog)s abc123 --status in_progress
  %(prog)s abc123 --reschedule "+3d"
  %(prog)s abc123 --title "Updated title" --priority 1
  %(prog)s abc123 --cancel
  %(prog)s abc123 --delete
  %(prog)s abc123 --interactive

Supported date formats for --reschedule:
  - ISO: 2026-01-15
  - Relative: today, tomorrow, +3d, +2w
  - Natural: Jan 15, January 15 2026

Status values:
  - pending, in_progress, completed, missed, cancelled
        """
    )

    # Commitment ID (required)
    parser.add_argument(
        "commitment_id",
        type=str,
        nargs='?',
        help="Commitment ID to update"
    )

    # Mode
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Interactive mode with prompts"
    )

    # Quick actions
    parser.add_argument(
        "--complete", "-c",
        action="store_true",
        help="Mark as complete"
    )

    parser.add_argument(
        "--missed", "-m",
        action="store_true",
        help="Mark as missed"
    )

    parser.add_argument(
        "--cancel",
        action="store_true",
        help="Cancel the commitment"
    )

    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the commitment permanently"
    )

    # Update options
    parser.add_argument(
        "--status", "-s",
        type=str,
        help="Update status (pending, in_progress, completed, missed, cancelled)"
    )

    parser.add_argument(
        "--reschedule", "-r",
        type=str,
        help="Reschedule to new due date (YYYY-MM-DD, 'today', '+3d')"
    )

    parser.add_argument(
        "--title", "-t",
        type=str,
        help="Update title"
    )

    parser.add_argument(
        "--priority", "-p",
        type=int,
        help="Update priority (1-5)"
    )

    parser.add_argument(
        "--domain",
        type=str,
        help="Update domain"
    )

    parser.add_argument(
        "--tags",
        type=str,
        help="Update tags (comma-separated)"
    )

    parser.add_argument(
        "--notes", "-n",
        type=str,
        help="Add or update notes"
    )

    parser.add_argument(
        "--state-dir",
        type=str,
        help="Custom state directory path"
    )

    args = parser.parse_args()

    # Validate commitment_id
    if not args.commitment_id:
        if not args.interactive:
            print("❌ Error: commitment_id is required")
            parser.print_help()
            return 1
        else:
            commitment_id = input("Enter commitment ID: ").strip()
            if not commitment_id:
                print("❌ Error: commitment_id is required")
                return 1
            args.commitment_id = commitment_id

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

    # Get commitment
    commitment = tracker.get_commitment(args.commitment_id)
    if not commitment:
        print(f"❌ Commitment not found: {args.commitment_id}")
        print("\n💡 Tip: Use 'python commands/commitment_list.py' to see all commitments")
        return 1

    # Keep copy for Commitments.md update
    old_commitment = Commitment.from_dict(commitment.to_dict())

    # Interactive mode
    if args.interactive:
        success = interactive_update(tracker, args.commitment_id, state_dir)
        return 0 if success else 1

    # Quick actions
    if args.complete:
        tracker.mark_completed(args.commitment_id, notes=args.notes)
        commitment = tracker.get_commitment(args.commitment_id)
        update_commitments_md_status(commitment, old_commitment, state_dir)
        print(f"\n✅ Marked '{commitment.title}' as complete!")
        if commitment.is_recurring():
            print(f"   🔥 Streak: {commitment.streak_count} days")
            print(f"   📊 Completion rate: {commitment.completion_rate:.1f}%")
        print(f"\n📁 Updated:")
        print(f"   ✓ State/CommitmentData.json")
        print(f"   ✓ State/Commitments.md")
        return 0

    if args.missed:
        tracker.mark_missed(args.commitment_id, notes=args.notes)
        commitment = tracker.get_commitment(args.commitment_id)
        update_commitments_md_status(commitment, old_commitment, state_dir)
        print(f"\n📝 Marked '{commitment.title}' as missed")
        if args.notes:
            print(f"   Note: {args.notes}")
        print(f"\n📁 Updated:")
        print(f"   ✓ State/CommitmentData.json")
        print(f"   ✓ State/Commitments.md")
        return 0

    if args.cancel:
        tracker.update_commitment(args.commitment_id, status=CommitmentStatus.CANCELLED.value)
        commitment = tracker.get_commitment(args.commitment_id)
        update_commitments_md_status(commitment, old_commitment, state_dir)
        print(f"\n✅ Cancelled '{commitment.title}'")
        print(f"\n📁 Updated:")
        print(f"   ✓ State/CommitmentData.json")
        print(f"   ✓ State/Commitments.md")
        return 0

    if args.delete:
        print(f"⚠️  About to DELETE '{commitment.title}' permanently")
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm == 'yes':
            tracker.delete_commitment(args.commitment_id)
            remove_from_commitments_md(commitment, state_dir)
            print(f"\n✅ Deleted '{commitment.title}' permanently")
            print(f"\n📁 Updated:")
            print(f"   ✓ State/CommitmentData.json")
            print(f"   ✓ State/Commitments.md")
            return 0
        else:
            print("❌ Deletion cancelled.")
            return 1

    # Build updates dict for other options
    updates = {}

    if args.status:
        status = validate_status(args.status)
        if status:
            # Use .value to ensure we get the string value, not the enum
            updates['status'] = status.value if hasattr(status, 'value') else status
        else:
            print(f"❌ Invalid status: {args.status}")
            return 1

    if args.reschedule:
        due_date = parse_date(args.reschedule)
        if due_date:
            updates['due_date'] = due_date
        else:
            print(f"❌ Invalid date: {args.reschedule}")
            return 1

    if args.title:
        updates['title'] = args.title

    if args.priority:
        updates['priority'] = validate_priority(args.priority)

    if args.domain:
        updates['domain'] = args.domain.lower()

    if args.tags:
        updates['tags'] = parse_tags(args.tags)

    if args.notes:
        updates['notes'] = args.notes

    # Apply updates
    if updates:
        tracker.update_commitment(args.commitment_id, **updates)
        commitment = tracker.get_commitment(args.commitment_id)
        update_commitments_md_status(commitment, old_commitment, state_dir)

        print(f"\n✅ Updated commitment: {commitment.title}")
        print("=" * 60)
        for key, value in updates.items():
            print(f"  {key}: {value}")
        print("=" * 60)

        print(f"\n📁 Updated:")
        print(f"   ✓ State/CommitmentData.json")
        print(f"   ✓ State/Commitments.md")

        return 0

    # If no action specified, show help
    print("❌ No action specified. Use --complete, --missed, --status, or other options.")
    print("   Or use --interactive for interactive mode.")
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
