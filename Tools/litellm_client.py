#!/usr/bin/env python3
"""
LiteLLM Client for Thanos Personal Assistant Framework
Unified multi-model API client supporting Claude, GPT, Gemini, and 100+ models.

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
"""

from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple


# LiteLLM import with fallback
try:
    import litellm
    from litellm import acompletion, completion
    from litellm.exceptions import (
        APIConnectionError as LiteLLMConnectionError,
        APIError as LiteLLMAPIError,
        RateLimitError as LiteLLMRateLimitError,
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
    from anthropic import APIConnectionError, APIStatusError, RateLimitError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class ModelResponse:
    """Standardized response from any model provider."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    cached: bool = False
    metadata: Dict = field(default_factory=dict)


class UsageTracker:
    """Track token usage and costs across all model providers."""

    def __init__(self, storage_path: str, pricing: Dict[str, Dict[str, float]]):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.pricing = pricing
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Initialize storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self.storage_path.write_text(json.dumps({
                "sessions": [],
                "daily_totals": {},
                "model_breakdown": {},
                "provider_breakdown": {},
                "last_updated": datetime.now().isoformat()
            }, indent=2))

    def _get_provider(self, model: str) -> str:
        """Determine provider from model name."""
        if "claude" in model.lower():
            return "anthropic"
        elif "gpt" in model.lower():
            return "openai"
        elif "gemini" in model.lower():
            return "google"
        else:
            return "unknown"

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a given model and token count."""
        # Normalize model name for pricing lookup
        model_key = model
        for key in self.pricing:
            if key in model or model in key:
                model_key = key
                break

        pricing = self.pricing.get(model_key, {"input": 0.01, "output": 0.03})
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        return input_cost + output_cost

    def record(self, model: str, input_tokens: int, output_tokens: int,
               cost_usd: float, latency_ms: float, operation: str = "chat",
               metadata: Optional[Dict] = None) -> Dict:
        """Record a single API call's usage."""
        provider = self._get_provider(model)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "operation": operation,
            "metadata": metadata or {}
        }

        # Load, update, save
        data = json.loads(self.storage_path.read_text())
        data["sessions"].append(entry)

        # Update daily totals
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in data["daily_totals"]:
            data["daily_totals"][today] = {"tokens": 0, "cost": 0.0, "calls": 0}
        data["daily_totals"][today]["tokens"] += input_tokens + output_tokens
        data["daily_totals"][today]["cost"] += cost_usd
        data["daily_totals"][today]["calls"] += 1

        # Update model breakdown
        if model not in data.get("model_breakdown", {}):
            data.setdefault("model_breakdown", {})[model] = {"tokens": 0, "cost": 0.0, "calls": 0}
        data["model_breakdown"][model]["tokens"] += input_tokens + output_tokens
        data["model_breakdown"][model]["cost"] += cost_usd
        data["model_breakdown"][model]["calls"] += 1

        # Update provider breakdown
        if provider not in data.get("provider_breakdown", {}):
            data.setdefault("provider_breakdown", {})[provider] = {"tokens": 0, "cost": 0.0, "calls": 0}
        data["provider_breakdown"][provider]["tokens"] += input_tokens + output_tokens
        data["provider_breakdown"][provider]["cost"] += cost_usd
        data["provider_breakdown"][provider]["calls"] += 1

        data["last_updated"] = datetime.now().isoformat()

        # Keep only last 1000 session entries
        if len(data["sessions"]) > 1000:
            data["sessions"] = data["sessions"][-1000:]

        self.storage_path.write_text(json.dumps(data, indent=2))
        return entry

    def get_summary(self, days: int = 30) -> Dict:
        """Get usage summary for the specified number of days."""
        data = json.loads(self.storage_path.read_text())
        cutoff = datetime.now() - timedelta(days=days)

        total_tokens = 0
        total_cost = 0.0
        total_calls = 0

        for date_str, daily in data.get("daily_totals", {}).items():
            try:
                date = datetime.strptime(date_str, "%Y-%m-%d")
                if date >= cutoff:
                    total_tokens += daily.get("tokens", 0)
                    total_cost += daily.get("cost", 0.0)
                    total_calls += daily.get("calls", 0)
            except ValueError:
                continue

        return {
            "period_days": days,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "total_calls": total_calls,
            "avg_daily_tokens": total_tokens / max(days, 1),
            "avg_daily_cost": total_cost / max(days, 1),
            "projected_monthly_cost": (total_cost / max(days, 1)) * 30,
            "model_breakdown": data.get("model_breakdown", {}),
            "provider_breakdown": data.get("provider_breakdown", {})
        }

    def get_today(self) -> Dict:
        """Get today's usage stats."""
        data = json.loads(self.storage_path.read_text())
        today = datetime.now().strftime("%Y-%m-%d")
        return data.get("daily_totals", {}).get(today, {"tokens": 0, "cost": 0.0, "calls": 0})


