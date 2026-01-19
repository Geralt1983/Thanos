# Thanos Statusline Integration

This document describes how the Thanos statusline is integrated with Claude Code.

## Overview

The Thanos statusline replaces the default Claude Flow statusline with Thanos-specific metrics, showing work progress, health data, and session information at a glance.

## Components

### 1. Python Generator (`hooks/statusline/thanos_statusline.py`)

The core statusline generator that collects data from various Thanos sources:

**Data Sources:**
- **WorkOS Database** - Work points, daily target, streak, active tasks
- **Oura Cache** - Readiness score from `State/OuraCache.json`
- **TimeState** - Interaction count from `State/TimeState.json`
- **Git** - Current branch name

**Output Format:**
```
Thanos | Opus 4.5 | main | 12/18pt + | 85r | 5d | 3 active | #42
```

**Components Explained:**
| Component | Example | Description |
|-----------|---------|-------------|
| Project | `Thanos` | Project identifier (always shown) |
| Model | `Opus 4.5` | Current Claude model |
| Branch | `main` | Git branch |
| Points | `12/18pt +` | Points earned/target with pace indicator |
| Readiness | `85r` | Oura readiness score |
| Streak | `5d` | Consecutive days meeting goal |
| Active | `3 active` | Number of active tasks |
| Interactions | `#42` | Today's interaction count |

**Pace Indicators:**
- `+` (green) - Ahead of pace
- `=` (yellow) - On track
- `-` (red) - Behind pace

### 2. Shell Wrapper (`hooks/statusline/thanos_status.sh`)

A bash script that:
1. Calls the Python generator
2. Provides fallback if Python fails
3. Handles stdin JSON context from Claude Code

### 3. Claude Code Configuration (`.claude/settings.json`)

The statusline is configured in the settings file:

```json
{
  "statusLine": {
    "type": "command",
    "command": "hooks/statusline/thanos_status.sh 2>/dev/null || echo \"Thanos\"",
    "refreshMs": 10000,
    "enabled": true
  }
}
```

**Configuration Options:**
- `refreshMs: 10000` - Refresh every 10 seconds (reduced from 5s to minimize overhead)
- `enabled: true` - Statusline is active

## Data Flow

```
Claude Code
    |
    v
hooks/statusline/thanos_status.sh
    |
    v
hooks/statusline/thanos_statusline.py
    |
    +---> State/thanos_unified.db (work metrics)
    |
    +---> State/OuraCache.json (readiness)
    |
    +---> State/TimeState.json (interactions)
    |
    +---> git (branch name)
    |
    v
Formatted statusline with ANSI colors
```

## Color Coding

The statusline uses ANSI color codes for visual feedback:

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Points/Pace | Ahead (+15%) | On track (+-15%) | Behind (-15%) |
| Readiness | >= 85 | 70-84 | < 70 |
| Streak | (always red/orange for fire effect) | | |

## Troubleshooting

### Statusline Not Showing

1. Check if hooks directory exists:
   ```bash
   ls -la hooks/statusline/
   ```

2. Test the statusline manually:
   ```bash
   echo '{}' | ./hooks/statusline/thanos_status.sh
   ```

3. Verify settings.json has correct path:
   ```bash
   jq '.statusLine' .claude/settings.json
   ```

### Missing Data

1. **No points/streak**: Check if `State/thanos_unified.db` exists and has `daily_metrics` table
2. **No readiness**: Verify Oura data is cached in `State/OuraCache.json`
3. **No interactions**: Check `State/TimeState.json` has `interaction_count_today`

### Performance Issues

If the statusline causes slowdown:
1. Increase `refreshMs` in settings.json (e.g., 30000 for 30 seconds)
2. Check database file sizes
3. Verify no lock contention on SQLite databases

## Customization

### Adding New Metrics

Edit `hooks/statusline/thanos_statusline.py` to add new data sources:

```python
def get_custom_metric() -> str:
    # Your implementation
    return "value"

def generate_statusline(context: dict = None) -> str:
    # ... existing code ...

    # Add your metric
    custom = get_custom_metric()
    if custom:
        parts.append(f"{Colors.CYAN}{custom}{Colors.RESET}")

    return " | ".join(parts)
```

### Changing Colors

Modify the `Colors` class in `thanos_statusline.py`:

```python
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    # Add or modify color codes
    CUSTOM = "\033[38;5;208m"  # Orange
```

### Adjusting Thresholds

Pace and readiness thresholds can be adjusted in the respective functions:
- `format_pace_indicator()` - Work pace thresholds
- `format_readiness()` - Oura readiness thresholds

## Integration with WorkOS MCP

The statusline reads from the same database that WorkOS MCP uses, ensuring consistency between:
- The statusline display
- The `/pa:daily` briefing
- Task completion tracking

## Files

| File | Purpose |
|------|---------|
| `hooks/statusline/thanos_statusline.py` | Main Python generator |
| `hooks/statusline/thanos_status.sh` | Shell wrapper for Claude Code |
| `.claude/settings.json` | Claude Code configuration |
| `docs/statusline_integration.md` | This documentation |
