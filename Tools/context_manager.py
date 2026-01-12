#!/usr/bin/env python3
"""
ContextManager - Manages context window usage and provides reporting.

This is a minimal stub implementation to support interactive mode.
Full implementation would track actual context window usage.
"""

from typing import Dict, List


class ContextManager:
    """Manages context window usage tracking."""

    def __init__(self, max_tokens: int = 200000):
        """
        Initialize context manager.

        Args:
            max_tokens: Maximum context window size (default: 200K for Claude)
        """
        self.max_tokens = max_tokens

    def get_usage_report(self, history: List[Dict], system_prompt: str) -> Dict:
        """
        Get context window usage report.

        Args:
            history: List of message dicts
            system_prompt: System prompt text

        Returns:
            Dictionary with usage information
        """
        # Simple token estimation (roughly 4 chars per token)
        system_tokens = len(system_prompt) // 4
        history_tokens = sum(len(msg.get("content", "")) for msg in history) // 4
        total_used = system_tokens + history_tokens

        return {
            "system_tokens": system_tokens,
            "history_tokens": history_tokens,
            "messages_in_context": len(history),
            "total_used": total_used,
            "available": self.max_tokens,
            "usage_percent": (total_used / self.max_tokens) * 100 if self.max_tokens > 0 else 0,
        }
