# tests/unit/test_context_injector.py
import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timedelta
from Tools.context_injector import (
    _estimate_tokens,
    _calculate_priority_score,
    get_yesterday_session,
    build_temporal_context,
    build_emotional_context,
    active_projects_context,
    recent_commitments_context,
    relationship_context,
    build_session_context,
    MAX_CONTEXT_TOKENS
)

class TestTokenEstimation:
    def test_estimate_tokens_short_string(self):
        assert _estimate_tokens("test") > 0

    def test_estimate_tokens_proportional(self):
        short = _estimate_tokens("hello")
        long = _estimate_tokens("hello " * 100)
        assert long > short * 50

class TestPriorityScore:
    def test_recent_items_score_higher(self):
        recent = _calculate_priority_score(datetime.now(), heat=0.5)
        old = _calculate_priority_score(datetime.now() - timedelta(days=30), heat=0.5)
        assert recent > old

    def test_high_heat_scores_higher_than_low_heat(self):
        high = _calculate_priority_score(datetime.now() - timedelta(days=7), heat=0.9)
        low = _calculate_priority_score(datetime.now() - timedelta(days=7), heat=0.1)
        assert high > low

class TestYesterdaySession:
    @patch('Tools.context_injector.Path')
    def test_get_yesterday_session_not_found(self, mock_path):
        # Configure chained path operations for sessions_dir.exists()
        mock_sessions_dir = Mock()
        mock_sessions_dir.exists.return_value = False
        mock_path.return_value.parent.parent.__truediv__.return_value = mock_sessions_dir
        result = get_yesterday_session()
        assert result is None

class TestTemporalContext:
    def test_temporal_context_has_header(self):
        result = build_temporal_context()
        assert "## Temporal Context" in result

    def test_temporal_context_has_time(self):
        result = build_temporal_context()
        assert "Current time:" in result

class TestEmotionalContext:
    @patch('Tools.context_injector.get_yesterday_session')
    def test_emotional_context_no_session(self, mock_session):
        mock_session.return_value = None
        result = build_emotional_context()
        assert "Emotional Continuity" in result

class TestSessionContext:
    def test_build_session_context_succeeds(self):
        result = build_session_context()
        assert result is not None
        assert len(result) > 0

    def test_build_session_context_respects_token_budget(self):
        result = build_session_context()
        tokens = _estimate_tokens(result)
        assert tokens <= MAX_CONTEXT_TOKENS

    def test_build_session_context_has_all_sections(self):
        result = build_session_context()
        assert "Temporal Context" in result
        assert "Energy Context" in result
        assert "Emotional Continuity" in result
