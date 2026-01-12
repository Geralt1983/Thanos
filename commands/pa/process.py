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
# LLM CATEGORIZATION LOGIC
# =============================================================================

# System prompt for brain dump categorization
CATEGORIZATION_SYSTEM_PROMPT = """You are an intelligent categorization assistant for brain dump entries.

Your task is to analyze brain dump entries and determine:
1. **Category**: thought, task, idea, or worry
   - thought: Random observation, reflection, or musing
   - task: Clear action item or something that needs doing
   - idea: Creative concept, potential project, or inspiration
   - worry: Concern, anxiety, or potential problem

2. **Actionability**: Should this become a task?
   - Only convert to task if it's a clear, concrete action item
   - Be CONSERVATIVE - when in doubt, archive it
   - Thoughts, worries, and vague ideas should generally be archived
   - Only well-defined actions become tasks

3. **Task Details** (if converting to task):
   - title: Clear, concise task name (max 100 chars)
   - description: Full context from brain dump entry
   - category: "work" or "personal"

Output Format:
Return ONLY a valid JSON object with this exact structure:
{
  "category": "thought|task|idea|worry",
  "should_convert_to_task": true|false,
  "task_title": "string (only if should_convert_to_task=true)",
  "task_description": "string (only if should_convert_to_task=true)",
  "task_category": "work|personal (only if should_convert_to_task=true)",
  "reasoning": "brief explanation of categorization decision"
}

Remember: Be conservative with task creation. It's better to archive something that could be a task than to clutter the task list with vague items."""


async def analyze_brain_dump_entry(content: str) -> Dict[str, Any]:
    """
    Use LLM to analyze and categorize a brain dump entry.

    Args:
        content: The brain dump entry content to analyze

    Returns:
        Dict with categorization results:
        {
            "category": str,  # thought/task/idea/worry
            "should_convert_to_task": bool,
            "task_title": str (optional),
            "task_description": str (optional),
            "task_category": str (optional),  # work/personal
            "reasoning": str
        }
    """
    import json

    client = get_client()

    # Build prompt requesting JSON output
    prompt = f"""Analyze this brain dump entry and categorize it:

---
{content}
---

Return your analysis as a JSON object following the format specified in the system prompt."""

    try:
        # Use Haiku for fast, cost-effective classification
        model = "claude-3-5-haiku-20241022"

        response = client.chat(
            prompt=prompt,
            model=model,
            system_prompt=CATEGORIZATION_SYSTEM_PROMPT,
            temperature=0.3,  # Lower temperature for consistent categorization
            max_tokens=500,  # Categorization responses are short
        )

        # Parse JSON from response
        # Try to extract JSON if it's wrapped in markdown code blocks
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()

        result = json.loads(response_clean)

        # Validate required fields
        if "category" not in result or "should_convert_to_task" not in result:
            raise ValueError("Missing required fields in LLM response")

        # Validate category value
        valid_categories = ["thought", "task", "idea", "worry"]
        if result["category"] not in valid_categories:
            raise ValueError(f"Invalid category: {result['category']}")

        # If converting to task, ensure task fields are present
        if result["should_convert_to_task"]:
            if not result.get("task_title") or not result.get("task_category"):
                raise ValueError("Missing task fields when should_convert_to_task=true")

            # Validate task_category
            if result["task_category"] not in ["work", "personal"]:
                result["task_category"] = "personal"  # Default to personal

            # Use task_description or fall back to original content
            if not result.get("task_description"):
                result["task_description"] = content

        return result

    except json.JSONDecodeError as e:
        # Fallback: categorize as thought and archive
        return {
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": f"Failed to parse LLM response as JSON: {str(e)}. Defaulting to archive.",
        }
    except Exception as e:
        # Fallback: categorize as thought and archive
        return {
            "category": "thought",
            "should_convert_to_task": False,
            "reasoning": f"Error during categorization: {str(e)}. Defaulting to archive.",
        }


# =============================================================================
# MAIN COMMAND (stub for now - will be implemented in subtask 2.3)
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
