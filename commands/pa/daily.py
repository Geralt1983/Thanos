"""
Personal Assistant: Daily Briefing Command

Generates a comprehensive morning briefing to start the day with clarity and focus.

Usage:
    python -m commands.pa.daily [focus]

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime
from pathlib import Path
import sys
from typing import Optional


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for daily briefing persona
SYSTEM_PROMPT = """You are Jeremy's personal assistant generating his daily briefing.

Your role:
- Start the day with clarity and focus
- Surface priorities and commitments
- Be direct and actionable
- No fluff, just what matters

You know Jeremy:
- Epic consultant (ClinDoc, Bridges, HL7 interfaces)
- Has ADHD - needs clear priorities, not overwhelming lists
- Target: 15-20 billable hours/week
- Partner Ashley, baby Sullivan (9 months)
- Values: stoic philosophy, building > consuming

Output format:
- Use markdown
- Start with top 3 priorities
- Include any calendar items
- Surface pending commitments
- Keep it scannable (bullet points)
- End with a single focus recommendation
"""


def build_context() -> str:
    """Build context from State/Memory/History files."""
    context_parts = []
    project_root = Path(__file__).parent.parent.parent

    # Yesterday's summary
    yesterday_file = project_root / "History" / "yesterday.md"
    if yesterday_file.exists():
        with open(yesterday_file) as f:
            context_parts.append(f"## Yesterday\n{f.read()}")

    # Today's state
    today_file = project_root / "State" / "Today.md"
    if today_file.exists():
        with open(today_file) as f:
            context_parts.append(f"## Current State\n{f.read()}")

    # Commitments
    commitments_file = project_root / "State" / "Commitments.md"
    if commitments_file.exists():
        with open(commitments_file) as f:
            context_parts.append(f"## Active Commitments\n{f.read()}")

    # Calendar (if available)
    calendar_file = project_root / "State" / "calendar_today.json"
    if calendar_file.exists():
        import json

        with open(calendar_file) as f:
            try:
                events = json.load(f)
                context_parts.append(f"## Today's Calendar\n{json.dumps(events, indent=2)}")
            except json.JSONDecodeError:
                pass

    # Inbox items
    inbox_dir = project_root / "Inbox"
    if inbox_dir.exists():
        inbox_items = list(inbox_dir.glob("*.md"))
        if inbox_items:
            context_parts.append(f"## Inbox Items: {len(inbox_items)} pending")

    return "\n\n".join(context_parts) if context_parts else "No context files found."


def save_to_history(response: str):
    """Save the daily briefing to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "DailyBriefings"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"daily_{timestamp.strftime('%Y-%m-%d')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Daily Briefing - {timestamp.strftime('%B %d, %Y')}\n\n")
        f.write(f"*Generated at {timestamp.strftime('%I:%M %p')}*\n\n")
        f.write(response)


def execute(args: Optional[str] = None) -> str:
    """
    Generate daily briefing.

    Args:
        args: Optional focus area (work | personal | epic | all)

    Returns:
        The generated briefing
    """
    client = get_client()

    # Build context from files
    context = build_context()

    # Build prompt
    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""Today is {today}.

{context}

Generate my daily briefing with:
1. Today's top 3 priorities (most important first)
2. Calendar/meetings summary (if any)
3. Pending commitments that need attention
4. Quick wins I can knock out
5. One focus recommendation for optimal energy use

{f"Special focus: {args}" if args else ""}

Be concise. I have ADHD - don't overwhelm me.
"""

    # Use gpt-4o-mini for cost effectiveness (simple task)
    model = "gpt-4o-mini"

    print(f"☀️  Generating daily briefing for {today}...")
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
    save_to_history(response)
    print("\n✅ Saved to History/DailyBriefings/")

    return response


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
