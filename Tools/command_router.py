#!/usr/bin/env python3
"""
CommandRouter - Routes and executes slash commands for Thanos Interactive Mode

Single Responsibility: Command parsing and delegation
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
import os
from pathlib import Path
import re
from typing import Callable, Optional


# MemOS integration (optional - graceful degradation if unavailable)
try:
    from Tools.memos import MemOS, get_memos, init_memos

    MEMOS_AVAILABLE = True
except ImportError:
    MEMOS_AVAILABLE = False
    MemOS = None


# ANSI color codes (copied from thanos_interactive.py)
class Colors:
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class CommandAction(Enum):
    """Action to take after command execution"""

    CONTINUE = "continue"
    QUIT = "quit"


@dataclass
class CommandResult:
    """Result from command execution"""

    action: CommandAction = CommandAction.CONTINUE
    message: Optional[str] = None
    success: bool = True


class CommandRouter:
    """Routes and executes slash commands"""

    def __init__(
        self,
        orchestrator,  # ThanosOrchestrator
        session_manager,  # SessionManager
        context_manager,  # ContextManager
        state_reader,  # StateReader
        thanos_dir: Path,
    ):
        """
        Initialize with injected dependencies.

        Args:
            orchestrator: ThanosOrchestrator for /run command and agent info
            session_manager: SessionManager for history operations
            context_manager: ContextManager for context usage info
            state_reader: StateReader for state and commitments
            thanos_dir: Path to Thanos root directory
        """
        self.orchestrator = orchestrator
        self.session = session_manager
        self.context_mgr = context_manager
        self.state_reader = state_reader
        self.thanos_dir = thanos_dir
        self.current_agent = "ops"  # Track current agent
        self.current_model = None  # None = use default from config
        self.current_prompt_mode = None  # None = use default from config

        # Available models (from config/api.json)
        self._available_models = {
            "opus": "claude-opus-4-5-20251101",
            "sonnet": "claude-sonnet-4-20250514",
            "haiku": "claude-3-5-haiku-20241022",
        }
        self._default_model = "opus"

        # MemOS integration (lazy initialization)
        self._memos: Optional[MemOS] = None
        self._memos_initialized = False

        # Calendar adapter integration (lazy initialization)
        self._calendar_adapter = None
        self._calendar_initialized = False

        # Command registry: {command_name: (handler_function, description, arg_names)}
        self._commands: dict[str, tuple[Callable, str, list[str]]] = {}
        self._register_commands()

        # Build trigger patterns for intelligent routing
        self._trigger_patterns: dict[str, list[re.Pattern]] = {}
        self._build_trigger_patterns()

    def _build_trigger_patterns(self):
        """Build regex patterns from agent triggers for intelligent routing."""
        for agent_name, agent in self.orchestrator.agents.items():
            triggers = getattr(agent, "triggers", None)
            if triggers:
                patterns = []
                for trigger in triggers:
                    # Build case-insensitive pattern for each trigger phrase
                    # Escape special regex chars and create word boundary pattern
                    escaped = re.escape(trigger.lower())
                    patterns.append(re.compile(escaped, re.IGNORECASE))
                self._trigger_patterns[agent_name] = patterns

    def _get_memos(self) -> Optional["MemOS"]:
        """Get MemOS instance, initializing if needed."""
        if not MEMOS_AVAILABLE:
            return None

        if not self._memos_initialized:
            try:
                # Try to get existing instance
                self._memos = get_memos()
                self._memos_initialized = True
            except Exception:
                # Initialize new instance
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Can't use asyncio.run in running loop
                        self._memos = None
                    else:
                        self._memos = loop.run_until_complete(init_memos())
                        self._memos_initialized = True
                except Exception:
                    self._memos = None

        return self._memos

    def _run_async(self, coro):
        """Run async coroutine from sync context."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new loop for nested async
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(coro)
        except Exception:
            return None

    def _get_calendar_adapter(self):
        """Get calendar adapter, initializing if needed."""
        if not self._calendar_initialized:
            try:
                from Tools.adapters import GoogleCalendarAdapter, GOOGLE_CALENDAR_AVAILABLE
                if GOOGLE_CALENDAR_AVAILABLE:
                    self._calendar_adapter = GoogleCalendarAdapter()
                    self._calendar_initialized = True
                else:
                    self._calendar_adapter = None
                    self._calendar_initialized = True
            except Exception:
                self._calendar_adapter = None
                self._calendar_initialized = True

        return self._calendar_adapter

    def detect_agent(self, message: str, auto_switch: bool = True) -> Optional[str]:
        """
        Detect the appropriate agent for a message based on trigger patterns.

        Args:
            message: User message to analyze
            auto_switch: If True, switch current_agent when match found

        Returns:
            Agent name if a better match found, None if current agent is appropriate
        """
        message_lower = message.lower()
        scores: dict[str, int] = {}

        # Score each agent based on trigger matches
        for agent_name, patterns in self._trigger_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern.search(message_lower):
                    score += 1
            if score > 0:
                scores[agent_name] = score

        if not scores:
            return None

        # Find highest scoring agent
        best_agent = max(scores, key=scores.get)

        # Only switch if different from current and score is meaningful
        if best_agent != self.current_agent and scores[best_agent] >= 1:
            if auto_switch:
                self.current_agent = best_agent
                return best_agent
            return best_agent

        return None

    def _register_commands(self):
        """Register all available commands with their handlers"""
        self._commands = {
            "agent": (self._cmd_agent, "Switch agent", ["name"]),
            "a": (self._cmd_agent, "Switch agent (alias)", ["name"]),
            "clear": (self._cmd_clear, "Clear history", []),
            "save": (self._cmd_save, "Save session", []),
            "usage": (self._cmd_usage, "Show token stats", []),
            "context": (self._cmd_context, "Show context usage", []),
            "state": (self._cmd_state, "Show current state", []),
            "s": (self._cmd_state, "Show current state (alias)", []),
            "commitments": (self._cmd_commitments, "Show commitments", []),
            "c": (self._cmd_commitments, "Show commitments (alias)", []),
            "help": (self._cmd_help, "Show help", []),
            "h": (self._cmd_help, "Show help (alias)", []),
            "quit": (self._cmd_quit, "Exit", []),
            "q": (self._cmd_quit, "Exit (alias)", []),
            "exit": (self._cmd_quit, "Exit (alias)", []),
            "run": (self._cmd_run, "Run Thanos command", ["cmd"]),
            "agents": (self._cmd_list_agents, "List agents", []),
            "sessions": (self._cmd_sessions, "List saved sessions", []),
            "resume": (self._cmd_resume, "Resume a session", ["session_id"]),
            "r": (self._cmd_resume, "Resume session (alias)", ["session_id"]),
            "recall": (self._cmd_recall, "Search past sessions", ["query"]),
            "remember": (self._cmd_remember, "Store a memory in MemOS", ["content"]),
            "memory": (self._cmd_memory, "Memory system info", []),
            "branch": (self._cmd_branch, "Create conversation branch", ["name"]),
            "branches": (self._cmd_branches, "List branches", []),
            "switch": (self._cmd_switch, "Switch to branch", ["branch"]),
            "patterns": (self._cmd_patterns, "Show conversation patterns", []),
            "model": (self._cmd_model, "Switch AI model", ["name"]),
            "m": (self._cmd_model, "Switch model (alias)", ["name"]),
            "calendar": (self._cmd_calendar, "Show calendar events", ["args"]),
            "cal": (self._cmd_calendar, "Show calendar (alias)", ["args"]),
            "schedule": (self._cmd_schedule, "Schedule a task", ["args"]),
            "free": (self._cmd_free, "Find free time slots", ["args"]),
            "prompt": (self._cmd_prompt, "Switch prompt display mode", ["mode"]),
            "p": (self._cmd_prompt, "Switch prompt mode (alias)", ["mode"]),
        }

    def route_command(self, input_str: str) -> CommandResult:
        """
        Route and execute a command.

        Args:
            input_str: Command string (e.g., "/state", "/agent ops")

        Returns:
            CommandResult with action and message
        """
        parts = input_str.split(maxsplit=1)
        command = parts[0][1:].lower()  # Remove leading '/'
        args = parts[1] if len(parts) > 1 else ""

        handler_info = self._commands.get(command)
        if handler_info:
            handler, _, _ = handler_info
            return handler(args)
        else:
            print(
                f"{Colors.DIM}Unknown command: /{command}. "
                f"Type /help for available commands.{Colors.RESET}"
            )
            return CommandResult(action=CommandAction.CONTINUE, success=False)

    def get_available_commands(self) -> list[tuple[str, str, list[str]]]:
        """Get list of available commands for help text"""
        # Return unique commands (filter out aliases for main list)
        unique_commands = []
        seen_handlers = set()
        for cmd, (handler, desc, args) in self._commands.items():
            if handler not in seen_handlers:
                unique_commands.append((cmd, desc, args))
                seen_handlers.add(handler)
        return sorted(unique_commands)

    # ========================================================================
    # Command Handlers
    # ========================================================================

    def _cmd_agent(self, args: str) -> CommandResult:
        """Switch to a different agent."""
        if not args:
            print(f"Current agent: {self.current_agent}")
            print(f"Available: {', '.join(self.orchestrator.agents.keys())}")
            return CommandResult()

        agent_name = args.lower().strip()
        if agent_name in self.orchestrator.agents:
            self.current_agent = agent_name
            agent = self.orchestrator.agents[agent_name]
            print(f"{Colors.DIM}Switched to {agent.name} ({agent.role}){Colors.RESET}")
            return CommandResult()
        else:
            print(f"{Colors.DIM}Unknown agent: {agent_name}{Colors.RESET}")
            print(f"Available: {', '.join(self.orchestrator.agents.keys())}")
            return CommandResult(success=False)

    def _cmd_clear(self, args: str) -> CommandResult:
        """Clear conversation history."""
        self.session.clear()
        print(f"{Colors.DIM}Conversation cleared.{Colors.RESET}")
        return CommandResult()

    def _cmd_save(self, args: str) -> CommandResult:
        """Save session to History/Sessions/."""
        filepath = self.session.save()
        print(f"{Colors.DIM}Session saved: {filepath}{Colors.RESET}")
        return CommandResult()

    def _cmd_usage(self, args: str) -> CommandResult:
        """Show token usage statistics."""
        stats = self.session.get_stats()
        print(f"""
{Colors.CYAN}Session Usage:{Colors.RESET}
  Duration: {stats["duration_minutes"]} minutes
  Messages: {stats["message_count"]}
  Input tokens: {stats["total_input_tokens"]:,}
  Output tokens: {stats["total_output_tokens"]:,}
  Estimated cost: ${stats["total_cost"]:.4f}
""")
        return CommandResult()

    def _cmd_context(self, args: str) -> CommandResult:
        """Show context window usage."""
        agent = self.orchestrator.agents.get(self.current_agent)
        system_prompt = self.orchestrator._build_system_prompt(agent=agent)
        history = self.session.get_messages_for_api()

        report = self.context_mgr.get_usage_report(history, system_prompt)
        print(f"""
{Colors.CYAN}Context Window:{Colors.RESET}
  System prompt: ~{report["system_tokens"]:,} tokens
  Conversation: ~{report["history_tokens"]:,} tokens ({report["messages_in_context"]} messages)
  Total used: ~{report["total_used"]:,} / {report["available"]:,} tokens
  Usage: {report["usage_percent"]:.1f}%
""")
        return CommandResult()

    def _cmd_state(self, args: str) -> CommandResult:
        """Show current Thanos state (Today.md context)."""
        ctx = self.state_reader.get_quick_context()
        print(f"""
{Colors.CYAN}Current Thanos State:{Colors.RESET}""")

        if ctx["focus"]:
            print(f"  Focus: {ctx['focus']}")

        if ctx["top3"]:
            print("\n  Today's Top 3:")
            for i, item in enumerate(ctx["top3"], 1):
                print(f"    {i}. {item}")

        if ctx["pending_commitments"] > 0:
            print(f"\n  Pending Commitments: {ctx['pending_commitments']}")

        if ctx["blockers"]:
            print(f"  Blockers: {', '.join(ctx['blockers'])}")

        if ctx["energy"]:
            print(f"  Energy: {ctx['energy']}")

        if ctx["week_theme"]:
            print(f"  Week Theme: {ctx['week_theme']}")

        if not any([ctx["focus"], ctx["top3"], ctx["pending_commitments"]]):
            print(f"  {Colors.DIM}No active state loaded{Colors.RESET}")

        print()
        return CommandResult()

    def _cmd_commitments(self, args: str) -> CommandResult:
        """Show active commitments from Commitments.md."""
        commitments_file = self.thanos_dir / "State" / "Commitments.md"
        if not commitments_file.exists():
            print(f"{Colors.DIM}No commitments file found.{Colors.RESET}")
            return CommandResult(success=False)

        try:
            content = commitments_file.read_text()
            print(f"\n{Colors.CYAN}Active Commitments:{Colors.RESET}\n")

            # Parse and display uncompleted commitments
            lines = content.split("\n")
            in_section = False
            shown_count = 0

            for line in lines:
                if line.startswith("## Work Commitments") or line.startswith(
                    "## Personal Commitments"
                ):
                    in_section = True
                    print(f"{Colors.BOLD}{line[3:]}{Colors.RESET}")
                    continue

                if in_section and line.startswith("##"):
                    in_section = False

                if in_section and "- [ ]" in line:
                    print(f"  {line.strip()}")
                    shown_count += 1

            if shown_count == 0:
                print(f"  {Colors.DIM}No pending commitments{Colors.RESET}")
            print()
            return CommandResult()

        except Exception as e:
            print(f"{Colors.DIM}Error reading commitments: {e}{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_help(self, args: str) -> CommandResult:
        """Show help information."""
        print(f"""
{Colors.CYAN}Commands:{Colors.RESET}
  /agent <name>  - Switch agent (strategy, coach, health, ops)
  /agents        - List all available agents
  /clear         - Clear conversation history
  /context       - Show context window usage
  /state         - Show current Thanos state (focus, top 3, energy)
  /commitments   - Show active commitments
  /usage         - Show token/cost statistics
  /save          - Save session to History/Sessions/
  /sessions      - List saved sessions
  /resume <id>   - Resume a saved session (/resume last for most recent)
  /recall <q>    - Search memories (MemOS hybrid) or past sessions
  /remember <c>  - Store a memory in MemOS knowledge graph
  /memory        - Show memory system info (Neo4j, ChromaDB, sessions)
  /branch [name] - Create conversation branch from current point
  /branches      - List all branches of this session
  /switch <ref>  - Switch to a different branch (by name or id)
  /patterns      - Show conversation patterns and usage analytics
  /model [name]  - Switch AI model (opus, sonnet, haiku)
  /prompt [mode] - Switch prompt display (compact, standard, verbose)
  /calendar [when] - Show calendar events (today, tomorrow, week, YYYY-MM-DD)
  /schedule <task> - Schedule a task on calendar
  /free [when]   - Find free time slots (today, tomorrow, week)
  /run <cmd>     - Run a Thanos command (e.g., /run pa:daily)
  /help          - Show this help
  /quit          - Exit interactive mode

{Colors.CYAN}Shortcuts:{Colors.RESET}
  /a = /agent, /s = /state, /c = /commitments
  /r = /resume, /m = /model, /h = /help, /q = /quit
  /p = /prompt, /cal = /calendar

{Colors.DIM}Tip: Use \""" for multi-line input{Colors.RESET}
""")
        return CommandResult()

    def _cmd_quit(self, args: str) -> CommandResult:
        """Exit interactive mode."""
        return CommandResult(action=CommandAction.QUIT)

    def _cmd_run(self, args: str) -> CommandResult:
        """Run a Thanos command."""
        if not args:
            print(f"{Colors.DIM}Usage: /run <command> (e.g., /run pa:daily){Colors.RESET}")
            return CommandResult(success=False)

        print(f"{Colors.DIM}Running {args}...{Colors.RESET}\n")
        try:
            self.orchestrator.run_command(args, stream=True)
            return CommandResult()
        except Exception as e:
            print(f"{Colors.DIM}Error running command: {e}{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_list_agents(self, args: str) -> CommandResult:
        """List all available agents."""
        print(f"\n{Colors.CYAN}Available Agents:{Colors.RESET}")
        for name, agent in self.orchestrator.agents.items():
            marker = "→" if name == self.current_agent else " "
            print(f"  {marker} {name}: {agent.role}")
            print(f"      Voice: {agent.voice}")
        print()
        return CommandResult()

    def _cmd_sessions(self, args: str) -> CommandResult:
        """List recent saved sessions."""
        sessions = self.session.list_sessions(limit=10)
        if not sessions:
            print(f"{Colors.DIM}No saved sessions found.{Colors.RESET}")
            return CommandResult()

        print(f"\n{Colors.CYAN}Recent Sessions:{Colors.RESET}")
        for s in sessions:
            print(
                f"  {s['id']}  {s['date']}  {s['agent']:8}  "
                f"{s['messages']:3} msgs  {s['tokens']:,} tokens"
            )
        print(f"\n{Colors.DIM}Use /resume <id> or /resume last to restore{Colors.RESET}\n")
        return CommandResult()

    def _cmd_resume(self, args: str) -> CommandResult:
        """Resume a saved session."""
        if not args:
            # Show sessions and prompt
            sessions = self.session.list_sessions(limit=5)
            if not sessions:
                print(f"{Colors.DIM}No saved sessions to resume.{Colors.RESET}")
                return CommandResult(success=False)

            print(f"\n{Colors.CYAN}Recent Sessions:{Colors.RESET}")
            for s in sessions:
                print(f"  {s['id']}  {s['date']}  {s['agent']:8}  {s['messages']:3} msgs")
            print(f"\n{Colors.DIM}Usage: /resume <session_id> or /resume last{Colors.RESET}\n")
            return CommandResult()

        session_id = args.strip()
        if self.session.load_session(session_id):
            # Update current agent to match restored session
            self.current_agent = self.session.session.agent
            stats = self.session.get_stats()
            print(f"{Colors.CYAN}Session restored:{Colors.RESET}")
            print(f"  ID: {stats['session_id']}")
            print(f"  Agent: {stats['current_agent']}")
            print(f"  Messages: {stats['message_count']}")
            print(
                f"  Previous tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}"
            )
            print(
                f"\n{Colors.DIM}Conversation history loaded. "
                f"Continue where you left off.{Colors.RESET}\n"
            )
            return CommandResult()
        else:
            print(f"{Colors.DIM}Session not found: {session_id}{Colors.RESET}")
            print(f"{Colors.DIM}Use /sessions to list available sessions.{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_remember(self, args: str) -> CommandResult:
        """Store a memory in MemOS knowledge graph."""
        if not args:
            print(f"{Colors.DIM}Usage: /remember <content to store>{Colors.RESET}")
            print(
                f"{Colors.DIM}Options: /remember decision: <text>  - "
                f"Store as decision{Colors.RESET}"
            )
            print(
                f"{Colors.DIM}         /remember pattern: <text>  - Store as pattern{Colors.RESET}"
            )
            print(
                f"{Colors.DIM}         /remember <text>           - "
                f"Store as observation{Colors.RESET}"
            )
            return CommandResult()

        memos = self._get_memos()
        if not memos:
            print(
                f"{Colors.DIM}MemOS not available. "
                f"Check Neo4j/ChromaDB configuration.{Colors.RESET}"
            )
            return CommandResult(success=False)

        # Parse memory type from prefix
        memory_type = "observation"
        content = args.strip()
        domain = "general"

        # Check for type prefixes
        type_prefixes = {
            "decision:": "decision",
            "pattern:": "pattern",
            "commitment:": "commitment",
            "entity:": "entity",
        }

        for prefix, mtype in type_prefixes.items():
            if content.lower().startswith(prefix):
                memory_type = mtype
                content = content[len(prefix) :].strip()
                break

        # Detect domain from current agent
        agent_domain_map = {
            "ops": "work",
            "strategy": "work",
            "coach": "personal",
            "health": "health",
        }
        domain = agent_domain_map.get(self.current_agent, "general")

        # Extract entities (simple: words starting with @)
        entities = []
        words = content.split()
        for word in words:
            if word.startswith("@") and len(word) > 1:
                entities.append(word[1:])

        # Store the memory
        result = self._run_async(
            memos.remember(
                content=content,
                memory_type=memory_type,
                domain=domain,
                entities=entities if entities else None,
                metadata={
                    "agent": self.current_agent,
                    "session_id": self.session.session.id
                    if hasattr(self.session, "session")
                    else None,
                },
            )
        )

        if result and result.success:
            print(f"\n{Colors.CYAN}Memory stored:{Colors.RESET}")
            print(f"  Type: {memory_type}")
            print(f"  Domain: {domain}")
            if entities:
                print(f"  Entities: {', '.join(entities)}")
            if result.graph_results:
                node_id = result.graph_results.get("node_id", "")
                print(f"  Graph ID: {node_id[:8]}..." if node_id else "")
            if result.vector_results:
                print("  Vector stored: ✓")
            print()
            return CommandResult()
        else:
            error = result.error if result else "Unknown error"
            print(f"{Colors.DIM}Failed to store memory: {error}{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_recall(self, args: str) -> CommandResult:
        """Search memories using MemOS hybrid search or past sessions."""
        import json

        if not args:
            print(f"{Colors.DIM}Usage: /recall <search query>{Colors.RESET}")
            print(f"{Colors.DIM}Example: /recall Memphis client{Colors.RESET}")
            print(f"{Colors.DIM}Flags: --sessions (search only sessions){Colors.RESET}")
            return CommandResult()

        # Check for --sessions flag to skip MemOS
        sessions_only = "--sessions" in args
        query = args.replace("--sessions", "").strip()

        # Try MemOS first (hybrid search)
        memos = self._get_memos() if not sessions_only else None
        memos_results = []

        if memos:
            result = self._run_async(
                memos.recall(query=query, limit=5, use_graph=True, use_vector=True)
            )

            if result and result.success:
                # Combine vector and graph results
                if result.vector_results:
                    for item in result.vector_results[:3]:
                        memos_results.append(
                            {
                                "source": "vector",
                                "content": item.get("content", "")[:150],
                                "type": item.get("memory_type", "memory"),
                                "score": item.get("similarity", 0),
                            }
                        )

                if result.graph_results:
                    nodes = result.graph_results.get("nodes", [])
                    for node in nodes[:3]:
                        props = node.get("properties", {})
                        memos_results.append(
                            {
                                "source": "graph",
                                "content": props.get("content", props.get("description", ""))[:150],
                                "type": node.get("labels", ["memory"])[0]
                                if node.get("labels")
                                else "memory",
                                "id": node.get("id", "")[:8],
                            }
                        )

        # Display MemOS results
        if memos_results:
            print(
                f"\n{Colors.CYAN}MemOS Knowledge Graph "
                f"({len(memos_results)} results):{Colors.RESET}\n"
            )
            for r in memos_results:
                source_icon = "🔍" if r["source"] == "vector" else "🔗"
                score_str = f" ({r.get('score', 0):.2f})" if r.get("score") else ""
                print(f"  {source_icon} [{r['type']}]{score_str}")
                print(f"     {r['content']}...")
                print()

        # Also search session history (fallback or additional)
        history_dir = self.thanos_dir / "History" / "Sessions"
        session_matches = []

        if history_dir.exists():
            json_files = sorted(
                history_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
            )[:30]  # Limit to last 30 sessions

            for json_file in json_files:
                try:
                    data = json.loads(json_file.read_text())
                    for msg in data.get("history", []):
                        content = msg.get("content", "").lower()
                        if query.lower() in content:
                            session_matches.append(
                                {
                                    "session": data.get("id", json_file.stem),
                                    "date": data.get("started_at", "")[:16].replace("T", " "),
                                    "role": msg.get("role", "unknown"),
                                    "preview": msg.get("content", "")[:100],
                                }
                            )
                            if len(session_matches) >= 5:
                                break
                except (json.JSONDecodeError, KeyError):
                    continue
                if len(session_matches) >= 5:
                    break

        # Display session results
        if session_matches:
            print(
                f"\n{Colors.CYAN}Session History ({len(session_matches)} matches):{Colors.RESET}\n"
            )
            for m in session_matches:
                role_color = Colors.PURPLE if m["role"] == "user" else Colors.CYAN
                print(f"  {Colors.DIM}{m['date']}{Colors.RESET} ({m['session']})")
                print(f"  {role_color}{m['role']}:{Colors.RESET} {m['preview']}...")
                print()

        if not memos_results and not session_matches:
            print(f"{Colors.DIM}No matches found for: {query}{Colors.RESET}")
            return CommandResult()

        if session_matches:
            print(f"{Colors.DIM}Use /resume <session_id> to restore a session{Colors.RESET}\n")

        return CommandResult()

    def _cmd_memory(self, args: str) -> CommandResult:
        """Display memory system information including MemOS (Neo4j + ChromaDB)."""
        print(f"\n{Colors.CYAN}Memory Systems:{Colors.RESET}\n")

        # MemOS Status (primary system)
        print(f"  {Colors.BOLD}MemOS Hybrid Memory:{Colors.RESET}")
        memos = self._get_memos()
        if memos:
            print("    ✓ MemOS initialized")

            # Neo4j status
            neo4j_url = os.environ.get("NEO4J_URL", "")
            if neo4j_url:
                # Mask URL for security
                masked_url = neo4j_url.split("@")[-1] if "@" in neo4j_url else neo4j_url[:30]
                print(f"    🔗 Neo4j Graph: {masked_url}")
            else:
                print("    🔗 Neo4j Graph: Not configured")

            # ChromaDB status
            chroma_path = os.environ.get("CHROMADB_PATH", "~/.chromadb")
            print(f"    🔍 ChromaDB Vectors: {chroma_path}")

            # Try to get stats
            if hasattr(memos, "_neo4j") and memos._neo4j:
                try:
                    result = self._run_async(memos._neo4j.health_check())
                    if result and result.success:
                        print("    ✓ Neo4j connected")
                except Exception:
                    print("    ⚠ Neo4j connection issue")
        else:
            if MEMOS_AVAILABLE:
                print("    ⚠ MemOS available but not initialized")
                print("    💡 MemOS will initialize on first /remember or /recall")
            else:
                print("    ✗ MemOS not available")
                print("    💡 Install neo4j and chromadb packages")

        print()

        # Check for session history
        history_dir = self.thanos_dir / "History" / "Sessions"
        if history_dir.exists():
            session_count = len(list(history_dir.glob("*.json")))
            print(f"  📝 Session History: {session_count} saved sessions")
            print(f"     Location: {history_dir}")
        else:
            print("  📝 Session History: Not initialized")

        # Check for swarm memory
        swarm_db = self.thanos_dir / ".swarm" / "memory.db"
        if swarm_db.exists():
            size_kb = swarm_db.stat().st_size / 1024
            print(f"  🔮 Swarm Memory: {size_kb:.1f} KB")
            print(f"     Location: {swarm_db}")
        else:
            print("  🔮 Swarm Memory: Not initialized")

        # Check for hive-mind memory
        hive_db = self.thanos_dir / ".hive-mind" / "memory.db"
        if hive_db.exists():
            size_kb = hive_db.stat().st_size / 1024
            print(f"  🐝 Hive Mind Memory: {size_kb:.1f} KB")
            print(f"     Location: {hive_db}")
        else:
            print("  🐝 Hive Mind Memory: Not initialized")

        # Check for claude-mem integration
        claude_mem = Path.home() / ".claude-mem"
        if claude_mem.exists():
            print("  🧠 Claude-mem: Active")
            print(f"     Location: {claude_mem}")
        else:
            print("  🧠 Claude-mem: Not detected")

        print(f"\n{Colors.DIM}Commands:{Colors.RESET}")
        print(f"{Colors.DIM}  /remember <content> - Store memory in knowledge graph{Colors.RESET}")
        print(
            f"{Colors.DIM}  /recall <query>     - Search memories (hybrid search){Colors.RESET}\n"
        )
        return CommandResult()

    def _cmd_branch(self, args: str) -> CommandResult:
        """Create a conversation branch from current point."""
        branch_name = args.strip() if args else None
        new_id = self.session.create_branch(branch_name)
        branch_info = self.session.get_branch_info()

        print(f"\n{Colors.CYAN}Branch created:{Colors.RESET}")
        print(f"  Name: {branch_info['name']}")
        print(f"  ID: {new_id}")
        print(f"  Branched from: {branch_info['parent_id']}")
        print(f"  At message: {branch_info['branch_point']}")
        print(
            f"\n{Colors.DIM}Continue conversation on this branch. "
            f"Use /branches to list all.{Colors.RESET}\n"
        )
        return CommandResult()

    def _cmd_branches(self, args: str) -> CommandResult:
        """List all branches of current session tree."""
        branches = self.session.list_branches()

        if not branches:
            print(f"{Colors.DIM}No branches found for this session.{Colors.RESET}")
            return CommandResult()

        print(f"\n{Colors.CYAN}Session Branches:{Colors.RESET}\n")
        for b in branches:
            marker = "→" if b.get("is_current") else " "
            parent_info = (
                f" (from {b['parent_id'][:4]}... at msg {b['branch_point']})"
                if b.get("parent_id")
                else ""
            )
            print(f"  {marker} {b['name']}: {b['id']}{parent_info}")
            print(f"      {b['date']}  {b['messages']} messages")

        print(f"\n{Colors.DIM}Use /switch <name or id> to change branches{Colors.RESET}\n")
        return CommandResult()

    def _cmd_switch(self, args: str) -> CommandResult:
        """Switch to a different branch."""
        if not args:
            # Show branches
            return self._cmd_branches("")

        branch_ref = args.strip()
        if self.session.switch_branch(branch_ref):
            # Update current agent to match branch
            self.current_agent = self.session.session.agent
            branch_info = self.session.get_branch_info()
            stats = self.session.get_stats()

            print(f"\n{Colors.CYAN}Switched to branch:{Colors.RESET}")
            print(f"  Name: {branch_info['name']}")
            print(f"  ID: {branch_info['id']}")
            print(f"  Messages: {stats['message_count']}")
            print(f"\n{Colors.DIM}Conversation restored from branch point.{Colors.RESET}\n")
            return CommandResult()
        else:
            print(f"{Colors.DIM}Branch not found: {branch_ref}{Colors.RESET}")
            print(f"{Colors.DIM}Use /branches to list available branches.{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_patterns(self, args: str) -> CommandResult:
        """Analyze conversation patterns from session history."""
        from collections import Counter
        from datetime import datetime
        import json

        history_dir = self.thanos_dir / "History" / "Sessions"
        if not history_dir.exists():
            print(f"{Colors.DIM}No session history to analyze.{Colors.RESET}")
            return CommandResult()

        # Collect session data
        sessions_data = []
        json_files = list(history_dir.glob("*.json"))

        if not json_files:
            print(f"{Colors.DIM}No saved sessions found.{Colors.RESET}")
            return CommandResult()

        for json_file in json_files:
            try:
                data = json.loads(json_file.read_text())
                sessions_data.append(data)
            except (json.JSONDecodeError, KeyError):
                continue

        if not sessions_data:
            print(f"{Colors.DIM}No valid session data to analyze.{Colors.RESET}")
            return CommandResult()

        # Analyze patterns
        agent_usage = Counter()
        hour_usage = Counter()
        session_lengths = []
        total_messages = 0

        for session in sessions_data:
            # Agent usage
            agent = session.get("agent", "unknown")
            agent_usage[agent] += 1

            # Time of day
            started = session.get("started_at", "")
            if started:
                try:
                    dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                    hour_usage[dt.hour] += 1
                except ValueError:
                    pass

            # Session length (messages)
            msg_count = len(session.get("history", []))
            if msg_count > 0:
                session_lengths.append(msg_count)
                total_messages += msg_count

        # Calculate statistics
        total_sessions = len(sessions_data)
        avg_messages = total_messages / total_sessions if total_sessions > 0 else 0

        # Find peak hours
        peak_hours = hour_usage.most_common(3)
        peak_hour_strs = []
        for hour, _ in peak_hours:
            if hour < 12:
                peak_hour_strs.append(f"{hour}am" if hour > 0 else "12am")
            else:
                h = hour - 12 if hour > 12 else 12
                peak_hour_strs.append(f"{h}pm")

        # Display patterns
        print(f"\n{Colors.CYAN}Conversation Patterns:{Colors.RESET}\n")
        print(f"  {Colors.BOLD}Session Overview:{Colors.RESET}")
        print(f"    Total sessions: {total_sessions}")
        print(f"    Total messages: {total_messages}")
        print(f"    Avg messages/session: {avg_messages:.1f}")

        print(f"\n  {Colors.BOLD}Agent Usage:{Colors.RESET}")
        for agent, count in agent_usage.most_common():
            pct = (count / total_sessions) * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            print(f"    {agent:12} {bar} {pct:.0f}%")

        if peak_hour_strs:
            print(f"\n  {Colors.BOLD}Peak Activity Hours:{Colors.RESET}")
            print(f"    Most active: {', '.join(peak_hour_strs)}")

        # Productivity insight based on session sizes
        if session_lengths:
            long_sessions = sum(1 for s in session_lengths if s > 10)
            short_sessions = sum(1 for s in session_lengths if s <= 5)
            print(f"\n  {Colors.BOLD}Session Types:{Colors.RESET}")
            print(f"    Deep sessions (>10 msgs): {long_sessions}")
            print(f"    Quick sessions (≤5 msgs): {short_sessions}")

        print(f"\n{Colors.DIM}Based on {total_sessions} saved sessions{Colors.RESET}\n")
        return CommandResult()

    def _cmd_model(self, args: str) -> CommandResult:
        """Switch AI model for responses."""
        if not args:
            # Show current model and available options
            current = self.current_model or self._default_model
            print(f"\n{Colors.CYAN}AI Model:{Colors.RESET}")
            print(f"  Current: {current} ({self._available_models.get(current, 'unknown')})")
            print(f"\n{Colors.CYAN}Available Models:{Colors.RESET}")
            for alias, full_name in self._available_models.items():
                marker = "→" if alias == current else " "
                # Add cost hints
                if alias == "opus":
                    cost = "$15/$75 per 1M tokens (most capable)"
                elif alias == "sonnet":
                    cost = "$3/$15 per 1M tokens (balanced)"
                else:
                    cost = "$0.25/$1.25 per 1M tokens (fastest)"
                print(f"  {marker} {alias:8} {full_name}")
                print(f"           {Colors.DIM}{cost}{Colors.RESET}")
            print(f"\n{Colors.DIM}Usage: /model <opus|sonnet|haiku>{Colors.RESET}\n")
            return CommandResult()

        model_name = args.lower().strip()
        if model_name in self._available_models:
            old_model = self.current_model or self._default_model
            self.current_model = model_name
            print(f"{Colors.CYAN}Model switched:{Colors.RESET} {old_model} → {model_name}")
            print(f"{Colors.DIM}Using: {self._available_models[model_name]}{Colors.RESET}")
            return CommandResult()
        else:
            print(f"{Colors.DIM}Unknown model: {model_name}{Colors.RESET}")
            print(f"Available: {', '.join(self._available_models.keys())}")
            return CommandResult(success=False)

    def get_current_model(self) -> str:
        """Get the current model full name for API calls."""
        model_alias = self.current_model or self._default_model
        return self._available_models.get(model_alias, self._available_models[self._default_model])

    def _cmd_prompt(self, args: str) -> CommandResult:
        """Switch prompt display mode."""
        available_modes = ["compact", "standard", "verbose"]

        if not args:
            # Show current mode and available options
            current = self.current_prompt_mode or "compact"
            print(f"\n{Colors.CYAN}Prompt Display Mode:{Colors.RESET}")
            print(f"  Current: {current}")
            print(f"\n{Colors.CYAN}Available Modes:{Colors.RESET}")
            for mode in available_modes:
                marker = "→" if mode == current else " "
                if mode == "compact":
                    desc = "Tokens and cost only - (1.2K | $0.04)"
                elif mode == "standard":
                    desc = "Adds session duration - (45m | 1.2K tokens | $0.04)"
                else:  # verbose
                    desc = "Full details - (45m | 12 msgs | 1.2K in | 3.4K out | $0.04)"
                print(f"  {marker} {mode:10} {desc}")
            print(f"\n{Colors.DIM}Usage: /prompt <compact|standard|verbose>{Colors.RESET}\n")
            return CommandResult()

        mode = args.lower().strip()
        if mode in available_modes:
            old_mode = self.current_prompt_mode or "compact"
            self.current_prompt_mode = mode
            print(f"{Colors.CYAN}Prompt mode switched:{Colors.RESET} {old_mode} → {mode}")
            return CommandResult()
        else:
            print(f"{Colors.DIM}Unknown mode: {mode}{Colors.RESET}")
            print(f"Available: {', '.join(available_modes)}")
            return CommandResult(success=False)

    def _cmd_calendar(self, args: str) -> CommandResult:
        """Show calendar events for today or a specified date."""
        calendar = self._get_calendar_adapter()
        if not calendar:
            print(f"{Colors.DIM}Calendar integration not available. Install google-auth, google-auth-oauthlib, and google-api-python-client.{Colors.RESET}")
            return CommandResult(success=False)

        if not calendar.is_authenticated():
            print(f"{Colors.DIM}Calendar not authenticated. Use /run tools to authorize Google Calendar.{Colors.RESET}")
            return CommandResult(success=False)

        try:
            # Parse args: default to today, support "tomorrow", "week", or specific date
            import json
            from datetime import datetime, timedelta

            if not args or args.lower() in ["today", ""]:
                # Show today's events
                result = self._run_async(calendar.call_tool("get_today_events", {}))
            elif args.lower() == "tomorrow":
                # Show tomorrow's events
                tomorrow = datetime.now() + timedelta(days=1)
                start = tomorrow.strftime("%Y-%m-%d")
                end = (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d")
                result = self._run_async(calendar.call_tool("get_events", {
                    "start_date": start,
                    "end_date": end
                }))
            elif args.lower() in ["week", "this week"]:
                # Show this week's events
                start = datetime.now().strftime("%Y-%m-%d")
                end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                result = self._run_async(calendar.call_tool("get_events", {
                    "start_date": start,
                    "end_date": end
                }))
            else:
                # Try to parse as date
                try:
                    date_obj = datetime.strptime(args, "%Y-%m-%d")
                    start = date_obj.strftime("%Y-%m-%d")
                    end = (date_obj + timedelta(days=1)).strftime("%Y-%m-%d")
                    result = self._run_async(calendar.call_tool("get_events", {
                        "start_date": start,
                        "end_date": end
                    }))
                except ValueError:
                    print(f"{Colors.DIM}Invalid date format. Use YYYY-MM-DD or 'today', 'tomorrow', 'week'{Colors.RESET}")
                    return CommandResult(success=False)

            if result and result.success:
                data = result.data
                events = data.get("events", [])

                print(f"\n{Colors.CYAN}Calendar Events:{Colors.RESET}")
                if not events:
                    print(f"{Colors.DIM}  No events found{Colors.RESET}")
                else:
                    for event in events:
                        summary = event.get("summary", "Untitled")
                        start = event.get("start", {})
                        if "dateTime" in start:
                            time_str = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00")).strftime("%I:%M %p")
                        elif "date" in start:
                            time_str = "All day"
                        else:
                            time_str = "Unknown time"

                        print(f"  • {time_str:12} {summary}")

                        # Show location if available
                        if event.get("location"):
                            print(f"    {Colors.DIM}📍 {event['location']}{Colors.RESET}")

                print()
                return CommandResult()
            else:
                error_msg = result.error if result else "Unknown error"
                print(f"{Colors.DIM}Failed to fetch calendar: {error_msg}{Colors.RESET}")
                return CommandResult(success=False)

        except Exception as e:
            print(f"{Colors.DIM}Error fetching calendar: {e}{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_schedule(self, args: str) -> CommandResult:
        """Schedule a task on the calendar."""
        calendar = self._get_calendar_adapter()
        if not calendar:
            print(f"{Colors.DIM}Calendar integration not available.{Colors.RESET}")
            return CommandResult(success=False)

        if not calendar.is_authenticated():
            print(f"{Colors.DIM}Calendar not authenticated. Use /run tools to authorize.{Colors.RESET}")
            return CommandResult(success=False)

        if not args:
            print(f"{Colors.DIM}Usage: /schedule <task description>{Colors.RESET}")
            print(f"{Colors.DIM}Example: /schedule Review PR{Colors.RESET}")
            return CommandResult(success=False)

        try:
            # For now, delegate to the orchestrator to handle intelligent scheduling
            # The orchestrator can use find_free_slots and block_time_for_task
            print(f"{Colors.CYAN}Scheduling task:{Colors.RESET} {args}")
            print(f"{Colors.DIM}Let me find a good time slot for this...{Colors.RESET}")

            # This is a placeholder - the actual scheduling logic should be in the agent
            # For now, just inform the user to use natural language with the agent
            print(f"\n{Colors.DIM}Tip: For intelligent scheduling, ask the agent in natural language:{Colors.RESET}")
            print(f'{Colors.DIM}Example: "Schedule this task for tomorrow morning"{Colors.RESET}\n')

            return CommandResult()

        except Exception as e:
            print(f"{Colors.DIM}Error scheduling task: {e}{Colors.RESET}")
            return CommandResult(success=False)

    def _cmd_free(self, args: str) -> CommandResult:
        """Find free time slots in calendar."""
        calendar = self._get_calendar_adapter()
        if not calendar:
            print(f"{Colors.DIM}Calendar integration not available.{Colors.RESET}")
            return CommandResult(success=False)

        if not calendar.is_authenticated():
            print(f"{Colors.DIM}Calendar not authenticated. Use /run tools to authorize.{Colors.RESET}")
            return CommandResult(success=False)

        try:
            from datetime import datetime, timedelta
            import json

            # Parse args: default to today, support "tomorrow", "week"
            if not args or args.lower() in ["today", ""]:
                start = datetime.now().strftime("%Y-%m-%d")
                end = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                period = "today"
            elif args.lower() == "tomorrow":
                tomorrow = datetime.now() + timedelta(days=1)
                start = tomorrow.strftime("%Y-%m-%d")
                end = (tomorrow + timedelta(days=1)).strftime("%Y-%m-%d")
                period = "tomorrow"
            elif args.lower() in ["week", "this week"]:
                start = datetime.now().strftime("%Y-%m-%d")
                end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                period = "this week"
            else:
                print(f"{Colors.DIM}Usage: /free [today|tomorrow|week]{Colors.RESET}")
                return CommandResult(success=False)

            result = self._run_async(calendar.call_tool("find_free_slots", {
                "start_date": start,
                "end_date": end,
                "min_duration_minutes": 30,
                "working_hours_start": 9,
                "working_hours_end": 18,
            }))

            if result and result.success:
                data = result.data
                free_slots = data.get("free_slots", [])

                print(f"\n{Colors.CYAN}Free Time Slots ({period}):{Colors.RESET}")
                if not free_slots:
                    print(f"{Colors.DIM}  No free slots found{Colors.RESET}")
                else:
                    for slot in free_slots[:10]:  # Show first 10 slots
                        start_time = datetime.fromisoformat(slot["start"].replace("Z", "+00:00"))
                        end_time = datetime.fromisoformat(slot["end"].replace("Z", "+00:00"))
                        duration = slot.get("duration_minutes", 0)

                        date_str = start_time.strftime("%a %m/%d")
                        time_range = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"

                        print(f"  • {date_str:10} {time_range:25} ({duration} min)")

                if len(free_slots) > 10:
                    print(f"{Colors.DIM}  ... and {len(free_slots) - 10} more slots{Colors.RESET}")

                print()
                return CommandResult()
            else:
                error_msg = result.error if result else "Unknown error"
                print(f"{Colors.DIM}Failed to find free slots: {error_msg}{Colors.RESET}")
                return CommandResult(success=False)

        except Exception as e:
            print(f"{Colors.DIM}Error finding free slots: {e}{Colors.RESET}")
            return CommandResult(success=False)
