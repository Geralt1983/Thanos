#!/usr/bin/env python3
"""
Thanos Orchestrator - Routes requests to appropriate agents and commands.
Replaces Claude Code's built-in skill system with direct API integration.

Usage:
    from Tools.thanos_orchestrator import thanos

    # Run a command
    response = thanos.run_command("pa:daily")

    # Chat with an agent
    response = thanos.chat("I'm overwhelmed", agent="ops")

    # Auto-route based on content
    response = thanos.route("What should I do today?")
"""

import os
import re
import json
import sys
from pathlib import Path
from typing import Optional, Dict, List, Any, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

# Ensure Thanos project is in path for imports
_THANOS_DIR = Path(__file__).parent.parent
if str(_THANOS_DIR) not in sys.path:
    sys.path.insert(0, str(_THANOS_DIR))

# Lazy import for API client - only needed for chat/run, not hooks
if TYPE_CHECKING:
    from Tools.claude_api_client import ClaudeAPIClient

_api_client_module = None

def _get_api_client_module():
    """Lazy load the API client module."""
    global _api_client_module
    if _api_client_module is None:
        from Tools import claude_api_client
        _api_client_module = claude_api_client
    return _api_client_module


@dataclass
class Agent:
    """Represents a Thanos agent with personality and triggers."""
    name: str
    role: str
    voice: str
    triggers: List[str]
    content: str
    file_path: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> 'Agent':
        """Parse an agent definition from markdown file."""
        content = file_path.read_text()

        # Extract frontmatter
        frontmatter = {}
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                for line in parts[1].strip().split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        key = key.strip()
                        value = value.strip()
                        # Parse list values
                        if value.startswith('['):
                            value = json.loads(value.replace("'", '"'))
                        frontmatter[key] = value
                content = parts[2]

        return cls(
            name=frontmatter.get('name', file_path.stem),
            role=frontmatter.get('role', 'Assistant'),
            voice=frontmatter.get('voice', 'helpful'),
            triggers=frontmatter.get('triggers', []),
            content=content.strip(),
            file_path=str(file_path)
        )


