#!/usr/bin/env python3
"""
HistorySearchHandler - Handles semantic search of conversation history.

This module provides semantic search capabilities for conversation history
using Memory V2 (Neon pgvector). Messages can be searched using natural
language queries to find relevant past conversations.

Commands:
    /history-search <query>  - Semantically search conversation history

Classes:
    HistorySearchHandler: Handler for conversation history semantic search

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output
    - MemoryService: Memory V2 service for semantic search (Neon pgvector)

Architecture:
    Memories are stored in Neon pgvector with metadata:
    - source: Where the memory came from (conversation, manual, etc.)
    - client: Associated client name
    - project: Associated project name
    - session_id: Session identifier for grouping messages
    - timestamp: Message timestamp (ISO format)
    - role: Message role (user, assistant)
    - agent: Agent name that handled the message
    - date: Date string for filtering (YYYY-MM-DD)

    Semantic search uses vector embeddings (mem0 + Voyage AI) ranked by
    similarity * heat * importance to find relevant memories.

Example:
    handler = HistorySearchHandler(orchestrator, session_mgr, context_mgr,
                                   state_reader, thanos_dir)

    # Search conversation history
    result = handler.handle_history_search("authentication implementation")

    # Results show relevant memories with context and relevance scores

See Also:
    - Tools.command_handlers.base: Base handler infrastructure
    - Tools.memory_v2: Memory V2 service for semantic search
"""

import re
import logging

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors

logger = logging.getLogger(__name__)


