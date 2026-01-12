# Automated Daily Briefing - Installation Guide

This guide helps you set up automated daily briefings that run at your configured times without manual intervention.

## Quick Installation

### Step 1: Choose Your Method

**Linux Users (Recommended):**
```bash
./scripts/install_briefing_systemd.sh
```

**macOS Users or Linux Alternative:**
```bash
./scripts/install_briefing_cron.sh
```

### Step 2: Configure Your Schedule

Edit the configuration file to set your preferred times:

```bash
vim config/briefing_schedule.json
```

Example configuration:
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

### Step 3: Wait for Your First Briefing

The scheduler will automatically run at your configured times. Check the logs:

```bash
tail -f logs/briefing_scheduler.log
```

## What Gets Installed

### Cron Installation
- ✓ Adds entry to your user crontab (runs every minute)
- ✓ Creates log directory: `logs/`
- ✓ Logs to: `logs/briefing_scheduler.log` and `logs/cron.log`
- ✓ No system-wide changes

### Systemd Installation
- ✓ Creates user service: `~/.config/systemd/user/briefing-scheduler.service`
- ✓ Creates user timer: `~/.config/systemd/user/briefing-scheduler.timer`
- ✓ Creates log directory: `logs/`
- ✓ Logs to: `logs/briefing_scheduler.log` and journalctl
- ✓ No system-wide changes

## Requirements Validation

Both installation scripts automatically validate:

- ✅ Python 3.7+ is installed
- ✅ Project structure is correct (State/, Templates/, config/)
- ✅ Required Python modules can be imported
- ✅ Log directory can be created
- ✅ (Optional) Jinja2 for template rendering

If any requirement fails, the script will stop and show a clear error message.

## Uninstallation

To remove the scheduler:

```bash
# Remove everything
./scripts/uninstall_briefing.sh

# Remove only cron
./scripts/uninstall_briefing.sh --cron

# Remove only systemd
./scripts/uninstall_briefing.sh --systemd
```

The uninstall script:
- ✅ Stops all running services/timers
- ✅ Removes cron entries
- ✅ Removes systemd service/timer files
- ✅ Optionally removes logs and run state
- ✅ Preserves configuration and State files

## Troubleshooting

### Briefing Not Running?

1. **Check if installed:**
   ```bash
   # For cron
   crontab -l | grep briefing

   # For systemd
   systemctl --user status briefing-scheduler.timer
   ```

2. **Check configuration:**
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

**"Python not found"**
- Install Python 3.7+ and ensure it's in your PATH
- On macOS: `brew install python3`
- On Linux: `sudo apt-get install python3` or `sudo yum install python3`

**"Failed to import BriefingScheduler"**
- Check that you're in the correct directory
- Verify all project files are present: `ls Tools/briefing_scheduler.py`

**"Jinja2 not installed"**
- This is optional but recommended
- Install: `pip3 install jinja2`
- Briefings will work without it (using fallback rendering)

**"Permission denied"**
- Ensure scripts are executable: `chmod +x scripts/*.sh`
- Check log directory permissions: `chmod 755 logs/`

## Management Commands

### Systemd (Linux)

```bash
# View status
systemctl --user status briefing-scheduler.timer
systemctl --user status briefing-scheduler.service

# View logs (live)
journalctl --user -u briefing-scheduler.service -f

# Stop/Start
systemctl --user stop briefing-scheduler.timer
systemctl --user start briefing-scheduler.timer

# Disable/Enable
systemctl --user disable briefing-scheduler.timer
systemctl --user enable briefing-scheduler.timer

# Manual trigger
systemctl --user start briefing-scheduler.service
```

### Cron (macOS/Linux)

```bash
# View crontab
crontab -l

# Edit crontab
crontab -e

# View logs
tail -f logs/briefing_scheduler.log
tail -f logs/cron.log

# Manual trigger
cd /path/to/project && python3 -m Tools.briefing_scheduler --mode once
```

## Next Steps

After installation:

1. **Customize Templates**: Edit `Templates/briefing_morning.md` and `Templates/briefing_evening.md`
2. **Adjust Configuration**: Modify `config/briefing_schedule.json` for your preferences
3. **Set Delivery Channels**: Choose CLI, file, or notifications
4. **Test It**: Wait for your first scheduled briefing or run manually

## Documentation

- **Full Installation Guide**: `scripts/README.md`
- **Configuration Guide**: `config/README.md`
- **Scheduler Guide**: `docs/SCHEDULER_GUIDE.md`
- **Template Customization**: `Templates/README.md`

## Security Notes

- All operations run as your user (no sudo required)
- Scripts only access files in the project directory
- Logs may contain task/commitment data - protect with `chmod 700 logs/`
- Configuration is user-specific - not shared across accounts

## Getting Help

If you encounter issues:

1. Check the logs (see Troubleshooting above)
2. Validate configuration: `python3 -m Tools.config_validator config/briefing_schedule.json`
3. Test manually: `python3 -m Tools.briefing_scheduler --mode once`
4. Review detailed docs: `scripts/README.md`
5. Check existing GitHub issues or create a new one

---

**Questions?** See `scripts/README.md` for detailed documentation.