@dataclass
class Command:
    """Represents a Thanos command/skill."""
    name: str
    description: str
    parameters: List[str]
    workflow: str
    content: str
    file_path: str

    @classmethod
    def from_markdown(cls, file_path: Path) -> 'Command':
        """Parse a command definition from markdown file."""
        content = file_path.read_text()

        # Extract command name from first heading
        name_match = re.search(r'^#\s+(/\w+:\w+)', content, re.MULTILINE)
        name = name_match.group(1) if name_match else file_path.stem

        # Extract description (first paragraph after heading)
        desc_match = re.search(r'^#[^\n]+\n+([^\n#]+)', content, re.MULTILINE)
        description = desc_match.group(1).strip() if desc_match else ""

        # Extract parameters section
        params = []
        params_match = re.search(r'## Parameters\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if params_match:
            for line in params_match.group(1).split('\n'):
                if line.strip().startswith('-'):
                    params.append(line.strip()[1:].strip())

        # Extract workflow section
        workflow_match = re.search(r'## Workflow\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        workflow = workflow_match.group(1).strip() if workflow_match else ""

        return cls(
            name=name,
            description=description,
            parameters=params,
            workflow=workflow,
            content=content,
            file_path=str(file_path)
        )


class ThanosOrchestrator:
    """Main orchestrator for Thanos personal assistant."""

    def __init__(self, base_dir: str = None, api_client: "ClaudeAPIClient" = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.api_client = api_client

        # Load components
        self.agents: Dict[str, Agent] = {}
        self.commands: Dict[str, Command] = {}
        self.context: Dict[str, str] = {}

        self._load_agents()
        self._load_commands()
        self._load_context()

    def _load_agents(self):
        """Load all agent definitions."""
        agents_dir = self.base_dir / "Agents"
        if agents_dir.exists():
            for file in agents_dir.glob("*.md"):
                if file.name != "AgentFactory.md":
                    try:
                        agent = Agent.from_markdown(file)
                        self.agents[agent.name.lower()] = agent
                    except Exception as e:
                        print(f"Warning: Failed to load agent {file}: {e}")

    def _load_commands(self):
        """Load all command definitions."""
        commands_dir = self.base_dir / "commands"
        if commands_dir.exists():
            for subdir in commands_dir.iterdir():
                if subdir.is_dir():
                    for file in subdir.glob("*.md"):
                        if file.name != "README.md":
                            try:
                                cmd = Command.from_markdown(file)
                                # Store by multiple keys
                                self.commands[cmd.name] = cmd
                                self.commands[file.stem] = cmd
                                # Also store as prefix:name
                                prefix = subdir.name
                                self.commands[f"{prefix}:{file.stem}"] = cmd
                            except Exception as e:
                                print(f"Warning: Failed to load command {file}: {e}")

    def _load_context(self):
        """Load context files."""
        context_dir = self.base_dir / "Context"
        if context_dir.exists():
            for file in context_dir.glob("*.md"):
                try:
                    self.context[file.stem] = file.read_text()
                except Exception as e:
                    print(f"Warning: Failed to load context {file}: {e}")

    def _build_system_prompt(self, agent: Optional[Agent] = None,
                             command: Optional[Command] = None,
                             include_context: bool = True) -> str:
        """Build system prompt for API call."""
        parts = []

        # Base identity
        parts.append("""You are Thanos - Jeremy's personal AI assistant and external prefrontal cortex.
You manage his entire life: work, family, health, and goals.
You are proactive, direct, and warm but honest.
You track patterns and surface them.""")

        # Add core context
        if include_context and "CORE" in self.context:
            parts.append("\n## About Jeremy\n" + self.context["CORE"])

        # Add agent personality
        if agent:
            parts.append(f"\n## Current Role: {agent.role}")
            parts.append(f"Voice: {agent.voice}")
            parts.append(f"\n{agent.content}")

        # Add command context
        if command:
            parts.append(f"\n## Current Command: {command.name}")
            parts.append(f"{command.description}")
            parts.append(f"\n### Workflow\n{command.workflow}")

        # Add current state
        state_file = self.base_dir / "State" / "Today.md"
        if state_file.exists():
            try:
                today_state = state_file.read_text()
                parts.append(f"\n## Today's State\n{today_state[:2000]}")  # Limit size
            except:
                pass

        return "\n\n".join(parts)

    def _ensure_client(self):
        """Ensure API client is initialized."""
        if self.api_client is None:
            api_module = _get_api_client_module()
            self.api_client = api_module.init_client(str(self.base_dir / "config" / "api.json"))

    def find_agent(self, message: str) -> Optional[Agent]:
        """Find the best matching agent for a message."""
        message_lower = message.lower()

        for agent in self.agents.values():
            for trigger in agent.triggers:
                if trigger.lower() in message_lower:
                    return agent

        # Default to Ops for task-related queries
        if any(word in message_lower for word in ['task', 'do', 'plan', 'schedule']):
            return self.agents.get('ops')

        return None

    def find_command(self, query: str) -> Optional[Command]:
        """Find a command by name or pattern."""
        # Direct lookup
        if query in self.commands:
            return self.commands[query]

        # Try with common prefixes
        for prefix in ['pa', 'sc']:
            key = f"{prefix}:{query}"
            if key in self.commands:
                return self.commands[key]

        # Fuzzy match
        query_lower = query.lower()
        for name, cmd in self.commands.items():
            if query_lower in name.lower():
                return cmd

        return None

    def run_command(self, command_name: str, args: str = "",
                    stream: bool = False) -> str:
        """Execute a command and return the response."""
        self._ensure_client()

        command = self.find_command(command_name)
        if not command:
            return f"Command not found: {command_name}"

        system_prompt = self._build_system_prompt(command=command)

        user_prompt = f"Execute the {command.name} command."
        if args:
            user_prompt += f"\nArguments: {args}"
        user_prompt += "\n\nFollow the workflow exactly and provide the output in the specified format."

        if stream:
            result = ""
            for chunk in self.api_client.chat_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                operation=f"command:{command_name}"
            ):
                print(chunk, end="", flush=True)
                result += chunk
            print()
            return result
        else:
            return self.api_client.chat(
                prompt=user_prompt,
                system_prompt=system_prompt,
                operation=f"command:{command_name}"
            )

    def chat(self, message: str, agent: Optional[str] = None,
             stream: bool = False) -> str:
        """Chat with a specific agent or auto-detect."""
        self._ensure_client()

        # Get agent
        if agent:
            agent_obj = self.agents.get(agent.lower())
        else:
            agent_obj = self.find_agent(message)

        system_prompt = self._build_system_prompt(agent=agent_obj)

        if stream:
            result = ""
            for chunk in self.api_client.chat_stream(
                prompt=message,
                system_prompt=system_prompt,
                operation=f"chat:{agent_obj.name if agent_obj else 'default'}"
            ):
                print(chunk, end="", flush=True)
                result += chunk
            print()
            return result
        else:
            return self.api_client.chat(
                prompt=message,
                system_prompt=system_prompt,
                operation=f"chat:{agent_obj.name if agent_obj else 'default'}"
            )

    def route(self, message: str, stream: bool = False) -> str:
        """Auto-route a message to the appropriate handler."""
        # Check for command pattern
        cmd_match = re.match(r'^/(\w+:\w+)\s*(.*)?$', message)
        if cmd_match:
            return self.run_command(cmd_match.group(1), cmd_match.group(2) or "", stream)

        # Otherwise chat with auto-detected agent
        return self.chat(message, stream=stream)

    def list_commands(self) -> List[str]:
        """List all available commands."""
        seen = set()
        result = []
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                seen.add(cmd.name)
                result.append(f"{cmd.name} - {cmd.description[:50]}...")
        return sorted(result)

    def list_agents(self) -> List[str]:
        """List all available agents."""
        return [f"{a.name} ({a.role})" for a in self.agents.values()]

    def get_usage(self, days: int = 30) -> Dict:
        """Get API usage summary."""
        self._ensure_client()
        return self.api_client.get_usage_summary(days)


# Singleton instance
_thanos_instance = None

def get_thanos(base_dir: str = None) -> ThanosOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _thanos_instance
    if _thanos_instance is None:
        _thanos_instance = ThanosOrchestrator(base_dir)
    return _thanos_instance

# Convenience alias
thanos = None  # Will be initialized on first use


def init_thanos(base_dir: str = None) -> ThanosOrchestrator:
    """Initialize the global thanos instance."""
    global thanos
    thanos = ThanosOrchestrator(base_dir)
    return thanos


def _log_hook_error(error: str):
    """Log hook errors to file without disrupting hook execution."""
    try:
        log_dir = Path.home() / ".claude" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "hooks.log"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(log_file, 'a') as f:
            f.write(f"[{timestamp}] [thanos-orchestrator] {error}\n")
    except Exception:
        pass  # Silently fail - we can't break hooks


def _output_hook_response(context: str):
    """Output JSON in Claude hook format."""
    print(json.dumps({
        "hookSpecificOutput": {
            "additionalContext": context
        }
    }))


def handle_hook(event: str, args: List[str], base_dir: Path):
    """Handle hook events from Claude Code lifecycle.

    This function is designed to be fast and reliable:
    - No API calls
    - Only local file reads
    - Graceful error handling (always exit 0)
    - Outputs JSON in Claude hook format

    Args:
        event: Hook event name (morning-brief, session-end)
        args: Additional arguments
        base_dir: Thanos base directory
    """
    try:
        if event == "morning-brief":
            # Fast path: read state files, no API calls
            from Tools.state_reader import StateReader
            reader = StateReader(base_dir / "State")
            ctx = reader.get_quick_context()

            parts = []
            if ctx["focus"]:
                parts.append(f"FOCUS: {ctx['focus']}")
            if ctx["top3"]:
                # Abbreviate to first 2 items
                items = ctx["top3"][:2]
                if len(items) == 1:
                    parts.append(f"TOP: {items[0]}")
                else:
                    parts.append(f"TOP: {items[0]} / {items[1]}...")
            if ctx["pending_commitments"] > 0:
                parts.append(f"PENDING: {ctx['pending_commitments']} commitments")
            if ctx["blockers"]:
                parts.append(f"BLOCKED: {ctx['blockers'][0]}")

            if parts:
                context = "[THANOS] " + " | ".join(parts)
                if ctx["is_morning"]:
                    context += "\n[ACTION] Consider running /pa:daily for full morning briefing"
                _output_hook_response(context)

        elif event == "session-end":
            # Log session to History/Sessions
            history_dir = base_dir / "History" / "Sessions"
            history_dir.mkdir(parents=True, exist_ok=True)

            now = datetime.now()
            filename = now.strftime("%Y-%m-%d-%H%M.md")
            log_path = history_dir / filename

            # Don't overwrite existing logs (multiple sessions same minute)
            if log_path.exists():
                # Append a suffix
                for i in range(2, 10):
                    alt_path = history_dir / now.strftime(f"%Y-%m-%d-%H%M-{i}.md")
                    if not alt_path.exists():
                        log_path = alt_path
                        break

            session_log = f"""# Session: {now.strftime("%Y-%m-%d %H:%M")}

## Summary
- Duration: ~unknown (hook-logged)
- Topics: [to be populated]

## Context at End
"""
            # Add quick context snapshot
            try:
                from Tools.state_reader import StateReader
                reader = StateReader(base_dir / "State")
                ctx = reader.get_quick_context()
                if ctx["focus"]:
                    session_log += f"- Focus: {ctx['focus']}\n"
                if ctx["pending_commitments"] > 0:
                    session_log += f"- Pending commitments: {ctx['pending_commitments']}\n"
            except Exception:
                session_log += "- [Context unavailable]\n"

            session_log += f"""
## State Changes
- Check git diff for file changes

---
*Auto-logged by Thanos Orchestrator*
"""

            log_path.write_text(session_log)
            # Output confirmation (not as hook context, just for logging)
            print(f"Session logged: {log_path.name}", file=__import__('sys').stderr)

        else:
            _log_hook_error(f"Unknown hook event: {event}")

    except Exception as e:
        _log_hook_error(f"{event} error: {e}")
        # Always exit cleanly for hooks
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Thanos Orchestrator")
        print("==================")
        print("Usage:")
        print("  python thanos_orchestrator.py list-commands")
        print("  python thanos_orchestrator.py list-agents")
        print("  python thanos_orchestrator.py run <command> [args]")
        print("  python thanos_orchestrator.py chat <message>")
        print("  python thanos_orchestrator.py usage")
        print("  python thanos_orchestrator.py hook <event> [args]")
        print()
        print("Hook events:")
        print("  morning-brief   - Generate quick morning context (no API)")
        print("  session-end     - Log session to History/Sessions/")
        sys.exit(0)

    # Hook subcommand - handle before ThanosOrchestrator init for speed
    if sys.argv[1] == "hook":
        if len(sys.argv) < 3:
            print("Usage: thanos_orchestrator.py hook <event> [args]", file=sys.stderr)
            sys.exit(0)  # Exit 0 even on error for hooks

        event = sys.argv[2]
        hook_args = sys.argv[3:] if len(sys.argv) > 3 else []
        base_dir = Path(__file__).parent.parent
        handle_hook(event, hook_args, base_dir)
        sys.exit(0)

    t = ThanosOrchestrator()

    if sys.argv[1] == "list-commands":
        print("Available Commands:")
        for cmd in t.list_commands():
            print(f"  {cmd}")

    elif sys.argv[1] == "list-agents":
        print("Available Agents:")
        for agent in t.list_agents():
            print(f"  {agent}")

    elif sys.argv[1] == "run" and len(sys.argv) >= 3:
        cmd_name = sys.argv[2]
        args = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        print(f"Running {cmd_name}...")
        print("-" * 40)
        t.run_command(cmd_name, args, stream=True)

    elif sys.argv[1] == "chat" and len(sys.argv) >= 3:
        message = " ".join(sys.argv[2:])
        t.chat(message, stream=True)

    elif sys.argv[1] == "usage":
        try:
            usage = t.get_usage()
            print("API Usage (Last 30 Days)")
            print(f"   Tokens: {usage['total_tokens']:,}")
            print(f"   Cost: ${usage['total_cost_usd']:.2f}")
            print(f"   Monthly Projection: ${usage['projected_monthly_cost']:.2f}")
        except Exception as e:
            print(f"Error getting usage: {e}")

    else:
        print(f"Unknown command: {sys.argv[1]}")
