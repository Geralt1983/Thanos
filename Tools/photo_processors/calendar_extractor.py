#!/usr/bin/env python3
"""
Calendar Photo Extractor.

Uses Claude Vision to OCR calendar photos and extract events with dates/times.
Returns structured event data ready for Google Calendar.
"""

import os
import json
import base64
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger('calendar_extractor')


@dataclass
class ExtractedEvent:
    """An event extracted from a calendar photo."""
    title: str
    date: str  # ISO format YYYY-MM-DD
    start_time: Optional[str] = None  # HH:MM format
    end_time: Optional[str] = None  # HH:MM format
    location: Optional[str] = None
    description: Optional[str] = None
    all_day: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_gcal_format(self, timezone: str = "America/New_York") -> Dict[str, Any]:
        """Convert to Google Calendar event format."""
        event = {
            "summary": self.title,
            "description": self.description or "",
            "location": self.location or "",
        }

        if self.all_day or not self.start_time:
            # All-day event
            event["start"] = {"date": self.date}
            event["end"] = {"date": self.date}
        else:
            # Timed event
            start_dt = f"{self.date}T{self.start_time}:00"
            end_time = self.end_time or self._default_end_time()
            end_dt = f"{self.date}T{end_time}:00"

            event["start"] = {"dateTime": start_dt, "timeZone": timezone}
            event["end"] = {"dateTime": end_dt, "timeZone": timezone}

        return event

    def _default_end_time(self) -> str:
        """Default to 1 hour after start."""
        if self.start_time:
            hour = int(self.start_time.split(":")[0])
            minute = self.start_time.split(":")[1] if ":" in self.start_time else "00"
            end_hour = (hour + 1) % 24
            return f"{end_hour:02d}:{minute}"
        return "12:00"


@dataclass
class CalendarExtractionResult:
    """Result of calendar photo extraction."""
    success: bool
    events: List[ExtractedEvent]
    raw_text: Optional[str] = None
    calendar_type: Optional[str] = None  # monthly, weekly, daily, event_flyer
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "events": [e.to_dict() for e in self.events],
            "raw_text": self.raw_text,
            "calendar_type": self.calendar_type,
            "error": self.error
        }


EXTRACTION_PROMPT = '''Analyze this calendar image and extract all events/appointments.

For each event found, extract:
- title: Event name/description
- date: Date in YYYY-MM-DD format (use the current year 2026 if not specified)
- start_time: Start time in HH:MM 24-hour format (if shown)
- end_time: End time in HH:MM 24-hour format (if shown)
- location: Location if mentioned
- all_day: true if it's an all-day event

Also identify:
- calendar_type: "monthly", "weekly", "daily", or "event_flyer"
- raw_text: Brief summary of what text you can see

Return JSON only:
```json
{
  "calendar_type": "monthly|weekly|daily|event_flyer",
  "raw_text": "Brief text summary",
  "events": [
    {
      "title": "Event name",
      "date": "2026-01-25",
      "start_time": "14:00",
      "end_time": "15:00",
      "location": "Room 101",
      "all_day": false
    }
  ]
}
```

If no events are found, return empty events array.
If the image is not a calendar, return {"error": "Not a calendar image", "events": []}.

Today's date is: {today}
'''


class CalendarExtractor:
    """
    Extract calendar events from photos using Claude Vision.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        """
        Initialize the extractor.

        Args:
            api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
            model: Claude model to use (must support vision).
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        self._client = None

        if not self.api_key:
            logger.warning("No ANTHROPIC_API_KEY found - extraction will fail")

    @property
    def client(self):
        """Lazy-load the Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed")
        return self._client

    async def extract_from_file(self, image_path: str) -> CalendarExtractionResult:
        """
        Extract calendar events from an image file.

        Args:
            image_path: Path to the image file.

        Returns:
            CalendarExtractionResult with extracted events.
        """
        path = Path(image_path)
        if not path.exists():
            return CalendarExtractionResult(
                success=False,
                events=[],
                error=f"File not found: {image_path}"
            )

        # Read and encode image
        with open(path, 'rb') as f:
            image_data = base64.standard_b64encode(f.read()).decode('utf-8')

        # Determine media type
        suffix = path.suffix.lower()
        media_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        media_type = media_types.get(suffix, 'image/jpeg')

        return await self._extract(image_data, media_type)

    async def extract_from_base64(self, image_data: str, media_type: str = "image/jpeg") -> CalendarExtractionResult:
        """
        Extract calendar events from base64-encoded image.

        Args:
            image_data: Base64-encoded image data.
            media_type: MIME type of the image.

        Returns:
            CalendarExtractionResult with extracted events.
        """
        return await self._extract(image_data, media_type)

    async def _extract(self, image_data: str, media_type: str) -> CalendarExtractionResult:
        """
        Internal extraction method.
        """
        try:
            response = await self._call_claude_vision(image_data, media_type)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return CalendarExtractionResult(
                success=False,
                events=[],
                error=str(e)
            )

    async def _call_claude_vision(self, image_data: str, media_type: str) -> str:
        """
        Call Claude Vision API.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        prompt = EXTRACTION_PROMPT.format(today=today)

        def sync_call():
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            )
            return response.content[0].text

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_call)

    def _parse_response(self, response: str) -> CalendarExtractionResult:
        """
        Parse Claude's response into structured data.
        """
        response = response.strip()

        # Handle markdown code blocks
        if '```' in response:
            lines = response.split('\n')
            json_lines = []
            in_block = False
            for line in lines:
                if line.startswith('```'):
                    in_block = not in_block
                    continue
                if in_block:
                    json_lines.append(line)
            response = '\n'.join(json_lines)

        try:
            data = json.loads(response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return CalendarExtractionResult(
                success=False,
                events=[],
                error=f"Failed to parse response: {e}"
            )

        # Check for error response
        if data.get('error'):
            return CalendarExtractionResult(
                success=False,
                events=[],
                error=data['error']
            )

        # Parse events
        events = []
        for event_data in data.get('events', []):
            try:
                event = ExtractedEvent(
                    title=event_data.get('title', 'Untitled'),
                    date=event_data.get('date', datetime.now().strftime('%Y-%m-%d')),
                    start_time=event_data.get('start_time'),
                    end_time=event_data.get('end_time'),
                    location=event_data.get('location'),
                    description=event_data.get('description'),
                    all_day=event_data.get('all_day', False)
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}")
                continue

        return CalendarExtractionResult(
            success=True,
            events=events,
            raw_text=data.get('raw_text'),
            calendar_type=data.get('calendar_type')
        )


# Convenience function
async def extract_calendar_events(image_path: str) -> CalendarExtractionResult:
    """
    Extract calendar events from an image file.

    Args:
        image_path: Path to the calendar image.

    Returns:
        CalendarExtractionResult with extracted events.
    """
    extractor = CalendarExtractor()
    return await extractor.extract_from_file(image_path)
