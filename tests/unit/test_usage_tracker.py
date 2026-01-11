"""
Unit tests for the UsageTracker class.
Tests usage tracking, cost calculation, and statistics aggregation.
"""
import json
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Tools.litellm import UsageTracker


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for test files."""
    return tmp_path


# ============================================================================
# UsageTracker Tests
# ============================================================================

class TestUsageTracker:
    """Tests for the UsageTracker class."""

    def test_init_creates_storage_file(self, temp_dir):
        """UsageTracker should create storage file on initialization."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}

        tracker = UsageTracker(str(storage_path), pricing)

        assert storage_path.exists()
        data = json.loads(storage_path.read_text())
        assert "sessions" in data
        assert "daily_totals" in data

    def test_calculate_cost(self, temp_dir):
        """calculate_cost should compute correct costs based on pricing."""
        storage_path = temp_dir / "usage.json"
        pricing = {
            "claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}
        }
        tracker = UsageTracker(str(storage_path), pricing)

        # 1000 input tokens = $0.015, 1000 output tokens = $0.075
        cost = tracker.calculate_cost("claude-opus-4-5-20251101", 1000, 1000)
        assert cost == pytest.approx(0.09)

    def test_record_updates_storage(self, temp_dir):
        """record should update storage with usage data."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        tracker.record(
            model="claude-opus-4-5-20251101",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.0225,
            latency_ms=1500,
            operation="test"
        )

        data = json.loads(storage_path.read_text())
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["input_tokens"] == 500
        assert data["sessions"][0]["output_tokens"] == 200

    def test_get_today_returns_daily_stats(self, temp_dir):
        """get_today should return today's usage statistics."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        tracker.record("claude-opus-4-5-20251101", 100, 50, 0.01, 1000)
        tracker.record("claude-opus-4-5-20251101", 200, 100, 0.02, 1200)

        today = tracker.get_today()
        assert today["tokens"] == 450  # (100+50) + (200+100)
        assert today["calls"] == 2

    def test_get_summary_aggregates_correctly(self, temp_dir):
        """get_summary should aggregate usage over the specified period."""
        storage_path = temp_dir / "usage.json"
        pricing = {"claude-opus-4-5-20251101": {"input": 0.015, "output": 0.075}}
        tracker = UsageTracker(str(storage_path), pricing)

        # Record some usage
        tracker.record("claude-opus-4-5-20251101", 1000, 500, 0.05, 1500)

        summary = tracker.get_summary(30)
        assert summary["total_tokens"] == 1500
        assert summary["total_calls"] == 1
        assert "projected_monthly_cost" in summary

    def test_provider_detection(self, temp_dir):
        """_get_provider should correctly identify providers from model names."""
        storage_path = temp_dir / "usage.json"
        pricing = {}
        tracker = UsageTracker(str(storage_path), pricing)

        assert tracker._get_provider("claude-opus-4-5-20251101") == "anthropic"
        assert tracker._get_provider("gpt-4o") == "openai"
        assert tracker._get_provider("gemini-pro") == "google"
        assert tracker._get_provider("unknown-model") == "unknown"
