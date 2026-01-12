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

import re

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

    def _highlight_query_terms(self, content: str, query: str, max_length: int = 300) -> str:
        """
        Highlight query terms in content and create an intelligent preview.

        Extracts a preview window around the first match if possible, otherwise
        shows the beginning of the content. Highlights all occurrences of query
        terms using BOLD formatting.

        Args:
            content: Full message content
            query: Search query (may contain multiple words)
            max_length: Maximum preview length in characters

        Returns:
            Formatted preview with highlighted query terms
        """
        if not content:
            return ""

        # Split query into words for highlighting
        query_words = query.lower().split()

        # Find first significant match position for context window
        first_match_pos = len(content)  # Default to end if no match
        for word in query_words:
            if len(word) > 2:  # Skip very short words
                pos = content.lower().find(word)
                if pos != -1 and pos < first_match_pos:
                    first_match_pos = pos

        # Determine preview window
        if first_match_pos < len(content):
            # Center preview around first match
            start = max(0, first_match_pos - max_length // 3)
            end = min(len(content), start + max_length)
            preview = content[start:end]
            prefix = "..." if start > 0 else ""
            suffix = "..." if end < len(content) else ""
        else:
            # No match found, show beginning
            preview = content[:max_length]
            prefix = ""
            suffix = "..." if len(content) > max_length else ""

        # Highlight query terms (case-insensitive)
        for word in query_words:
            if len(word) > 1:  # Skip single characters
                # Create case-insensitive pattern that preserves original case
                pattern = re.compile(re.escape(word), re.IGNORECASE)
                preview = pattern.sub(
                    lambda m: f"{Colors.BOLD}{m.group()}{Colors.RESET}",
                    preview
                )

        return f"{prefix}{preview}{suffix}"

    def _parse_filters(self, args: str) -> tuple:
        """
        Parse search query and optional filters from command arguments.

        Supports filter syntax:
        - agent:<name> - Filter by agent name
        - date:<YYYY-MM-DD> - Filter by specific date
        - session:<id> - Filter by session ID
        - after:<YYYY-MM-DD> - Filter messages after date (inclusive)
        - before:<YYYY-MM-DD> - Filter messages before date (inclusive)

        Examples:
        - "authentication agent:architect"
        - "API decisions date:2026-01-11"
        - "error handling session:abc123"
        - "database changes after:2026-01-01 before:2026-01-31"

        Args:
            args: Raw command arguments with query and filters

        Returns:
            Tuple of (query_string, where_clause_dict)
        """
        # Pattern to match key:value filters
        filter_pattern = r'(\w+):([^\s]+)'

        # Extract all filters
        filters = {}
        matches = re.findall(filter_pattern, args)

        for key, value in matches:
            filters[key] = value

        # Remove filters from query to get clean search query
        query = re.sub(filter_pattern, '', args).strip()

        # Build ChromaDB where clause
        where_clause = {}

        # Direct equality filters
        if 'agent' in filters:
            where_clause['agent'] = filters['agent']

        if 'session' in filters or 'session_id' in filters:
            session_id = filters.get('session') or filters.get('session_id')
            where_clause['session_id'] = session_id

        if 'date' in filters:
            where_clause['date'] = filters['date']

        # Date range filters (ChromaDB uses $gte and $lte operators)
        if 'after' in filters and 'before' in filters:
            # Combined range: after <= date <= before
            where_clause['date'] = {
                '$gte': filters['after'],
                '$lte': filters['before']
            }
        elif 'after' in filters:
            # Only after: date >= after
            where_clause['date'] = {'$gte': filters['after']}
        elif 'before' in filters:
            # Only before: date <= before
            where_clause['date'] = {'$lte': filters['before']}

        return query, where_clause if where_clause else None

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
        - With filters: /history-search database changes agent:architect date:2026-01-11
        - Date range: /history-search API work after:2026-01-01 before:2026-01-31

        Supported filters:
        - agent:<name> - Filter by agent name
        - date:<YYYY-MM-DD> - Filter by specific date
        - session:<id> - Filter by session ID (prefix matching supported)
        - after:<YYYY-MM-DD> - Messages on or after this date
        - before:<YYYY-MM-DD> - Messages on or before this date

        Args:
            args: Search query (natural language) with optional filters

        Returns:
            CommandResult with action and success status
        """
        if not args:
            print(f"{Colors.DIM}Usage: /history-search <query> [filters]{Colors.RESET}")
            print(f"{Colors.DIM}Example: /history-search authentication implementation{Colors.RESET}")
            print(f"{Colors.DIM}Filters: agent:<name> date:<YYYY-MM-DD> session:<id>{Colors.RESET}")
            print(f"{Colors.DIM}         after:<date> before:<date>{Colors.RESET}")
            print(f"{Colors.DIM}Tip: Use natural language to search past conversations{Colors.RESET}")
            return CommandResult()

        # Parse query and filters
        query, where_filter = self._parse_filters(args)

        # Validate that we have a query after filter extraction
        if not query:
            print(f"{Colors.DIM}Error: No search query provided{Colors.RESET}")
            print(f"{Colors.DIM}Filters must be combined with a search query{Colors.RESET}")
            return CommandResult(success=False)

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
            # Build search parameters
            search_params = {
                "query": query,
                "collection": "conversations",
                "limit": 10,
            }

            # Add where clause if filters were provided
            if where_filter:
                search_params["where"] = where_filter

            result = self._run_async(
                self.session._chroma.call_tool(
                    "semantic_search",
                    search_params,
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

            # Display results with context and highlighting
            print(f"\n{Colors.CYAN}Conversation History Search Results:{Colors.RESET}")

            # Show active filters if any
            if where_filter:
                filter_parts = []
                for key, value in where_filter.items():
                    if isinstance(value, dict):
                        # Date range filter
                        if '$gte' in value and '$lte' in value:
                            filter_parts.append(f"{key}: {value['$gte']} to {value['$lte']}")
                        elif '$gte' in value:
                            filter_parts.append(f"{key} >= {value['$gte']}")
                        elif '$lte' in value:
                            filter_parts.append(f"{key} <= {value['$lte']}")
                    else:
                        filter_parts.append(f"{key}={value}")
                print(f"{Colors.DIM}Active filters: {', '.join(filter_parts)}{Colors.RESET}")

            print(f"{Colors.DIM}Found {len(results)} semantically similar messages:{Colors.RESET}\n")

            for i, match in enumerate(results, 1):
                content = match.get("content", "")
                metadata = match.get("metadata", {})
                similarity = match.get("similarity", 0)

                # Extract metadata
                session_id = metadata.get("session_id", "unknown")
                date = metadata.get("date", "unknown")
                timestamp = metadata.get("timestamp", "")
                role = metadata.get("role", "unknown")
                agent = metadata.get("agent", "unknown")

                # Format similarity score as percentage
                score_pct = similarity * 100

                # Color code by role
                role_color = Colors.PURPLE if role == "user" else Colors.CYAN

                # Get time from timestamp if available
                time_str = ""
                if timestamp and "T" in timestamp:
                    time_str = timestamp.split("T")[1][:5]  # HH:MM

                # Format session context line
                context_parts = [
                    f"{date}",
                    f"{time_str}" if time_str else None,
                    f"agent:{agent}",
                    f"session:{session_id[:8]}"
                ]
                context_str = " • ".join(p for p in context_parts if p)

                # Display result with enhanced formatting
                print(f"  {i}. {Colors.BOLD}[{score_pct:.1f}% match]{Colors.RESET}")
                print(f"     {Colors.DIM}{context_str}{Colors.RESET}")

                # Highlight query terms in content preview
                highlighted_preview = self._highlight_query_terms(content, query, max_length=250)
                print(f"     {role_color}{role}:{Colors.RESET} {highlighted_preview}")
                print()

            # Show helpful tips
            print(f"{Colors.DIM}💡 Tips:{Colors.RESET}")
            print(f"{Colors.DIM}   • Use /resume <session_id> to restore a session{Colors.RESET}")
            print(f"{Colors.DIM}   • Query terms are highlighted in {Colors.BOLD}bold{Colors.RESET}{Colors.DIM}{Colors.RESET}")
            print(f"{Colors.DIM}   • Add filters: agent:<name> date:<YYYY-MM-DD> session:<id>{Colors.RESET}")
            print(f"{Colors.DIM}   • Date ranges: after:<date> before:<date>{Colors.RESET}\n")

            return CommandResult()

        except Exception as e:
            print(f"{Colors.DIM}Error searching conversation history: {e}{Colors.RESET}")
            return CommandResult(success=False)
