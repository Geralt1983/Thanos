"""
Personal Assistant: Weekly Review Command

Comprehensive weekly review for reflection, planning, and continuous improvement.

Usage:
    python -m commands.pa.weekly [phase]

Phases:
    review  - Full weekly review (default)
    reflect - Just reflection phase
    plan    - Just planning phase
    metrics - Weekly metrics summary

Model: claude-opus-4.5 (strategic task - deep reasoning)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for strategic weekly review
SYSTEM_PROMPT = """You are Jeremy's strategic thinking partner for weekly reviews.

Your role:
- Facilitate deep reflection
- Surface patterns and insights
- Challenge assumptions about priorities
- Connect actions to long-term goals
- Be thoughtful, not just efficient

Jeremy's context:
- Epic consultant - $500k annual revenue target
- Target: 15-20 billable hours/week
- Has ADHD - patterns matter for optimization
- Partner Ashley, baby Sullivan (9 months)
- Building Thanos (personal AI infrastructure)
- Values: Stoic philosophy, systems thinking

Weekly review principles:
- Look back before looking forward
- Celebrate wins, even small ones
- Identify root causes, not just symptoms
- Connect to quarterly/annual goals
- End with clear priorities, not a long list
- Ask uncomfortable questions when needed
"""


def build_context() -> str:
    """Build comprehensive context for weekly review."""
    context_parts = []
    project_root = Path(__file__).parent.parent.parent

    # Week summary (if exists)
    week_file = project_root / "History" / "week_summary.md"
    if week_file.exists():
        with open(week_file, 'r') as f:
            context_parts.append(f"## Week Summary\n{f.read()}")

    # Goals and targets
    goals_file = project_root / "State" / "Goals.md"
    if goals_file.exists():
        with open(goals_file, 'r') as f:
            context_parts.append(f"## Goals\n{f.read()}")

    # Commitments
    commitments_file = project_root / "State" / "Commitments.md"
    if commitments_file.exists():
        with open(commitments_file, 'r') as f:
            context_parts.append(f"## Commitments\n{f.read()}")

    # Recent daily briefings
    briefings_dir = project_root / "History" / "DailyBriefings"
    if briefings_dir.exists():
        week_ago = datetime.now() - timedelta(days=7)
        recent_briefings = []
        for bf in sorted(briefings_dir.glob("daily_*.md"), reverse=True)[:7]:
            try:
                # Parse date from filename
                date_str = bf.stem.replace("daily_", "")
                bf_date = datetime.strptime(date_str, "%Y-%m-%d")
                if bf_date >= week_ago:
                    with open(bf, 'r') as f:
                        recent_briefings.append(f"### {date_str}\n{f.read()[:500]}")
            except (ValueError, OSError):
                pass
        if recent_briefings:
            context_parts.append(f"## Daily Briefings (Past Week)\n" + "\n\n".join(recent_briefings[:3]))

    # Core context
    core_file = project_root / "Context" / "CORE.md"
    if core_file.exists():
        with open(core_file, 'r') as f:
            context_parts.append(f"## Core Values & Goals\n{f.read()[:800]}")

    # Client work summary
    clients_dir = project_root / "Context" / "Clients"
    if clients_dir.exists():
        client_files = list(clients_dir.glob("*.md"))
        if client_files:
            client_list = [f"- {cf.stem}" for cf in client_files]
            context_parts.append(f"## Active Clients\n" + "\n".join(client_list))

    return "\n\n".join(context_parts) if context_parts else "No historical data available yet."


def save_to_history(phase: str, response: str):
    """Save weekly review to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "WeeklyReviews"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    week_num = timestamp.isocalendar()[1]
    filename = f"weekly_{timestamp.strftime('%Y')}_W{week_num:02d}_{phase}.md"

    with open(history_dir / filename, 'w') as f:
        f.write(f"# Weekly {phase.title()} - Week {week_num}, {timestamp.strftime('%Y')}\n")
        f.write(f"*{timestamp.strftime('%B %d, %Y')}*\n\n")
        f.write(response)


