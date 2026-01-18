#!/usr/bin/env python3
"""
Thanos CLI - Personal AI Assistant

NATURAL LANGUAGE INTERFACE:
  Ask questions naturally and Thanos will route to the appropriate agent or command.

Examples:
  thanos What should I focus on today?
  thanos I'm feeling overwhelmed with tasks
  thanos Should I take this client?

EXPLICIT COMMANDS:
  thanos interactive              Launch interactive mode
  thanos chat <message>           Chat with auto-routing
  thanos agent <name> <message>   Chat with specific agent
  thanos run <command> [args]     Run a specific command
  thanos usage                    Show API usage statistics
  thanos agents                   List available agents
  thanos commands                 List available commands

SHORTCUTS:
  thanos daily                    Run daily briefing (pa:daily)
  thanos morning                  Run daily briefing (pa:daily)
  thanos brief                    Run daily briefing (pa:daily)
  thanos email                    Check emails (pa:email)
  thanos tasks                    Review tasks (pa:tasks)
  thanos schedule                 Check schedule (pa:schedule)
  thanos weekly                   Weekly review (pa:weekly)
  thanos export                   Export data (pa:export)

COMMAND PATTERNS:
  Commands can be called with prefix:name pattern:
    thanos pa:daily
    thanos pa:email
    thanos custom:action

VISUAL FEEDBACK SYSTEM:
  This CLI provides visual feedback during long-running operations:

  1. STATIC INDICATOR (🟣):
     - Shown in thanos.py before natural language routing
     - Immediate visual confirmation that input was received
     - Backward compatible with existing test expectations

  2. ANIMATED SPINNERS:
     - Handled by ThanosOrchestrator (not visible in this file)
     - Command execution: Cyan "Executing {command}..." spinner
     - Chat operations: Magenta "Thinking..." or "Thinking as {agent}..." spinner
     - TTY-aware: Only shown in terminals, silent in pipes/redirects
     - Auto-stops before streaming output to avoid interference

  The combination provides clear feedback throughout the request lifecycle:
  - User sees 🟣 immediately (input acknowledged)
  - User sees animated spinner during API call (processing)
  - User sees response text (completion)
"""

from pathlib import Path
import re
import sys
import os

# Load environment variables (API keys)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass


# Ensure Thanos project is in path
THANOS_DIR = Path(__file__).parent
if str(THANOS_DIR) not in sys.path:
    sys.path.insert(0, str(THANOS_DIR))

from Tools.thanos_orchestrator import ThanosOrchestrator  # noqa: E402


# ========================================================================
# Command Shortcuts Mapping
# ========================================================================

COMMAND_SHORTCUTS = {
    # Daily briefing shortcuts
    "daily": "pa:daily",
    "morning": "pa:daily",
    "brief": "pa:daily",
    "briefing": "pa:daily",
    # Email shortcuts
    "email": "pa:email",
    "emails": "pa:email",
    "inbox": "pa:email",
    # Schedule shortcuts
    "schedule": "pa:schedule",
    "calendar": "pa:schedule",
    # Task shortcuts
    "tasks": "pa:tasks",
    "task": "pa:tasks",
    # Weekly review shortcuts
    "weekly": "pa:weekly",
    "week": "pa:weekly",
    "review": "pa:weekly",
    # Data export shortcuts
    "export": "pa:export",
}

# ========================================================================
# System Commands
# ========================================================================

SYSTEM_COMMANDS = {
    "usage",
    "agents",
    "commands",
    "help",
    "-h",
    "--help",
    "interactive",
    "i",
    "chat",
    "agent",
    "run",
}

# ========================================================================
# Natural Language Detection
# ========================================================================


def is_natural_language(text: str) -> bool:
    """
    Detect if input is natural language vs command.

    Returns True if input contains:
    - Question words (what, why, how, when, where, who, should, can, etc.)
    - Self-references (I, I'm, my, me, myself)
    - Multi-word sentences (3+ words)
    - Emotional words (help, need, want, feel, overwhelmed, stuck, etc.)

    Args:
        text: Input text to analyze

    Returns:
        True if natural language detected, False otherwise
    """
    if not text or not text.strip():
        return False

    # Normalize text for detection
    text_lower = text.lower().strip()

    # Question word patterns (start of sentence)
    question_words = [
        "what",
        "why",
        "how",
        "when",
        "where",
        "who",
        "should",
        "can",
        "could",
        "would",
        "will",
        "is",
        "am",
        "are",
        "do",
        "does",
        "did",
    ]

    # Check if starts with question word
    first_word = text_lower.split()[0] if text_lower.split() else ""
    if first_word in question_words:
        return True

    # Self-reference patterns
    self_patterns = [
        r"\bi\b",  # "I"
        r"\bi\'m\b",  # "I'm"
        r"\bim\b",  # "Im"
        r"\bi\'ve\b",  # "I've"
        r"\bive\b",  # "Ive"
        r"\bmy\b",  # "my"
        r"\bme\b",  # "me"
        r"\bmyself\b",  # "myself"
    ]

    for pattern in self_patterns:
        if re.search(pattern, text_lower):
            return True

    # Emotional/help words
    emotional_words = [
        "help",
        "need",
        "want",
        "feel",
        "feeling",
        "tired",
        "overwhelmed",
        "struggling",
        "stuck",
        "confused",
    ]

    for word in emotional_words:
        if word in text_lower:
            return True

    # Multi-word sentences (3+ words suggests natural language)
    word_count = len(text_lower.split())
    return word_count >= 3


