# Briefing Schedule Configuration

This directory contains configuration files for the automated daily briefing system.

## Files

- **briefing_schedule.json** - Main configuration file for scheduling briefings
- **briefing_schedule.schema.json** - JSON Schema for validation and documentation
- **README.md** - This file

## Configuration Overview

The `briefing_schedule.json` file controls when and how your daily briefings are generated and delivered.

### Main Sections

#### 1. Briefings

Define your briefing types (morning, evening, or custom):

```json
"briefings": {
  "morning": {
    "enabled": true,
    "time": "07:00",
    "days": { ... },
    "template": "briefing_morning.md",
    "delivery_channels": ["cli", "file"]
  }
}
```

**Options:**
- `enabled` (boolean): Turn this briefing on/off
- `time` (string): Time in 24-hour format (HH:MM)
- `timezone` (string): "local" or specific timezone (e.g., "America/New_York")
- `days` (object): Day-of-week settings (true/false for each day)
- `template` (string): Template filename from Templates/ directory
- `delivery_channels` (array): How to deliver ("cli", "file", "notification")

**Example: Weekday-only morning briefing**
```json
"morning": {
  "enabled": true,
  "time": "07:00",
  "days": {
    "monday": true,
    "tuesday": true,
    "wednesday": true,
    "thursday": true,
    "friday": true,
    "saturday": false,
    "sunday": false
  }
}
```

#### 2. Delivery

Configure how briefings are delivered:

```json
"delivery": {
  "cli": {
    "enabled": true,
    "color": true
  },
  "file": {
    "enabled": true,
    "output_dir": "History/DailyBriefings",
    "filename_pattern": "{date}_{type}_briefing.md"
  },
  "notification": {
    "enabled": false,
    "summary_only": true
  }
}
```

**Delivery Channels:**

- **CLI**: Output to terminal/console
  - `color`: Use colored output (requires terminal support)

- **File**: Save to file
  - `output_dir`: Directory path (relative or absolute)
  - `filename_pattern`: Supports placeholders:
    - `{date}` → YYYY-MM-DD
    - `{type}` → morning/evening
    - `{timestamp}` → full ISO timestamp

- **Notification**: Desktop notifications (requires terminal-notifier/notify-send)
  - `summary_only`: Show top 3 priorities only (vs. full briefing)

#### 3. Content

Control what appears in your briefings:

```json
"content": {
  "max_priorities": 3,
  "include_quick_wins": true,
  "include_calendar": true,
  "include_energy_prompts": false,
  "weekend_mode": {
    "enabled": true,
    "exclude_work_tasks": true,
    "focus_on_personal": true
  }
}
```

**Options:**
- `max_priorities`: Number of top priorities to show (1-10)
- `include_quick_wins`: Show simple, quick tasks you can knock out
- `include_calendar`: Include calendar items (if available)
- `include_energy_prompts`: Prompt for health/energy state during briefing
- `weekend_mode`: Special behavior for Saturdays/Sundays
  - `exclude_work_tasks`: Hide work tasks on weekends (unless urgent)
  - `focus_on_personal`: Prioritize personal tasks on weekends

#### 4. Scheduler

Configure the scheduler daemon:

```json
"scheduler": {
  "check_interval_minutes": 1,
  "prevent_duplicate_runs": true,
  "log_file": "logs/briefing_scheduler.log",
  "error_notification": true
}
```

**Options:**
- `check_interval_minutes`: How often to check if briefing should run (1-60)
- `prevent_duplicate_runs`: Ensure briefing only runs once per day
- `log_file`: Path to log file for scheduler events
- `error_notification`: Send notification if briefing generation fails

#### 5. Advanced

Advanced settings for power users:

```json
"advanced": {
  "state_dir": "State",
  "templates_dir": "Templates",
  "use_llm_enhancement": false,
  "llm_model": "gpt-4o-mini",
  "pattern_learning_enabled": false
}
```

