#!/usr/bin/env python3
"""
MemoryHandler - Handles MemOS integration commands in Thanos Interactive Mode.

This module manages memory storage and retrieval using the MemOS hybrid memory
system, which combines Neo4j knowledge graph with ChromaDB vector store for
powerful semantic search and relationship tracking. It provides functionality
for storing observations, decisions, patterns, and entities, as well as searching
across both graph relationships and semantic similarity.

Commands:
    /remember <content>     - Store a memory in MemOS knowledge graph
    /recall <query>         - Search memories using hybrid search
    /memory                 - Display memory system information and status

Classes:
    MemoryHandler: Handler for all MemOS integration commands

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output
    - MEMOS_AVAILABLE: Flag indicating if MemOS is available
    - MemOS: Hybrid memory system (optional dependency)

Architecture:
    MemOS provides a dual-storage architecture:
    - Neo4j graph database: Stores structured knowledge with entities and relationships
    - ChromaDB vector store: Enables semantic similarity search
    - Hybrid search: Combines graph traversal and vector similarity for optimal recall

    Memory types supported:
    - decision: Important decisions and their rationale
    - pattern: Recurring patterns and insights
    - commitment: Promises and obligations
    - entity: People, projects, tools, concepts
    - observation: General notes and observations

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
    - Tools.memos: MemOS hybrid memory system
    - Tools.command_handlers.base: Base handler infrastructure
"""

import json
import os
from pathlib import Path

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors, MEMOS_AVAILABLE


class MemoryHandler(BaseHandler):
    """
    Handler for MemOS integration commands.

    Provides functionality for:
    - Storing memories with type classification (decision, pattern, observation, etc.)
    - Searching memories using hybrid search (vector + graph)
    - Displaying memory system status and configuration
    - Entity extraction and domain classification
    - Session history search fallback
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
        Handle /remember command - Store a memory in MemOS knowledge graph.

        Stores content in both Neo4j (for relationship tracking) and ChromaDB
        (for semantic search). Supports type prefixes for categorization:
        - decision: Important decisions and their rationale
        - pattern: Recurring patterns or best practices
        - commitment: Promises or commitments made
        - entity: Information about people, projects, or things
        - observation: General observations (default)

        Entity extraction: Words starting with @ are extracted as entities.
        Domain detection: Automatically categorized based on current agent.

        Args:
            args: Content to store, optionally prefixed with type (e.g., "decision: ...")

        Returns:
            CommandResult with action and success status
        """
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
        current_agent = self._get_current_agent()
        agent_domain_map = {
            "ops": "work",
            "strategy": "work",
            "coach": "personal",
            "health": "health",
        }
        domain = agent_domain_map.get(current_agent, "general")

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
                    "agent": current_agent,
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

    def handle_recall(self, args: str) -> CommandResult:
        """
        Handle /recall command - Search memories using MemOS hybrid search.

        Searches both the knowledge graph (for relationship-based results) and
        vector store (for semantic similarity). Also searches session history
        as a fallback or supplement.

        Results include:
        - Vector search: Semantically similar memories with similarity scores
        - Graph search: Related entities and patterns from knowledge graph
        - Session history: Past conversations matching the query

        Args:
            args: Search query, optionally with --sessions flag to skip MemOS

        Returns:
            CommandResult with action and success status
        """
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

    def handle_memory(self, args: str) -> CommandResult:
        """
        Handle /memory command - Display memory system information.

        Shows comprehensive status of all memory systems available to Thanos:
        - MemOS (Neo4j + ChromaDB): Primary hybrid memory system
        - Session History: Saved conversation sessions
        - Swarm Memory: Multi-agent coordination memory
        - Hive Mind Memory: Collective intelligence memory
        - Claude-mem: Claude's persistent memory integration

        Displays connection status, configuration, and storage locations.

        Args:
            args: Command arguments (ignored for this command)

        Returns:
            CommandResult with action and success status
        """
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
