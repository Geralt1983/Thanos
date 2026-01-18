"""
Calendar Service - Calendar and external service integration

Extracted from ThanosOrchestrator for single-responsibility.
Handles calendar and WorkOS adapter integration with caching.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any

from Tools.error_logger import log_error


class CalendarService:
    """Service for calendar and WorkOS integration.

    Usage:
        service = CalendarService()
        context = await service.get_calendar_context()
        conflicts = await service.check_time_conflict(start, end)
    """

    # Cache TTL in seconds
    CACHE_TTL = 300  # 5 minutes

    def __init__(self):
        """Initialize calendar service."""
        # Calendar adapter
        self._calendar_adapter = None
        self._calendar_context_cache: Optional[Dict[str, Any]] = None
        self._calendar_cache_time: Optional[datetime] = None

        # WorkOS adapter
        self._workos_adapter = None
        self._workos_context_cache: Optional[Dict[str, Any]] = None
        self._workos_cache_time: Optional[datetime] = None

    def _get_calendar_adapter(self) -> Optional[Any]:
        """Lazy load the calendar adapter.

        Returns:
            GoogleCalendarAdapter or None if unavailable
        """
        if self._calendar_adapter is None:
            try:
                from Tools.adapters import GoogleCalendarAdapter, GOOGLE_CALENDAR_AVAILABLE

                if not GOOGLE_CALENDAR_AVAILABLE:
                    return None

                self._calendar_adapter = GoogleCalendarAdapter()

                # Check if authenticated
                if not self._calendar_adapter.is_authenticated():
                    return None

            except Exception as e:
                log_error("calendar_service", e, "Failed to initialize calendar adapter")
                return None

        return self._calendar_adapter

    def _get_workos_adapter(self) -> Optional[Any]:
        """Lazy load the WorkOS adapter.

        Returns:
            WorkOSAdapter or None if unavailable
        """
        if self._workos_adapter is None:
            try:
                from Tools.adapters.workos import WorkOSAdapter

                self._workos_adapter = WorkOSAdapter()
            except Exception as e:
                log_error("calendar_service", e, "Failed to initialize WorkOS adapter")
                return None

        return self._workos_adapter

    def _is_cache_valid(self, cache_time: Optional[datetime]) -> bool:
        """Check if a cache is still valid.

        Args:
            cache_time: When the cache was last updated

        Returns:
            True if cache is valid, False otherwise
        """
        if cache_time is None:
            return False
        return (datetime.now() - cache_time).seconds < self.CACHE_TTL

    async def get_calendar_context(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get calendar context with caching.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with calendar context including:
            - events: List of today's events
            - summary: Human-readable calendar summary
            - next_event: Details of next upcoming event
            - free_until: Next busy period
            - event_count: Number of events
        """
        # Check cache
        if not force_refresh and self._is_cache_valid(self._calendar_cache_time):
            return self._calendar_context_cache

        adapter = self._get_calendar_adapter()
        if adapter is None:
            return None

        try:
            # Fetch today's events
            result = await adapter.call_tool("get_today_events", {})

            if not result.success:
                return None

            events = result.data.get("events", [])

            # Generate summary
            summary_result = await adapter.call_tool(
                "generate_calendar_summary",
                {"date": datetime.now().strftime("%Y-%m-%d")},
            )

            summary = (
                summary_result.data.get("summary", "")
                if summary_result.success
                else ""
            )

            # Find next event
            now = datetime.now()
            next_event = None
            for event in events:
                event_start_str = event.get("start", {}).get("dateTime")
                if event_start_str:
                    try:
                        event_start = datetime.fromisoformat(
                            event_start_str.replace("Z", "+00:00")
                        )
                        if event_start.tzinfo is not None:
                            event_start = event_start.replace(tzinfo=None)
                        if event_start > now:
                            next_event = event
                            break
                    except (ValueError, AttributeError):
                        continue

            # Calculate free until
            free_until = None
            if next_event:
                event_start_str = next_event.get("start", {}).get("dateTime")
                if event_start_str:
                    try:
                        free_until = datetime.fromisoformat(
                            event_start_str.replace("Z", "+00:00")
                        )
                        if free_until.tzinfo is not None:
                            free_until = free_until.replace(tzinfo=None)
                    except (ValueError, AttributeError):
                        pass

            context = {
                "events": events,
                "summary": summary,
                "next_event": next_event,
                "free_until": free_until,
                "event_count": len(events),
            }

            # Cache result
            self._calendar_context_cache = context
            self._calendar_cache_time = datetime.now()

            return context

        except Exception as e:
            log_error("calendar_service", e, "Failed to fetch calendar context")
            return None

    def get_calendar_context_sync(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for getting calendar context.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with calendar context or None if unavailable
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._calendar_context_cache
            else:
                return asyncio.run(self.get_calendar_context(force_refresh))
        except RuntimeError:
            return asyncio.run(self.get_calendar_context(force_refresh))
        except Exception as e:
            log_error("calendar_service", e, "Failed to get calendar context")
            return None

    async def check_time_conflict(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Check if a time slot conflicts with calendar events.

        Args:
            start_time: Proposed start time
            end_time: Proposed end time

        Returns:
            Dictionary with:
            - has_conflict: Boolean
            - conflicts: List of conflicting events
            - message: Human-readable conflict description
        """
        adapter = self._get_calendar_adapter()
        if adapter is None:
            return {
                "has_conflict": False,
                "conflicts": [],
                "message": "Calendar not available",
            }

        try:
            result = await adapter.call_tool(
                "check_conflicts",
                {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
            )

            if not result.success:
                return {
                    "has_conflict": False,
                    "conflicts": [],
                    "message": "Unable to check conflicts",
                }

            return result.data

        except Exception as e:
            log_error("calendar_service", e, "Failed to check time conflict")
            return {
                "has_conflict": False,
                "conflicts": [],
                "message": f"Error checking conflicts: {str(e)}",
            }

    def check_time_conflict_sync(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """Synchronous wrapper for checking time conflicts.

        Args:
            start_time: Proposed start time
            end_time: Proposed end time

        Returns:
            Dictionary with conflict information
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Use cached context for conflict check
                context = self._calendar_context_cache
                if context is None:
                    return {
                        "has_conflict": False,
                        "conflicts": [],
                        "message": "Calendar not available",
                    }

                conflicts = []
                for event in context.get("events", []):
                    event_start_str = event.get("start", {}).get("dateTime")
                    event_end_str = event.get("end", {}).get("dateTime")
                    if event_start_str and event_end_str:
                        try:
                            event_start = datetime.fromisoformat(
                                event_start_str.replace("Z", "+00:00")
                            )
                            event_end = datetime.fromisoformat(
                                event_end_str.replace("Z", "+00:00")
                            )
                            if event_start.tzinfo is not None:
                                event_start = event_start.replace(tzinfo=None)
                            if event_end.tzinfo is not None:
                                event_end = event_end.replace(tzinfo=None)

                            # Check overlap
                            if start_time < event_end and end_time > event_start:
                                conflicts.append(event)
                        except (ValueError, AttributeError):
                            continue

                return {
                    "has_conflict": len(conflicts) > 0,
                    "conflicts": conflicts,
                    "message": f"Found {len(conflicts)} conflict(s)"
                    if conflicts
                    else "No conflicts",
                }
            else:
                return asyncio.run(self.check_time_conflict(start_time, end_time))
        except RuntimeError:
            return asyncio.run(self.check_time_conflict(start_time, end_time))
        except Exception as e:
            log_error("calendar_service", e, "Failed to check time conflict")
            return {
                "has_conflict": False,
                "conflicts": [],
                "message": f"Error: {str(e)}",
            }

    async def get_workos_context(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Get WorkOS context with caching.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with WorkOS context or None if unavailable
        """
        if not force_refresh and self._is_cache_valid(self._workos_cache_time):
            return self._workos_context_cache

        adapter = self._get_workos_adapter()
        if adapter is None:
            return None

        try:
            result = await adapter.call_tool("daily_summary", {})
            if not result.success:
                return None

            context = result.data
            self._workos_context_cache = context
            self._workos_cache_time = datetime.now()
            return context
        except Exception as e:
            log_error("calendar_service", e, "Failed to fetch WorkOS context")
            return None

    def get_workos_context_sync(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for getting WorkOS context.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with WorkOS context or None if unavailable
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return self._workos_context_cache
            else:
                return asyncio.run(self.get_workos_context(force_refresh))
        except RuntimeError:
            return asyncio.run(self.get_workos_context(force_refresh))
        except Exception as e:
            log_error("calendar_service", e, "Failed to get WorkOS context")
            return None

    def clear_cache(self) -> None:
        """Clear all cached context."""
        self._calendar_context_cache = None
        self._calendar_cache_time = None
        self._workos_context_cache = None
        self._workos_cache_time = None
