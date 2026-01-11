"""
Briefing Scheduler Daemon

Runs continuously and triggers briefings at configured times.
Supports both continuous daemon mode and single-check mode (for cron).
"""

import os
import sys
import json
import time
import signal
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from Tools.briefing_engine import BriefingEngine
from Tools.config_validator import ConfigValidator


class BriefingScheduler:
    """
    Daemon that monitors schedule configuration and triggers briefings
    at configured times.
    """

    def __init__(self, config_path: str = None, state_dir: str = None, templates_dir: str = None):
        """
        Initialize the scheduler daemon.

        Args:
            config_path: Path to briefing_schedule.json (default: config/briefing_schedule.json)
            state_dir: Path to State directory (default: ./State)
            templates_dir: Path to Templates directory (default: ./Templates)
        """
        # Set default paths
        if config_path is None:
            config_path = os.path.join(os.getcwd(), "config", "briefing_schedule.json")
        if state_dir is None:
            state_dir = os.path.join(os.getcwd(), "State")
        if templates_dir is None:
            templates_dir = os.path.join(os.getcwd(), "Templates")

        self.config_path = Path(config_path)
        self.state_dir = Path(state_dir)
        self.templates_dir = Path(templates_dir)

        # Load configuration
        self.config = self._load_config()

        # Setup logging
        self.logger = self._setup_logging()

        # Initialize state tracking for duplicate prevention
        self.run_state_file = Path(self.state_dir) / ".briefing_runs.json"
        self.run_state = self._load_run_state()

        # Initialize BriefingEngine
        self.engine = BriefingEngine(
            state_dir=str(self.state_dir),
            templates_dir=str(self.templates_dir)
        )

        # Flag for graceful shutdown
        self.should_stop = False

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        self.logger.info("BriefingScheduler initialized")
        self.logger.info(f"Config: {self.config_path}")
        self.logger.info(f"State: {self.state_dir}")
        self.logger.info(f"Templates: {self.templates_dir}")

    def _load_config(self) -> Dict[str, Any]:
        """Load and validate configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # Validate config
        validator = ConfigValidator(str(self.config_path))
        is_valid, errors = validator.validate()
        if not is_valid:
            error_msg = "Config validation failed:\n" + "\n".join(errors)
            raise ValueError(error_msg)

        # Load config
        with open(self.config_path, 'r') as f:
            config = json.load(f)

        return config

    def _setup_logging(self) -> logging.Logger:
        """Setup logging to file and console."""
        log_file = self.config.get("scheduler", {}).get("log_file", "logs/briefing_scheduler.log")
        log_path = Path(log_file)

        # Create logs directory if needed
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create logger
        logger = logging.getLogger("briefing_scheduler")
        logger.setLevel(logging.INFO)

        # File handler
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        return logger

    def _load_run_state(self) -> Dict[str, Any]:
        """Load run state for duplicate prevention."""
        if self.run_state_file.exists():
            try:
                with open(self.run_state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load run state: {e}")
                return {}
        return {}

    def _save_run_state(self):
        """Save run state to file."""
        try:
            self.run_state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.run_state_file, 'w') as f:
                json.dump(self.run_state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save run state: {e}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.should_stop = True

    def _get_current_day_name(self) -> str:
        """Get current day name in lowercase (monday, tuesday, etc.)."""
        return datetime.now().strftime("%A").lower()

    def _has_run_today(self, briefing_type: str) -> bool:
        """Check if a briefing has already run today."""
        if not self.config.get("scheduler", {}).get("prevent_duplicate_runs", True):
            return False

        today_str = date.today().isoformat()
        run_key = f"{today_str}_{briefing_type}"

        return run_key in self.run_state

    def _mark_as_run(self, briefing_type: str):
        """Mark a briefing as run for today."""
        today_str = date.today().isoformat()
        run_key = f"{today_str}_{briefing_type}"

        self.run_state[run_key] = {
            "timestamp": datetime.now().isoformat(),
            "type": briefing_type
        }

        # Clean up old entries (keep only last 7 days)
        cutoff_date = date.today() - timedelta(days=7)
        self.run_state = {
            k: v for k, v in self.run_state.items()
            if k.split('_')[0] >= cutoff_date.isoformat()
        }

        self._save_run_state()

    def _should_run_briefing(self, briefing_type: str, config: Dict[str, Any], current_time: datetime) -> bool:
        """
        Check if a briefing should run now.

        Args:
            briefing_type: Type of briefing (morning, evening, etc.)
            config: Briefing configuration
            current_time: Current datetime

        Returns:
            True if briefing should run now
        """
        # Check if enabled
        if not config.get("enabled", False):
            return False

        # Check day of week
        current_day = self._get_current_day_name()
        if not config.get("days", {}).get(current_day, False):
            return False

        # Check if already run today
        if self._has_run_today(briefing_type):
            return False

        # Check time
        scheduled_time_str = config.get("time", "")
        if not scheduled_time_str:
            return False

        try:
            # Parse scheduled time (format: HH:MM)
            scheduled_hour, scheduled_minute = map(int, scheduled_time_str.split(':'))

            # Check if current time matches (within the check interval window)
            current_hour = current_time.hour
            current_minute = current_time.minute

            # We match if we're in the same hour and minute
            if current_hour == scheduled_hour and current_minute == scheduled_minute:
                return True

        except Exception as e:
            self.logger.error(f"Failed to parse time '{scheduled_time_str}': {e}")
            return False

        return False

    def _run_briefing(self, briefing_type: str, config: Dict[str, Any]):
        """
        Execute a briefing.

        Args:
            briefing_type: Type of briefing (morning, evening, etc.)
            config: Briefing configuration
        """
        try:
            self.logger.info(f"Starting {briefing_type} briefing...")

            # Gather context
            context = self.engine.gather_context()

            # Get template name
            template_name = config.get("template", f"briefing_{briefing_type}.md")

            # Determine briefing type for rendering (morning/evening)
            render_type = "morning" if "morning" in briefing_type.lower() else "evening"

            # Render briefing
            briefing_content = self.engine.render_briefing(
                briefing_type=render_type,
                custom_sections=None
            )

            # Deliver via configured channels
            delivery_channels = config.get("delivery_channels", ["cli"])
            self._deliver_briefing(briefing_type, briefing_content, delivery_channels)

            # Mark as run
            self._mark_as_run(briefing_type)

            self.logger.info(f"Completed {briefing_type} briefing successfully")

        except Exception as e:
            self.logger.error(f"Failed to run {briefing_type} briefing: {e}", exc_info=True)

            # Send error notification if enabled
            if self.config.get("scheduler", {}).get("error_notification", True):
                self._send_error_notification(briefing_type, str(e))

    def _deliver_briefing(self, briefing_type: str, content: str, channels: List[str]):
        """
        Deliver briefing via configured channels.

        Args:
            briefing_type: Type of briefing
            content: Briefing content
            channels: List of delivery channels
        """
        delivery_config = self.config.get("delivery", {})

        for channel in channels:
            try:
                if channel == "cli" and delivery_config.get("cli", {}).get("enabled", True):
                    self._deliver_cli(briefing_type, content, delivery_config.get("cli", {}))
                elif channel == "file" and delivery_config.get("file", {}).get("enabled", True):
                    self._deliver_file(briefing_type, content, delivery_config.get("file", {}))
                elif channel == "notification" and delivery_config.get("notification", {}).get("enabled", False):
                    self._deliver_notification(briefing_type, content, delivery_config.get("notification", {}))
                else:
                    self.logger.debug(f"Channel '{channel}' not enabled or not supported")
            except Exception as e:
                self.logger.error(f"Failed to deliver via {channel}: {e}")

    def _deliver_cli(self, briefing_type: str, content: str, config: Dict[str, Any]):
        """Deliver briefing to CLI (stdout)."""
        self.logger.info(f"Delivering {briefing_type} briefing to CLI")
        print(f"\n{'='*80}")
        print(f"  {briefing_type.upper()} BRIEFING - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"{'='*80}\n")
        print(content)
        print(f"\n{'='*80}\n")

    def _deliver_file(self, briefing_type: str, content: str, config: Dict[str, Any]):
        """Deliver briefing to file."""
        output_dir = config.get("output_dir", "History/DailyBriefings")
        filename_pattern = config.get("filename_pattern", "{date}_{type}_briefing.md")

        # Format filename
        filename = filename_pattern.format(
            date=date.today().isoformat(),
            type=briefing_type
        )

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Write file
        file_path = output_path / filename
        with open(file_path, 'w') as f:
            f.write(content)

        self.logger.info(f"Saved {briefing_type} briefing to {file_path}")

    def _deliver_notification(self, briefing_type: str, content: str, config: Dict[str, Any]):
        """Deliver briefing via desktop notification."""
        # This is a stub for now - will be implemented in Phase 4
        self.logger.info(f"Notification delivery not yet implemented for {briefing_type}")

    def _send_error_notification(self, briefing_type: str, error: str):
        """Send error notification to user."""
        self.logger.error(f"Error notification: {briefing_type} failed - {error}")
        # TODO: Implement actual notification mechanism

    def check_and_run(self):
        """
        Check if any briefings should run now and execute them.
        This is called once per check interval.
        """
        current_time = datetime.now()

        # Iterate through all configured briefings
        briefings = self.config.get("briefings", {})
        for briefing_type, briefing_config in briefings.items():
            if self._should_run_briefing(briefing_type, briefing_config, current_time):
                self.logger.info(f"Triggering {briefing_type} briefing at {current_time.strftime('%H:%M')}")
                self._run_briefing(briefing_type, briefing_config)

    def run_once(self):
        """
        Run a single check cycle.
        Useful for cron-based scheduling where the scheduler is invoked periodically.
        """
        self.logger.info("Running single check cycle")
        self.check_and_run()
        self.logger.info("Check cycle complete")

    def run_daemon(self):
        """
        Run as a continuous daemon.
        Checks schedule every N minutes and sleeps between checks.
        """
        check_interval = self.config.get("scheduler", {}).get("check_interval_minutes", 1)
        self.logger.info(f"Starting daemon mode with {check_interval} minute check interval")

        while not self.should_stop:
            try:
                self.check_and_run()

                # Sleep until next check (in 1-second increments to allow for quick shutdown)
                sleep_seconds = check_interval * 60
                for _ in range(sleep_seconds):
                    if self.should_stop:
                        break
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"Error in daemon loop: {e}", exc_info=True)
                # Sleep a bit before retrying to avoid tight error loops
                time.sleep(60)

        self.logger.info("Daemon shutting down")


def main():
    """Main entry point for the scheduler daemon."""
    import argparse

    parser = argparse.ArgumentParser(description="Briefing Scheduler Daemon")
    parser.add_argument(
        "--mode",
        choices=["daemon", "once"],
        default="daemon",
        help="Run mode: 'daemon' for continuous operation, 'once' for single check (cron mode)"
    )
    parser.add_argument(
        "--config",
        help="Path to briefing_schedule.json (default: config/briefing_schedule.json)"
    )
    parser.add_argument(
        "--state-dir",
        help="Path to State directory (default: ./State)"
    )
    parser.add_argument(
        "--templates-dir",
        help="Path to Templates directory (default: ./Templates)"
    )

    args = parser.parse_args()

    try:
        # Initialize scheduler
        scheduler = BriefingScheduler(
            config_path=args.config,
            state_dir=args.state_dir,
            templates_dir=args.templates_dir
        )

        # Run in selected mode
        if args.mode == "once":
            scheduler.run_once()
        else:
            scheduler.run_daemon()

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
