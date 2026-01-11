"""
LiteLLM Package for Thanos Personal Assistant Framework

Modular multi-model API client supporting Claude, GPT, Gemini, and 100+ models.
This package provides separate modules for different concerns:
- models: Shared data classes and models
- usage_tracker: Token usage tracking and cost accounting
- complexity_analyzer: Automatic prompt complexity analysis for model routing
- response_cache: Response caching to reduce API calls
- client: Main LiteLLM client for API communication

Usage:
    from Tools.litellm import LiteLLMClient, get_client

    # Initialize with config
    client = get_client()

    # Auto-route based on complexity
    response = client.chat("Complex analysis question")

    # Force specific model
    response = client.chat("Simple task", model="claude-3-5-haiku-20241022")

    # Streaming
    for chunk in client.chat_stream("Your prompt"):
        print(chunk, end="", flush=True)

"""

# Import all classes and functions from submodules
from .models import ModelResponse
from .usage_tracker import UsageTracker
from .complexity_analyzer import ComplexityAnalyzer
from .response_cache import ResponseCache
from .client import LiteLLMClient, get_client, init_client

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
]
