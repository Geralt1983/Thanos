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


from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from ..state_store import SQLiteStateStore

class UsageTracker:
    """Track token usage and costs across all model providers using SQLite."""

    def __init__(self, storage_path: str, pricing: Dict[str, Dict[str, float]]):
        """
        Initialize tracker.
        
        Args:
            storage_path: Path to the SQLite DB (previously JSON path). 
                          If a JSON path is passed, we'll strip the extension 
                          or redirect to operator_state.db in the same dir.
        """
        path_obj = Path(storage_path)
        
        # Retrofit: If passed a .json file, point to operator_state.db in the same directory
        # This handles legacy callers without breaking them immediately
        if path_obj.suffix == '.json':
            self.db_path = path_obj.parent / "operator_state.db"
        else:
            self.db_path = path_obj

        self.store = SQLiteStateStore(self.db_path)
        self.pricing = pricing

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
        
        # Record to SQLite
        self.store.record_turn_log(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            # We don't have these metrics easily available in this signature, default to 0
            tool_call_count=1 if "command" in operation else 0
        )

        return {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "latency_ms": latency_ms,
            "operation": operation
        }

    def get_summary(self, days: int = 30) -> Dict:
        """Get usage summary for the specified number of days."""
        # This is a bit more complex to reconstruct fully from SQLite without writing custom SQL
        # for aggregations. For now, we'll implement a basic aggregation.
        
        import sqlite3
        
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()
        
        summary = {
            "period_days": days,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "total_calls": 0,
            "model_breakdown": {},
            "provider_breakdown": {}
        }
        
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                cursor = conn.cursor()
                
                # Totals
                cursor.execute("""
                    SELECT 
                        COUNT(*), 
                        SUM(input_tokens + output_tokens), 
                        SUM(cost_usd)
                    FROM turn_logs 
                    WHERE timestamp >= ?
                """, (cutoff_str,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    summary["total_calls"] = row[0]
                    summary["total_tokens"] = row[1] or 0
                    summary["total_cost_usd"] = row[2] or 0.0
                
                # Model Breakdown
                cursor.execute("""
                    SELECT 
                        model,
                        COUNT(*),
                        SUM(input_tokens + output_tokens),
                        SUM(cost_usd)
                    FROM turn_logs
                    WHERE timestamp >= ?
                    GROUP BY model
                """, (cutoff_str,))
                
                for row in cursor.fetchall():
                    model = row[0]
                    provider = self._get_provider(model)
                    
                    summary["model_breakdown"][model] = {
                        "calls": row[1],
                        "tokens": row[2],
                        "cost": row[3]
                    }
                    
                    if provider not in summary["provider_breakdown"]:
                        summary["provider_breakdown"][provider] = {"calls": 0, "tokens": 0, "cost": 0.0}
                    
                    summary["provider_breakdown"][provider]["calls"] += row[1]
                    summary["provider_breakdown"][provider]["tokens"] += row[2]
                    summary["provider_breakdown"][provider]["cost"] += row[3]

        except sqlite3.Error as e:
            print(f"Error generating summary: {e}")
            
        return summary

    def get_today(self) -> Dict:
        """Get today's usage stats."""
        import sqlite3
        today_start = datetime.now().strftime("%Y-%m-%d")
        
        stats = {"tokens": 0, "cost": 0.0, "calls": 0}
        
        try:
            with sqlite3.connect(self.store.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*), 
                        SUM(input_tokens + output_tokens), 
                        SUM(cost_usd)
                    FROM turn_logs 
                    WHERE timestamp >= ?
                """, (today_start,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    stats["calls"] = row[0]
                    stats["tokens"] = row[1] or 0
                    stats["cost"] = row[2] or 0.0
        except sqlite3.Error:
            pass
            
        return stats

