"""
Health: Summary Command

Generates a comprehensive health metrics dashboard combining Oura Ring data
(readiness, sleep, stress) into a unified health snapshot.

Usage:
    python -m commands.health.summary [--llm-enhance] [--trends]

Flags:
    --llm-enhance: Use LLM to provide personalized insights
    --trends: Include 7-day trend analysis

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime, timedelta
from pathlib import Path
import sys
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.adapters.oura import OuraAdapter
from Tools.litellm_client import get_client
from Tools.output_formatter import format_header, format_list, is_mobile, wrap_text
from Tools.health.hrv_baseline import detect_deviation


# System prompt for health summary persona (used for optional LLM enhancement)
SYSTEM_PROMPT = """You are Jeremy's health assistant providing his daily health summary.

Your role:
- Present health metrics clearly and actionably
- Identify patterns and correlations between metrics
- Provide evidence-based recommendations
- Be direct and supportive, not alarmist
- Focus on actionable insights

You know Jeremy:
- Epic consultant with ADHD - needs clear, scannable information
- Values data-driven decisions and stoic philosophy
- Active lifestyle, prioritizes sleep and recovery
- Partner Ashley, baby Sullivan (9 months) - sleep can be challenging
- Target: 15-20 billable hours/week, needs optimal energy

Output format:
- Use markdown
- Start with overall health status
- Present key metrics (readiness, sleep, stress)
- Highlight notable patterns or changes
- Provide 2-3 actionable recommendations
- Keep it scannable (bullet points, clear sections)
"""


async def fetch_health_data() -> dict:
    """
    Fetch health metrics from Oura Ring.

    Returns:
        Dictionary with readiness, sleep, stress, and summary data.
        Returns empty dict with error key if fetch fails.
    """
    try:
        adapter = OuraAdapter()
        result = await adapter.call_tool("get_today_health", {})

        if result.success:
            return result.data
        else:
            return {"error": f"Failed to fetch health data: {result.error}"}

    except Exception as e:
        return {"error": f"Error fetching health data: {str(e)}"}
    finally:
        await adapter.close()


async def fetch_weekly_trends() -> dict:
    """
    Fetch 7-day health trends from Oura Ring.

    Returns:
        Dictionary with trend analysis including averages, ranges, and patterns.
        Returns empty dict with error key if fetch fails.
    """
    try:
        adapter = OuraAdapter()
        today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
        seven_days_ago = (datetime.now(ZoneInfo("America/New_York")) - timedelta(days=6)).strftime("%Y-%m-%d")

        result = await adapter.call_tool("get_daily_summary", {
            "start_date": seven_days_ago,
            "end_date": today
        })

        if result.success:
            return _analyze_weekly_trends(result.data)
        else:
            return {"error": f"Failed to fetch weekly data: {result.error}"}

    except Exception as e:
        return {"error": f"Error fetching weekly data: {str(e)}"}
    finally:
        await adapter.close()


def _analyze_weekly_trends(data: dict) -> dict:
    """
    Analyze weekly health data to identify trends.

    Args:
        data: Raw weekly data from OuraAdapter

    Returns:
        Dictionary with trend statistics and analysis
    """
    readiness_scores = [item.get("score") for item in data.get("readiness", []) if item.get("score")]
    sleep_scores = [item.get("score") for item in data.get("sleep", []) if item.get("score")]
    stress_data = data.get("stress", [])

    trends = {
        "readiness": _calculate_trend_stats(readiness_scores, "Readiness"),
        "sleep": _calculate_trend_stats(sleep_scores, "Sleep"),
        "patterns": []
    }

    # Identify patterns
    if readiness_scores and sleep_scores:
        # Check for declining trends
        readiness_trend = _get_trend_direction(readiness_scores)
        sleep_trend = _get_trend_direction(sleep_scores)

        if readiness_trend == "declining" and sleep_trend == "declining":
            trends["patterns"].append("⚠️ Both readiness and sleep declining - prioritize recovery")
        elif readiness_trend == "improving" and sleep_trend == "improving":
            trends["patterns"].append("✅ Positive trend: Both sleep and recovery improving")
        elif readiness_trend == "declining" and sleep_trend != "declining":
            trends["patterns"].append("⚠️ Readiness declining despite stable sleep - check stress and activity")
        elif sleep_trend == "declining":
            trends["patterns"].append("⚠️ Sleep quality declining - review sleep environment and bedtime routine")

        # Check if below optimal
        avg_readiness = sum(readiness_scores) / len(readiness_scores)
        avg_sleep = sum(sleep_scores) / len(sleep_scores)

        if avg_readiness < 70:
            trends["patterns"].append("📊 Week average: Low readiness - consider lighter training load")
        if avg_sleep < 70:
            trends["patterns"].append("📊 Week average: Suboptimal sleep - focus on sleep hygiene")

    if not trends["patterns"]:
        trends["patterns"].append("📊 Metrics stable across the week")

    return trends


def _calculate_trend_stats(scores: List[int], metric_name: str) -> Dict[str, Any]:
    """
    Calculate statistical analysis for a metric's trend.

    Args:
        scores: List of scores over time
        metric_name: Name of the metric for display

    Returns:
        Dictionary with min, max, average, and trend direction
    """
    if not scores:
        return {
            "average": None,
            "min": None,
            "max": None,
            "trend": "no_data",
            "days": 0
        }

    return {
        "average": round(sum(scores) / len(scores), 1),
        "min": min(scores),
        "max": max(scores),
        "trend": _get_trend_direction(scores),
        "days": len(scores)
    }


def _get_trend_direction(scores: List[int]) -> str:
    """
    Determine if a metric is improving, declining, or stable.

    Args:
        scores: List of scores in chronological order

    Returns:
        "improving", "declining", or "stable"
    """
    if len(scores) < 2:
        return "stable"

    # Compare first half to second half
    mid = len(scores) // 2
    first_half_avg = sum(scores[:mid]) / mid
    second_half_avg = sum(scores[mid:]) / len(scores[mid:])

    diff_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100

    if diff_pct > 5:
        return "improving"
    elif diff_pct < -5:
        return "declining"
    else:
        return "stable"


def _format_weekly_trends(trends: dict) -> str:
    """
    Format weekly trends data into a readable string.
    Uses responsive formatting for mobile/desktop.

    Args:
        trends: Trend analysis from _analyze_weekly_trends

    Returns:
        Formatted string with trend visualizations
    """
    mobile = is_mobile()

    if "error" in trends:
        return f"\n{format_header('7-Day Trends')}\n\n❌ {trends['error']}\n"

    output = "\n" + format_header("7-Day Trends") + "\n\n"

    trend_emoji_map = {
        "improving": "📈",
        "declining": "📉",
        "stable": "➡️",
        "no_data": "❓"
    }

    # Readiness trends
    readiness = trends.get("readiness", {})
    if readiness.get("average"):
        trend_emoji = trend_emoji_map.get(readiness.get("trend", "stable"), "➡️")

        if mobile:
            # Compact format for mobile
            output += f"{trend_emoji} Readiness: {readiness['average']} avg\n"
            output += f"  Range: {readiness['min']}-{readiness['max']}\n"
        else:
            output += f"**Readiness** {trend_emoji}\n"
            output += f"- Average: {readiness['average']} ({_get_status_emoji(int(readiness['average']))})\n"
            output += f"- Range: {readiness['min']} - {readiness['max']}\n"
            output += f"- Trend: {readiness['trend'].replace('_', ' ').title()}\n\n"
    else:
        output += "Readiness: No data\n"

    # Sleep trends
    sleep = trends.get("sleep", {})
    if sleep.get("average"):
        trend_emoji = trend_emoji_map.get(sleep.get("trend", "stable"), "➡️")

        if mobile:
            output += f"\n{trend_emoji} Sleep: {sleep['average']} avg\n"
            output += f"  Range: {sleep['min']}-{sleep['max']}\n"
        else:
            output += f"**Sleep** {trend_emoji}\n"
            output += f"- Average: {sleep['average']} ({_get_status_emoji(int(sleep['average']))})\n"
            output += f"- Range: {sleep['min']} - {sleep['max']}\n"
            output += f"- Trend: {sleep['trend'].replace('_', ' ').title()}\n\n"
    else:
        output += "\nSleep: No data\n"

    # Patterns
    patterns = trends.get("patterns", [])
    if patterns:
        if mobile:
            output += "\nPatterns:\n"
        else:
            output += "**Patterns Detected:**\n"
        for pattern in patterns:
            if mobile:
                pattern = wrap_text(pattern, 38)
            output += f"- {pattern}\n"

    return output


def _get_status_emoji(score: int) -> str:
    """Get emoji indicator for a score."""
    if score >= 85:
        return "🟢"
    elif score >= 70:
        return "🟡"
    elif score >= 55:
        return "🟠"
    else:
        return "🔴"


def _format_duration(seconds: int) -> str:
    """Format seconds into readable duration (e.g., '7h 23m')."""
    if not seconds:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _analyze_sleep_quality(sleep: Dict[str, Any]) -> List[str]:
    """
    Analyze sleep data and generate insights.

    Args:
        sleep: Sleep data from Oura

    Returns:
        List of insight strings
    """
    insights = []

    if not sleep:
        return insights

    # Sleep duration analysis
    total_sleep = sleep.get("total_sleep_duration", 0)
    if total_sleep > 0:
        hours = total_sleep / 3600
        if hours < 6.5:
            insights.append("⚠️ Sleep duration is below optimal (< 6.5h)")
        elif hours >= 8 and hours <= 9:
            insights.append("✅ Sleep duration is in optimal range (8-9h)")

    # Sleep efficiency
    efficiency = sleep.get("efficiency")
    if efficiency:
        if efficiency < 85:
            insights.append(f"⚠️ Sleep efficiency is low ({efficiency}%) - consider sleep environment")
        elif efficiency >= 90:
            insights.append(f"✅ Excellent sleep efficiency ({efficiency}%)")

    # REM sleep analysis
    rem_duration = sleep.get("rem_sleep_duration", 0)
    if rem_duration > 0:
        rem_hours = rem_duration / 3600
        rem_pct = (rem_duration / total_sleep * 100) if total_sleep > 0 else 0
        if rem_pct < 20:
            insights.append(f"⚠️ REM sleep is low ({rem_pct:.0f}%) - may affect learning and mood")
        elif rem_pct >= 25:
            insights.append(f"✅ Strong REM sleep ({rem_pct:.0f}%)")

    # Deep sleep analysis
    deep_duration = sleep.get("deep_sleep_duration", 0)
    if deep_duration > 0:
        deep_hours = deep_duration / 3600
        deep_pct = (deep_duration / total_sleep * 100) if total_sleep > 0 else 0
        if deep_pct < 15:
            insights.append(f"⚠️ Deep sleep is low ({deep_pct:.0f}%) - physical recovery may be limited")
        elif deep_pct >= 20:
            insights.append(f"✅ Good deep sleep ({deep_pct:.0f}%)")

    # Restfulness
    restless_periods = sleep.get("restless_periods")
    if restless_periods and restless_periods > 15:
        insights.append(f"⚠️ High restless periods ({restless_periods}) - check sleep environment")

    return insights


def _analyze_readiness(readiness: Dict[str, Any]) -> List[str]:
    """
    Analyze readiness data and generate insights.

    Args:
        readiness: Readiness data from Oura

    Returns:
        List of insight strings
    """
    insights = []

    if not readiness:
        return insights

    score = readiness.get("score", 0)

    # Overall readiness assessment
    if score >= 85:
        insights.append("💪 Body is well-recovered and ready for challenging activities")
    elif score >= 70:
        insights.append("👍 Good readiness - can handle normal workload")
    elif score < 70:
        insights.append("⚠️ Below-optimal readiness - consider lighter activities or rest")

    # Analyze contributors
    contributors = readiness.get("contributors", {})

    # Activity balance
    activity_balance = contributors.get("activity_balance")
    if activity_balance and activity_balance < 70:
        insights.append("📊 Activity balance is low - consider adjusting activity levels")

    # Body temperature
    body_temp = contributors.get("body_temperature")
    if body_temp and body_temp < 70:
        insights.append("🌡️ Body temperature deviation - may indicate illness or stress")

    # HRV balance
    hrv_balance = contributors.get("hrv_balance")
    if hrv_balance and hrv_balance < 70:
        insights.append("💓 HRV is low - indicates high stress or inadequate recovery")
    elif hrv_balance and hrv_balance >= 85:
        insights.append("💓 Excellent HRV - strong stress resilience")

    # Recovery index
    recovery_index = contributors.get("recovery_index")
    if recovery_index and recovery_index < 70:
        insights.append("🔄 Recovery is incomplete - prioritize rest")

    # Resting heart rate
    resting_hr = contributors.get("resting_heart_rate")
    if resting_hr and resting_hr < 70:
        insights.append("❤️ Elevated resting heart rate - may indicate overtraining or stress")

    # Sleep balance
    sleep_balance = contributors.get("sleep_balance")
    if sleep_balance and sleep_balance < 70:
        insights.append("😴 Sleep debt accumulating - prioritize longer sleep tonight")

    # Previous day activity
    prev_day_activity = contributors.get("previous_day_activity")
    if prev_day_activity and prev_day_activity < 70:
        insights.append("🏃 High previous day activity - ensure adequate recovery")

    return insights


def _analyze_stress(stress: Dict[str, Any]) -> List[str]:
    """
    Analyze stress data and generate insights.

    Args:
        stress: Stress data from Oura

    Returns:
        List of insight strings
    """
    insights = []

    if not stress:
        return insights

    day_summary = stress.get("day_summary", "").lower()

    if day_summary == "restored":
        insights.append("✅ Well-managed stress - good balance of activity and recovery")
    elif day_summary == "normal":
        insights.append("👍 Normal stress levels - maintain current balance")
    elif day_summary in ["stressed", "high"]:
        insights.append("⚠️ Elevated stress detected - consider recovery activities")

    # Recovery time
    recovery_high = stress.get("recovery_high")
    stress_high = stress.get("stress_high")

    if recovery_high and stress_high:
        recovery_pct = (recovery_high / (recovery_high + stress_high) * 100)
        if recovery_pct < 30:
            insights.append("🔄 Low recovery time today - schedule recovery activities")
        elif recovery_pct >= 50:
            insights.append("🔄 Good recovery time - stress is well-managed")

    return insights


def _get_current_hrv(data: Dict[str, Any]) -> Optional[float]:
    """
    Extract current HRV value from health data.

    Args:
        data: Health data from OuraAdapter

    Returns:
        Current HRV value or None if not available
    """
    sleep = data.get("sleep", {})
    if not sleep:
        return None

    # Try both possible HRV field names
    hrv = sleep.get("average_hrv") or sleep.get("hrv_average")
    return float(hrv) if hrv else None


def _format_hrv_baseline(data: Dict[str, Any]) -> str:
    """
    Format HRV baseline section showing baseline, current HRV, and deviation.

    Args:
        data: Health data from OuraAdapter

    Returns:
        Formatted HRV baseline section string
    """
    mobile = is_mobile()

    # Extract current HRV from sleep data
    current_hrv = _get_current_hrv(data)

    # If no current HRV, can't show baseline comparison
    if current_hrv is None:
        return ""

    # Detect deviation from baseline
    deviation_result = detect_deviation(current_hrv)

    # If no baseline available yet, show message
    if deviation_result is None:
        return "\n💓 HRV: {:.1f} ms (baseline not yet established)\n".format(current_hrv)

    # Format the HRV baseline section
    output = []

    # Status emoji based on deviation status
    status_emoji_map = {
        "normal": "🟢",
        "warning": "🟡",
        "critical": "🔴"
    }
    status_emoji = status_emoji_map.get(deviation_result.status, "⚪")

    # Main HRV line with status
    output.append(f"\n{status_emoji} HRV Baseline: {deviation_result.baseline_mean:.1f} ms")

    # HRV details
    hrv_items = []
    hrv_items.append(f"Current: {deviation_result.current_hrv:.1f} ms")

    # Deviation with appropriate formatting
    deviation_sign = "+" if deviation_result.percent_deviation >= 0 else ""
    hrv_items.append(f"Deviation: {deviation_sign}{deviation_result.percent_deviation:.1f}%")

    # Confidence level
    confidence_pct = int(deviation_result.confidence * 100)
    hrv_items.append(f"Confidence: {confidence_pct}%")

    # Status interpretation for warning/critical
    if deviation_result.status == "warning":
        hrv_items.append("⚠️ Moderately low - elevated stress/recovery need")
    elif deviation_result.status == "critical":
        hrv_items.append("🚨 Critically low - high stress/poor recovery")

    output.append(format_list(hrv_items))

    return "\n".join(output)


def _generate_recommendations(data: Dict[str, Any]) -> List[str]:
    """
    Generate personalized recommendations based on health data.

    Args:
        data: Complete health data snapshot

    Returns:
        List of actionable recommendations
    """
    recommendations = []

    readiness = data.get("readiness", {})
    sleep = data.get("sleep", {})
    stress = data.get("stress", {})
    activity = data.get("activity", {})

    readiness_score = readiness.get("score", 0) if readiness else 0
    sleep_score = sleep.get("score", 0) if sleep else 0

    # Check HRV baseline deviation
    current_hrv = _get_current_hrv(data)
    if current_hrv:
        deviation_result = detect_deviation(current_hrv)
        if deviation_result:
            if deviation_result.status == "critical":
                recommendations.append("🚨 **Priority**: HRV critically low - prioritize rest and recovery")
            elif deviation_result.status == "warning":
                recommendations.append("⚠️ HRV below baseline - reduce stress and prioritize recovery")

    # Priority 1: Critical issues
    if readiness_score < 55:
        recommendations.append("🚨 **Priority**: Take a recovery day - readiness is critically low")

    if sleep_score < 55:
        sleep_duration = sleep.get("total_sleep_duration", 0) / 3600 if sleep else 0
        if sleep_duration < 6:
            recommendations.append("🚨 **Priority**: Address sleep - aim for 8+ hours tonight")

    # Priority 2: Optimization opportunities
    if sleep:
        efficiency = sleep.get("efficiency", 0)
        if efficiency < 85:
            recommendations.append("🛏️ Improve sleep environment (dark, cool, quiet) to boost efficiency")

        rem_duration = sleep.get("rem_sleep_duration", 0)
        total_sleep = sleep.get("total_sleep_duration", 1)
        rem_pct = (rem_duration / total_sleep * 100) if total_sleep > 0 else 0
        if rem_pct < 20:
            recommendations.append("🧠 Reduce alcohol and aim for consistent sleep schedule to improve REM")

    if readiness:
        contributors = readiness.get("contributors", {})
        hrv_balance = contributors.get("hrv_balance", 100)
        if hrv_balance < 70:
            recommendations.append("🧘 Practice stress management (meditation, breathwork) to improve HRV")

    if stress:
        day_summary = stress.get("day_summary", "").lower()
        if day_summary in ["stressed", "high"]:
            recommendations.append("🌿 Schedule recovery activities (walk, stretching, time in nature)")

    # Priority 3: General optimization
    if readiness_score >= 85 and sleep_score >= 85:
        recommendations.append("💪 Great recovery state - good day for challenging work or training")
    elif readiness_score >= 70 and sleep_score >= 70:
        recommendations.append("⚡ Solid baseline - maintain current habits for sustained performance")

    # Activity-based recommendations
    if activity:
        activity_score = activity.get("score", 0)
        if activity_score < 70:
            recommendations.append("🚶 Aim for more movement today - short walks between focus sessions")

    # Default fallback
    if not recommendations:
        recommendations.append("📊 Continue monitoring trends - maintain current health habits")

    return recommendations


def format_health_summary(data: dict) -> str:
    """
    Format health data into a comprehensive, unified dashboard.
    Uses responsive formatting for mobile/desktop.

    Args:
        data: Health data from OuraAdapter

    Returns:
        Formatted string with metrics, insights, and recommendations
    """
    if "error" in data:
        return f"⚠️  {data['error']}\n\nUnable to generate health summary."

    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    summary = data.get("summary", {})
    readiness = data.get("readiness", {})
    sleep = data.get("sleep", {})
    stress = data.get("stress", {})
    activity = data.get("activity", {})
    mobile = is_mobile()

    # Build the summary output
    output = []

    # Title - responsive
    if mobile:
        output.append(f"━━━ Health Dashboard ━━━")
        output.append(f"📅 {date}")
    else:
        output.append(f"# 💚 Health Dashboard - {date}\n")

    # Overall status
    status = summary.get("overall_status", "unknown").title()
    status_emoji_map = {
        "excellent": "🟢",
        "good": "🟢",
        "fair": "🟡",
        "poor": "🔴",
        "unknown": "⚪"
    }
    status_emoji = status_emoji_map.get(status.lower(), "⚪")
    output.append(f"\n{status_emoji} Overall: {status}\n")

    # Key Metrics Section
    output.append(format_header("Key Metrics"))

    # Readiness
    if readiness and "score" in readiness:
        score = readiness["score"]
        emoji = _get_status_emoji(score)
        output.append(f"\n{emoji} Readiness: {score}/100")

        # Readiness contributors
        contributors = readiness.get("contributors", {})
        if contributors:
            contrib_items = []
            contributor_pairs = [
                ("Sleep Balance", contributors.get("sleep_balance")),
                ("Activity", contributors.get("activity_balance")),
                ("HRV", contributors.get("hrv_balance")),
                ("Recovery", contributors.get("recovery_index")),
            ]
            for name, value in contributor_pairs:
                if value is not None:
                    contrib_emoji = _get_status_emoji(value)
                    contrib_items.append(f"{contrib_emoji} {name}: {value}")
            output.append(format_list(contrib_items))
    else:
        output.append("\n⚪ Readiness: No data")

    # Sleep
    if sleep and "score" in sleep:
        score = sleep["score"]
        emoji = _get_status_emoji(score)
        total_sleep = sleep.get("total_sleep_duration", 0)
        output.append(f"\n{emoji} Sleep: {score}/100 ({_format_duration(total_sleep)})")

        # Sleep details
        sleep_items = []
        efficiency = sleep.get("efficiency")
        if efficiency:
            sleep_items.append(f"Efficiency: {efficiency}%")

        # Sleep stages - compact on mobile
        rem = sleep.get("rem_sleep_duration", 0)
        deep = sleep.get("deep_sleep_duration", 0)
        light = sleep.get("light_sleep_duration", 0)

        if mobile:
            # Compact stage display for mobile
            stages = []
            if rem > 0:
                stages.append(f"REM {_format_duration(rem)}")
            if deep > 0:
                stages.append(f"Deep {_format_duration(deep)}")
            if stages:
                sleep_items.append(" | ".join(stages))
        else:
            if rem > 0:
                sleep_items.append(f"REM: {_format_duration(rem)}")
            if deep > 0:
                sleep_items.append(f"Deep: {_format_duration(deep)}")
            if light > 0:
                sleep_items.append(f"Light: {_format_duration(light)}")

        restless = sleep.get("restless_periods")
        if restless:
            sleep_items.append(f"Restless: {restless}")

        output.append(format_list(sleep_items))
    else:
        output.append("\n⚪ Sleep: No data")

    # Stress
    if stress:
        day_summary = stress.get("day_summary", "Unknown")
        stress_emoji_map = {
            "restored": "🟢",
            "normal": "🟡",
            "stressed": "🔴",
            "high": "🔴"
        }
        stress_emoji = stress_emoji_map.get(day_summary.lower(), "⚪")
        output.append(f"\n{stress_emoji} Stress: {day_summary.title()}")

        # Stress breakdown - compact
        recovery_high = stress.get("recovery_high")
        stress_high = stress.get("stress_high")
        if recovery_high and stress_high:
            total_time = recovery_high + stress_high
            recovery_pct = (recovery_high / total_time * 100) if total_time > 0 else 0
            stress_pct = (stress_high / total_time * 100) if total_time > 0 else 0
            stress_items = [
                f"Recovery: {_format_duration(recovery_high)} ({recovery_pct:.0f}%)",
                f"Stress: {_format_duration(stress_high)} ({stress_pct:.0f}%)"
            ]
            output.append(format_list(stress_items))
    else:
        output.append("\n⚪ Stress: No data")

    # Activity (optional, if available)
    if activity and "score" in activity:
        score = activity["score"]
        emoji = _get_status_emoji(score)
        output.append(f"\n{emoji} Activity: {score}/100")

    # HRV Baseline Section
    hrv_baseline_section = _format_hrv_baseline(data)
    if hrv_baseline_section:
        output.append(hrv_baseline_section)

    # Health Insights Section
    output.append("\n" + format_header("Insights"))

    all_insights = []
    all_insights.extend(_analyze_readiness(readiness))
    all_insights.extend(_analyze_sleep_quality(sleep))
    all_insights.extend(_analyze_stress(stress))

    if all_insights:
        # Limit insights on mobile
        max_insights = 5 if mobile else 8
        insight_items = []
        for insight in all_insights[:max_insights]:
            if mobile:
                insight = wrap_text(insight, 38)
            insight_items.append(insight)
        output.append(format_list(insight_items))
    else:
        output.append("No significant insights")

    # Recommendations Section
    output.append("\n" + format_header("Recommendations"))

    recommendations = _generate_recommendations(data)
    if recommendations:
        max_recs = 3 if mobile else 5
        rec_items = []
        for rec in recommendations[:max_recs]:
            if mobile:
                rec = wrap_text(rec, 38)
            rec_items.append(rec)
        output.append(format_list(rec_items, numbered=True))
    else:
        output.append("Continue current health practices")

    # Footer
    if mobile:
        output.append("\n━" * 20)
    else:
        output.append("")

    return "\n".join(output)


def save_to_history(summary: str):
    """Save the health summary to History."""
    project_root = Path(__file__).parent.parent.parent
    history_dir = project_root / "History" / "HealthSummaries"
    history_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now()
    filename = f"health_{timestamp.strftime('%Y-%m-%d')}.md"

    with open(history_dir / filename, "w") as f:
        f.write(f"# Health Summary - {timestamp.strftime('%B %d, %Y')}\n\n")
        f.write(f"*Generated at {timestamp.strftime('%I:%M %p')}*\n\n")
        f.write(summary)


async def execute(use_llm_enhancement: bool = False, show_trends: bool = False) -> str:
    """
    Generate health summary using OuraAdapter.

    Args:
        use_llm_enhancement: If True, uses LLM to enhance the output with insights
        show_trends: If True, includes 7-day trend analysis

    Returns:
        The generated health summary
    """
    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"💚 Generating health summary for {today}...")

    # Fetch health data
    print("📊 Fetching Oura Ring data...")
    health_data = await fetch_health_data()

    # Fetch weekly trends if requested
    trends_data = None
    if show_trends:
        print("📈 Fetching 7-day trends...")
        trends_data = await fetch_weekly_trends()

    # Format the summary
    summary = format_health_summary(health_data)

    # Add trends if available
    if trends_data:
        summary += _format_weekly_trends(trends_data)

    print("-" * 50)

    # If LLM enhancement is requested, pass through LLM for personalization
    if use_llm_enhancement and "error" not in health_data:
        print(f"✨ Enhancing with gpt-4o-mini...\n")
        client = get_client()
        model = "gpt-4o-mini"

        enhance_prompt = f"""Today is {today}.

Here's the health summary data:

{summary}

Raw data for context:
{health_data}

Please review and enhance this health summary to:
1. Add personalized insights based on the metrics
2. Identify any concerning patterns or positive trends
3. Provide specific, actionable recommendations
4. Keep the format scannable and ADHD-friendly
5. Be supportive and evidence-based, not alarmist
"""

        response_parts = []
        for chunk in client.chat_stream(
            prompt=enhance_prompt,
            model=model,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.7
        ):
            print(chunk, end="", flush=True)
            response_parts.append(chunk)

        summary = "".join(response_parts)
    else:
        # Just print the basic formatted summary
        print(summary)

    print("\n" + "-" * 50)

    # Save to history
    save_to_history(summary)
    print("\n✅ Saved to History/HealthSummaries/")

    return summary


def main():
    """CLI entry point."""
    import asyncio

    # Check for flags
    use_llm = "--llm-enhance" in sys.argv
    show_trends = "--trends" in sys.argv

    # Run the async execute function
    asyncio.run(execute(use_llm_enhancement=use_llm, show_trends=show_trends))


if __name__ == "__main__":
    main()
