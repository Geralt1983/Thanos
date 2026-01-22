#!/usr/bin/env python3
"""
Health Monitor - Thanos Operator Daemon

Monitors Oura health metrics and generates alerts for low readiness,
poor sleep, high stress, and HRV deviations.

Architecture:
    - Uses cache-first strategy via ~/.oura-cache/ SQLite database
    - Fallback to direct MCP calls if cache unavailable
    - Graceful degradation on errors (returns empty alert list)

Alert Triggers:
    - Readiness < 60: Low energy warning
    - Readiness < 50: Critical burnout risk
    - Sleep < 6 hours: Sleep deficit warning
    - Sleep < 5 hours: Critical sleep debt
    - HRV deviation > 15%: Stress indicator
"""

import asyncio
import logging
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import circuit breaker for MCP resilience
from Tools.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Alert data structure for Operator daemon."""
    type: str  # 'health', 'task', 'pattern'
    severity: str  # 'info', 'warning', 'critical'
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: str
    dedup_key: Optional[str] = None
    priority: Optional[str] = None  # For alerter routing

    def __post_init__(self):
        """Map severity to priority for backward compatibility."""
        if not self.priority:
            self.priority = self.severity


class HealthMonitor:
    """
    Monitor health metrics from Oura Ring via cached database.

    Data Flow:
        1. Check ~/.oura-cache/oura-health.db (primary)
        2. Fallback to direct Oura MCP call if cache stale/unavailable
        3. Return empty list on complete failure (graceful degradation)

    Thresholds:
        - readiness_warning: 65
        - readiness_critical: 50
        - sleep_hours_warning: 6.0
        - sleep_hours_critical: 5.0
        - hrv_warning_deviation: 15%
        - hrv_critical_deviation: 25%
    """

    def __init__(
        self,
        circuit: CircuitBreaker,
        cache_db_path: Optional[Path] = None,
        thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Health Monitor.

        Args:
            circuit: Circuit breaker for MCP protection
            cache_db_path: Path to Oura cache database
            thresholds: Custom thresholds (overrides defaults)
        """
        self.circuit = circuit

        # Setup cache database path
        if cache_db_path is None:
            home = Path.home()
            cache_db_path = home / ".oura-cache" / "oura-health.db"
        self.cache_db_path = cache_db_path

        # Default thresholds
        self.thresholds = {
            'readiness_warning': 65,
            'readiness_critical': 50,
            'sleep_hours_warning': 6.0,
            'sleep_hours_critical': 5.0,
            'hrv_warning_deviation': 15,
            'hrv_critical_deviation': 25,
            'stress_warning': 75,
            'stress_critical': 85
        }

        if thresholds:
            self.thresholds.update(thresholds)

        logger.info(
            f"HealthMonitor initialized: cache={self.cache_db_path}, "
            f"thresholds={self.thresholds}"
        )

    async def check(self) -> List[Alert]:
        """
        Run health checks and generate alerts.

        Returns:
            List of Alert objects (empty on errors - graceful degradation)
        """
        try:
            logger.debug("Running health checks")

            # Get today's health data
            health_data = await self._get_health_data()

            if not health_data:
                logger.warning("No health data available - skipping health checks")
                return []

            alerts = []

            # Check readiness score
            readiness_alert = self._check_readiness(health_data)
            if readiness_alert:
                alerts.append(readiness_alert)

            # Check sleep duration
            sleep_alert = self._check_sleep(health_data)
            if sleep_alert:
                alerts.append(sleep_alert)

            # Check HRV deviation
            hrv_alert = self._check_hrv(health_data)
            if hrv_alert:
                alerts.append(hrv_alert)

            # Check stress level
            stress_alert = self._check_stress(health_data)
            if stress_alert:
                alerts.append(stress_alert)

            logger.info(f"Health checks complete: {len(alerts)} alerts generated")
            return alerts

        except Exception as e:
            logger.error(f"Health monitor check failed: {e}", exc_info=True)
            return []  # Graceful degradation

    async def _get_health_data(self) -> Optional[Dict[str, Any]]:
        """
        Get today's health data from cache or MCP.

        Returns:
            Dictionary with readiness, sleep, hrv data or None
        """
        try:
            # Try cache first
            data = await self._get_from_cache()
            if data:
                logger.debug("Using cached health data")
                return data

            # Fallback to MCP call (if implemented)
            logger.warning("Cache unavailable, MCP fallback not yet implemented")
            return None

        except Exception as e:
            logger.error(f"Failed to get health data: {e}")
            return None

    async def _get_from_cache(self) -> Optional[Dict[str, Any]]:
        """
        Read health data from SQLite cache database.

        Expected schema (from oura-mcp):
            - readiness_data: id, day, data (JSON), cached_at, expires_at
            - sleep_data: id, day, data (JSON), cached_at, expires_at
            - activity_data: id, day, data (JSON), cached_at, expires_at

        Returns:
            Health data dict or None if unavailable
        """
        if not self.cache_db_path.exists():
            logger.debug(f"Cache DB not found: {self.cache_db_path}")
            return None

        try:
            # Get today's date
            today = datetime.now().strftime('%Y-%m-%d')

            # Connect to cache database
            conn = sqlite3.connect(self.cache_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query readiness data (JSON blob)
            cursor.execute(
                "SELECT data FROM readiness_data WHERE day = ? ORDER BY day DESC LIMIT 1",
                (today,)
            )
            readiness_row = cursor.fetchone()

            # Query sleep data (JSON blob)
            cursor.execute(
                "SELECT data FROM sleep_data WHERE day = ? ORDER BY day DESC LIMIT 1",
                (today,)
            )
            sleep_row = cursor.fetchone()

            conn.close()

            # Parse results
            if not readiness_row and not sleep_row:
                logger.debug(f"No data for today ({today}) in cache")
                return None

            data = {
                'date': today,
                'readiness_score': None,
                'sleep_hours': None,
                'hrv': None,
                'stress_level': None
            }

            # Parse readiness JSON
            if readiness_row:
                readiness_json = json.loads(readiness_row['data'])
                data['readiness_score'] = readiness_json.get('score')

                # Check contributors for HRV
                contributors = readiness_json.get('contributors', {})
                hrv_balance = contributors.get('hrv_balance')
                if hrv_balance:
                    # HRV balance is 0-100, we want actual HRV value
                    # For now, store the balance score
                    data['hrv_balance'] = hrv_balance

            # Parse sleep JSON
            if sleep_row:
                sleep_json = json.loads(sleep_row['data'])
                # Total sleep in seconds
                total_sleep_seconds = sleep_json.get('total_sleep_duration', 0)
                data['sleep_hours'] = total_sleep_seconds / 3600.0
                data['sleep_score'] = sleep_json.get('score')

            logger.debug(f"Cache data: readiness={data['readiness_score']}, sleep={data['sleep_hours']}h")
            return data

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    def _check_readiness(self, health_data: Dict[str, Any]) -> Optional[Alert]:
        """
        Check readiness score and generate alert if below threshold.

        Args:
            health_data: Health metrics dictionary

        Returns:
            Alert if readiness is low, None otherwise
        """
        readiness = health_data.get('readiness_score')
        if readiness is None:
            return None

        if readiness < self.thresholds['readiness_critical']:
            return Alert(
                type='health',
                severity='critical',
                title='Critical: Very Low Readiness',
                message=(
                    f"Your readiness is {readiness} (Very Low). "
                    f"You're at risk of burnout. Rest today."
                ),
                data={
                    'readiness_score': readiness,
                    'threshold': self.thresholds['readiness_critical'],
                    'metric': 'readiness'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"health:readiness:critical:{health_data.get('date')}"
            )

        elif readiness < self.thresholds['readiness_warning']:
            return Alert(
                type='health',
                severity='warning',
                title='Low Readiness Detected',
                message=(
                    f"Your readiness is {readiness} (Low). "
                    f"Consider lighter tasks today."
                ),
                data={
                    'readiness_score': readiness,
                    'threshold': self.thresholds['readiness_warning'],
                    'metric': 'readiness'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"health:readiness:warning:{health_data.get('date')}"
            )

        return None

    def _check_sleep(self, health_data: Dict[str, Any]) -> Optional[Alert]:
        """
        Check sleep duration and generate alert if insufficient.

        Args:
            health_data: Health metrics dictionary

        Returns:
            Alert if sleep is insufficient, None otherwise
        """
        sleep_hours = health_data.get('sleep_hours')
        if sleep_hours is None:
            return None

        if sleep_hours < self.thresholds['sleep_hours_critical']:
            return Alert(
                type='health',
                severity='critical',
                title='Critical: Severe Sleep Debt',
                message=(
                    f"You slept only {sleep_hours:.1f} hours (target: 7-9h). "
                    f"Severe sleep debt detected. Prioritize rest."
                ),
                data={
                    'sleep_hours': sleep_hours,
                    'threshold': self.thresholds['sleep_hours_critical'],
                    'metric': 'sleep'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"health:sleep:critical:{health_data.get('date')}"
            )

        elif sleep_hours < self.thresholds['sleep_hours_warning']:
            return Alert(
                type='health',
                severity='warning',
                title='Sleep Deficit Detected',
                message=(
                    f"You slept {sleep_hours:.1f} hours (target: 7-9h). "
                    f"Consider an earlier bedtime tonight."
                ),
                data={
                    'sleep_hours': sleep_hours,
                    'threshold': self.thresholds['sleep_hours_warning'],
                    'metric': 'sleep'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"health:sleep:warning:{health_data.get('date')}"
            )

        return None

    def _check_hrv(self, health_data: Dict[str, Any]) -> Optional[Alert]:
        """
        Check HRV deviation from baseline.

        Note: HRV tracking requires baseline calculation over 30 days.
        Currently placeholder until HRV data available in cache.

        Args:
            health_data: Health metrics dictionary

        Returns:
            Alert if HRV deviation significant, None otherwise
        """
        hrv = health_data.get('hrv')
        if hrv is None:
            return None

        # TODO: Implement HRV baseline calculation
        # For now, return None
        return None

    def _check_stress(self, health_data: Dict[str, Any]) -> Optional[Alert]:
        """
        Check stress level from Oura data.

        Note: Stress data may be in separate table or not available.
        Currently placeholder.

        Args:
            health_data: Health metrics dictionary

        Returns:
            Alert if stress is high, None otherwise
        """
        stress = health_data.get('stress_level')
        if stress is None:
            return None

        if stress >= self.thresholds['stress_critical']:
            return Alert(
                type='health',
                severity='critical',
                title='Critical: Very High Stress',
                message=(
                    f"Your stress level is {stress}/100 (Very High). "
                    f"Take a break and practice stress reduction."
                ),
                data={
                    'stress_level': stress,
                    'threshold': self.thresholds['stress_critical'],
                    'metric': 'stress'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"health:stress:critical:{health_data.get('date')}"
            )

        elif stress >= self.thresholds['stress_warning']:
            return Alert(
                type='health',
                severity='warning',
                title='Elevated Stress Detected',
                message=(
                    f"Your stress level is {stress}/100. "
                    f"Consider taking breaks throughout the day."
                ),
                data={
                    'stress_level': stress,
                    'threshold': self.thresholds['stress_warning'],
                    'metric': 'stress'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"health:stress:warning:{health_data.get('date')}"
            )

        return None