def execute(args: Optional[str] = None) -> str:
    """
    Execute weekly review.

    Args:
        args: Phase (review | reflect | plan | metrics)

    Returns:
        The generated review
    """
    client = get_client()

    # Parse phase from args
    phase = args.strip().lower() if args else "review"
    if phase not in ["review", "reflect", "plan", "metrics"]:
        phase = "review"

    # Build context
    context = build_context()
    today = datetime.now()
    week_num = today.isocalendar()[1]

    # Build prompt based on phase
    if phase == "reflect":
        prompt = f"""Week {week_num} Reflection

{context}

Guide me through reflection:

**1. What happened this week?**
- Key accomplishments (celebrate these)
- What didn't get done? (no judgment, just facts)

**2. What worked well?**
- Patterns to repeat
- Energy and focus observations

**3. What didn't work?**
- Friction points
- Root causes (not just symptoms)

**4. Surprises and learnings?**
- Unexpected insights
- What did I learn about myself?

Help me see patterns I might miss.
"""
    elif phase == "plan":
        prompt = f"""Week {week_num + 1} Planning

{context}

Help me plan the upcoming week:

**1. Top 3 Priorities**
- What absolutely must happen?
- Why these specifically?

**2. Time Allocation**
- Billable work target: 15-20 hours
- How should hours be distributed across clients?

**3. Focus Blocks**
- What needs deep work time?
- When should I schedule it?

**4. Risks and Contingencies**
- What could derail the week?
- How to protect priorities?

**5. Weekly Intention**
- One theme or mindset for the week

Be specific and actionable.
"""
    elif phase == "metrics":
        prompt = f"""Week {week_num} Metrics Summary

{context}

Provide a metrics-focused summary:

**Hours & Revenue**
- Billable hours this week (target: 15-20)
- Revenue generated
- Hours by client
- Efficiency ($/hour)

**Tasks & Productivity**
- Tasks completed
- Tasks added
- Net progress

**Health & Energy**
- Energy pattern observations
- Focus quality

**Trends**
- Compared to last week
- Compared to monthly average

Just the numbers and key insights. No fluff.
"""
    else:  # Full review
        prompt = f"""Week {week_num} Comprehensive Review

{context}

Guide me through a complete weekly review:

## Part 1: REFLECT (Look Back)

**Accomplishments**
- What got done? (be specific)
- What am I proud of?

**Incomplete Items**
- What didn't happen?
- Why? (be honest about root causes)

**Patterns**
- Energy patterns observed
- Productivity patterns
- Avoidance patterns (if any)

**Learnings**
- What worked well?
- What would I do differently?

## Part 2: ASSESS (Current State)

**Goal Progress**
- Revenue: Progress toward $500k?
- Hours: Averaging 15-20/week?
- Life: Family time quality?

**Client Health**
- Status of each active client
- Any concerns?

**Personal**
- Health/energy trends
- Relationship with Ashley
- Time with Sullivan

## Part 3: PLAN (Look Forward)

**Next Week Priorities** (Top 3 only)
1. Most important commitment
2. Second priority
3. Third priority

**Schedule Strategy**
- Focus blocks needed
- Meeting batching
- Buffer time

**Risks**
- What could derail next week?
- Mitigation strategy

**Weekly Intention**
- One word or phrase theme

---

Take your time. This is my most important reflection of the week.
Ask me uncomfortable questions if you see patterns I'm avoiding.
"""

    # Use Claude Opus for strategic thinking
    model = "claude-opus-4.5"

    print(f"📊 Weekly {phase.title()} - Week {week_num}")
    print(f"📡 Using {model}")
    print(f"⏱️  This may take 30-60 seconds for comprehensive analysis...\n")
    print("-" * 60)

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

    print("\n" + "-" * 60)

    response = "".join(response_parts)

    # Save to history
    save_to_history(phase, response)
    print(f"\n✅ Saved to History/WeeklyReviews/")

    return response


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
