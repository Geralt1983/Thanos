#!/usr/bin/env python3
"""
MemoryHandler - Handles memory commands in Thanos Interactive Mode.

This module manages memory storage and retrieval using Memory V2 (primary)
with fallback to MemOS (legacy). Memory V2 uses cloud-first architecture
with heat decay for ADHD-friendly memory surfacing.

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
    - Memory V2: Cloud-first memory with heat decay (primary)
    - MemOS: Legacy hybrid memory system (fallback)

Architecture:
    Memory V2 (Primary):
    - mem0: Automatic fact extraction and deduplication
    - OpenAI: Embeddings (text-embedding-3-small, 1536 dimensions)
    - Neon pgvector: Vector storage (serverless PostgreSQL)
    - Heat decay: Recent/accessed memories surface naturally

    MemOS (Fallback):
    - Neo4j graph database: Stores structured knowledge
    - ChromaDB vector store: Enables semantic similarity search

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
    - Tools.memory_v2: Cloud-first memory with heat decay
    - Tools.memos: Legacy MemOS hybrid memory system
    - Tools.command_handlers.base: Base handler infrastructure
"""

import json
import os
from pathlib import Path

from Tools.command_handlers.base import (
    BaseHandler,
    CommandResult,
    Colors,
    MEMOS_AVAILABLE,
    MEMORY_V2_AVAILABLE,
)


