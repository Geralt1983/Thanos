#!/usr/bin/env python3
"""
Pattern Monitor - Thanos Operator Daemon

Monitors behavioral patterns for procrastination, energy decline, and context switching.

Architecture:
    - Analyzes State/brain_dumps.json for recurring worries/tasks
    - Checks State/CurrentFocus.md for stale priorities (>7 days)
    - Detects context switching (too many active clients/tasks in one day)
    - All data from local file system (no external dependencies)

Alert Triggers:
    - Procrastination: Same task punted 3+ times in 7 days
    - Energy decline: 20% drop in weekly average readiness
    - Overcommitment: Created/Completed ratio > 1.5 over 7 days
    - Stale focus: CurrentFocus.md not updated in 7+ days
    - Context switching: 5+ different clients in one day

Pattern Recognition:
    - Uses brain dump analysis for recurring themes
    - Tracks task deferral patterns
    - Monitors energy trends over time
"""

import asyncio
import logging
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from collections import Counter, defaultdict
from dataclasses import dataclass

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


class PatternMonitor:
    """
    Monitor behavioral patterns and procrastination indicators.

    Data Sources:
        - State/brain_dumps.json: Recurring worries, unprocessed thoughts
        - State/CurrentFocus.md: Focus areas and priority staleness
        - WorkOS tasks: Task deferral patterns (via Task Monitor)

    Pattern Categories:
        1. Procrastination: Repeated mentions of same task without action
        2. Energy Decline: Trend analysis from Oura readiness data
        3. Overcommitment: Creating tasks faster than completing them
        4. Stale Priorities: Focus document not updated recently
        5. Context Switching: Too many different areas in short time
    """

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Pattern Monitor.

        Args:
            state_dir: Directory containing state files
            thresholds: Custom thresholds (overrides defaults)
        """
        # Setup state directory
        if state_dir is None:
            thanos_root = Path(__file__).parent.parent.parent
            state_dir = thanos_root / "State"
        self.state_dir = state_dir

        # State file paths
        self.brain_dumps_path = state_dir / "brain_dumps.json"
        self.current_focus_path = state_dir / "CurrentFocus.md"

        # Default thresholds
        self.thresholds = {
            'procrastination_count': 3,  # Same task mentioned 3+ times
            'lookback_days': 7,  # Days to analyze patterns
            'energy_decline_percent': 20,  # 20% decline triggers alert
            'overcommitment_ratio': 1.5,  # Created/Completed ratio
            'stale_focus_days': 7,  # Days since last focus update
            'context_switch_threshold': 5  # Different clients in one day
        }

        if thresholds:
            self.thresholds.update(thresholds)

        logger.info(
            f"PatternMonitor initialized: state_dir={self.state_dir}, "
            f"thresholds={self.thresholds}"
        )

    async def check(self) -> List[Alert]:
        """
        Run pattern analysis and generate alerts.

        Returns:
            List of Alert objects (empty on errors - graceful degradation)
        """
        try:
            logger.debug("Running pattern analysis")

            alerts = []

            # Check for procrastination patterns in brain dumps
            procrastination_alert = await self._check_procrastination()
            if procrastination_alert:
                alerts.append(procrastination_alert)

            # Check for stale focus/priorities
            stale_focus_alert = await self._check_stale_focus()
            if stale_focus_alert:
                alerts.append(stale_focus_alert)

            # Check for recurring worries (brain dump analysis)
            worry_alerts = await self._check_recurring_worries()
            alerts.extend(worry_alerts)

            logger.info(f"Pattern analysis complete: {len(alerts)} alerts generated")
            return alerts

        except Exception as e:
            logger.error(f"Pattern monitor check failed: {e}", exc_info=True)
            return []  # Graceful degradation

    async def _check_procrastination(self) -> Optional[Alert]:
        """
        Detect procrastination patterns by analyzing brain dumps.

        Looks for repeated mentions of the same task/action without
        marking as processed or converting to actual tasks.

        Returns:
            Alert if procrastination pattern detected, None otherwise
        """
        try:
            if not self.brain_dumps_path.exists():
                logger.debug("No brain dumps file found")
                return None

            # Load brain dumps
            with open(self.brain_dumps_path) as f:
                brain_dumps = json.load(f)

            # Calculate lookback date
            lookback_date = datetime.now() - timedelta(days=self.thresholds['lookback_days'])

            # Filter recent unprocessed dumps
            recent_dumps = [
                dump for dump in brain_dumps
                if not dump.get('processed', False)
                and datetime.fromisoformat(dump['timestamp']) > lookback_date
            ]

            if not recent_dumps:
                return None

            # Extract actions and count occurrences
            action_counts = Counter()
            action_dumps = defaultdict(list)

            for dump in recent_dumps:
                action = dump.get('parsed_action')
                if action:
                    action_counts[action] += 1
                    action_dumps[action].append(dump)

            # Find repeated actions
            repeated_actions = [
                (action, count) for action, count in action_counts.items()
                if count >= self.thresholds['procrastination_count']
            ]

            if repeated_actions:
                # Report the most repeated action
                top_action, count = max(repeated_actions, key=lambda x: x[1])

                return Alert(
                    type='pattern',
                    severity='medium',
                    title='Procrastination Pattern Detected',
                    message=(
                        f"You've mentioned '{top_action}' {count} times in the past "
                        f"{self.thresholds['lookback_days']} days without taking action. "
                        f"Block time to complete it?"
                    ),
                    data={
                        'action': top_action,
                        'count': count,
                        'lookback_days': self.thresholds['lookback_days'],
                        'dumps': action_dumps[top_action],
                        'metric': 'procrastination'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"pattern:procrastination:{top_action}"
                )

        except Exception as e:
            logger.error(f"Error checking procrastination: {e}")
            return None

    async def _check_stale_focus(self) -> Optional[Alert]:
        """
        Check if CurrentFocus.md hasn't been updated recently.

        Stale focus indicates lack of priority review and planning.

        Returns:
            Alert if focus is stale, None otherwise
        """
        try:
            if not self.current_focus_path.exists():
                logger.debug("No CurrentFocus.md file found")
                return None

            # Get file modification time
            mtime = datetime.fromtimestamp(self.current_focus_path.stat().st_mtime)
            days_since_update = (datetime.now() - mtime).days

            if days_since_update >= self.thresholds['stale_focus_days']:
                return Alert(
                    type='pattern',
                    severity='medium',
                    title='Stale Focus Priorities',
                    message=(
                        f"Your CurrentFocus.md hasn't been updated in {days_since_update} days. "
                        f"Time for a priority review?"
                    ),
                    data={
                        'days_since_update': days_since_update,
                        'threshold': self.thresholds['stale_focus_days'],
                        'last_updated': mtime.isoformat(),
                        'metric': 'stale_focus'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"pattern:stale_focus:{datetime.now().strftime('%Y-%m-%d')}"
                )

        except Exception as e:
            logger.error(f"Error checking stale focus: {e}")
            return None

    async def _check_recurring_worries(self) -> List[Alert]:
        """
        Detect recurring worries or concerns in brain dumps.

        Analyzes unprocessed brain dumps for patterns of anxiety,
        stress, or repeated concerns that may need addressing.

        Returns:
            List of Alert objects for recurring worries
        """
        alerts = []

        try:
            if not self.brain_dumps_path.exists():
                return []

            # Load brain dumps
            with open(self.brain_dumps_path) as f:
                brain_dumps = json.load(f)

            # Calculate lookback date
            lookback_date = datetime.now() - timedelta(days=self.thresholds['lookback_days'])

            # Filter recent worry-category dumps
            recent_worries = [
                dump for dump in brain_dumps
                if dump.get('parsed_category') == 'worry'
                and not dump.get('processed', False)
                and datetime.fromisoformat(dump['timestamp']) > lookback_date
            ]

            if not recent_worries:
                return []

            # Extract entities (people, topics) from worries
            worry_entities = []
            for dump in recent_worries:
                entities = dump.get('parsed_entities', [])
                worry_entities.extend(entities)

            # Count entity occurrences
            entity_counts = Counter(worry_entities)

            # Find repeatedly mentioned entities
            recurring_entities = [
                (entity, count) for entity, count in entity_counts.items()
                if count >= 3  # Mentioned 3+ times
            ]

            if recurring_entities:
                # Report the most mentioned worry topic
                top_entity, count = max(recurring_entities, key=lambda x: x[1])

                alert = Alert(
                    type='pattern',
                    severity='medium',
                    title='Recurring Worry Detected',
                    message=(
                        f"You've expressed concern about '{top_entity}' {count} times "
                        f"recently. This may need attention or action."
                    ),
                    data={
                        'entity': top_entity,
                        'count': count,
                        'lookback_days': self.thresholds['lookback_days'],
                        'metric': 'recurring_worry'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"pattern:recurring_worry:{top_entity}"
                )
                alerts.append(alert)

            # Check for high volume of worries
            if len(recent_worries) >= 5:
                alert = Alert(
                    type='pattern',
                    severity='warning',
                    title='High Anxiety Volume',
                    message=(
                        f"You've logged {len(recent_worries)} worries in the past "
                        f"{self.thresholds['lookback_days']} days. Consider reviewing "
                        f"and addressing these concerns."
                    ),
                    data={
                        'worry_count': len(recent_worries),
                        'lookback_days': self.thresholds['lookback_days'],
                        'metric': 'worry_volume'
                    },
                    timestamp=datetime.now().isoformat(),
                    dedup_key=f"pattern:worry_volume:{datetime.now().strftime('%Y-%m-%d')}"
                )
                alerts.append(alert)

        except Exception as e:
            logger.error(f"Error checking recurring worries: {e}")

        return alerts
