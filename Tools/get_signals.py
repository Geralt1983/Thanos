#!/usr/bin/env python3
"""
Signal Fetcher for Thanos Startup Sequence.

Fetches high-priority alerts from Sentinel and Honeycomb systems
to surface at session start. Part of CLAUDE.md startup protocol.

Returns signals in format: {type, priority, message, person, commitment_id}
"""

import asyncio
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.alert_checkers.commitment_reminder_checker import CommitmentReminderChecker
from Tools.alert_checkers.relationship_decay_checker import RelationshipDecayChecker
from Tools.journal import EventType


@dataclass
class SignalState:
    """Persistent state for signal acknowledgments."""
    acknowledged_signals: Dict[str, str] = field(default_factory=dict)  # signal_id -> timestamp

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SignalState':
        return cls(**data)


class SignalManager:
    """
    Manages signal persistence to avoid repeat notifications.

    Features:
    - Track acknowledged signals with timestamps
    - Auto-cleanup of old acknowledgments (24h window)
    - Persistent state across sessions
    """

    def __init__(self, state_file: str = "State/signal_state.json", ack_window_hours: int = 24):
        """
        Initialize the signal manager.

        Args:
            state_file: Path to state file (relative to project root)
            ack_window_hours: How long to remember acknowledgments (default 24h)
        """
        self.state_file = Path(__file__).parent.parent / state_file
        self.ack_window = timedelta(hours=ack_window_hours)
        self.state = SignalState()
        self._load_state()

    def _load_state(self):
        """Load persistent state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file) as f:
                    data = json.load(f)
                    self.state = SignalState.from_dict(data)
        except Exception as e:
            # Start with empty state if load fails
            self.state = SignalState()

    def _save_state(self):
        """Save state to file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=2)
        except Exception as e:
            # Log but don't crash
            print(f"⚠️  Could not save signal state: {e}", file=sys.stderr)

    def _clean_old_acknowledgments(self):
        """Remove acknowledgments older than the window."""
        now = datetime.now()
        cutoff = now - self.ack_window
        cutoff_str = cutoff.isoformat()

        expired = [
            sig_id for sig_id, timestamp in self.state.acknowledged_signals.items()
            if timestamp < cutoff_str
        ]

        for sig_id in expired:
            del self.state.acknowledged_signals[sig_id]

        if expired:
            self._save_state()

    def generate_signal_id(self, signal: Dict[str, Any]) -> str:
        """
        Generate a unique ID for a signal based on its key attributes.

        Args:
            signal: Signal dictionary

        Returns:
            Unique signal ID string
        """
        signal_type = signal.get('type', '')
        severity = signal.get('severity', '')

        # For commitment reminders, use commitment_id with severity to differentiate events
        if signal_type == 'CommitmentReminderCell' and 'commitment_id' in signal:
            return f"commitment-{signal['commitment_id']}-{severity}"

        # For relationship decay, use person with severity to differentiate events
        elif signal_type == 'RelationshipCell' and 'person' in signal:
            return f"relationship-{signal['person']}-{severity}"

        # For generic signals, hash the message with severity
        else:
            message_hash = hashlib.md5(signal.get('message', '').encode()).hexdigest()[:8]
            return f"{signal_type.lower()}-{severity}-{message_hash}"

    def is_acknowledged(self, signal_id: str) -> bool:
        """
        Check if a signal has been acknowledged.

        Args:
            signal_id: Signal ID to check

        Returns:
            True if signal is acknowledged and within window
        """
        return signal_id in self.state.acknowledged_signals

    def mark_acknowledged(self, signal_id: str):
        """
        Mark a signal as acknowledged.

        Args:
            signal_id: Signal ID to acknowledge
        """
        self.state.acknowledged_signals[signal_id] = datetime.now().isoformat()
        self._save_state()

    def filter_acknowledged(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter out acknowledged signals.

        Args:
            signals: List of signal dictionaries

        Returns:
            List with acknowledged signals removed
        """
        # Clean old acknowledgments first
        self._clean_old_acknowledgments()

        # Filter out acknowledged signals
        filtered = []
        for signal in signals:
            sig_id = self.generate_signal_id(signal)
            if not self.is_acknowledged(sig_id):
                # Add signal_id to the signal for later reference
                signal['signal_id'] = sig_id
                filtered.append(signal)

        return filtered


def format_signal(alert) -> Dict[str, Any]:
    """
    Format an Alert object as a Signal for the startup sequence.

    Args:
        alert: Alert object from checker

    Returns:
        Dict with signal format: {type, priority, message, person, commitment_id}
    """
    # Determine signal type based on alert data
    alert_type = alert.data.get('alert_type', '')

    if alert_type == 'relationship_decay':
        signal_type = 'RelationshipCell'
    elif 'commitment_id' in alert.data:
        signal_type = 'CommitmentReminderCell'
    else:
        signal_type = 'MemoryDecayCell'

    # Map severity to priority
    priority_map = {
        'critical': 'critical',
        'warning': 'high',
        'alert': 'high',
        'info': 'medium',
        'debug': 'low'
    }
    priority = priority_map.get(alert.severity, 'medium')

    # Build signal
    signal = {
        'type': signal_type,
        'priority': priority,
        'message': alert.title,
        'severity': alert.severity
    }

    # Add optional fields if available
    if 'person' in alert.data and alert.data['person']:
        signal['person'] = alert.data['person']
    if 'person_name' in alert.data:
        signal['person'] = alert.data['person_name']
    if 'commitment_id' in alert.data:
        signal['commitment_id'] = alert.data['commitment_id']
    if 'days_until' in alert.data:
        signal['days_until'] = alert.data['days_until']
    if 'days_since_mention' in alert.data:
        signal['days_since_mention'] = alert.data['days_since_mention']

    return signal


async def get_signals() -> List[Dict[str, Any]]:
    """
    Fetch signals from Sentinel and Honeycomb systems.
    Filters out acknowledged signals to avoid repeat notifications.

    Returns:
        List of signal dictionaries (unacknowledged only)
    """
    signals = []

    try:
        # Initialize checkers
        commitment_checker = CommitmentReminderChecker()
        relationship_checker = RelationshipDecayChecker()

        # Run checks
        commitment_alerts = await commitment_checker.check()
        relationship_alerts = await relationship_checker.check()

        # Combine and filter for high-priority only
        all_alerts = commitment_alerts + relationship_alerts

        # Filter for warning/critical severity (high-priority signals)
        high_priority_alerts = [
            alert for alert in all_alerts
            if alert.severity in ('critical', 'warning')
        ]

        # Format as signals
        all_signals = [format_signal(alert) for alert in high_priority_alerts]

        # Filter out acknowledged signals
        signal_manager = SignalManager()
        signals = signal_manager.filter_acknowledged(all_signals)

    except Exception as e:
        # Log error but don't crash - return empty signals
        print(f"⚠️  Signal fetch error: {e}", file=sys.stderr)

    return signals


def format_output(signals: List[Dict[str, Any]], output_format: str = "json") -> str:
    """
    Format signals for display at session start.

    Args:
        signals: List of signal dictionaries
        output_format: "json" for structured JSON, "text" for human-readable

    Returns:
        Formatted string (JSON or human-readable text)
    """
    if output_format == "json":
        # Return structured JSON
        if not signals:
            return json.dumps({"count": 0, "signals": [], "summary": "No signals"})

        return json.dumps({
            "count": len(signals),
            "signals": signals,
            "summary": f"{len(signals)} signal(s) from Sentinel/Honeycomb"
        }, indent=2)

    # Human-readable text format (legacy)
    if not signals:
        return "No signals"

    # Build output
    lines = []
    lines.append(f"🔔 {len(signals)} Signal(s) from Sentinel/Honeycomb:\n")

    for signal in signals:
        signal_type = signal['type']
        priority = signal['priority']
        message = signal['message']

        # Choose emoji based on signal type
        if signal_type == 'CommitmentReminderCell':
            emoji = '📅'
        elif signal_type == 'RelationshipCell':
            emoji = '💙'
        else:
            emoji = '🔔'

        # Format with priority indicator
        priority_indicator = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '📢',
            'low': 'ℹ️'
        }.get(priority, '📝')

        lines.append(f"{emoji} {priority_indicator} [{signal_type}] {message}")

        # Add person context if available
        if 'person' in signal:
            lines.append(f"   → Person: {signal['person']}")

        # Add timing context
        if 'days_until' in signal:
            lines.append(f"   → Due in {signal['days_until']} day(s)")
        elif 'days_since_mention' in signal:
            lines.append(f"   → Last mentioned {signal['days_since_mention']} day(s) ago")

        lines.append("")  # Blank line between signals

    return "\n".join(lines)


async def main():
    """Main entry point for get_signals.py"""
    import sys
    # Allow text mode with --text flag for backwards compatibility
    output_format = "text" if "--text" in sys.argv else "json"

    signals = await get_signals()
    output = format_output(signals, output_format=output_format)
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