class MemoryHandler(BaseHandler):
    """
    Handler for memory integration commands.

    Provides functionality for:
    - Storing memories with automatic fact extraction (Memory V2)
    - Searching memories with heat-based ranking (recent/accessed surface first)
    - ADHD helpers: what's hot, what's cold
    - Displaying memory system status and configuration
    - Fallback to MemOS if Memory V2 is unavailable

    Priority:
    1. Memory V2 (cloud-first with heat decay)
    2. MemOS (legacy Neo4j + ChromaDB)
    3. Session history (last resort)
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

        Uses Memory V2 (cloud-first with heat decay) as primary storage,
        with fallback to MemOS if unavailable.

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

        # Try Memory V2 first (primary)
        memory_v2 = self._get_memory_v2()
        if memory_v2:
            try:
                result = memory_v2.add(content, metadata=metadata)

                if result:
                    print(f"\n{Colors.GREEN}Memory stored (V2):{Colors.RESET}")
                    print(f"  Type: {memory_type}")
                    if client:
                        print(f"  Client: {client}")
                    if entities:
                        print(f"  Entities: {', '.join(entities)}")
                    print("  Heat: 1.0 (fresh)")
                    print()
                    return CommandResult()
            except Exception as e:
                # Log but continue to fallback
                print(f"{Colors.YELLOW}Memory V2 failed, trying MemOS...{Colors.RESET}")

        # Fallback to MemOS
        memos = self._get_memos()
        if memos:
            # Detect domain from current agent
            agent_domain_map = {
                "ops": "work",
                "strategy": "work",
                "coach": "personal",
                "health": "health",
            }
            domain = agent_domain_map.get(current_agent, "general")

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
                print(f"\n{Colors.GREEN}Memory stored (MemOS):{Colors.RESET}")
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
                print(f"{Colors.RED}Failed to store memory: {error}{Colors.RESET}")
                return CommandResult(success=False)

        # No memory system available
        print(
            f"{Colors.RED}No memory system available. "
            f"Check Memory V2 or MemOS configuration.{Colors.RESET}"
        )
        return CommandResult(success=False)

    def handle_recall(self, args: str) -> CommandResult:
        """
        Handle /recall command - Search memories using semantic search.

        Uses Memory V2 (with heat-based ranking) as primary search,
        with fallback to MemOS hybrid search. Also searches session history.

        Results include:
        - Memory V2: Heat-ranked semantic search (similarity * heat * importance)
        - MemOS (fallback): Vector + graph hybrid search
        - Session history: Past conversations matching the query

        Flags:
            --sessions: Search only session history, skip memory systems
            --hot: Show what's hot (top of mind, high heat)
            --cold: Show what's cold (neglected, low heat)

        Args:
            args: Search query with optional flags

        Returns:
            CommandResult with action and success status
        """
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
        memory_v2 = self._get_memory_v2()
        if memory_v2:
            if show_hot:
                hot_memories = memory_v2.whats_hot(10)
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

            if show_cold:
                cold_memories = memory_v2.whats_cold(threshold=0.3, limit=10)
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

        memory_results = []

        # Try Memory V2 first (unless sessions_only)
        if memory_v2 and not sessions_only and query:
            try:
                results = memory_v2.search(query, limit=5)
                for mem in results:
                    heat = mem.get("heat", 1.0)
                    heat_icon = "🔥" if heat > 0.7 else "•" if heat > 0.3 else "❄️"
                    memory_results.append({
                        "source": "v2",
                        "content": mem.get("memory", mem.get("content", ""))[:150],
                        "score": mem.get("effective_score", mem.get("score", 0)),
                        "heat": heat,
                        "heat_icon": heat_icon,
                        "client": mem.get("client"),
                    })
            except Exception as e:
                print(f"{Colors.YELLOW}Memory V2 search failed, trying MemOS...{Colors.RESET}")

        # Fallback to MemOS if no Memory V2 results
        if not memory_results and not sessions_only:
            memos = self._get_memos()
            if memos:
                result = self._run_async(
                    memos.recall(query=query, limit=5, use_graph=True, use_vector=True)
                )

                if result and result.success:
                    if result.vector_results:
                        for item in result.vector_results[:3]:
                            memory_results.append({
                                "source": "memos_vector",
                                "content": item.get("content", "")[:150],
                                "type": item.get("memory_type", "memory"),
                                "score": item.get("similarity", 0),
                            })

                    if result.graph_results:
                        nodes = result.graph_results.get("nodes", [])
                        for node in nodes[:3]:
                            props = node.get("properties", {})
                            memory_results.append({
                                "source": "memos_graph",
                                "content": props.get("content", props.get("description", ""))[:150],
                                "type": node.get("labels", ["memory"])[0] if node.get("labels") else "memory",
                            })

        # Display memory results
        if memory_results:
            source_label = "Memory V2" if memory_results[0].get("source") == "v2" else "MemOS"
            print(f"\n{Colors.CYAN}{source_label} Results ({len(memory_results)}):{Colors.RESET}\n")
            for r in memory_results:
                if r.get("source") == "v2":
                    heat_icon = r.get("heat_icon", "•")
                    score = r.get("score", 0)
                    client_str = f" #{r['client']}" if r.get("client") else ""
                    print(f"  {heat_icon} ({score:.2f}){client_str}")
                    print(f"     {r['content']}...")
                else:
                    source_icon = "🔍" if r["source"] == "memos_vector" else "🔗"
                    score_str = f" ({r.get('score', 0):.2f})" if r.get("score") else ""
                    type_str = f"[{r.get('type', 'memory')}]"
                    print(f"  {source_icon} {type_str}{score_str}")
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
        - Memory V2: Cloud-first memory with heat decay (primary)
        - MemOS (Neo4j + ChromaDB): Legacy hybrid memory system
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
        print(f"\n{Colors.CYAN}Memory Systems:{Colors.RESET}\n")

        # Memory V2 Status (primary system)
        print(f"  {Colors.BOLD}Memory V2 (Primary):{Colors.RESET}")
        memory_v2 = self._get_memory_v2()
        if memory_v2:
            print("    ✓ Memory V2 initialized")
            try:
                stats = memory_v2.stats()
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

                print("    🔗 Backend: OpenAI embeddings + Neon pgvector")
            except Exception as e:
                print(f"    {Colors.YELLOW}⚠ Could not fetch stats: {e}{Colors.RESET}")
        else:
            if MEMORY_V2_AVAILABLE:
                print(f"    {Colors.YELLOW}⚠ Memory V2 available but not initialized{Colors.RESET}")
                print(f"    {Colors.YELLOW}💡 Check THANOS_MEMORY_DATABASE_URL and OPENAI_API_KEY in .env{Colors.RESET}")
            else:
                print("    ✗ Memory V2 not available")
                print(f"    {Colors.YELLOW}💡 Install mem0ai and psycopg2 packages{Colors.RESET}")

        print()

        # MemOS Status (fallback system)
        print(f"  {Colors.BOLD}MemOS (Fallback):{Colors.RESET}")
        memos = self._get_memos()
        if memos:
            print("    ✓ MemOS initialized")

            # Neo4j status
            neo4j_url = os.environ.get("NEO4J_URL", "")
            if neo4j_url:
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
                    print(f"    {Colors.YELLOW}⚠ Neo4j connection issue{Colors.RESET}")
        else:
            if MEMOS_AVAILABLE:
                print(f"    {Colors.YELLOW}⚠ MemOS available but not initialized{Colors.RESET}")
            else:
                print("    ✗ MemOS not available (dependencies missing)")

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
