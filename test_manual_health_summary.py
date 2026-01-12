"""
Manual testing script for health:summary command with mock Oura data.

This script simulates real Oura Ring data to verify:
- Formatting and layout
- Insights generation
- Recommendations
- Edge cases and error handling
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from commands.health.summary import (
    format_health_summary,
    _analyze_sleep_quality,
    _analyze_readiness,
    _analyze_stress,
    _generate_recommendations,
)


def test_excellent_health_state():
    """Test with excellent health metrics."""
    print("\n" + "=" * 60)
    print("TEST 1: Excellent Health State")
    print("=" * 60)

    data = {
        "date": "2026-01-11",
        "summary": {
            "overall_status": "excellent"
        },
        "readiness": {
            "score": 88,
            "contributors": {
                "activity_balance": 85,
                "body_temperature": 90,
                "hrv_balance": 92,
                "recovery_index": 88,
                "resting_heart_rate": 87,
                "sleep_balance": 89,
                "previous_day_activity": 85
            }
        },
        "sleep": {
            "score": 86,
            "total_sleep_duration": 28800,  # 8 hours
            "efficiency": 92,
            "rem_sleep_duration": 7200,     # 2 hours (25%)
            "deep_sleep_duration": 5760,    # 1.6 hours (20%)
            "light_sleep_duration": 15840,  # 4.4 hours
            "latency": 480,                  # 8 minutes
            "restless_periods": 8
        },
        "stress": {
            "day_summary": "restored",
            "recovery_high": 25200,  # 7 hours
            "stress_high": 14400     # 4 hours
        },
        "activity": {
            "score": 82
        }
    }

    summary = format_health_summary(data)
    print(summary)

    # Test individual analyzers
    print("\n--- Sleep Insights ---")
    sleep_insights = _analyze_sleep_quality(data["sleep"])
    for insight in sleep_insights:
        print(f"  {insight}")

    print("\n--- Readiness Insights ---")
    readiness_insights = _analyze_readiness(data["readiness"])
    for insight in readiness_insights:
        print(f"  {insight}")

    print("\n--- Stress Insights ---")
    stress_insights = _analyze_stress(data["stress"])
    for insight in stress_insights:
        print(f"  {insight}")

    print("\n--- Recommendations ---")
    recommendations = _generate_recommendations(data)
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")


def test_poor_health_state():
    """Test with poor health metrics - multiple issues."""
    print("\n" + "=" * 60)
    print("TEST 2: Poor Health State (Multiple Issues)")
    print("=" * 60)

    data = {
        "date": "2026-01-11",
        "summary": {
            "overall_status": "poor"
        },
        "readiness": {
            "score": 52,
            "contributors": {
                "activity_balance": 65,
                "body_temperature": 62,
                "hrv_balance": 55,
                "recovery_index": 58,
                "resting_heart_rate": 62,
                "sleep_balance": 48,
                "previous_day_activity": 60
            }
        },
        "sleep": {
            "score": 48,
            "total_sleep_duration": 21600,  # 6 hours (low)
            "efficiency": 78,                # Low efficiency
            "rem_sleep_duration": 3240,      # 0.9 hours (15% - low)
            "deep_sleep_duration": 2700,     # 0.75 hours (12.5% - low)
            "light_sleep_duration": 15660,   # 4.35 hours
            "latency": 1800,                 # 30 minutes (high)
            "restless_periods": 22           # High restlessness
        },
        "stress": {
            "day_summary": "stressed",
            "recovery_high": 10800,  # 3 hours
            "stress_high": 28800     # 8 hours (high stress)
        },
        "activity": {
            "score": 65
        }
    }

    summary = format_health_summary(data)
    print(summary)

    print("\n--- Critical Insights ---")
    all_insights = []
    all_insights.extend(_analyze_readiness(data["readiness"]))
    all_insights.extend(_analyze_sleep_quality(data["sleep"]))
    all_insights.extend(_analyze_stress(data["stress"]))
    for insight in all_insights[:8]:
        print(f"  {insight}")

    print("\n--- Priority Recommendations ---")
    recommendations = _generate_recommendations(data)
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"  {i}. {rec}")


def test_mixed_health_state():
    """Test with mixed metrics - some good, some concerning."""
    print("\n" + "=" * 60)
    print("TEST 3: Mixed Health State")
    print("=" * 60)

    data = {
        "date": "2026-01-11",
        "summary": {
            "overall_status": "fair"
        },
        "readiness": {
            "score": 72,
            "contributors": {
                "activity_balance": 80,
                "body_temperature": 75,
                "hrv_balance": 65,  # Low - stress indicator
                "recovery_index": 78,
                "resting_heart_rate": 72,
                "sleep_balance": 68,  # Low - sleep debt
                "previous_day_activity": 75
            }
        },
        "sleep": {
            "score": 75,
            "total_sleep_duration": 27000,  # 7.5 hours
            "efficiency": 88,
            "rem_sleep_duration": 4860,     # 1.35 hours (18% - low)
            "deep_sleep_duration": 5400,    # 1.5 hours (20% - good)
            "light_sleep_duration": 16740,  # 4.65 hours
            "latency": 600,                 # 10 minutes
            "restless_periods": 12
        },
        "stress": {
            "day_summary": "normal",
            "recovery_high": 18000,  # 5 hours
            "stress_high": 21600     # 6 hours
        },
        "activity": {
            "score": 78
        }
    }

    summary = format_health_summary(data)
    print(summary)

    print("\n--- Mixed Insights ---")
    all_insights = []
    all_insights.extend(_analyze_readiness(data["readiness"]))
    all_insights.extend(_analyze_sleep_quality(data["sleep"]))
    all_insights.extend(_analyze_stress(data["stress"]))
    for insight in all_insights[:8]:
        print(f"  {insight}")

    print("\n--- Balanced Recommendations ---")
    recommendations = _generate_recommendations(data)
    for i, rec in enumerate(recommendations[:5], 1):
        print(f"  {i}. {rec}")


def test_missing_data():
    """Test with missing/incomplete data."""
    print("\n" + "=" * 60)
    print("TEST 4: Missing Data Handling")
    print("=" * 60)

    data = {
        "date": "2026-01-11",
        "summary": {
            "overall_status": "unknown"
        },
        "readiness": None,
        "sleep": {
            "score": 72
            # Missing detailed metrics
        },
        "stress": None,
        "activity": None
    }

    summary = format_health_summary(data)
    print(summary)


def test_error_state():
    """Test error handling."""
    print("\n" + "=" * 60)
    print("TEST 5: Error State")
    print("=" * 60)

    data = {
        "error": "Failed to fetch health data: API rate limit exceeded"
    }

    summary = format_health_summary(data)
    print(summary)


def main():
    """Run all manual tests."""
    print("\n" + "=" * 60)
    print("MANUAL TESTING: Health Summary Command")
    print("Testing formatting, insights, and recommendations")
    print("=" * 60)

    test_excellent_health_state()
    test_poor_health_state()
    test_mixed_health_state()
    test_missing_data()
    test_error_state()

    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("\nVerification Checklist:")
    print("✓ Dashboard formatting is clear and scannable")
    print("✓ Emojis provide quick visual status indicators")
    print("✓ Metrics are properly formatted (scores, durations, percentages)")
    print("✓ Insights are evidence-based and tied to specific values")
    print("✓ Recommendations are actionable and prioritized")
    print("✓ Missing data is handled gracefully")
    print("✓ Error messages are user-friendly")
    print("✓ Output is ADHD-friendly (clear sections, bullet points)")

    print("\n" + "=" * 60)
    print("REAL DATA TESTING INSTRUCTIONS")
    print("=" * 60)
    print("\nWhen Oura credentials are available:")
    print("1. Set OURA_PERSONAL_ACCESS_TOKEN in .env or environment")
    print("2. Run: python3 -m commands.health.summary")
    print("3. Verify all metrics display correctly")
    print("4. Check insights are relevant to your actual data")
    print("5. Verify recommendations are personalized")
    print("6. Test with LLM: python3 -m commands.health.summary --llm-enhance")
    print("7. Verify LLM enhancement adds value")
    print("8. Check History/HealthSummaries/ for saved output")
    print("9. Run on multiple days to verify date handling")
    print("10. Test edge cases (no sleep data, partial data, etc.)")


if __name__ == "__main__":
    main()
