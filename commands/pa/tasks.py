"""
Personal Assistant: Task Management Command

Helps manage, prioritize, and track tasks.

Usage:
    python -m commands.pa.tasks [action]

Actions:
    list     - List active tasks
    add      - Add a new task
    next     - Get next recommended action
    review   - Review and prioritize tasks
    complete - Mark a task as complete

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime
from pathlib import Path
import re
import sys
from typing import Optional


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for task assistant persona
SYSTEM_PROMPT = """You are Jeremy's task management assistant.

Your role:
- Track and prioritize tasks
- Surface what needs attention
- Help break down big tasks
- Keep things moving

Jeremy's context:
- Epic consultant - clients: Memphis, Raleigh, Orlando, Kentucky
- Target: 15-20 billable hours/week
- Has ADHD - needs clear priorities, not long lists
- Values: Getting things done > perfect planning

Task principles:
- Top 3 priorities at any time
- Break big tasks into next actions
- Surface blocked items
- Celebrate completions
- Eisenhower matrix: Urgent/Important
"""


def build_context() -> str:
    """Build task context from available sources."""
    context_parts = []
    project_root = Path(__file__).parent.parent.parent

    # Commitments
    commitments_file = project_root / "State" / "Commitments.md"
    if commitments_file.exists():
        with open(commitments_file) as f:
            context_parts.append(f"## Active Commitments\n{f.read()}")

    # Today's focus
    today_file = project_root / "State" / "Today.md"
    if today_file.exists():
        with open(today_file) as f:
            context_parts.append(f"## Today\n{f.read()}")

    # Current focus
    focus_file = project_root / "State" / "CurrentFocus.md"
    if focus_file.exists():
        with open(focus_file) as f:
            context_parts.append(f"## Current Focus\n{f.read()}")

    # Inbox (tasks to process)
    inbox_dir = project_root / "Inbox"
    if inbox_dir.exists():
        inbox_items = list(inbox_dir.glob("*.md"))
        if inbox_items:
            items_text = []
            for item in inbox_items[:10]:  # Limit to 10
                with open(item) as f:
                    content = f.read()[:200]  # First 200 chars
                    items_text.append(f"- **{item.stem}**: {content[:100]}...")
            context_parts.append(f"## Inbox ({len(inbox_items)} items)\n" + "\n".join(items_text))

    return "\n\n".join(context_parts) if context_parts else "No task data available."


def save_to_history(action: str, response: str):
    """Save task action to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "Tasks"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"tasks_{action}_{timestamp.strftime('%Y-%m-%d_%H%M')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Tasks {action.title()} - {timestamp.strftime('%B %d, %Y %I:%M %p')}\n\n")
        f.write(response)


def find_matching_task(search_term: str) -> list[tuple[Path, str, int]]:
    """Find tasks matching the search term in state files.

    Searches Today.md, Commitments.md, and ThisWeek.md for incomplete
    tasks (- [ ]) that match the search term (case-insensitive).

    Args:
        search_term: Partial or full task name to search for

    Returns:
        List of tuples: (file_path, full_line, line_number)
    """
    project_root = Path(__file__).parent.parent.parent
    state_files = [
        project_root / "State" / "Today.md",
        project_root / "State" / "Commitments.md",
        project_root / "State" / "ThisWeek.md",
    ]

    matches = []
    search_lower = search_term.lower()

    for state_file in state_files:
        if not state_file.exists():
            continue

        try:
            content = state_file.read_text()
            lines = content.split("\n")

            for line_num, line in enumerate(lines):
                # Match incomplete checkbox items:
                # - [ ] task, * [ ] task, 1. [ ] task
                checkbox_match = re.match(r"^(\s*)([\-\*]|\d+\.)\s*\[ \]\s*(.+)", line)
                if checkbox_match:
                    task_text = checkbox_match.group(3)
                    # Case-insensitive partial match
                    if search_lower in task_text.lower():
                        matches.append((state_file, line, line_num))
        except Exception:
            continue

    return matches