# ========================================================================
# Usage Display
# ========================================================================


def print_usage():
    """Print usage information."""
    print(__doc__)


# ========================================================================
# Main CLI Entry Point
# ========================================================================


def main():
    """
    Main CLI entry point.

    Parses command line arguments and routes to appropriate handlers:
    - System commands (help, usage, agents, commands, interactive)
    - Explicit commands (chat, agent, run)
    - Command shortcuts (daily, email, tasks, etc.)
    - Command patterns (prefix:name)
    - Natural language (routed via orchestrator)
    """
    args = sys.argv[1:]

    # No arguments - print usage
    if not args:
        print_usage()
        sys.exit(0)

    # Get first argument (command/first word)
    first_arg = args[0].lower()

    # Help flags
    if first_arg in ["help", "-h", "--help"]:
        print_usage()
        return

    # Initialize orchestrator
    from Tools.server_manager import ServerManager
    ServerManager.ensure_chroma_running()
    
    orchestrator = ThanosOrchestrator(str(THANOS_DIR))

    # ====================================================================
    # System Commands
    # ====================================================================

    # Interactive mode
    if first_arg in ["interactive", "i"]:
        try:
            from Tools.thanos_interactive import ThanosInteractive

            interactive = ThanosInteractive(orchestrator)
            interactive.run()
        except ImportError:
            print("Error: Interactive mode not available")
            sys.exit(1)
        return

    # Chat command
    if first_arg == "chat":
        if len(args) < 2:
            print("Usage: thanos chat <message>")
            print('Example: thanos chat "What should I focus on today?"')
            sys.exit(1)
        message = " ".join(args[1:])
        orchestrator.chat(message, stream=True)
        return

    # Agent command
    if first_arg == "agent":
        if len(args) < 3:
            print("Usage: thanos agent <agent_name> <message>")
            print('Example: thanos agent coach "Help me focus"')
            print()
            print("Available agents:")
            for _agent_id, agent in orchestrator.agents.items():
                print(f"  {agent.name}")
            sys.exit(1)
        agent_name = args[1]
        message = " ".join(args[2:])
        orchestrator.chat(message, agent=agent_name, stream=True)
        return

    # Run command
    if first_arg == "run":
        if len(args) < 2:
            print("Usage: thanos run <command> [args]")
            print("Example: thanos run pa:daily")
            sys.exit(1)
        command = args[1]
        extra_args = " ".join(args[2:]) if len(args) > 2 else ""
        orchestrator.run_command(command, extra_args, stream=True)
        return

    # Usage command
    if first_arg == "usage":
        try:
            usage = orchestrator.get_usage()
            print("\nClaude API Usage (Last 30 Days)")
            print("=" * 40)
            print(f"  Total Tokens:     {usage['total_tokens']:,}")
            print(f"  Total Cost:       ${usage['total_cost_usd']:.2f}")
            print(f"  Total Calls:      {usage['total_calls']}")
            print(f"  Monthly Projection: ${usage['projected_monthly_cost']:.2f}")
            print()
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        return

    # Agents command
    if first_arg == "agents":
        print("\nAvailable Agents")
        print("=" * 40)
        for _agent_id, agent in orchestrator.agents.items():
            print(f"\n{agent.name}")
            print(f"  Role: {agent.role}")
            if agent.triggers:
                print(f"  Triggers: {', '.join(agent.triggers)}")
        print()
        return

    # Commands command
    if first_arg == "commands":
        print("\nAvailable Commands")
        print("=" * 40)
        for cmd in orchestrator.list_commands():
            print(f"  {cmd}")
        print()
        return

    # ====================================================================
    # Command Routing
    # ====================================================================

    # Single word - check shortcuts
    if len(args) == 1:
        # Check if it's a shortcut
        if first_arg in COMMAND_SHORTCUTS:
            command = COMMAND_SHORTCUTS[first_arg]
            print(f"Running {command}...")
            orchestrator.run_command(command, "", stream=True)
            return

        # Check if it's an explicit command pattern (prefix:name)
        if ":" in first_arg:
            parts = first_arg.split(":")
            if len(parts) == 2:
                orchestrator.run_command(first_arg, "", stream=True)
                return

    # Multiple words or non-shortcut
    full_text = " ".join(args)

    # Check if first word is explicit command pattern (with additional args)
    if ":" in first_arg:
        parts = first_arg.split(":")
        if len(parts) == 2:
            command = first_arg
            extra_args = " ".join(args[1:]) if len(args) > 1 else ""
            orchestrator.run_command(command, extra_args, stream=True)
            return

    # Natural language detection
    if is_natural_language(full_text):
        # ================================================================
        # VISUAL FEEDBACK: Static indicator (🟣)
        # ================================================================
        # WHY PRINT 🟣 HERE:
        # - Provides immediate visual confirmation of input
        # - Backward compatible with test expectations (test_thanos_cli.py)
        # - Shown BEFORE routing to distinguish from spinner feedback
        #
        # SPINNER INTEGRATION:
        # - After routing, orchestrator will show animated spinner
        # - Spinner is handled in run_command() or chat() (not here)
        # - This keeps thanos.py simple and orchestrator responsible for API feedback
        print("🟣", flush=True)  # Static visual indicator
        orchestrator.route(full_text, stream=True)
        return

    # Default: treat as natural language (fallback)
    # Same visual feedback pattern as above
    print("🟣", flush=True)  # Static visual indicator
    orchestrator.route(full_text, stream=True)


if __name__ == "__main__":
    main()
