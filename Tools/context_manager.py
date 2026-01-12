"""
Context Manager for Thanos conversation history and token counting.

This module provides context window management for Claude API interactions,
including token estimation, message history trimming, and usage reporting.

GLOBAL ENCODER CACHING:
----------------------
The tiktoken encoder is expensive to initialize (~100ms per instance).
Since encoders are stateless and thread-safe, we cache a single encoder
instance at module level for reuse across all ContextManager instances.

Benefits:
- Subsequent ContextManager instantiations are ~100ms faster
- Reduced memory overhead from multiple encoder instances
- Thread-safe: tiktoken encoders can be safely shared across contexts

The cached encoder is initialized lazily on first use via _get_cached_encoder()
and reused for the lifetime of the Python process. If initialization fails,
the system gracefully falls back to heuristic token estimation (len/3.5).

Usage:
    from Tools.context_manager import ContextManager

    # Create manager for a specific model
    cm = ContextManager(model="claude-opus-4-5-20251101")

    # Estimate tokens in text
    tokens = cm.estimate_tokens("Your text here")

    # Trim conversation history to fit context window
    trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)

    # Get usage statistics
    report = cm.get_usage_report(history, system_prompt)
"""

from typing import Any, Dict, List, Optional, Tuple

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
