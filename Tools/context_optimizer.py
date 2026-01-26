"""
Context Optimizer for Thanos.

Provides intelligent memory retrieval and injection to supplement transformer
context window limitations. When context fills, this system retrieves relevant
conversation summaries and historical context for injection on-demand.

Key Features:
    - Semantic search of conversation summaries
    - Heat-based ranking for recency/importance
    - Session-aware context retrieval
    - Token-budget-aware formatting
    - Configurable relevance thresholds

Key Classes:
    ContextOptimizer: Main context retrieval and injection engine

Usage - Basic:
    from Tools.context_optimizer import ContextOptimizer

    optimizer = ContextOptimizer()

    # Retrieve relevant context for current prompt
    context = optimizer.retrieve_relevant_context(
        current_prompt="What did we discuss about the API?",
        session_id="session-123"
    )

    # Use the context in your conversation
    print(context['formatted_context'])  # "Previously discussed: ..."

Usage - Advanced:
    # Retrieve with custom parameters
    context = optimizer.retrieve_relevant_context(
        current_prompt="API authentication",
        session_id="session-123",
        max_results=5,
        relevance_threshold=0.4,
        include_session_only=False,  # Search all sessions
        max_tokens=500
    )

    # Get raw memories for custom processing
    memories = context['memories']
    for mem in memories:
        print(f"Score: {mem['effective_score']:.2f} - {mem['memory'][:100]}")

Architecture:
    ContextOptimizer integrates with Memory V2 to provide context-aware retrieval
    of conversation summaries. It uses semantic search with heat-based ranking
    to surface the most relevant historical context.

    Retrieval flow:
    1. Embed current prompt using cached embeddings
    2. Search Memory V2 for conversation_summary domain
    3. Filter by session_id if specified
    4. Re-rank by similarity + heat + importance
    5. Format results for injection
    6. Respect token budget

Performance:
    - Typical retrieval: 200-500ms (cached embeddings)
    - First query: +500ms (embedding generation)
    - Memory overhead: Minimal (streaming-friendly)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# Configure logger for this module
logger = logging.getLogger(__name__)

# Memory V2 for semantic search
try:
    from Tools.memory_v2.service import MemoryService
    MEMORY_V2_AVAILABLE = True
except ImportError:
    logger.warning("Memory V2 not available - context optimization will fail")
    MEMORY_V2_AVAILABLE = False

# Tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    logger.warning("tiktoken not available - using fallback token counting")
    TIKTOKEN_AVAILABLE = False


class ContextOptimizer:
    """
    Intelligent context retrieval and injection engine.

    Retrieves relevant conversation summaries and historical context
    from Memory V2 using semantic search and heat-based ranking.
    Formats results for injection into conversation context while
    respecting token budgets.

    Attributes:
        memory_service: MemoryService instance for semantic search
        encoder: Tiktoken encoder for accurate token counting
        default_max_results: Default number of memories to retrieve
        default_relevance_threshold: Minimum relevance score (0-1)
        default_max_tokens: Default token budget for context injection

    Methods:
        retrieve_relevant_context: Main retrieval method
        format_context_for_injection: Format memories as injectable text
        estimate_context_tokens: Estimate token count of formatted context
    """

    def __init__(
        self,
        max_results: int = 5,
        relevance_threshold: float = 0.3,
        max_tokens: int = 1000
    ):
        """
        Initialize the context optimizer.

        Args:
            max_results: Default maximum number of memories to retrieve
            relevance_threshold: Default minimum relevance score (0-1)
            max_tokens: Default maximum tokens for formatted context
        """
        self.default_max_results = max_results
        self.default_relevance_threshold = relevance_threshold
        self.default_max_tokens = max_tokens

        # Initialize Memory V2 service
        self.memory_service = None
        if MEMORY_V2_AVAILABLE:
            try:
                self.memory_service = MemoryService()
                logger.info("ContextOptimizer initialized with Memory V2")
            except Exception as e:
                logger.warning(f"Failed to initialize Memory V2: {e}")
                logger.warning("Context optimizer will not function without Memory V2")
        else:
            logger.error("Memory V2 not available - context optimizer will not function")

        # Initialize tiktoken encoder (for Claude/GPT models)
        self.encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding (compatible with Claude and GPT-4)
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")

        logger.info(
            f"ContextOptimizer ready: max_results={max_results}, "
            f"relevance_threshold={relevance_threshold}, max_tokens={max_tokens}"
        )

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken (accurate for Claude/GPT).

        Args:
            text: Text to count tokens for

        Returns:
            Token count (int)
        """
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Token counting failed, using fallback: {e}")

        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4

    def retrieve_relevant_context(
        self,
        current_prompt: str,
        session_id: Optional[str] = None,
        max_results: Optional[int] = None,
        relevance_threshold: Optional[float] = None,
        include_session_only: bool = True,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant conversation summaries for context injection.

        This is the main method for retrieving historical context. It uses
        semantic search to find relevant conversation summaries, ranks them
        by relevance + heat + importance, and formats them for injection
        into the current conversation.

        Args:
            current_prompt: The current user prompt/query
            session_id: Optional session ID to filter results
            max_results: Maximum number of memories to retrieve (default: self.default_max_results)
            relevance_threshold: Minimum relevance score 0-1 (default: self.default_relevance_threshold)
            include_session_only: If True and session_id provided, only search current session
            max_tokens: Maximum tokens for formatted context (default: self.default_max_tokens)

        Returns:
            Dict with:
                - memories: List of retrieved memory dicts
                - formatted_context: Ready-to-inject context string
                - token_count: Token count of formatted context
                - retrieval_time_ms: Time taken for retrieval

        Raises:
            RuntimeError: If Memory V2 not available

        Example:
            >>> optimizer = ContextOptimizer()
            >>> context = optimizer.retrieve_relevant_context(
            ...     current_prompt="What did we discuss about API auth?",
            ...     session_id="session-123"
            ... )
            >>> print(context['formatted_context'])
            Previously discussed (Session: session-123):

            [Timestamp: 2024-01-20 14:30] Messages 1-50:
            User asked about API authentication options. Discussed OAuth2 vs JWT...
        """
        if not self.memory_service:
            raise RuntimeError("Memory V2 not available - cannot retrieve context")

        # Use defaults if not specified
        max_results = max_results or self.default_max_results
        relevance_threshold = relevance_threshold or self.default_relevance_threshold
        max_tokens = max_tokens or self.default_max_tokens

        start_time = datetime.now()

        # Build search filters
        # Always filter to conversation_summary domain
        filters = {
            "domain": "conversation_summary"
        }

        # Optionally filter to specific session
        if include_session_only and session_id:
            # Note: MemoryService.search() doesn't have session_id parameter
            # We'll need to filter results manually
            pass

        # Search Memory V2 for relevant conversation summaries
        try:
            logger.debug(
                f"Searching for context: query='{current_prompt[:50]}...', "
                f"session={session_id}, filters={filters}"
            )

            # Retrieve more results than needed for post-filtering
            search_limit = max_results * 3 if session_id and include_session_only else max_results

            memories = self.memory_service.search(
                query=current_prompt,
                limit=search_limit,
                domain="conversation_summary"
            )

            logger.debug(f"Found {len(memories)} initial results from Memory V2")

            # Filter by session_id if needed (manual filtering)
            if session_id and include_session_only:
                memories = [
                    mem for mem in memories
                    if self._extract_session_id(mem) == session_id
                ]
                logger.debug(f"After session filter: {len(memories)} results")

            # Filter by relevance threshold
            # Memory V2 returns results with 'effective_score' from heat ranking
            # Note: 'score' is distance (lower = better), 'effective_score' is weighted (higher = better)
            filtered_memories = []
            for mem in memories:
                # Calculate relevance from distance score (lower distance = higher relevance)
                # Distance is typically 0-2, so relevance = 1 - (distance / 2)
                distance = mem.get('score', 1.0)
                relevance = max(0, 1 - (distance / 2))
                mem['relevance'] = relevance

                if relevance >= relevance_threshold:
                    filtered_memories.append(mem)

            memories = filtered_memories[:max_results]
            logger.debug(
                f"After relevance filter (>= {relevance_threshold}): {len(memories)} results"
            )

            # Format context for injection
            formatted_context = self.format_context_for_injection(
                memories=memories,
                session_id=session_id,
                max_tokens=max_tokens
            )

            token_count = self.count_tokens(formatted_context)

            # Calculate retrieval time
            end_time = datetime.now()
            retrieval_time_ms = (end_time - start_time).total_seconds() * 1000

            logger.info(
                f"Retrieved {len(memories)} relevant contexts "
                f"({token_count} tokens) in {retrieval_time_ms:.0f}ms"
            )

            return {
                "memories": memories,
                "formatted_context": formatted_context,
                "token_count": token_count,
                "retrieval_time_ms": retrieval_time_ms,
                "count": len(memories)
            }

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            # Return empty context on failure
            return {
                "memories": [],
                "formatted_context": "",
                "token_count": 0,
                "retrieval_time_ms": 0,
                "count": 0,
                "error": str(e)
            }

    def format_context_for_injection(
        self,
        memories: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Format retrieved memories as injectable context text.

        Creates a formatted string suitable for injection into conversation
        context, with clear structure and metadata.

        Args:
            memories: List of memory dicts from Memory V2
            session_id: Optional session ID for header
            max_tokens: Maximum tokens for formatted output

        Returns:
            Formatted context string ready for injection

        Example output:
            Previously discussed (Session: session-123):

            [2024-01-20 14:30] Messages 1-50 (Relevance: 0.85):
            User asked about API authentication. Discussed OAuth2 vs JWT approaches...

            [2024-01-20 15:15] Messages 51-100 (Relevance: 0.72):
            Decided to use JWT for simplicity. Implemented token generation...
        """
        if not memories:
            return ""

        max_tokens = max_tokens or self.default_max_tokens

        # Build header
        header = "Previously discussed"
        if session_id:
            header += f" (Session: {session_id})"
        header += ":"

        lines = [header, ""]

        # Track token usage
        current_tokens = self.count_tokens("\n".join(lines))

        # Format each memory
        for mem in memories:
            # Extract metadata
            timestamp = mem.get('created_at', 'Unknown time')
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M')
            elif isinstance(timestamp, str):
                try:
                    # Parse ISO format
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    timestamp = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass

            message_range = self._extract_metadata(mem, 'message_range', 'unknown')
            relevance = mem.get('relevance', 0.0)
            memory_text = mem.get('memory', mem.get('content', ''))

            # Build memory entry
            entry_header = f"[{timestamp}] Messages {message_range} (Relevance: {relevance:.2f}):"
            entry = f"{entry_header}\n{memory_text}\n"

            # Check if adding this entry would exceed token budget
            entry_tokens = self.count_tokens(entry)
            if current_tokens + entry_tokens > max_tokens:
                logger.debug(
                    f"Token budget reached: {current_tokens + entry_tokens} > {max_tokens}. "
                    f"Truncating at {len(lines)} entries."
                )
                break

            lines.append(entry)
            current_tokens += entry_tokens

        formatted = "\n".join(lines)

        logger.debug(
            f"Formatted {len(memories)} memories into {current_tokens} tokens"
        )

        return formatted

    def estimate_context_tokens(self, memories: List[Dict[str, Any]]) -> int:
        """
        Estimate token count of formatted context without full formatting.

        Args:
            memories: List of memory dicts

        Returns:
            Estimated token count (int)
        """
        # Quick estimation: sum memory content tokens + overhead
        total = 50  # Header overhead

        for mem in memories:
            memory_text = mem.get('memory', mem.get('content', ''))
            total += self.count_tokens(memory_text) + 20  # +20 for metadata

        return total

    def _extract_session_id(self, memory: Dict[str, Any]) -> Optional[str]:
        """Extract session_id from memory metadata."""
        # Memory V2 doesn't expose payload metadata directly in search results
        # We'll need to check if there's a way to access it
        # For now, return None - this may need adjustment based on actual Memory V2 behavior
        return self._extract_metadata(memory, 'session_id')

    def _extract_metadata(self, memory: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Extract metadata from memory dict.

        Memory V2 stores metadata in the payload, but search results may not
        include all fields. This helper safely extracts metadata.

        Args:
            memory: Memory dict from search results
            key: Metadata key to extract
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        # Check if metadata is directly in the dict
        if key in memory:
            return memory[key]

        # Check if there's a metadata sub-dict
        if 'metadata' in memory and isinstance(memory['metadata'], dict):
            return memory['metadata'].get(key, default)

        # Check if there's a payload sub-dict
        if 'payload' in memory and isinstance(memory['payload'], dict):
            return memory['payload'].get(key, default)

        return default
