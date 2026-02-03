"""
LiteLLM Package for Thanos Personal Assistant Framework

Unified multi-model API client supporting 100+ AI models including Claude, GPT-4,
Gemini, and more. This package provides intelligent model routing, cost optimization,
usage tracking, and response caching in a modular, production-ready architecture.

Package Structure:
    models.py: Shared data models (ModelResponse dataclass)
    usage_tracker.py: Token usage tracking and cost accounting with persistent storage
    complexity_analyzer.py: Intelligent prompt analysis for automatic model routing
    response_cache.py: TTL-based response caching to reduce redundant API calls
    client.py: Main LiteLLMClient orchestrating all components

Key Features:
    - Unified API for 100+ models via LiteLLM library
    - Automatic model selection based on prompt complexity (saves costs)
    - Response caching with TTL (reduces redundant API calls)
    - Comprehensive usage and cost tracking (per model, provider, and day)
    - Fallback chains for reliability
    - Streaming and non-streaming support
    - Configurable via JSON or environment variables

Quick Start:
    from Tools.litellm import get_client

    # Get singleton client instance
    client = get_client()

    # Simple chat (auto-routes to appropriate model based on complexity)
    response = client.chat("What is the capital of France?")
    print(response)  # "Paris"

Basic Usage:
    from Tools.litellm import get_client

    client = get_client()

    # Auto-route based on complexity analysis
    response = client.chat("Explain quantum computing in detail")
    # Automatically uses anthropic/claude-opus-4-5 for complex queries

    # Simple queries use cheaper models
    response = client.chat("Hi there!")
    # Automatically uses anthropic/claude-3-5-haiku-20241022 for simple queries

    # Force specific model
    response = client.chat(
        "Your prompt",
        model="anthropic/claude-sonnet-4-5",
        max_tokens=2048,
        temperature=0.7
    )

    # Streaming responses
    for chunk in client.chat_stream("Tell me a story"):
        print(chunk, end="", flush=True)

Advanced Usage:
    from Tools.litellm import LiteLLMClient

    # Initialize with custom config
    client = LiteLLMClient(config_path="custom/api.json")

    # With conversation history
    history = [
        {"role": "user", "content": "What is Python?"},
        {"role": "assistant", "content": "Python is a programming language."}
    ]
    response = client.chat("Tell me more", history=history)

    # Analyze complexity without making API call
    analysis = client.analyze_complexity("Complex technical question...")
    print(f"Complexity score: {analysis['complexity_score']}")
    print(f"Recommended model: {analysis['selected_model']}")

    # Get usage statistics
    summary = client.get_usage_summary(days=30)
    print(f"30-day cost: ${summary['total_cost_usd']:.2f}")
    print(f"Projected monthly: ${summary['projected_monthly_cost']:.2f}")

    today = client.get_today_usage()
    print(f"Today: {today['calls']} calls, ${today['cost']:.4f}")

Direct Component Usage:
    from Tools.litellm import (
        UsageTracker,
        ComplexityAnalyzer,
        ResponseCache,
        ModelResponse
    )

    # Use components independently if needed
    tracker = UsageTracker("State/usage.json", pricing={...})
    analyzer = ComplexityAnalyzer(config={...})
    cache = ResponseCache("Memory/cache/", ttl_seconds=3600)

Environment Variables:
    The package expects API keys in environment variables:
    - ANTHROPIC_API_KEY: For Claude models
    - OPENAI_API_KEY: For GPT models
    - GEMINI_API_KEY: For Google Gemini models

Configuration:
    By default, loads config from config/api.json with settings for:
    - Model routing rules (complexity thresholds)
    - Fallback chains (reliability)
    - Usage tracking (storage paths, pricing)
    - Caching (TTL, size limits)
    - Default parameters (max_tokens, temperature)

Availability Checks:
    from Tools.litellm import LITELLM_AVAILABLE, ANTHROPIC_AVAILABLE

    if LITELLM_AVAILABLE:
        print("LiteLLM library is installed - full functionality")
    elif ANTHROPIC_AVAILABLE:
        print("Fallback to direct Anthropic API - limited functionality")

Exports:
    Core Client:
        - LiteLLMClient: Main client class
        - get_client(): Get/create singleton instance
        - init_client(): Force reinitialize with new config

    Data Models:
        - ModelResponse: Standardized response dataclass

    Components:
        - UsageTracker: Token and cost tracking
        - ComplexityAnalyzer: Prompt complexity analysis
        - ResponseCache: Response caching

    Constants:
        - LITELLM_AVAILABLE: True if litellm installed
        - ANTHROPIC_AVAILABLE: True if anthropic installed

    Module References:
        - anthropic: Anthropic module for test mocking

Cost Optimization:
    The automatic routing can reduce costs by 80%+ by intelligently selecting
    models based on query complexity:
    - Simple queries → Haiku (~$0.0001 per request)
    - Standard queries → Sonnet (~$0.003 per request)
    - Complex queries → Opus (~$0.015 per request)

Performance:
    - Cache hits: <1ms (instant response)
    - API calls: 500-3000ms (depends on model)
    - Streaming: First token in ~200-500ms
    - Complexity analysis: <10ms overhead

Thread Safety:
    The singleton client instance (via get_client()) is thread-safe for reads.
    For multi-threaded writes, create separate instances per thread using
    LiteLLMClient() directly.

See Also:
    - client.py: Detailed API documentation
    - config/api.json: Configuration file structure
    - State/usage.json: Usage tracking data format
"""

# Import all classes and functions from submodules
from .models import ModelResponse
from .usage_tracker import UsageTracker
from .complexity_analyzer import ComplexityAnalyzer
from .response_cache import ResponseCache
from .client import (
    LiteLLMClient,
    get_client,
    init_client,
    LITELLM_AVAILABLE,
    ANTHROPIC_AVAILABLE,
)

# Import anthropic module for test mocking compatibility
try:
    import anthropic
except ImportError:
    anthropic = None

# Export all public classes and functions
__all__ = [
    # Core client
    "LiteLLMClient",
    "get_client",
    "init_client",
    # Data models
    "ModelResponse",
    # Component classes
    "UsageTracker",
    "ComplexityAnalyzer",
    "ResponseCache",
    # Constants for availability checking
    "LITELLM_AVAILABLE",
    "ANTHROPIC_AVAILABLE",
    # Module reference for test mocking
    "anthropic",
]
