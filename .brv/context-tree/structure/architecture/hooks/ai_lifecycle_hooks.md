## Relations
@structure/infrastructure/web_automation/google_automation_constraints.md

## Raw Concept
**Task:**
Automate therapy session scheduling for Jeff Willis

**Changes:**
- Automated therapy session extraction from Gmail to Family calendar

**Flow:**
Gmail Scan -> Detect "Jeff Willis" therapy session -> Extract time/date -> Proactively create 1hr event in Family calendar

**Timestamp:** 2026-02-02

## Narrative
### Structure
- Input: Gmail scan
- Logic: Identify 'Jeff Willis' + scheduled time
- Output: Google Calendar entry (Family calendar)

### Dependencies
Requires read access to Gmail and write access to Google Calendar (Family calendar).

### Features
- Proactive scheduling: Events are added automatically without user confirmation if time/date are clear.
- Target: Therapy sessions with 'Jeff Willis'.
- Calendar: 'Family' calendar.
- Duration: Default to 1-hour blocks.
