# Pocket Recorder - Voice Recording MCP Integration

Query your Pocket AI voice recordings directly from OpenClaw.

## Overview

Pocket AI is a voice recorder app that transcribes and extracts action items. This skill connects to Pocket's MCP server to search transcripts, fetch recordings, and manage action items.

## API Key

Set in `.env`:
```bash
POCKET_API_KEY=pk_f4451a02092e7368e4c9164e7082f42b534538e48fabd68adf8a197625fe2b70
```

## Available Tools

### 1. Search Recordings
**Use when:** User asks about past conversations, "what did I talk about", "find recording about X"

```bash
node scripts/search_recordings.js "product launch discussion"
```

Optional filters:
- `--after 2026-01-01` - recordings after date
- `--before 2026-02-01` - recordings before date
- `--tags meeting,work` - filter by tags

### 2. Get Recording Transcript
**Use when:** User wants full transcript of a specific recording

```bash
node scripts/get_recording.js <recording_id>
```

Returns full transcript with signed audio URL.

### 3. Search Action Items
**Use when:** User asks about todos, tasks, reminders from recordings

```bash
node scripts/search_action_items.js --status TODO --priority HIGH
```

Filters:
- `--status TODO|IN_PROGRESS|COMPLETED|CANCELLED`
- `--priority CRITICAL|HIGH|MEDIUM|LOW`
- `--category TASK|MEETING|REMINDER`
- `--due-before 2026-02-15`
- `--due-after 2026-02-01`

### 4. Recent Recordings
**Use when:** "Show my recent recordings", "what did I record today"

```bash
node scripts/recent_recordings.js --days 7
```

## Examples

**"What did I talk about regarding the budget?"**
```bash
node scripts/search_recordings.js "budget"
```

**"Show recordings from this week"**
```bash
node scripts/recent_recordings.js --days 7
```

**"Find all high-priority action items"**
```bash
node scripts/search_action_items.js --priority HIGH --status TODO
```

**"Get transcript from recording abc123"**
```bash
node scripts/get_recording.js abc123
```

## MCP Endpoint

- URL: `https://public.heypocketai.com/mcp`
- Auth: `Authorization: Bearer ${POCKET_API_KEY}`
- Protocol: MCP over HTTP (SSE)

## Notes

- Recordings are searchable immediately after creation
- Audio URLs are signed and expire after 1 hour
- Action items are automatically extracted from transcripts
- Tags can be added in the Pocket app

## References

- Pocket MCP Docs: https://docs.heypocketai.com/docs/mcp
- Pocket Settings: https://app.heypocketai.com/settings/developer
