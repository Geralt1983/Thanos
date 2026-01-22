# Thanos Hooks Configuration

## Overview

Thanos uses Claude Code hooks to run background tasks during session lifecycle events. All hooks are configured to run **silently** - they execute their work without displaying output in the Claude Code interface.

## Hook Locations

| File | Scope |
|------|-------|
| `~/.claude/settings.json` | Global (all projects) |
| `.claude/settings.json` | Project-specific (Thanos) |
| `plugins/cache/thedotmack/claude-mem/9.0.0/hooks/hooks.json` | Claude-mem plugin |

## Active Hooks

### SessionStart

Runs once when a Claude Code session begins.

| Hook | Purpose |
|------|---------|
| `on-session-start.sh` | Injects morning context, checks Oura data |
| `thanos_orchestrator.py hook morning-brief` | Generates quick morning context |
| `thanos-start.sh` | Displays DESTINY header, runs daily-brief.ts |

### UserPromptSubmit

Runs on every user message.

| Hook | Purpose |
|------|---------|
| `time_tracker.py --context` | Tracks session time |
| `extract-commitments.sh` | Extracts commitments from conversation |
| `claude-mem new-hook.js` | Memory indexing |

### Stop

Runs when session ends.

| Hook | Purpose |
|------|---------|
| `on-session-end.sh` | Session cleanup |
| `track-token-usage.sh record` | Records token usage |
| `thanos_orchestrator.py hook session-end` | Logs session to History |
| `claude-mem summary-hook.js` | Generates session summary |

### PostToolUse (claude-mem only)

Runs after every tool call.

| Hook | Purpose |
|------|---------|
| `save-hook.js` | Saves observations to memory |

## Output Suppression

All hooks use `>/dev/null 2>&1` to suppress output:

```json
{
  "type": "command",
  "command": "script.sh >/dev/null 2>&1",
  "timeout": 5000
}
```

This ensures:
- Hooks run in background
- No "hook success" messages appear
- No error messages clutter the interface
- All functionality is preserved

## Troubleshooting

### Hooks not running?

1. Check file permissions: `chmod +x script.sh`
2. Verify paths are absolute
3. Check timeout isn't too short

### Need to debug a hook?

Temporarily remove `>/dev/null 2>&1` to see output:

```json
"command": "script.sh"  // Shows output for debugging
```

### Hooks running but no effect?

Check the hook's log file or run manually:

```bash
# Test time tracker
python3 ~/Projects/Thanos/Tools/time_tracker.py --context

# Test session start
~/Projects/Thanos/hooks/session-start/thanos-start.sh
```

## Configuration Reference

### Global (~/.claude/settings.json)

```json
{
  "hooks": {
    "SessionStart": [...],
    "Stop": [...],
    "UserPromptSubmit": [...]
  },
  "enabledPlugins": {
    "claude-mem@thedotmack": true
  }
}
```

### Project (.claude/settings.json)

```json
{
  "hooks": {
    "SessionStart": [...],
    "UserPromptSubmit": [...],
    "Stop": [...]
  },
  "statusLine": {
    "command": "hooks/statusline/thanos_status.sh",
    "refreshMs": 10000,
    "enabled": true
  }
}
```

## Adding New Hooks

1. Create the script in `hooks/` directory
2. Make it executable: `chmod +x script.sh`
3. Add to appropriate settings.json with output suppression
4. Test manually before relying on it

Example:

```json
{
  "type": "command",
  "command": "/path/to/new-hook.sh >/dev/null 2>&1",
  "timeout": 5000,
  "continueOnError": true
}
```
