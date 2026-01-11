#!/usr/bin/env python3
"""
Usage tracking and cost accounting for LiteLLM client.

This module provides comprehensive tracking of API usage across all model providers,
including token consumption, costs, and performance metrics. Data is persisted to
JSON storage with automatic aggregation by day, model, and provider.

Key Features:
    - Automatic token and cost calculation per model
    - Persistent storage with daily aggregation
    - Model and provider-level breakdowns
    - Historical summaries and trend analysis
    - Configurable pricing tables for cost estimation

Key Classes:
    UsageTracker: Main class for recording and querying usage data

Usage:
    from Tools.litellm.usage_tracker import UsageTracker

    # Initialize tracker with pricing
    tracker = UsageTracker(
        storage_path="State/usage.json",
        pricing={
            "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005}
        }
    )

    # Record API call
    tracker.record(
        model="claude-sonnet-4-20250514",
        input_tokens=150,
        output_tokens=200,
        cost_usd=0.0045,
        latency_ms=1234.5,
        operation="chat"
    )

    # Get summaries
    summary = tracker.get_summary(days=30)  # Last 30 days
    today = tracker.get_today()  # Today's usage

Storage Format:
    The tracker maintains a JSON file with:
    - sessions: Individual API call records (last 1000)
    - daily_totals: Aggregated usage by date
    - model_breakdown: Usage statistics per model
    - provider_breakdown: Usage statistics per provider
    - last_updated: Timestamp of last update

This module is automatically initialized by LiteLLMClient and transparently
tracks all API interactions without requiring explicit calls.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict


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
