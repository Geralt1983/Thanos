#!/usr/bin/env python3
"""
Thanos Status Command - Comprehensive System Dashboard.

Displays unified state, health, alerts, and system status.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Setup path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from Tools.output_formatter import format_header as responsive_header, is_mobile, wrap_text, format_list as responsive_list


# ANSI color codes
class Colors:
    PURPLE = "\033[35m"
    CYAN = "\033[36m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    WHITE = "\033[37m"


@dataclass
class StatusSection:
    """A section of the status display."""
    title: str
    content: str
    status: str = "ok"  # ok, warning, critical, unknown


class ThanosStatus:
    """
    Comprehensive status command for Thanos.

    Displays:
    - State summary (tasks, commitments, focus)
    - Health metrics (Oura)
    - Recent alerts (Journal)
    - Circuit breaker health
    - Daemon status
    - Brain dump queue
    """

    def __init__(self, thanos_dir: Optional[Path] = None):
        """Initialize status command with Thanos directory."""
        self.thanos_dir = thanos_dir or Path(__file__).parent.parent
        self.state_dir = self.thanos_dir / "State"

    def _format_header(self, text: str, width: int = 50) -> str:
        """Format a section header - responsive for mobile/desktop."""
        if is_mobile():
            return f"\n{Colors.BOLD}{Colors.CYAN}{responsive_header(text)}{Colors.RESET}"
        return f"\n{Colors.BOLD}{Colors.CYAN}{'─' * 3} {text} {'─' * (width - len(text) - 5)}{Colors.RESET}"

    def _format_status_indicator(self, status: str) -> str:
        """Format a status indicator."""
        indicators = {
            "ok": f"{Colors.GREEN}●{Colors.RESET}",
            "warning": f"{Colors.YELLOW}●{Colors.RESET}",
            "critical": f"{Colors.RED}●{Colors.RESET}",
            "unknown": f"{Colors.DIM}○{Colors.RESET}"
        }
        return indicators.get(status, indicators["unknown"])

    def _format_value(self, label: str, value: Any, status: str = "ok") -> str:
        """Format a labeled value."""
        indicator = self._format_status_indicator(status)
        return f"  {indicator} {Colors.DIM}{label}:{Colors.RESET} {value}"

    def get_state_summary(self) -> StatusSection:
        """Get state summary from unified state store or legacy files."""
        content_lines = []
        overall_status = "ok"

        try:
            # Try unified state store first
            try:
                from Tools.state_store import StateStore
                store = StateStore()

                # Get today's tasks
                tasks = store.get_tasks_due_today()
                overdue = store.get_overdue_tasks()
                commitments = store.get_active_commitments()

                if overdue:
                    overall_status = "critical" if len(overdue) >= 3 else "warning"
                    content_lines.append(self._format_value(
                        "Overdue tasks",
                        f"{Colors.RED}{len(overdue)}{Colors.RESET}",
                        "critical"
                    ))

                content_lines.append(self._format_value(
                    "Due today",
                    len(tasks),
                    "ok" if tasks else "warning"
                ))

                content_lines.append(self._format_value(
                    "Active commitments",
                    len(commitments),
                    "ok"
                ))

            except ImportError:
                # Fallback to legacy state files
                today_file = self.state_dir / "Today.md"
                commitments_file = self.state_dir / "Commitments.md"

                if today_file.exists():
                    content = today_file.read_text()
                    # Count tasks (lines starting with - [ ])
                    open_tasks = content.count("- [ ]")
                    done_tasks = content.count("- [x]")
                    content_lines.append(self._format_value(
                        "Tasks today",
                        f"{done_tasks}/{done_tasks + open_tasks} done",
                        "ok" if open_tasks < 5 else "warning"
                    ))
                else:
                    content_lines.append(self._format_value("Today.md", "not found", "unknown"))

                if commitments_file.exists():
                    content = commitments_file.read_text()
                    # Count commitment items
                    commitment_count = content.count("##") - 1  # Exclude title
                    content_lines.append(self._format_value(
                        "Commitments",
                        f"{max(0, commitment_count)} tracked",
                        "ok"
                    ))

            # Get focus area
            focus_file = self.state_dir / "CurrentFocus.md"
            if focus_file.exists():
                focus = focus_file.read_text().strip().split('\n')[0]
                if focus.startswith('#'):
                    focus = focus.lstrip('#').strip()
                content_lines.append(self._format_value("Focus", focus[:30], "ok"))

        except Exception as e:
            content_lines.append(f"  {Colors.RED}Error loading state: {e}{Colors.RESET}")
            overall_status = "critical"

        return StatusSection(
            title="State",
            content='\n'.join(content_lines) if content_lines else "  No state data",
            status=overall_status
        )

    def get_health_summary(self) -> StatusSection:
        """Get health summary from Oura cache or API."""
        content_lines = []
        overall_status = "unknown"

        try:
            # Check for cached Oura data
            cache_file = self.state_dir / "OuraCache.json"
            today = datetime.now().strftime("%Y-%m-%d")

            if cache_file.exists():
                cache = json.loads(cache_file.read_text())
                data = cache.get(today, {})

                if data:
                    # Readiness
                    readiness = data.get("readiness", {}).get("score")
                    if readiness is not None:
                        status = "ok" if readiness >= 70 else ("warning" if readiness >= 50 else "critical")
                        overall_status = status
                        content_lines.append(self._format_value(
                            "Readiness",
                            f"{readiness}/100",
                            status
                        ))

                    # Sleep
                    sleep = data.get("sleep", {}).get("score")
                    if sleep is not None:
                        status = "ok" if sleep >= 70 else ("warning" if sleep >= 55 else "critical")
                        if status == "critical":
                            overall_status = status
                        content_lines.append(self._format_value(
                            "Sleep",
                            f"{sleep}/100",
                            status
                        ))

                    # HRV
                    hrv = data.get("readiness", {}).get("contributors", {}).get("hrv_balance")
                    if hrv is not None:
                        status = "ok" if hrv >= 50 else ("warning" if hrv >= 30 else "critical")
                        content_lines.append(self._format_value(
                            "HRV Balance",
                            f"{hrv}",
                            status
                        ))

            if not content_lines:
                content_lines.append(f"  {Colors.DIM}No health data cached for today{Colors.RESET}")
                content_lines.append(f"  {Colors.DIM}Run /oura to fetch latest{Colors.RESET}")

        except Exception as e:
            content_lines.append(f"  {Colors.DIM}Health data unavailable: {e}{Colors.RESET}")

        return StatusSection(
            title="Health",
            content='\n'.join(content_lines),
            status=overall_status
        )

    def get_alerts_summary(self) -> StatusSection:
        """Get recent alerts from journal."""
        content_lines = []
        overall_status = "ok"

        try:
            from Tools.journal import Journal

            journal = Journal()
            alerts = journal.get_alerts(acknowledged=False, limit=5)

            if alerts:
                # Count by severity
                by_severity = {}
                for alert in alerts:
                    sev = alert.severity.value
                    by_severity[sev] = by_severity.get(sev, 0) + 1

                if by_severity.get('critical', 0) > 0:
                    overall_status = "critical"
                elif by_severity.get('warning', 0) > 0 or by_severity.get('alert', 0) > 0:
                    overall_status = "warning"

                content_lines.append(self._format_value(
                    "Unacknowledged",
                    len(alerts),
                    overall_status
                ))

                # Show most recent alerts
                for alert in alerts[:3]:
                    severity_color = {
                        'critical': Colors.RED,
                        'alert': Colors.RED,
                        'warning': Colors.YELLOW,
                        'info': Colors.BLUE
                    }.get(alert.severity.value, Colors.DIM)

                    time_str = alert.timestamp.strftime("%H:%M")
                    msg = alert.message[:40] + "..." if len(alert.message) > 40 else alert.message
                    content_lines.append(
                        f"  {severity_color}[{alert.severity.value.upper()}]{Colors.RESET} "
                        f"{Colors.DIM}{time_str}{Colors.RESET} {msg}"
                    )
            else:
                content_lines.append(f"  {Colors.GREEN}✓ No unacknowledged alerts{Colors.RESET}")

        except ImportError:
            content_lines.append(f"  {Colors.DIM}Journal not initialized{Colors.RESET}")
        except Exception as e:
            content_lines.append(f"  {Colors.DIM}Could not load alerts: {e}{Colors.RESET}")

        return StatusSection(
            title="Alerts",
            content='\n'.join(content_lines),
            status=overall_status
        )

    def get_circuit_breaker_summary(self) -> StatusSection:
        """Get circuit breaker health status."""
        content_lines = []
        overall_status = "ok"

        try:
            from Tools.circuit_breaker import get_circuit_health, get_all_circuits

            health = get_circuit_health()
            circuits = get_all_circuits()

            if circuits:
                open_count = sum(1 for c in circuits.values() if c.state.name == "OPEN")
                half_open = sum(1 for c in circuits.values() if c.state.name == "HALF_OPEN")

                if open_count > 0:
                    overall_status = "critical"
                elif half_open > 0:
                    overall_status = "warning"

                content_lines.append(self._format_value(
                    "Circuits",
                    f"{len(circuits)} registered",
                    "ok"
                ))

                if open_count > 0:
                    content_lines.append(self._format_value(
                        "Open (failing)",
                        f"{Colors.RED}{open_count}{Colors.RESET}",
                        "critical"
                    ))

                if half_open > 0:
                    content_lines.append(self._format_value(
                        "Half-open (testing)",
                        half_open,
                        "warning"
                    ))

                # Show any problematic circuits
                for name, circuit in circuits.items():
                    if circuit.state.name != "CLOSED":
                        status = "critical" if circuit.state.name == "OPEN" else "warning"
                        content_lines.append(
                            f"    {self._format_status_indicator(status)} "
                            f"{name}: {circuit.state.name}"
                        )
            else:
                content_lines.append(f"  {Colors.DIM}No circuits registered{Colors.RESET}")

        except ImportError:
            content_lines.append(f"  {Colors.DIM}Circuit breaker not initialized{Colors.RESET}")
        except Exception as e:
            content_lines.append(f"  {Colors.DIM}Could not load circuits: {e}{Colors.RESET}")

        return StatusSection(
            title="Circuit Breakers",
            content='\n'.join(content_lines),
            status=overall_status
        )

    def get_daemon_summary(self) -> StatusSection:
        """Get background daemon status."""
        content_lines = []
        overall_status = "unknown"

        try:
            daemon_state_file = self.state_dir / "daemon_state.json"

            if daemon_state_file.exists():
                state = json.loads(daemon_state_file.read_text())

                last_run = state.get("last_run")
                if last_run:
                    last_run_dt = datetime.fromisoformat(last_run)
                    age = datetime.now() - last_run_dt
                    age_mins = age.total_seconds() / 60

                    # Expect run every 15 minutes
                    if age_mins < 20:
                        overall_status = "ok"
                        status = "ok"
                    elif age_mins < 60:
                        overall_status = "warning"
                        status = "warning"
                    else:
                        overall_status = "critical"
                        status = "critical"

                    content_lines.append(self._format_value(
                        "Last run",
                        f"{int(age_mins)}m ago",
                        status
                    ))

                content_lines.append(self._format_value(
                    "Total runs",
                    state.get("run_count", 0),
                    "ok"
                ))

                content_lines.append(self._format_value(
                    "Total alerts",
                    state.get("total_alerts", 0),
                    "ok"
                ))

                # Show checker states
                checker_states = state.get("checker_states", {})
                for checker_name, checker_state in checker_states.items():
                    error = checker_state.get("error")
                    if error:
                        content_lines.append(self._format_value(
                            f"  {checker_name}",
                            f"{Colors.RED}error{Colors.RESET}",
                            "critical"
                        ))
            else:
                content_lines.append(f"  {Colors.DIM}Daemon not yet run{Colors.RESET}")
                content_lines.append(f"  {Colors.DIM}Run: python Tools/alert_daemon.py --once{Colors.RESET}")

        except Exception as e:
            content_lines.append(f"  {Colors.DIM}Could not load daemon state: {e}{Colors.RESET}")

        return StatusSection(
            title="Alert Daemon",
            content='\n'.join(content_lines),
            status=overall_status
        )

    def get_brain_dump_summary(self) -> StatusSection:
        """Get brain dump queue summary."""
        content_lines = []
        overall_status = "ok"

        try:
            brain_dump_file = self.state_dir / "brain_dumps.json"

            if brain_dump_file.exists():
                entries = json.loads(brain_dump_file.read_text())
                unprocessed = [e for e in entries if not e.get("processed", False)]

                if unprocessed:
                    # Count by category
                    by_category: Dict[str, int] = {}
                    for entry in unprocessed:
                        cat = entry.get("parsed_category", "uncategorized")
                        by_category[cat] = by_category.get(cat, 0) + 1

                    if len(unprocessed) > 10:
                        overall_status = "warning"

                    content_lines.append(self._format_value(
                        "Pending",
                        len(unprocessed),
                        overall_status
                    ))

                    # Show breakdown
                    for cat, count in sorted(by_category.items(), key=lambda x: -x[1]):
                        emoji = {
                            'task': '✅',
                            'idea': '💡',
                            'worry': '😰',
                            'commitment': '🤝',
                            'thought': '💭',
                            'question': '❓'
                        }.get(cat, '📝')
                        content_lines.append(f"    {emoji} {cat}: {count}")
                else:
                    content_lines.append(f"  {Colors.GREEN}✓ Brain dump queue empty{Colors.RESET}")
            else:
                content_lines.append(f"  {Colors.DIM}No brain dumps captured yet{Colors.RESET}")

        except Exception as e:
            content_lines.append(f"  {Colors.DIM}Could not load brain dumps: {e}{Colors.RESET}")

        return StatusSection(
            title="Brain Dump",
            content='\n'.join(content_lines),
            status=overall_status
        )

    def get_full_status(self) -> str:
        """Generate complete status display with responsive layout."""
        sections = [
            self.get_state_summary(),
            self.get_health_summary(),
            self.get_alerts_summary(),
            self.get_circuit_breaker_summary(),
            self.get_daemon_summary(),
            self.get_brain_dump_summary(),
        ]

        # Build header with overall status
        overall_statuses = [s.status for s in sections]
        if "critical" in overall_statuses:
            overall = "critical"
            status_text = f"{Colors.RED}⚠ ISSUES{Colors.RESET}" if is_mobile() else f"{Colors.RED}⚠ ISSUES DETECTED{Colors.RESET}"
        elif "warning" in overall_statuses:
            overall = "warning"
            status_text = f"{Colors.YELLOW}⚡ ATTENTION{Colors.RESET}" if is_mobile() else f"{Colors.YELLOW}⚡ NEEDS ATTENTION{Colors.RESET}"
        elif "unknown" in overall_statuses and all(s == "unknown" for s in overall_statuses):
            overall = "unknown"
            status_text = f"{Colors.DIM}○ INIT{Colors.RESET}" if is_mobile() else f"{Colors.DIM}○ INITIALIZING{Colors.RESET}"
        else:
            overall = "ok"
            status_text = f"{Colors.GREEN}✓ OK{Colors.RESET}" if is_mobile() else f"{Colors.GREEN}✓ ALL SYSTEMS GO{Colors.RESET}"

        # Build output - responsive header
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        if is_mobile():
            # Compact header for mobile
            output = [
                f"\n{Colors.BOLD}{Colors.PURPLE}━━━ THANOS ━━━{Colors.RESET}",
                f"{status_text}  {Colors.DIM}{now}{Colors.RESET}",
            ]
        else:
            output = [
                f"\n{Colors.BOLD}{Colors.PURPLE}╔{'═' * 48}╗{Colors.RESET}",
                f"{Colors.BOLD}{Colors.PURPLE}║{Colors.RESET}  {Colors.BOLD}THANOS STATUS{Colors.RESET}  {status_text}  {Colors.DIM}{now}{Colors.RESET}",
                f"{Colors.BOLD}{Colors.PURPLE}╚{'═' * 48}╝{Colors.RESET}",
            ]

        for section in sections:
            output.append(self._format_header(section.title))
            output.append(section.content)

        # Responsive footer
        footer_width = 35 if is_mobile() else 50
        output.append(f"\n{Colors.DIM}{'─' * footer_width}{Colors.RESET}\n")

        return '\n'.join(output)


def main():
    """Run status command standalone."""
    import argparse

    parser = argparse.ArgumentParser(description='Thanos Status')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--section', type=str, help='Show only specific section')
    args = parser.parse_args()

    status = ThanosStatus()

    if args.json:
        sections = {
            'state': status.get_state_summary(),
            'health': status.get_health_summary(),
            'alerts': status.get_alerts_summary(),
            'circuits': status.get_circuit_breaker_summary(),
            'daemon': status.get_daemon_summary(),
            'brain_dump': status.get_brain_dump_summary(),
        }
        output = {
            name: {'title': s.title, 'status': s.status}
            for name, s in sections.items()
        }
        print(json.dumps(output, indent=2))
    elif args.section:
        section_map = {
            'state': status.get_state_summary,
            'health': status.get_health_summary,
            'alerts': status.get_alerts_summary,
            'circuits': status.get_circuit_breaker_summary,
            'daemon': status.get_daemon_summary,
            'brain_dump': status.get_brain_dump_summary,
        }
        if args.section in section_map:
            section = section_map[args.section]()
            print(status._format_header(section.title))
            print(section.content)
        else:
            print(f"Unknown section: {args.section}")
            print(f"Available: {', '.join(section_map.keys())}")
    else:
        print(status.get_full_status())


if __name__ == '__main__':
    main()
