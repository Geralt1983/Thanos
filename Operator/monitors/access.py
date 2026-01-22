#!/usr/bin/env python3
"""
Access Monitor - Thanos Operator Daemon

Monitors Phase 4 access layer (tmux, ttyd, Tailscale) for availability
and generates alerts when remote access components fail.

Architecture:
    - Uses AccessCoordinator to check component health
    - Monitors tmux sessions, ttyd daemon, Tailscale VPN
    - Graceful degradation on errors (returns empty alert list)

Alert Triggers:
    - Ttyd daemon down: High priority (remote access broken)
    - Tailscale disconnected: Critical priority (VPN access lost)
    - No tmux sessions: Medium priority (session persistence issue)
    - Component health degraded: Info priority (performance issue)

Integration:
    - Uses Access/access_coordinator.py for health checks
    - No MCP dependencies (local system checks only)
    - Fast execution (<100ms typical)
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Add project to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import circuit breaker for consistency
from Tools.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Alert data structure for Operator daemon."""
    type: str  # 'health', 'task', 'pattern', 'access'
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


class AccessMonitor:
    """
    Monitor Phase 4 access layer for remote access availability.

    Data Flow:
        1. Import AccessCoordinator dynamically (avoid circular deps)
        2. Query component health (tmux, ttyd, Tailscale)
        3. Generate alerts for degraded/failed components
        4. Return empty list on complete failure (graceful degradation)

    Thresholds:
        - ttyd_down: High priority (remote web access broken)
        - tailscale_disconnected: Critical priority (VPN lost)
        - no_tmux_sessions: Medium priority (persistence issue)
    """

    def __init__(
        self,
        circuit: CircuitBreaker,
        thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Access Monitor.

        Args:
            circuit: Circuit breaker (unused, for consistency)
            thresholds: Custom thresholds (reserved for future use)
        """
        self.circuit = circuit

        # Default thresholds (future extensibility)
        self.thresholds = {
            'ttyd_check_enabled': True,
            'tailscale_check_enabled': True,
            'tmux_check_enabled': True,
        }

        if thresholds:
            self.thresholds.update(thresholds)

        logger.info(
            f"AccessMonitor initialized: thresholds={self.thresholds}"
        )

    async def check(self) -> List[Alert]:
        """
        Run access layer checks and generate alerts.

        Returns:
            List of Alert objects (empty on errors - graceful degradation)
        """
        try:
            logger.debug("Running access layer checks")

            # Dynamically import to avoid circular dependencies
            try:
                from Access.access_coordinator import AccessCoordinator
            except ImportError as e:
                logger.error(f"Failed to import AccessCoordinator: {e}")
                return []  # Graceful degradation

            # Get access layer status
            try:
                coordinator = AccessCoordinator()
                status = coordinator.get_full_status()
            except Exception as e:
                logger.error(f"Failed to get access status: {e}")
                return []  # Graceful degradation

            alerts = []

            # Check ttyd (web terminal)
            if self.thresholds['ttyd_check_enabled']:
                ttyd_alerts = self._check_ttyd_health(status)
                alerts.extend(ttyd_alerts)

            # Check Tailscale (VPN)
            if self.thresholds['tailscale_check_enabled']:
                tailscale_alerts = self._check_tailscale_health(status)
                alerts.extend(tailscale_alerts)

            # Check tmux (session persistence)
            if self.thresholds['tmux_check_enabled']:
                tmux_alerts = self._check_tmux_health(status)
                alerts.extend(tmux_alerts)

            logger.info(f"Access checks complete: {len(alerts)} alerts generated")
            return alerts

        except Exception as e:
            logger.error(f"Access monitor check failed: {e}", exc_info=True)
            return []  # Graceful degradation

    def _check_ttyd_health(self, status: Dict[str, Any]) -> List[Alert]:
        """
        Check ttyd web terminal daemon health.

        Args:
            status: Full status dictionary from AccessCoordinator

        Returns:
            List of Alert objects for ttyd issues
        """
        alerts = []
        ttyd = status.get('components', {}).get('ttyd', {})

        if not ttyd.get('available'):
            # Ttyd not installed - info only (not all systems need it)
            alert = Alert(
                type='access',
                severity='info',
                title='Ttyd Not Installed',
                message=(
                    "Web terminal (ttyd) is not installed. "
                    "Remote browser access unavailable."
                ),
                data={
                    'component': 'ttyd',
                    'metric': 'availability',
                    'available': False
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:ttyd_unavailable:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        elif not ttyd.get('running'):
            # Ttyd installed but not running - high priority
            alert = Alert(
                type='access',
                severity='high',
                title='Web Terminal Offline',
                message=(
                    "Ttyd daemon is not running. "
                    "Remote web access broken. Start with: thanos-web start"
                ),
                data={
                    'component': 'ttyd',
                    'metric': 'daemon_status',
                    'running': False,
                    'resolution': 'thanos-web start'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:ttyd_down:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        elif not ttyd.get('healthy'):
            # Ttyd running but unhealthy - warning
            issues = ttyd.get('issues', [])
            alert = Alert(
                type='access',
                severity='warning',
                title='Web Terminal Degraded',
                message=(
                    f"Ttyd daemon health check failed: {', '.join(issues)}. "
                    f"Remote access may be unreliable."
                ),
                data={
                    'component': 'ttyd',
                    'metric': 'health_check',
                    'healthy': False,
                    'issues': issues
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:ttyd_degraded:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        return alerts

    def _check_tailscale_health(self, status: Dict[str, Any]) -> List[Alert]:
        """
        Check Tailscale VPN connection health.

        Args:
            status: Full status dictionary from AccessCoordinator

        Returns:
            List of Alert objects for Tailscale issues
        """
        alerts = []
        tailscale = status.get('components', {}).get('tailscale', {})

        if not tailscale.get('available'):
            # Tailscale not installed - info only
            alert = Alert(
                type='access',
                severity='info',
                title='Tailscale Not Installed',
                message=(
                    "VPN (Tailscale) is not installed. "
                    "Remote network access unavailable."
                ),
                data={
                    'component': 'tailscale',
                    'metric': 'availability',
                    'available': False
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:tailscale_unavailable:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        elif not tailscale.get('running'):
            # Tailscale installed but not connected - critical
            alert = Alert(
                type='access',
                severity='critical',
                title='VPN Disconnected',
                message=(
                    "Tailscale VPN is not connected. "
                    "Remote access via mobile/laptop broken. Connect with: thanos-vpn connect"
                ),
                data={
                    'component': 'tailscale',
                    'metric': 'connection_status',
                    'running': False,
                    'resolution': 'thanos-vpn connect'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:tailscale_down:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        elif not tailscale.get('healthy'):
            # Tailscale connected but unhealthy - warning
            issues = tailscale.get('issues', [])
            alert = Alert(
                type='access',
                severity='warning',
                title='VPN Connection Degraded',
                message=(
                    f"Tailscale health check failed: {', '.join(issues)}. "
                    f"Remote access may be unreliable."
                ),
                data={
                    'component': 'tailscale',
                    'metric': 'health_check',
                    'healthy': False,
                    'issues': issues
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:tailscale_degraded:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        return alerts

    def _check_tmux_health(self, status: Dict[str, Any]) -> List[Alert]:
        """
        Check tmux session persistence health.

        Args:
            status: Full status dictionary from AccessCoordinator

        Returns:
            List of Alert objects for tmux issues
        """
        alerts = []
        tmux = status.get('components', {}).get('tmux', {})

        if not tmux.get('available'):
            # Tmux not installed - warning (core component)
            alert = Alert(
                type='access',
                severity='warning',
                title='Tmux Not Installed',
                message=(
                    "Session manager (tmux) is not installed. "
                    "Session persistence unavailable. Install with: brew install tmux"
                ),
                data={
                    'component': 'tmux',
                    'metric': 'availability',
                    'available': False,
                    'resolution': 'brew install tmux'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:tmux_unavailable:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        elif not tmux.get('running'):
            # Tmux installed but no sessions - medium priority
            # (Could be normal if user hasn't started session yet)
            alert = Alert(
                type='access',
                severity='medium',
                title='No Tmux Sessions',
                message=(
                    "No tmux sessions running. "
                    "Session persistence inactive. Start with: thanos-tmux"
                ),
                data={
                    'component': 'tmux',
                    'metric': 'session_count',
                    'running': False,
                    'resolution': 'thanos-tmux'
                },
                timestamp=datetime.now().isoformat(),
                dedup_key=f"access:tmux_no_sessions:{datetime.now().strftime('%Y-%m-%d')}"
            )
            alerts.append(alert)

        return alerts
