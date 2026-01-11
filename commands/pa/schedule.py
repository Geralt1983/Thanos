"""
Personal Assistant: Schedule Management Command

Helps manage calendar, scheduling, and time blocking.

Usage:
    python -m commands.pa.schedule [action]

Actions:
    today   - Review today's schedule
    week    - Week overview
    block   - Schedule focus time
    find    - Find available time

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime
from pathlib import Path
import sys
from typing import Optional


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for schedule assistant persona
SYSTEM_PROMPT = """You are Jeremy's calendar and scheduling assistant.

Your role:
- Manage calendar and time blocking
- Find optimal meeting times
- Protect focus time
- Balance work and family

Jeremy's context:
- Epic consultant - 15-20 billable hours/week target
- Has ADHD - needs protected focus blocks
- Partner Ashley, baby Sullivan (9 months)
- Best focus: mornings (8-11am when Vyvanse peaks)
- Avoid late meetings when possible

Scheduling principles:
- Batch similar meetings
- Protect mornings for deep work
- Buffer time between meetings
- Account for energy levels
- Family time is sacred (evenings/weekends)
"""


def build_context() -> str:
    """Build calendar context from available sources."""
    context_parts = []
    project_root = Path(__file__).parent.parent.parent

    # Today's calendar
    calendar_file = project_root / "State" / "calendar_today.json"
    if calendar_file.exists():
        import json

        with open(calendar_file) as f:
            try:
                events = json.load(f)
                context_parts.append(f"## Today's Calendar\n{json.dumps(events, indent=2)}")
            except json.JSONDecodeError:
                pass

    # Week calendar
    week_file = project_root / "State" / "calendar_week.json"
    if week_file.exists():
        import json

        with open(week_file) as f:
            try:
                events = json.load(f)
                context_parts.append(f"## This Week\n{json.dumps(events, indent=2)}")
            except json.JSONDecodeError:
                pass

    # Current focus
    focus_file = project_root / "State" / "CurrentFocus.md"
    if focus_file.exists():
        with open(focus_file) as f:
            context_parts.append(f"## Current Focus\n{f.read()}")

    return "\n\n".join(context_parts) if context_parts else "No calendar data available."


def save_to_history(action: str, response: str):
    """Save schedule action to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "Schedule"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"schedule_{action}_{timestamp.strftime('%Y-%m-%d_%H%M')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Schedule {action.title()} - {timestamp.strftime('%B %d, %Y %I:%M %p')}\n\n")
        f.write(response)


def execute(args: Optional[str] = None) -> str:
    """
    Execute schedule command.

    Args:
        args: Action and details

    Returns:
        The generated response
    """
    client = get_client()

    # Parse action from args
    if args:
        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else "today"
        details = parts[1] if len(parts) > 1 else ""
    else:
        action = "today"
        details = ""

    # Build context
    context = build_context()
    today = datetime.now().strftime("%A, %B %d, %Y")

    # Build prompt based on action
    if action == "today":
        prompt = f"""Today is {today}.

{context}

Review my schedule for today:
1. List all meetings/events in chronological order
2. Identify any conflicts or back-to-back issues
3. Suggest optimal focus time blocks
4. Note any preparation needed

{f"Additional context: {details}" if details else ""}
"""
    elif action == "week":
        prompt = f"""Today is {today}.

{context}

Provide a week overview:
1. Major meetings and commitments
2. Days with light vs heavy schedules
3. Best days for deep work
4. Potential scheduling conflicts
5. Recommendations for time allocation

{f"Additional context: {details}" if details else ""}
"""
    elif action == "block":
        prompt = f"""Today is {today}.

{context}

Help me schedule focus time:
{details if details else "Find optimal blocks for deep work this week."}

Consider:
- My ADHD and Vyvanse timing (peaks 2-3 hours after dose)
- Best focus time is usually 8-11am
- Need buffer after meetings to refocus
- Protect at least 2-3 hour blocks
"""
    elif action == "find":
        prompt = f"""Today is {today}.

{context}

Find available time for:
{details if details else "a 1-hour meeting this week"}

Requirements:
- Avoid fragmenting focus blocks
- Prefer afternoons for meetings
- Account for time zone differences if client meeting
- Suggest 2-3 options
"""
    else:
        prompt = """Help me manage my schedule. Available actions:

1. **today** - Review today's schedule
2. **week** - Week overview
3. **block [task]** - Schedule focus time for a task
4. **find [need]** - Find available time for meetings

Example: /pa:schedule block Deep work on Baptist report

What would you like to do?
"""

    # Use gpt-4o-mini for cost effectiveness
    model = "gpt-4o-mini"

    print(f"📅 Schedule Assistant - {action.title()}")
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
