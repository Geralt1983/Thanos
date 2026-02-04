#!/usr/bin/env python3
"""
Main LiteLLM client for unified multi-model API access.

This module provides the core LiteLLMClient class that orchestrates API calls
across 100+ model providers (Anthropic Claude, OpenAI GPT, Google Gemini, etc.)
with intelligent features including automatic model routing, response caching,
usage tracking, and fallback handling.

Key Features:
    - Unified API for 100+ models via LiteLLM
    - Automatic model selection based on complexity analysis
    - Response caching with TTL for cost reduction
    - Comprehensive usage and cost tracking
    - Fallback chains for reliability
    - Streaming and non-streaming support
    - Configurable via JSON file or environment variables

Key Classes:
    LiteLLMClient: Main client for API communication

Key Functions:
    get_client(): Get or create singleton client instance
    init_client(): Force re-initialize client with new config

Usage - Basic:
    from Tools.litellm import get_client

    client = get_client()

    # Simple chat (auto-routes to appropriate model)
    response = client.chat("What is the capital of France?")
    print(response)  # "Paris"

Usage - Advanced:
    from Tools.litellm import LiteLLMClient

    # Initialize with custom config
    client = LiteLLMClient(config_path="config/api.json")

    # Force specific model
    response = client.chat(
        "Analyze this complex system architecture...",
        model="anthropic/claude-opus-4-5",
        max_tokens=8000,
        temperature=0.7,
        system_prompt="You are a senior architect."
    )

    # Streaming responses
    for chunk in client.chat_stream("Tell me a story"):
        print(chunk, end="", flush=True)

    # With conversation history
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    response = client.chat("How are you?", history=history)

    # Analyze complexity without making a call
    analysis = client.analyze_complexity("Complex technical question...")
    print(f"Complexity: {analysis['complexity_score']}")
    print(f"Recommended model: {analysis['selected_model']}")

    # Get usage statistics
    summary = client.get_usage_summary(days=30)
    print(f"Monthly cost: ${summary['projected_monthly_cost']:.2f}")

    today = client.get_today_usage()
    print(f"Today: {today['calls']} calls, ${today['cost']:.4f}")

Configuration:
    The client loads configuration from config/api.json (or custom path):

    {
        "litellm": {
            "default_model": "anthropic/claude-opus-4-5",
            "fallback_chain": ["anthropic/claude-opus-4-5", "anthropic/claude-sonnet-4-5"],
            "timeout": 600,
            "max_retries": 3,
            "providers": {
                "anthropic": {
                    "api_key_env": "ANTHROPIC_API_KEY",
                    "models": {...}
                }
            }
        },
        "model_routing": {
            "rules": {
                "complex": {"model": "anthropic/claude-opus-4-5", "min_complexity": 0.7},
                "standard": {"model": "anthropic/claude-sonnet-4-5", "min_complexity": 0.3},
                "simple": {"model": "anthropic/claude-3-5-haiku-20241022", "max_complexity": 0.3}
            }
        },
        "usage_tracking": {
            "enabled": true,
            "storage_path": "State/usage.json"
        },
        "caching": {
            "enabled": true,
            "ttl_seconds": 3600
        }
    }

Environment Variables:
    Required API keys (set based on providers used):
    - ANTHROPIC_API_KEY: For Claude models
    - OPENAI_API_KEY: For GPT models
    - GEMINI_API_KEY: For Gemini models

Architecture:
    The LiteLLMClient integrates several components:

    1. ComplexityAnalyzer: Analyzes prompts to determine optimal model tier
    2. ResponseCache: Caches responses to reduce redundant API calls
    3. UsageTracker: Tracks token usage and costs across all providers
    4. LiteLLM: Underlying library providing unified API access

    Request flow:
    1. Analyze complexity (if auto-routing)
    2. Select model based on tier
    3. Check cache for existing response
    4. Make API call (with fallback if needed)
    5. Track usage and costs
    6. Cache response for future use
    7. Return response to caller

Fallback Handling:
    If a model fails (rate limit, error, etc.), the client automatically
    tries the next model in the fallback chain. This ensures reliability
    even during API issues.

Error Handling:
    - RateLimitError: Automatic fallback to next model in chain
    - APIConnectionError: Retry with exponential backoff
    - APIError: Logged and raised with context

Availability Checks:
    - LITELLM_AVAILABLE: True if litellm library installed
    - ANTHROPIC_AVAILABLE: True if anthropic library installed (fallback)

Module Integration:
    This module is the main entry point for the LiteLLM package. It imports
    and coordinates UsageTracker, ComplexityAnalyzer, and ResponseCache to
    provide a complete, production-ready API client solution.

Performance:
    - Cache hits: <1ms response time
    - Typical API calls: 500-3000ms depending on model
    - Streaming: First token in ~200-500ms
    - Complexity analysis overhead: <10ms

Cost Optimization:
    The automatic routing feature can reduce costs by 80%+ by using cheaper
    models for simple tasks. Example:
    - Simple query on Haiku: $0.0001
    - Same query on Opus: $0.0015
    - Savings: 93% per simple query
"""

import os
import json
import time
import logging
import warnings
from pathlib import Path
from typing import Optional, Dict, Generator, Any, List, Union

# Configure logger for this module
logger = logging.getLogger(__name__)

# Import support classes from the package
from .usage_tracker import UsageTracker
from .complexity_analyzer import ComplexityAnalyzer
from .response_cache import ResponseCache
from .agent_router import AgentRouter

# LiteLLM import with fallback
try:
    import litellm
    from litellm import completion, acompletion
    from litellm.exceptions import (
        RateLimitError as LiteLLMRateLimitError,
        APIConnectionError as LiteLLMConnectionError,
        APIError as LiteLLMAPIError,
    )
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    LiteLLMRateLimitError = Exception
    LiteLLMConnectionError = Exception
    LiteLLMAPIError = Exception

