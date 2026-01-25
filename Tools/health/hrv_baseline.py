"""
HRV Baseline Calculator for Thanos.

Syncs HRV data from Oura Ring and calculates personalized baselines
for stress detection and energy state management.
"""

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

from Tools.state_store.store import StateStore


@dataclass
class BaselineResult:
    """
    HRV baseline calculation result.

    Contains statistical measures of normal HRV range for an individual,
    calculated from historical data with outlier filtering.
    """
    mean: float  # Mean HRV value
    stddev: float  # Standard deviation
    confidence: float  # Confidence level (0-1) based on data points
    data_points: int  # Number of HRV values used in calculation
    min_value: float  # Minimum HRV in dataset
    max_value: float  # Maximum HRV in dataset


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
    # Import OuraAdapter locally to avoid dependency issues when only using calculate_baseline
    from Tools.adapters.oura import OuraAdapter

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


def calculate_baseline(days: int = 14, min_data_points: int = 3) -> Optional[BaselineResult]:
    """
    Calculate HRV baseline from stored data using rolling window with outlier filtering.

    Uses a 14-day rolling window by default. Filters outliers that are more than
    2 standard deviations from the mean to ensure a robust baseline.

    Args:
        days: Number of days to include in baseline calculation (default: 14)
        min_data_points: Minimum HRV readings required for valid baseline (default: 3)

    Returns:
        BaselineResult with mean, stddev, and confidence metrics, or None if insufficient data

    Algorithm:
        1. Query last N days of HRV data from StateStore
        2. Return None if fewer than min_data_points available
        3. Calculate initial mean and standard deviation
        4. Filter outliers (values > 2 std dev from mean)
        5. Recalculate mean and stddev on filtered dataset
        6. Calculate confidence based on number of data points
        7. Return BaselineResult

    Confidence Calculation:
        - < 3 points: insufficient (returns None)
        - 3-6 points: 0.6 confidence (limited data)
        - 7-10 points: 0.8 confidence (moderate data)
        - 11-13 points: 0.9 confidence (good data)
        - 14+ points: 0.95 confidence (full 14-day window)
    """
    store = StateStore()

    # Calculate date range for query
    tz = ZoneInfo("America/New_York")
    today = datetime.now(tz).date()
    start_date = today - timedelta(days=days - 1)

    # Query HRV metrics from StateStore
    metrics = store.get_health_metrics(
        metric_type="hrv",
        start_date=start_date,
        end_date=today,
        limit=days
    )

    # Extract HRV values
    hrv_values: List[float] = [m.value for m in metrics if m.value is not None]

    # Check for sufficient data
    if len(hrv_values) < min_data_points:
        return None

    # Calculate initial statistics
    initial_mean = statistics.mean(hrv_values)
    initial_stddev = statistics.stdev(hrv_values) if len(hrv_values) > 1 else 0.0

    # Filter outliers (values more than 2 std dev from mean)
    # Only filter if we have enough data and variation
    if len(hrv_values) > 3 and initial_stddev > 0:
        filtered_values = [
            v for v in hrv_values
            if abs(v - initial_mean) <= 2 * initial_stddev
        ]
        # Use filtered values if we still have enough data
        if len(filtered_values) >= min_data_points:
            hrv_values = filtered_values

    # Recalculate on filtered dataset
    mean = statistics.mean(hrv_values)
    stddev = statistics.stdev(hrv_values) if len(hrv_values) > 1 else 0.0

    # Calculate confidence based on data points
    data_count = len(hrv_values)
    if data_count >= 14:
        confidence = 0.95
    elif data_count >= 11:
        confidence = 0.90
    elif data_count >= 7:
        confidence = 0.80
    else:
        confidence = 0.60

    return BaselineResult(
        mean=mean,
        stddev=stddev,
        confidence=confidence,
        data_points=data_count,
        min_value=min(hrv_values),
        max_value=max(hrv_values)
    )


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
