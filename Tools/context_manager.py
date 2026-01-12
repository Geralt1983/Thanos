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

THREAD SAFETY CONSIDERATIONS:
-----------------------------
This module is designed for safe concurrent use with the following guarantees:

1. Encoder Immutability:
   - tiktoken encoders are immutable and stateless after initialization
   - Multiple threads can safely call encoder.encode() concurrently
   - No locks are needed when using the cached encoder instance

2. Lazy Initialization Race Condition:
   - In rare cases, concurrent first-time access may initialize multiple encoders
   - This is harmless: one instance becomes cached, others are garbage collected
   - The slight overhead (2-3x initialization) is acceptable vs. lock contention
   - After initialization, all threads share the same cached instance

3. ContextManager Instances:
   - Each ContextManager instance is independent and stores its own state
   - Instances can be safely created and used in different threads
   - The shared encoder is read-only and never modified

4. GIL Protection:
   - Python's Global Interpreter Lock (GIL) prevents race conditions in the
     module-level _CACHED_ENCODER assignment
   - No additional synchronization primitives are required

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

    Thread Safety:
        This function is thread-safe with the following considerations:

        - Check-then-set pattern: The function uses a non-atomic check-then-set
          pattern (if _CACHED_ENCODER is not None). In rare concurrent first-calls,
          multiple threads may pass the None check simultaneously.

        - Race condition is benign: If multiple threads initialize encoders
          concurrently, Python's GIL ensures the final assignment is atomic.
          One encoder becomes cached, others are garbage collected. This slight
          initialization overhead is acceptable vs. lock contention costs.

        - Read-only after init: Once initialized, all threads safely read the
          same cached encoder. tiktoken encoders are immutable and thread-safe
          for concurrent encode() calls.

        - No locks needed: The performance benefit of lock-free access outweighs
          the negligible cost of potential duplicate initialization on first use.

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

    # Initialize encoder on first use with error handling
    try:
        _CACHED_ENCODER = tiktoken.get_encoding("cl100k_base")
        return _CACHED_ENCODER
    except Exception as e:
        # If initialization fails (network issues, corrupted cache, etc.),
        # return None to allow fallback to heuristic token estimation
        return None


class ContextManager:
    """
    Manages conversation context and token counting for Claude API interactions.

    This class provides methods for estimating token counts, trimming conversation
    history to fit within context windows, and reporting usage statistics.

    Attributes:
        model (str): The Claude model identifier being used
        max_tokens (int): Maximum context window size for the model
        OUTPUT_RESERVE (int): Tokens reserved for model output
        available_tokens (int): Tokens available for input (max - reserve)
        encoding (Optional[Any]): Cached tiktoken encoder instance

    Example:
        cm = ContextManager(model="claude-opus-4-5-20251101")
        tokens = cm.estimate_tokens("Hello world")
        trimmed, was_trimmed = cm.trim_history(history, system_prompt, new_message)
    """

    # Make MODEL_LIMITS accessible at class level for tests
    MODEL_LIMITS = MODEL_LIMITS

    def __init__(self, model: str = "claude-opus-4-5-20251101"):
        """
        Initialize ContextManager for a specific Claude model.

        Args:
            model (str): Claude model identifier. Defaults to "claude-opus-4-5-20251101".
                        If model is not in MODEL_LIMITS, uses default limit of 100k tokens.

        The initialization:
        1. Sets the model name
        2. Looks up max_tokens from MODEL_LIMITS (or uses default)
        3. Sets OUTPUT_RESERVE constant
        4. Calculates available_tokens for input
        5. Gets the cached tiktoken encoder instance
        """
        self.model = model

        # Look up token limit for this model, with fallback to default
        self.max_tokens = MODEL_LIMITS.get(model, MODEL_LIMITS["default"])

        # Set output reserve constant
        self.OUTPUT_RESERVE = OUTPUT_RESERVE

        # Calculate available tokens for input (context window - output reserve)
        self.available_tokens = self.max_tokens - self.OUTPUT_RESERVE

        # Get the cached encoder instance (may be None if tiktoken unavailable)
        self.encoding = _get_cached_encoder()

    def estimate_tokens(self, text: Optional[str]) -> int:
        """
        Estimate the number of tokens in a text string.

        Uses tiktoken encoder if available, otherwise falls back to heuristic
        estimation (length / 3.5). This provides accurate token counts for
        context management and trimming decisions.

        Args:
            text (Optional[str]): The text to estimate tokens for.
                                 Can be None or empty string.

        Returns:
            int: Estimated number of tokens in the text.
                 Returns 0 for None or empty strings.

        Fallback Behavior:
            - If tiktoken is unavailable: uses heuristic (len/3.5)
            - If encoding fails: uses heuristic (len/3.5)
            - The heuristic assumes ~3.5 characters per token on average

        Example:
            cm = ContextManager()
            tokens = cm.estimate_tokens("Hello world")  # Returns ~3 tokens
        """
        # Handle None and empty strings
        if not text:
            return 0

        # Try to use tiktoken encoder if available
        if self.encoding is not None:
            try:
                # Use tiktoken for accurate token counting
                encoded = self.encoding.encode(text)
                return len(encoded)
            except Exception:
                # If encoding fails, fall through to heuristic estimation
                pass

        # Fallback: heuristic estimation (characters / 3.5)
        # This provides a reasonable approximation when tiktoken is unavailable
        return int(len(text) / 3.5)
