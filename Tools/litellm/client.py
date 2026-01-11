#!/usr/bin/env python3
"""
Main LiteLLM client for unified multi-model API access.

This module provides the primary LiteLLMClient class which orchestrates
API calls across multiple model providers with intelligent routing, caching,
and usage tracking capabilities.
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Generator, Any, List

# Import support classes from the package
from .usage_tracker import UsageTracker
from .complexity_analyzer import ComplexityAnalyzer
from .response_cache import ResponseCache

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


# Export constants and classes
__all__ = [
    "LiteLLMClient",
    "get_client",
    "init_client",
    "LITELLM_AVAILABLE",
    "ANTHROPIC_AVAILABLE",
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
        self.config = self._load_config(config_path)

        # Setup providers API keys
        self._setup_api_keys()

        # Initialize components
        self._init_usage_tracker()
        self._init_cache()
        self._init_complexity_analyzer()
        self._init_fallback_client()

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
                "default_model": "claude-opus-4-5-20251101",
                "fallback_chain": ["claude-opus-4-5-20251101", "claude-sonnet-4-20250514"],
                "timeout": 600,
                "max_retries": 3,
                "retry_delay": 1.0
            },
            "model_routing": {
                "rules": {
                    "complex": {"model": "claude-opus-4-5-20251101", "min_complexity": 0.7},
                    "standard": {"model": "claude-sonnet-4-20250514", "min_complexity": 0.3},
                    "simple": {"model": "claude-3-5-haiku-20241022", "max_complexity": 0.3}
                }
            },
            "usage_tracking": {"enabled": True, "storage_path": "State/usage.json"},
            "caching": {"enabled": True, "ttl_seconds": 3600, "storage_path": "Memory/cache/"},
            "defaults": {"max_tokens": 4096, "temperature": 1.0}
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

    def _init_fallback_client(self):
        """Initialize fallback Anthropic client if LiteLLM unavailable."""
        if not LITELLM_AVAILABLE and ANTHROPIC_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                self.fallback_client = anthropic.Anthropic(api_key=api_key)
            else:
                self.fallback_client = None
        else:
            self.fallback_client = None

    def _select_model(self, prompt: str, history: Optional[List[Dict]] = None,
                      model_override: Optional[str] = None) -> str:
        """Select appropriate model based on complexity analysis."""
        if model_override:
            return model_override

        complexity, tier = self.complexity_analyzer.analyze(prompt, history)

        # Get model from routing rules
        rule = self.routing_rules.get(tier, {})
        return rule.get("model", self.config.get("litellm", {}).get("default_model", "claude-opus-4-5-20251101"))

    def _call_with_fallback(self, model: str, messages: List[Dict],
                            max_tokens: int, temperature: float,
                            system: Optional[str] = None,
                            stream: bool = False) -> Any:
        """Make API call with fallback chain support."""
        fallback_chain = self.config.get("litellm", {}).get("fallback_chain", [model])

        if model not in fallback_chain:
            fallback_chain = [model] + fallback_chain

        last_error = None
        for fallback_model in fallback_chain:
            try:
                return self._make_call(fallback_model, messages, max_tokens,
                                       temperature, system, stream)
            except Exception as e:
                last_error = e
                continue

        raise last_error or Exception("All models in fallback chain failed")

    def _make_call(self, model: str, messages: List[Dict],
                   max_tokens: int, temperature: float,
                   system: Optional[str] = None,
                   stream: bool = False) -> Any:
        """Make actual API call via LiteLLM or fallback."""

        if LITELLM_AVAILABLE:
            # Build messages with system prompt
            full_messages = []
            if system:
                full_messages.append({"role": "system", "content": system})
            full_messages.extend(messages)

            if stream:
                return completion(
                    model=model,
                    messages=full_messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stream=True
                )
            else:
                return completion(
                    model=model,
                    messages=full_messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )

        elif self.fallback_client:
            # Direct Anthropic fallback
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }
            if system:
                kwargs["system"] = system

            if stream:
                return self.fallback_client.messages.stream(**kwargs)
            else:
                return self.fallback_client.messages.create(**kwargs)

        else:
            raise RuntimeError("No API client available. Install litellm or anthropic.")

    def chat(self, prompt: str, model: Optional[str] = None,
             max_tokens: Optional[int] = None, temperature: Optional[float] = None,
             system_prompt: Optional[str] = None, history: Optional[List[Dict]] = None,
             use_cache: bool = True, operation: str = "chat",
             metadata: Optional[Dict] = None) -> str:
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

        Returns:
            The assistant's response text
        """
        defaults = self.config.get("defaults", {})
        max_tokens = max_tokens or defaults.get("max_tokens", 4096)
        temperature = temperature if temperature is not None else defaults.get("temperature", 1.0)

        # Select model based on complexity
        selected_model = self._select_model(prompt, history, model)

        # Check cache
        cache_params = {"max_tokens": max_tokens, "temperature": temperature, "system": system_prompt}
        if use_cache and self.cache:
            cached = self.cache.get(prompt, selected_model, cache_params)
            if cached:
                return cached

        # Build messages
        messages = list(history) if history else []
        messages.append({"role": "user", "content": prompt})

        # Make API call with timing
        start_time = time.time()

        response = self._call_with_fallback(
            model=selected_model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt
        )

        latency_ms = (time.time() - start_time) * 1000

        # Extract response text and usage
        if LITELLM_AVAILABLE:
            response_text = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
        else:
            response_text = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

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
                metadata=metadata
            )

        # Cache response
        if use_cache and self.cache:
            self.cache.set(prompt, selected_model, cache_params, response_text)

        return response_text

    def chat_stream(self, prompt: str, model: Optional[str] = None,
                    max_tokens: Optional[int] = None, temperature: Optional[float] = None,
                    system_prompt: Optional[str] = None, history: Optional[List[Dict]] = None,
                    operation: str = "chat_stream",
                    metadata: Optional[Dict] = None) -> Generator[str, None, None]:
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

        Yields:
            Response text chunks as they arrive
        """
        defaults = self.config.get("defaults", {})
        max_tokens = max_tokens or defaults.get("max_tokens", 4096)
        temperature = temperature if temperature is not None else defaults.get("temperature", 1.0)

        # Select model
        selected_model = self._select_model(prompt, history, model)

        # Build messages
        messages = list(history) if history else []
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        full_response = ""
        input_tokens = 0
        output_tokens = 0

        if LITELLM_AVAILABLE:
            response = self._call_with_fallback(
                model=selected_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    text = chunk.choices[0].delta.content
                    full_response += text
                    yield text

                # Estimate tokens (LiteLLM streaming doesn't always provide usage)
                output_tokens = len(full_response) // 4

            input_tokens = len(prompt) // 4 + sum(len(m.get("content", "")) // 4 for m in messages[:-1])

        elif self.fallback_client:
            with self._make_call(
                model=selected_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                stream=True
            ) as stream:
                for text in stream.text_stream:
                    full_response += text
                    yield text

                final = stream.get_final_message()
                input_tokens = final.usage.input_tokens
                output_tokens = final.usage.output_tokens

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
                metadata=metadata
            )

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
        complexity, tier = self.complexity_analyzer.analyze(prompt, history)
        selected_model = self._select_model(prompt, history)

        return {
            "complexity_score": complexity,
            "tier": tier,
            "selected_model": selected_model,
            "routing_rules": self.routing_rules
        }

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
