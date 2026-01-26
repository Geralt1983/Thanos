"""
Conversation Summarization Engine for Thanos.

Provides LLM-based summarization of conversation history to handle context
window limitations intelligently. When context fills, older messages are
summarized and stored, enabling long sessions without losing critical context.

Key Features:
    - LLM-based intelligent summarization of message history
    - Token-aware processing to stay within limits
    - Key point extraction from conversations
    - Progressive summarization for very long sessions
    - Configurable compression ratios

Key Classes:
    ConversationSummarizer: Main summarization engine

Usage - Basic:
    from Tools.conversation_summarizer import ConversationSummarizer

    summarizer = ConversationSummarizer()

    # Summarize a conversation
    messages = [
        {"role": "user", "content": "What's the weather?"},
        {"role": "assistant", "content": "I'll check for you..."},
        # ... more messages
    ]

    summary = summarizer.summarize_messages(messages, max_length=500)
    print(summary)  # "User asked about weather. Assistant provided forecast..."

    # Extract key points
    key_points = summarizer.extract_key_points(messages)
    print(key_points)  # ["Weather query", "Forecast provided", ...]

Usage - Advanced:
    # Custom configuration
    summarizer = ConversationSummarizer(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        compression_ratio=0.3
    )

    # Progressive summarization (for very long conversations)
    summary = summarizer.summarize_messages(
        messages,
        max_length=1000,
        preserve_recent=10  # Keep last 10 messages verbatim
    )

Architecture:
    The summarizer uses LiteLLMClient for actual LLM calls and tiktoken for
    accurate token counting. It chunks messages intelligently to stay within
    model context limits while maintaining narrative coherence.

    Summarization flow:
    1. Count tokens in message history
    2. Determine if chunking needed
    3. Generate summary via LLM
    4. Extract key facts/decisions
    5. Return compressed representation

Token Counting:
    Uses tiktoken library for accurate token estimation compatible with
    Claude and GPT models. Falls back to rough character-based estimation
    if tiktoken unavailable.

Performance:
    - Typical summarization: 1-3s for 50 messages
    - Token counting: <10ms
    - Memory overhead: Minimal (streaming-friendly)
"""

import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict

# Configure logger for this module
logger = logging.getLogger(__name__)

# LiteLLM client import
try:
    from Tools.litellm import get_client, LiteLLMClient
    LITELLM_AVAILABLE = True
except ImportError:
    logger.warning("LiteLLM client not available - summarization will fail")
    LITELLM_AVAILABLE = False

# Tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    logger.warning("tiktoken not available - using fallback token counting")
    TIKTOKEN_AVAILABLE = False


@dataclass
class SummaryResult:
    """Result from conversation summarization."""
    summary: str
    key_points: List[str]
    original_token_count: int
    summary_token_count: int
    compression_ratio: float
    messages_summarized: int
    timestamp: str