def complete_task(search_term: str) -> str:
    """Mark a task as complete in state files.

    Finds the first matching incomplete task and marks it as complete
    by replacing '- [ ]' with '- [x]' (or similar checkbox formats).

    Args:
        search_term: Partial or full task name to complete

    Returns:
        Status message indicating success or failure
    """
    if not search_term.strip():
        return "❌ Please provide a task name to complete.\n\nUsage: /pa:tasks complete <task name>"

    matches = find_matching_task(search_term)

    if not matches:
        return (
            f"❌ No incomplete task found matching: '{search_term}'\n\n"
            f"Try `/pa:tasks list` to see available tasks."
        )

    if len(matches) > 1:
        # Multiple matches - show them and ask for more specific input
        result = f"⚠️ Found {len(matches)} matching tasks. Please be more specific:\n\n"
        for file_path, line, _ in matches:
            file_name = file_path.name
            # Clean up the line for display
            task_text = re.sub(r"^[\s\-\*\d\.]*\[ \]\s*", "", line)
            result += f"  • [{file_name}] {task_text.strip()}\n"
        return result

    # Single match - complete it
    file_path, matched_line, line_num = matches[0]

    try:
        content = file_path.read_text()
        lines = content.split("\n")

        # Replace the checkbox with completed version
        # Handle various formats: - [ ], * [ ], 1. [ ]
        original_line = lines[line_num]
        completed_line = re.sub(r"(\s*)([\-\*]|\d+\.)\s*\[ \]", r"\1\2 [x]", original_line)

        lines[line_num] = completed_line

        # Write back to file
        file_path.write_text("\n".join(lines))

        # Extract task name for confirmation
        task_text = re.sub(r"^[\s\-\*\d\.]*\[[ x]\]\s*", "", completed_line)

        return f"✅ Task completed!\n\n**{task_text.strip()}**\n\nUpdated: {file_path.name}"

    except Exception as e:
        return f"❌ Error completing task: {str(e)}"


def execute(args: Optional[str] = None) -> str:
    """
    Execute task command.

    Args:
        args: Action and details

    Returns:
        The generated response
    """
    client = get_client()

    # Parse action from args
    if args:
        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else "list"
        details = parts[1] if len(parts) > 1 else ""
    else:
        action = "next"
        details = ""

    # Build context
    context = build_context()

    # Build prompt based on action
    if action == "list":
        prompt = f"""{context}

List my active tasks organized by:
1. **Due Today** - Must complete today
2. **This Week** - Due within 7 days
3. **Backlog** - No urgent deadline
4. **Blocked** - Waiting on something

For each task, show:
- Task name
- Client (if applicable)
- Due date
- Status

{f"Filter: {details}" if details else ""}
"""
    elif action == "add":
        prompt = f"""{context}

Help me capture this new task:
{details if details else "Please describe the task to add."}

I need:
1. Clear task name
2. Suggested priority (high/medium/low)
3. Suggested due date (if any)
4. Next action to get started
5. Which file to add it to (Commitments.md or Today.md)
"""
    elif action == "next":
        prompt = f"""{context}

What should I do right now?

Consider:
1. What's most urgent?
2. What's most important?
3. Current energy level (assume medium if unknown)
4. Time available (assume 30 min block)

Give me ONE clear next action, not a list.
Why this one? (one sentence)
"""
    elif action == "review":
        prompt = f"""{context}

Review my tasks and help me:

1. **Prioritize**: What's the right order?
2. **Prune**: What can be dropped or delegated?
3. **Break down**: What big tasks need smaller steps?
4. **Unblock**: What's stuck and how to unstick it?

Use Eisenhower matrix:
- Urgent + Important → Do first
- Important + Not Urgent → Schedule
- Urgent + Not Important → Delegate
- Neither → Consider dropping

{f"Focus on: {details}" if details else ""}
"""
    elif action == "complete":
        # Handle task completion directly without LLM
        result = complete_task(details)
        print("✅ Task Manager - Complete")
        print("-" * 50)
        print(result)
        print("-" * 50)
        save_to_history(action, result)
        return result

    else:
        prompt = """Help me manage my tasks. Available actions:

1. **list** - Show all active tasks
2. **add [task]** - Add a new task
3. **next** - Get the single next action
4. **review** - Prioritize and clean up tasks
5. **complete [task]** - Mark a task as done

Example: /pa:tasks add Follow up with Memphis about interface spec
Example: /pa:tasks complete Kentucky spec

What would you like to do?
"""

    # Use gpt-4o-mini for cost effectiveness
    model = "gpt-4o-mini"

    print(f"✅ Task Manager - {action.title()}")
    print(f"📡 Using {model}\n")
    print("-" * 50)

    # Stream response
    response_parts = []
    for chunk in client.chat_stream(
        prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
    ):
        print(chunk, end="", flush=True)
        response_parts.append(chunk)

    print("\n" + "-" * 50)

    response = "".join(response_parts)

    # Save to history
    save_to_history(action, response)

    return response


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
