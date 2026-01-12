# Automated Daily Briefing Engine

> **Intelligent, automated daily briefings that help you start and end your day with clarity and intention.**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🎯 What is This?

The Automated Daily Briefing Engine generates personalized morning and evening briefings to help you:

- **Start your day with clarity** - Know your top priorities before opening email
- **End your day with reflection** - Review accomplishments and prep for tomorrow
- **Stay aligned with goals** - Track commitments and focus areas automatically
- **Work with your energy** - Get task recommendations based on your energy levels
- **Learn from patterns** - System adapts based on your work habits

**Designed for ADHD-friendly productivity:** Concise, automated, and requires zero manual prompting.

---

## ✨ Key Features

### 🤖 Fully Automated
- **Scheduled delivery** at your preferred times (morning, evening)
- **No manual prompting** required - runs on cron or systemd
- **Reliable execution** with duplicate prevention

### 🧠 Intelligent Content
- **Smart priority ranking** based on deadlines, importance, and urgency
- **Energy-aware recommendations** - complex tasks for high energy, admin for low
- **Pattern learning** - adapts based on your completion history (14+ days)
- **Adaptive content** - gentler reentry after inactivity, concise when you're productive

### 🏥 Health State Integration
- **Energy tracking** (1-10 scale) with 7-day trends
- **Sleep monitoring** to identify patterns
- **Medication timing** (Vyvanse support for ADHD users)
- **Task recommendations** matched to your current energy level

### 📊 Multi-Channel Delivery
- **CLI output** - Terminal display with colors
- **File output** - Saved to `History/DailyBriefings/`
- **Desktop notifications** - macOS and Linux support
- **State sync** - Updates `State/Today.md` automatically

### 🎨 Fully Customizable
- **Jinja2 templates** - Edit what's included and how it's formatted
- **Custom sections** - Add your own content sections
- **Flexible config** - Enable/disable features, adjust timing
- **CLI tools** - Manage configuration without editing JSON

---

## 🚀 Quick Start

### 1. Install

**Linux (recommended):**
```bash
./scripts/install_briefing_systemd.sh
```

**macOS or Linux alternative:**
```bash
./scripts/install_briefing_cron.sh
```

### 2. Configure

Edit `config/briefing_schedule.json` to set your preferred times:

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

Or use the CLI tool:

```bash
python3 -m commands.pa.briefing_config set briefings.morning.time 08:00
python3 -m commands.pa.briefing_config enable evening
```

### 3. Test

Generate a briefing manually to see what it looks like:

```bash
python3 -m commands.pa.briefing morning
```

### 4. Done!

Wait for your first automated briefing, or check the logs:

```bash
tail -f logs/briefing_scheduler.log
```

---

## 📖 Example Output

### Morning Briefing

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

## 💡 Quick Wins
- Reply to emails
- Update task status
- Review calendar

---

## 💪 Weekday Focus
It's Monday - let's make it productive! Consider your energy levels when tackling complex tasks.

---

*Generated at 2026-01-13 07:00 AM*
```

### Evening Briefing (Sundays)

Sunday evening briefings include a **Weekly Pattern Review** showing:
- 📈 Most productive days and times
- 🎯 Task category breakdown
- 💡 Key insights and pattern changes
- 🚀 Optimizations for next week

---

## 📋 Requirements

- **Python:** 3.7 or higher
- **Operating System:** Linux or macOS
- **Optional:** Jinja2 (`pip3 install jinja2`) for template rendering

---

## 📚 Documentation

### Getting Started
- **[Complete User Guide](docs/briefing_engine_guide.md)** - Comprehensive documentation
- **[Installation Guide](INSTALLATION.md)** - Quick setup instructions
- **[Installation Scripts](scripts/README.md)** - Cron vs systemd details
- **[Example Output](docs/EXAMPLE_OUTPUT.md)** - See what briefings look like

### Configuration
- **[Configuration Guide](config/README.md)** - Full config reference
- **[Configuration CLI](docs/BRIEFING_CONFIG_CLI.md)** - Manage config via command line
- **[Scheduler Guide](docs/SCHEDULER_GUIDE.md)** - Scheduler technical details

### Customization
- **[Template Customization](docs/briefing_customization.md)** - Edit templates
- **[Custom Sections](docs/CUSTOM_SECTIONS.md)** - Add custom content
- **[Delivery Channels](docs/DELIVERY_CHANNELS.md)** - Configure delivery methods

### Features
- **[Health State Tracker](docs/HEALTH_STATE_TRACKER.md)** - Energy and sleep tracking
- **[Pattern Analyzer](docs/PATTERN_ANALYZER.md)** - Pattern learning details
- **[Briefing Command](docs/BRIEFING_COMMAND.md)** - Manual briefing generation

### Developer Resources
- **[Architecture Guide](docs/briefing_architecture.md)** - System architecture and extension points

---

## 🛠️ Usage

### Automated Briefings

Once installed, briefings run automatically. No action needed!

### Manual Briefings

Generate briefings on demand:

```bash
# Basic usage
python3 -m commands.pa.briefing morning
python3 -m commands.pa.briefing evening

# With energy level
python3 -m commands.pa.briefing morning --energy-level 7

# Preview without saving
python3 -m commands.pa.briefing morning --dry-run

# Without health prompts
python3 -m commands.pa.briefing morning --no-prompts
```

### Configuration Management

View and edit configuration without touching JSON:

```bash
# Show configuration
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
```

### Scheduler Management

**systemd (Linux):**
```bash
# Check status
systemctl --user status briefing-scheduler.timer

# View logs
journalctl --user -u briefing-scheduler.service -f

