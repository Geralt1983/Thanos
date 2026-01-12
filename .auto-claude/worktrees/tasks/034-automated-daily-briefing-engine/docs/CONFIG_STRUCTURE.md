# Briefing Schedule Configuration Structure

This document describes the configuration structure designed for scheduling automated daily briefings.

## Overview

The configuration system provides comprehensive control over when, how, and what briefings are generated and delivered. It supports multiple briefing types (morning, evening, custom), flexible scheduling, multiple delivery channels, and extensive customization.

## Configuration Files

### Primary Files

1. **config/briefing_schedule.json** - Main configuration file
   - Production-ready defaults
   - Morning briefing enabled by default
   - Evening briefing disabled by default
   - File and CLI delivery enabled

2. **config/briefing_schedule.schema.json** - JSON Schema definition
   - Complete schema for validation
   - Documents all available options
   - Provides type checking and validation rules

3. **config/briefing_schedule.example.json** - Example configuration
   - Shows advanced features
   - Multiple briefing types (weekday/weekend morning, midday, evening)
   - All features enabled for demonstration

4. **config/README.md** - Comprehensive user documentation
   - Setup and configuration guide
   - Common configuration examples
   - Troubleshooting tips

## Configuration Structure

### 1. Briefings Section

Defines briefing types and their schedules:

```json
"briefings": {
  "morning": {
    "enabled": true,
    "time": "07:00",
    "timezone": "local",
    "days": {
      "monday": true,
      "tuesday": true,
      // ... other days
    },
    "template": "briefing_morning.md",
    "delivery_channels": ["cli", "file"]
  }
}
```

**Features:**
- Support for unlimited custom briefing types
- Per-briefing enable/disable toggle
- Precise time scheduling (24-hour format)
- Timezone support (local or specific timezone)
- Day-of-week granularity (enable/disable per day)
- Custom templates per briefing type
- Multiple delivery channels per briefing

### 2. Delivery Section

Controls how briefings are delivered:

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

**Supported Channels:**
- **CLI**: Terminal/console output with optional colors
- **File**: Save to markdown files with customizable paths
- **Notification**: Desktop notifications (macOS/Linux)
- **State Sync**: Update State/Today.md (Phase 4)
- **Email**: Future enhancement (Phase 4)

### 3. Content Section

Controls what appears in briefings:

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

**Features:**
- Configurable number of top priorities
- Optional quick wins section
- Calendar integration
- Energy/health state prompts (Phase 3)
- Weekend-specific behavior

### 4. Scheduler Section

Controls the scheduler daemon:

```json
"scheduler": {
  "check_interval_minutes": 1,
  "prevent_duplicate_runs": true,
  "log_file": "logs/briefing_scheduler.log",
  "error_notification": true
}
```

**Features:**
- Configurable check interval
- Duplicate run prevention
- Comprehensive logging
- Error notifications

### 5. Advanced Section

Power user settings:

```json
"advanced": {
  "state_dir": "State",
  "templates_dir": "Templates",
  "use_llm_enhancement": false,
  "llm_model": "gpt-4o-mini",
  "pattern_learning_enabled": false
}
```

**Features:**
- Custom directory paths
- Optional LLM enhancement
- Pattern learning (Phase 6)

## Design Principles

### 1. Flexibility
- Support for unlimited custom briefing types
- Mix and match delivery channels
- Easy to add new briefing times or types

### 2. Sensible Defaults
- Morning briefing enabled out-of-box
- Conservative defaults (no notifications by default)
- Works immediately without configuration changes

### 3. Day-of-Week Awareness
- Fine-grained control over which days each briefing runs
- Support for different weekend schedules
- Easy to create weekday-only or weekend-only briefings

### 4. Extensibility
- Schema-based validation
- Support for custom briefing types beyond morning/evening
- Pluggable delivery channels (Phase 4)
- Future: custom content sections (Phase 5)

### 5. ADHD-Friendly
- Clear, unambiguous time formats (24-hour)
- Visual configuration (JSON with comments via documentation)
- Easy enable/disable without losing configuration
- Not overwhelming - defaults to minimal briefings

## Validation

Configuration validation is provided via `Tools/config_validator.py`:

