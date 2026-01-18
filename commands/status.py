#!/usr/bin/env python3
"""
Thanos Status Command

Provides a comprehensive status overview including:
- Active alerts
- Task and commitment summary
- Health metrics
- Brain dump queue
- System status

Usage:
    python -m commands.status [--json] [--alerts-only] [--brief]

Part of the Clarity pillar for the Thanos architecture.
"""

import asyncio
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.state_store import get_db
from Tools.journal import Journal
from Tools.alert_checker import AlertManager, run_alert_check, AlertPriority


def get_task_summary() -> Dict[str, Any]:
    """Get summary of tasks from state store."""
    db = get_db()
    today = date.today()

    try:
        # Count tasks by status
        all_tasks = db.execute_sql("""
            SELECT status, COUNT(*) as count
            FROM tasks
            WHERE status != 'done' AND status != 'cancelled'
            GROUP BY status
        """)

        # Get overdue tasks
        overdue = db.execute_sql("""
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND due_date IS NOT NULL
            AND date(due_date) < date('now')
        """)

        # Get tasks due today
        due_today = db.execute_sql("""
            SELECT COUNT(*) as count
            FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            AND date(due_date) = date('now')
        """)

        # Get tasks by domain
        by_domain = db.execute_sql("""
            SELECT domain, COUNT(*) as count
            FROM tasks
            WHERE status NOT IN ('done', 'cancelled')
            GROUP BY domain
        """)

        return {
            'total': sum(r['count'] for r in all_tasks),
            'by_status': {r['status']: r['count'] for r in all_tasks},
            'overdue': overdue[0]['count'] if overdue else 0,
            'due_today': due_today[0]['count'] if due_today else 0,
            'by_domain': {r['domain'] or 'unassigned': r['count'] for r in by_domain},
        }
    except Exception as e:
        return {'error': str(e)}


def get_commitment_summary() -> Dict[str, Any]:
    """Get summary of commitments."""
    db = get_db()
    today = date.today()

    try:
        # Get active commitments
        active = db.get_active_commitments()

        # Categorize by due status
        overdue = []
        due_soon = []  # within 7 days
        upcoming = []

        for c in active:
            due_str = c.get('due_date')
            if due_str:
                try:
                    due_date = date.fromisoformat(due_str[:10])
                    days_until = (due_date - today).days

                    if days_until < 0:
                        overdue.append({
                            'title': c.get('title'),
                            'person': c.get('person'),
                            'days_overdue': abs(days_until),
                        })
                    elif days_until <= 7:
                        due_soon.append({
                            'title': c.get('title'),
                            'person': c.get('person'),
                            'days_until': days_until,
                        })
                    else:
                        upcoming.append(c)
                except (ValueError, TypeError):
                    upcoming.append(c)
            else:
                upcoming.append(c)

        return {
            'total': len(active),
            'overdue': overdue,
            'due_soon': due_soon,
            'upcoming_count': len(upcoming),
        }
    except Exception as e:
        return {'error': str(e)}


def get_health_summary() -> Dict[str, Any]:
    """Get recent health metrics summary."""
    db = get_db()
    today = date.today()
    yesterday = today - timedelta(days=1)

    try:
        metrics = db.get_health_metrics(start_date=yesterday, end_date=today)

        # Extract key metrics
        result = {
            'available': len(metrics) > 0,
            'sleep_score': None,
            'readiness_score': None,
            'activity_score': None,
        }

        for m in metrics:
            metric_type = m.get('metric_type', '')
            score = m.get('score')

            if 'sleep' in metric_type.lower() and score:
                result['sleep_score'] = score
            elif 'readiness' in metric_type.lower() and score:
                result['readiness_score'] = score
            elif 'activity' in metric_type.lower() and score:
                result['activity_score'] = score

        return result
    except Exception as e:
        return {'error': str(e), 'available': False}


