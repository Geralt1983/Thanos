# Automated Daily Briefing Engine - Complete User Guide

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Using the Briefing System](#using-the-briefing-system)
6. [Template Customization](#template-customization)
7. [Health State Tracking](#health-state-tracking)
8. [Pattern Learning](#pattern-learning)
9. [Delivery Channels](#delivery-channels)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Topics](#advanced-topics)
12. [FAQ](#faq)

---

## Overview

### What is the Automated Daily Briefing Engine?

The Automated Daily Briefing Engine is an intelligent system that generates personalized morning and evening briefings to help you start and end your day with clarity and intention. Designed with ADHD-friendly principles, it automatically delivers briefings at configured times without requiring manual prompts.

### Key Features

✨ **Automated Scheduling**
- Morning and evening briefings at your preferred times
- Day-of-week scheduling (weekday/weekend modes)
- Reliable execution via cron or systemd

🎯 **Intelligent Content**
- Smart priority ranking based on deadlines and urgency
- Energy-aware task recommendations
- Pattern learning from your work habits
- Adaptive content based on recent activity

🏥 **Health State Integration**
- Daily energy level tracking (1-10 scale)
- Sleep hours monitoring
- Medication timing (Vyvanse support for ADHD users)
- Health trend analysis and insights

📊 **Multi-Channel Delivery**
- CLI output
- File output (History/DailyBriefings/)
- Desktop notifications (macOS/Linux)
- State file sync (updates State/Today.md)

🎨 **Fully Customizable**
- Jinja2-based template system
- Custom content sections
- Configurable delivery channels
- Adjustable priority ranking

---

## Quick Start

### 1. Install the Scheduler

**Linux (recommended):**
```bash
./scripts/install_briefing_systemd.sh
```

**macOS or Linux alternative:**
```bash
./scripts/install_briefing_cron.sh
```

### 2. Configure Your Schedule

Edit `config/briefing_schedule.json`:
```json
{
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
}
```

### 3. Test It

Generate a briefing manually:
```bash
python3 -m commands.pa.briefing morning
```

### 4. Wait for Your First Automated Briefing

Check logs to confirm it's working:
```bash
tail -f logs/briefing_scheduler.log
```

---

## Installation

### System Requirements

- **Python:** 3.7 or higher
- **Operating System:** Linux or macOS
- **Optional:** Jinja2 (`pip3 install jinja2`) for template rendering

### Installation Methods

There are two installation methods, both install as user services (no root access required):

#### Method 1: systemd (Linux Only, Recommended)

**Advantages:**
- Better process management
- Integration with journalctl logging
- Automatic restart on failure
- Easy start/stop control

**Installation:**
```bash
./scripts/install_briefing_systemd.sh
```

**Management:**
```bash
# Check status
systemctl --user status briefing-scheduler.timer

# View logs
journalctl --user -u briefing-scheduler.service -f

# Stop/start
systemctl --user stop briefing-scheduler.timer
systemctl --user start briefing-scheduler.timer
```

#### Method 2: cron (macOS and Linux)

**Advantages:**
- Universal (works on all Unix-like systems)
- Simple and reliable
- Minimal requirements

**Installation:**
```bash
./scripts/install_briefing_cron.sh
```

**Management:**
```bash
# View cron entries
crontab -l

# View logs
tail -f logs/briefing_scheduler.log

# Manual trigger
cd /path/to/project && python3 -m Tools.briefing_scheduler --mode once
```

### Uninstallation

```bash
# Remove everything
./scripts/uninstall_briefing.sh

# Remove specific method
./scripts/uninstall_briefing.sh --cron
./scripts/uninstall_briefing.sh --systemd
```

### Validation

Both installation scripts automatically validate:
- ✅ Python 3.7+ installation
- ✅ Project structure (State/, Templates/, config/)
- ✅ Python module imports
- ✅ Log directory creation
- ✅ Optional: Jinja2 availability

**See also:** [INSTALLATION.md](../INSTALLATION.md) and [scripts/README.md](../scripts/README.md)

---

## Configuration

### Configuration Files

The briefing system uses JSON configuration files:

1. **briefing_schedule.json** (Simple) - Basic scheduling configuration
2. **briefing_config.json** (Advanced) - Comprehensive configuration with health, patterns, and advanced features

### Simple Configuration (briefing_schedule.json)

Perfect for getting started:

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "template": "briefing_morning.md",
      "days": {
        "monday": true,
        "tuesday": true,
        "wednesday": true,
        "thursday": true,
        "friday": true,
        "saturday": false,
        "sunday": false
      },
      "delivery_channels": ["cli", "file"]
    },
    "evening": {
      "enabled": true,
      "time": "19:00",
      "template": "briefing_evening.md",
      "days": {
        "monday": false,
        "tuesday": false,
        "wednesday": false,
        "thursday": false,
        "friday": false,
        "saturday": false,
        "sunday": true
      },
      "delivery_channels": ["file"]
    }
  },
  "delivery": {
    "cli": {
      "enabled": true,
      "colored_output": true
    },
    "file": {
      "enabled": true,
      "output_dir": "History/DailyBriefings",
      "filename_format": "{date}_{type}_briefing.md"
    }
  },
  "content": {
    "max_priorities": 3,
    "include_quick_wins": true,
    "weekend_mode": "personal_focus"
  },
  "scheduler": {
    "check_interval_minutes": 1,
    "prevent_duplicate_runs": true,
    "log_file": "logs/briefing_scheduler.log",
    "log_level": "INFO"
  }
}
```

### Configuration Management CLI

Use the CLI tool to view and edit configuration without manual JSON editing:

```bash
# Show entire configuration
python3 -m commands.pa.briefing_config show

# Get specific value
python3 -m commands.pa.briefing_config get briefings.morning.time

# Set value
python3 -m commands.pa.briefing_config set briefings.morning.time 08:00

# Enable/disable features
python3 -m commands.pa.briefing_config enable evening
python3 -m commands.pa.briefing_config disable notifications

# Validate configuration
python3 -m commands.pa.briefing_config validate

# List all available keys
python3 -m commands.pa.briefing_config list-keys
```

### Example Configurations

#### Morning Briefing Only (Weekdays)

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:30",
      "days": {
        "monday": true,
        "tuesday": true,
        "wednesday": true,
        "thursday": true,
        "friday": true,
        "saturday": false,
        "sunday": false
      }
    },
    "evening": {
      "enabled": false
    }
  }
}
```

#### Weekend Review Only

```json
{
  "briefings": {
    "morning": {
      "enabled": false
    },
    "evening": {
      "enabled": true,
      "time": "19:00",
      "days": {
        "monday": false,
        "tuesday": false,
        "wednesday": false,
        "thursday": false,
        "friday": false,
        "saturday": false,
        "sunday": true
      }
    }
  }
}
```

### Validation

Always validate your configuration before saving:

```bash
python3 -m Tools.config_validator config/briefing_schedule.json
```

**See also:** [config/README.md](../config/README.md) and [docs/BRIEFING_CONFIG_CLI.md](BRIEFING_CONFIG_CLI.md)

---

## Using the Briefing System

### Automated Briefings

Once installed, briefings run automatically at configured times. No action required!

**What happens automatically:**
1. Scheduler checks configuration every minute
2. At configured time (e.g., 07:00), checks if briefing already ran today
3. Generates briefing using BriefingEngine
4. Delivers via configured channels (CLI, file, notification, state sync)
5. Records run to prevent duplicates

### Manual Briefings

Generate a briefing on demand:

```bash
# Basic usage
python3 -m commands.pa.briefing morning
python3 -m commands.pa.briefing evening

# With energy level
python3 -m commands.pa.briefing morning --energy-level 7

# Dry run (preview without saving)
python3 -m commands.pa.briefing morning --dry-run

# Without health prompts
python3 -m commands.pa.briefing morning --no-prompts

# Verbose logging
python3 -m commands.pa.briefing morning --verbose
```

### Morning Briefing Features

A typical morning briefing includes:

📊 **Adaptive Mode**
- Reentry mode (3+ days inactive)
- Catchup mode (5+ overdue tasks)
- Concise mode (15+ activities in 7 days)

🏥 **Health State** (if enabled)
- Current energy level (1-10)
- Sleep hours
- Medication timing (Vyvanse)
- 7-day trend

🎯 **Top 3 Priorities**
- Smart ranking by urgency and deadline
- Day-of-week adaptations
- Energy-aware recommendations
- Pattern-based boosts

📋 **Active Commitments**
- From State/Commitments.md
- Filtered to active items
- Deadline tracking

📅 **This Week's Tasks**
- From State/ThisWeek.md
- Pending tasks only

🎓 **Current Focus Areas**
- From State/CurrentFocus.md

💡 **Quick Wins**
- Simple tasks under 15 minutes
- Momentum builders

🌴/💪 **Weekend/Weekday Mode**
- Adapted content based on day

### Evening Briefing Features

A typical evening briefing includes:

📊 **Energy & Productivity Check**
- Morning vs evening energy comparison
- Energy trend analysis
- 7-day health trend

✅ **Today's Accomplishments**
- Reflection on completed tasks
- Celebration of wins

⚡ **Energy-Draining Activities** (if significant drain)
- Identified draining tasks
- Suggestions for improvement

💡 **Improvements for Tomorrow**
- User-provided improvements
- System-generated recommendations

🔮 **Tomorrow's Preview**
- Top priorities for tomorrow
- Preview of upcoming tasks

📝 **Tomorrow Prep Checklist**
- Evening prep tasks

💭 **Commitment Progress**
- Progress on active commitments

📊 **Weekly Pattern Review** (Sundays only)
- Most productive days/times
- Task category breakdown
- Pattern changes
- Optimizations for next week

### Example Output

**Morning Briefing Example:**

```markdown
# ☀️ Morning Briefing - Monday, January 13, 2026

Good morning! Here's your personalized briefing for today.

---

## 🏥 Health State
**Current Energy:** 7/10 | **Sleep:** 7.5 hours | **Vyvanse:** 07:15

**7-Day Trend:**
- Average Energy: 6.8/10
- Average Sleep: 7.2 hours
- Your best day: Wednesday (8/10)

---

## 🎯 Top 3 Priorities

**1. Finish Q1 product roadmap**
   - Category: work
   - Urgency: HIGH
   - Why: Due today, work task, Monday boost

**2. Review PR from Sarah**
   - Category: work
   - Urgency: HIGH
   - Why: Due today

**3. Plan team meeting agenda**
   - Category: work
   - Urgency: MEDIUM
   - Why: Due this week, frequently done on Mondays

---

## 📋 Active Commitments
- Complete product roadmap (due: 2026-01-13)
  - Category: work
- Launch marketing campaign (due: 2026-01-20)
  - Category: work

---

## 💡 Quick Wins
- Reply to emails
- Update task status
- Review calendar

---

## 💪 Weekday Focus
It's Monday - let's make it productive! Consider your energy levels when tackling complex tasks.

---

*Generated at 2026-01-13 07:00 AM*
*Briefing Type: Morning*
```

**See also:** [docs/BRIEFING_COMMAND.md](BRIEFING_COMMAND.md)

---

## Template Customization

### Template System

The briefing system uses Jinja2 templates for flexible, customizable output.

**Template Files:**
- `Templates/briefing_morning.md` - Morning briefing template
- `Templates/briefing_evening.md` - Evening briefing template
- `Templates/briefing_weekly_review.md` - Weekly review template (Sundays)

### Available Variables

#### Common Variables (All Templates)

```python
today_date          # e.g., "2026-01-13"
day_of_week         # e.g., "Monday"
is_weekend          # Boolean
generated_at        # Timestamp
top_priorities      # List of prioritized items
active_commitments  # List of active commitments
pending_tasks       # List of pending tasks
focus_areas         # List of focus areas
quick_wins          # List of quick win tasks
custom_sections     # List of custom sections
```

#### Morning-Specific Variables

```python
health_state        # Current health state and trend
adaptive_mode       # Adaptive mode info (reentry/catchup/concise)
```

#### Evening-Specific Variables

```python
reflection_data         # Evening reflection data
accomplishments         # Today's accomplishments
tomorrow_priorities     # Preview of tomorrow
prep_checklist         # Tomorrow prep items
commitment_progress    # Progress on commitments
weekly_review          # Weekly pattern review (Sundays)
```

### Customization Examples

#### Example 1: Remove Health State Section

Edit `Templates/briefing_morning.md`:

```markdown
{% if false %}  <!-- Disable health state section -->
## 🏥 Health State
...
{% endif %}
```

#### Example 2: Reorder Sections

Move "Quick Wins" before "Top Priorities":

```markdown
## 💡 Quick Wins
{% if quick_wins %}
...
{% endif %}

---

## 🎯 Top 3 Priorities
{% if top_priorities %}
...
{% endif %}
```

#### Example 3: Add Custom Content

Add a motivational quote section:

```markdown
---

## 💭 Daily Quote

> "The best way to predict the future is to create it."
> - Peter Drucker

---
```

#### Example 4: Conditional Content

Show different content based on energy level:

```markdown
{% if health_state and health_state.energy_level <= 5 %}
## ⚠️ Low Energy Mode
Focus on admin tasks and don't overcommit today.
{% elif health_state and health_state.energy_level >= 8 %}
## 🚀 High Energy Mode
Great time for deep work and complex problem-solving!
{% endif %}
```

### Custom Sections (Config-Based)

Add custom sections via configuration:

```json
{
  "content": {
    "sections": [
      {
        "id": "motivation",
        "title": "Daily Motivation",
        "enabled": true,
        "template": "Remember your goals and stay focused!",
        "conditions": {
          "days": ["monday"],
          "briefing_types": ["morning"]
        }
      }
    ]
  }
}
```

**See also:**
- [Templates/README.md](../Templates/README.md)
- [docs/briefing_customization.md](briefing_customization.md)
- [docs/CUSTOM_SECTIONS.md](CUSTOM_SECTIONS.md)

---

## Health State Tracking

### Overview

Health state tracking helps the briefing system provide energy-aware recommendations and identify patterns in your productivity.

### Daily Tracking

**Tracked Metrics:**
- **Energy Level:** 1-10 scale
- **Sleep Hours:** Hours of sleep last night
- **Vyvanse Time:** Medication timing (for ADHD users)
- **Notes:** Optional daily notes

### Energy Level Scale

```
10 - Peak performance, exceptional focus
9  - Excellent energy, ready for deep work
8  - High energy, good for complex tasks
7  - Good energy, most tasks manageable
6  - Moderate energy, routine work fine
5  - Average energy, pacing needed
4  - Below average, focus on simple tasks
3  - Low energy, minimal demands
2  - Very low, survival mode
1  - Exhausted, rest required
```

### How It's Used

**Morning Briefing:**
- Prompts for health state during generation
- Shows 7-day trend
- Influences task recommendations

**Task Recommendations:**
- **High Energy (8-10):** Deep work, complex tasks, architecture
- **Good Energy (6-7):** Balanced mix of work
- **Moderate Energy (4-5):** Admin tasks, lighter work
- **Low Energy (1-3):** Simple tasks only, reschedule complex work

**Evening Briefing:**
- Prompts for evening energy level
- Compares morning vs evening
- Identifies energy-draining activities

### Pattern Detection

With 14+ days of data, the system identifies:
- Day-of-week energy patterns (e.g., "Energy low on Mondays")
- Best/worst energy days
- Sleep-energy correlation
- Optimal medication timing

### Manual Health Logging

Track health state manually:

```python
from Tools.health_state_tracker import HealthStateTracker

tracker = HealthStateTracker()
tracker.log_entry(
    energy_level=7,
    sleep_hours=7.5,
    vyvanse_time="07:15",
    notes="Felt good, productive morning"
)
```

**See also:** [docs/HEALTH_STATE_TRACKER.md](HEALTH_STATE_TRACKER.md)

---

## Pattern Learning

### Overview

Pattern learning analyzes your task completion history to provide intelligent, personalized recommendations.

### How It Works

1. **Tracking:** System records task completions with metadata (day, time, category)
2. **Analysis:** After 14+ days, patterns are identified
3. **Application:** Patterns influence (but don't override) priority ranking

### Detected Patterns

- **Day-of-Week:** Tasks frequently done on specific days (e.g., "Admin tasks on Fridays")
- **Time-of-Day:** Tasks typically done at certain times (morning/afternoon/evening)
- **Category:** Task category distributions across days

### Configuration

Enable pattern learning in `config/briefing_config.json`:

```json
{
  "patterns": {
    "enabled": true,
    "minimum_days_required": 14,
    "lookback_days": 90,
    "patterns_file": "State/BriefingPatterns.json",
    "influence_level": "medium"
  }
}
```

**Influence Levels:**
- **Low:** ≤5 point boost (subtle hints)
- **Medium:** ≤10 point boost (moderate influence)
- **High:** ≤15 point boost (strong influence)

### Example Pattern Insights

```
Pattern: "Admin tasks on Fridays"
- 12 admin tasks completed on Fridays
- Confidence: 85%
- Effect: Admin tasks get +8 point boost on Fridays
```

### Important Notes

- ⚠️ Patterns influence, never override deadline urgency
- 📊 Requires minimum 14 days of data
- 🔒 Can be disabled anytime via config
- 🎯 Most effective with consistent task tracking

**See also:** [docs/PATTERN_ANALYZER.md](PATTERN_ANALYZER.md)

---

## Delivery Channels

### Overview

Briefings can be delivered through multiple channels simultaneously.

### Available Channels

#### 1. CLI Output

Prints briefing to terminal with optional colored output.

```json
{
  "delivery": {
    "cli": {
      "enabled": true,
      "colored_output": true
    }
  }
}
```

#### 2. File Output

Saves briefing to file (default: `History/DailyBriefings/`).

```json
{
  "delivery": {
    "file": {
      "enabled": true,
      "output_dir": "History/DailyBriefings",
      "filename_format": "{date}_{type}_briefing.md"
    }
  }
}
```

#### 3. Desktop Notifications

Sends OS notifications with briefing summary.

```json
{
  "delivery": {
    "notification": {
      "enabled": true,
      "show_summary": true,
      "max_summary_length": 200
    }
  }
}
```

**Platform Support:**
- **macOS:** terminal-notifier or osascript fallback
- **Linux:** notify-send
- **Windows:** Not supported

#### 4. State Sync

Updates `State/Today.md` with briefing content.

```json
{
  "delivery": {
    "state_sync": {
      "enabled": true,
      "target_file": "State/Today.md",
      "section_mapping": {
        "morning": "## Morning Brief",
        "evening": "## Evening Brief"
      }
    }
  }
}
```

#### 5. Email (Future)

Email delivery is planned but not yet implemented.

```json
{
  "delivery": {
    "email": {
      "enabled": false,
      "to": "your-email@example.com"
    }
  }
}
```

### Multi-Channel Delivery

Enable multiple channels simultaneously:

```json
{
  "briefings": {
    "morning": {
      "delivery_channels": ["cli", "file", "notification", "state_sync"]
    }
  }
}
```

**See also:**
- [docs/DELIVERY_CHANNELS.md](DELIVERY_CHANNELS.md)
- [docs/STATE_SYNC_CHANNEL.md](STATE_SYNC_CHANNEL.md)

---

## Troubleshooting

### Briefing Not Running

**1. Check if scheduler is installed:**

```bash
# For systemd
systemctl --user status briefing-scheduler.timer

# For cron
crontab -l | grep briefing
```

**2. Validate configuration:**

```bash
python3 -m Tools.config_validator config/briefing_schedule.json
```

**3. Check logs:**

```bash
# For systemd
journalctl --user -u briefing-scheduler.service -n 50

# For cron
tail -50 logs/briefing_scheduler.log
```

**4. Test manually:**

```bash
python3 -m Tools.briefing_scheduler --mode once
```

### Common Issues

#### "Python not found"

**Solution:** Install Python 3.7+
```bash
# macOS
brew install python3

# Linux
sudo apt-get install python3  # Debian/Ubuntu
sudo yum install python3      # CentOS/RHEL
```

#### "Failed to import BriefingScheduler"

**Solution:** Check you're in correct directory and files exist
```bash
pwd  # Should be project root
ls Tools/briefing_scheduler.py
ls Tools/briefing_engine.py
```

#### "Jinja2 not installed"

**Solution:** Install Jinja2 (optional but recommended)
```bash
pip3 install jinja2
```

Briefings will work without Jinja2 using fallback rendering.

#### "Permission denied"

**Solution:** Check file permissions
```bash
# Scripts executable
chmod +x scripts/*.sh

# Log directory writable
chmod 755 logs/

# Config readable
chmod 644 config/briefing_schedule.json
```

#### "Configuration invalid"

**Solution:** Use validator to find issues
```bash
python3 -m Tools.config_validator config/briefing_schedule.json
```

Common config errors:
- Invalid time format (use "HH:MM" 24-hour)
- Invalid JSON syntax
- Missing required fields

#### "Briefing runs multiple times per day"

**Solution:** Check duplicate prevention is enabled
```json
{
  "scheduler": {
    "prevent_duplicate_runs": true
  }
}
```

Check run state file:
```bash
cat State/.briefing_runs.json
```

#### "Wrong timezone"

**Solution:** Scheduler uses system timezone
```bash
# Check system time
date

# Check Python time
python3 -c "from datetime import datetime; print(datetime.now())"
```

If times don't match, fix system timezone settings.

### Getting Help

If issues persist:

1. Review logs for detailed error messages
2. Check documentation: `docs/SCHEDULER_GUIDE.md`
3. Test components individually (BriefingEngine, scheduler, config)
4. Create a GitHub issue with logs and configuration

---

## Advanced Topics

### Custom Section Data Providers

Create custom data providers for sections:

```python
# custom_providers.py
def get_weather_data(context):
    # Fetch weather data
    return {
        'temperature': 72,
        'condition': 'Sunny',
        'forecast': 'Clear skies all day'
    }
```

Register in config:

```json
{
  "content": {
    "sections": [
      {
        "id": "weather",
        "title": "Today's Weather",
        "enabled": true,
        "data_provider": "custom_providers.get_weather_data"
      }
    ]
  }
}
```

### LLM Enhancement (Optional)

Enable LLM-powered insights:

```json
{
  "advanced": {
    "llm_enhancement": {
      "enabled": true,
      "model": "gpt-4",
      "temperature": 0.7,
      "max_tokens": 500
    }
  }
}
```

**Note:** Requires LiteLLM client and API keys.

### Multiple Briefing Types

Create custom briefing types beyond morning/evening:

```json
{
  "briefings": {
    "midday_check": {
      "enabled": true,
      "time": "12:00",
      "template": "briefing_midday.md",
      "delivery_channels": ["notification"]
    }
  }
}
```

### Running as Different User

For system-wide installation:

```bash
# Create system service (as root)
sudo cp ~/.config/systemd/user/briefing-scheduler.* /etc/systemd/system/

# Edit to specify user
sudo systemctl edit briefing-scheduler.service
# Add: User=username

# Enable
sudo systemctl enable briefing-scheduler.timer
```

### Backup and Restore

**Backup important files:**
```bash
# Configuration
cp config/briefing_schedule.json config/briefing_schedule.json.backup

# Health log
cp State/HealthLog.json State/HealthLog.json.backup

# Pattern data
cp State/BriefingPatterns.json State/BriefingPatterns.json.backup
```

**Restore:**
```bash
cp config/briefing_schedule.json.backup config/briefing_schedule.json
# Restart scheduler after restore
```

---

## FAQ

### Q: Do briefings work without Jinja2?

**A:** Yes! Briefings will work without Jinja2, but templates won't be rendered. You'll get structured data output instead. For best experience, install Jinja2:
```bash
pip3 install jinja2
```

### Q: Can I disable health prompts?

**A:** Yes! Use the `--no-prompts` flag:
```bash
python3 -m commands.pa.briefing morning --no-prompts
```

Or disable health tracking entirely in config:
```json
{
  "health": {
    "enabled": false
  }
}
```

### Q: How do I change briefing times?

**A:** Edit configuration:
```bash
python3 -m commands.pa.briefing_config set briefings.morning.time 08:00
```

Or manually edit `config/briefing_schedule.json`.

### Q: Can I run briefings without installing scheduler?

**A:** Yes! Use manual command:
```bash
python3 -m commands.pa.briefing morning
```

### Q: Do patterns affect urgent deadlines?

**A:** No! Patterns never override deadline urgency. An item due today will always be prioritized, regardless of patterns.

### Q: Can I use both cron and systemd?

**A:** Not recommended. Choose one method. If you install both, you may get duplicate briefings.

### Q: How do I temporarily disable briefings?

**A:** Easiest way:
```bash
# For systemd
systemctl --user stop briefing-scheduler.timer

# For cron
crontab -e  # Comment out the briefing line
```

Or disable in config:
```bash
python3 -m commands.pa.briefing_config disable morning
python3 -m commands.pa.briefing_config disable evening
```

### Q: Where are briefings saved?

**A:** Default location: `History/DailyBriefings/`

Filename format: `{date}_{type}_briefing.md`
- Example: `2026-01-13_morning_briefing.md`

### Q: Can I customize the notification sound?

**A:** Not currently supported through config. Notifications use OS defaults.

### Q: How long is pattern data kept?

**A:** Pattern data older than 180 days is automatically cleaned up. Configurable via:
```json
{
  "patterns": {
    "lookback_days": 90
  }
}
```

### Q: Can I have different configurations for weekdays vs weekends?

**A:** Yes! Use day-specific settings:
```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "days": {
        "saturday": false,
        "sunday": false
      }
    }
  }
}
```

### Q: How do I see what's in my pattern data?

**A:** Check the pattern file:
```bash
cat State/BriefingPatterns.json | python3 -m json.tool
```

Or use pattern analyzer example:
```bash
python3 example_pattern_analyzer.py
```

---

## Additional Resources

### Documentation

- [INSTALLATION.md](../INSTALLATION.md) - Quick installation guide
- [scripts/README.md](../scripts/README.md) - Installation scripts details
- [config/README.md](../config/README.md) - Configuration reference
- [Templates/README.md](../Templates/README.md) - Template documentation
- [docs/SCHEDULER_GUIDE.md](SCHEDULER_GUIDE.md) - Scheduler technical guide
- [docs/BRIEFING_COMMAND.md](BRIEFING_COMMAND.md) - Manual briefing command
- [docs/BRIEFING_CONFIG_CLI.md](BRIEFING_CONFIG_CLI.md) - Config management CLI
- [docs/briefing_customization.md](briefing_customization.md) - Template customization
- [docs/CUSTOM_SECTIONS.md](CUSTOM_SECTIONS.md) - Custom sections guide
- [docs/HEALTH_STATE_TRACKER.md](HEALTH_STATE_TRACKER.md) - Health tracking API
- [docs/PATTERN_ANALYZER.md](PATTERN_ANALYZER.md) - Pattern learning details
- [docs/DELIVERY_CHANNELS.md](DELIVERY_CHANNELS.md) - Delivery channels guide

### Example Scripts

- `example_briefing_engine.py` - BriefingEngine usage
- `example_priority_ranking.py` - Priority ranking examples
- `example_template_rendering.py` - Template rendering
- `example_health_state_tracker.py` - Health tracking
- `example_pattern_analyzer.py` - Pattern analysis
- `example_delivery_channels.py` - Delivery channel usage

### Support

- **Issues:** Report bugs on GitHub
- **Questions:** Check FAQ above
- **Feature Requests:** Submit on GitHub

---

**Last Updated:** January 2026
**Version:** 1.0
**Author:** Thanos Team