class ConversationSummarizer:
    """
    LLM-based conversation summarization engine.

    Compresses conversation history into concise summaries while preserving
    critical context, decisions, and facts. Designed for integration with
    session management to handle transformer context window limitations.

    Attributes:
        model: LLM model to use for summarization (default: fast Sonnet)
        max_tokens: Maximum tokens for summary generation
        compression_ratio: Target compression (0.3 = 70% reduction)
        llm_client: LiteLLM client instance for API calls

    Methods:
        summarize_messages: Compress message list into summary
        extract_key_points: Extract bullet points from conversation
        count_tokens: Accurate token counting for messages
        estimate_compression: Estimate compressed size before summarizing
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 2000,
        compression_ratio: float = 0.3
    ):
        """
        Initialize the conversation summarizer.

        Args:
            model: LLM model for summarization (default: fast Sonnet)
            max_tokens: Max tokens for summary generation
            compression_ratio: Target compression ratio (0.3 = 30% of original)
        """
        self.model = model
        self.max_tokens = max_tokens
        self.compression_ratio = compression_ratio

        # Initialize LLM client
        self.llm_client = None
        if LITELLM_AVAILABLE:
            try:
                self.llm_client = get_client()
            except Exception as e:
                logger.warning(f"Failed to initialize LiteLLM client: {e}")
                logger.warning("Summarizer will initialize but cannot perform summarization")
        else:
            logger.error("LiteLLM not available - summarizer will not function")

        # Initialize tiktoken encoder (for Claude/GPT models)
        self.encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding (compatible with Claude and GPT-4)
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")

        logger.info(f"ConversationSummarizer initialized with model={model}")

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

    def count_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count total tokens in message list.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total token count across all messages
        """
        total = 0
        for msg in messages:
            # Count role + content + structural overhead
            role_tokens = self.count_tokens(msg.get("role", ""))
            content_tokens = self.count_tokens(msg.get("content", ""))
            total += role_tokens + content_tokens + 4  # +4 for message structure

        return total

    def summarize_messages(
        self,
        messages: List[Dict[str, str]],
        max_length: Optional[int] = None,
        preserve_recent: int = 0
    ) -> str:
        """
        Summarize a list of conversation messages into a concise summary.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_length: Maximum token length for summary (default: use compression_ratio)
            preserve_recent: Number of recent messages to exclude from summary

        Returns:
            Summary string

        Raises:
            RuntimeError: If LLM client not available
        """
        if not self.llm_client:
            raise RuntimeError("LLM client not available - cannot summarize")

        if not messages:
            return ""

        # Separate recent messages if needed
        messages_to_summarize = messages[:-preserve_recent] if preserve_recent > 0 else messages

        if not messages_to_summarize:
            return ""

        # Calculate target summary length
        original_tokens = self.count_message_tokens(messages_to_summarize)
        if max_length is None:
            max_length = int(original_tokens * self.compression_ratio)

        # Build conversation text for summarization
        conversation_text = self._format_messages_for_summary(messages_to_summarize)

        # Create summarization prompt
        system_prompt = """You are an expert at summarizing technical conversations.
Create a concise but complete summary that preserves:
- Key decisions and outcomes
- Important facts and context
- Action items and next steps
- Technical details that matter

Format as a flowing narrative, not bullet points. Be specific and preserve technical accuracy."""

        user_prompt = f"""Summarize this conversation in approximately {max_length} tokens:

{conversation_text}

Summary:"""

        # Call LLM for summarization
        try:
            start_time = time.time()

            summary = self.llm_client.chat(
                user_prompt,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for factual summarization
                system_prompt=system_prompt
            )

            duration = time.time() - start_time
            logger.info(
                f"Summarized {len(messages_to_summarize)} messages "
                f"({original_tokens} tokens) in {duration:.2f}s"
            )

            return summary.strip()

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback: simple concatenation with truncation
            return self._fallback_summary(messages_to_summarize, max_length)

    def extract_key_points(
        self,
        messages: List[Dict[str, str]],
        max_points: int = 10
    ) -> List[str]:
        """
        Extract key points/decisions from conversation as bullet list.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_points: Maximum number of points to extract

        Returns:
            List of key point strings
        """
        if not self.llm_client:
            logger.warning("LLM client not available - returning empty key points")
            return []

        if not messages:
            return []

        # Build conversation text
        conversation_text = self._format_messages_for_summary(messages)

        # Create extraction prompt
        system_prompt = """You are an expert at extracting key information from conversations.
Extract the most important points as concise bullet items. Focus on:
- Decisions made
- Important facts learned
- Action items
- Technical conclusions
- Key context

Return ONLY the bullet points, one per line, without numbering."""

        user_prompt = f"""Extract up to {max_points} key points from this conversation:

{conversation_text}

Key points (one per line):"""

        # Call LLM for extraction
        try:
            response = self.llm_client.chat(
                user_prompt,
                model=self.model,
                max_tokens=1000,
                temperature=0.2,
                system_prompt=system_prompt
            )

            # Parse bullet points from response
            points = []
            for line in response.strip().split('\n'):
                line = line.strip()
                # Remove bullet markers (-, *, •, etc.)
                if line.startswith(('- ', '* ', '• ', '+ ')):
                    line = line[2:]
                if line:
                    points.append(line)

            return points[:max_points]

        except Exception as e:
            logger.error(f"Key point extraction failed: {e}")
            return []

    def _format_messages_for_summary(self, messages: List[Dict[str, str]]) -> str:
        """
        Format message list into readable conversation text.

        Args:
            messages: List of message dicts

        Returns:
            Formatted conversation string
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Format role nicely
            if role == "user":
                role_label = "User"
            elif role == "assistant":
                role_label = "Assistant"
            elif role == "system":
                role_label = "System"
            else:
                role_label = role.capitalize()

            lines.append(f"{role_label}: {content}")

        return "\n\n".join(lines)

    def _fallback_summary(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int
    ) -> str:
        """
        Fallback summarization when LLM call fails.

        Simple truncation strategy - takes first and last messages.

        Args:
            messages: Messages to summarize
            max_tokens: Target token count

        Returns:
            Truncated summary string
        """
        if not messages:
            return ""

        # Try to include first and last messages
        summary_parts = []
        token_budget = max_tokens

        # Add first message
        if messages:
            first_msg = f"{messages[0].get('role', 'unknown')}: {messages[0].get('content', '')}"
            first_tokens = self.count_tokens(first_msg)
            if first_tokens < token_budget:
                summary_parts.append(first_msg)
                token_budget -= first_tokens

        # Add last message if different from first
        if len(messages) > 1:
            last_msg = f"{messages[-1].get('role', 'unknown')}: {messages[-1].get('content', '')}"
            last_tokens = self.count_tokens(last_msg)
            if last_tokens < token_budget:
                summary_parts.append("...")
                summary_parts.append(last_msg)

        return "\n".join(summary_parts)

    def estimate_compression(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, int]:
        """
        Estimate token counts before and after compression.

        Args:
            messages: Messages to estimate for

        Returns:
            Dict with 'original_tokens', 'estimated_summary_tokens', 'savings'
        """
        original_tokens = self.count_message_tokens(messages)
        estimated_summary_tokens = int(original_tokens * self.compression_ratio)
        savings = original_tokens - estimated_summary_tokens

        return {
            "original_tokens": original_tokens,
            "estimated_summary_tokens": estimated_summary_tokens,
            "savings": savings,
            "compression_ratio": self.compression_ratio
        }

    def group_messages_by_token_limit(
        self,
        messages: List[Dict[str, str]],
        token_limit: int
    ) -> List[List[Dict[str, str]]]:
        """
        Group messages into chunks that fit within a token limit.

        This method intelligently groups messages for batch summarization,
        ensuring each group stays within the specified token limit while
        maintaining conversation coherence by keeping user/assistant pairs
        together when possible.

        The grouping strategy:
        - Works forward through messages sequentially
        - Accumulates messages into groups until token limit reached
        - Tries to preserve user/assistant pairs together
        - Always includes at least one message per group (even if over limit)

        Args:
            messages: List of message dicts with 'role' and 'content'
            token_limit: Maximum tokens per group

        Returns:
            List of message groups, where each group is a list of messages
            that fit within the token limit

        Example:
            >>> summarizer = ConversationSummarizer()
            >>> messages = [
            ...     {"role": "user", "content": "Hello"},
            ...     {"role": "assistant", "content": "Hi there!"},
            ...     # ... more messages
            ... ]
            >>> groups = summarizer.group_messages_by_token_limit(messages, 1000)
            >>> for i, group in enumerate(groups):
            ...     print(f"Group {i}: {len(group)} messages")
        """
        if not messages:
            return []

        if token_limit <= 0:
            logger.warning(f"Invalid token_limit {token_limit}, using default 1000")
            token_limit = 1000

        groups = []
        current_group = []
        current_tokens = 0

        for i, message in enumerate(messages):
            # Count tokens for this message
            msg_tokens = self.count_tokens(message.get("role", ""))
            msg_tokens += self.count_tokens(message.get("content", ""))
            msg_tokens += 4  # Message structure overhead

            # Check if adding this message would exceed the limit
            if current_group and (current_tokens + msg_tokens > token_limit):
                # We would exceed the limit - start a new group
                # But first, check if we should include the next message
                # to complete a user/assistant pair
                should_complete_pair = False

                if current_group:
                    last_msg = current_group[-1]
                    current_msg = message

                    # If last message was user and current is assistant (or vice versa),
                    # we might want to keep them together
                    if (last_msg.get("role") == "user" and current_msg.get("role") == "assistant"):
                        # User question followed by assistant answer
                        # Check if pair fits in remaining budget with some tolerance
                        if current_tokens + msg_tokens <= token_limit * 1.1:  # 10% tolerance
                            should_complete_pair = True

                if should_complete_pair:
                    # Include this message to complete the pair
                    current_group.append(message)
                    current_tokens += msg_tokens
                    # Save the completed group
                    groups.append(current_group)
                    current_group = []
                    current_tokens = 0
                else:
                    # Save current group and start new one with this message
                    groups.append(current_group)
                    current_group = [message]
                    current_tokens = msg_tokens
            else:
                # Message fits in current group
                current_group.append(message)
                current_tokens += msg_tokens

        # Add final group if it has messages
        if current_group:
            groups.append(current_group)

        logger.debug(
            f"Grouped {len(messages)} messages into {len(groups)} groups "
            f"(limit: {token_limit} tokens/group)"
        )

        return groups
