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


def format_health_summary(data: dict) -> str:
    """
    Format health data into a readable summary.

    Args:
        data: Health data from OuraAdapter

    Returns:
        Formatted markdown string
    """
    if "error" in data:
        return f"⚠️  {data['error']}\n\nUnable to generate health summary."

    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    summary = data.get("summary", {})
    readiness = data.get("readiness", {})
    sleep = data.get("sleep", {})
    stress = data.get("stress", {})

    # Build the summary output
    output = []
    output.append(f"# Health Summary - {date}\n")

    # Overall status
    status = summary.get("overall_status", "unknown").title()
    output.append(f"## Overall Status: {status}\n")

    # Key metrics
    output.append("## Key Metrics\n")

    if readiness and "score" in readiness:
        score = readiness["score"]
        output.append(f"**Readiness:** {score}/100")

    if sleep and "score" in sleep:
        score = sleep["score"]
        total_sleep = sleep.get("total_sleep_duration", 0) / 3600  # Convert seconds to hours
        output.append(f"**Sleep:** {score}/100 ({total_sleep:.1f}h)")

    if stress:
        if "day_summary" in stress:
            stress_level = stress["day_summary"]
            output.append(f"**Stress:** {stress_level}")

    # Recommendations
    recommendations = summary.get("recommendations", [])
    if recommendations:
        output.append("\n## Recommendations\n")
        for rec in recommendations:
            output.append(f"- {rec}")

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
