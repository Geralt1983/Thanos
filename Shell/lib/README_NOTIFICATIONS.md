# Thanos Unified Notification System

Production-ready notification system for macOS and Telegram with advanced features.

## Features

- **Multi-Channel Delivery**: macOS Notification Center, Telegram, and Voice Alerts
- **Priority-Based Routing**: Automatically route to appropriate channels based on severity
- **Rate Limiting**: Max 10 notifications per minute to prevent spam
- **Deduplication**: Suppress duplicate notifications within 5-minute window
- **Automatic Retry**: 3 attempts with 2-second delays for failed sends
- **Dry-Run Mode**: Test notifications without actually sending
- **Comprehensive Logging**: Track all notification activity

## Priority Routing

| Priority  | Channels                                  | Use Case                    |
|-----------|------------------------------------------|-----------------------------|
| `info`    | macOS Notification Center only           | Completed tasks, status updates |
| `warning` | macOS + Telegram                         | Low energy, missed deadlines |
| `critical`| macOS + Telegram + Voice Alert           | System failures, urgent alerts |

## Installation

The notification system is already installed in Thanos at `Shell/lib/notifications.py`.

### Dependencies

```bash
pip install requests  # For Telegram API
```

### Configuration

Set environment variables:

```bash
# Required for Telegram notifications
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

## Usage

### Command Line Interface

```bash
# Basic usage
python3 Shell/lib/notifications.py <priority> <title> <message>

# Info notification (macOS only)
python3 Shell/lib/notifications.py info "Task Complete" "Code review finished"

# Warning (macOS + Telegram)
python3 Shell/lib/notifications.py warning "Low Energy" "Readiness score: 45"

# Critical alert (all channels)
python3 Shell/lib/notifications.py critical "System Alert" "Daemon crashed"

# Test with dry-run
python3 Shell/lib/notifications.py --dry-run critical "Test" "Won't actually send"

# Force send (bypass rate limiting and deduplication)
python3 Shell/lib/notifications.py --force info "Important" "Send immediately"

# Add subtitle (macOS only)
python3 Shell/lib/notifications.py --subtitle "Details" info "Title" "Message"
```

### Python API

```python
from Shell.lib.notifications import notify, NotificationRouter

# Simple usage
notify(
    title="Task Complete",
    message="Code review finished",
    priority="info"
)

# Advanced usage with all options
notify(
    title="System Alert",
    message="Daemon crashed - immediate attention required",
    priority="critical",
    subtitle="Error Details",
    force=True,      # Skip rate limiting and deduplication
    dry_run=False    # Actually send the notification
)

# Create custom router instance
router = NotificationRouter(
    telegram_token="custom_token",
    telegram_chat_id="custom_chat",
    dry_run=True
)

results = router.send(
    title="Custom Notification",
    message="Using custom router",
    priority="warning"
)

# Check results
if results.get("skipped"):
    print(f"Notification skipped: {results['skipped']}")
else:
    successful_channels = [k for k in results if results[k] and k != 'skipped']
    print(f"Sent via: {successful_channels}")
```

## Rate Limiting

Prevents notification spam by enforcing a maximum of **10 notifications per minute**.

When rate limit is exceeded:
- Notification is dropped
- Warning logged
- `skipped='rate_limit_exceeded'` returned

**Bypass**: Use `--force` flag or `force=True` parameter.

## Deduplication

Prevents sending the same notification multiple times within a **5-minute window**.

How it works:
- Creates MD5 hash of `title:message`
- Tracks recent notifications
- Suppresses duplicates automatically

When duplicate detected:
- Notification is skipped
- Debug message logged
- `skipped='duplicate'` returned

**Bypass**: Use `--force` flag or `force=True` parameter.

## Retry Logic

Automatically retries failed sends up to **3 times** with **2-second delays**.

Retries are applied to:
- macOS notifications (osascript failures)
- Telegram API calls (network errors)
- Voice alerts (synthesis failures)

## Dry-Run Mode

Test notifications without actually sending them.

```bash
# CLI
python3 Shell/lib/notifications.py --dry-run info "Test" "Message"

# Python
notify(title="Test", message="Message", priority="info", dry_run=True)
```

In dry-run mode:
- All checks (rate limiting, deduplication) still apply
- Notifications are logged but not sent
- Returns simulated success for all channels

## Integration Examples

### Shell Script

```bash
#!/bin/bash
# Send notification from shell script

python3 Shell/lib/notifications.py info "Backup Complete" "All files backed up successfully"
```

### Python Daemon

```python
import time
from Shell.lib.notifications import NotificationRouter

# Create single router instance (maintains rate limiting and deduplication)
router = NotificationRouter()

while True:
    try:
        # Monitor system health
        if check_system_health():
            router.send("Health Check", "All systems operational", "info")
        else:
            router.send("Health Alert", "System degraded", "warning")
    except Exception as e:
        router.send("Daemon Error", str(e), "critical")

    time.sleep(60)
```

### Integration with Existing Telegram Bot

The notification system uses the Telegram API directly. To integrate with the existing Telegram bot in `Tools/telegram_bot.py`:

```python
# In Tools/telegram_bot.py
from Shell.lib.notifications import notify

# Send notification via unified system
notify(
    title="Brain Dump Captured",
    message=f"New {category} captured successfully",
    priority="info"
)
```

## Testing

Run the comprehensive test suite:

```bash
python3 Shell/lib/test_notifications.py
```

Tests cover:
- Deduplication logic
- Rate limiting enforcement
- Priority routing
- Retry mechanism

## Troubleshooting

### Telegram notifications not sending

Check configuration:
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

Test Telegram API manually:
```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\": \"$TELEGRAM_CHAT_ID\", \"text\": \"Test\"}"
```

### macOS notifications not appearing

Check permissions:
- System Settings → Notifications → Terminal (or your terminal app)
- Ensure notifications are enabled

Test manually:
```bash
osascript -e 'display notification "Test" with title "Test Title"'
```

### Voice alerts not working

Ensure voice synthesis module exists:
```bash
ls Shell/lib/voice.py
```

Check voice.py implementation for dependencies.

## Architecture

```
NotificationRouter
├── Rate Limiting (deque of timestamps)
├── Deduplication (hash → timestamp map)
├── Channel Routing
│   ├── macOS (osascript)
│   ├── Telegram (API)
│   └── Voice (synthesis module)
└── Retry Logic (3 attempts, 2s delay)
```

## Future Enhancements

- [ ] Persistent rate limiting across process restarts
- [ ] Custom notification templates
- [ ] Batch notification support
- [ ] Webhook integration
- [ ] Discord/Slack channel support
- [ ] Email notifications for critical alerts
- [ ] Notification history/audit log

## Related Files

- `Shell/lib/notifications.py` - Main implementation
- `Shell/lib/voice.py` - Voice synthesis module
- `Shell/lib/test_notifications.py` - Test suite
- `Tools/telegram_bot.py` - Telegram bot integration

## Support

For issues or questions, check the logs:
```bash
# Notification logs use the 'thanos.notifications' logger
# Set logging level in your application or via environment
export PYTHONLOGLEVEL=DEBUG
```
