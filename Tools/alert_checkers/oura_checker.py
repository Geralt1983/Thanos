#!/usr/bin/env python3
"""
Oura Ring Alert Checker for Thanos.

Monitors health metrics from Oura Ring for alerting.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

from .base import ThresholdChecker, Alert

import sys
sys.path.insert(0, str(__file__).rsplit('/Tools', 1)[0])

from Tools.journal import EventType


class OuraChecker(ThresholdChecker):
    """Check Oura Ring health metrics for alerts."""

    source = "oura"
    check_interval = 1800  # 30 minutes (health data updates less frequently)

    # Thresholds based on Jeremy's baseline and health goals
    THRESHOLDS = {
        'readiness_score': {
            'warning': 65,
            'critical': 50,
            'comparison': 'below',
            'unit': ''
        },
        'sleep_score': {
            'warning': 70,
            'critical': 55,
            'comparison': 'below',
            'unit': ''
        },
        'hrv_balance': {
            'warning': 40,
            'critical': 25,
            'comparison': 'below',
            'unit': ''
        },
        'resting_heart_rate': {
            'warning': 65,
            'critical': 75,
            'comparison': 'above',
            'unit': ' bpm'
        },
        'sleep_efficiency': {
            'warning': 80,
            'critical': 70,
            'comparison': 'below',
            'unit': '%'
        },
        'deep_sleep_minutes': {
            'warning': 45,
            'critical': 30,
            'comparison': 'below',
            'unit': ' min'
        },
        'rem_sleep_minutes': {
            'warning': 60,
            'critical': 40,
            'comparison': 'below',
            'unit': ' min'
        }
    }

    def __init__(self, oura_adapter=None):
        """
        Initialize Oura checker.

        Args:
            oura_adapter: Optional OuraAdapter instance. If None, uses MCP.
        """
        super().__init__()
        self.oura_adapter = oura_adapter

    async def check(self) -> List[Alert]:
        """
        Run Oura health checks and return alerts.

        Checks:
        - Readiness score
        - Sleep score and quality
        - HRV balance
        - Activity levels
        - Recovery status
        - Stress indicators
        """
        alerts = []

        try:
            # Get today's readiness
            readiness = await self._get_readiness()
            if readiness:
                alerts.extend(self._check_readiness(readiness))

            # Get sleep data
            sleep = await self._get_sleep()
            if sleep:
                alerts.extend(self._check_sleep(sleep))

            # Get stress data
            stress = await self._get_stress()
            if stress:
                alerts.extend(self._check_stress(stress))

            # Check for declining trends
            trends = await self._get_weekly_trends()
            if trends:
                alerts.extend(self._check_trends(trends))

        except Exception as e:
            alerts.append(Alert(
                type=EventType.SYNC_FAILED,
                severity="warning",
                title=f"Oura check error: {str(e)[:50]}",
                data={'error': str(e), 'checker': self.source}
            ))

        return alerts

    async def _get_readiness(self) -> Optional[Dict[str, Any]]:
        """Get today's readiness data from Oura."""
        # Real implementation would use Oura MCP or adapter
        # return await self.oura_adapter.get_daily_readiness()
        return None

    async def _get_sleep(self) -> Optional[Dict[str, Any]]:
        """Get last night's sleep data from Oura."""
        return None

    async def _get_stress(self) -> Optional[Dict[str, Any]]:
        """Get today's stress data from Oura."""
        return None

    async def _get_weekly_trends(self) -> Optional[Dict[str, Any]]:
        """Get 7-day trends from Oura."""
        return None

    def _check_readiness(self, readiness: Dict[str, Any]) -> List[Alert]:
        """Check readiness metrics against thresholds."""
        alerts = []

        # Overall readiness score
        score = readiness.get('score')
        if score is not None:
            alert = self.check_threshold(
                value=score,
                warning_threshold=self.THRESHOLDS['readiness_score']['warning'],
                critical_threshold=self.THRESHOLDS['readiness_score']['critical'],
                metric_name="Readiness",
                comparison='below'
            )
            if alert:
                # Add recommendation based on contributing factors
                contributors = readiness.get('contributors', {})
                lowest_contributor = min(contributors.items(), key=lambda x: x[1]) if contributors else None
                if lowest_contributor:
                    alert.data['lowest_contributor'] = lowest_contributor[0]
                    alert.data['contributor_score'] = lowest_contributor[1]
                alerts.append(alert)

        # HRV balance
        hrv = readiness.get('contributors', {}).get('hrv_balance')
        if hrv is not None:
            alert = self.check_threshold(
                value=hrv,
                warning_threshold=self.THRESHOLDS['hrv_balance']['warning'],
                critical_threshold=self.THRESHOLDS['hrv_balance']['critical'],
                metric_name="HRV Balance",
                comparison='below'
            )
            if alert:
                alerts.append(alert)

        # Resting heart rate
        rhr = readiness.get('contributors', {}).get('resting_heart_rate')
        if rhr is not None:
            alert = self.check_threshold(
                value=rhr,
                warning_threshold=self.THRESHOLDS['resting_heart_rate']['warning'],
                critical_threshold=self.THRESHOLDS['resting_heart_rate']['critical'],
                metric_name="Resting HR",
                comparison='above',
                unit=' bpm'
            )
            if alert:
                alerts.append(alert)

        return alerts

    def _check_sleep(self, sleep: Dict[str, Any]) -> List[Alert]:
        """Check sleep metrics against thresholds."""
        alerts = []

        # Overall sleep score
        score = sleep.get('score')
        if score is not None:
            alert = self.check_threshold(
                value=score,
                warning_threshold=self.THRESHOLDS['sleep_score']['warning'],
                critical_threshold=self.THRESHOLDS['sleep_score']['critical'],
                metric_name="Sleep Score",
                comparison='below'
            )
            if alert:
                # Add sleep stage breakdown
                alert.data['total_sleep'] = sleep.get('total_sleep_duration')
                alert.data['deep_sleep'] = sleep.get('deep_sleep_duration')
                alert.data['rem_sleep'] = sleep.get('rem_sleep_duration')
                alerts.append(alert)

        # Check sleep duration
        total_minutes = sleep.get('total_sleep_duration', 0)
        if total_minutes and total_minutes < 360:  # Less than 6 hours
            severity = "critical" if total_minutes < 300 else "warning"
            hours = total_minutes / 60
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity=severity,
                title=f"Low sleep: {hours:.1f}h (target: 7-8h)",
                data={
                    'sleep_minutes': total_minutes,
                    'sleep_hours': hours,
                    'target_hours': 7.5
                },
                dedup_key=f"oura:low_sleep:{severity}"
            ))

        # Check deep sleep
        deep_minutes = sleep.get('deep_sleep_duration', 0)
        if deep_minutes is not None:
            alert = self.check_threshold(
                value=deep_minutes,
                warning_threshold=self.THRESHOLDS['deep_sleep_minutes']['warning'],
                critical_threshold=self.THRESHOLDS['deep_sleep_minutes']['critical'],
                metric_name="Deep Sleep",
                comparison='below',
                unit=' min'
            )
            if alert:
                alerts.append(alert)

        # Check sleep efficiency
        efficiency = sleep.get('efficiency')
        if efficiency is not None:
            alert = self.check_threshold(
                value=efficiency,
                warning_threshold=self.THRESHOLDS['sleep_efficiency']['warning'],
                critical_threshold=self.THRESHOLDS['sleep_efficiency']['critical'],
                metric_name="Sleep Efficiency",
                comparison='below',
                unit='%'
            )
            if alert:
                alerts.append(alert)

        return alerts

    def _check_stress(self, stress: Dict[str, Any]) -> List[Alert]:
        """Check stress metrics for alerts."""
        alerts = []

        high_stress_minutes = stress.get('stress_high', 0)
        recovery_minutes = stress.get('recovery_high', 0)

        # Alert if high stress with no recovery
        if high_stress_minutes > 60 and recovery_minutes < 15:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="warning",
                title=f"High stress ({high_stress_minutes}min) with low recovery ({recovery_minutes}min)",
                data={
                    'high_stress_minutes': high_stress_minutes,
                    'recovery_minutes': recovery_minutes,
                    'stress_ratio': high_stress_minutes / max(recovery_minutes, 1)
                },
                dedup_key="oura:high_stress_low_recovery"
            ))

        # Sustained high stress
        if high_stress_minutes > 120:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="critical",
                title=f"Sustained high stress: {high_stress_minutes} minutes today",
                data={
                    'high_stress_minutes': high_stress_minutes,
                    'recommendation': 'Consider a break or stress-relief activity'
                },
                dedup_key="oura:sustained_high_stress"
            ))

        return alerts

    def _check_trends(self, trends: Dict[str, Any]) -> List[Alert]:
        """Check 7-day trends for concerning patterns."""
        alerts = []

        # Check for declining readiness trend
        readiness_trend = trends.get('readiness_trend', [])
        if len(readiness_trend) >= 5:
            # Check if last 5 days are declining
            is_declining = all(
                readiness_trend[i] > readiness_trend[i + 1]
                for i in range(len(readiness_trend) - 4, len(readiness_trend) - 1)
            )
            if is_declining:
                alerts.append(Alert(
                    type=EventType.HEALTH_ALERT,
                    severity="warning",
                    title="Declining readiness trend over 5 days",
                    data={
                        'trend': readiness_trend[-5:],
                        'recommendation': 'Prioritize recovery'
                    },
                    dedup_key="oura:declining_readiness_trend"
                ))

        # Check for sleep debt accumulation
        sleep_scores = trends.get('sleep_scores', [])
        if len(sleep_scores) >= 3:
            recent_avg = sum(sleep_scores[-3:]) / 3
            if recent_avg < 65:
                alerts.append(Alert(
                    type=EventType.HEALTH_ALERT,
                    severity="warning",
                    title=f"Sleep debt accumulating: 3-day avg {recent_avg:.0f}",
                    data={
                        'recent_scores': sleep_scores[-3:],
                        'average': recent_avg,
                        'recommendation': 'Prioritize sleep tonight'
                    },
                    dedup_key="oura:sleep_debt"
                ))

        return alerts
