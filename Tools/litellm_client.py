#!/usr/bin/env python3
"""
LiteLLM Client for Thanos Personal Assistant Framework
Unified multi-model API client supporting Claude, GPT, Gemini, and 100+ models.

This module is a backward-compatibility wrapper. All functionality has been
moved to the Tools.litellm package for better organization and maintainability.

Usage:
    from Tools.litellm_client import LiteLLMClient, get_client

    # Initialize with config
    client = get_client()

    # Auto-route based on complexity
    response = client.chat("Complex analysis question")

    # Force specific model
    response = client.chat("Simple task", model="claude-3-5-haiku-20241022")

    # Streaming
    for chunk in client.chat_stream("Your prompt"):
        print(chunk, end="", flush=True)

New usage (recommended):
    from Tools.litellm import LiteLLMClient, get_client
"""

# Import all classes and functions from the new package structure
from Tools.litellm import (
    # Core client
    LiteLLMClient,
    get_client,
    init_client,
    # Data models
    ModelResponse,
    # Component classes
    UsageTracker,
    ComplexityAnalyzer,
    ResponseCache,
    # Constants
    LITELLM_AVAILABLE,
    ANTHROPIC_AVAILABLE,
    # Module references
    anthropic,
)

# Re-export everything for backward compatibility
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
    # Constants
    "LITELLM_AVAILABLE",
    "ANTHROPIC_AVAILABLE",
    # Module references
    "anthropic",
]

# Convenience alias for backward compatibility
litellm_client = None


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("Testing LiteLLM Client...")
        try:
            client = LiteLLMClient()

            # Test complexity analysis
            analysis = client.analyze_complexity("What's 2+2?")
            print(f"Simple query complexity: {analysis}")

            analysis = client.analyze_complexity(
                "Analyze the architecture of this system and provide a comprehensive redesign strategy."
            )
            print(f"Complex query complexity: {analysis}")

            # Test actual call
            response = client.chat("Say 'Hello from Thanos LiteLLM!' and nothing else.")
            print(f"Response: {response}")
            print(f"\nToday's usage: {client.get_today_usage()}")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    elif len(sys.argv) > 1 and sys.argv[1] == "usage":
        try:
            client = LiteLLMClient()
            summary = client.get_usage_summary(30)
            print("LiteLLM Usage (Last 30 Days)")
            print(f"   Total Tokens: {summary.get('total_tokens', 0):,}")
            print(f"   Total Cost: ${summary.get('total_cost_usd', 0):.2f}")
            print(f"   Total Calls: {summary.get('total_calls', 0)}")
            print(f"   Projected Monthly: ${summary.get('projected_monthly_cost', 0):.2f}")

            if summary.get("model_breakdown"):
                print("\nBy Model:")
                for model, stats in summary["model_breakdown"].items():
                    print(f"   {model}: {stats['calls']} calls, ${stats['cost']:.2f}")

        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif len(sys.argv) > 1 and sys.argv[1] == "models":
        try:
            client = LiteLLMClient()
            print("Available Models:")
            for model in client.list_available_models():
                print(f"   - {model}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    else:
        print("Usage: python litellm_client.py [test|usage|models]")
