# Briefing Scheduler Guide

Complete guide to the automated briefing scheduler daemon.

## Overview

The BriefingScheduler daemon automatically runs briefings at configured times. It can run as:
- **Continuous daemon**: Checks schedule every minute, runs indefinitely
- **Cron mode**: Single check per invocation, suitable for cron scheduling

## Quick Start

### Run Once (Cron Mode)

```bash
python -m Tools.briefing_scheduler --mode once
```

This checks if any briefings are due right now and runs them. Ideal for cron jobs.

### Run as Daemon

```bash
python -m Tools.briefing_scheduler --mode daemon
```

This runs continuously, checking the schedule every minute (configurable).

### Custom Configuration

```bash
python -m Tools.briefing_scheduler \
  --mode daemon \
  --config /path/to/config.json \
  --state-dir /path/to/State \
  --templates-dir /path/to/Templates
```

## Configuration

The scheduler reads from `config/briefing_schedule.json`. See `config/README.md` for full configuration documentation.

### Key Configuration Options

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "days": {
        "monday": true,
        "tuesday": true,
        ...
      },
      "delivery_channels": ["cli", "file"]
    }
  },
  "scheduler": {
    "check_interval_minutes": 1,
    "prevent_duplicate_runs": true,
    "log_file": "logs/briefing_scheduler.log"
  }
}
```

## Features

### Duplicate Prevention

By default, the scheduler prevents running the same briefing multiple times per day:

- Tracks run state in `State/.briefing_runs.json`
- Automatically cleans up runs older than 7 days
- Can be disabled with `"prevent_duplicate_runs": false`

### Timezone Handling

The scheduler uses the system's local timezone. Briefing times are specified in 24-hour format (HH:MM).

### Day-of-Week Scheduling

Each briefing can be enabled/disabled per day:

```json
"days": {
  "monday": true,
  "tuesday": true,
  "wednesday": true,
  "thursday": true,
  "friday": true,
  "saturday": false,  // Skip weekends
  "sunday": false
}
```

### Graceful Shutdown

The daemon handles SIGTERM and SIGINT signals gracefully:

```bash
# Send shutdown signal
kill -TERM <pid>

# Or use Ctrl+C
```

The daemon will:
1. Stop checking for new briefings
2. Complete any in-progress briefing
3. Save state and exit cleanly

### Logging

All scheduler activity is logged to the configured log file (default: `logs/briefing_scheduler.log`):

- Startup/shutdown events
- Each briefing check
- Briefing executions
- Errors and warnings

Log format:
```
2026-01-11 07:00:01 - briefing_scheduler - INFO - Triggering morning briefing at 07:00
2026-01-11 07:00:02 - briefing_scheduler - INFO - Completed morning briefing successfully
```

### Error Handling

If a briefing fails:
- Error is logged with full stack trace
- Error notification sent (if enabled)
- Scheduler continues running
- Other briefings are not affected

## Delivery Channels

The scheduler supports multiple delivery channels configured per briefing:

### CLI Output

Prints briefing to stdout with formatting:

```json
"delivery_channels": ["cli"]
```

### File Output

Saves briefing to a file:

```json
"delivery": {
  "file": {
    "enabled": true,
    "output_dir": "History/DailyBriefings",
    "filename_pattern": "{date}_{type}_briefing.md"
  }
}
```

Creates files like: `2026-01-11_morning_briefing.md`

### Multiple Channels

Run multiple channels simultaneously:

```json
"delivery_channels": ["cli", "file", "notification"]
```

## Running as a Service

### Systemd (Linux)

Coming in subtask 2.3 - installation scripts for systemd.

### Launchd (macOS)

Coming in subtask 2.3 - installation scripts for launchd.

### Cron

Add to crontab to check every minute:

```cron
* * * * * cd /path/to/thanos && python -m Tools.briefing_scheduler --mode once >> logs/cron.log 2>&1
```

Or check less frequently:

```cron
# Check every 5 minutes
*/5 * * * * cd /path/to/thanos && python -m Tools.briefing_scheduler --mode once

# Check at specific times
0 7 * * * cd /path/to/thanos && python -m Tools.briefing_scheduler --mode once  # 7 AM
0 19 * * 1-5 cd /path/to/thanos && python -m Tools.briefing_scheduler --mode once  # 7 PM weekdays
```

## Manual Testing

### Check Configuration

```bash
python example_scheduler.py
```

This runs interactive examples showing:
- Configuration status
- Scheduled briefings
- Run state
- Manual triggering

### Test Single Briefing

```python
from Tools.briefing_scheduler import BriefingScheduler

scheduler = BriefingScheduler()

# Manually run a briefing (ignores schedule)
briefing_config = scheduler.config["briefings"]["morning"]
scheduler._run_briefing("morning", briefing_config)
```

### Check Run State

```python
from Tools.briefing_scheduler import BriefingScheduler

scheduler = BriefingScheduler()

# Check if briefings have run today
print(f"Morning run: {scheduler._has_run_today('morning')}")
print(f"Evening run: {scheduler._has_run_today('evening')}")

