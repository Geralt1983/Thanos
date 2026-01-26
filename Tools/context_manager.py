#!/usr/bin/env python3
"""
ContextManager - Manages context window usage and provides reporting.

Provides accurate token counting using tiktoken and determines when
conversation history should be summarized to stay within context limits.

Key Features:
    - Accurate token counting via tiktoken
    - Context window usage tracking
    - Summarization trigger logic
    - Fallback estimation when tiktoken unavailable

Key Classes:
    ContextManager: Main interface for context window management

Usage:
    from Tools.context_manager import ContextManager

    # Initialize context manager
    cm = ContextManager(max_tokens=200000)

    # Get usage report
    report = cm.get_usage_report(history, system_prompt)
    print(f"Usage: {report['usage_percent']:.1f}%")

    # Check if summarization needed
    if cm.should_summarize(history, system_prompt):
        print("Time to summarize!")
"""

import logging
from typing import Dict, List

# Configure logger for this module
logger = logging.getLogger(__name__)

# Tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    logger.warning("tiktoken not available - using fallback token counting")
    TIKTOKEN_AVAILABLE = False

# Summarization threshold (trigger at 70% of max tokens)
SUMMARIZATION_THRESHOLD = 0.70


class ContextManager:
    """
    Manages context window usage tracking with accurate token counting.

    Tracks context window usage and determines when conversation history
    should be summarized to prevent hitting token limits.

    Attributes:
        max_tokens: Maximum context window size
        encoder: Tiktoken encoder for accurate token counting
        summarization_threshold: Percentage at which to trigger summarization

    Methods:
        count_tokens: Count tokens in text using tiktoken
        get_usage_report: Get detailed context window usage statistics
        should_summarize: Check if summarization should be triggered
    """

    def __init__(self, max_tokens: int = 200000):
        """
        Initialize context manager.

        Args:
            max_tokens: Maximum context window size (default: 200K for Claude)
        """
        self.max_tokens = max_tokens
        self.summarization_threshold = SUMMARIZATION_THRESHOLD

        # Initialize tiktoken encoder (for Claude/GPT models)
        self.encoder = None
        if TIKTOKEN_AVAILABLE:
            try:
                # Use cl100k_base encoding (compatible with Claude and GPT-4)
                self.encoder = tiktoken.get_encoding("cl100k_base")
                logger.info("ContextManager initialized with tiktoken encoder")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken encoder: {e}")
        else:
            logger.warning("ContextManager initialized without tiktoken - using fallback estimation")

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

    def get_usage_report(self, history: List[Dict], system_prompt: str) -> Dict:
        """
        Get context window usage report with accurate token counting.

        Args:
            history: List of message dicts
            system_prompt: System prompt text

        Returns:
            Dictionary with usage information including:
                - system_tokens: Tokens used by system prompt
                - history_tokens: Tokens used by conversation history
                - messages_in_context: Number of messages in history
                - total_used: Total tokens used
                - available: Maximum tokens available
                - usage_percent: Percentage of context window used
                - should_summarize: Boolean indicating if summarization recommended
        """
        # Count tokens accurately using tiktoken
        system_tokens = self.count_tokens(system_prompt)
        history_tokens = sum(self.count_tokens(msg.get("content", "")) for msg in history)
        total_used = system_tokens + history_tokens

        usage_percent = (total_used / self.max_tokens) * 100 if self.max_tokens > 0 else 0

        return {
            "system_tokens": system_tokens,
            "history_tokens": history_tokens,
            "messages_in_context": len(history),
            "total_used": total_used,
            "available": self.max_tokens,
            "usage_percent": usage_percent,
            "should_summarize": usage_percent >= (self.summarization_threshold * 100),
        }

    def should_summarize(self, history: List[Dict], system_prompt: str = "") -> bool:
        """
        Check if conversation history should be summarized.

        Triggers summarization when context window usage exceeds the
        configured threshold (default: 70%). This prevents hitting
        hard token limits while leaving room for continued conversation.

        Args:
            history: List of message dicts
            system_prompt: System prompt text (optional, default: "")

        Returns:
            True if summarization should be triggered, False otherwise
        """
        # Calculate current usage
        system_tokens = self.count_tokens(system_prompt) if system_prompt else 0
        history_tokens = sum(self.count_tokens(msg.get("content", "")) for msg in history)
        total_used = system_tokens + history_tokens

        usage_ratio = total_used / self.max_tokens if self.max_tokens > 0 else 0

        # Trigger when usage exceeds threshold
        should_trigger = usage_ratio >= self.summarization_threshold

        if should_trigger:
            logger.info(
                f"Summarization threshold reached: {usage_ratio:.1%} "
                f"({total_used:,} / {self.max_tokens:,} tokens)"
            )

        return should_trigger