def get_brain_dump_summary() -> Dict[str, Any]:
    """Get brain dump queue summary."""
    db = get_db()

    try:
        unprocessed = db.get_unprocessed_brain_dumps(limit=100)

        # Group by category
        by_category: Dict[str, int] = {}
        for dump in unprocessed:
            cat = dump.get('category') or 'uncategorized'
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            'unprocessed': len(unprocessed),
            'by_category': by_category,
        }
    except Exception as e:
        return {'error': str(e), 'unprocessed': 0}


async def get_alerts_summary() -> Dict[str, Any]:
    """Get current alerts summary."""
    try:
        alerts = await run_alert_check()

        by_priority: Dict[str, int] = {}
        by_type: Dict[str, int] = {}

        for alert in alerts:
            # Count by priority
            priority = alert.priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1

            # Count by type
            alert_type = alert.alert_type.value
            by_type[alert_type] = by_type.get(alert_type, 0) + 1

        return {
            'total': len(alerts),
            'by_priority': by_priority,
            'by_type': by_type,
            'alerts': [
                {
                    'priority': a.priority.value,
                    'title': a.title,
                    'message': a.message,
                }
                for a in alerts[:10]  # Top 10 alerts
            ],
        }
    except Exception as e:
        return {'error': str(e), 'total': 0}


def get_system_status() -> Dict[str, Any]:
    """Get system status information."""
    db = get_db()

    try:
        # Get schema version
        schema_version = db.get_schema_version()

        # Get database stats
        tables = db.execute_sql("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """)

        # Get recent journal entries
        journal = Journal()
        recent_events = journal.query(limit=5)

        return {
            'database': {
                'path': str(db.db_path),
                'schema_version': schema_version,
                'tables': len(tables),
            },
            'journal': {
                'recent_events': len(recent_events),
            },
        }
    except Exception as e:
        return {'error': str(e)}


async def generate_status(
    alerts_only: bool = False,
    brief: bool = False
) -> Dict[str, Any]:
    """
    Generate comprehensive status report.

    Args:
        alerts_only: Only include alerts section
        brief: Generate brief summary

    Returns:
        Status dictionary
    """
    timestamp = datetime.now().isoformat()

    if alerts_only:
        return {
            'timestamp': timestamp,
            'alerts': await get_alerts_summary(),
        }

    status = {
        'timestamp': timestamp,
        'alerts': await get_alerts_summary(),
        'tasks': get_task_summary(),
        'commitments': get_commitment_summary(),
        'health': get_health_summary(),
        'brain_dumps': get_brain_dump_summary(),
    }

    if not brief:
        status['system'] = get_system_status()

    return status


