# Briefing Scheduler Installation Scripts

This directory contains installation scripts for setting up the Briefing Scheduler to run automatically on your system.

## Quick Start

Choose one of the two installation methods based on your system:

### For Linux (Recommended: systemd)

```bash
./scripts/install_briefing_systemd.sh
```

### For macOS or Linux (Alternative: cron)

```bash
./scripts/install_briefing_cron.sh
```

## Installation Methods

### Method 1: systemd (Linux Only)

**Recommended for Linux systems** as it provides better process management, logging, and control.

**Features:**
- Automatic start on system boot (user session)
- Better logging via `journalctl`
- Easy start/stop/status control
- Automatic restart on failure
- Runs every minute via systemd timer

**Installation:**
```bash
./scripts/install_briefing_systemd.sh
```

**Management Commands:**
```bash
# View timer status
systemctl --user status briefing-scheduler.timer

# View service status
systemctl --user status briefing-scheduler.service

# View logs (live)
journalctl --user -u briefing-scheduler.service -f

# Stop/start timer
systemctl --user stop briefing-scheduler.timer
systemctl --user start briefing-scheduler.timer

# Manually trigger a check
systemctl --user start briefing-scheduler.service
```

**Files Created:**
- `~/.config/systemd/user/briefing-scheduler.service` - Service definition
- `~/.config/systemd/user/briefing-scheduler.timer` - Timer definition

### Method 2: cron (macOS and Linux)

**Universal method** that works on macOS and Linux systems.

**Features:**
- Works on all Unix-like systems
- Simple and reliable
- Runs every minute via cron
- Minimal system requirements

**Installation:**
```bash
./scripts/install_briefing_cron.sh
```

**Management Commands:**
```bash
# View cron entries
crontab -l

# View logs
tail -f logs/briefing_scheduler.log
tail -f logs/cron.log

# Edit cron entries
crontab -e

# Manually test
cd /path/to/project && python3 -m Tools.briefing_scheduler --mode once
```

**Cron Entry Created:**
```cron
# Thanos Briefing Scheduler
* * * * * cd /path/to/project && python3 -m Tools.briefing_scheduler --mode once >> /path/to/project/logs/cron.log 2>&1
```

## Uninstallation

### Remove Everything (Both Methods)

```bash
./scripts/uninstall_briefing.sh
```

### Remove Specific Method

```bash
# Remove only cron
./scripts/uninstall_briefing.sh --cron

# Remove only systemd
./scripts/uninstall_briefing.sh --systemd
```

The uninstall script will:
- Remove cron entries (if using cron)
- Stop and remove systemd service/timer (if using systemd)
- Optionally remove log files and run state
- Preserve configuration and templates

## Requirements

### System Requirements
- Python 3.7 or higher
- Bash shell
- Linux or macOS operating system

### Optional Dependencies
- **Jinja2** (for template rendering): `pip3 install jinja2`
  - If not installed, briefings will still work but templates will be skipped

### Validated on Installation
The installation scripts automatically validate:
- ✓ Python version (>= 3.7)
- ✓ Project structure (State/, Templates/, config/)
- ✓ Required Python modules can be imported
- ✓ Log directory exists/created
- ✓ Optional: Jinja2 availability

## Configuration

After installation, edit the configuration file to set your preferred briefing times:

```bash
# Edit configuration
vim config/briefing_schedule.json

# Or use your preferred editor
nano config/briefing_schedule.json
```

**Key configuration options:**
```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",     // 24-hour format
      "days": {
        "monday": true,
        "tuesday": true,
        // ... enable/disable per day
      }
    }
  }
}
```

See `config/README.md` for complete configuration documentation.

## How It Works

### Scheduling Architecture

Both installation methods use the same underlying scheduler but trigger it differently:

1. **Cron/Timer Trigger**: Every minute, the system triggers the scheduler
2. **Scheduler Check**: The scheduler reads `config/briefing_schedule.json`
3. **Time Match**: Compares current time against configured briefing times
4. **Day Check**: Verifies the briefing is enabled for today
5. **Duplicate Prevention**: Checks if briefing already ran today (in `State/.briefing_runs.json`)
6. **Briefing Generation**: If due and not run, generates and delivers the briefing
7. **State Update**: Records the run to prevent duplicates

### Why Every Minute?

The scheduler runs every minute to ensure briefings trigger within 60 seconds of the configured time. The duplicate prevention system ensures briefings only run once per day even if the scheduler runs multiple times.

**Example:**
- Configured time: `07:00`
- Scheduler checks: `06:59`, `07:00`, `07:01`, ...
- At `07:00`: Briefing runs and is recorded
- At `07:01` and later: Scheduler sees briefing already ran today, skips

## Troubleshooting

### Briefing Not Running

