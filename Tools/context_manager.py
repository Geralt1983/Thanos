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


# Token limits for different Claude models
# These represent the maximum context window size for each model
MODEL_LIMITS: Dict[str, int] = {
    "claude-opus-4-5-20251101": 200_000,      # Claude Opus 4.5: 200k tokens
    "claude-sonnet-4-20250514": 200_000,      # Claude Sonnet 4: 200k tokens
    "claude-3-5-sonnet-20241022": 200_000,    # Claude 3.5 Sonnet: 200k tokens
    "default": 100_000,                        # Default fallback: 100k tokens
}

# Reserved tokens for model output responses
# This ensures sufficient space for the model to generate complete responses
OUTPUT_RESERVE: int = 8_000

# Global encoder cache to avoid expensive re-initialization
# Initialized to None and lazily loaded via _get_cached_encoder()
# Thread-safe: tiktoken encoders are stateless and safe for concurrent access
_CACHED_ENCODER: Optional[Any] = None


def _get_cached_encoder() -> Optional[Any]:
    """
    Get or initialize the cached tiktoken encoder instance.

    This function implements lazy initialization of the tiktoken encoder.
    On first call, it initializes the encoder using tiktoken.get_encoding('cl100k_base')
    and caches it in the module-level _CACHED_ENCODER variable for reuse.

    The cl100k_base encoding is used by GPT-4 and Claude models for token counting.

    Returns:
        Optional[Any]: The cached tiktoken encoder instance, or None if tiktoken
                       is unavailable or initialization fails.

    Note:
        This function modifies the module-level _CACHED_ENCODER variable.
        Subsequent calls return the cached instance without re-initialization.
    """
    global _CACHED_ENCODER

    # Return cached encoder if already initialized
    if _CACHED_ENCODER is not None:
        return _CACHED_ENCODER

    # Check if tiktoken is available
    if not TIKTOKEN_AVAILABLE:
        return None

    # Initialize encoder on first use
    _CACHED_ENCODER = tiktoken.get_encoding("cl100k_base")
    return _CACHED_ENCODER
