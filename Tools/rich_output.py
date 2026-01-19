#!/usr/bin/env python3
"""
Rich-style formatting utility for Thanos CLI output.

Provides formatted tables, status bars, and progress indicators using
Python's rich library for beautiful terminal output.

Usage:
    from Tools.rich_output import (
        health_table, task_table, status_bar,
        progress_spinner, RichOutput
    )

    # Display health metrics
    health_table(readiness=85, sleep=78, hrv=45, rhr=58, energy="high")

    # Show tasks matched to energy level
    task_table(tasks, energy_level="medium")

    # Compact status bar
    status_bar(energy="high", readiness=85, active_tasks=3, points=12)

Can also be called via subprocess from other tools:
    python Tools/rich_output.py --health 85,78,45,58,high
    python Tools/rich_output.py --status high,85,3,12
"""

import sys
import json
import argparse
from typing import List, Dict, Any, Optional, Callable
from contextlib import contextmanager
from io import StringIO

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.live import Live
from rich.style import Style
from rich.box import ROUNDED, SIMPLE, MINIMAL


# Global console instance
console = Console()


def get_score_style(score: int, thresholds: tuple = (70, 85)) -> str:
    """
    Get color style based on score thresholds.

    Args:
        score: Numeric score to evaluate
        thresholds: Tuple of (low_threshold, high_threshold)
                   - score >= high_threshold = green
                   - low_threshold <= score < high_threshold = yellow
                   - score < low_threshold = red

    Returns:
        Style string for Rich
    """
    low, high = thresholds
    if score >= high:
        return "green"
    elif score >= low:
        return "yellow"
    else:
        return "red"


def get_score_indicator(score: int, thresholds: tuple = (70, 85)) -> str:
    """
    Get status indicator based on score.

    Args:
        score: Numeric score
        thresholds: (low, high) thresholds

    Returns:
        Status emoji/indicator
    """
    low, high = thresholds
    if score >= high:
        return "[green]OK[/green]"
    elif score >= low:
        return "[yellow]FAIR[/yellow]"
    else:
        return "[red]LOW[/red]"


