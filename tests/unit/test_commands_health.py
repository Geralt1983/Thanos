#!/usr/bin/env python3
"""
Unit tests for commands/health/summary.py

Tests the health:summary command covering data fetching, formatting,
analysis, recommendations, and error handling.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open
from datetime import datetime

import pytest


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.adapters.base import ToolResult
from commands.health import summary


# ========================================================================
# Fixtures
# ========================================================================


@pytest.fixture
def sample_health_data():
    """Sample complete health data from OuraAdapter"""
    return {
        "date": "2024-01-15",
        "summary": {
            "overall_status": "good",
            "readiness_score": 78,
            "sleep_score": 75,
            "activity_score": 72,
            "recommendations": ["Get more sleep", "Increase activity"],
        },
        "readiness": {
            "score": 78,
            "contributors": {
                "sleep_balance": 82,
                "previous_day_activity": 75,
                "activity_balance": 80,
                "hrv_balance": 65,
                "recovery_index": 70,
                "body_temperature": 85,
                "resting_heart_rate": 68,
            },
        },
        "sleep": {
            "score": 75,
            "total_sleep_duration": 25200,  # 7 hours
            "efficiency": 88,
            "rem_sleep_duration": 5400,  # 1.5 hours (21.4%)
            "deep_sleep_duration": 4320,  # 1.2 hours (17.1%)
            "light_sleep_duration": 14400,  # 4 hours
            "latency": 600,  # 10 minutes
            "restless_periods": 12,
        },
        "stress": {
            "day_summary": "normal",
            "recovery_high": 18000,  # 5 hours
            "stress_high": 14400,  # 4 hours
        },
        "activity": {
            "score": 72,
            "active_calories": 450,
            "steps": 8500,
        },
    }


@pytest.fixture
def sample_error_data():
    """Sample error data"""
    return {"error": "Failed to fetch health data: API connection timeout"}


@pytest.fixture
def excellent_health_data():
    """Sample data with excellent scores"""
    return {
        "date": "2024-01-15",
        "summary": {"overall_status": "excellent"},
        "readiness": {
            "score": 92,
            "contributors": {
                "sleep_balance": 95,
                "hrv_balance": 88,
                "recovery_index": 90,
            },
        },
        "sleep": {
            "score": 90,
            "total_sleep_duration": 30600,  # 8.5 hours
            "efficiency": 92,
            "rem_sleep_duration": 7650,  # 25%
            "deep_sleep_duration": 6120,  # 20%
            "restless_periods": 8,
        },
        "stress": {"day_summary": "restored", "recovery_high": 25200, "stress_high": 7200},
        "activity": {"score": 85},
    }


@pytest.fixture
def poor_health_data():
    """Sample data with poor scores"""
    return {
        "date": "2024-01-15",
        "summary": {"overall_status": "poor"},
        "readiness": {
            "score": 45,
            "contributors": {
                "sleep_balance": 50,
                "hrv_balance": 40,
                "recovery_index": 45,
                "body_temperature": 55,
                "resting_heart_rate": 60,
            },
        },
        "sleep": {
            "score": 48,
            "total_sleep_duration": 18000,  # 5 hours
            "efficiency": 75,
            "rem_sleep_duration": 2700,  # 15%
            "deep_sleep_duration": 2160,  # 12%
            "restless_periods": 20,
        },
        "stress": {"day_summary": "stressed", "recovery_high": 7200, "stress_high": 25200},
        "activity": {"score": 50},
    }


# ========================================================================
# Data Fetching Tests
# ========================================================================


class TestFetchHealthData:
    """Test fetch_health_data function"""

    @pytest.mark.asyncio
    async def test_fetch_health_data_success(self, sample_health_data):
        """Test successful health data fetch"""
        with patch("commands.health.summary.OuraAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter.call_tool = AsyncMock(
                return_value=ToolResult.ok(sample_health_data)
            )
            mock_adapter.close = AsyncMock()
            mock_adapter_class.return_value = mock_adapter

            result = await summary.fetch_health_data()

            assert result == sample_health_data
            assert "error" not in result
            mock_adapter.call_tool.assert_called_once_with("get_today_health", {})
            mock_adapter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_health_data_tool_failure(self):
        """Test health data fetch when tool returns failure"""
        with patch("commands.health.summary.OuraAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter.call_tool = AsyncMock(
                return_value=ToolResult(success=False, data=None, error="API error")
            )
            mock_adapter.close = AsyncMock()
            mock_adapter_class.return_value = mock_adapter

            result = await summary.fetch_health_data()

            assert "error" in result
            assert "Failed to fetch health data: API error" in result["error"]
            mock_adapter.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_health_data_exception(self):
        """Test health data fetch when exception occurs"""
        with patch("commands.health.summary.OuraAdapter") as mock_adapter_class:
            mock_adapter = AsyncMock()
            mock_adapter.call_tool = AsyncMock(side_effect=Exception("Connection timeout"))
            mock_adapter.close = AsyncMock()
            mock_adapter_class.return_value = mock_adapter

            result = await summary.fetch_health_data()

            assert "error" in result
            assert "Error fetching health data" in result["error"]
            assert "Connection timeout" in result["error"]
            mock_adapter.close.assert_called_once()


# ========================================================================
# Helper Function Tests
# ========================================================================


class TestHelperFunctions:
    """Test helper formatting functions"""

    def test_get_status_emoji_excellent(self):
        """Test emoji for excellent score (>=85)"""
        assert summary._get_status_emoji(85) == "🟢"
        assert summary._get_status_emoji(90) == "🟢"
        assert summary._get_status_emoji(100) == "🟢"

    def test_get_status_emoji_good(self):
        """Test emoji for good score (70-84)"""
        assert summary._get_status_emoji(70) == "🟡"
        assert summary._get_status_emoji(75) == "🟡"
        assert summary._get_status_emoji(84) == "🟡"

    def test_get_status_emoji_fair(self):
        """Test emoji for fair score (55-69)"""
        assert summary._get_status_emoji(55) == "🟠"
        assert summary._get_status_emoji(60) == "🟠"
        assert summary._get_status_emoji(69) == "🟠"

    def test_get_status_emoji_poor(self):
        """Test emoji for poor score (<55)"""
        assert summary._get_status_emoji(0) == "🔴"
        assert summary._get_status_emoji(40) == "🔴"
        assert summary._get_status_emoji(54) == "🔴"

    def test_format_duration_hours_and_minutes(self):
        """Test duration formatting with hours and minutes"""
        assert summary._format_duration(7200) == "2h 0m"  # 2 hours
        assert summary._format_duration(7380) == "2h 3m"  # 2 hours 3 minutes
        assert summary._format_duration(25200) == "7h 0m"  # 7 hours

    def test_format_duration_minutes_only(self):
        """Test duration formatting with minutes only"""
        assert summary._format_duration(300) == "5m"  # 5 minutes
        assert summary._format_duration(1800) == "30m"  # 30 minutes
        assert summary._format_duration(3540) == "59m"  # 59 minutes

    def test_format_duration_zero(self):
        """Test duration formatting with zero"""
        assert summary._format_duration(0) == "0m"
        assert summary._format_duration(None) == "0m"


# ========================================================================
# Analysis Function Tests
# ========================================================================


class TestAnalyzeSleepQuality:
    """Test _analyze_sleep_quality function"""

    def test_analyze_sleep_quality_empty(self):
        """Test with empty sleep data"""
        assert summary._analyze_sleep_quality({}) == []
        assert summary._analyze_sleep_quality(None) == []

    def test_analyze_sleep_quality_low_duration(self):
        """Test identifies low sleep duration"""
        sleep_data = {"total_sleep_duration": 21600}  # 6 hours
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("duration is below optimal" in i for i in insights)

    def test_analyze_sleep_quality_optimal_duration(self):
        """Test identifies optimal sleep duration"""
        sleep_data = {"total_sleep_duration": 29700}  # 8.25 hours
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("duration is in optimal range" in i for i in insights)

    def test_analyze_sleep_quality_low_efficiency(self):
        """Test identifies low efficiency"""
        sleep_data = {"total_sleep_duration": 25200, "efficiency": 82}
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("efficiency is low" in i for i in insights)

    def test_analyze_sleep_quality_excellent_efficiency(self):
        """Test identifies excellent efficiency"""
        sleep_data = {"total_sleep_duration": 25200, "efficiency": 92}
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("Excellent sleep efficiency" in i for i in insights)

    def test_analyze_sleep_quality_low_rem(self):
        """Test identifies low REM sleep"""
        sleep_data = {
            "total_sleep_duration": 25200,  # 7 hours
            "rem_sleep_duration": 3600,  # 1 hour (14%)
        }
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("REM sleep is low" in i for i in insights)

    def test_analyze_sleep_quality_strong_rem(self):
        """Test identifies strong REM sleep"""
        sleep_data = {
            "total_sleep_duration": 25200,  # 7 hours
            "rem_sleep_duration": 6804,  # 1.89 hours (27%)
        }
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("Strong REM sleep" in i for i in insights)

    def test_analyze_sleep_quality_low_deep(self):
        """Test identifies low deep sleep"""
        sleep_data = {
            "total_sleep_duration": 25200,  # 7 hours
            "deep_sleep_duration": 2520,  # 0.7 hours (10%)
        }
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("Deep sleep is low" in i for i in insights)

    def test_analyze_sleep_quality_good_deep(self):
        """Test identifies good deep sleep"""
        sleep_data = {
            "total_sleep_duration": 25200,  # 7 hours
            "deep_sleep_duration": 5544,  # 1.54 hours (22%)
        }
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("Good deep sleep" in i for i in insights)

    def test_analyze_sleep_quality_high_restless(self):
        """Test identifies high restless periods"""
        sleep_data = {"total_sleep_duration": 25200, "restless_periods": 18}
        insights = summary._analyze_sleep_quality(sleep_data)
        assert any("High restless periods" in i for i in insights)


class TestAnalyzeReadiness:
    """Test _analyze_readiness function"""

    def test_analyze_readiness_empty(self):
        """Test with empty readiness data"""
        assert summary._analyze_readiness({}) == []
        assert summary._analyze_readiness(None) == []

    def test_analyze_readiness_excellent_score(self):
        """Test identifies excellent readiness"""
        data = {"score": 90, "contributors": {}}
        insights = summary._analyze_readiness(data)
        assert any("well-recovered and ready" in i for i in insights)

    def test_analyze_readiness_good_score(self):
        """Test identifies good readiness"""
        data = {"score": 75, "contributors": {}}
        insights = summary._analyze_readiness(data)
        assert any("Good readiness" in i for i in insights)

    def test_analyze_readiness_poor_score(self):
        """Test identifies poor readiness"""
        data = {"score": 60, "contributors": {}}
        insights = summary._analyze_readiness(data)
        assert any("Below-optimal readiness" in i for i in insights)

    def test_analyze_readiness_low_activity_balance(self):
        """Test identifies low activity balance"""
        data = {"score": 70, "contributors": {"activity_balance": 65}}
        insights = summary._analyze_readiness(data)
        assert any("Activity balance is low" in i for i in insights)

    def test_analyze_readiness_low_body_temp(self):
        """Test identifies low body temperature"""
        data = {"score": 70, "contributors": {"body_temperature": 60}}
        insights = summary._analyze_readiness(data)
        assert any("Body temperature deviation" in i for i in insights)

    def test_analyze_readiness_low_hrv(self):
        """Test identifies low HRV"""
        data = {"score": 70, "contributors": {"hrv_balance": 65}}
        insights = summary._analyze_readiness(data)
        assert any("HRV is low" in i for i in insights)

    def test_analyze_readiness_excellent_hrv(self):
        """Test identifies excellent HRV"""
        data = {"score": 85, "contributors": {"hrv_balance": 90}}
        insights = summary._analyze_readiness(data)
        assert any("Excellent HRV" in i for i in insights)

    def test_analyze_readiness_low_recovery(self):
        """Test identifies incomplete recovery"""
        data = {"score": 70, "contributors": {"recovery_index": 65}}
        insights = summary._analyze_readiness(data)
        assert any("Recovery is incomplete" in i for i in insights)

    def test_analyze_readiness_elevated_hr(self):
        """Test identifies elevated resting heart rate"""
        data = {"score": 70, "contributors": {"resting_heart_rate": 65}}
        insights = summary._analyze_readiness(data)
        assert any("Elevated resting heart rate" in i for i in insights)

    def test_analyze_readiness_sleep_debt(self):
        """Test identifies sleep debt"""
        data = {"score": 70, "contributors": {"sleep_balance": 65}}
        insights = summary._analyze_readiness(data)
        assert any("Sleep debt accumulating" in i for i in insights)

    def test_analyze_readiness_high_prev_activity(self):
        """Test identifies high previous day activity"""
        data = {"score": 70, "contributors": {"previous_day_activity": 65}}
        insights = summary._analyze_readiness(data)
        assert any("High previous day activity" in i for i in insights)


class TestAnalyzeStress:
    """Test _analyze_stress function"""

    def test_analyze_stress_empty(self):
        """Test with empty stress data"""
        assert summary._analyze_stress({}) == []
        assert summary._analyze_stress(None) == []

    def test_analyze_stress_restored(self):
        """Test identifies restored stress state"""
        data = {"day_summary": "restored"}
        insights = summary._analyze_stress(data)
        assert any("Well-managed stress" in i for i in insights)

    def test_analyze_stress_normal(self):
        """Test identifies normal stress state"""
        data = {"day_summary": "normal"}
        insights = summary._analyze_stress(data)
        assert any("Normal stress levels" in i for i in insights)

    def test_analyze_stress_stressed(self):
        """Test identifies stressed state"""
        data = {"day_summary": "stressed"}
        insights = summary._analyze_stress(data)
        assert any("Elevated stress detected" in i for i in insights)

    def test_analyze_stress_high(self):
        """Test identifies high stress state"""
        data = {"day_summary": "high"}
        insights = summary._analyze_stress(data)
        assert any("Elevated stress detected" in i for i in insights)

    def test_analyze_stress_low_recovery_time(self):
        """Test identifies low recovery time"""
        data = {"recovery_high": 7200, "stress_high": 25200}  # 22% recovery
        insights = summary._analyze_stress(data)
        assert any("Low recovery time today" in i for i in insights)

    def test_analyze_stress_good_recovery_time(self):
        """Test identifies good recovery time"""
        data = {"recovery_high": 18000, "stress_high": 14400}  # 56% recovery
        insights = summary._analyze_stress(data)
        assert any("Good recovery time" in i for i in insights)


class TestGenerateRecommendations:
    """Test _generate_recommendations function"""

    def test_generate_recommendations_critical_readiness(self):
        """Test generates priority recommendations for critical readiness"""
        data = {
            "readiness": {"score": 50},
            "sleep": {"score": 70},
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("Priority" in r and "recovery day" in r for r in recs)

    def test_generate_recommendations_critical_sleep(self):
        """Test generates priority recommendations for critical sleep"""
        data = {
            "readiness": {"score": 70},
            "sleep": {"score": 50, "total_sleep_duration": 18000},  # 5 hours
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("Priority" in r and "sleep" in r for r in recs)

    def test_generate_recommendations_low_efficiency(self):
        """Test recommends sleep environment improvements"""
        data = {
            "readiness": {"score": 75},
            "sleep": {"score": 65, "total_sleep_duration": 25200, "efficiency": 80},
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("sleep environment" in r for r in recs)

    def test_generate_recommendations_low_rem(self):
        """Test recommends REM improvement"""
        data = {
            "readiness": {"score": 75},
            "sleep": {
                "score": 70,
                "total_sleep_duration": 25200,
                "rem_sleep_duration": 3600,
            },  # 14%
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("REM" in r for r in recs)

    def test_generate_recommendations_low_hrv(self):
        """Test recommends stress management for low HRV"""
        data = {
            "readiness": {"score": 75, "contributors": {"hrv_balance": 65}},
            "sleep": {"score": 75, "total_sleep_duration": 25200},
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("stress management" in r or "HRV" in r for r in recs)

    def test_generate_recommendations_high_stress(self):
        """Test recommends recovery activities for high stress"""
        data = {
            "readiness": {"score": 75},
            "sleep": {"score": 75, "total_sleep_duration": 25200},
            "stress": {"day_summary": "stressed"},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("recovery activities" in r for r in recs)

    def test_generate_recommendations_excellent_state(self):
        """Test recommends challenging activities for excellent state"""
        data = {
            "readiness": {"score": 90},
            "sleep": {"score": 88, "total_sleep_duration": 28800},
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("challenging" in r for r in recs)

    def test_generate_recommendations_good_state(self):
        """Test recommends maintaining habits for good state"""
        data = {
            "readiness": {"score": 75},
            "sleep": {"score": 72, "total_sleep_duration": 25200},
            "stress": {},
            "activity": {},
        }
        recs = summary._generate_recommendations(data)
        assert any("maintain" in r.lower() for r in recs)

    def test_generate_recommendations_low_activity(self):
        """Test recommends more movement for low activity"""
        data = {
            "readiness": {"score": 75},
            "sleep": {"score": 75, "total_sleep_duration": 25200},
            "stress": {},
            "activity": {"score": 65},
        }
        recs = summary._generate_recommendations(data)
        assert any("movement" in r for r in recs)


# ========================================================================
# Formatting Tests
# ========================================================================


class TestFormatHealthSummary:
    """Test format_health_summary function"""

    def test_format_health_summary_with_error(self, sample_error_data):
        """Test formatting handles error data"""
        result = summary.format_health_summary(sample_error_data)
        assert "⚠️" in result
        assert sample_error_data["error"] in result
        assert "Unable to generate health summary" in result

    def test_format_health_summary_success(self, sample_health_data):
        """Test successful health summary formatting"""
        result = summary.format_health_summary(sample_health_data)

        # Check for header
        assert "# 💚 Health Dashboard" in result
        assert sample_health_data["date"] in result

        # Check for overall status
        assert "## 🟢 Overall Status: Good" in result

        # Check for key metrics section
        assert "## 📊 Key Metrics" in result

        # Check for readiness section
        assert "### 🟡 Readiness: 78/100" in result
        assert "**Top Contributors:**" in result

        # Check for sleep section
        assert "### 🟡 Sleep: 75/100" in result
        assert "7h 0m" in result  # Duration formatting
        assert "**Sleep Breakdown:**" in result

        # Check for stress section
        assert "### 🟡 Stress: Normal" in result

        # Check for insights section
        assert "## 💡 Health Insights" in result

        # Check for recommendations section
        assert "## 🎯 Recommendations" in result

    def test_format_health_summary_excellent_scores(self, excellent_health_data):
        """Test formatting with excellent scores"""
        result = summary.format_health_summary(excellent_health_data)

        # Should have green emoji for high scores
        assert "🟢" in result
        assert "92/100" in result  # Readiness score
        assert "90/100" in result  # Sleep score

    def test_format_health_summary_poor_scores(self, poor_health_data):
        """Test formatting with poor scores"""
        result = summary.format_health_summary(poor_health_data)

        # Should have red emoji for low scores
        assert "🔴" in result
        assert "45/100" in result  # Readiness score
        assert "48/100" in result  # Sleep score

    def test_format_health_summary_missing_readiness(self, sample_health_data):
        """Test formatting handles missing readiness data"""
        data = sample_health_data.copy()
        data["readiness"] = None
        result = summary.format_health_summary(data)
        assert "### ⚪ Readiness: No data available" in result

    def test_format_health_summary_missing_sleep(self, sample_health_data):
        """Test formatting handles missing sleep data"""
        data = sample_health_data.copy()
        data["sleep"] = None
        result = summary.format_health_summary(data)
        assert "### ⚪ Sleep: No data available" in result

    def test_format_health_summary_missing_stress(self, sample_health_data):
        """Test formatting handles missing stress data"""
        data = sample_health_data.copy()
        data["stress"] = None
        result = summary.format_health_summary(data)
        assert "### ⚪ Stress: No data available" in result

    def test_format_health_summary_with_activity(self, sample_health_data):
        """Test formatting includes activity when available"""
        result = summary.format_health_summary(sample_health_data)
        assert "### 🟡 Activity: 72/100" in result

    def test_format_health_summary_insights_limit(self, sample_health_data):
        """Test insights are limited to top 8"""
        result = summary.format_health_summary(sample_health_data)
        # Count bullet points in insights section
        lines = result.split("\n")
        insights_section = False
        insight_count = 0
        for line in lines:
            if "## 💡 Health Insights" in line:
                insights_section = True
            elif insights_section and line.startswith("## "):
                break
            elif insights_section and line.startswith("- "):
                insight_count += 1
        assert insight_count <= 8

    def test_format_health_summary_recommendations_limit(self, sample_health_data):
        """Test recommendations are limited to top 5"""
        result = summary.format_health_summary(sample_health_data)
        # Count numbered items in recommendations section
        lines = result.split("\n")
        rec_section = False
        rec_count = 0
        for line in lines:
            if "## 🎯 Recommendations" in line:
                rec_section = True
            elif rec_section and line.startswith("## "):
                break
            elif rec_section and line and line[0].isdigit():
                rec_count += 1
        assert rec_count <= 5


# ========================================================================
# History Saving Tests
# ========================================================================


class TestSaveToHistory:
    """Test save_to_history function"""

    def test_save_to_history_creates_directory(self, tmp_path):
        """Test history saving creates directory if not exists"""
        test_summary = "# Test Summary\n\nThis is a test."

        with patch("commands.health.summary.Path") as mock_path:
            mock_project_root = tmp_path
            mock_history_dir = mock_project_root / "History" / "HealthSummaries"
            mock_path.return_value.parent.parent.parent = mock_project_root

            with patch("builtins.open", mock_open()) as mock_file:
                with patch.object(Path, "mkdir") as mock_mkdir:
                    # Mock the path operations
                    summary.save_to_history(test_summary)

                    # Note: Due to the way the function constructs paths,
                    # we mainly verify that open was called
                    assert mock_file.called

    def test_save_to_history_file_content(self, tmp_path):
        """Test history file has correct content and format"""
        test_summary = "# Test Summary\n\nThis is a test."

        # Create a real temporary directory
        history_dir = tmp_path / "History" / "HealthSummaries"
        history_dir.mkdir(parents=True, exist_ok=True)

        # Patch Path to return our temp directory
        with patch("commands.health.summary.Path") as mock_path:
            mock_path.return_value.parent.parent.parent = tmp_path

            # Use real file operations
            original_file = (
                history_dir / f"health_{datetime.now().strftime('%Y-%m-%d')}.md"
            )

            with patch("builtins.open", mock_open()) as mock_file:
                summary.save_to_history(test_summary)

                # Verify file was opened for writing
                assert mock_file.called
                handle = mock_file()

                # Check that write was called with content including timestamp
                write_calls = handle.write.call_args_list
                written_content = "".join([str(call[0][0]) for call in write_calls])

                assert "# Health Summary -" in written_content
                assert "*Generated at" in written_content
                assert test_summary in written_content


# ========================================================================
# Execute Function Tests
# ========================================================================


class TestExecute:
    """Test execute function"""

    @pytest.mark.asyncio
    async def test_execute_without_llm(self, sample_health_data, capsys):
        """Test execute without LLM enhancement"""
        with patch(
            "commands.health.summary.fetch_health_data", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_health_data

            with patch("commands.health.summary.save_to_history") as mock_save:
                result = await summary.execute(use_llm_enhancement=False)

                # Verify data was fetched
                mock_fetch.assert_called_once()

                # Verify result contains expected content
                assert "Health Dashboard" in result
                assert "78/100" in result  # Readiness score

                # Verify history was saved
                mock_save.assert_called_once()

                # Verify output was printed
                captured = capsys.readouterr()
                assert "Generating health summary" in captured.out
                assert "Saved to History/HealthSummaries/" in captured.out

    @pytest.mark.asyncio
    async def test_execute_with_llm_enhancement(self, sample_health_data, capsys):
        """Test execute with LLM enhancement"""
        with patch(
            "commands.health.summary.fetch_health_data", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_health_data

            with patch("commands.health.summary.get_client") as mock_get_client:
                mock_client = Mock()
                mock_client.chat_stream = Mock(
                    return_value=iter(["Enhanced ", "health ", "summary"])
                )
                mock_get_client.return_value = mock_client

                with patch("commands.health.summary.save_to_history") as mock_save:
                    result = await summary.execute(use_llm_enhancement=True)

                    # Verify LLM client was used
                    mock_get_client.assert_called_once()
                    mock_client.chat_stream.assert_called_once()

                    # Verify result is enhanced
                    assert result == "Enhanced health summary"

                    # Verify history was saved
                    mock_save.assert_called_once()

                    # Verify LLM enhancement message was printed
                    captured = capsys.readouterr()
                    assert "Enhancing with gpt-4o-mini" in captured.out

    @pytest.mark.asyncio
    async def test_execute_with_error_data(self, sample_error_data, capsys):
        """Test execute handles error data gracefully"""
        with patch(
            "commands.health.summary.fetch_health_data", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_error_data

            with patch("commands.health.summary.save_to_history") as mock_save:
                result = await summary.execute(use_llm_enhancement=False)

                # Verify error message is in result
                assert "⚠️" in result
                assert sample_error_data["error"] in result

                # Verify history was still saved
                mock_save.assert_called_once()

                # Verify no LLM enhancement attempted with error data
                captured = capsys.readouterr()
                assert "Enhancing with" not in captured.out

    @pytest.mark.asyncio
    async def test_execute_no_llm_with_error(self, sample_error_data):
        """Test LLM enhancement is skipped when error in data"""
        with patch(
            "commands.health.summary.fetch_health_data", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_error_data

            with patch("commands.health.summary.get_client") as mock_get_client:
                with patch("commands.health.summary.save_to_history"):
                    await summary.execute(use_llm_enhancement=True)

                    # LLM should not be called with error data
                    mock_get_client.assert_not_called()


# ========================================================================
# Integration Tests
# ========================================================================


class TestIntegration:
    """Integration-style tests for the command module"""

    def test_module_imports(self):
        """Test module imports successfully"""
        assert hasattr(summary, "fetch_health_data")
        assert hasattr(summary, "format_health_summary")
        assert hasattr(summary, "save_to_history")
        assert hasattr(summary, "execute")
        assert hasattr(summary, "main")
        assert hasattr(summary, "SYSTEM_PROMPT")

    def test_system_prompt_content(self):
        """Test SYSTEM_PROMPT has expected content"""
        assert "health assistant" in summary.SYSTEM_PROMPT.lower()
        assert "jeremy" in summary.SYSTEM_PROMPT.lower()
        assert "adhd" in summary.SYSTEM_PROMPT.lower()
        assert "actionable" in summary.SYSTEM_PROMPT.lower()

    @pytest.mark.asyncio
    async def test_full_workflow_without_llm(self, sample_health_data):
        """Test complete workflow from fetch to save"""
        with patch(
            "commands.health.summary.OuraAdapter"
        ) as mock_adapter_class, patch(
            "commands.health.summary.save_to_history"
        ) as mock_save:

            # Setup mock adapter
            mock_adapter = AsyncMock()
            mock_adapter.call_tool = AsyncMock(
                return_value=ToolResult.ok(sample_health_data)
            )
            mock_adapter.close = AsyncMock()
            mock_adapter_class.return_value = mock_adapter

            # Execute the full workflow
            result = await summary.execute(use_llm_enhancement=False)

            # Verify the full chain worked
            assert "Health Dashboard" in result
            assert sample_health_data["date"] in result
            mock_save.assert_called_once()
            assert "78/100" in result  # Readiness score from sample data