**Features:**
- JSON syntax validation
- Schema validation (if jsonschema available)
- Custom business logic validation
- Clear error messages with location information

**Validation Checks:**
- Time format (HH:MM, 24-hour)
- Time range (00:00 to 23:59)
- All days present in configuration
- Valid delivery channels
- Range checks (max_priorities, check_interval)
- Warning for no days enabled

**Usage:**
```bash
python -m Tools.config_validator config/briefing_schedule.json
```

## Common Patterns

### Pattern 1: Weekday Morning Only
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
  }
}
```

### Pattern 2: Different Weekend Schedule
```json
"briefings": {
  "morning_weekday": {
    "enabled": true,
    "time": "07:00",
    "days": { /* weekdays only */ }
  },
  "morning_weekend": {
    "enabled": true,
    "time": "09:00",  // Later on weekends
    "days": { /* weekends only */ }
  }
}
```

### Pattern 3: Morning + Evening
```json
"briefings": {
  "morning": {
    "enabled": true,
    "time": "07:00"
  },
  "evening": {
    "enabled": true,
    "time": "19:00"
  }
}
```

### Pattern 4: Notification-Only
```json
"briefings": {
  "morning": {
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

## Implementation Notes

### Phase 2.1 Completion (This Phase)
- ✅ JSON configuration structure designed
- ✅ JSON Schema for validation
- ✅ Default configuration provided
- ✅ Example configuration with advanced features
- ✅ ConfigValidator utility created
- ✅ Comprehensive unit tests
- ✅ User documentation (README.md)
- ✅ Technical documentation (this file)

### Future Phases
- **Phase 2.2**: Scheduler daemon will read this config
- **Phase 2.3**: Installation scripts will use this config
- **Phase 2.4**: Manual trigger command will support --config flag
- **Phase 4**: Delivery channels implementation
- **Phase 5**: Extended customization (custom sections, etc.)

## Testing

Unit tests cover:
- Valid minimal configuration
- Invalid time formats
- Invalid time ranges
- Missing days configuration
- Invalid delivery channels
- Invalid range values (max_priorities, check_interval)
- Missing config files
- Invalid JSON syntax
- Warnings for edge cases (no days enabled)
- Validation of actual config files in repo

**Running Tests:**
```bash
pytest tests/unit/test_config_validator.py -v
```

## Acceptance Criteria Met

All acceptance criteria from implementation plan 2.1:

✅ **Config includes morning_time (e.g., '07:00')**
- Supported in briefings.morning.time
- 24-hour HH:MM format
- Validated by schema and custom validator

✅ **Config includes evening_time (e.g., '19:00')**
- Supported in briefings.evening.time
- Same format and validation as morning_time

✅ **Can enable/disable individual briefings**
- Each briefing has "enabled" boolean
- Easy to toggle without losing configuration

✅ **Supports weekday vs weekend schedules**
- Per-briefing "days" object with all 7 days
- Can create separate briefings for weekday/weekend
- Weekend-specific content behavior in content.weekend_mode

✅ **JSON schema documented**
- Complete JSON Schema in briefing_schedule.schema.json
- Definitions for all types and constraints
- Referenced from main config via $schema

✅ **Default config provided**
- briefing_schedule.json with sensible defaults
- Morning enabled, evening disabled
- All days enabled for morning
- File + CLI delivery

## Files Created

1. `config/briefing_schedule.json` (959 bytes)
2. `config/briefing_schedule.schema.json` (5,731 bytes)
3. `config/briefing_schedule.example.json` (1,532 bytes)
4. `config/README.md` (9,862 bytes)
5. `Tools/config_validator.py` (10,127 bytes)
6. `tests/unit/test_config_validator.py` (11,220 bytes)
7. `docs/CONFIG_STRUCTURE.md` (this file)

**Total:** 7 new files, ~39KB of configuration, validation, and documentation

## References

- Implementation Plan: `.auto-claude/specs/034-automated-daily-briefing-engine/implementation_plan.json`
- Spec: `.auto-claude/specs/034-automated-daily-briefing-engine/spec.md`
- JSON Schema Spec: https://json-schema.org/draft-07/schema
- Template Documentation: `Templates/README.md`
