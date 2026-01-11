# Briefing Scheduler

Automated daemon for running briefings at scheduled times.

## Quick Start

```bash
# Run as continuous daemon
python -m Tools.briefing_scheduler --mode daemon

# Run single check (for cron)
python -m Tools.briefing_scheduler --mode once

# Custom config
python -m Tools.briefing_scheduler --mode daemon --config path/to/config.json
```

## Features

- ✓ Continuous daemon mode or single-check cron mode
- ✓ Configurable check interval (default: 1 minute)
- ✓ Automatic duplicate prevention per day
- ✓ Day-of-week scheduling
- ✓ Multiple delivery channels (CLI, file, notification)
- ✓ Graceful shutdown on SIGTERM/SIGINT
- ✓ Comprehensive logging
- ✓ Timezone aware

## Architecture

```
BriefingScheduler
├── Config loading & validation
├── Run state tracking (duplicate prevention)
├── Schedule checking
│   ├── Check enabled
│   ├── Check day of week
│   ├── Check time match
│   └── Check not already run
├── Briefing execution
│   ├── Gather context (BriefingEngine)
│   ├── Render template
│   └── Deliver via channels
└── Logging & error handling
```

## Configuration

Reads from `config/briefing_schedule.json`:

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "days": { "monday": true, ... },
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

See `config/README.md` for full configuration options.

## Run State

Tracks executions in `State/.briefing_runs.json`:

```json
{
  "2026-01-11_morning": {
    "timestamp": "2026-01-11T07:00:01",
    "type": "morning"
  }
}
```

- Automatically cleans up entries older than 7 days
- Can be disabled with `prevent_duplicate_runs: false`

## Command Line Arguments

- `--mode`: `daemon` (continuous) or `once` (single check)
- `--config`: Path to config file (default: `config/briefing_schedule.json`)
- `--state-dir`: Path to State directory (default: `./State`)
- `--templates-dir`: Path to Templates directory (default: `./Templates`)

## Signal Handling

- `SIGTERM`: Graceful shutdown
- `SIGINT` (Ctrl+C): Graceful shutdown

The scheduler will:
1. Set `should_stop` flag
2. Complete current briefing
3. Save state
4. Exit cleanly

## Logging

All activity logged to configured log file:

```
2026-01-11 07:00:00 - briefing_scheduler - INFO - BriefingScheduler initialized
2026-01-11 07:00:01 - briefing_scheduler - INFO - Triggering morning briefing at 07:00
2026-01-11 07:00:02 - briefing_scheduler - INFO - Completed morning briefing successfully
```

## Examples

See `example_scheduler.py` for interactive examples:

```bash
python example_scheduler.py
```

## Testing

Run unit tests:

```bash
pytest tests/unit/test_briefing_scheduler.py -v
```

Tests cover:
- Initialization and config validation
- Duplicate prevention
- Time checking logic
- Day-of-week filtering
- Run state persistence
- File delivery
- Signal handling

## Integration

Uses `BriefingEngine` from `Tools/briefing_engine.py`:
- Same context gathering as manual commands
- Same template rendering
- Same State file structure
- Consistent output format

## Production Deployment

### Cron (All Platforms)

```cron
* * * * * cd /path/to/thanos && python -m Tools.briefing_scheduler --mode once
```

### Systemd (Linux)

Coming in subtask 2.3.

### Launchd (macOS)

Coming in subtask 2.3.

## Troubleshooting

**Briefing not running?**
- Check if enabled in config
- Verify day and time are correct
- Check if already run (view logs or run state)
- Ensure scheduler process is running

**Duplicate runs?**
- Multiple scheduler instances may be running
- Check `prevent_duplicate_runs` is enabled

**Wrong time?**
- Verify system timezone
- Times are in 24-hour local time

See `docs/SCHEDULER_GUIDE.md` for comprehensive troubleshooting.

## Documentation

- [Scheduler Guide](../docs/SCHEDULER_GUIDE.md) - Complete usage guide
- [Configuration Guide](../config/README.md) - Config options
- [Template Guide](../Templates/README.md) - Template customization
