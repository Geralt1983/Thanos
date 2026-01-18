#!/usr/bin/env python3
"""
Integration tests for Thanos features:
- Session Opening (Context Injection)
- Data Pulling (WorkOS, Calendar)
- MCP Integration Caching
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from pathlib import Path
import sys

import sys
from unittest.mock import MagicMock

# Mock asyncpg before importing adapters
# This is required because WorkOSAdapter imports asyncpg at module level
mock_asyncpg = MagicMock()
sys.modules["asyncpg"] = mock_asyncpg

# Mock GoogleCalendarAdapter module before import
# This is required because google-auth libs might be missing
mock_gc_module = MagicMock()
sys.modules["Tools.adapters.google_calendar"] = mock_gc_module
# Mock the class inside the module
mock_gc_module.GoogleCalendarAdapter = MagicMock

# Ensure Thanos project is in path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.thanos_orchestrator import ThanosOrchestrator, Agent
from Tools.adapters.base import ToolResult

@pytest.fixture
def orchestrator(tmp_path):
    """Create a ThanosOrchestrator with mocked dependencies."""
    # Create temp state directory and file
    state_dir = tmp_path / "State"
    state_dir.mkdir()
    (state_dir / "Today.md").write_text("Test Focus\nOther content", encoding="utf-8")
    (state_dir / "operator_state.db").touch() # Needed for SQLiteStateStore

    with patch("Tools.thanos_orchestrator.StateReader") as MockStateReader, \
         patch("Tools.thanos_orchestrator.SQLiteStateStore") as MockStateStore, \
         patch("Tools.thanos_orchestrator.SummaryBuilder") as MockSummaryBuilder, \
         patch("Tools.adapters.workos.WorkOSAdapter") as MockWorkOS, \
         patch("Tools.adapters.google_calendar.GoogleCalendarAdapter") as MockCalendar:
        
        # Setup StateReader
        mock_reader = MockStateReader.return_value
        mock_reader.get_current_focus.return_value = "Test Focus"
        mock_reader.get_energy_state.return_value = "High"
        mock_reader.get_blockers.return_value = ["None"]
        mock_reader.get_todays_top3.return_value = ["Task A", "Task B"]
        mock_reader.calculate_elapsed_time.return_value = 3600
        mock_reader.format_elapsed_time.return_value = "1 hour"

        # Setup StateStore
        mock_store = MockStateStore.return_value
        mock_store.get_state.side_effect = lambda k, d=None: {
            "daily_plan": ["Do things"],
            "scoreboard": {"wins": 5},
            "workos_summary": "WorkOS Summary Data",
            "calendar_summary": "Calendar Summary Data"
        }.get(k, d)
        
        # Setup WorkOS Adapter
        mock_workos_instance = MockWorkOS.return_value
        mock_workos_instance.call_tool = AsyncMock()
        mock_workos_instance.call_tool.return_value = ToolResult.ok({
            "active_tasks": [{"id": 1, "title": "Test Task"}],
            "progress": "Good",
            "generated_at": "2024-01-01T12:00:00"
        })

        # Setup Calendar Adapter
        mock_calendar_instance = MockCalendar.return_value
        mock_calendar_instance.is_authenticated.return_value = True
        mock_calendar_instance.call_tool = AsyncMock()
        mock_calendar_instance.call_tool.side_effect = self_calendar_side_effect

        mock_calendar_instance.call_tool.side_effect = self_calendar_side_effect

        orch = ThanosOrchestrator(base_dir=str(tmp_path))
        
        # Manually inject mocked adapters since they are lazy loaded
        orch._workos_adapter = mock_workos_instance
        orch._calendar_adapter = mock_calendar_instance
        
        return orch

def self_calendar_side_effect(tool_name, args):
    """Mock calendar tool calls."""
    if tool_name == "get_today_events":
        return ToolResult.ok({"events": [{"id": "ev1", "summary": "Meeting", "start": {"dateTime": "2024-01-01T10:00:00Z"}}]})
    if tool_name == "generate_calendar_summary":
        return ToolResult.ok({"summary": "Busy day with 1 meeting."})
    return ToolResult.error("Unknown tool")

@pytest.mark.asyncio
class TestSessionOpening:
    """Tests for Session Opening and Context Injection."""

    async def test_system_prompt_construction(self, orchestrator):
        """Verify the system prompt contains all necessary validation contexts."""
        # Setup context file
        orchestrator.context["CORE"] = "Core Identity Data"
        
        # Build prompt
        prompt = orchestrator._build_system_prompt(include_context=True)
        
        # Validation
        assert "You are The Operator" in prompt
        assert "## Temporal Context" in prompt
        assert "Core Identity Data" in prompt
        assert "Test Focus" in prompt  # From StateReader (Today's State)
        assert "WorkOS Summary Data" in prompt # From StateStore
        assert "Calendar Summary Data" in prompt # From StateStore

    async def test_temporal_context(self, orchestrator):
        """Verify temporal context calculation."""
        context = orchestrator._build_time_context()
        assert "Current time:" in context
        assert "Last interaction: 1 hour" in context

@pytest.mark.asyncio
class TestDataPulling:
    """Tests for Data Pulling and Aggregation."""

    async def test_workos_context_fetching(self, orchestrator):
        """Verify WorkOS context is fetched and matches expectation."""
        context = await orchestrator._fetch_workos_context_async(force_refresh=True)
        
        assert context is not None
        assert "active_tasks" in context
        assert context["active_tasks"][0]["title"] == "Test Task"
        orchestrator._workos_adapter.call_tool.assert_called_with("daily_summary", {})

    async def test_calendar_context_fetching(self, orchestrator):
        """Verify Calendar context is fetched and summarized."""
        with patch("Tools.thanos_orchestrator.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 0, 0) # Before meeting
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            context = await orchestrator._fetch_calendar_context_async(force_refresh=True)
            
            assert context is not None
            assert context["summary"] == "Busy day with 1 meeting."
            assert len(context["events"]) == 1
            assert context["next_event"]["summary"] == "Meeting"

@pytest.mark.asyncio
class TestMCPCaching:
    """Tests for MCP Integration Caching."""

    async def test_workos_caching(self, orchestrator):
        """Verify that WorkOS data is cached and not re-fetched within TTL."""
        # First fetch
        await orchestrator._fetch_workos_context_async(force_refresh=True)
        call_count_start = orchestrator._workos_adapter.call_tool.call_count
        
        # Second fetch (should hit cache)
        # Mock time to be within 5 mins
        orchestrator._workos_cache_time = datetime.now()
        await orchestrator._fetch_workos_context_async(force_refresh=False)
        
        call_count_end = orchestrator._workos_adapter.call_tool.call_count
        assert call_count_end == call_count_start

    async def test_calendar_caching(self, orchestrator):
        """Verify that Calendar data is cached and not re-fetched within TTL."""
        # First fetch
        await orchestrator._fetch_calendar_context_async(force_refresh=True)
        call_count_start = orchestrator._calendar_adapter.call_tool.call_count
        
        # Second fetch (should hit cache)
        orchestrator._calendar_cache_time = datetime.now()
        await orchestrator._fetch_calendar_context_async(force_refresh=False)
        
        call_count_end = orchestrator._calendar_adapter.call_tool.call_count
        assert call_count_end == call_count_start

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
