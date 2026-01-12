"""
Personal Assistant: Daily Briefing Command

Generates a comprehensive morning briefing to start the day with clarity and focus.

Usage:
    python -m commands.pa.daily [focus]

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime
from pathlib import Path
import subprocess
import sys
from typing import Optional


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client
from Tools.briefing_engine import BriefingEngine


# System prompt for daily briefing persona (used for optional LLM enhancement)
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


def sync_calendar_quietly(timezone: str = "America/New_York") -> bool:
    """
    Quietly sync today's calendar data before generating briefing.

    Args:
        timezone: Timezone for date calculations

    Returns:
        True if sync succeeded, False otherwise
    """
    project_root = Path(__file__).parent.parent.parent
    sync_script = project_root / "Tools" / "calendar_sync.py"

    # Skip if sync script doesn't exist
    if not sync_script.exists():
        return False

    try:
        # Run sync quietly (capture output)
        result = subprocess.run(
            [sys.executable, str(sync_script), "--today", "--timezone", timezone],
            capture_output=True,
            text=True,
            timeout=30
        )

        return result.returncode == 0

    except (subprocess.TimeoutExpired, Exception):
        # Fail silently - calendar sync is optional
        return False


def build_context_legacy() -> str:
    """
    Build context from State/Memory/History files (legacy method).

    This is kept for backward compatibility and to augment BriefingEngine data.
    """
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

    return "\n\n".join(context_parts) if context_parts else ""


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


def execute(args: Optional[str] = None, use_llm_enhancement: bool = False) -> str:
    """
    Generate daily briefing using BriefingEngine.

    Args:
        args: Optional focus area (work | personal | epic | all)
        use_llm_enhancement: If True, uses LLM to enhance the template output

    Returns:
        The generated briefing
    """
    project_root = Path(__file__).parent.parent.parent

    # Initialize BriefingEngine
    engine = BriefingEngine(
        state_dir=str(project_root / "State"),
        templates_dir=str(project_root / "Templates")
    )

    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"☀️  Generating daily briefing for {today}...")
    print(f"📊 Using BriefingEngine v2.0")

    # Auto-sync today's calendar (quietly)
    sync_calendar_quietly()

    try:
        # Gather context using the new engine
        context = engine.gather_context()

        # Render briefing using template
        try:
            briefing = engine.render_briefing(
                briefing_type="morning",
                context=context,
                energy_level=None  # Could prompt user for this
            )

            # Add legacy context (Yesterday, Today, Calendar, Inbox) as custom sections
            legacy_context = build_context_legacy()
            if legacy_context:
                briefing += f"\n\n---\n\n## Additional Context\n\n{legacy_context}"

            # Add focus area if specified
            if args:
                briefing += f"\n\n---\n\n**Today's Special Focus:** {args}"

            print("-" * 50)

            # If LLM enhancement is requested, pass through LLM for personalization
            if use_llm_enhancement:
                print(f"✨ Enhancing with {model}...\n")
                client = get_client()
                model = "gpt-4o-mini"

                enhance_prompt = f"""Today is {today}.

Here's the generated briefing:

{briefing}

Please review and enhance this briefing to:
1. Make it more conversational and personalized for Jeremy
2. Add any insights or connections between tasks
3. Keep the same structure but polish the language
4. Maintain the ADHD-friendly format (scannable, not overwhelming)

{f"Special focus: {args}" if args else ""}
"""

                response_parts = []
                for chunk in client.chat_stream(
                    prompt=enhance_prompt,
                    model=model,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.7
                ):
                    print(chunk, end="", flush=True)
                    response_parts.append(chunk)

                briefing = "".join(response_parts)
            else:
                # Just print the template-generated briefing
                print(briefing)

            print("\n" + "-" * 50)

        except ValueError as e:
            # Fallback to legacy LLM-based generation if template rendering fails
            print(f"⚠️  Template rendering unavailable: {e}")
            print(f"📡 Falling back to LLM generation with gpt-4o-mini\n")
            print("-" * 50)

            briefing = _generate_with_llm_legacy(context, args)
            print(briefing)
            print("\n" + "-" * 50)

    except Exception as e:
        # Complete fallback to original implementation
        print(f"⚠️  BriefingEngine error: {e}")
        print(f"📡 Falling back to legacy implementation\n")
        print("-" * 50)

        from commands.pa import daily as legacy_daily
        context_str = legacy_daily.build_context()
        briefing = _generate_with_llm_legacy_full(context_str, args)
        print(briefing)
        print("\n" + "-" * 50)

    # Save to history
    save_to_history(briefing)
    print("\n✅ Saved to History/DailyBriefings/")

    return briefing


def _generate_with_llm_legacy(context: dict, args: Optional[str] = None) -> str:
    """Generate briefing using LLM with BriefingEngine context."""
    client = get_client()
    model = "gpt-4o-mini"

    # Format context for LLM
    context_str = f"""## Active Commitments
{chr(10).join([f"- {c['title']} (Category: {c['category']})" + (f" - Due: {c['deadline']}" if c.get('deadline') else "")
               for c in context.get('commitments', []) if not c.get('is_complete', False)])}

## This Week's Tasks
{chr(10).join([f"- {t['text']}" for t in context.get('this_week', {}).get('tasks', []) if not t.get('is_complete', False)])}

## Current Focus
{chr(10).join([f"- {area}" for area in context.get('current_focus', {}).get('focus_areas', [])])}
"""

    # Add legacy context
    legacy_context = build_context_legacy()
    if legacy_context:
        context_str += f"\n\n{legacy_context}"

    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""Today is {today}.

{context_str}

Generate my daily briefing with:
1. Today's top 3 priorities (most important first)
2. Calendar/meetings summary (if any)
3. Pending commitments that need attention
4. Quick wins I can knock out
5. One focus recommendation for optimal energy use

{f"Special focus: {args}" if args else ""}

Be concise. I have ADHD - don't overwhelm me.
"""

    response_parts = []
    for chunk in client.chat_stream(
        prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
    ):
        response_parts.append(chunk)

    return "".join(response_parts)


def _generate_with_llm_legacy_full(context_str: str, args: Optional[str] = None) -> str:
    """Complete fallback to original LLM generation."""
    client = get_client()
    model = "gpt-4o-mini"

    today = datetime.now().strftime("%A, %B %d, %Y")
    prompt = f"""Today is {today}.

{context_str}

Generate my daily briefing with:
1. Today's top 3 priorities (most important first)
2. Calendar/meetings summary (if any)
3. Pending commitments that need attention
4. Quick wins I can knock out
5. One focus recommendation for optimal energy use

{f"Special focus: {args}" if args else ""}

Be concise. I have ADHD - don't overwhelm me.
"""

    response_parts = []
    for chunk in client.chat_stream(
        prompt=prompt, model=model, system_prompt=SYSTEM_PROMPT, temperature=0.7
    ):
        response_parts.append(chunk)

    return "".join(response_parts)


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