1. **Check if scheduler is active:**
   ```bash
   # For systemd
   systemctl --user status briefing-scheduler.timer

   # For cron
   crontab -l | grep briefing
   ```

2. **Check configuration:**
   ```bash
   # Validate config
   python3 -m Tools.config_validator config/briefing_schedule.json

   # Check if briefing is enabled
   cat config/briefing_schedule.json | grep -A5 "morning"
   ```

3. **Check logs:**
   ```bash
   # For systemd
   journalctl --user -u briefing-scheduler.service -n 50

   # For cron
   tail -50 logs/briefing_scheduler.log
   tail -50 logs/cron.log
   ```

4. **Test manually:**
   ```bash
   cd /path/to/project
   python3 -m Tools.briefing_scheduler --mode once
   ```

### Python Import Errors

If the scheduler can't import required modules:

```bash
# Test imports
cd /path/to/project
python3 -c "from Tools.briefing_scheduler import BriefingScheduler"

# Check Python path
python3 -c "import sys; print(sys.path)"
```

### Permission Issues

If logs show permission errors:

```bash
# Fix log directory permissions
chmod 755 logs/
chmod 644 logs/*.log

# Fix State directory permissions
chmod 755 State/
chmod 644 State/*
```

### Timezone Issues

The scheduler uses the system's local timezone. To verify:

```bash
# Check system timezone
date
timedatectl  # Linux only

# Check Python timezone
python3 -c "from datetime import datetime; print(datetime.now())"
```

## Comparison: systemd vs cron

| Feature | systemd | cron |
|---------|---------|------|
| **Platform** | Linux only | macOS, Linux |
| **Logging** | journalctl integration | File-based |
| **Control** | systemctl commands | crontab editing |
| **Auto-restart** | Yes (on failure) | No |
| **User service** | Yes (survives logout*) | Yes |
| **Complexity** | Medium | Simple |
| **Recommended** | Linux users | macOS users |

*Note: systemd user services can be configured to start on boot and survive logout with `loginctl enable-linger`.

## Examples

### Example 1: Morning Briefing Only

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:30"
    },
    "evening": {
      "enabled": false
    }
  }
}
```

Install and it will run at 7:30 AM every day.

### Example 2: Weekday Morning, Sunday Evening

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

### Example 3: Testing Configuration

Before enabling daily briefings, test the configuration:

```bash
# 1. Validate config
python3 -m Tools.config_validator config/briefing_schedule.json

# 2. Test briefing generation
cd /path/to/project
python3 -m Tools.briefing_scheduler --mode once

# 3. Check logs
tail logs/briefing_scheduler.log

# 4. If satisfied, install
./scripts/install_briefing_systemd.sh  # or install_briefing_cron.sh
```

## Security Considerations

### User Context

Both installation methods run as **your user account**:
- Can only access files you have permission to read/write
- Runs with your environment variables
- Uses your Python installation

### Log Files

Logs are written to the project directory and may contain:
- Briefing content (tasks, commitments)
- File paths
- Error messages

Ensure proper permissions on the logs directory:

```bash
chmod 700 logs/  # Owner only
```

### Configuration

The configuration file may contain sensitive paths. Protect it:

```bash
chmod 600 config/briefing_schedule.json  # Owner read/write only
```

## Advanced Usage

### Custom Project Location

If you move the project, reinstall:

```bash
# Uninstall from old location
cd /old/path
./scripts/uninstall_briefing.sh

# Install from new location
cd /new/path
./scripts/install_briefing_systemd.sh
```

### Multiple Instances

To run briefings for multiple projects:

1. Install each project separately
2. Use different config files
3. For systemd: Create separate service/timer files with different names
4. For cron: Each project gets its own cron entry

### Running as System Service (Advanced)

For a system-wide installation (all users), adapt the systemd scripts:

```bash
# Copy service files to system location
sudo cp ~/.config/systemd/user/briefing-scheduler.* /etc/systemd/system/

# Edit to run as specific user
sudo systemctl edit briefing-scheduler.service
# Add: User=yourusername

# Enable and start
sudo systemctl enable briefing-scheduler.timer
sudo systemctl start briefing-scheduler.timer
```

## Getting Help

If you encounter issues:

1. Check the logs (see Troubleshooting section)
2. Verify configuration: `python3 -m Tools.config_validator config/briefing_schedule.json`
3. Test manually: `python3 -m Tools.briefing_scheduler --mode once`
4. Review documentation: `docs/SCHEDULER_GUIDE.md`
5. Check GitHub issues or create a new one

## Related Documentation

- **Configuration Guide**: `config/README.md`
- **Scheduler Guide**: `docs/SCHEDULER_GUIDE.md`
- **Template Customization**: `Templates/README.md`
- **Main Spec**: `.auto-claude/specs/034-automated-daily-briefing-engine/spec.md`