class HistorySearchHandler(BaseHandler):
    """
    Handler for semantic search of conversation history.

    Provides functionality for:
    - Semantic search across all memories using Memory V2 (Neon pgvector)
    - Filtering by client, source, or memory type
    - Displaying results with context, heat scores, and relevance
    - Heat-based ranking (recent/accessed memories rank higher)
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

        # Initialize Memory V2 service (lazy loading)
        self._memory_service = None

    @property
    def memory_service(self):
        """Lazy-load Memory V2 service."""
        if self._memory_service is None:
            try:
                from Tools.memory_v2 import get_memory_service
                self._memory_service = get_memory_service()
            except Exception as e:
                logger.warning(f"Failed to initialize Memory V2: {e}")
                return None
        return self._memory_service

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
        - client:<name> - Filter by client name
        - source:<name> - Filter by source (conversation, manual, telegram, etc.)
        - type:<name> - Filter by memory type
        - agent:<name> - Filter by agent name (legacy, maps to source)
        - date:<YYYY-MM-DD> - Filter by specific date (note: limited support)
        - session:<id> - Filter by session ID (note: limited support)

        Note: Memory V2 uses simpler filtering than ChromaDB. Date ranges
        (after/before) are not directly supported. For complex date queries,
        consider using the memory_v2 service directly with SQL.

        Examples:
        - "authentication client:Orlando"
        - "API decisions source:conversation"
        - "error handling type:decision"
        - "database changes client:Memphis"

        Args:
            args: Raw command arguments with query and filters

        Returns:
            Tuple of (query_string, filter_dict)
        """
        # Pattern to match key:value filters
        filter_pattern = r'(\w+):([^\s]+)'

        # Extract all filters
        raw_filters = {}
        matches = re.findall(filter_pattern, args)

        for key, value in matches:
            raw_filters[key] = value

        # Remove filters from query to get clean search query
        query = re.sub(filter_pattern, '', args).strip()

        # Build Memory V2 filter dict
        filters = {}

        # Map filter keys to Memory V2 schema
        if 'client' in raw_filters:
            filters['client'] = raw_filters['client']

        if 'source' in raw_filters:
            filters['source'] = raw_filters['source']

        # Legacy agent filter - map to source if it looks like a source type
        if 'agent' in raw_filters:
            # For backward compatibility, treat agent as a generic filter
            # Memory V2 doesn't have native agent support, but we preserve
            # it for display purposes
            filters['agent'] = raw_filters['agent']

        if 'type' in raw_filters or 'memory_type' in raw_filters:
            filters['memory_type'] = raw_filters.get('type') or raw_filters.get('memory_type')

        # Session and date filters (preserved for compatibility)
        if 'session' in raw_filters or 'session_id' in raw_filters:
            session_id = raw_filters.get('session') or raw_filters.get('session_id')
            filters['session_id'] = session_id

        if 'date' in raw_filters:
            filters['date'] = raw_filters['date']

        # Note: after/before date ranges not directly supported in Memory V2
        # Store them for display purposes but they won't filter results
        if 'after' in raw_filters:
            filters['_after'] = raw_filters['after']
        if 'before' in raw_filters:
            filters['_before'] = raw_filters['before']

        return query, filters if filters else None

    def handle_history_search(self, args: str) -> CommandResult:
        """
        Handle /history-search command - Search memories using semantic similarity.

        Uses Memory V2's semantic search with heat-based ranking to find relevant
        memories. Results are ranked by similarity * heat * importance.

        Query syntax:
        - Basic: /history-search authentication
        - Multi-word: /history-search API implementation patterns
        - Context-aware: /history-search what did we decide about testing
        - With filters: /history-search database changes client:Orlando
        - Source filter: /history-search meeting notes source:hey_pocket

        Supported filters:
        - client:<name> - Filter by client name
        - source:<name> - Filter by source (conversation, manual, telegram, hey_pocket)
        - type:<name> - Filter by memory type

        Args:
            args: Search query (natural language) with optional filters

        Returns:
            CommandResult with action and success status
        """
        if not args:
            print(f"{Colors.DIM}Usage: /history-search <query> [filters]{Colors.RESET}")
            print(f"{Colors.DIM}Example: /history-search authentication implementation{Colors.RESET}")
            print(f"{Colors.DIM}Filters: client:<name> source:<name> type:<type>{Colors.RESET}")
            print(f"{Colors.DIM}Tip: Use natural language to search memories{Colors.RESET}")
            return CommandResult()

        # Parse query and filters
        query, filters = self._parse_filters(args)

        # Validate that we have a query after filter extraction
        if not query:
            print(f"{Colors.DIM}Error: No search query provided{Colors.RESET}")
            print(f"{Colors.DIM}Filters must be combined with a search query{Colors.RESET}")
            return CommandResult(success=False)

        # Check if Memory V2 service is available
        if self.memory_service is None:
            print(
                f"{Colors.DIM}Memory V2 not configured. "
                f"Memory search requires THANOS_MEMORY_DATABASE_URL.{Colors.RESET}"
            )
            print(
                f"{Colors.DIM}Falling back to /recall command for simple text search.{Colors.RESET}"
            )
            return CommandResult(success=False)

        # Perform semantic search using Memory V2
        try:
            # Extract filters for Memory V2 (only supported ones)
            memory_filters = None
            if filters:
                memory_filters = {
                    k: v for k, v in filters.items()
                    if k in ('client', 'source', 'memory_type') and not k.startswith('_')
                }
                if not memory_filters:
                    memory_filters = None

            # Search using Memory V2
            results = self.memory_service.search(
                query=query,
                limit=10,
                filters=memory_filters
            )

            if not results:
                print(f"{Colors.DIM}No matches found for: {query}{Colors.RESET}")
                print(
                    f"{Colors.DIM}Tip: Memories are automatically indexed when added.{Colors.RESET}"
                )
                return CommandResult()

            # Display results with context and highlighting
            print(f"\n{Colors.CYAN}Memory Search Results:{Colors.RESET}")

            # Show active filters if any
            if filters:
                filter_parts = []
                for key, value in filters.items():
                    if not key.startswith('_'):  # Skip internal keys
                        filter_parts.append(f"{key}={value}")
                if filter_parts:
                    print(f"{Colors.DIM}Active filters: {', '.join(filter_parts)}{Colors.RESET}")

            print(f"{Colors.DIM}Found {len(results)} relevant memories:{Colors.RESET}\n")

            for i, match in enumerate(results, 1):
                # Memory V2 uses 'memory' key, fall back to 'content'
                content = match.get("memory", match.get("content", ""))

                # Get scores
                effective_score = match.get("effective_score", match.get("score", 0))
                heat = match.get("heat", 1.0)
                importance = match.get("importance", 1.0)

                # Get metadata
                client = match.get("client", "")
                source = match.get("source", "")
                memory_type = match.get("memory_type", "")
                created_at = match.get("created_at", "")

                # Format score as percentage
                score_pct = effective_score * 100 if effective_score <= 1 else effective_score

                # Heat indicator
                if heat > 0.7:
                    heat_indicator = f"{Colors.RED}🔥{Colors.RESET}"
                elif heat > 0.3:
                    heat_indicator = "•"
                else:
                    heat_indicator = f"{Colors.CYAN}❄️{Colors.RESET}"

                # Format context line
                context_parts = []
                if client:
                    context_parts.append(f"client:{client}")
                if source:
                    context_parts.append(f"source:{source}")
                if memory_type:
                    context_parts.append(f"type:{memory_type}")
                if created_at:
                    # Extract date part
                    date_str = str(created_at)[:10] if created_at else ""
                    if date_str:
                        context_parts.append(date_str)
                context_str = " • ".join(context_parts) if context_parts else "no context"

                # Display result with enhanced formatting
                print(f"  {i}. {heat_indicator} {Colors.BOLD}[{score_pct:.1f}% relevance]{Colors.RESET}")
                print(f"     {Colors.DIM}{context_str}{Colors.RESET}")

                # Highlight query terms in content preview
                highlighted_preview = self._highlight_query_terms(content, query, max_length=250)
                print(f"     {highlighted_preview}")
                print()

            # Show helpful tips
            print(f"{Colors.DIM}Tips:{Colors.RESET}")
            print(f"{Colors.DIM}   - 🔥 = hot (recently accessed)  • = warm  ❄️ = cold (neglected){Colors.RESET}")
            print(f"{Colors.DIM}   - Add filters: client:<name> source:<name> type:<type>{Colors.RESET}")
            print(f"{Colors.DIM}   - Use /memory-hot to see current focus areas{Colors.RESET}\n")

            return CommandResult()

        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            print(f"{Colors.DIM}Error searching memories: {e}{Colors.RESET}")
            return CommandResult(success=False)
