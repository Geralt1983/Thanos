#!/usr/bin/env python3
"""
Signal Fetcher for Thanos Startup Sequence.

Fetches high-priority alerts from Sentinel and Honeycomb systems
to surface at session start. Part of CLAUDE.md startup protocol.

Returns signals in format: {type, priority, message, person, commitment_id}
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Setup path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.alert_checkers.commitment_reminder_checker import CommitmentReminderChecker
from Tools.alert_checkers.relationship_decay_checker import RelationshipDecayChecker
from Tools.journal import EventType


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

    Returns:
        List of signal dictionaries
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
        signals = [format_signal(alert) for alert in high_priority_alerts]

    except Exception as e:
        # Log error but don't crash - return empty signals
        print(f"⚠️  Signal fetch error: {e}", file=sys.stderr)

    return signals


def format_output(signals: List[Dict[str, Any]]) -> str:
    """
    Format signals for display at session start.

    Args:
        signals: List of signal dictionaries

    Returns:
        Formatted string for output
    """
    if not signals:
        return "No critical signals"

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
    signals = await get_signals()
    output = format_output(signals)
    print(output)


if __name__ == "__main__":
    asyncio.run(main())
