"""
Personal Assistant: Brainstorm Command

Facilitates creative thinking and idea generation.

Usage:
    python -m commands.pa.brainstorm [topic]

Model: claude-3-5-sonnet-20241022 (standard task - needs creativity)
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for brainstorm assistant persona
SYSTEM_PROMPT = """You are Jeremy's brainstorming partner.

Your role:
- Generate diverse ideas
- Challenge assumptions
- Build on concepts
- Connect dots across domains
- Be creative but practical

Jeremy's context:
- Epic consultant - deep healthcare IT expertise
- Building Thanos (personal AI infrastructure)
- Interested in systems thinking, stoicism
- Values: Building > consuming, automation > manual
- Thinks in conversation, not lists

Brainstorming principles:
- Start divergent (many ideas), then converge
- No judgment initially
- Build on ideas with "Yes, and..."
- Ask provocative questions
- Connect to things Jeremy knows
- End with actionable next steps
"""


def build_context() -> str:
    """Build context from available sources."""
    context_parts = []
    project_root = Path(__file__).parent.parent.parent

    # Core context (values, goals)
    core_file = project_root / "Context" / "CORE.md"
    if core_file.exists():
        with open(core_file, 'r') as f:
            context_parts.append(f"## Jeremy's Context\n{f.read()[:1000]}")

    # Recent ideas (if tracked)
    ideas_dir = project_root / "Memory" / "Ideas"
    if ideas_dir.exists():
        idea_files = sorted(ideas_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
        if idea_files:
            recent = idea_files[0]
            with open(recent, 'r') as f:
                context_parts.append(f"## Recent Brainstorm\n{f.read()[:500]}")

    return "\n\n".join(context_parts) if context_parts else ""


def save_to_history(topic: str, response: str):
    """Save brainstorm to Memory/Ideas."""
    project_root = Path(__file__).parent.parent.parent
    ideas_dir = project_root / "Memory" / "Ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    # Sanitize topic for filename
    safe_topic = "".join(c if c.isalnum() or c in " -_" else "" for c in topic[:30])
    safe_topic = safe_topic.strip().replace(" ", "_") or "brainstorm"
    filename = f"{timestamp.strftime('%Y-%m-%d')}_{safe_topic}.md"

    with open(ideas_dir / filename, 'w') as f:
        f.write(f"# Brainstorm: {topic}\n")
        f.write(f"*{timestamp.strftime('%B %d, %Y %I:%M %p')}*\n\n")
        f.write(response)


def execute(args: Optional[str] = None) -> str:
    """
    Execute brainstorm session.

    Args:
        args: Topic or question to brainstorm

    Returns:
        The generated ideas
    """
    client = get_client()

    # Build context
    context = build_context()

    topic = args if args else "What should I be thinking about right now?"

    prompt = f"""{context}

Let's brainstorm about: **{topic}**

Phase 1 - DIVERGE (many ideas):
- Generate 5-7 diverse approaches or ideas
- Don't filter yet - wild ideas welcome
- Include at least one unconventional option

Phase 2 - BUILD:
- Pick the 2-3 most promising ideas
- Develop each one further
- What would make it work?
- What could go wrong?

Phase 3 - CONVERGE:
- What's the single best path forward?
- What's the smallest next step to test it?
- What would change your mind?

Let's think together.
"""

    # Use Claude Sonnet for creative tasks (better reasoning)
    model = "claude-3-5-sonnet-20241022"

    print(f"💡 Brainstorm: {topic[:50]}...")
    print(f"📡 Using {model}\n")
    print("-" * 50)

    # Stream response
    response_parts = []
    for chunk in client.chat_stream(
        prompt=prompt,
        model=model,
        system_prompt=SYSTEM_PROMPT,
        temperature=0.9  # Higher for creativity
    ):
        print(chunk, end="", flush=True)
        response_parts.append(chunk)

    print("\n" + "-" * 50)

    response = "".join(response_parts)

    # Save to ideas
    save_to_history(topic, response)
    print(f"\n✅ Saved to Memory/Ideas/")

    return response


def main():
    """CLI entry point."""
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
    execute(args)


if __name__ == "__main__":
    main()
