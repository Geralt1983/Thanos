"""
Personal Assistant: Email Management Command

Helps manage, triage, and draft email responses.

Usage:
    python -m commands.pa.email [action]

Actions:
    triage  - Prioritize unread emails
    draft   - Draft a response
    summary - Summarize email threads

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime
from pathlib import Path
import sys
from typing import Optional


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.litellm_client import get_client


# System prompt for email assistant persona
SYSTEM_PROMPT = """You are Jeremy's email management assistant.

Your role:
- Help triage and prioritize emails
- Draft professional responses
- Summarize lengthy threads
- Be efficient and action-oriented

Jeremy's context:
- Epic consultant (ClinDoc, Bridges, HL7)
- Clients: Memphis, Raleigh, Orlando, Kentucky
- Values: Direct communication, no fluff
- Has ADHD - needs clear, scannable responses

Email principles:
- Client emails are high priority
- Separate FYI from action-required
- Draft responses that sound like Jeremy (professional but warm)
- Keep responses concise
- Always include next steps when relevant
"""


def build_context() -> str:
    """Build email context from available sources."""
    context_parts = []
    project_root = Path(__file__).parent.parent.parent

    # Email context file (if exists)
    email_context = project_root / "State" / "email_context.md"
    if email_context.exists():
        with open(email_context) as f:
            context_parts.append(f"## Recent Email Context\n{f.read()}")

    # Client information
    clients_dir = project_root / "Context" / "Clients"
    if clients_dir.exists():
        client_files = list(clients_dir.glob("*.md"))
        if client_files:
            context_parts.append(f"## Active Clients: {len(client_files)}")
            for cf in client_files[:5]:  # Limit to first 5
                context_parts.append(f"- {cf.stem}")

    return "\n\n".join(context_parts) if context_parts else "No email context available."


def save_to_history(action: str, response: str):
    """Save email action to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "Email"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"email_{action}_{timestamp.strftime('%Y-%m-%d_%H%M')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Email {action.title()} - {timestamp.strftime('%B %d, %Y %I:%M %p')}\n\n")
        f.write(response)


def execute(args: Optional[str] = None) -> str:
    """
    Execute email command.

    Args:
        args: Action and details (e.g., "draft Reply to Memphis about timeline")

    Returns:
        The generated response
    """
    client = get_client()

    # Parse action from args
    if args:
        parts = args.split(maxsplit=1)
        action = parts[0].lower() if parts else "help"
        details = parts[1] if len(parts) > 1 else ""
    else:
        action = "help"
        details = ""

    # Build context
    context = build_context()

    # Build prompt based on action
    if action == "triage":
        prompt = f"""{context}

Help me triage my emails. Categorize them into:
1. **Urgent** - Needs response today
2. **Important** - Response needed within 48h
3. **FYI** - No action needed
4. **Delegate** - Someone else should handle

{f"Additional context: {details}" if details else ""}

For each category, list the emails and suggest next actions.
"""
    elif action == "draft":
        prompt = f"""{context}

Draft an email response:
{details if details else "Please provide the email context you want me to respond to."}

Requirements:
- Sound like Jeremy (professional, direct, warm)
- Keep it concise
- Include clear next steps
- Suggest a subject line if new email
"""
    elif action == "summary":
        prompt = f"""{context}

Summarize the following email thread:
{details if details else "Please provide the email thread to summarize."}

Include:
- Key points discussed
- Decisions made
- Action items
- Outstanding questions
"""
    else:
        prompt = """Help me manage my emails. Available actions:

1. **triage** - Prioritize and categorize emails
2. **draft [context]** - Draft a response
3. **summary [thread]** - Summarize an email thread

Example: /pa:email draft Reply to Baptist about the interface timeline

What would you like to do?
"""

    # Use gpt-4o-mini for cost effectiveness
    model = "gpt-4o-mini"

    print(f"📧 Email Assistant - {action.title()}")
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
