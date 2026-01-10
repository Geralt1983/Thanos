"""
Personal Assistant: Task Management Command

Helps manage, prioritize, and track tasks.

Usage:
    python -m commands.pa.tasks [action]

Actions:
    list    - List active tasks
    add     - Add a new task
    next    - Get next recommended action
    review  - Review and prioritize tasks

Model: gpt-4o-mini (simple task - cost effective)
"""

import sys
from pathlib import Path
from datetime import datetime
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
        with open(commitments_file, 'r') as f:
            context_parts.append(f"## Active Commitments\n{f.read()}")

    # Today's focus
    today_file = project_root / "State" / "Today.md"
    if today_file.exists():
        with open(today_file, 'r') as f:
            context_parts.append(f"## Today\n{f.read()}")

    # Current focus
    focus_file = project_root / "State" / "CurrentFocus.md"
    if focus_file.exists():
        with open(focus_file, 'r') as f:
            context_parts.append(f"## Current Focus\n{f.read()}")

    # Inbox (tasks to process)
    inbox_dir = project_root / "Inbox"
    if inbox_dir.exists():
        inbox_items = list(inbox_dir.glob("*.md"))
        if inbox_items:
            items_text = []
            for item in inbox_items[:10]:  # Limit to 10
                with open(item, 'r') as f:
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

    with open(history_dir / filename, 'w') as f:
        f.write(f"# Tasks {action.title()} - {timestamp.strftime('%B %d, %Y %I:%M %p')}\n\n")
        f.write(response)


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
    else:
        prompt = """Help me manage my tasks. Available actions:

1. **list** - Show all active tasks
2. **add [task]** - Add a new task
3. **next** - Get the single next action
4. **review** - Prioritize and clean up tasks

Example: /pa:tasks add Follow up with Memphis about interface spec

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
        prompt=prompt,
        model=model,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.7
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
