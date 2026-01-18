#!/usr/bin/env python3
"""
Calendar Alert Checker for Thanos.

Monitors Google Calendar for meeting conflicts, preparation needs, and scheduling issues.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .base import AlertChecker, Alert

import sys
sys.path.insert(0, str(__file__).rsplit('/Tools', 1)[0])

from Tools.journal import EventType


class CalendarChecker(AlertChecker):
    """Check calendar for scheduling alerts."""

    source = "calendar"
    check_interval = 600  # 10 minutes (more frequent for meetings)

    # Meeting types that need prep time
    PREP_REQUIRED_KEYWORDS = [
        'client', 'presentation', 'demo', 'review', 'interview',
        'stakeholder', 'exec', 'leadership', 'board', 'kickoff'
    ]

    # Buffer time preferences
    MIN_BUFFER_BETWEEN_MEETINGS = 15  # minutes
    PREP_TIME_FOR_IMPORTANT_MEETINGS = 30  # minutes

    def __init__(self, calendar_adapter=None):
        """
        Initialize Calendar checker.

        Args:
            calendar_adapter: Optional GoogleCalendarAdapter. If None, uses default.
        """
        super().__init__()
        self.calendar_adapter = calendar_adapter

    async def check(self) -> List[Alert]:
        """
        Run calendar checks and return alerts.

        Checks:
        - Upcoming meetings (15, 30 min reminders)
        - Back-to-back meetings without breaks
        - Important meetings needing prep time
        - Meeting conflicts
        - Day overload (too many hours of meetings)
        - Early morning meetings (sleep impact)
        """
        alerts = []

        try:
            # Get today's events
            events = await self._get_today_events()
            if events:
                alerts.extend(self._check_upcoming_meetings(events))
                alerts.extend(self._check_back_to_back(events))
                alerts.extend(self._check_day_load(events))

            # Get tomorrow's events for prep alerts
            tomorrow_events = await self._get_tomorrow_events()
            if tomorrow_events:
                alerts.extend(self._check_tomorrow_prep(tomorrow_events))

            # Check for conflicts in next 7 days
            week_events = await self._get_week_events()
            if week_events:
                alerts.extend(self._check_conflicts(week_events))

        except Exception as e:
            alerts.append(Alert(
                type=EventType.SYNC_FAILED,
                severity="warning",
                title=f"Calendar check error: {str(e)[:50]}",
                data={'error': str(e), 'checker': self.source}
            ))

        return alerts

    async def _get_today_events(self) -> Optional[List[Dict[str, Any]]]:
        """Get today's calendar events."""
        # Real implementation would use calendar adapter
        return None

    async def _get_tomorrow_events(self) -> Optional[List[Dict[str, Any]]]:
        """Get tomorrow's calendar events."""
        return None

    async def _get_week_events(self) -> Optional[List[Dict[str, Any]]]:
        """Get next 7 days of calendar events."""
        return None

    def _check_upcoming_meetings(self, events: List[Dict[str, Any]]) -> List[Alert]:
        """Check for meetings starting soon."""
        alerts = []
        now = datetime.now()

        for event in events:
            start_time = self._parse_event_time(event.get('start'))
            if not start_time:
                continue

            minutes_until = (start_time - now).total_seconds() / 60

            # 15-minute warning
            if 10 <= minutes_until <= 15:
                title = event.get('summary', 'Meeting')
                alerts.append(Alert(
                    type=EventType.CALENDAR_REMINDER,
                    severity="info",
                    title=f"📅 {title} in {int(minutes_until)} min",
                    data={
                        'event_id': event.get('id'),
                        'event_title': title,
                        'start_time': start_time.isoformat(),
                        'minutes_until': int(minutes_until),
                        'location': event.get('location'),
                        'meet_link': self._extract_meet_link(event)
                    },
                    dedup_key=f"calendar:reminder:15:{event.get('id')}"
                ))

            # 5-minute warning (more urgent)
            elif 3 <= minutes_until <= 5:
                title = event.get('summary', 'Meeting')
                meet_link = self._extract_meet_link(event)
                alerts.append(Alert(
                    type=EventType.CALENDAR_REMINDER,
                    severity="warning",
                    title=f"⚡ {title} starting NOW",
                    data={
                        'event_id': event.get('id'),
                        'event_title': title,
                        'start_time': start_time.isoformat(),
                        'minutes_until': int(minutes_until),
                        'meet_link': meet_link
                    },
                    dedup_key=f"calendar:reminder:5:{event.get('id')}"
                ))

        return alerts

    def _check_back_to_back(self, events: List[Dict[str, Any]]) -> List[Alert]:
        """Check for back-to-back meetings without breaks."""
        alerts = []

        # Sort by start time
        sorted_events = sorted(
            events,
            key=lambda e: self._parse_event_time(e.get('start')) or datetime.max
        )

        for i in range(len(sorted_events) - 1):
            current = sorted_events[i]
            next_event = sorted_events[i + 1]

            current_end = self._parse_event_time(current.get('end'))
            next_start = self._parse_event_time(next_event.get('start'))

            if not current_end or not next_start:
                continue

            gap_minutes = (next_start - current_end).total_seconds() / 60

            # Less than minimum buffer
            if 0 <= gap_minutes < self.MIN_BUFFER_BETWEEN_MEETINGS:
                alerts.append(Alert(
                    type=EventType.CALENDAR_CONFLICT,
                    severity="info",
                    title=f"Back-to-back: {current.get('summary', 'Meeting')} → {next_event.get('summary', 'Meeting')}",
                    data={
                        'first_event': current.get('summary'),
                        'second_event': next_event.get('summary'),
                        'gap_minutes': int(gap_minutes),
                        'end_time': current_end.isoformat(),
                        'next_start': next_start.isoformat()
                    },
                    dedup_key=f"calendar:back_to_back:{current.get('id')}:{next_event.get('id')}"
                ))

        return alerts

    def _check_day_load(self, events: List[Dict[str, Any]]) -> List[Alert]:
        """Check if day has too many meeting hours."""
        alerts = []

        total_minutes = 0
        for event in events:
            start = self._parse_event_time(event.get('start'))
            end = self._parse_event_time(event.get('end'))
            if start and end:
                duration = (end - start).total_seconds() / 60
                total_minutes += duration

        total_hours = total_minutes / 60

        # More than 6 hours of meetings
        if total_hours >= 6:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="warning",
                title=f"Heavy meeting day: {total_hours:.1f}h scheduled",
                data={
                    'total_meeting_hours': total_hours,
                    'meeting_count': len(events),
                    'recommendation': 'Block recovery time tomorrow'
                },
                dedup_key="calendar:heavy_day"
            ))

        # More than 4 meetings
        elif len(events) >= 5:
            alerts.append(Alert(
                type=EventType.HEALTH_ALERT,
                severity="info",
                title=f"Busy day: {len(events)} meetings ({total_hours:.1f}h)",
                data={
                    'meeting_count': len(events),
                    'total_hours': total_hours
                },
                dedup_key="calendar:many_meetings"
            ))

        return alerts

    def _check_tomorrow_prep(self, events: List[Dict[str, Any]]) -> List[Alert]:
        """Check for important meetings tomorrow that need prep time."""
        alerts = []
        now = datetime.now()

        for event in events:
            title = (event.get('summary') or '').lower()

            # Check if this needs prep time
            needs_prep = any(keyword in title for keyword in self.PREP_REQUIRED_KEYWORDS)

            if needs_prep:
                start_time = self._parse_event_time(event.get('start'))
                if start_time:
                    # Check if it's an early morning meeting
                    if start_time.hour < 10:
                        alerts.append(Alert(
                            type=EventType.CALENDAR_REMINDER,
                            severity="info",
                            title=f"Early meeting tomorrow: {event.get('summary')} at {start_time.strftime('%I:%M %p')}",
                            data={
                                'event_title': event.get('summary'),
                                'start_time': start_time.isoformat(),
                                'recommendation': 'Prepare tonight, wind down early'
                            },
                            dedup_key=f"calendar:prep:{event.get('id')}"
                        ))
                    else:
                        alerts.append(Alert(
                            type=EventType.CALENDAR_REMINDER,
                            severity="info",
                            title=f"Important meeting tomorrow: {event.get('summary')}",
                            data={
                                'event_title': event.get('summary'),
                                'start_time': start_time.isoformat(),
                                'prep_time_needed': self.PREP_TIME_FOR_IMPORTANT_MEETINGS
                            },
                            dedup_key=f"calendar:tomorrow_prep:{event.get('id')}"
                        ))

        return alerts

    def _check_conflicts(self, events: List[Dict[str, Any]]) -> List[Alert]:
        """Check for overlapping events in the coming week."""
        alerts = []

        # Group events by day
        events_by_day: Dict[str, List[Dict[str, Any]]] = {}
        for event in events:
            start = self._parse_event_time(event.get('start'))
            if start:
                day_key = start.strftime('%Y-%m-%d')
                if day_key not in events_by_day:
                    events_by_day[day_key] = []
                events_by_day[day_key].append(event)

        # Check each day for conflicts
        for day, day_events in events_by_day.items():
            sorted_events = sorted(
                day_events,
                key=lambda e: self._parse_event_time(e.get('start')) or datetime.max
            )

            for i in range(len(sorted_events)):
                for j in range(i + 1, len(sorted_events)):
                    event_a = sorted_events[i]
                    event_b = sorted_events[j]

                    if self._events_overlap(event_a, event_b):
                        alerts.append(Alert(
                            type=EventType.CALENDAR_CONFLICT,
                            severity="critical",
                            title=f"Conflict on {day}: {event_a.get('summary')} ↔ {event_b.get('summary')}",
                            data={
                                'event_a': event_a.get('summary'),
                                'event_b': event_b.get('summary'),
                                'event_a_time': event_a.get('start'),
                                'event_b_time': event_b.get('start'),
                                'day': day
                            },
                            dedup_key=f"calendar:conflict:{event_a.get('id')}:{event_b.get('id')}"
                        ))

        return alerts

    def _parse_event_time(self, time_data: Any) -> Optional[datetime]:
        """Parse event time from Google Calendar format."""
        if not time_data:
            return None

        if isinstance(time_data, str):
            try:
                return datetime.fromisoformat(time_data.replace('Z', '+00:00'))
            except ValueError:
                return None
        elif isinstance(time_data, dict):
            # Google Calendar format: {'dateTime': '...', 'timeZone': '...'}
            dt_str = time_data.get('dateTime') or time_data.get('date')
            if dt_str:
                try:
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                except ValueError:
                    return None
        return None

    def _events_overlap(self, event_a: Dict[str, Any], event_b: Dict[str, Any]) -> bool:
        """Check if two events overlap in time."""
        a_start = self._parse_event_time(event_a.get('start'))
        a_end = self._parse_event_time(event_a.get('end'))
        b_start = self._parse_event_time(event_b.get('start'))
        b_end = self._parse_event_time(event_b.get('end'))

        if not all([a_start, a_end, b_start, b_end]):
            return False

        # Events overlap if one starts before the other ends
        return a_start < b_end and b_start < a_end

    def _extract_meet_link(self, event: Dict[str, Any]) -> Optional[str]:
        """Extract Google Meet link from event."""
        # Check hangoutLink
        if 'hangoutLink' in event:
            return event['hangoutLink']

        # Check conferenceData
        conf_data = event.get('conferenceData', {})
        entry_points = conf_data.get('entryPoints', [])
        for entry in entry_points:
            if entry.get('entryPointType') == 'video':
                return entry.get('uri')

        # Check description for meet links
        description = event.get('description', '')
        if 'meet.google.com' in description:
            import re
            match = re.search(r'https://meet\.google\.com/[a-z-]+', description)
            if match:
                return match.group(0)

        return None
