#!/usr/bin/env python3
"""
MemoryHandler - Handles memory commands in Thanos Interactive Mode.

This module manages memory storage and retrieval using the memory_router,
which automatically handles backend selection and fallbacks.

Commands:
    /remember <content>     - Store a memory
    /recall <query>         - Search memories using semantic search
    /memory                 - Display memory system information and status

Classes:
    MemoryHandler: Handler for all memory integration commands

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output
    - memory_router: Unified memory routing layer (Memory V2 primary, fallbacks available)

Architecture:
    All memory operations are routed through Tools.memory_router:
    - add_memory(): Store content (automatically uses Memory V2 with fallbacks)
    - search_memory(): Semantic search with heat-based ranking
    - whats_hot(): ADHD helper - what's top of mind
    - whats_cold(): ADHD helper - what's neglected
    - get_stats(): System statistics

    Memory metadata:
    - source: Where the memory came from (manual, brain_dump, etc.)
    - client: Associated client name
    - project: Associated project name
    - type: Memory classification (decision, pattern, observation, etc.)

Example:
    handler = MemoryHandler(orchestrator, session_mgr, context_mgr,
                           state_reader, thanos_dir)

    # Store a memory
    result = handler.handle_remember("Decided to use FastAPI for API server")

    # Recall memories
    result = handler.handle_recall("API framework decisions")

    # Check memory system status
    result = handler.handle_memory("")

See Also:
    - Tools.memory_router: Unified memory routing layer
    - Tools.memory_v2: Cloud-first memory with heat decay (primary backend)
    - Tools.command_handlers.base: Base handler infrastructure
"""

import json
import os
from pathlib import Path

from Tools.command_handlers.base import (
    BaseHandler,
    CommandResult,
    Colors,
)

# Import memory router for all memory operations
try:
    from Tools import memory_router
    MEMORY_ROUTER_AVAILABLE = True
except ImportError:
    MEMORY_ROUTER_AVAILABLE = False


