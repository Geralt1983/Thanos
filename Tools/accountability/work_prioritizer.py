#!/usr/bin/env python3
"""
Work Task Prioritization Engine.

Prioritizes work tasks using three lenses:
1. Biggest Pile - Most backlogged client
2. Most Ignored - Longest since last interaction
3. Energy Match - Match task complexity to current readiness
"""

import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Handle both CLI and module imports
try:
    from .models import ClientWorkload, WorkPriorityMode
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from models import ClientWorkload, WorkPriorityMode

logger = logging.getLogger('work_prioritizer')


class WorkPrioritizer:
    """
    Prioritizes work tasks across clients.

    Provides three modes of prioritization:
    - biggest_pile: Focus on client with most tasks
    - most_ignored: Focus on client not touched longest
    - energy_match: Match work to current energy level
    """

    def __init__(self, db_url: Optional[str] = None):
        """
        Initialize the work prioritizer.

        Args:
            db_url: Optional database URL. Uses DATABASE_URL env var if not provided.
        """
        self.db_url = db_url or os.getenv('DATABASE_URL')

    async def get_client_workloads(self) -> List[ClientWorkload]:
        """
        Get workload metrics for all clients.

        Returns:
            List of ClientWorkload objects.
        """
        try:
            import httpx

            # Use WorkOS MCP to get clients and tasks
            clients = await self._fetch_clients()
            tasks = await self._fetch_active_tasks()

            workloads = []
            today = date.today()

            for client in clients:
                client_id = client.get('id')
                client_name = client.get('name', 'Unknown')

                # Filter tasks for this client
                client_tasks = [
                    t for t in tasks
                    if t.get('clientId') == client_id
                ]

                if not client_tasks:
                    continue

                # Calculate metrics
                task_count = len(client_tasks)

                # Days since last touch (completed task or interaction)
                last_touch = self._get_last_touch(client_tasks)
                if last_touch:
                    days_since = (today - last_touch).days
                else:
                    days_since = 30  # Default to 30 days if no touch

                # Oldest task age
                oldest_created = min(
                    (self._parse_date(t.get('createdAt')) for t in client_tasks),
                    default=today
                )
                oldest_age = (today - oldest_created).days if oldest_created else 0

                # High priority count
                high_priority = sum(
                    1 for t in client_tasks
                    if t.get('valueTier') in ['milestone', 'deliverable']
                )

                # Total points
                tier_points = {
                    'checkbox': 1,
                    'progress': 2,
                    'deliverable': 4,
                    'milestone': 7
                }
                total_points = sum(
                    tier_points.get(t.get('valueTier', 'checkbox'), 1)
                    for t in client_tasks
                )

                workloads.append(ClientWorkload(
                    client_id=client_id,
                    client_name=client_name,
                    task_count=task_count,
                    days_since_touch=days_since,
                    oldest_task_age=oldest_age,
                    high_priority_count=high_priority,
                    total_points=total_points,
                ))

            return workloads

        except Exception as e:
            logger.error(f"Failed to get client workloads: {e}")
            return []

    async def _fetch_clients(self) -> List[Dict]:
        """Fetch clients from WorkOS."""
        try:
            # Try to use local state store first
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            from Tools.state_store import get_db
            db = get_db()

            # Try to get from local cache
            clients = db.execute_sql("""
                SELECT id, name FROM clients WHERE is_active = 1
            """)
            if clients:
                return clients
        except:
            pass

        # Fallback: return empty (would need MCP integration)
        return []

    async def _fetch_active_tasks(self) -> List[Dict]:
        """Fetch active work tasks."""
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))

            from Tools.state_store import get_db
            db = get_db()

            tasks = db.execute_sql("""
                SELECT * FROM tasks
                WHERE status IN ('active', 'queued')
                AND category = 'work'
            """)
            return tasks or []
        except:
            pass

        return []

    def _get_last_touch(self, tasks: List[Dict]) -> Optional[date]:
        """Get the most recent touch date from tasks."""
        dates = []
        for task in tasks:
            # Check completedAt, updatedAt
            for field in ['completedAt', 'updatedAt', 'updated_at']:
                if task.get(field):
                    parsed = self._parse_date(task[field])
                    if parsed:
                        dates.append(parsed)

        return max(dates) if dates else None

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            # Handle ISO format
            if 'T' in str(date_str):
                return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
            return date.fromisoformat(str(date_str)[:10])
        except:
            return None

    def prioritize(
        self,
        workloads: List[ClientWorkload],
        mode: WorkPriorityMode,
        current_readiness: int = 70
    ) -> List[ClientWorkload]:
        """
        Sort workloads by priority.

        Args:
            workloads: List of client workloads.
            mode: Prioritization mode.
            current_readiness: Current Oura readiness score.

        Returns:
            Sorted list (highest priority first).
        """
        return sorted(
            workloads,
            key=lambda w: w.priority_score(mode, current_readiness),
            reverse=True
        )

    def suggest_next_client(
        self,
        workloads: List[ClientWorkload],
        mode: WorkPriorityMode,
        current_readiness: int = 70
    ) -> Optional[ClientWorkload]:
        """
        Suggest the next client to work on.

        Args:
            workloads: List of client workloads.
            mode: Prioritization mode.
            current_readiness: Current Oura readiness score.

        Returns:
            Top priority ClientWorkload or None.
        """
        prioritized = self.prioritize(workloads, mode, current_readiness)
        return prioritized[0] if prioritized else None

    def get_balance_report(self, workloads: List[ClientWorkload]) -> Dict[str, Any]:
        """
        Generate a balance report across clients.

        Args:
            workloads: List of client workloads.

        Returns:
            Report with balance metrics.
        """
        if not workloads:
            return {'error': 'No workloads to analyze'}

        import statistics

        task_counts = [w.task_count for w in workloads]
        touch_days = [w.days_since_touch for w in workloads]

        return {
            'client_count': len(workloads),
            'total_tasks': sum(task_counts),
            'task_distribution': {
                'mean': statistics.mean(task_counts),
                'stddev': statistics.stdev(task_counts) if len(task_counts) > 1 else 0,
                'max': max(task_counts),
                'min': min(task_counts),
            },
            'neglect_distribution': {
                'mean': statistics.mean(touch_days),
                'max_neglected': max(workloads, key=lambda w: w.days_since_touch).client_name,
                'max_days': max(touch_days),
            },
            'recommendations': self._generate_recommendations(workloads),
        }

    def _generate_recommendations(self, workloads: List[ClientWorkload]) -> List[str]:
        """Generate recommendations based on workload analysis."""
        recommendations = []

        # Find most neglected
        most_neglected = max(workloads, key=lambda w: w.days_since_touch)
        if most_neglected.days_since_touch > 7:
            recommendations.append(
                f"Client '{most_neglected.client_name}' hasn't been touched in "
                f"{most_neglected.days_since_touch} days - consider reaching out."
            )

        # Find biggest pile
        biggest_pile = max(workloads, key=lambda w: w.task_count)
        if biggest_pile.task_count > 10:
            recommendations.append(
                f"Client '{biggest_pile.client_name}' has {biggest_pile.task_count} "
                f"active tasks - consider prioritizing or delegating."
            )

        # Check for imbalance
        import statistics
        counts = [w.task_count for w in workloads]
        if len(counts) > 1:
            stddev = statistics.stdev(counts)
            mean = statistics.mean(counts)
            if stddev > mean * 0.5:  # High variance
                recommendations.append(
                    "Task distribution is unbalanced across clients. "
                    "Consider redistributing attention."
                )

        return recommendations


