"""
Health: Summary Command

Generates a comprehensive health metrics dashboard combining Oura Ring data
(readiness, sleep, stress) into a unified health snapshot.

Usage:
    python -m commands.health.summary [--llm-enhance]

Model: gpt-4o-mini (simple task - cost effective)
"""

from datetime import datetime
from pathlib import Path
import sys
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from Tools.adapters.oura import OuraAdapter
from Tools.litellm_client import get_client


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


def _analyze_sleep_quality(sleep: dict) -> list[str]:
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


def _analyze_readiness(readiness: dict) -> list[str]:
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


def _analyze_stress(stress: dict) -> list[str]:
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


def _generate_recommendations(data: dict) -> list[str]:
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

    Args:
        data: Health data from OuraAdapter

    Returns:
        Formatted markdown string with metrics, insights, and recommendations
    """
    if "error" in data:
        return f"⚠️  {data['error']}\n\nUnable to generate health summary."

    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    summary = data.get("summary", {})
    readiness = data.get("readiness", {})
    sleep = data.get("sleep", {})
    stress = data.get("stress", {})
    activity = data.get("activity", {})

    # Build the summary output
    output = []
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
    output.append(f"## {status_emoji} Overall Status: {status}\n")

    # Key Metrics Section
    output.append("## 📊 Key Metrics\n")

    # Readiness
    if readiness and "score" in readiness:
        score = readiness["score"]
        emoji = _get_status_emoji(score)
        output.append(f"### {emoji} Readiness: {score}/100\n")

        # Readiness contributors
        contributors = readiness.get("contributors", {})
        if contributors:
            output.append("**Top Contributors:**")
            contributor_items = [
                ("Sleep Balance", contributors.get("sleep_balance")),
                ("Previous Day Activity", contributors.get("previous_day_activity")),
                ("Activity Balance", contributors.get("activity_balance")),
                ("HRV Balance", contributors.get("hrv_balance")),
                ("Recovery Index", contributors.get("recovery_index")),
            ]
            for name, value in contributor_items:
                if value is not None:
                    contrib_emoji = _get_status_emoji(value)
                    output.append(f"- {contrib_emoji} {name}: {value}/100")
            output.append("")
    else:
        output.append("### ⚪ Readiness: No data available\n")

    # Sleep
    if sleep and "score" in sleep:
        score = sleep["score"]
        emoji = _get_status_emoji(score)
        total_sleep = sleep.get("total_sleep_duration", 0)
        output.append(f"### {emoji} Sleep: {score}/100 ({_format_duration(total_sleep)})\n")

        # Sleep details
        output.append("**Sleep Breakdown:**")
        efficiency = sleep.get("efficiency")
        if efficiency:
            output.append(f"- Efficiency: {efficiency}%")

        # Sleep stages
        rem = sleep.get("rem_sleep_duration", 0)
        deep = sleep.get("deep_sleep_duration", 0)
        light = sleep.get("light_sleep_duration", 0)

        if rem > 0:
            output.append(f"- REM: {_format_duration(rem)}")
        if deep > 0:
            output.append(f"- Deep: {_format_duration(deep)}")
        if light > 0:
            output.append(f"- Light: {_format_duration(light)}")

        # Latency
        latency = sleep.get("latency")
        if latency:
            output.append(f"- Time to Sleep: {_format_duration(latency)}")

        restless = sleep.get("restless_periods")
        if restless:
            output.append(f"- Restless Periods: {restless}")

        output.append("")
    else:
        output.append("### ⚪ Sleep: No data available\n")

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
        output.append(f"### {stress_emoji} Stress: {day_summary.title()}\n")

        # Stress breakdown
        recovery_high = stress.get("recovery_high")
        stress_high = stress.get("stress_high")
        if recovery_high and stress_high:
            total_time = recovery_high + stress_high
            recovery_pct = (recovery_high / total_time * 100) if total_time > 0 else 0
            stress_pct = (stress_high / total_time * 100) if total_time > 0 else 0
            output.append("**Daytime Balance:**")
            output.append(f"- Recovery Time: {_format_duration(recovery_high)} ({recovery_pct:.0f}%)")
            output.append(f"- Stress Time: {_format_duration(stress_high)} ({stress_pct:.0f}%)")
            output.append("")
    else:
        output.append("### ⚪ Stress: No data available\n")

    # Activity (optional, if available)
    if activity and "score" in activity:
        score = activity["score"]
        emoji = _get_status_emoji(score)
        output.append(f"### {emoji} Activity: {score}/100\n")

    # Health Insights Section
    output.append("## 💡 Health Insights\n")

    all_insights = []
    all_insights.extend(_analyze_readiness(readiness))
    all_insights.extend(_analyze_sleep_quality(sleep))
    all_insights.extend(_analyze_stress(stress))

    if all_insights:
        for insight in all_insights[:8]:  # Limit to top 8 insights to avoid overwhelming
            output.append(f"- {insight}")
        output.append("")
    else:
        output.append("- No significant insights to report\n")

    # Recommendations Section
    output.append("## 🎯 Recommendations\n")

    recommendations = _generate_recommendations(data)
    if recommendations:
        for i, rec in enumerate(recommendations[:5], 1):  # Top 5 recommendations
            output.append(f"{i}. {rec}")
    else:
        output.append("- Continue current health practices\n")

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


async def execute(use_llm_enhancement: bool = False) -> str:
    """
    Generate health summary using OuraAdapter.

    Args:
        use_llm_enhancement: If True, uses LLM to enhance the output with insights

    Returns:
        The generated health summary
    """
    today = datetime.now().strftime("%A, %B %d, %Y")
    print(f"💚 Generating health summary for {today}...")

    # Fetch health data
    print("📊 Fetching Oura Ring data...")
    health_data = await fetch_health_data()

    # Format the summary
    summary = format_health_summary(health_data)

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

    # Check for LLM enhancement flag
    use_llm = "--llm-enhance" in sys.argv

    # Run the async execute function
    asyncio.run(execute(use_llm_enhancement=use_llm))


if __name__ == "__main__":
    main()