**Options:**
- `state_dir`: Location of State files (Commitments.md, etc.)
- `templates_dir`: Location of template files
- `use_llm_enhancement`: Use AI to enhance template-based briefings
- `llm_model`: Which AI model to use for enhancement
- `pattern_learning_enabled`: Learn from your patterns over time (Phase 6 feature)

## Common Configurations

### Example 1: Morning Only, Weekdays
```json
"briefings": {
  "morning": {
    "enabled": true,
    "time": "07:00",
    "days": {
      "monday": true, "tuesday": true, "wednesday": true,
      "thursday": true, "friday": true,
      "saturday": false, "sunday": false
    }
  },
  "evening": {
    "enabled": false
  }
}
```

### Example 2: Morning + Evening, All Days
```json
"briefings": {
  "morning": {
    "enabled": true,
    "time": "07:00",
    "days": { /* all true */ }
  },
  "evening": {
    "enabled": true,
    "time": "19:00",
    "days": { /* all true */ }
  }
}
```

### Example 3: Weekend vs Weekday Times
Create separate briefing types for different schedules:
```json
"briefings": {
  "morning_weekday": {
    "enabled": true,
    "time": "07:00",
    "days": {
      "monday": true, "tuesday": true, "wednesday": true,
      "thursday": true, "friday": true,
      "saturday": false, "sunday": false
    }
  },
  "morning_weekend": {
    "enabled": true,
    "time": "09:00",
    "days": {
      "monday": false, "tuesday": false, "wednesday": false,
      "thursday": false, "friday": false,
      "saturday": true, "sunday": true
    }
  }
}
```

### Example 4: Notification-Only
```json
"briefings": {
  "morning": {
    "enabled": true,
    "time": "07:00",
    "delivery_channels": ["notification"]
  }
},
"delivery": {
  "notification": {
    "enabled": true,
    "summary_only": true
  }
}
```

## Validation

The configuration is validated against `briefing_schedule.schema.json`. Common errors:

- **Invalid time format**: Use HH:MM (e.g., "07:00", not "7:00 AM")
- **Unknown delivery channel**: Must be one of: cli, file, notification, state_sync, email
- **Invalid day name**: Use lowercase full day names (monday, tuesday, etc.)

## Testing Your Configuration

Before enabling the scheduler, test your configuration:

```bash
# Test morning briefing generation
python -m commands.pa.briefing morning --config config/briefing_schedule.json --dry-run

# Test evening briefing generation
python -m commands.pa.briefing evening --config config/briefing_schedule.json --dry-run
```

## Disabling Briefings

To temporarily disable all briefings without losing your configuration:

**Option 1: Disable individual briefings**
```json
"morning": { "enabled": false }
```

**Option 2: Stop the scheduler**
```bash
# If using cron
crontab -e  # Comment out the briefing lines

# If using systemd
sudo systemctl stop briefing-scheduler
```

## Migration

When updating to a new version of the briefing system:

1. Check `version` field in the schema
2. Review changelog for breaking changes
3. Validate your config against new schema
4. Test with `--dry-run` before enabling

## Troubleshooting

**Briefing not running at scheduled time:**
- Check scheduler logs: `tail -f logs/briefing_scheduler.log`
- Verify enabled: `"enabled": true` in briefing config
- Verify day is enabled: Check `days` object
- Check scheduler is running: `ps aux | grep briefing_scheduler`

**Config validation errors:**
- Validate manually: `python -m Tools.validate_config config/briefing_schedule.json`
- Check JSON syntax: Use `jq . config/briefing_schedule.json`
- Review error messages for specific issues

**Missing briefing content:**
- Verify State files exist: `ls -la State/`
- Check `state_dir` in advanced settings
- Review templates: `ls -la Templates/`

## Support

For more information:
- **Templates**: See `Templates/README.md` for customizing briefing templates
- **Scheduler**: See `docs/briefing_scheduler.md` for scheduler setup
- **Architecture**: See `docs/briefing_architecture.md` for technical details