# View full run state
print(scheduler.run_state)
```

### Reset Run State

To allow a briefing to run again today:

```bash
# Remove run state file
rm State/.briefing_runs.json
```

Or edit the JSON file to remove specific entries.

## Architecture

### Check Flow

```
1. check_and_run() called (every check interval)
   ↓
2. For each configured briefing:
   ↓
3. _should_run_briefing() checks:
   - Is enabled?
   - Is today enabled?
   - Already run today?
   - Is it the scheduled time?
   ↓
4. If yes → _run_briefing():
   - Gather context from State files
   - Render briefing template
   - Deliver via configured channels
   - Mark as run
   ↓
5. Sleep until next check interval
```

### State Tracking

Run state is stored in `State/.briefing_runs.json`:

```json
{
  "2026-01-11_morning": {
    "timestamp": "2026-01-11T07:00:01",
    "type": "morning"
  },
  "2026-01-11_evening": {
    "timestamp": "2026-01-11T19:00:02",
    "type": "evening"
  }
}
```

Entries older than 7 days are automatically removed.

## Troubleshooting

### Briefing Not Running

Check:
1. Is the briefing enabled in config?
2. Is today's day enabled?
3. Is the time correct? (24-hour format)
4. Has it already run today? (check logs or run state)
5. Is the scheduler actually running? (check process list)

### Duplicate Runs

If briefings run multiple times:
1. Check if multiple scheduler instances are running
2. Verify `prevent_duplicate_runs` is enabled
3. Check file permissions on `State/.briefing_runs.json`

### Missing Output Files

If file delivery isn't working:
1. Check `delivery.file.enabled` is true
2. Verify `output_dir` exists and is writable
3. Check logs for file writing errors
4. Verify `filename_pattern` is valid

### Timezone Issues

If briefings run at wrong times:
1. Verify system timezone is correct: `date`
2. Times in config are in 24-hour local time
3. Check scheduler logs for actual trigger times

### High CPU Usage

If daemon uses too much CPU:
1. Check `check_interval_minutes` isn't too small
2. Review template complexity
3. Check for errors in logs (tight error loops)
4. Consider using cron mode instead

## Performance

### Resource Usage

In daemon mode with 1-minute check interval:
- CPU: < 0.1% (when idle)
- Memory: ~30-50 MB
- Disk: Minimal (logging only)

### Optimization Tips

1. **Use cron mode** for simple schedules (lower overhead)
2. **Increase check interval** if precise timing isn't critical
3. **Disable duplicate prevention** if running via cron (state tracking not needed)
4. **Limit delivery channels** to what you actually use
5. **Rotate logs** to prevent unbounded growth

## Security

### File Permissions

The scheduler requires:
- Read access to: `config/`, `State/`, `Templates/`
- Write access to: `State/`, `logs/`, `History/DailyBriefings/`

### Running as Non-Root

Always run the scheduler as a non-privileged user. It doesn't require root access.

### Configuration Validation

Config files are validated on startup. Invalid configs will prevent the scheduler from starting.

## Integration

### With Existing Commands

The scheduler uses the same `BriefingEngine` as the manual `daily.py` command, ensuring consistency.

### With Other Tools

Briefings can be triggered by:
- The scheduler daemon (automatic)
- Cron jobs (scheduled)
- Manual commands (ad-hoc)
- Other scripts (programmatic)

All use the same underlying engine and respect the same configuration.

## Advanced Usage

### Custom Briefing Types

Add new briefing types to config:

```json
"briefings": {
  "morning": { ... },
  "evening": { ... },
  "midday": {
    "enabled": true,
    "time": "12:00",
    "template": "briefing_midday.md",
    ...
  }
}
```

Create corresponding template: `Templates/briefing_midday.md`

### Programmatic Control

```python
from Tools.briefing_scheduler import BriefingScheduler

# Initialize
scheduler = BriefingScheduler()

# Run single check
scheduler.check_and_run()

# Run specific briefing (bypass schedule)
config = scheduler.config["briefings"]["morning"]
scheduler._run_briefing("morning", config)

# Check what would run now
from datetime import datetime
now = datetime.now()
for btype, bconfig in scheduler.config["briefings"].items():
    if scheduler._should_run_briefing(btype, bconfig, now):
        print(f"{btype} would run now")
```

### Monitoring

Monitor scheduler health:

```bash
# Check if process is running
ps aux | grep briefing_scheduler

# Monitor log file
tail -f logs/briefing_scheduler.log

# Check recent runs
cat State/.briefing_runs.json | jq .
```

## Next Steps

- **Subtask 2.3**: Installation scripts for cron and systemd
- **Subtask 2.4**: Manual trigger command (`commands/pa/briefing.py`)
- **Phase 4**: Additional delivery channels (notifications, email)

## Related Documentation

- [Configuration Guide](../config/README.md) - Full config options
- [Template Customization](../Templates/README.md) - Customize briefing templates
- [BriefingEngine API](../Tools/briefing_engine.py) - Core engine documentation
- [Integration Notes](./INTEGRATION_NOTES.md) - Integration with existing commands
