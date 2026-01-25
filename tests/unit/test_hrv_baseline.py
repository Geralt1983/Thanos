#!/usr/bin/env python3
"""
Comprehensive tests for HRV baseline calculator.

Tests cover:
- Baseline calculation with varying data points
- Outlier filtering algorithm
- Confidence level calculation
- Deviation detection and status classification
- Edge cases: insufficient data, single values, zero stddev
"""

import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from Tools.health.hrv_baseline import (
    BaselineResult,
    DeviationResult,
    calculate_baseline,
    detect_deviation,
)
from Tools.state_store.store import StateStore


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    return tmp_path / "test_hrv.db"


@pytest.fixture
def store(temp_db_path):
    """Create a StateStore instance with a temporary database."""
    return StateStore(db_path=temp_db_path)


@pytest.fixture
def store_with_hrv_data(store):
    """Create a store with sample HRV data for testing."""
    today = date.today()

    # Add 14 days of stable HRV data (mean ~50, stddev ~5)
    hrv_values = [48, 52, 49, 51, 50, 53, 47, 50, 52, 49, 51, 50, 48, 52]

    for i, hrv in enumerate(hrv_values):
        metric_date = today - timedelta(days=13 - i)
        store.add_health_metric(
            date=metric_date.isoformat(),
            metric_type="hrv",
            value=float(hrv)
        )

    return store


@pytest.fixture
def store_with_outliers(store):
    """Create a store with HRV data containing outliers."""
    today = date.today()

    # Add data with outliers: mean ~50, but has extreme values
    hrv_values = [48, 52, 49, 51, 25, 53, 47, 50, 85, 49, 51, 50, 48, 52]

    for i, hrv in enumerate(hrv_values):
        metric_date = today - timedelta(days=13 - i)
        store.add_health_metric(
            date=metric_date.isoformat(),
            metric_type="hrv",
            value=float(hrv)
        )

    return store


@pytest.fixture
def store_with_minimal_data(store):
    """Create a store with exactly 3 data points (minimum required)."""
    today = date.today()

    hrv_values = [48, 50, 52]

    for i, hrv in enumerate(hrv_values):
        metric_date = today - timedelta(days=2 - i)
        store.add_health_metric(
            date=metric_date.isoformat(),
            metric_type="hrv",
            value=float(hrv)
        )

    return store


@pytest.fixture
def store_with_insufficient_data(store):
    """Create a store with only 2 data points (insufficient)."""
    today = date.today()

    hrv_values = [48, 52]

    for i, hrv in enumerate(hrv_values):
        metric_date = today - timedelta(days=1 - i)
        store.add_health_metric(
            date=metric_date.isoformat(),
            metric_type="hrv",
            value=float(hrv)
        )

    return store


# ============================================================================
# Baseline Calculation Tests
# ============================================================================


class TestBaselineCalculation:
    """Tests for calculate_baseline function."""

    def test_baseline_with_full_dataset(self, store_with_hrv_data):
        """Test baseline calculation with full 14 days of data."""
        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None
        assert isinstance(result, BaselineResult)

        # Check statistical values are reasonable
        assert 45 <= result.mean <= 55  # Mean should be around 50
        assert result.stddev > 0  # Should have some variation
        assert result.data_points == 14
        assert result.confidence == 0.95  # Full dataset confidence

        # Check min/max values
        assert result.min_value < result.mean
        assert result.max_value > result.mean

    def test_baseline_with_minimal_data(self, store_with_minimal_data):
        """Test baseline calculation with exactly min_data_points."""
        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None
        assert result.data_points == 3
        assert result.confidence == 0.60  # Low confidence for 3 points
        assert 45 <= result.mean <= 55
        assert result.stddev > 0

    def test_baseline_with_insufficient_data(self, store_with_insufficient_data):
        """Test that insufficient data returns None."""
        result = calculate_baseline(days=14, min_data_points=3)

        assert result is None

    def test_baseline_with_no_data(self, store):
        """Test that empty database returns None."""
        result = calculate_baseline(days=14, min_data_points=3)

        assert result is None

    def test_baseline_outlier_filtering(self, store_with_outliers):
        """Test that outliers are filtered from baseline calculation."""
        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None

        # After filtering outliers (25 and 85), mean should be close to 50
        assert 47 <= result.mean <= 53

        # Data points should be less than 14 due to outlier removal
        assert result.data_points < 14
        assert result.data_points >= 3  # Should keep at least min_data_points

    def test_baseline_confidence_levels(self, store):
        """Test confidence level calculation at different data point counts."""
        today = date.today()

        # Test with 3-6 points: confidence = 0.60
        for i in range(5):
            store.add_health_metric(
                date=(today - timedelta(days=4 - i)).isoformat(),
                metric_type="hrv",
                value=50.0
            )
        result = calculate_baseline(days=14, min_data_points=3)
        assert result.confidence == 0.60

        # Add more to get 7-10 points: confidence = 0.80
        for i in range(3):
            store.add_health_metric(
                date=(today - timedelta(days=7 - i)).isoformat(),
                metric_type="hrv",
                value=50.0
            )
        result = calculate_baseline(days=14, min_data_points=3)
        assert result.confidence == 0.80

        # Add more to get 11-13 points: confidence = 0.90
        for i in range(3):
            store.add_health_metric(
                date=(today - timedelta(days=10 - i)).isoformat(),
                metric_type="hrv",
                value=50.0
            )
        result = calculate_baseline(days=14, min_data_points=3)
        assert result.confidence == 0.90

        # Add one more to get 14+ points: confidence = 0.95
        store.add_health_metric(
            date=(today - timedelta(days=13)).isoformat(),
            metric_type="hrv",
            value=50.0
        )
        result = calculate_baseline(days=14, min_data_points=3)
        assert result.confidence == 0.95

    def test_baseline_custom_window_size(self, store_with_hrv_data):
        """Test baseline calculation with custom window size."""
        # Calculate 7-day baseline instead of 14-day
        result = calculate_baseline(days=7, min_data_points=3)

        assert result is not None
        # Should have 7 or fewer data points
        assert result.data_points <= 7

    def test_baseline_custom_min_data_points(self, store_with_hrv_data):
        """Test baseline calculation with custom min_data_points."""
        # Require at least 10 data points
        result = calculate_baseline(days=14, min_data_points=10)

        assert result is not None
        assert result.data_points >= 10

    def test_baseline_with_identical_values(self, store):
        """Test baseline calculation when all HRV values are identical."""
        today = date.today()

        # Add 5 identical values
        for i in range(5):
            store.add_health_metric(
                date=(today - timedelta(days=4 - i)).isoformat(),
                metric_type="hrv",
                value=50.0
            )

        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None
        assert result.mean == 50.0
        assert result.stddev == 0.0  # No variation
        assert result.min_value == 50.0
        assert result.max_value == 50.0

    def test_baseline_min_max_values(self, store_with_hrv_data):
        """Test that min and max values are correctly identified."""
        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None
        assert result.min_value <= result.mean <= result.max_value
        assert result.max_value - result.min_value > 0  # Should have range