async def get_prioritized_clients(
    mode: str = "biggest_pile",
    readiness: int = 70
) -> List[Dict[str, Any]]:
    """
    Convenience function to get prioritized client list.

    Args:
        mode: Prioritization mode (biggest_pile, most_ignored, energy_match).
        readiness: Current Oura readiness score.

    Returns:
        List of prioritized client workloads.
    """
    prioritizer = WorkPrioritizer()
    workloads = await prioritizer.get_client_workloads()

    try:
        priority_mode = WorkPriorityMode(mode)
    except ValueError:
        priority_mode = WorkPriorityMode.BIGGEST_PILE

    prioritized = prioritizer.prioritize(workloads, priority_mode, readiness)

    return [w.to_dict() for w in prioritized]


# CLI interface
if __name__ == '__main__':
    import asyncio
    import argparse

    parser = argparse.ArgumentParser(description='Work Prioritization Engine')
    parser.add_argument(
        '--mode', '-m',
        choices=['biggest_pile', 'most_ignored', 'energy_match'],
        default='biggest_pile',
        help='Prioritization mode'
    )
    parser.add_argument(
        '--readiness', '-r',
        type=int,
        default=70,
        help='Current readiness score (0-100)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Show balance report'
    )
    args = parser.parse_args()

    async def main():
        prioritizer = WorkPrioritizer()
        workloads = await prioritizer.get_client_workloads()

        if not workloads:
            print("No client workloads found.")
            return

        mode = WorkPriorityMode(args.mode)
        prioritized = prioritizer.prioritize(workloads, mode, args.readiness)

        print(f"\n=== Work Priority ({args.mode}) ===")
        print(f"Readiness: {args.readiness}\n")

        for i, w in enumerate(prioritized[:5], 1):
            score = w.priority_score(mode, args.readiness)
            print(f"{i}. {w.client_name}")
            print(f"   Tasks: {w.task_count} | Days Silent: {w.days_since_touch} | Score: {score:.1f}")

        if args.report:
            print("\n=== Balance Report ===")
            report = prioritizer.get_balance_report(workloads)
            print(f"Clients: {report['client_count']}")
            print(f"Total Tasks: {report['total_tasks']}")
            print(f"Most Neglected: {report['neglect_distribution']['max_neglected']} "
                  f"({report['neglect_distribution']['max_days']} days)")
            print("\nRecommendations:")
            for rec in report.get('recommendations', []):
                print(f"  • {rec}")

    asyncio.run(main())