class ComplexityAnalyzer:
    """Analyze prompt complexity for model routing."""

    def __init__(self, config: Dict):
        self.config = config
        self.factors = config.get("complexity_factors", {
            "token_count_weight": 0.3,
            "keyword_weight": 0.4,
            "history_length_weight": 0.3
        })

    def analyze(self, prompt: str, history: Optional[List[Dict]] = None) -> Tuple[float, str]:
        """
        Analyze prompt complexity and return score with recommended tier.

        Returns:
            Tuple of (complexity_score: float, tier: str)
        """
        scores = []

        # Token count factor (rough estimate: 4 chars per token)
        estimated_tokens = len(prompt) / 4
        if history:
            estimated_tokens += sum(len(m.get("content", "")) / 4 for m in history)

        token_score = min(estimated_tokens / 2000, 1.0)  # Normalize to 0-1
        scores.append(("token_count", token_score, self.factors.get("token_count_weight", 0.3)))

        # Keyword complexity factor
        complex_indicators = [
            "analyze", "architecture", "strategy", "debug", "investigate",
            "optimize", "refactor", "design", "explain", "comprehensive",
            "detailed", "thoroughly", "step by step", "reasoning"
        ]
        simple_indicators = [
            "quick", "simple", "lookup", "translate", "format",
            "summarize briefly", "one sentence", "yes or no"
        ]

        prompt_lower = prompt.lower()
        complex_matches = sum(1 for ind in complex_indicators if ind in prompt_lower)
        simple_matches = sum(1 for ind in simple_indicators if ind in prompt_lower)

        keyword_score = min((complex_matches * 0.2) - (simple_matches * 0.15) + 0.5, 1.0)
        keyword_score = max(keyword_score, 0.0)
        scores.append(("keyword", keyword_score, self.factors.get("keyword_weight", 0.4)))

        # History length factor
        history_len = len(history) if history else 0
        history_score = min(history_len / 10, 1.0)  # Normalize: 10+ messages = max complexity
        scores.append(("history", history_score, self.factors.get("history_length_weight", 0.3)))

        # Calculate weighted average
        total_weight = sum(w for _, _, w in scores)
        complexity = sum(s * w for _, s, w in scores) / total_weight if total_weight > 0 else 0.5

        # Determine tier
        if complexity >= 0.7:
            tier = "complex"
        elif complexity >= 0.3:
            tier = "standard"
        else:
            tier = "simple"

        return complexity, tier


class ResponseCache:
    """Cache responses with TTL and model-specific storage."""

    def __init__(self, cache_path: str, ttl_seconds: int, max_size_mb: int = 100):
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
        self.max_size_bytes = max_size_mb * 1024 * 1024

    def _get_cache_key(self, prompt: str, model: str, params: Dict) -> str:
        """Generate a cache key from prompt and parameters."""
        content = json.dumps({
            "prompt": prompt,
            "model": model,
            "params": {k: v for k, v in params.items() if k != "history"}
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get(self, prompt: str, model: str, params: Dict) -> Optional[str]:
        """Retrieve cached response if valid."""
        cache_key = self._get_cache_key(prompt, model, params)
        cache_file = self.cache_path / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            cached = json.loads(cache_file.read_text())
            cached_time = datetime.fromisoformat(cached["timestamp"])
            if datetime.now() - cached_time < timedelta(seconds=self.ttl_seconds):
                return cached["response"]
            else:
                cache_file.unlink()  # Remove expired cache
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        return None

    def set(self, prompt: str, model: str, params: Dict, response: str):
        """Cache a response."""
        cache_key = self._get_cache_key(prompt, model, params)
        cache_file = self.cache_path / f"{cache_key}.json"

        cache_file.write_text(json.dumps({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "response": response
        }))

    def clear_expired(self):
        """Remove expired cache entries."""
        cutoff = datetime.now() - timedelta(seconds=self.ttl_seconds)
        for cache_file in self.cache_path.glob("*.json"):
            try:
                cached = json.loads(cache_file.read_text())
                cached_time = datetime.fromisoformat(cached["timestamp"])
                if cached_time < cutoff:
                    cache_file.unlink()
            except (json.JSONDecodeError, KeyError, ValueError):
                cache_file.unlink()  # Remove corrupted cache


class LiteLLMClient:
    """Unified multi-model client using LiteLLM with intelligent routing."""

    def __init__(self, config_path: str = None):
        # Find config
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "api.json"
        else:
            config_path = Path(config_path)

        self.base_dir = Path(__file__).parent.parent
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


# Convenience alias
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
