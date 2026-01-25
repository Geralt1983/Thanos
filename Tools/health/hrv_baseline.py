"""
HRV Baseline Calculator for Thanos.

Syncs HRV data from Oura Ring and calculates personalized baselines
for stress detection and energy state management.
"""

from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from Tools.adapters.oura import OuraAdapter
from Tools.state_store.store import StateStore


async def sync_hrv_data(days: int = 14) -> None:
    """
    Sync HRV data from Oura for the specified number of past days.

    Fetches sleep sessions from Oura Ring, extracts HRV values,
    and stores them in the StateStore for baseline calculation.

    Args:
        days: Number of days to fetch (default: 14 for rolling baseline)

    Raises:
        ValueError: If Oura access token is not configured
        Exception: If data fetch or storage fails
    """
    # Initialize adapters
    oura = OuraAdapter()
    store = StateStore()

    # Calculate date range
    tz = ZoneInfo("America/New_York")
    today = datetime.now(tz).date()
    start_date = (today - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    # Fetch sleep data with HRV
    result = await oura.call_tool(
        "get_sleep",
        {"start_date": start_date, "end_date": end_date}
    )

    if not result.success:
        raise Exception(f"Failed to fetch sleep data: {result.error}")

    # Extract and store HRV values
    sleep_sessions = result.data
    hrv_count = 0

    for session in sleep_sessions:
        # Each session has a day (date) and HRV metrics
        session_date = session.get("day")
        hrv_value = session.get("hrv_average") or session.get("average_hrv")

        if session_date and hrv_value:
            # Store HRV metric
            store.add_health_metric(
                date=session_date,
                metric_type="hrv",
                value=float(hrv_value)
            )
            hrv_count += 1

    print(f"OK - HRV data synced ({hrv_count} days)")


async def calculate_baseline() -> Optional[dict]:
    """
    Calculate HRV baseline from stored data.

    Returns:
        dict with baseline metrics or None if insufficient data
    """
    # TODO: Implement in subtask-2-1
    raise NotImplementedError("Baseline calculation not yet implemented")


async def detect_deviation(current_hrv: float) -> Optional[dict]:
    """
    Detect deviation from baseline.

    Args:
        current_hrv: Current HRV value to compare

    Returns:
        dict with deviation metrics or None if no baseline
    """
    # TODO: Implement in subtask-2-3
    raise NotImplementedError("Deviation detection not yet implemented")


if __name__ == "__main__":
    import asyncio
    asyncio.run(sync_hrv_data())