# Fallback to direct Anthropic if LiteLLM unavailable
try:
    import anthropic
    from anthropic import RateLimitError, APIConnectionError, APIStatusError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

# Fallback to direct OpenAI if LiteLLM unavailable
try:
    import openai
    from openai import OpenAI, AsyncOpenAI, RateLimitError as OpenAIRateLimitError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None
    openai = None

try:
    from pydantic.warnings import PydanticSerializationUnexpectedValue
except Exception:
    PydanticSerializationUnexpectedValue = None

# Optional dotenv support for local .env loading
try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None

# ... (rest of imports)

# Export constants and classes
__all__ = [
    "LiteLLMClient",
    "get_client",
    "init_client",
    "LITELLM_AVAILABLE",
    "ANTHROPIC_AVAILABLE",
    "OPENAI_AVAILABLE",
]


class LiteLLMClient:
    """Unified multi-model client using LiteLLM with intelligent routing."""

    def __init__(self, config_path: str = None):
        # Find config
        if config_path is None:
            base_dir = Path(__file__).parent.parent.parent
            config_path = base_dir / "config" / "api.json"
        else:
            config_path = Path(config_path)

        self.base_dir = Path(__file__).parent.parent.parent
        # Load .env if present so fallback clients can pick up API keys.
        if load_dotenv:
            env_path = self.base_dir / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=False)
        self.config = self._load_config(config_path)
        self.allow_fallback_client = bool(
            self.config.get("litellm", {}).get("allow_fallback_client", False)
        )

        # Setup providers API keys
        self._setup_api_keys()

        # Initialize components
        self._init_usage_tracker()
        self._init_cache()
        self._init_complexity_analyzer()
        self._init_agent_router()
        self._init_fallback_client()
        self._init_openai_client()

        # Configure LiteLLM
        if LITELLM_AVAILABLE:
            litellm.drop_params = True  # Ignore unsupported params
            litellm.set_verbose = False

    def _load_config(self, config_path: Path) -> Dict:
        """Load configuration from JSON file."""
        if config_path.exists():
            return json.loads(config_path.read_text())

        # Default config
        return {
            "litellm": {
                "default_model": "anthropic/claude-sonnet-4-5",
                "fallback_chain": ["anthropic/claude-sonnet-4-5", "anthropic/claude-opus-4-5", "anthropic/claude-3-5-haiku-20241022"],
                "allow_fallback_client": False,
                "timeout": 600,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "model_routing": {
                "rules": {
                    "complex": {"model": "anthropic/claude-opus-4-5", "min_complexity": 0.7},
                    "standard": {"model": "anthropic/claude-sonnet-4-5", "min_complexity": 0.3},
                    "simple": {"model": "anthropic/claude-3-5-haiku-20241022", "max_complexity": 0.3}
                }
            },
            "usage_tracking": {"enabled": True, "storage_path": "State/usage.json"},
            "caching": {"enabled": True, "ttl_seconds": 3600, "storage_path": "Memory/cache/"},
            "defaults": {"max_tokens": 4096, "temperature": 1.0},
            "openai_responses": {
                "enabled": False,
                "model_prefixes": ["gpt-"],
                "tiers": {
                    "simple": {"verbosity": "low", "reasoning_effort": "low", "max_output_tokens": 512},
                    "standard": {"verbosity": "medium", "reasoning_effort": "medium", "max_output_tokens": 2048},
                    "complex": {"verbosity": "high", "reasoning_effort": "high", "max_output_tokens": 4096}
                }
            }
        }

    def _setup_api_keys(self):
        """Setup API keys from environment variables."""
        providers = self.config.get("litellm", {}).get("providers", {})

        for provider, pconfig in providers.items():
            key_env = pconfig.get("api_key_env")
            if key_env and os.environ.get(key_env):
                # LiteLLM uses standard env var names
                if provider == "anthropic":
                    os.environ["ANTHROPIC_API_KEY"] = os.environ.get(key_env, "")
                elif provider == "openai":
                    os.environ["OPENAI_API_KEY"] = os.environ.get(key_env, "")
                elif provider == "google":
                    os.environ["GEMINI_API_KEY"] = os.environ.get(key_env, "")

    def _init_usage_tracker(self):
        """Initialize usage tracker."""
        usage_config = self.config.get("usage_tracking", {})
        if usage_config.get("enabled", True):
            storage_path = usage_config.get("storage_path", "State/usage.json")
            if not Path(storage_path).is_absolute():
                storage_path = self.base_dir / storage_path
            pricing = usage_config.get("pricing", {})
            self.usage_tracker = UsageTracker(str(storage_path), pricing)
        else:
            self.usage_tracker = None

    def _init_cache(self):
        """Initialize response cache."""
        cache_config = self.config.get("caching", {})
        if cache_config.get("enabled", True):
            cache_path = cache_config.get("storage_path", "Memory/cache/")
            if not Path(cache_path).is_absolute():
                cache_path = self.base_dir / cache_path
            self.cache = ResponseCache(
                str(cache_path),
                cache_config.get("ttl_seconds", 3600),
                cache_config.get("max_cache_size_mb", 100)
            )
        else:
            self.cache = None

    def _init_complexity_analyzer(self):
        """Initialize complexity analyzer for model routing."""
        routing_config = self.config.get("model_routing", {})
        self.complexity_analyzer = ComplexityAnalyzer(routing_config)
        self.routing_rules = routing_config.get("rules", {})

    def _init_agent_router(self):
        """Initialize agent-based router for persona model selection."""
        self.agent_router = AgentRouter(self.config)

    def _init_fallback_client(self):
        """Initialize fallback clients if LiteLLM unavailable."""
        self.fallback_client_anthropic = None
        self.fallback_client_openai = None
        
        if not self.allow_fallback_client:
            return
            
        # Anthropic Fallback
        if not LITELLM_AVAILABLE and ANTHROPIC_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.fallback_client_anthropic = anthropic.Anthropic(api_key=api_key)

        # OpenAI Fallback
        if not LITELLM_AVAILABLE and OPENAI_AVAILABLE:
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.fallback_client_openai = openai.OpenAI(api_key=api_key)

    def _init_openai_client(self):
        """Initialize OpenAI client for tiered responses."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None

    def _get_routing_decision(self, prompt: str,
                              history: Optional[List[Dict]] = None,
                              model_override: Optional[str] = None) -> Dict[str, Any]:
        """Return model and tier decision for a prompt."""
        if model_override:
            return {
                "model": model_override,
                "tier": "override",
                "complexity": None
            }

        complexity, tier = self.complexity_analyzer.analyze(prompt, history)
        rule = self.routing_rules.get(tier, {})
        selected_model = rule.get(
            "model",
            self.config.get("litellm", {}).get("default_model", "anthropic/claude-opus-4-5")
        )
        return {
            "model": selected_model,
            "tier": tier,
            "complexity": complexity
        }

    def _select_model(self, prompt: str, history: Optional[List[Dict]] = None,
                      model_override: Optional[str] = None) -> str:
        """Select appropriate model based on complexity analysis."""
        decision = self._get_routing_decision(prompt, history, model_override)
        return decision["model"]

    def _openai_responses_config(self) -> Dict[str, Any]:
        """Return OpenAI responses config section."""
        return self.config.get("openai_responses", {})

    def _is_openai_model(self, model: str) -> bool:
        """Determine if model should use OpenAI responses API."""
        config = self._openai_responses_config()
        prefixes = config.get("model_prefixes", ["gpt-"])
        return any(model.startswith(prefix) for prefix in prefixes)

    def _should_use_openai_responses(self, model: str) -> bool:
        """Check if OpenAI responses API should be used."""
        config = self._openai_responses_config()
        return bool(config.get("enabled", False) and self.openai_client and self._is_openai_model(model))

    def _build_openai_responses_params(self, tier: Optional[str],
                                       max_tokens: int) -> Dict[str, Any]:
        """Build tiered responses parameters for OpenAI."""
        config = self._openai_responses_config()
        tiers = config.get("tiers", {})
        tier_settings = tiers.get(tier or "standard", {})
        max_output_tokens = tier_settings.get("max_output_tokens", max_tokens)
        reasoning_effort = tier_settings.get("reasoning_effort")

        params = {
            "verbosity": tier_settings.get("verbosity"),
            "max_output_tokens": min(max_tokens, max_output_tokens)
        }
        if reasoning_effort:
            params["reasoning"] = {"effort": reasoning_effort}
        return params

    def _extract_openai_response_text(self, response: Any) -> str:
        """Extract text output from OpenAI responses API."""
        if hasattr(response, "output_text") and response.output_text:
            return response.output_text
        output_text = []
        for item in getattr(response, "output", []) or []:
            if getattr(item, "type", "") == "message":
                for content in getattr(item, "content", []) or []:
                    if getattr(content, "type", "") == "output_text":
                        output_text.append(getattr(content, "text", ""))
        return "".join(output_text)

    def _extract_openai_usage(self, response: Any) -> Dict[str, int]:
        """Extract token usage from OpenAI responses API."""
        usage = getattr(response, "usage", None)
        return {
            "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
            "reasoning_tokens": getattr(usage, "reasoning_tokens", 0) if usage else 0
        }

    def _call_with_fallback(self, model: str, messages: List[Dict],
                            max_tokens: int, temperature: float,
                            system: Optional[str] = None,
                            stream: bool = False,
                            tier: Optional[str] = None,
                            tools: Optional[List[Dict]] = None,
                            tool_choice: Optional[Dict] = None) -> Any:
        """
        Make API call with automatic fallback chain support.

        This method implements a fallback chain mechanism that automatically tries
        alternative models when API calls fail. Unlike traditional retry logic,
        this system IMMEDIATELY moves to the next configured model on ANY failure,
        with NO delays or exponential backoff.

        How Fallback Chain Works:
            1. Constructs fallback chain from config/api.json
            2. If requested model not in chain, prepends it automatically
            3. Tries each model in sequence until success or chain exhaustion
            4. On ANY error (RateLimitError, APIConnectionError, APIStatusError):
               - Immediately tries next model in chain
               - No waiting, no exponential backoff
               - Silent failure (no logging unless DEBUG enabled)
            5. If all models fail, raises the last error encountered

        Chain Construction Example:
            Config: fallback_chain = ["anthropic/claude-opus-4-5", "anthropic/claude-sonnet-4-5"]
            Request: model = "anthropic/claude-3-5-haiku-20241022"
            Final chain: ["anthropic/claude-3-5-haiku-20241022", "anthropic/claude-opus-4-5", "anthropic/claude-sonnet-4-5"]

        IMPORTANT - This is NOT Retry Logic:
            - Fallback = Tries different MODELS (immediate, no delay)
            - Retry = Retries same MODEL (with exponential backoff)
            - Both can work together (retry logic handled by external middleware)
            - See docs/TROUBLESHOOTING.md for detailed comparison

        Silent Failures:
            Individual model failures are SILENT by default. You will NOT see
            which models failed or why unless debug logging is enabled:

                export LITELLM_LOG_LEVEL=DEBUG

            Without debug logging, you only see the final result (success or
            exhaustion). This can make troubleshooting difficult.

        Cache Behavior:
            WARNING: Cache keys use the REQUESTED model, not the fallback model
            that actually processed the request.

            Example:
                - Request anthropic/claude-opus-4-5 (fails) → fallback to anthropic/claude-sonnet-4-5 (succeeds)
                - Response cached against "anthropic/claude-opus-4-5" (not "anthropic/claude-sonnet-4-5")
                - Next request to anthropic/claude-opus-4-5 → cache miss, tries opus again
                - Result: Lower cache hit rates, repeated failures

            This is expected behavior. See docs/TROUBLESHOOTING.md section
            "Cache Behavior with Fallbacks" for details.

        Usage Tracking:
            WARNING: Usage tracking records the REQUESTED model, not the fallback
            model that actually processed the request. This leads to INACCURATE
            cost calculations.

            Example:
                - User requests: anthropic/claude-opus-4-5 (costs $15/1M input tokens)
                - Actual model: anthropic/claude-sonnet-4-5 (costs $3/1M input tokens)
                - Tracked as: anthropic/claude-opus-4-5 ← WRONG PRICING
                - Result: Cost reports show 5x higher costs than reality

            See docs/TROUBLESHOOTING.md section "Usage Tracking with Fallbacks"
            for monitoring strategies.

        Args:
            model: The initially requested model (will be prepended to chain)
            messages: List of message dicts with 'role' and 'content' keys
            max_tokens: Maximum tokens to generate in response
            temperature: Sampling temperature (0.0-2.0)
            system: Optional system prompt for context/persona
            stream: If True, return streaming response generator

        Returns:
            API response object (format depends on provider and stream mode):
            - LiteLLM: completion response with choices[0].message.content
            - Direct Anthropic: message object with content[0].text
            - Stream mode: generator yielding chunks

        Raises:
            Exception: The last error encountered if all models in chain fail.
                      Common errors: RateLimitError, APIConnectionError,
                      APIStatusError (401/403/429/500/503)

        Configuration:
            Set fallback chain in config/api.json:
            {
                "litellm": {
                    "fallback_chain": [
                        "anthropic/claude-opus-4-5",     // Anthropic
                        "gpt-4-turbo",                  // OpenAI
                        "anthropic/claude-sonnet-4-5"      // Anthropic fallback
                    ]
                }
            }

        Best Practices:
            ✅ Use models from DIFFERENT providers for resilience
            ✅ Order by preference (best model first)
            ✅ Enable debug logging during troubleshooting
            ✅ Monitor fallback patterns in production
            ❌ Don't use all models from same provider (rate limits affect all)
            ❌ Don't rely on usage tracking cost accuracy with fallbacks

        Troubleshooting:
            For detailed troubleshooting of API errors, rate limits, fallback
            failures, and monitoring strategies, see:
            docs/TROUBLESHOOTING.md - API Error Handling section

        See Also:
            - _make_call(): Underlying method that executes single API call
            - config/api.json: Fallback chain configuration
            - docs/TROUBLESHOOTING.md: Comprehensive error handling guide
        """
        fallback_chain = self.config.get("litellm", {}).get("fallback_chain", [model])

        if model not in fallback_chain:
            fallback_chain = [model] + fallback_chain

        last_error = None
        for fallback_model in fallback_chain:
            try:
                return self._make_call(fallback_model, messages, max_tokens,
                                       temperature, system, stream, tier, tools, tool_choice)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"API call failed for model {fallback_model}: {type(e).__name__}: {e}"
                )
                continue

        logger.error(
            f"All models in fallback chain failed. Last error: {type(last_error).__name__}: {last_error}"
        )
        raise last_error or Exception("All models in fallback chain failed")

    def _call_with_retry(self, func, *args, max_retries: int = 3, **kwargs) -> Any:
        """
        Execute a function with exponential backoff retry for transient API failures.

        Retries on these HTTP status codes:
            - 404: Not Found (transient in some API configurations)
            - 429: Rate Limited (back off and retry)
            - 500: Internal Server Error
            - 502: Bad Gateway
            - 503: Service Unavailable
            - 504: Gateway Timeout

        Args:
            func: The function to call
            *args: Positional arguments for func
            max_retries: Maximum number of retry attempts (default: 3)
            **kwargs: Keyword arguments for func

        Returns:
            The result of func(*args, **kwargs)

        Raises:
            The last exception if all retries fail or if error is not retryable
        """
        retryable_codes = {404, 429, 500, 502, 503, 504}
        last_error = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e

                # Extract status code from various exception types
                status_code = None

                # LiteLLM exceptions
                if hasattr(e, 'status_code'):
                    status_code = e.status_code
                # Anthropic APIStatusError
                elif hasattr(e, 'status'):
                    status_code = e.status
                # Some exceptions wrap the status in response
                elif hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                    status_code = e.response.status_code
                # OpenAI exceptions often have status_code attribute
                elif hasattr(e, 'http_status'):
                    status_code = e.http_status
                # Check error message for status codes as fallback
                elif '404' in str(e) or 'not found' in str(e).lower():
                    status_code = 404
                elif '429' in str(e) or 'rate limit' in str(e).lower():
                    status_code = 429
                elif '500' in str(e):
                    status_code = 500
                elif '502' in str(e):
                    status_code = 502
                elif '503' in str(e):
                    status_code = 503
                elif '504' in str(e):
                    status_code = 504

                # Check if error is retryable and we have retries left
                is_retryable = status_code in retryable_codes if status_code else False
                is_last_attempt = attempt == max_retries - 1

                if not is_retryable or is_last_attempt:
                    raise

                # Exponential backoff: 1s, 2s, 4s
                delay = 2 ** attempt
                logger.info(
                    f"Retryable error (status {status_code}), attempt {attempt + 1}/{max_retries}. "
                    f"Retrying in {delay}s: {type(e).__name__}: {e}"
                )
                time.sleep(delay)

        # Should not reach here, but raise last error if we do
        raise last_error

    def _is_anthropic_model(self, model: str) -> bool:
        """Check if model is an Anthropic Claude model."""
        anthropic_prefixes = ["claude-", "anthropic/"]
        return any(model.startswith(prefix) for prefix in anthropic_prefixes)

    def _convert_tools_for_anthropic(self, tools: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI-style tools to Anthropic format.

        OpenAI format: {"type": "function", "function": {"name": "x", "description": "y", "parameters": {...}}}
        Anthropic format: {"name": "x", "description": "y", "input_schema": {...}}
        """
        converted = []
        for tool in tools:
            if tool.get("type") == "function" and "function" in tool:
                func = tool["function"]
                converted.append({
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {"type": "object", "properties": {}})
                })
            else:
                # Already in Anthropic format or unknown format, pass through
                converted.append(tool)
        return converted

    def _convert_messages_for_anthropic(self, messages: List[Dict]) -> List[Dict]:
        """
        Convert OpenAI-style messages to Anthropic format.

        Handles tool results which use different formats:
        - OpenAI: {"role": "tool", "tool_call_id": "x", "content": "..."}
        - Anthropic: {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "x", "content": "..."}]}

        Also handles assistant messages with tool_calls:
        - OpenAI: {"role": "assistant", "tool_calls": [...]}
        - Anthropic: {"role": "assistant", "content": [{"type": "tool_use", ...}]}
        """
        converted = []
        tool_results_batch = []

        for msg in messages:
            role = msg.get("role", "")

            if role == "tool":
                # Collect tool results to batch them
                tool_results_batch.append({
                    "type": "tool_result",
                    "tool_use_id": msg.get("tool_call_id", ""),
                    "content": msg.get("content", "")
                })
            else:
                # Flush any pending tool results before adding next message
                if tool_results_batch:
                    converted.append({
                        "role": "user",
                        "content": tool_results_batch
                    })
                    tool_results_batch = []

                if role == "assistant" and msg.get("tool_calls"):
                    # Convert assistant message with tool calls
                    content = []
                    if msg.get("content"):
                        content.append({"type": "text", "text": msg["content"]})
                    for tc in msg.get("tool_calls", []):
                        func = tc.get("function", {})
                        import json
                        try:
                            args = json.loads(func.get("arguments", "{}"))
                        except:
                            args = {}
                        content.append({
                            "type": "tool_use",
                            "id": tc.get("id", ""),
                            "name": func.get("name", ""),
                            "input": args
                        })
                    converted.append({"role": "assistant", "content": content})
                else:
                    # Pass through other messages
                    converted.append(msg)

        # Flush any remaining tool results
        if tool_results_batch:
            converted.append({
                "role": "user",
                "content": tool_results_batch
            })

        return converted

    def _make_call(self, model: str, messages: List[Dict],
                   max_tokens: int, temperature: float,
                   system: Optional[str] = None,
                   stream: bool = False,
                   tier: Optional[str] = None,
                   tools: Optional[List[Dict]] = None,
                   tool_choice: Optional[Dict] = None) -> Any:
        """Make actual API call via LiteLLM or fallback with retry logic for transient failures."""
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        # Convert tools and messages for Anthropic models
        if self._is_anthropic_model(model):
            if tools:
                tools = self._convert_tools_for_anthropic(tools)
            # Convert messages with tool results to Anthropic format
            full_messages = self._convert_messages_for_anthropic(full_messages)

        # Get max_retries from config (default: 3)
        max_retries = self.config.get("litellm", {}).get("max_retries", 3)

        if self._should_use_openai_responses(model):
            params = self._build_openai_responses_params(tier, max_tokens)
            if stream:
                return self._call_with_retry(
                    self.openai_client.responses.stream,
                    model=model,
                    input=full_messages,
                    temperature=temperature,
                    max_retries=max_retries,
                    **{k: v for k, v in params.items() if v is not None}
                )
            return self._call_with_retry(
                self.openai_client.responses.create,
                model=model,
                input=full_messages,
                temperature=temperature,
                max_retries=max_retries,
                **{k: v for k, v in params.items() if v is not None}
            )

        if LITELLM_AVAILABLE:
            # Build base kwargs
            litellm_kwargs = {
                "model": model,
                "messages": full_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            # Add tools if provided
            if tools:
                litellm_kwargs["tools"] = tools

            if stream:
                return self._call_with_retry(
                    completion,
                    stream=True,
                    max_retries=max_retries,
                    **litellm_kwargs
                )
            else:
                return self._call_with_retry(
                    completion,
                    max_retries=max_retries,
                    **litellm_kwargs
                )

        # Fallbacks
        elif model.startswith("gpt") and self.fallback_client_openai:
             # Direct OpenAI Fallback
             # Adjust model names if needed (e.g. gpt-4.1-mini -> gpt-4o-mini if mapped)
             # For now assume model names overlap or are close enough

             # System prompt handled differently in OpenAI (as a message)
             full_messages = []
             if system:
                 full_messages.append({"role": "system", "content": system})
             full_messages.extend(messages)

             kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": full_messages
             }
             if tools:
                 kwargs["tools"] = tools

             if stream:
                 return self._call_with_retry(
                     self.fallback_client_openai.chat.completions.create,
                     stream=True,
                     max_retries=max_retries,
                     **kwargs
                 )
             else:
                 return self._call_with_retry(
                     self.fallback_client_openai.chat.completions.create,
                     max_retries=max_retries,
                     **kwargs
                 )

        elif self.fallback_client_anthropic:
            # Direct Anthropic fallback - use converted messages (no system in messages for Anthropic)
            # Filter out system messages from full_messages (Anthropic uses separate system param)
            anthropic_messages = [m for m in full_messages if m.get("role") != "system"]
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": anthropic_messages  # Use converted messages
            }
            if system:
                kwargs["system"] = system
            if tools:
                kwargs["tools"] = tools
                # Default to 'any' to encourage tool use when tools are provided
                kwargs["tool_choice"] = tool_choice or {"type": "auto"}

            if stream:
                return self._call_with_retry(
                    self.fallback_client_anthropic.messages.stream,
                    max_retries=max_retries,
                    **kwargs
                )
            else:
                return self._call_with_retry(
                    self.fallback_client_anthropic.messages.create,
                    max_retries=max_retries,
                    **kwargs
                )

        else:
            raise RuntimeError(f"LiteLLM not available and no suitable fallback for model {model}")

    def chat(self, prompt: str, model: Optional[str] = None,
             max_tokens: Optional[int] = None, temperature: Optional[float] = None,
             system_prompt: Optional[str] = None, history: Optional[List[Dict]] = None,
             use_cache: bool = True, operation: str = "chat",
             metadata: Optional[Dict] = None, agent: Optional[str] = None,
             tools: Optional[List[Dict]] = None,
             tool_choice: Optional[Dict] = None) -> Union[str, Dict]:
        """
        Send a chat message and get a response with intelligent model routing.

        Args:
            prompt: The user message to send
            model: Model override (auto-routes if not specified)
            max_tokens: Max tokens override
            temperature: Temperature override
            system_prompt: System prompt for persona/context
            history: Previous conversation messages
            use_cache: Whether to use response caching
            operation: Operation name for usage tracking
            metadata: Additional metadata for usage tracking
            agent: Optional agent name for persona-based routing
                   (ops, coach, strategy, health)
            tools: Optional list of tool definitions for MCP tool calling.
                   Each tool should be a dict with 'type', 'function' keys.
                   Example: [{"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}]

        Returns:
            str: The assistant's response text (when no tool calls)
            Dict: When tool calls are present, returns:
                  {"type": "tool_calls", "tool_calls": [...], "content": str|None}
        """
        defaults = self.config.get("defaults", {})
        max_tokens = max_tokens or defaults.get("max_tokens", 4096)
        temperature = temperature if temperature is not None else defaults.get("temperature", 1.0)

        # Select model: agent routing > explicit model > complexity routing
        if agent and not model:
            agent_model = self.agent_router.get_model(agent)
            if agent_model:
                model = agent_model
        
        decision = self._get_routing_decision(prompt, history, model)
        selected_model = decision["model"]
        tier = decision["tier"]
        complexity = decision["complexity"]

        # Check cache
        cache_params = {"max_tokens": max_tokens, "temperature": temperature, "system": system_prompt}
        if use_cache and self.cache:
            cached = self.cache.get(prompt, selected_model, cache_params)
            if cached:
                return cached

        # Build messages
        messages = list(history) if history else []
        
        # Check if we need to append the prompt
        # If history was provided, the last message might be the current prompt
        should_append = True
        if messages and messages[-1].get("role") == "user" and messages[-1].get("content") == prompt:
            should_append = False
            
        if should_append:
            messages.append({"role": "user", "content": prompt})

        # Make API call with timing
        start_time = time.time()

        response = self._call_with_fallback(
            model=selected_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            tier=tier,
            tools=tools,
            tool_choice=tool_choice
        )

        latency_ms = (time.time() - start_time) * 1000

        # Check for tool calls in response
        tool_calls = None
        if hasattr(response, "choices") and response.choices:
            # OpenAI format
            message = response.choices[0].message
            tool_calls = getattr(message, "tool_calls", None)
        elif hasattr(response, "content") and hasattr(response, "stop_reason"):
            # Anthropic format - check for tool_use blocks in content
            if response.stop_reason == "tool_use":
                tool_calls = []
                for block in response.content:
                    if getattr(block, "type", None) == "tool_use":
                        # Convert Anthropic tool_use to OpenAI tool_call format
                        import json
                        tool_calls.append(type('ToolCall', (), {
                            'id': block.id,
                            'type': 'function',
                            'function': type('Function', (), {
                                'name': block.name,
                                'arguments': json.dumps(block.input)
                            })()
                        })())

        # Extract response text and usage
        openai_reasoning_tokens = None
        api_error = False
        api_error_message = None

        if self._should_use_openai_responses(selected_model) and not hasattr(response, "choices"):
            response_text = self._extract_openai_response_text(response)
            usage = self._extract_openai_usage(response)
            input_tokens = usage["input_tokens"]
            output_tokens = usage["output_tokens"]
            openai_reasoning_tokens = usage["reasoning_tokens"]
            if input_tokens == 0 and output_tokens == 0:
                api_error = True
                api_error_message = "OpenAI responses API returned no usage data"
                logger.warning(f"API call returned no usage data for model {selected_model}")
        elif LITELLM_AVAILABLE:
            usage = getattr(response, "usage", None)
            if usage is None:
                api_error = True
                api_error_message = "LiteLLM response missing usage data"
                logger.warning(f"API call returned no usage data for model {selected_model}")
                input_tokens = 0
                output_tokens = 0
                response_text = response.choices[0].message.content if hasattr(response, "choices") and response.choices else ""
            else:
                openai_reasoning_tokens = getattr(usage, "reasoning_tokens", None)
                response_text = response.choices[0].message.content
                input_tokens = usage.prompt_tokens
                output_tokens = usage.completion_tokens
        else:
            # Handle different fallback client response formats
            if hasattr(response, 'choices'):
                # OpenAI Format
                response_text = response.choices[0].message.content
                usage = getattr(response, "usage", None)
                if usage is None:
                    api_error = True
                    api_error_message = "OpenAI response missing usage data"
                    logger.warning(f"API call returned no usage data for model {selected_model}")
                    input_tokens = 0
                    output_tokens = 0
                else:
                    input_tokens = usage.prompt_tokens
                    output_tokens = usage.completion_tokens
            else:
                # Anthropic Format - extract text from content blocks
                response_text = ""
                for block in response.content:
                    if getattr(block, "type", None) == "text":
                        response_text += getattr(block, "text", "")
                usage = getattr(response, "usage", None)
                if usage is None:
                    api_error = True
                    api_error_message = "Anthropic response missing usage data"
                    logger.warning(f"API call returned no usage data for model {selected_model}")
                    input_tokens = 0
                    output_tokens = 0
                else:
                    input_tokens = usage.input_tokens
                    output_tokens = usage.output_tokens

        # Calculate cost and track usage
        if self.usage_tracker:
            cost = self.usage_tracker.calculate_cost(selected_model, input_tokens, output_tokens)
            self.usage_tracker.record(
                model=selected_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                operation=operation,
                metadata={
                    **(metadata or {}),
                    "openai_reasoning_tokens": openai_reasoning_tokens,
                    "routing_tier": tier,
                    "complexity_score": complexity,
                    "api_error": api_error,
                    "api_error_message": api_error_message
                }
            )

        # Cache response (only cache if no tool calls - tool calls are dynamic)
        if use_cache and self.cache and not tool_calls:
            self.cache.set(prompt, selected_model, cache_params, response_text)

        # Return tool calls dict if present, otherwise return text content
        if tool_calls:
            # Convert tool_calls to serializable format
            serialized_tool_calls = []
            for tc in tool_calls:
                tc_dict = {
                    "id": getattr(tc, "id", None),
                    "type": getattr(tc, "type", "function"),
                    "function": {
                        "name": getattr(tc.function, "name", None) if hasattr(tc, "function") else None,
                        "arguments": getattr(tc.function, "arguments", "{}") if hasattr(tc, "function") else "{}"
                    }
                }
                serialized_tool_calls.append(tc_dict)
            return {
                "type": "tool_calls",
                "tool_calls": serialized_tool_calls,
                "content": response_text
            }

        return response_text

    def route(self, query: str, candidates: List[str], classification_prompt: str = None) -> str:
        """
        Route a query to one of the candidate labels using an LLM.

        Args:
            query: The user query to route
            candidates: List of valid categories/agents
            classification_prompt: Optional custom system prompt

        Returns:
            The selected candidate string
        """
        if not classification_prompt:
            classification_prompt = (
                "You are an intent classification system. "
                "Classify the following query into exactly one of these categories: "
                f"{', '.join(candidates)}. "
                "Return ONLY the category name in lowercase. No other text."
            )

        # Use the simplest model for routing (usually cheap and fast)
        response = self.chat(
            prompt=f"Query: {query}\nCategory:",
            system_prompt=classification_prompt,
            model=self.config.get("model_routing", {}).get("rules", {}).get("simple", {}).get("model"),
            max_tokens=10,
            temperature=0.0
        )

        result = response.strip().lower()
        
        # Validation - finding the best match
        for candidate in candidates:
            if candidate in result:
                return candidate
        
        # Default to first candidate if no clear match
        return candidates[0]

    def chat_stream(self, prompt: str, model: Optional[str] = None,
                    max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                    system_prompt: Optional[str] = None, history: Optional[List[Dict]] = None,
                    operation: str = "chat_stream",
                    metadata: Optional[Dict] = None, agent: Optional[str] = None,
                    tools: Optional[List[Dict]] = None) -> Generator[Union[str, Dict], None, None]:
        """
        Stream a chat response token by token.

        Args:
            prompt: The user message to send
            model: Model override (auto-routes if not specified)
            max_tokens: Max tokens override
            temperature: Temperature override
            system_prompt: System prompt for persona/context
            history: Previous conversation messages
            operation: Operation name for usage tracking
            metadata: Additional metadata for usage tracking
            agent: Optional agent name for persona-based routing
            tools: Optional list of tool definitions for MCP tool calling.
                   Note: Tool calls don't work well with streaming. If tools are provided
                   and the model returns tool calls, use non-streaming chat() instead.

        Yields:
            Response text chunks as they arrive.
            Finally yields a dict {"type": "usage", "usage": {...}} with stats.
        """
        defaults = self.config.get("defaults", {})
        max_tokens = max_tokens or defaults.get("max_tokens", 4096)
        temperature = temperature if temperature is not None else defaults.get("temperature", 1.0)

        # Select model: agent routing > explicit model > complexity routing
        if agent and not model:
            agent_model = self.agent_router.get_model(agent)
            if agent_model:
                model = agent_model
        
        # Select model
        decision = self._get_routing_decision(prompt, history, model)
        selected_model = decision["model"]
        tier = decision["tier"]
        complexity = decision["complexity"]

        # Build messages
        messages = list(history) if history else []
        
        # Check if we need to append the prompt
        should_append = True
        if messages and messages[-1].get("role") == "user" and messages[-1].get("content") == prompt:
            should_append = False
            
        if should_append:
            messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        openai_reasoning_tokens = None
        if self._should_use_openai_responses(selected_model):
            response = self._call_with_fallback(
                model=selected_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                stream=True,
                tier=tier,
                tools=tools
            )
            with response as stream:
                for event in stream:
                    if getattr(event, "type", "") == "response.output_text.delta":
                        text = getattr(event, "delta", "")
                        full_response += text
                        yield text
                final_response = stream.get_final_response()
                usage = self._extract_openai_usage(final_response)
                input_tokens = usage["input_tokens"]
                output_tokens = usage["output_tokens"]
                openai_reasoning_tokens = usage["reasoning_tokens"]
        elif LITELLM_AVAILABLE:
            response = self._call_with_fallback(
                model=selected_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                stream=True,
                tier=tier,
                tools=tools
            )

            for chunk in response:
                text = None
                choice = None
                if hasattr(chunk, "choices") and chunk.choices:
                    choice = chunk.choices[0]
                if choice is not None:
                    delta = getattr(choice, "delta", None)
                    if isinstance(delta, dict):
                        text = delta.get("content") or delta.get("text")
                    elif delta is not None:
                        text = getattr(delta, "content", None) or getattr(delta, "text", None)
                    if text is None:
                        message = getattr(choice, "message", None)
                        if isinstance(message, dict):
                            text = message.get("content")
                        elif message is not None:
                            text = getattr(message, "content", None)
                    if text is None:
                        text = getattr(choice, "text", None)
                if text:
                    full_response += text
                    yield text

                # Estimate tokens (LiteLLM streaming doesn't always provide usage)
                output_tokens = len(full_response) // 4

            input_tokens = len(prompt) // 4 + sum(len(m.get("content", "")) // 4 for m in messages[:-1])

        elif self.fallback_client_anthropic or self.fallback_client_openai:
            response = self._make_call(
                model=selected_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                stream=True,
                tools=tools
            )
            
            # Handle Anthropic Stream (Context Manager)
            # MessageStreamManager needs to be entered to get the stream with text_stream
            is_anthropic_manager = type(response).__name__ == 'MessageStreamManager'
            if hasattr(response, "text_stream") or is_anthropic_manager:
                with response as stream:
                    for text in stream.text_stream:
                        full_response += text
                        yield text
                    final = stream.get_final_message()
                    input_tokens = final.usage.input_tokens
                    output_tokens = final.usage.output_tokens
            
            # Handle OpenAI Stream (Iterator)
            else:
                 for chunk in response:
                    text = None
                    if hasattr(chunk, "choices") and chunk.choices:
                        delta = chunk.choices[0].delta
                        text = getattr(delta, "content", "") or ""
                    
                    if text:
                        full_response += text
                        yield text
                 
                 # OpenAI stream usage is often in the last chunk or ignored in simple implementations
                 # We can estimate or check for usage chunk
                 output_tokens = len(full_response) // 4
                 input_tokens = len(prompt) // 4  # Rough estimate since we lost exact count

        else:
            msg = "No LLM client available for streaming responses."
            if not LITELLM_AVAILABLE:
                msg += " LiteLLM is missing."
            if not self.fallback_client_anthropic and not self.fallback_client_openai:
                msg += " Available fallbacks (Anthropic/OpenAI) could not be initialized (check API keys)."
            raise RuntimeError(msg)

        latency_ms = (time.time() - start_time) * 1000

        # Track usage
        if self.usage_tracker:
            cost = self.usage_tracker.calculate_cost(selected_model, input_tokens, output_tokens)
            self.usage_tracker.record(
                model=selected_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
                operation=operation,
                metadata={
                    **(metadata or {}),
                    "openai_reasoning_tokens": openai_reasoning_tokens,
                    "routing_tier": tier,
                    "complexity_score": complexity
                }
            )

        # Yield usage stats at the end
        yield {
            "type": "usage",
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost if self.usage_tracker else 0.0,
                "model": selected_model
            }
        }

        if not full_response:
            raise RuntimeError("Streaming response returned no content.")

    def get_usage_summary(self, days: int = 30) -> Dict:
        """Get usage summary for the specified period."""
        if self.usage_tracker:
            return self.usage_tracker.get_summary(days)
        return {}

    def get_today_usage(self) -> Dict:
        """Get today's usage stats."""
        if self.usage_tracker:
            return self.usage_tracker.get_today()
        return {"tokens": 0, "cost": 0.0, "calls": 0}

    def analyze_complexity(self, prompt: str, history: Optional[List[Dict]] = None) -> Dict:
        """Analyze prompt complexity and return routing info."""
        decision = self._get_routing_decision(prompt, history)
        complexity = decision["complexity"]
        tier = decision["tier"]
        selected_model = decision["model"]

        return {
            "complexity_score": complexity,
            "tier": tier,
            "selected_model": selected_model,
            "routing_rules": self.routing_rules
        }

    def shutdown(self, timeout: float = 5.0):
        """
        Gracefully shutdown the client and flush pending usage data.
        
        Args:
            timeout: Maximum time to wait for operations to complete (not fully used yet)
        """
        if self.usage_tracker and hasattr(self.usage_tracker, 'flush'):
            # Assuming UsageTracker might have a flush method, or we implement basic cleanup
            pass
            # Ideally usage_tracker handles file writes immediately in this sync implementation,
            # but if we add async/buffering later, this is where we'd flush.
        
        if self.cache and hasattr(self.cache, 'close'):
            self.cache.close()

    def list_available_models(self) -> List[str]:
        """List all configured models."""
        models = []
        providers = self.config.get("litellm", {}).get("providers", {})
        for provider, pconfig in providers.items():
            for alias, model in pconfig.get("models", {}).items():
                models.append(model)
        return models


# Singleton instance management
_client_instance = None


def get_client(config_path: str = None) -> LiteLLMClient:
    """Get or create the singleton client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = LiteLLMClient(config_path)
    return _client_instance


def init_client(config_path: str = None) -> LiteLLMClient:
    """Initialize and return a new client instance."""
    global _client_instance
    _client_instance = LiteLLMClient(config_path)
    return _client_instance
