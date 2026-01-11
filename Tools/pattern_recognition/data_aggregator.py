"""
Data aggregator for pattern recognition engine.

Collects historical data from multiple sources:
- Task completion records from State files
- Oura health/sleep data via OuraAdapter
- Commitments from Neo4j knowledge graph
- Session history from History/Sessions/

Provides unified interface for pattern analyzers to access historical data.
"""

import os
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo

from Tools.adapters.oura import OuraAdapter
from Tools.adapters.neo4j_adapter import Neo4jAdapter
from Tools.adapters.base import ToolResult


@dataclass
class TaskCompletionRecord:
    """Record of a completed task."""
    task_name: str
    completed_date: date
    domain: str = "work"
    points: Optional[int] = None
    project: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionRecord:
    """Record of a session from History/Sessions/."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    topics: List[str] = field(default_factory=list)
    commitments_made: int = 0
    decisions_made: int = 0
    state_changes: List[str] = field(default_factory=list)
    energy_level: Optional[int] = None
    mood: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class HealthMetrics:
    """Health metrics from Oura Ring."""
    date: date
    readiness_score: Optional[int] = None
    sleep_score: Optional[int] = None
    activity_score: Optional[int] = None
    total_sleep_duration: Optional[int] = None  # minutes
    deep_sleep_duration: Optional[int] = None  # minutes
    rem_sleep_duration: Optional[int] = None  # minutes
    awake_time: Optional[int] = None  # minutes
    hrv_average: Optional[float] = None
    resting_heart_rate: Optional[int] = None
    steps: Optional[int] = None


@dataclass
class CommitmentRecord:
    """Commitment record from Neo4j."""
    commitment_id: str
    content: str
    to_whom: str
    deadline: Optional[str] = None
    domain: str = "work"
    priority: int = 3
    status: str = "pending"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class AggregatedData:
    """All aggregated historical data."""
    task_completions: List[TaskCompletionRecord] = field(default_factory=list)
    health_metrics: List[HealthMetrics] = field(default_factory=list)
    commitments: List[CommitmentRecord] = field(default_factory=list)
    sessions: List[SessionRecord] = field(default_factory=list)
    date_range: Optional[tuple[date, date]] = None


class DataAggregator:
    """
    Aggregates historical data from multiple sources for pattern recognition.

    This class provides methods to collect and normalize data from:
    - State files (Today.md, Commitments.md, etc.)
    - Oura Ring health/sleep metrics
    - Neo4j knowledge graph commitments
    - Historical session records
    """

    def __init__(
        self,
        state_dir: str = "./State",
        sessions_dir: str = "./History/Sessions",
        oura_adapter: Optional[OuraAdapter] = None,
        neo4j_adapter: Optional[Neo4jAdapter] = None
    ):
        """
        Initialize the data aggregator.

        Args:
            state_dir: Path to State directory with task files
            sessions_dir: Path to History/Sessions directory
            oura_adapter: Optional OuraAdapter instance (will create if not provided)
            neo4j_adapter: Optional Neo4jAdapter instance (will create if not provided)
        """
        self.state_dir = Path(state_dir)
        self.sessions_dir = Path(sessions_dir)
        self._oura_adapter = oura_adapter
        self._neo4j_adapter = neo4j_adapter

    async def _get_oura_adapter(self) -> Optional[OuraAdapter]:
        """Get or create Oura adapter."""
        if self._oura_adapter is None:
            try:
                self._oura_adapter = OuraAdapter()
            except (ValueError, Exception):
                # Oura adapter not configured - return None
                return None
        return self._oura_adapter

    async def _get_neo4j_adapter(self) -> Optional[Neo4jAdapter]:
        """Get or create Neo4j adapter."""
        if self._neo4j_adapter is None:
            try:
                self._neo4j_adapter = Neo4jAdapter()
            except (ValueError, ImportError, Exception):
                # Neo4j adapter not configured - return None
                return None
        return self._neo4j_adapter

    async def aggregate_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days_back: int = 30
    ) -> AggregatedData:
        """
        Aggregate all historical data from configured sources.

        Args:
            start_date: Start date for data collection (defaults to days_back from today)
            end_date: End date for data collection (defaults to today)
            days_back: Number of days to look back if start_date not provided

        Returns:
            AggregatedData containing all collected historical data
        """
        # Calculate date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days_back)

        data = AggregatedData(date_range=(start_date, end_date))

        # Collect data from all sources
        data.task_completions = await self._aggregate_task_completions(start_date, end_date)
        data.health_metrics = await self._aggregate_health_metrics(start_date, end_date)
        data.commitments = await self._aggregate_commitments(start_date, end_date)
        data.sessions = await self._aggregate_sessions(start_date, end_date)

        return data

    async def _aggregate_task_completions(
        self, start_date: date, end_date: date
    ) -> List[TaskCompletionRecord]:
        """
        Extract task completion records from State files.

        Looks for completed tasks in:
        - State/Today.md
        - State/Commitments.md
        - Other State/*.md files

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of TaskCompletionRecord objects
        """
        completions = []

        try:
            # Parse Commitments.md for completed items
            commitments_file = self.state_dir / "Commitments.md"
            if commitments_file.exists():
                completions.extend(
                    self._parse_commitments_file(commitments_file, start_date, end_date)
                )

            # Parse Today.md for completed tasks
            today_file = self.state_dir / "Today.md"
            if today_file.exists():
                completions.extend(
                    self._parse_today_file(today_file, start_date, end_date)
                )

        except Exception as e:
            # Log error but don't fail - pattern recognition can work with partial data
            pass

        return completions

    def _parse_commitments_file(
        self, file_path: Path, start_date: date, end_date: date
    ) -> List[TaskCompletionRecord]:
        """Parse completed tasks from Commitments.md file."""
        completions = []

        try:
            content = file_path.read_text()

            # Look for completed items with [x] and completion dates
            # Pattern: - [x] Task description | To Whom | YYYY-MM-DD | Complete
            pattern = r'-\s*\[x\]\s*([^|]+)\|[^|]+\|\s*(\d{4}-\d{2}-\d{2})[^|]*\|\s*Complete'
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                task_name = match.group(1).strip()
                date_str = match.group(2)
                completion_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                if start_date <= completion_date <= end_date:
                    completions.append(TaskCompletionRecord(
                        task_name=task_name,
                        completed_date=completion_date,
                        domain="work",  # Default to work
                        metadata={"source": "Commitments.md"}
                    ))

            # Also look for "Recently Completed" section
            # Pattern: - [YYYY-MM-DD] Task description
            recent_pattern = r'-\s*\[(\d{4}-\d{2}-\d{2})\]\s*(.+)'
            recent_matches = re.finditer(recent_pattern, content, re.MULTILINE)

            for match in recent_matches:
                date_str = match.group(1)
                task_name = match.group(2).strip()
                completion_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                if start_date <= completion_date <= end_date:
                    completions.append(TaskCompletionRecord(
                        task_name=task_name,
                        completed_date=completion_date,
                        domain="work",
                        metadata={"source": "Commitments.md (Recently Completed)"}
                    ))

        except Exception:
            pass

        return completions

    def _parse_today_file(
        self, file_path: Path, start_date: date, end_date: date
    ) -> List[TaskCompletionRecord]:
        """Parse completed tasks from Today.md file."""
        completions = []

        try:
            content = file_path.read_text()

            # Extract date from title: # Today - YYYY-MM-DD
            date_match = re.search(r'#\s*Today\s*-\s*(\d{4}-\d{2}-\d{2})', content)
            if not date_match:
                return completions

            today_date = datetime.strptime(date_match.group(1), "%Y-%m-%d").date()

            if not (start_date <= today_date <= end_date):
                return completions

            # Look for completed tasks with [x]
            pattern = r'-\s*\[x\]\s*(.+?)(?:\[|$)'
            matches = re.finditer(pattern, content, re.MULTILINE)

            for match in matches:
                task_name = match.group(1).strip()

                # Extract points if present: [Npts]
                points = None
                points_match = re.search(r'\[(\d+)pts?\]', task_name)
                if points_match:
                    points = int(points_match.group(1))

                completions.append(TaskCompletionRecord(
                    task_name=task_name,
                    completed_date=today_date,
                    domain="work",
                    points=points,
                    metadata={"source": "Today.md"}
                ))

        except Exception:
            pass

        return completions

    async def _aggregate_health_metrics(
        self, start_date: date, end_date: date
    ) -> List[HealthMetrics]:
        """
        Retrieve health metrics from Oura Ring API.

        Args:
            start_date: Start date for data collection
            end_date: End date for data collection

        Returns:
            List of HealthMetrics objects
        """
        metrics = []
        oura = await self._get_oura_adapter()

        if oura is None:
            return metrics

        try:
            # Get daily summary from Oura (readiness, sleep, activity)
            result = await oura.call_tool(
                "get_daily_summary",
                {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                }
            )

            if not result.success:
                return metrics

            data = result.data

            # Create a map of date -> metrics
            metrics_by_date: Dict[str, HealthMetrics] = {}

            # Process readiness data
            if data.get("readiness"):
                for entry in data["readiness"]:
                    day = entry.get("day")
                    if day:
                        if day not in metrics_by_date:
                            metrics_by_date[day] = HealthMetrics(
                                date=datetime.strptime(day, "%Y-%m-%d").date()
                            )
                        metrics_by_date[day].readiness_score = entry.get("score")

                        # Extract HRV if available
                        contributors = entry.get("contributors", {})
                        if isinstance(contributors, dict):
                            hrv_balance = contributors.get("hrv_balance")
                            if hrv_balance:
                                # This is a score, not actual HRV - would need sleep data for actual HRV
                                pass

            # Process sleep data
            if data.get("sleep"):
                for entry in data["sleep"]:
                    day = entry.get("day")
                    if day:
                        if day not in metrics_by_date:
                            metrics_by_date[day] = HealthMetrics(
                                date=datetime.strptime(day, "%Y-%m-%d").date()
                            )
                        metrics_by_date[day].sleep_score = entry.get("score")

                        # Extract sleep durations if available
                        contributors = entry.get("contributors", {})
                        if isinstance(contributors, dict):
                            total_sleep = contributors.get("total_sleep")
                            if total_sleep:
                                # Convert to minutes (Oura returns seconds)
                                metrics_by_date[day].total_sleep_duration = total_sleep // 60

                            deep_sleep = contributors.get("deep_sleep")
                            if deep_sleep:
                                metrics_by_date[day].deep_sleep_duration = deep_sleep // 60

                            rem_sleep = contributors.get("rem_sleep")
                            if rem_sleep:
                                metrics_by_date[day].rem_sleep_duration = rem_sleep // 60

            # Process activity data
            if data.get("activity"):
                for entry in data["activity"]:
                    day = entry.get("day")
                    if day:
                        if day not in metrics_by_date:
                            metrics_by_date[day] = HealthMetrics(
                                date=datetime.strptime(day, "%Y-%m-%d").date()
                            )
                        metrics_by_date[day].activity_score = entry.get("score")
                        metrics_by_date[day].steps = entry.get("steps")

            metrics = list(metrics_by_date.values())

        except Exception:
            # Return empty list on error - pattern recognition can work with partial data
            pass

        return metrics

    async def _aggregate_commitments(
        self, start_date: date, end_date: date
    ) -> List[CommitmentRecord]:
        """
        Retrieve commitments from Neo4j knowledge graph.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of CommitmentRecord objects
        """
        commitments = []
        neo4j = await self._get_neo4j_adapter()

        if neo4j is None:
            return commitments

        try:
            # Get all commitments (we'll filter by date after)
            result = await neo4j.call_tool("get_commitments", {"limit": 100})

            if not result.success:
                return commitments

            data = result.data.get("commitments", [])

            for commitment in data:
                # Filter by date range if created_at is available
                created_at_str = commitment.get("created_at")
                if created_at_str:
                    try:
                        created_at = datetime.fromisoformat(created_at_str).date()
                        if not (start_date <= created_at <= end_date):
                            continue
                    except (ValueError, AttributeError):
                        pass

                commitments.append(CommitmentRecord(
                    commitment_id=commitment.get("id", ""),
                    content=commitment.get("content", ""),
                    to_whom=commitment.get("to_whom", ""),
                    deadline=commitment.get("deadline"),
                    domain=commitment.get("domain", "work"),
                    priority=commitment.get("priority", 3),
                    status=commitment.get("status", "pending"),
                    created_at=commitment.get("created_at"),
                    completed_at=commitment.get("completed_at")
                ))

        except Exception:
            # Return empty list on error
            pass

        return commitments

    async def _aggregate_sessions(
        self, start_date: date, end_date: date
    ) -> List[SessionRecord]:
        """
        Parse session records from History/Sessions/ directory.

        Args:
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of SessionRecord objects
        """
        sessions = []

        if not self.sessions_dir.exists():
            return sessions

        try:
            # Iterate through all .md files in sessions directory
            for session_file in self.sessions_dir.glob("*.md"):
                if session_file.name == "CLAUDE.md":
                    continue  # Skip the CLAUDE.md file

                session = self._parse_session_file(session_file)
                if session:
                    # Filter by date range
                    session_date = session.start_time.date()
                    if start_date <= session_date <= end_date:
                        sessions.append(session)

        except Exception:
            pass

        return sessions

    def _parse_session_file(self, file_path: Path) -> Optional[SessionRecord]:
        """Parse a single session file from History/Sessions/."""
        try:
            content = file_path.read_text()

            # Extract session ID from filename: YYYY-MM-DD-HHMM.md
            session_id = file_path.stem

            # Parse start time from title or filename
            start_time = None
            title_match = re.search(r'#\s*Session:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', content)
            if title_match:
                date_str = title_match.group(1)
                time_str = title_match.group(2)
                start_time = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            else:
                # Try to parse from filename
                try:
                    start_time = datetime.strptime(session_id, "%Y-%m-%d-%H%M")
                except ValueError:
                    # Fallback to just date
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', session_id)
                    if date_match:
                        start_time = datetime.strptime(date_match.group(1), "%Y-%m-%d")

            if not start_time:
                return None

            # Extract other metadata
            duration = None
            topics = []
            commitments_made = 0
            decisions_made = 0
            state_changes = []
            energy_level = None
            mood = None
            summary = None

            # Parse summary
            summary_match = re.search(r'##\s*Summary\s*\n(.+)', content)
            if summary_match:
                summary = summary_match.group(1).strip()

            # Parse topics
            topics_match = re.search(r'##\s*Topics Covered\s*\n((?:- .+\n?)+)', content)
            if topics_match:
                topics = [
                    line.strip('- ').strip()
                    for line in topics_match.group(1).split('\n')
                    if line.strip().startswith('-')
                ]

            # Parse state changes
            state_match = re.search(r'##\s*State Changes\s*\n-\s*Updated:\s*(.+)', content)
            if state_match:
                state_changes = [
                    s.strip() for s in state_match.group(1).split(',')
                ]

            # Parse energy level
            energy_match = re.search(r'Energy level:\s*(\d+)', content)
            if energy_match:
                energy_level = int(energy_match.group(1))

            # Parse mood
            mood_match = re.search(r'Mood:\s*(\w+)', content)
            if mood_match:
                mood = mood_match.group(1)

            return SessionRecord(
                session_id=session_id,
                start_time=start_time,
                end_time=None,  # End time not always recorded
                duration_minutes=duration,
                topics=topics,
                commitments_made=commitments_made,
                decisions_made=decisions_made,
                state_changes=state_changes,
                energy_level=energy_level,
                mood=mood,
                summary=summary
            )

        except Exception:
            return None

    async def close(self):
        """Close any open connections."""
        if self._oura_adapter:
            await self._oura_adapter.close()
        if self._neo4j_adapter:
            await self._neo4j_adapter.close()