class MemoryHandler(BaseHandler):
    """
    Handler for memory integration commands.

    Provides functionality for:
    - Storing memories via memory_router (automatic backend selection)
    - Searching memories with heat-based ranking
    - ADHD helpers: what's hot, what's cold
    - Displaying memory system status and configuration

    All operations use memory_router which handles:
    - Backend selection (Memory V2 primary, automatic fallbacks)
    - Error handling and graceful degradation
    - Heat-based ranking for ADHD-friendly surfacing
    """

    def __init__(
        self,
        orchestrator,
        session_manager,
        context_manager,
        state_reader,
        thanos_dir,
        current_agent_getter=None,
    ):
        """
        Initialize MemoryHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for agent info
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context operations
            state_reader: StateReader for state operations
            thanos_dir: Path to Thanos root directory
            current_agent_getter: Optional callable to get current agent name
        """
        super().__init__(
            orchestrator,
            session_manager,
            context_manager,
            state_reader,
            thanos_dir,
            current_agent_getter,
        )

    def handle_remember(self, args: str) -> CommandResult:
        """
        Handle /remember command - Store a memory.

        Uses memory_router which automatically handles backend selection
        and fallbacks (Memory V2 primary, MemOS fallback).

        Supports type prefixes for categorization:
        - decision: Important decisions and their rationale
        - pattern: Recurring patterns or best practices
        - commitment: Promises or commitments made
        - entity: Information about people, projects, or things
        - observation: General observations (default)

        Entity extraction: Words starting with @ are extracted as entities.
        Client detection: Words starting with # are treated as client names.

        Args:
            args: Content to store, optionally prefixed with type (e.g., "decision: ...")

        Returns:
            CommandResult with action and success status
        """
        if not MEMORY_ROUTER_AVAILABLE:
            print(f"{Colors.RED}Memory router not available. Check installation.{Colors.RESET}")
            return CommandResult(success=False)

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
            print(
                f"{Colors.DIM}Tags: Use @entity for entities, #client for clients{Colors.RESET}"
            )
            return CommandResult()

        # Parse memory type from prefix
        memory_type = "observation"
        content = args.strip()

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

        # Extract entities (@word) and clients (#word)
        entities = []
        client = None
        words = content.split()
        for word in words:
            if word.startswith("@") and len(word) > 1:
                entities.append(word[1:])
            elif word.startswith("#") and len(word) > 1:
                client = word[1:]

        # Get current agent for metadata
        current_agent = self._get_current_agent()

        # Build metadata
        metadata = {
            "source": "manual",
            "type": memory_type,
            "agent": current_agent,
        }
        if client:
            metadata["client"] = client
        if entities:
            metadata["entities"] = entities
            # Also store as tags for heat boosting and filtering
            metadata["tags"] = entities

        # Store via memory router (handles backend selection automatically)
        try:
            result = memory_router.add_memory(content, metadata=metadata)

            if result:
                print(f"\n{Colors.GREEN}Memory stored:{Colors.RESET}")
                print(f"  Type: {memory_type}")
                if client:
                    print(f"  Client: {client}")
                if entities:
                    print(f"  Entities: {', '.join(entities)}")
                print("  Heat: 1.0 (fresh)")
                print()
                return CommandResult()
            else:
                print(f"{Colors.RED}Failed to store memory{Colors.RESET}")
                return CommandResult(success=False)
        except Exception as e:
            print(f"{Colors.RED}Error storing memory: {e}{Colors.RESET}")
            return CommandResult(success=False)

    def handle_recall(self, args: str) -> CommandResult:
        """
        Handle /recall command - Search memories using semantic search.

        Uses memory_router which handles backend selection and fallbacks.
        Also searches session history for past conversations.

        Flags:
            --sessions: Search only session history, skip memory systems
            --hot: Show what's hot (top of mind, high heat)
            --cold: Show what's cold (neglected, low heat)

        Args:
            args: Search query with optional flags

        Returns:
            CommandResult with action and success status
        """
        if not MEMORY_ROUTER_AVAILABLE:
            print(f"{Colors.RED}Memory router not available. Check installation.{Colors.RESET}")
            return CommandResult(success=False)

        if not args:
            print(f"{Colors.DIM}Usage: /recall <search query>{Colors.RESET}")
            print(f"{Colors.DIM}Example: /recall Memphis client{Colors.RESET}")
            print(f"{Colors.DIM}Flags:{Colors.RESET}")
            print(f"{Colors.DIM}  --sessions  Search only sessions{Colors.RESET}")
            print(f"{Colors.DIM}  --hot       Show top of mind memories{Colors.RESET}")
            print(f"{Colors.DIM}  --cold      Show neglected memories{Colors.RESET}")
            return CommandResult()

        # Check for flags
        sessions_only = "--sessions" in args
        show_hot = "--hot" in args
        show_cold = "--cold" in args
        query = args.replace("--sessions", "").replace("--hot", "").replace("--cold", "").strip()

        # Handle special ADHD helper commands
        if show_hot:
            try:
                hot_memories = memory_router.whats_hot(10)
                print(f"\n{Colors.CYAN}What's Hot (Top of Mind):{Colors.RESET}\n")
                if hot_memories:
                    for mem in hot_memories:
                        heat = mem.get("heat", 1.0)
                        content = mem.get("memory", mem.get("content", ""))[:100]
                        print(f"  🔥 ({heat:.2f}) {content}...")
                else:
                    print(f"  {Colors.DIM}No hot memories found{Colors.RESET}")
                print()
                return CommandResult()
            except Exception as e:
                print(f"{Colors.RED}Error fetching hot memories: {e}{Colors.RESET}")
                return CommandResult(success=False)

        if show_cold:
            try:
                cold_memories = memory_router.whats_cold(threshold=0.3, limit=10)
                print(f"\n{Colors.CYAN}What's Cold (Neglected):{Colors.RESET}\n")
                if cold_memories:
                    for mem in cold_memories:
                        heat = mem.get("heat", 0.1)
                        content = mem.get("memory", mem.get("content", ""))[:100]
                        print(f"  ❄️  ({heat:.2f}) {content}...")
                else:
                    print(f"  {Colors.DIM}No cold memories found{Colors.RESET}")
                print()
                return CommandResult()
            except Exception as e:
                print(f"{Colors.RED}Error fetching cold memories: {e}{Colors.RESET}")
                return CommandResult(success=False)

        memory_results = []

        # Search via memory router (unless sessions_only)
        if not sessions_only and query:
            try:
                results = memory_router.search_memory(query, limit=5)
                for mem in results:
                    heat = mem.get("heat", 1.0)
                    heat_icon = "🔥" if heat > 0.7 else "•" if heat > 0.3 else "❄️"
                    memory_results.append({
                        "source": "router",
                        "content": mem.get("memory", mem.get("content", ""))[:150],
                        "score": mem.get("effective_score", mem.get("score", 0)),
                        "heat": heat,
                        "heat_icon": heat_icon,
                        "client": mem.get("client"),
                    })
            except Exception as e:
                print(f"{Colors.YELLOW}Memory search error: {e}{Colors.RESET}")

        # Display memory results
        if memory_results:
            print(f"\n{Colors.CYAN}Memory Results ({len(memory_results)}):{Colors.RESET}\n")
            for r in memory_results:
                heat_icon = r.get("heat_icon", "•")
                score = r.get("score", 0)
                client_str = f" #{r['client']}" if r.get("client") else ""
                print(f"  {heat_icon} ({score:.2f}){client_str}")
                print(f"     {r['content']}...")
                print()

        # Also search session history
        history_dir = self.thanos_dir / "History" / "Sessions"
        session_matches = []

        if history_dir.exists() and query:
            json_files = sorted(
                history_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True
            )[:30]

            for json_file in json_files:
                try:
                    data = json.loads(json_file.read_text())
                    for msg in data.get("history", []):
                        content = msg.get("content", "").lower()
                        if query.lower() in content:
                            session_matches.append({
                                "session": data.get("id", json_file.stem),
                                "date": data.get("started_at", "")[:16].replace("T", " "),
                                "role": msg.get("role", "unknown"),
                                "preview": msg.get("content", "")[:100],
                            })
                            if len(session_matches) >= 5:
                                break
                except (json.JSONDecodeError, KeyError):
                    continue
                if len(session_matches) >= 5:
                    break

        # Display session results
        if session_matches:
            print(f"\n{Colors.CYAN}Session History ({len(session_matches)} matches):{Colors.RESET}\n")
            for m in session_matches:
                role_color = Colors.PURPLE if m["role"] == "user" else Colors.CYAN
                print(f"  {Colors.DIM}{m['date']}{Colors.RESET} ({m['session']})")
                print(f"  {role_color}{m['role']}:{Colors.RESET} {m['preview']}...")
                print()

        if not memory_results and not session_matches:
            print(f"{Colors.DIM}No matches found for: {query}{Colors.RESET}")
            return CommandResult()

        if session_matches:
            print(f"{Colors.DIM}Use /resume <session_id> to restore a session{Colors.RESET}\n")

        return CommandResult()

    def handle_memory(self, args: str) -> CommandResult:
        """
        Handle /memory command - Display memory system information.

        Shows comprehensive status of all memory systems available to Thanos:
        - Memory Router: Unified memory routing layer
        - Session History: Saved conversation sessions
        - Swarm Memory: Multi-agent coordination memory
        - Hive Mind Memory: Collective intelligence memory
        - Claude-mem: Claude's persistent memory integration

        Displays connection status, statistics, and storage locations.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
        if not MEMORY_ROUTER_AVAILABLE:
            print(f"{Colors.RED}Memory router not available. Check installation.{Colors.RESET}")
            return CommandResult(success=False)

        print(f"\n{Colors.CYAN}Memory Systems:{Colors.RESET}\n")

        # Memory Router Status
        print(f"  {Colors.BOLD}Memory Router (Unified Layer):{Colors.RESET}")
        try:
            stats = memory_router.get_stats()
            print("    ✓ Memory router initialized")

            total = stats.get("total", 0)
            hot_count = stats.get("hot_count", 0)
            cold_count = stats.get("cold_count", 0)
            avg_heat = stats.get("avg_heat", 0)

            print(f"    📊 Total memories: {total}")
            print(f"    🔥 Hot memories: {hot_count}")
            print(f"    ❄️  Cold memories: {cold_count}")
            print(f"    🌡️  Average heat: {avg_heat:.2f}")

            unique_clients = stats.get("unique_clients", 0)
            unique_projects = stats.get("unique_projects", 0)
            if unique_clients or unique_projects:
                print(f"    📁 Clients: {unique_clients}, Projects: {unique_projects}")

            print("    🔗 Backend: Memory V2 (mem0 + Neon + heat)")
        except Exception as e:
            print(f"    {Colors.YELLOW}⚠ Could not fetch stats: {e}{Colors.RESET}")
            print(f"    {Colors.YELLOW}💡 Check THANOS_MEMORY_DATABASE_URL and OPENAI_API_KEY in .env{Colors.RESET}")

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
        print(f"{Colors.DIM}  /remember <content>   - Store memory{Colors.RESET}")
        print(f"{Colors.DIM}  /recall <query>       - Search memories{Colors.RESET}")
        print(f"{Colors.DIM}  /recall --hot         - Show top of mind{Colors.RESET}")
        print(f"{Colors.DIM}  /recall --cold        - Show neglected memories{Colors.RESET}\n")
        return CommandResult()