# Stop/start
systemctl --user stop briefing-scheduler.timer
systemctl --user start briefing-scheduler.timer
```

**cron (macOS/Linux):**
```bash
# View cron entries
crontab -l

# View logs
tail -f logs/briefing_scheduler.log

# Manual trigger
python3 -m Tools.briefing_scheduler --mode once
```

---

## 🎨 Customization Examples

### Change Briefing Times

```bash
python3 -m commands.pa.briefing_config set briefings.morning.time 08:30
python3 -m commands.pa.briefing_config set briefings.evening.time 20:00
```

### Enable Weekday-Only Morning Briefings

Edit `config/briefing_schedule.json`:

```json
{
  "briefings": {
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
  }
}
```

### Customize Template Content

Edit `Templates/briefing_morning.md` to add/remove sections:

```markdown
## 🎯 Top 3 Priorities
{% if top_priorities %}
{% for item in top_priorities %}
**{{ loop.index }}. {{ item.title }}**
   - {{ item.priority_reason }}
{% endfor %}
{% endif %}

## 💭 Your Custom Section
Add whatever content you want here!
```

### Enable Pattern Learning

```bash
python3 -m commands.pa.briefing_config --comprehensive enable patterns
```

Or edit `config/briefing_config.json`:

```json
{
  "patterns": {
    "enabled": true,
    "minimum_days_required": 14,
    "influence_level": "medium"
  }
}
```

---

## 🔧 Troubleshooting

### Briefing Not Running?

1. **Check if installed:**
   ```bash
   # systemd
   systemctl --user status briefing-scheduler.timer

   # cron
   crontab -l | grep briefing
   ```

2. **Validate configuration:**
   ```bash
   python3 -m Tools.config_validator config/briefing_schedule.json
   ```

3. **Check logs:**
   ```bash
   tail -50 logs/briefing_scheduler.log
   ```

4. **Test manually:**
   ```bash
   python3 -m Tools.briefing_scheduler --mode once
   ```

### Common Issues

| Issue | Solution |
|-------|----------|
| Python not found | Install Python 3.7+: `brew install python3` (macOS) or `sudo apt-get install python3` (Linux) |
| Jinja2 not installed | Install: `pip3 install jinja2` (optional but recommended) |
| Permission denied | Make scripts executable: `chmod +x scripts/*.sh` |
| Invalid configuration | Validate: `python3 -m Tools.config_validator config/briefing_schedule.json` |
| Wrong timezone | Scheduler uses system time - check: `date` |

**See also:** [Troubleshooting Guide](docs/briefing_engine_guide.md#troubleshooting)

---

## 🏗️ Architecture

### Components

```
Automated Daily Briefing Engine
│
├── BriefingEngine (Tools/briefing_engine.py)
│   ├── Data gathering (State files)
│   ├── Priority ranking
│   ├── Template rendering
│   └── Health state integration
│
├── BriefingScheduler (Tools/briefing_scheduler.py)
│   ├── Time-based execution
│   ├── Duplicate prevention
│   └── Multi-channel delivery
│
├── HealthStateTracker (Tools/health_state_tracker.py)
│   ├── Energy tracking
│   ├── Pattern detection
│   └── Recommendations
│
├── PatternAnalyzer (Tools/pattern_analyzer.py)
│   ├── Task completion tracking
│   ├── Pattern identification
│   └── Context-aware recommendations
│
└── Delivery Channels (Tools/delivery_channels.py)
    ├── CLI output
    ├── File output
    ├── Notifications
    └── State sync
```

### Data Flow

```
1. Scheduler triggers at configured time
   ↓
2. BriefingEngine gathers context
   - Reads State files (Commitments.md, ThisWeek.md, etc.)
   - Gets health state from HealthLog.json
   - Gets patterns from BriefingPatterns.json
   ↓
3. Priority ranking with intelligence
   - Deadline urgency
   - Day-of-week adaptations
   - Energy-aware recommendations
   - Pattern-based boosts
   ↓
4. Template rendering
   - Jinja2 templates
   - Custom sections
   - Adaptive content
   ↓
5. Multi-channel delivery
   - CLI, file, notifications, state sync
   ↓
6. Run state tracking
   - Prevents duplicates
   - Records completion
```

---

## 🧪 Testing

The project includes comprehensive test coverage:

- **Unit Tests:** 233+ tests across all components
- **Integration Tests:** End-to-end scheduler and delivery testing
- **Coverage:** >90% code coverage

Run tests:

```bash
# All tests
python3 -m pytest tests/

# Specific test file
python3 -m pytest tests/unit/test_briefing_engine.py -v

# With coverage
python3 -m pytest tests/ --cov=Tools --cov-report=html
```

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- Additional delivery channels (Slack, Discord, etc.)
- Calendar integration (Google Calendar, iCal)
- Mobile app companion
- Web dashboard
- Additional pattern types
- More template examples

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with:
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- Python standard library

Inspired by:
- ADHD-friendly productivity principles
- Automated daily briefings from executive assistants
- GTD (Getting Things Done) methodology

---

## 📞 Support

- **Documentation:** [Complete User Guide](docs/briefing_engine_guide.md)
- **Issues:** Report bugs on GitHub
- **Questions:** Check [FAQ](docs/briefing_engine_guide.md#faq)
- **Feature Requests:** Submit on GitHub

---

## 🎯 What's Next?

Future enhancements:
- Email delivery channel
- Calendar integration
- Mobile notifications
- Web dashboard
- Voice briefings
- Team briefings

---

**Built with ❤️ for ADHD-friendly productivity**

*Start your day with clarity. End it with intention.*