# ============================================================================
# Deviation Detection Tests
# ============================================================================


class TestDeviationDetection:
    """Tests for detect_deviation function."""

    def test_deviation_with_no_baseline(self, store):
        """Test that deviation detection returns None when no baseline available."""
        result = detect_deviation(current_hrv=50.0)

        assert result is None

    def test_deviation_normal_status(self, store_with_hrv_data):
        """Test normal status when HRV is within 15% of baseline."""
        # Baseline mean should be around 50
        result = detect_deviation(current_hrv=50.0)

        assert result is not None
        assert isinstance(result, DeviationResult)
        assert result.status == "normal"
        assert result.current_hrv == 50.0
        assert -15.0 <= result.percent_deviation <= 15.0

    def test_deviation_warning_status(self, store_with_hrv_data):
        """Test warning status when HRV is 15-25% below baseline."""
        # If baseline mean is ~50, then 40 should be ~20% below (warning)
        result = detect_deviation(current_hrv=40.0)

        assert result is not None
        assert result.status == "warning"
        assert result.percent_deviation < -15.0
        assert result.percent_deviation >= -25.0

    def test_deviation_critical_status(self, store_with_hrv_data):
        """Test critical status when HRV is >25% below baseline."""
        # If baseline mean is ~50, then 35 should be ~30% below (critical)
        result = detect_deviation(current_hrv=35.0)

        assert result is not None
        assert result.status == "critical"
        assert result.percent_deviation < -25.0

    def test_deviation_positive_is_normal(self, store_with_hrv_data):
        """Test that positive deviations (high HRV) always return normal status."""
        # High HRV (good recovery) should be normal, not warning
        result = detect_deviation(current_hrv=70.0)

        assert result is not None
        assert result.status == "normal"
        assert result.percent_deviation > 0

    def test_deviation_exactly_at_threshold(self, store_with_hrv_data):
        """Test deviation exactly at 15% and 25% thresholds."""
        baseline = calculate_baseline()
        assert baseline is not None

        # Test exactly -15% (should be normal, not warning)
        hrv_at_15_percent = baseline.mean * 0.85
        result = detect_deviation(current_hrv=hrv_at_15_percent)
        assert result.status == "normal"

        # Test exactly -25% (should be warning, not critical)
        hrv_at_25_percent = baseline.mean * 0.75
        result = detect_deviation(current_hrv=hrv_at_25_percent)
        assert result.status == "warning"

    def test_deviation_includes_baseline_confidence(self, store_with_minimal_data):
        """Test that deviation result includes baseline confidence."""
        result = detect_deviation(current_hrv=50.0)

        assert result is not None
        assert 0 < result.confidence <= 1.0
        # With minimal data, confidence should be low (0.60)
        assert result.confidence == 0.60

    def test_deviation_metrics_calculated_correctly(self, store_with_hrv_data):
        """Test that deviation metrics are calculated correctly."""
        baseline = calculate_baseline()
        assert baseline is not None

        current_hrv = 45.0
        result = detect_deviation(current_hrv=current_hrv)

        assert result is not None
        assert result.current_hrv == current_hrv
        assert result.baseline_mean == baseline.mean

        # Check deviation calculation
        expected_deviation = current_hrv - baseline.mean
        assert abs(result.deviation - expected_deviation) < 0.01

        # Check percent deviation calculation
        expected_percent = (expected_deviation / baseline.mean) * 100
        assert abs(result.percent_deviation - expected_percent) < 0.1

    def test_deviation_percent_rounded(self, store_with_hrv_data):
        """Test that percent_deviation is rounded to 1 decimal place."""
        result = detect_deviation(current_hrv=48.3333)

        assert result is not None
        # Check that result has at most 1 decimal place
        assert result.percent_deviation == round(result.percent_deviation, 1)

    def test_deviation_with_zero_baseline_mean(self, store):
        """Test deviation when baseline mean is zero (edge case)."""
        today = date.today()

        # Add zero values (pathological case, but should not crash)
        for i in range(5):
            store.add_health_metric(
                date=(today - timedelta(days=4 - i)).isoformat(),
                metric_type="hrv",
                value=0.0
            )

        result = detect_deviation(current_hrv=0.0)

        # Should handle zero division gracefully
        assert result is not None
        assert result.percent_deviation == 0.0


