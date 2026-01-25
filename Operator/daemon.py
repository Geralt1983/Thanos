#!/usr/bin/env python3
"""
Operator Daemon - Thanos v2.0 Phase 3

Background process that continuously monitors health metrics, task deadlines,
and procrastination patterns. Provides proactive alerts via Telegram and
macOS notifications while integrating with MCP servers (WorkOS, Oura).

Usage:
    # Run once (testing)
    python Operator/daemon.py --dry-run --verbose

    # Run continuous (production)
    python Operator/daemon.py --config Operator/config.yaml

    # Via LaunchAgent (recommended)
    launchctl start com.thanos.operator

Architecture:
    - AsyncIO-based event loop with configurable intervals
    - Circuit breaker integration for resilient MCP calls
    - Alert deduplication within configurable time windows
    - State persistence across restarts
    - Graceful shutdown on SIGTERM/SIGINT
"""

import asyncio
import signal
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.journal import Journal, EventType, Severity
from Tools.circuit_breaker import CircuitBreaker, CircuitState
from Operator.alerters import (
    Alert as AlerterAlert,
    AlerterInterface,
    AlertSeverity,
    TelegramAlerter,
    NotificationAlerter,
    JournalAlerter,
)


# Configure logging
def setup_logging(log_path: Path, verbose: bool = False) -> logging.Logger:
    """Setup logging with file and console handlers."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create logger
    logger = logging.getLogger('operator')
    logger.setLevel(level)

    # File handler with rotation
    from logging.handlers import RotatingFileHandler
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


@dataclass
class OperatorConfig:
    """Configuration for the Operator daemon."""
    # Check intervals (seconds)
    check_interval: int = 300  # 5 minutes default
    health_check_interval: int = 900  # 15 minutes
    task_check_interval: int = 900  # 15 minutes
    pattern_check_interval: int = 1800  # 30 minutes

    # Deduplication
    dedup_window_seconds: int = 3600  # 1 hour
    max_alerts_per_run: int = 20

    # Quiet hours
    quiet_hours_enabled: bool = True
    quiet_hours_start: int = 22  # 10 PM
    quiet_hours_end: int = 7  # 7 AM

    # Enabled monitors
    enabled_monitors: List[str] = field(default_factory=lambda: ['health', 'tasks', 'patterns', 'access', 'checkpoint'])

    # Paths
    state_file: str = "State/operator_state.json"
    log_file: str = "logs/operator.log"
    pid_file: str = "logs/operator.pid"

    # Circuit breaker settings
    circuit_failure_threshold: int = 3
    circuit_timeout_seconds: int = 60
    circuit_half_open_attempts: int = 1

    @classmethod
    def from_yaml(cls, config_path: Path) -> 'OperatorConfig':
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(config_path) as f:
                data = yaml.safe_load(f)

            # Extract relevant sections
            intervals = data.get('intervals', {})
            dedup = data.get('deduplication', {})
            quiet = data.get('quiet_hours', {})
            monitors = data.get('monitors', {})
            circuit = data.get('circuit_breaker', {})

            # Build config
            return cls(
                check_interval=intervals.get('check_interval', 300),
                health_check_interval=intervals.get('health_check', 900),
                task_check_interval=intervals.get('task_check', 900),
                pattern_check_interval=intervals.get('pattern_check', 1800),
                dedup_window_seconds=dedup.get('window_seconds', 3600),
                max_alerts_per_run=dedup.get('max_alerts_per_run', 20),
                quiet_hours_enabled=quiet.get('enabled', True),
                quiet_hours_start=quiet.get('start', 22),
                quiet_hours_end=quiet.get('end', 7),
                enabled_monitors=[
                    name for name, config in monitors.items()
                    if config.get('enabled', True)
                ],
                circuit_failure_threshold=circuit.get('failure_threshold', 3),
                circuit_timeout_seconds=circuit.get('timeout_seconds', 60),
                circuit_half_open_attempts=circuit.get('half_open_attempts', 1)
            )

        except ImportError:
            raise ImportError("PyYAML not installed. Install with: pip install pyyaml")
        except Exception as e:
            raise ValueError(f"Failed to load config from {config_path}: {e}")


@dataclass
class DaemonState:
    """Persistent state for the daemon."""
    last_run: Optional[str] = None
    run_count: int = 0
    total_alerts: int = 0
    uptime_start: Optional[str] = None
    recent_dedup_keys: Dict[str, str] = field(default_factory=dict)  # key -> timestamp
    monitor_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    circuit_states: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DaemonState':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Alert:
    """Alert generated by monitors."""
    title: str
    message: str
    priority: str  # 'low', 'medium', 'high', 'critical'
    alert_type: str
    entity_id: Optional[str] = None
    dedup_key: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class OperatorDaemon:
    """
    Main Operator daemon process.

    Coordinates monitoring cycle:
        monitors → analyze → deduplicate → alert → persist
    """

    def __init__(
        self,
        config: OperatorConfig,
        dry_run: bool = False,
        verbose: bool = False
    ):
        """
        Initialize the Operator daemon.

        Args:
            config: Daemon configuration
            dry_run: If True, don't send alerts (testing mode)
            verbose: Enable verbose logging
        """
        self.config = config
        self.dry_run = dry_run
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Setup logging
        thanos_root = Path(__file__).parent.parent
        log_path = thanos_root / config.log_file
        self.logger = setup_logging(log_path, verbose)

        self.logger.info("=" * 60)
        self.logger.info("OPERATOR DAEMON INITIALIZING")
        self.logger.info("=" * 60)
        if dry_run:
            self.logger.warning("DRY RUN MODE - No alerts will be sent")

        # Initialize components
        self.state = DaemonState()
        self.journal = Journal()
        self.monitors: List[Any] = []
        self.alerters: List[Any] = []
        self.circuits: Dict[str, CircuitBreaker] = {}

        # Paths
        self.state_path = thanos_root / config.state_file
        self.pid_path = thanos_root / config.pid_file

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Load state and initialize components
        self._load_state()
        self._init_circuits()
        self._init_monitors()
        self._init_alerters()

        self.logger.info(f"Initialized with {len(self.monitors)} monitors, {len(self.alerters)} alerters")

    def _handle_shutdown(self, signum: int, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_event.set()

    def _load_state(self):
        """Load persistent state from file."""
        try:
            if self.state_path.exists():
                with open(self.state_path) as f:
                    data = json.load(f)
                    self.state = DaemonState.from_dict(data)
                    self.logger.info(f"Loaded state: {self.state.run_count} previous runs")
            else:
                self.logger.info("No previous state found, starting fresh")
                self.state.uptime_start = datetime.now().isoformat()
        except Exception as e:
            self.logger.warning(f"Could not load state: {e}, starting fresh")
            self.state = DaemonState()
            self.state.uptime_start = datetime.now().isoformat()

    def _save_state(self):
        """Save daemon state to file."""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_path, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            self.logger.error(f"Could not save state: {e}")

    def _init_circuits(self):
        """Initialize circuit breakers for MCP connections."""
        self.logger.debug("Initializing circuit breakers")

        # Circuit for WorkOS MCP
        self.circuits['workos'] = CircuitBreaker(
            name='workos_mcp',
            failure_threshold=self.config.circuit_failure_threshold,
            recovery_timeout=self.config.circuit_timeout_seconds,
            half_open_max_calls=self.config.circuit_half_open_attempts
        )

        # Circuit for Oura MCP
        self.circuits['oura'] = CircuitBreaker(
            name='oura_mcp',
            failure_threshold=self.config.circuit_failure_threshold,
            recovery_timeout=self.config.circuit_timeout_seconds,
            half_open_max_calls=self.config.circuit_half_open_attempts
        )

        self.logger.info(f"Initialized {len(self.circuits)} circuit breakers")

    def _init_monitors(self):
        """Initialize enabled monitors."""
        self.logger.debug("Initializing monitors")

        # Import monitor classes
        try:
            from Operator.monitors import HealthMonitor, TaskMonitor, PatternMonitor, AccessMonitor, CheckpointMonitor

            for monitor_name in self.config.enabled_monitors:
                self.logger.info(f"Initializing monitor: {monitor_name}")

                if monitor_name == 'health':
                    monitor = HealthMonitor(
                        circuit=self.circuits['oura']
                    )
                    self.monitors.append(monitor)
                    self.logger.info(f"✓ HealthMonitor initialized")

                elif monitor_name == 'tasks':
                    monitor = TaskMonitor(
                        circuit=self.circuits['workos']
                    )
                    self.monitors.append(monitor)
                    self.logger.info(f"✓ TaskMonitor initialized")

                elif monitor_name == 'patterns':
                    monitor = PatternMonitor()
                    self.monitors.append(monitor)
                    self.logger.info(f"✓ PatternMonitor initialized")

                elif monitor_name == 'access':
                    # AccessMonitor uses workos circuit for consistency
                    # (though local checks don't need circuit breaker)
                    monitor = AccessMonitor(
                        circuit=self.circuits['workos']
                    )
                    self.monitors.append(monitor)
                    self.logger.info(f"✓ AccessMonitor initialized")

                elif monitor_name == 'checkpoint':
                    # CheckpointMonitor for session crash recovery
                    monitor = CheckpointMonitor(
                        circuit=self.circuits['workos'],
                        config={
                            'process_orphans': True,
                            'orphan_threshold_hours': 2.0,
                            'max_orphans_per_run': 5
                        }
                    )
                    self.monitors.append(monitor)
                    self.logger.info(f"✓ CheckpointMonitor initialized")

                else:
                    self.logger.warning(f"Unknown monitor type: {monitor_name}")

        except Exception as e:
            self.logger.error(f"Failed to initialize monitors: {e}", exc_info=True)

    def _init_alerters(self):
        """Initialize enabled alerters."""
        self.logger.debug("Initializing alerters")

        # Placeholder - actual alerters will be in Operator/alerters/
        # For now, just log what would be initialized
        self.logger.info("Alerters: telegram, macos, journal")
        # TODO: Actual alerter initialization
        # from Operator.alerters import TelegramAlerter, MacOSAlerter, JournalAlerter

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        if not self.config.quiet_hours_enabled:
            return False

        hour = datetime.now().hour
        start = self.config.quiet_hours_start
        end = self.config.quiet_hours_end

        if start > end:
            # Spans midnight (e.g., 22-7)
            return hour >= start or hour < end
        else:
            return start <= hour < end

    def _clean_dedup_cache(self):
        """Remove expired deduplication keys."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.config.dedup_window_seconds)
        cutoff_str = cutoff.isoformat()

        expired = [
            key for key, timestamp in self.state.recent_dedup_keys.items()
            if timestamp < cutoff_str
        ]

        for key in expired:
            del self.state.recent_dedup_keys[key]

        if expired:
            self.logger.debug(f"Cleaned {len(expired)} expired dedup keys")

    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate within dedup window."""
        if not alert.dedup_key:
            return False
        return alert.dedup_key in self.state.recent_dedup_keys

    def _record_alert(self, alert: Alert):
        """Record alert in dedup cache."""
        if alert.dedup_key:
            self.state.recent_dedup_keys[alert.dedup_key] = datetime.now().isoformat()

    async def _run_monitors(self) -> List[Alert]:
        """Run all enabled monitors and collect alerts."""
        all_alerts: List[Alert] = []

        for monitor in self.monitors:
            try:
                self.logger.debug(f"Running monitor: {monitor.__class__.__name__}")
                alerts = await monitor.check()
                all_alerts.extend(alerts)
                self.logger.debug(f"Monitor {monitor.__class__.__name__}: {len(alerts)} alerts")
            except Exception as e:
                self.logger.error(f"Monitor {monitor.__class__.__name__} failed: {e}")

        return all_alerts

    async def _send_alerts(self, alerts: List[Alert]):
        """Send alerts through enabled alerters."""
        if self.dry_run:
            self.logger.info(f"DRY RUN: Would send {len(alerts)} alerts")
            for alert in alerts:
                self.logger.info(f"  [{alert.priority.upper()}] {alert.title}")
            return

        for alerter in self.alerters:
            try:
                await alerter.send_batch(alerts)
            except Exception as e:
                self.logger.error(f"Alerter {alerter.__class__.__name__} failed: {e}")

    async def check_cycle(self):
        """Run one complete check cycle."""
        cycle_start = datetime.now()
        self.logger.info("=" * 60)
        self.logger.info(f"CHECK CYCLE START - {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 60)

        try:
            # Clean deduplication cache
            self._clean_dedup_cache()

            # Run monitors and collect alerts
            all_alerts = await self._run_monitors()
            self.logger.info(f"Monitors generated {len(all_alerts)} total alerts")

            # Filter duplicates
            new_alerts = []
            for alert in all_alerts:
                if not self._is_duplicate(alert):
                    new_alerts.append(alert)
                    self._record_alert(alert)
                else:
                    self.logger.debug(f"Filtered duplicate: {alert.dedup_key}")

            self.logger.info(f"After deduplication: {len(new_alerts)} new alerts")

            # Apply alert storm prevention
            if len(new_alerts) > self.config.max_alerts_per_run:
                self.logger.warning(
                    f"Alert storm detected: {len(new_alerts)} alerts, "
                    f"limiting to {self.config.max_alerts_per_run}"
                )
                # Prioritize by priority
                priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
                new_alerts.sort(key=lambda a: priority_order.get(a.priority, 4))
                new_alerts = new_alerts[:self.config.max_alerts_per_run]

            # Filter by quiet hours
            if self._is_quiet_hours():
                self.logger.info("Quiet hours active - filtering non-critical alerts")
                new_alerts = [a for a in new_alerts if a.priority == 'critical']
                self.logger.info(f"After quiet hours filter: {len(new_alerts)} alerts")

            # Send alerts
            await self._send_alerts(new_alerts)

            # Update state
            self.state.last_run = cycle_start.isoformat()
            self.state.run_count += 1
            self.state.total_alerts += len(new_alerts)

            # Update circuit states
            for name, circuit in self.circuits.items():
                self.state.circuit_states[name] = circuit.state.value

            # Save state
            self._save_state()

            # Log cycle completion
            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            self.logger.info(
                f"Check cycle complete: {len(new_alerts)} alerts sent "
                f"({cycle_duration:.2f}s)"
            )

        except Exception as e:
            self.logger.error(f"Check cycle failed: {e}", exc_info=True)

    async def run(self):
        """Main daemon loop with graceful shutdown."""
        self.running = True
        self.logger.info("Operator daemon started")

        # Write PID file
        try:
            self.pid_path.parent.mkdir(parents=True, exist_ok=True)
            self.pid_path.write_text(str(sys.platform))
        except Exception as e:
            self.logger.warning(f"Could not write PID file: {e}")

        try:
            while self.running and not self.shutdown_event.is_set():
                # Run check cycle
                await self.check_cycle()

                # Wait for next interval or shutdown signal
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(),
                        timeout=self.config.check_interval
                    )
                except asyncio.TimeoutError:
                    # Normal - timeout means time for next check
                    pass

        except Exception as e:
            self.logger.critical(f"Fatal error in main loop: {e}", exc_info=True)

        finally:
            await self.cleanup()

    async def cleanup(self):
        """Graceful cleanup on shutdown."""
        self.logger.info("Starting cleanup sequence...")

        try:
            # Save final state
            self._save_state()
            self.logger.info("State saved")

            # Close circuit breakers (flush any pending state)
            for name, circuit in self.circuits.items():
                self.logger.debug(f"Closing circuit: {name}")

            # Remove PID file
            try:
                if self.pid_path.exists():
                    self.pid_path.unlink()
            except Exception:
                pass

            # Flush logs
            for handler in self.logger.handlers:
                handler.flush()

            self.logger.info("Cleanup complete - Operator daemon shutdown")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get daemon status for monitoring."""
        uptime = None
        if self.state.uptime_start:
            start = datetime.fromisoformat(self.state.uptime_start)
            uptime = (datetime.now() - start).total_seconds()

        return {
            'running': self.running,
            'last_run': self.state.last_run,
            'run_count': self.state.run_count,
            'total_alerts': self.state.total_alerts,
            'uptime_seconds': uptime,
            'enabled_monitors': self.config.enabled_monitors,
            'monitor_states': self.state.monitor_states,
            'circuit_states': self.state.circuit_states,
            'dedup_cache_size': len(self.state.recent_dedup_keys),
            'is_quiet_hours': self._is_quiet_hours(),
            'config': {
                'check_interval': self.config.check_interval,
                'max_alerts_per_run': self.config.max_alerts_per_run,
                'quiet_hours_enabled': self.config.quiet_hours_enabled
            }
        }


async def main():
    """Main entry point for the Operator daemon."""
    parser = argparse.ArgumentParser(
        description='Operator Daemon - Thanos v2.0 Phase 3'
    )
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to config YAML file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Testing mode - no alerts sent'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--status',
        action='store_true',
        help='Show daemon status and exit'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run one check cycle and exit'
    )

    args = parser.parse_args()

    # Load configuration
    if args.config and args.config.exists():
        try:
            config = OperatorConfig.from_yaml(args.config)
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    else:
        config = OperatorConfig()

    # Initialize daemon
    daemon = OperatorDaemon(
        config=config,
        dry_run=args.dry_run,
        verbose=args.verbose
    )

    # Handle status request
    if args.status:
        status = daemon.get_status()
        print(json.dumps(status, indent=2))
        return

    # Handle single run
    if args.once:
        await daemon.check_cycle()
        return

    # Run continuous
    await daemon.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
