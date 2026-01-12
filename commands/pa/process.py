"""
Personal Assistant: Process Brain Dump Command

Intelligently categorize and process brain dump entries, converting them to tasks
or archiving them.

Usage:
    python -m commands.pa.process [options]

Options:
    --dry-run    Preview processing without making changes
    --limit N    Process only N entries at a time (default: 10)

Model: claude-3-5-haiku-20241022 (fast classification task)
"""

from datetime import datetime
from pathlib import Path
import sys
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.adapters.workos import WorkOSAdapter
from Tools.litellm_client import get_client


# =============================================================================
# DATABASE ACCESS UTILITIES
# =============================================================================


async def get_unprocessed_entries(adapter: WorkOSAdapter, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get unprocessed brain dump entries.

    Args:
        adapter: WorkOSAdapter instance
        limit: Maximum number of entries to fetch

    Returns:
        List of brain dump entries where processed=0
    """
    pool = await adapter._get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, content, category, processed, created_at
            FROM brain_dump
            WHERE processed = 0
            ORDER BY created_at ASC
            LIMIT $1
            """,
            limit,
        )
        return [adapter._row_to_dict(r) for r in rows]


async def mark_as_processed(
    adapter: WorkOSAdapter, entry_id: int, task_id: Optional[int] = None
) -> bool:
    """
    Mark a brain dump entry as processed.

    Args:
        adapter: WorkOSAdapter instance
        entry_id: ID of the brain dump entry
        task_id: Optional ID of created task if converted

    Returns:
        True if successful, False otherwise
    """
    pool = await adapter._get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            UPDATE brain_dump
            SET processed = 1,
                processed_at = NOW(),
                converted_to_task_id = $2
            WHERE id = $1
            RETURNING id
            """,
            entry_id,
            task_id,
        )
        return result is not None


async def create_task_from_entry(
    adapter: WorkOSAdapter, content: str, category: str = "personal"
) -> Optional[int]:
    """
    Create a task from a brain dump entry.

    Args:
        adapter: WorkOSAdapter instance
        content: Brain dump content to convert to task
        category: Task category (work or personal, default: personal)

    Returns:
        Task ID if successful, None otherwise
    """
    pool = await adapter._get_pool()

    # Generate a concise title from content (first 100 chars or first sentence)
    title = content[:100] if len(content) <= 100 else content[:97] + "..."

    # Split on common sentence endings for better titles
    for ending in [". ", "! ", "? "]:
        if ending in content[:100]:
            title = content[:content.index(ending, 0, 100) + 1].strip()
            break

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO tasks (
                title, description, status, category, updated_at
            )
            VALUES ($1, $2, 'backlog', $3, NOW())
            RETURNING id
            """,
            title,
            content,
            category,
        )
        return row["id"] if row else None


# =============================================================================
# MAIN COMMAND (stub for now - will be implemented in subtasks 2.2 and 2.3)
# =============================================================================


def execute(args: Optional[str] = None) -> str:
    """
    Execute brain dump processing command.

    Args:
        args: Command arguments (--dry-run, --limit N)

    Returns:
        Processing results
    """
    # TODO: Implement in subtasks 2.2 and 2.3
    return "Brain dump processing command - coming soon!"


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    result = execute(args)
    print(result)


if __name__ == "__main__":
    main()