# ============================================================================
# Edge Cases and Integration Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and integration scenarios."""

    def test_baseline_with_single_value(self, store):
        """Test baseline calculation with only one data point."""
        today = date.today()
        store.add_health_metric(
            date=today.isoformat(),
            metric_type="hrv",
            value=50.0
        )

        result = calculate_baseline(days=14, min_data_points=1)

        assert result is not None
        assert result.data_points == 1
        assert result.mean == 50.0
        assert result.stddev == 0.0  # Only one value

    def test_baseline_with_two_values(self, store):
        """Test baseline calculation with two data points."""
        today = date.today()
        store.add_health_metric(
            date=today.isoformat(),
            metric_type="hrv",
            value=48.0
        )
        store.add_health_metric(
            date=(today - timedelta(days=1)).isoformat(),
            metric_type="hrv",
            value=52.0
        )

        result = calculate_baseline(days=14, min_data_points=2)

        assert result is not None
        assert result.data_points == 2
        assert result.mean == 50.0
        assert result.stddev > 0

    def test_baseline_ignores_other_metric_types(self, store):
        """Test that baseline only uses HRV metrics, not other types."""
        today = date.today()

        # Add HRV data
        for i in range(5):
            store.add_health_metric(
                date=(today - timedelta(days=4 - i)).isoformat(),
                metric_type="hrv",
                value=50.0
            )

        # Add other metric types that should be ignored
        for i in range(5):
            store.add_health_metric(
                date=(today - timedelta(days=4 - i)).isoformat(),
                metric_type="sleep_score",
                value=85.0
            )
            store.add_health_metric(
                date=(today - timedelta(days=4 - i)).isoformat(),
                metric_type="readiness",
                value=75.0
            )

        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None
        assert result.data_points == 5  # Should only count HRV metrics
        assert result.mean == 50.0  # Should use HRV values, not sleep/readiness

    def test_baseline_date_range_filtering(self, store):
        """Test that baseline only uses data within the specified date range."""
        today = date.today()

        # Add recent data (within 14 days)
        for i in range(7):
            store.add_health_metric(
                date=(today - timedelta(days=6 - i)).isoformat(),
                metric_type="hrv",
                value=50.0
            )

        # Add old data (outside 14-day window)
        for i in range(5):
            store.add_health_metric(
                date=(today - timedelta(days=20 + i)).isoformat(),
                metric_type="hrv",
                value=100.0  # Very different value
            )

        result = calculate_baseline(days=14, min_data_points=3)

        assert result is not None
        assert result.data_points == 7  # Should only use recent data
        assert result.mean == 50.0  # Should not be affected by old data

    def test_deviation_full_workflow(self, store):
        """Test complete workflow: add data, calculate baseline, detect deviation."""
        today = date.today()

        # Simulate 14 days of HRV data
        for i in range(14):
            store.add_health_metric(
                date=(today - timedelta(days=13 - i)).isoformat(),
                metric_type="hrv",
                value=50.0 + (i % 3)  # Slight variation
            )

        # Calculate baseline
        baseline = calculate_baseline()
        assert baseline is not None
        assert baseline.data_points == 14

        # Detect normal deviation
        normal_result = detect_deviation(current_hrv=50.0)
        assert normal_result is not None
        assert normal_result.status == "normal"

        # Detect warning deviation
        warning_result = detect_deviation(current_hrv=40.0)
        assert warning_result is not None
        assert warning_result.status in ["warning", "critical"]

        # Detect positive deviation (should be normal)
        positive_result = detect_deviation(current_hrv=60.0)
        assert positive_result is not None
        assert positive_result.status == "normal"
