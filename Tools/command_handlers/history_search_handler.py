#!/usr/bin/env python3
"""
HistorySearchHandler - Handles semantic search of conversation history.

This module provides semantic search capabilities for conversation history
using ChromaAdapter's vector search on the 'conversations' collection. Messages
indexed by SessionManager can be searched using natural language queries to find
relevant past conversations.

Commands:
    /history-search <query>  - Semantically search conversation history

Classes:
    HistorySearchHandler: Handler for conversation history semantic search

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output
    - ChromaAdapter: Vector search engine for semantic similarity
    - SessionManager: Manages sessions with ChromaAdapter integration

Architecture:
    Messages are indexed to ChromaAdapter's 'conversations' collection with metadata:
    - session_id: Session identifier for grouping messages
    - timestamp: Message timestamp (ISO format)
    - role: Message role (user, assistant)
    - agent: Agent name that handled the message
    - date: Date string for filtering (YYYY-MM-DD)

    Semantic search uses vector embeddings to find semantically similar messages
    across all indexed sessions, enabling "what did we discuss about X?" queries.

Example:
    handler = HistorySearchHandler(orchestrator, session_mgr, context_mgr,
                                   state_reader, thanos_dir)

    # Search conversation history
    result = handler.handle_history_search("authentication implementation")

    # Results show relevant messages with session context and similarity scores

See Also:
    - Tools.command_handlers.base: Base handler infrastructure
    - Tools.adapters.chroma_adapter: ChromaAdapter for vector search
    - Tools.session_manager: SessionManager with indexing capabilities
"""

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors


class HistorySearchHandler(BaseHandler):
    """
    Handler for semantic search of conversation history.

    Provides functionality for:
    - Semantic search across all indexed conversation messages
    - Filtering by session, date, agent, or role
    - Displaying results with session context and similarity scores
    - Graceful degradation when ChromaAdapter is not available
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
        Initialize HistorySearchHandler with dependencies.

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

    def handle_history_search(self, args: str) -> CommandResult:
        """
        Handle /history-search command - Search conversation history using semantic similarity.

        Uses ChromaAdapter's semantic_search to query the 'conversations' collection,
        finding messages that are semantically similar to the query. Results include
        session context (date, agent, role) and similarity scores.

        Query syntax:
        - Basic: /history-search authentication
        - Multi-word: /history-search API implementation patterns
        - Context-aware: /history-search what did we decide about testing

        Args:
            args: Search query (natural language)

        Returns:
            CommandResult with action and success status
        """
        if not args:
            print(f"{Colors.DIM}Usage: /history-search <query>{Colors.RESET}")
            print(f"{Colors.DIM}Example: /history-search authentication implementation{Colors.RESET}")
            print(f"{Colors.DIM}Tip: Use natural language to search past conversations{Colors.RESET}")
            return CommandResult()

        query = args.strip()

        # Check if SessionManager has ChromaAdapter configured
        if not hasattr(self.session, "_chroma") or self.session._chroma is None:
            print(
                f"{Colors.DIM}ChromaAdapter not configured. "
                f"Conversation history search requires ChromaDB.{Colors.RESET}"
            )
            print(
                f"{Colors.DIM}Falling back to /recall command for simple text search.{Colors.RESET}"
            )
            return CommandResult(success=False)

        # Perform semantic search on conversations collection
        try:
            result = self._run_async(
                self.session._chroma.call_tool(
                    "semantic_search",
                    {
                        "query": query,
                        "collection": "conversations",
                        "limit": 10,
                    },
                )
            )

            if not result or not result.success:
                error_msg = result.error if result else "Unknown error"
                print(f"{Colors.DIM}Search failed: {error_msg}{Colors.RESET}")
                return CommandResult(success=False)

            # Extract and format results
            results = result.data.get("results", [])

            if not results:
                print(f"{Colors.DIM}No matches found for: {query}{Colors.RESET}")
                print(
                    f"{Colors.DIM}Tip: Messages must be indexed first. "
                    f"Use SessionManager.index_session() to index current session.{Colors.RESET}"
                )
                return CommandResult()

            # Display results with context
            print(f"\n{Colors.CYAN}Conversation History Search Results ({len(results)} matches):{Colors.RESET}\n")

            for i, match in enumerate(results, 1):
                content = match.get("content", "")
                metadata = match.get("metadata", {})
                similarity = match.get("similarity", 0)

                # Extract metadata
                session_id = metadata.get("session_id", "unknown")
                date = metadata.get("date", "unknown")
                role = metadata.get("role", "unknown")
                agent = metadata.get("agent", "unknown")

                # Format similarity score as percentage
                score_pct = similarity * 100

                # Color code by role
                role_color = Colors.PURPLE if role == "user" else Colors.CYAN

                # Display result
                print(f"  {i}. {Colors.BOLD}[{score_pct:.1f}% match]{Colors.RESET} {Colors.DIM}{date} • {agent} • session {session_id[:4]}{Colors.RESET}")
                print(f"     {role_color}{role}:{Colors.RESET} {content[:200]}{'...' if len(content) > 200 else ''}")
                print()

            print(f"{Colors.DIM}Use /resume <session_id> to restore a session{Colors.RESET}\n")
            return CommandResult()

        except Exception as e:
            print(f"{Colors.DIM}Error searching conversation history: {e}{Colors.RESET}")
            return CommandResult(success=False)