def format_status_text(status: Dict[str, Any]) -> str:
    """Format status as human-readable text."""
    lines = []
    timestamp = datetime.fromisoformat(status['timestamp'])

    lines.append("╔════════════════════════════════════════╗")
    lines.append("║         THANOS STATUS REPORT          ║")
    lines.append(f"║   {timestamp.strftime('%Y-%m-%d %H:%M:%S')}              ║")
    lines.append("╚════════════════════════════════════════╝")
    lines.append("")

    # Alerts section
    alerts = status.get('alerts', {})
    alert_count = alerts.get('total', 0)
    if alert_count > 0:
        lines.append("🚨 ALERTS")
        lines.append("-" * 40)
        for alert in alerts.get('alerts', [])[:5]:
            emoji = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '📢',
                'low': 'ℹ️',
            }.get(alert.get('priority'), '📝')
            lines.append(f"  {emoji} {alert.get('title')}")
        if alert_count > 5:
            lines.append(f"  ... and {alert_count - 5} more")
        lines.append("")

    # Tasks section
    tasks = status.get('tasks', {})
    if not tasks.get('error'):
        lines.append("📋 TASKS")
        lines.append("-" * 40)
        lines.append(f"  Total active: {tasks.get('total', 0)}")
        if tasks.get('overdue', 0) > 0:
            lines.append(f"  ⚠️  Overdue: {tasks.get('overdue')}")
        if tasks.get('due_today', 0) > 0:
            lines.append(f"  📅 Due today: {tasks.get('due_today')}")
        by_domain = tasks.get('by_domain', {})
        if by_domain:
            lines.append(f"  Work: {by_domain.get('work', 0)} | Personal: {by_domain.get('personal', 0)}")
        lines.append("")

    # Commitments section
    commits = status.get('commitments', {})
    if not commits.get('error'):
        lines.append("🤝 COMMITMENTS")
        lines.append("-" * 40)
        lines.append(f"  Total active: {commits.get('total', 0)}")
        overdue = commits.get('overdue', [])
        if overdue:
            lines.append(f"  🚨 Overdue ({len(overdue)}):")
            for o in overdue[:3]:
                lines.append(f"     - {o['title']} ({o['days_overdue']}d)")
        due_soon = commits.get('due_soon', [])
        if due_soon:
            lines.append(f"  ⏰ Due soon ({len(due_soon)}):")
            for d in due_soon[:3]:
                days = d['days_until']
                when = "today" if days == 0 else f"in {days}d"
                lines.append(f"     - {d['title']} ({when})")
        lines.append("")

    # Health section
    health = status.get('health', {})
    if health.get('available'):
        lines.append("💪 HEALTH (Oura)")
        lines.append("-" * 40)
        if health.get('sleep_score'):
            emoji = '🟢' if health['sleep_score'] >= 70 else '🟡' if health['sleep_score'] >= 50 else '🔴'
            lines.append(f"  {emoji} Sleep: {health['sleep_score']}")
        if health.get('readiness_score'):
            emoji = '🟢' if health['readiness_score'] >= 70 else '🟡' if health['readiness_score'] >= 50 else '🔴'
            lines.append(f"  {emoji} Readiness: {health['readiness_score']}")
        if health.get('activity_score'):
            emoji = '🟢' if health['activity_score'] >= 70 else '🟡' if health['activity_score'] >= 50 else '🔴'
            lines.append(f"  {emoji} Activity: {health['activity_score']}")
        lines.append("")

    # Brain dumps section
    dumps = status.get('brain_dumps', {})
    if dumps.get('unprocessed', 0) > 0:
        lines.append("🧠 BRAIN DUMP QUEUE")
        lines.append("-" * 40)
        lines.append(f"  Unprocessed: {dumps.get('unprocessed')}")
        by_cat = dumps.get('by_category', {})
        if by_cat:
            cat_str = ", ".join(f"{k}: {v}" for k, v in by_cat.items())
            lines.append(f"  {cat_str}")
        lines.append("")

    # System section
    system = status.get('system', {})
    if system and not system.get('error'):
        lines.append("⚙️  SYSTEM")
        lines.append("-" * 40)
        db_info = system.get('database', {})
        lines.append(f"  Schema v{db_info.get('schema_version', '?')}, {db_info.get('tables', 0)} tables")
        lines.append("")

    lines.append("═" * 40)

    return "\n".join(lines)


async def execute(
    output_json: bool = False,
    alerts_only: bool = False,
    brief: bool = False
) -> str:
    """
    Execute status command.

    Args:
        output_json: Output as JSON
        alerts_only: Only show alerts
        brief: Brief summary

    Returns:
        Formatted status string
    """
    status = await generate_status(alerts_only=alerts_only, brief=brief)

    if output_json:
        return json.dumps(status, indent=2, default=str)
    else:
        return format_status_text(status)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Thanos Status Report')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--alerts-only', action='store_true', help='Only show alerts')
    parser.add_argument('--brief', action='store_true', help='Brief summary')
    args = parser.parse_args()

    result = asyncio.run(execute(
        output_json=args.json,
        alerts_only=args.alerts_only,
        brief=args.brief
    ))

    print(result)


if __name__ == "__main__":
    main()
