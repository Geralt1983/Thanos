#!/usr/bin/env python3
"""
Thanos Background Alert Daemon.

Continuous monitoring process that runs alert checkers and logs to journal.
Designed to run every 15 minutes via cron, launchd, or systemd.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict
import logging

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.journal import Journal, EventType, Severity
from Tools.alert_checkers import AlertChecker, Alert, WorkOSChecker, OuraChecker, CalendarChecker


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('alert_daemon')


@dataclass
class DaemonConfig:
    """Configuration for the alert daemon."""
    check_interval: int = 900  # 15 minutes default
    dedup_window: int = 3600  # 1 hour dedup window
    max_alerts_per_run: int = 20  # Prevent alert storms
    state_file: str = "State/daemon_state.json"
    enabled_checkers: List[str] = field(default_factory=lambda: ['workos', 'oura', 'calendar'])

    # Severity thresholds for notifications
    notify_severities: List[str] = field(default_factory=lambda: ['warning', 'alert', 'critical'])

    # Quiet hours (no non-critical alerts)
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 7     # 7 AM


@dataclass
class DaemonState:
    """Persistent state for the daemon."""
    last_run: Optional[str] = None
    run_count: int = 0
    total_alerts: int = 0
    recent_dedup_keys: Dict[str, str] = field(default_factory=dict)  # key -> timestamp
    checker_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DaemonState':
        return cls(**data)


class AlertDaemon:
    """
    Background daemon that runs alert checkers periodically.

    Features:
    - Configurable check intervals per checker
    - Alert deduplication within time window
    - Quiet hours support
    - Persistent state across runs
    - Journal integration for all alerts
    """

    def __init__(self, config: Optional[DaemonConfig] = None):
        """
        Initialize the alert daemon.

        Args:
            config: Optional DaemonConfig. Uses defaults if None.
        """
        self.config = config or DaemonConfig()
        self.state = DaemonState()
        self.journal = Journal()
        self.checkers: List[AlertChecker] = []

        # Initialize state file path
        self.state_path = Path(__file__).parent.parent / self.config.state_file

        # Load persistent state
        self._load_state()

        # Initialize checkers
        self._init_checkers()

    def _init_checkers(self):
        """Initialize enabled alert checkers."""
        checker_map = {
            'workos': WorkOSChecker,
            'oura': OuraChecker,
            'calendar': CalendarChecker
        }

        for checker_name in self.config.enabled_checkers:
            if checker_name in checker_map:
                try:
                    checker = checker_map[checker_name]()
                    self.checkers.append(checker)
                    logger.info(f"Initialized checker: {checker_name}")
                except Exception as e:
                    logger.error(f"Failed to initialize {checker_name}: {e}")

    def _load_state(self):
        """Load persistent state from file."""
        try:
            if self.state_path.exists():
                with open(self.state_path) as f:
                    data = json.load(f)
                    self.state = DaemonState.from_dict(data)
                    logger.debug(f"Loaded daemon state: {self.state.run_count} previous runs")
        except Exception as e:
            logger.warning(f"Could not load daemon state: {e}")
            self.state = DaemonState()

    def _save_state(self):
        """Save daemon state to file."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Could not save daemon state: {e}")

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        hour = datetime.now().hour
        if self.config.quiet_hours_start > self.config.quiet_hours_end:
            # Spans midnight (e.g., 22-7)
            return hour >= self.config.quiet_hours_start or hour < self.config.quiet_hours_end
        else:
            return self.config.quiet_hours_start <= hour < self.config.quiet_hours_end

    def _clean_dedup_cache(self):
        """Remove expired dedup keys."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.config.dedup_window)
        cutoff_str = cutoff.isoformat()

        expired = [
            key for key, timestamp in self.state.recent_dedup_keys.items()
            if timestamp < cutoff_str
        ]

        for key in expired:
            del self.state.recent_dedup_keys[key]

        if expired:
            logger.debug(f"Cleaned {len(expired)} expired dedup keys")

    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate within dedup window."""
        if not alert.dedup_key:
            return False
        return alert.dedup_key in self.state.recent_dedup_keys

    def _record_alert(self, alert: Alert):
        """Record alert in dedup cache."""
        if alert.dedup_key:
            self.state.recent_dedup_keys[alert.dedup_key] = datetime.now().isoformat()

    def _should_notify(self, alert: Alert) -> bool:
        """Determine if alert should trigger notification."""
        # Check severity threshold
        if alert.severity not in self.config.notify_severities:
            return False

        # Check quiet hours (only critical alerts during quiet hours)
        if self._is_quiet_hours() and alert.severity != 'critical':
            return False

        return True

    async def run_once(self) -> List[Alert]:
        """
        Run all checkers once and return alerts.

        Returns:
            List of non-duplicate alerts from all checkers.
        """
        start_time = time.time()
        all_alerts: List[Alert] = []

        # Clean dedup cache
        self._clean_dedup_cache()

        # Run each checker
        for checker in self.checkers:
            try:
                checker_start = time.time()
                alerts = await checker.safe_check()
                checker_time = time.time() - checker_start

                # Filter duplicates
                new_alerts = []
                for alert in alerts:
                    if not self._is_duplicate(alert):
                        new_alerts.append(alert)
                        self._record_alert(alert)
                    else:
                        logger.debug(f"Skipping duplicate: {alert.dedup_key}")

                all_alerts.extend(new_alerts)

                # Update checker state
                self.state.checker_states[checker.source] = {
                    'last_check': datetime.now().isoformat(),
                    'duration_ms': int(checker_time * 1000),
                    'alerts_generated': len(alerts),
                    'alerts_after_dedup': len(new_alerts),
                    'error': str(checker.last_error) if checker.last_error else None
                }

                logger.info(f"Checker {checker.source}: {len(new_alerts)} alerts ({checker_time:.2f}s)")

            except Exception as e:
                logger.error(f"Checker {checker.source} failed: {e}")

        # Limit alert storm
        if len(all_alerts) > self.config.max_alerts_per_run:
            logger.warning(f"Alert storm: {len(all_alerts)} alerts, limiting to {self.config.max_alerts_per_run}")
            # Prioritize by severity
            severity_order = {'critical': 0, 'alert': 1, 'warning': 2, 'info': 3, 'debug': 4}
            all_alerts.sort(key=lambda a: severity_order.get(a.severity, 5))
            all_alerts = all_alerts[:self.config.max_alerts_per_run]

        # Log alerts to journal
        for alert in all_alerts:
            try:
                severity = Severity[alert.severity.upper()] if hasattr(Severity, alert.severity.upper()) else Severity.INFO
                self.journal.log(
                    event_type=alert.type,
                    message=alert.title,
                    data=alert.data,
                    severity=severity,
                    source=f"daemon:{alert.data.get('checker', 'unknown')}"
                )
            except Exception as e:
                logger.error(f"Failed to log alert to journal: {e}")

        # Update daemon state
        self.state.last_run = datetime.now().isoformat()
        self.state.run_count += 1
        self.state.total_alerts += len(all_alerts)

        # Save state
        self._save_state()

        total_time = time.time() - start_time
        logger.info(f"Daemon run complete: {len(all_alerts)} alerts in {total_time:.2f}s")

        return all_alerts

    async def run_continuous(self, max_runs: Optional[int] = None):
        """
        Run daemon continuously with configured interval.

        Args:
            max_runs: Optional limit on number of runs. None for infinite.
        """
        runs = 0

        while max_runs is None or runs < max_runs:
            try:
                alerts = await self.run_once()

                # Send notifications for qualifying alerts
                for alert in alerts:
                    if self._should_notify(alert):
                        await self._send_notification(alert)

                runs += 1

                # Wait for next interval
                await asyncio.sleep(self.config.check_interval)

            except KeyboardInterrupt:
                logger.info("Daemon stopped by user")
                break
            except Exception as e:
                logger.error(f"Daemon run failed: {e}")
                # Wait before retry
                await asyncio.sleep(60)

    async def _send_notification(self, alert: Alert):
        """
        Send notification for alert.

        This is a placeholder - integrate with actual notification system.
        """
        # TODO: Integrate with Telegram bot, push notifications, etc.
        logger.info(f"NOTIFICATION [{alert.severity.upper()}]: {alert.title}")

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status for monitoring."""
        return {
            'last_run': self.state.last_run,
            'run_count': self.state.run_count,
            'total_alerts': self.state.total_alerts,
            'enabled_checkers': self.config.enabled_checkers,
            'checker_states': self.state.checker_states,
            'dedup_cache_size': len(self.state.recent_dedup_keys),
            'is_quiet_hours': self._is_quiet_hours(),
            'checkers': [
                checker.get_status() for checker in self.checkers
            ]
        }


async def main():
    """Run the alert daemon."""
    import argparse

    parser = argparse.ArgumentParser(description='Thanos Alert Daemon')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=900, help='Check interval in seconds')
    parser.add_argument('--checkers', nargs='+', help='Enable specific checkers')
    parser.add_argument('--status', action='store_true', help='Show daemon status and exit')
    args = parser.parse_args()

    # Build config
    config = DaemonConfig(
        check_interval=args.interval,
        enabled_checkers=args.checkers or ['workos', 'oura', 'calendar']
    )

    daemon = AlertDaemon(config)

    if args.status:
        status = daemon.get_status()
        print(json.dumps(status, indent=2))
        return

    if args.once:
        alerts = await daemon.run_once()
        print(f"\n=== {len(alerts)} Alert(s) ===")
        for alert in alerts:
            print(f"[{alert.severity.upper()}] {alert.title}")
    else:
        print(f"Starting alert daemon (interval: {config.check_interval}s)")
        await daemon.run_continuous()


if __name__ == '__main__':
    asyncio.run(main())