def health_table(
    readiness: int,
    sleep: int,
    hrv: int,
    rhr: int,
    energy: str,
    show_recommendations: bool = True,
    return_string: bool = False
) -> Optional[str]:
    """
    Create a formatted health status table.

    Args:
        readiness: Oura readiness score (0-100)
        sleep: Oura sleep score (0-100)
        hrv: Heart rate variability
        rhr: Resting heart rate
        energy: Energy level string (high/medium/low)
        show_recommendations: Whether to show recommendations based on scores
        return_string: If True, return as string instead of printing

    Returns:
        String output if return_string=True, else None (prints directly)
    """
    table = Table(
        title="[bold]Health Status[/bold]",
        box=ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Score", justify="right", style="bold")
    table.add_column("Status", justify="center")

    # Readiness row
    readiness_style = get_score_style(readiness)
    table.add_row(
        "Readiness",
        f"[{readiness_style}]{readiness}[/{readiness_style}]",
        get_score_indicator(readiness)
    )

    # Sleep row
    sleep_style = get_score_style(sleep)
    table.add_row(
        "Sleep",
        f"[{sleep_style}]{sleep}[/{sleep_style}]",
        get_score_indicator(sleep)
    )

    # HRV row (different thresholds - higher is better, typical range 20-70)
    hrv_style = get_score_style(hrv, thresholds=(30, 50))
    table.add_row(
        "HRV",
        f"[{hrv_style}]{hrv} ms[/{hrv_style}]",
        get_score_indicator(hrv, thresholds=(30, 50))
    )

    # RHR row (inverted - lower is generally better, typical range 50-80)
    # Invert the logic: < 60 is good, 60-70 is fair, > 70 is concerning
    if rhr < 60:
        rhr_style = "green"
        rhr_status = "[green]OK[/green]"
    elif rhr < 70:
        rhr_style = "yellow"
        rhr_status = "[yellow]FAIR[/yellow]"
    else:
        rhr_style = "red"
        rhr_status = "[red]HIGH[/red]"

    table.add_row(
        "RHR",
        f"[{rhr_style}]{rhr} bpm[/{rhr_style}]",
        rhr_status
    )

    # Energy level row
    energy_colors = {"high": "green", "medium": "yellow", "low": "red"}
    energy_style = energy_colors.get(energy.lower(), "white")
    energy_display = energy.upper()
    table.add_row(
        "Energy",
        f"[{energy_style} bold]{energy_display}[/{energy_style} bold]",
        f"[{energy_style}]{'*' * {'high': 3, 'medium': 2, 'low': 1}.get(energy.lower(), 0)}[/{energy_style}]"
    )

    if return_string:
        buffer = StringIO()
        temp_console = Console(file=buffer, force_terminal=True, width=60)
        temp_console.print(table)

        if show_recommendations:
            rec = _get_recommendation(readiness, sleep, energy)
            temp_console.print(f"\n[dim italic]{rec}[/dim italic]")

        return buffer.getvalue()
    else:
        console.print(table)

        if show_recommendations:
            rec = _get_recommendation(readiness, sleep, energy)
            console.print(f"\n[dim italic]{rec}[/dim italic]")

        return None


def _get_recommendation(readiness: int, sleep: int, energy: str) -> str:
    """Generate recommendation based on health metrics."""
    if readiness >= 85 and sleep >= 80:
        return "Great day for deep work and challenging tasks!"
    elif readiness >= 70:
        return "Good for standard tasks. Consider breaks for focus."
    elif readiness >= 60:
        return "Take it easier today. Focus on lighter tasks."
    else:
        return "Rest priority. Stick to essential tasks only."


def task_table(
    tasks: List[Dict[str, Any]],
    energy_level: str,
    show_match: bool = True,
    return_string: bool = False
) -> Optional[str]:
    """
    Display tasks matched to current energy level.

    Args:
        tasks: List of task dictionaries with keys:
               - title: Task title
               - category: 'work' or 'personal'
               - cognitive_load: 'low', 'medium', 'high'
               - status: 'active', 'queued', 'backlog'
               - value_tier: 'checkbox', 'progress', 'deliverable', 'milestone'
        energy_level: Current energy level ('high', 'medium', 'low')
        show_match: Show energy-task match indicator
        return_string: If True, return as string instead of printing

    Returns:
        String output if return_string=True, else None
    """
    energy_level = energy_level.lower()

    # Define which cognitive loads match which energy levels
    energy_to_cognitive = {
        "high": ["high", "medium", "low"],
        "medium": ["medium", "low"],
        "low": ["low"]
    }
    ideal_loads = energy_to_cognitive.get(energy_level, ["medium"])

    table = Table(
        title=f"[bold]Tasks for {energy_level.upper()} Energy[/bold]",
        box=ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Task", style="white", no_wrap=False, max_width=40)
    table.add_column("Type", justify="center", width=8)
    table.add_column("Load", justify="center", width=8)

    if show_match:
        table.add_column("Match", justify="center", width=6)

    # Sort tasks: matching cognitive load first, then by status
    def task_sort_key(t):
        load = t.get("cognitive_load", "medium")
        is_match = load in ideal_loads
        status_order = {"active": 0, "queued": 1, "backlog": 2}
        return (0 if is_match else 1, status_order.get(t.get("status"), 2))

    sorted_tasks = sorted(tasks, key=task_sort_key)

    for task in sorted_tasks[:15]:  # Limit to 15 tasks
        title = task.get("title", "Untitled")[:40]
        category = task.get("category", "work")
        cognitive_load = task.get("cognitive_load", "medium")

        # Category indicator
        cat_icon = "[blue]W[/blue]" if category == "work" else "[magenta]P[/magenta]"

        # Cognitive load with color
        load_colors = {"low": "green", "medium": "yellow", "high": "red"}
        load_color = load_colors.get(cognitive_load, "white")
        load_display = f"[{load_color}]{cognitive_load}[/{load_color}]"

        row = [title, cat_icon, load_display]

        if show_match:
            # Match indicator
            is_good_match = cognitive_load in ideal_loads
            match_indicator = "[green]Y[/green]" if is_good_match else "[dim]-[/dim]"
            row.append(match_indicator)

        table.add_row(*row)

    if return_string:
        buffer = StringIO()
        temp_console = Console(file=buffer, force_terminal=True, width=70)
        temp_console.print(table)
        return buffer.getvalue()
    else:
        console.print(table)
        return None


def status_bar(
    energy: str,
    readiness: int,
    active_tasks: int,
    points: int,
    target_points: int = 18,
    streak: int = 0,
    return_string: bool = False
) -> Optional[str]:
    """
    Create a compact status bar showing key metrics.

    Args:
        energy: Energy level (high/medium/low)
        readiness: Readiness score (0-100)
        active_tasks: Number of active tasks
        points: Points earned today
        target_points: Daily target points
        streak: Current streak days
        return_string: If True, return as string instead of printing

    Returns:
        String output if return_string=True, else None
    """
    energy_colors = {"high": "green", "medium": "yellow", "low": "red"}
    energy_style = energy_colors.get(energy.lower(), "white")

    # Build status components
    energy_text = f"[{energy_style} bold]{energy.upper()}[/{energy_style} bold]"

    readiness_style = get_score_style(readiness)
    readiness_text = f"[{readiness_style}]{readiness}[/{readiness_style}]"

    # Points progress
    points_pct = min(100, int((points / target_points) * 100)) if target_points > 0 else 0
    if points >= target_points:
        points_style = "green bold"
    elif points >= target_points * 0.7:
        points_style = "yellow"
    else:
        points_style = "white"
    points_text = f"[{points_style}]{points}/{target_points}[/{points_style}]"

    # Build the status line
    status_parts = [
        f"Energy: {energy_text}",
        f"Ready: {readiness_text}",
        f"Tasks: [cyan]{active_tasks}[/cyan]",
        f"Points: {points_text}",
    ]

    if streak > 0:
        status_parts.append(f"Streak: [yellow bold]{streak}d[/yellow bold]")

    status_line = " | ".join(status_parts)

    panel = Panel(
        status_line,
        title="[bold]Thanos Status[/bold]",
        border_style="blue",
        box=ROUNDED,
        padding=(0, 1)
    )

    if return_string:
        buffer = StringIO()
        temp_console = Console(file=buffer, force_terminal=True, width=80)
        temp_console.print(panel)
        return buffer.getvalue()
    else:
        console.print(panel)
        return None


@contextmanager
def progress_spinner(description: str = "Processing..."):
    """
    Context manager for showing a progress spinner during long operations.

    Args:
        description: Text to display alongside spinner

    Usage:
        with progress_spinner("Loading data..."):
            # long operation
            time.sleep(2)
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        task = progress.add_task(description, total=None)
        try:
            yield progress
        finally:
            progress.update(task, completed=True)


def progress_bar(
    items: List[Any],
    description: str = "Processing",
    process_func: Optional[Callable] = None
) -> List[Any]:
    """
    Process items with a progress bar.

    Args:
        items: List of items to process
        description: Progress bar description
        process_func: Optional function to apply to each item

    Returns:
        List of processed items (or original if no process_func)
    """
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task(description, total=len(items))

        for item in items:
            if process_func:
                result = process_func(item)
                results.append(result)
            else:
                results.append(item)
            progress.advance(task)

    return results


def alert_panel(
    title: str,
    message: str,
    severity: str = "info",
    return_string: bool = False
) -> Optional[str]:
    """
    Display an alert panel.

    Args:
        title: Alert title
        message: Alert message
        severity: 'info', 'warning', 'error', 'success'
        return_string: If True, return as string

    Returns:
        String output if return_string=True, else None
    """
    styles = {
        "info": ("blue", "INFO"),
        "warning": ("yellow", "WARNING"),
        "error": ("red", "ERROR"),
        "success": ("green", "SUCCESS")
    }

    color, badge = styles.get(severity, ("white", "NOTICE"))

    panel = Panel(
        f"[{color}]{message}[/{color}]",
        title=f"[bold {color}][{badge}] {title}[/bold {color}]",
        border_style=color,
        box=ROUNDED
    )

    if return_string:
        buffer = StringIO()
        temp_console = Console(file=buffer, force_terminal=True, width=70)
        temp_console.print(panel)
        return buffer.getvalue()
    else:
        console.print(panel)
        return None


def habit_grid(
    habits: List[Dict[str, Any]],
    days: int = 7,
    return_string: bool = False
) -> Optional[str]:
    """
    Display a habit completion grid.

    Args:
        habits: List of habit dictionaries with:
               - name: Habit name
               - emoji: Habit emoji
               - streak: Current streak
               - completions: List of completion dates (ISO strings)
        days: Number of days to show
        return_string: If True, return as string

    Returns:
        String output if return_string=True, else None
    """
    from datetime import datetime, timedelta

    table = Table(
        title="[bold]Habit Tracker[/bold]",
        box=SIMPLE,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Habit", style="white", no_wrap=True)

    # Add columns for each day
    today = datetime.now().date()
    date_cols = []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_name = day.strftime("%a")
        table.add_column(day_name, justify="center", width=4)
        date_cols.append(day.isoformat())

    table.add_column("Streak", justify="right", width=6)

    for habit in habits:
        name = habit.get("name", "Unknown")
        emoji = habit.get("emoji", "")
        streak = habit.get("streak", 0)
        completions = set(habit.get("completions", []))

        row = [f"{emoji} {name}"]

        for date_str in date_cols:
            if date_str in completions:
                row.append("[green]Y[/green]")
            else:
                row.append("[dim]-[/dim]")

        streak_style = "yellow bold" if streak > 0 else "dim"
        row.append(f"[{streak_style}]{streak}d[/{streak_style}]")

        table.add_row(*row)

    if return_string:
        buffer = StringIO()
        temp_console = Console(file=buffer, force_terminal=True, width=60)
        temp_console.print(table)
        return buffer.getvalue()
    else:
        console.print(table)
        return None


def brain_dump_list(
    entries: List[Dict[str, Any]],
    limit: int = 10,
    return_string: bool = False
) -> Optional[str]:
    """
    Display brain dump entries in a formatted list.

    Args:
        entries: List of brain dump dictionaries with:
                - content: The brain dump text
                - classification: thinking, venting, task, idea, etc.
                - timestamp: ISO timestamp
                - processed: bool
        limit: Maximum entries to show
        return_string: If True, return as string

    Returns:
        String output if return_string=True, else None
    """
    classification_styles = {
        "thinking": ("blue", "thought"),
        "venting": ("red", "vent"),
        "observation": ("cyan", "observe"),
        "note": ("white", "note"),
        "idea": ("yellow", "idea"),
        "personal_task": ("magenta", "p-task"),
        "work_task": ("blue", "w-task"),
        "commitment": ("green", "commit"),
        "mixed": ("dim", "mixed"),
        "task": ("cyan", "task"),
        "thought": ("blue", "thought"),
    }

    table = Table(
        title=f"[bold]Brain Dumps ({len(entries)} pending)[/bold]",
        box=ROUNDED,
        show_header=True,
        header_style="bold cyan"
    )

    table.add_column("Type", justify="center", width=8)
    table.add_column("Content", style="white", no_wrap=False, max_width=50)
    table.add_column("Status", justify="center", width=8)

    for entry in entries[:limit]:
        classification = entry.get("classification", "note")
        color, label = classification_styles.get(classification, ("white", classification[:6]))

        content = entry.get("content", "")[:50]
        if len(entry.get("content", "")) > 50:
            content += "..."

        processed = entry.get("processed", False)
        status = "[green]done[/green]" if processed else "[yellow]pending[/yellow]"

        table.add_row(
            f"[{color}]{label}[/{color}]",
            content,
            status
        )

    if len(entries) > limit:
        table.add_row(
            "[dim]...[/dim]",
            f"[dim]+{len(entries) - limit} more[/dim]",
            ""
        )

    if return_string:
        buffer = StringIO()
        temp_console = Console(file=buffer, force_terminal=True, width=70)
        temp_console.print(table)
        return buffer.getvalue()
    else:
        console.print(table)
        return None


class RichOutput:
    """
    Wrapper class for all rich output functions.

    Provides a unified interface and handles return_string consistently.
    """

    def __init__(self, return_string: bool = False):
        """
        Initialize RichOutput.

        Args:
            return_string: If True, all methods return strings instead of printing
        """
        self.return_string = return_string

    def health(self, readiness: int, sleep: int, hrv: int, rhr: int, energy: str, **kwargs) -> Optional[str]:
        """Display health table."""
        return health_table(
            readiness=readiness,
            sleep=sleep,
            hrv=hrv,
            rhr=rhr,
            energy=energy,
            return_string=self.return_string,
            **kwargs
        )

    def tasks(self, tasks: List[Dict], energy_level: str, **kwargs) -> Optional[str]:
        """Display task table."""
        return task_table(
            tasks=tasks,
            energy_level=energy_level,
            return_string=self.return_string,
            **kwargs
        )

    def status(self, energy: str, readiness: int, active_tasks: int, points: int, **kwargs) -> Optional[str]:
        """Display status bar."""
        return status_bar(
            energy=energy,
            readiness=readiness,
            active_tasks=active_tasks,
            points=points,
            return_string=self.return_string,
            **kwargs
        )

    def alert(self, title: str, message: str, severity: str = "info") -> Optional[str]:
        """Display alert panel."""
        return alert_panel(
            title=title,
            message=message,
            severity=severity,
            return_string=self.return_string
        )

    def habits(self, habits: List[Dict], days: int = 7) -> Optional[str]:
        """Display habit grid."""
        return habit_grid(
            habits=habits,
            days=days,
            return_string=self.return_string
        )

    def brain_dumps(self, entries: List[Dict], limit: int = 10) -> Optional[str]:
        """Display brain dump list."""
        return brain_dump_list(
            entries=entries,
            limit=limit,
            return_string=self.return_string
        )


def demo():
    """
    Demonstrate all rich output components with sample data.
    """
    console.print("\n[bold blue]Thanos Rich Output Demo[/bold blue]\n")
    console.print("=" * 60)

    # Health table demo
    console.print("\n[bold]1. Health Status Table[/bold]\n")
    health_table(
        readiness=78,
        sleep=82,
        hrv=45,
        rhr=58,
        energy="medium"
    )

    # Task table demo
    console.print("\n[bold]2. Energy-Aware Task Table[/bold]\n")
    sample_tasks = [
        {"title": "Review quarterly report", "category": "work", "cognitive_load": "high", "status": "active"},
        {"title": "Reply to emails", "category": "work", "cognitive_load": "low", "status": "active"},
        {"title": "Code review PR #42", "category": "work", "cognitive_load": "medium", "status": "queued"},
        {"title": "Schedule dentist appointment", "category": "personal", "cognitive_load": "low", "status": "active"},
        {"title": "Research vacation destinations", "category": "personal", "cognitive_load": "medium", "status": "backlog"},
    ]
    task_table(tasks=sample_tasks, energy_level="medium")

    # Status bar demo
    console.print("\n[bold]3. Status Bar[/bold]\n")
    status_bar(
        energy="medium",
        readiness=78,
        active_tasks=4,
        points=12,
        target_points=18,
        streak=5
    )

    # Alert panel demo
    console.print("\n[bold]4. Alert Panels[/bold]\n")
    alert_panel("Low Readiness", "Consider taking it easy today", severity="warning")

    # Habit grid demo
    console.print("\n[bold]5. Habit Tracker Grid[/bold]\n")
    from datetime import datetime, timedelta
    today = datetime.now().date()
    sample_habits = [
        {
            "name": "Exercise",
            "emoji": "running",
            "streak": 3,
            "completions": [
                (today - timedelta(days=i)).isoformat()
                for i in range(3)
            ]
        },
        {
            "name": "Read",
            "emoji": "books",
            "streak": 7,
            "completions": [
                (today - timedelta(days=i)).isoformat()
                for i in range(7)
            ]
        },
        {
            "name": "Meditate",
            "emoji": "pray",
            "streak": 0,
            "completions": [
                (today - timedelta(days=3)).isoformat(),
                (today - timedelta(days=5)).isoformat(),
            ]
        },
    ]
    habit_grid(habits=sample_habits, days=7)

    # Brain dump list demo
    console.print("\n[bold]6. Brain Dump List[/bold]\n")
    sample_dumps = [
        {"content": "Need to call mom about birthday plans", "classification": "personal_task", "processed": False},
        {"content": "Maybe we could add caching to improve API response times", "classification": "idea", "processed": False},
        {"content": "Feeling overwhelmed with the project timeline", "classification": "venting", "processed": False},
        {"content": "Noticed the CI build is slow lately", "classification": "observation", "processed": True},
    ]
    brain_dump_list(entries=sample_dumps)

    console.print("\n" + "=" * 60)
    console.print("[bold green]Demo complete![/bold green]\n")


def main():
    """CLI interface for rich_output module."""
    parser = argparse.ArgumentParser(
        description='Rich-style CLI output for Thanos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Display health metrics
  python rich_output.py --health 85,78,45,58,high

  # Display status bar
  python rich_output.py --status high,85,3,12

  # Display tasks from JSON
  python rich_output.py --tasks '[{"title":"Task 1","category":"work","cognitive_load":"high"}]' --energy medium

  # Run demo
  python rich_output.py --demo

  # Get output as string (for subprocess capture)
  python rich_output.py --health 85,78,45,58,high --as-string
"""
    )

    parser.add_argument('--health', type=str, metavar='SCORES',
                       help='Health metrics as: readiness,sleep,hrv,rhr,energy')
    parser.add_argument('--status', type=str, metavar='VALUES',
                       help='Status bar as: energy,readiness,tasks,points[,target,streak]')
    parser.add_argument('--tasks', type=str, metavar='JSON',
                       help='Tasks JSON array')
    parser.add_argument('--energy', type=str, default='medium',
                       help='Energy level for task matching')
    parser.add_argument('--alert', type=str, nargs=3, metavar=('TITLE', 'MSG', 'SEVERITY'),
                       help='Show alert panel')
    parser.add_argument('--demo', action='store_true',
                       help='Run demo showing all components')
    parser.add_argument('--as-string', action='store_true',
                       help='Return output as string (for subprocess)')
    parser.add_argument('--json-output', action='store_true',
                       help='Wrap string output in JSON for easy parsing')

    args = parser.parse_args()

    output = RichOutput(return_string=args.as_string)
    result = None

    if args.demo:
        demo()
        return

    if args.health:
        try:
            parts = args.health.split(',')
            result = output.health(
                readiness=int(parts[0]),
                sleep=int(parts[1]),
                hrv=int(parts[2]),
                rhr=int(parts[3]),
                energy=parts[4] if len(parts) > 4 else 'medium'
            )
        except (ValueError, IndexError) as e:
            console.print(f"[red]Error parsing health values: {e}[/red]")
            sys.exit(1)

    elif args.status:
        try:
            parts = args.status.split(',')
            result = output.status(
                energy=parts[0],
                readiness=int(parts[1]),
                active_tasks=int(parts[2]),
                points=int(parts[3]),
                target_points=int(parts[4]) if len(parts) > 4 else 18,
                streak=int(parts[5]) if len(parts) > 5 else 0
            )
        except (ValueError, IndexError) as e:
            console.print(f"[red]Error parsing status values: {e}[/red]")
            sys.exit(1)

    elif args.tasks:
        try:
            tasks = json.loads(args.tasks)
            result = output.tasks(tasks=tasks, energy_level=args.energy)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error parsing tasks JSON: {e}[/red]")
            sys.exit(1)

    elif args.alert:
        title, message, severity = args.alert
        result = output.alert(title=title, message=message, severity=severity)

    else:
        parser.print_help()
        return

    # Handle string output
    if args.as_string and result:
        if args.json_output:
            print(json.dumps({"output": result}))
        else:
            print(result)


if __name__ == "__main__":
    main()
