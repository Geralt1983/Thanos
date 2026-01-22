# Operator Alerters

**Implementation Status:** ✅ Complete
**Date:** 2026-01-20
**Phase:** Thanos v2.0 Phase 3 - Operator Daemon

---

## Overview

Alerters send notifications through various channels when monitors detect issues requiring attention. All alerters implement a common interface and handle errors gracefully without raising exceptions.

### Available Alerters

| Alerter | Channel | Use Case | Default Min Severity |
|---------|---------|----------|---------------------|
| **TelegramAlerter** | Telegram Bot API | Mobile alerts with retry | `warning` |
| **NotificationAlerter** | macOS Notification Center | Desktop alerts with sound | `warning` |
| **JournalAlerter** | Database + fallback file | Audit trail (always on) | `info` (all) |

---

## Architecture

### Base Interface

All alerters implement `AlerterInterface`:

```python
class AlerterInterface(ABC):
    @abstractmethod
    async def send(self, alert: Alert) -> bool:
        """Send alert. Returns True if successful, False otherwise."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if alerter is configured and ready."""
        pass

    def should_send(self, alert: Alert) -> bool:
        """Check if alert meets severity threshold."""
        pass
```

### Alert Data Structure

```python
@dataclass
class Alert:
    title: str              # Alert title
    message: str            # Alert body
    severity: AlertSeverity # info|warning|high|critical
    source_type: str        # health|task|pattern
    source_id: Optional[str]
    timestamp: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    dedup_key: Optional[str]  # For deduplication
```

---

## TelegramAlerter

Sends alerts via Telegram Bot API with Thanos voice formatting.

### Features

- **Severity-based emoji prefixes**: 🔴 🟠 ⚠️ ℹ️
- **Markdown formatting** with bold titles
- **Thanos quotes** for critical alerts
- **Rate limiting**: Max 1 message per minute
- **Retry logic**: 3 attempts with exponential backoff
- **Timeout**: 10 seconds per request

### Configuration

```python
from Operator.alerters import TelegramAlerter, Alert

alerter = TelegramAlerter(
    token="123456:ABC-DEF...",      # Or TELEGRAM_BOT_TOKEN env var
    chat_id="987654321",            # Or TELEGRAM_CHAT_ID env var
    min_severity="warning",         # info|warning|high|critical
    dry_run=False                   # Or OPERATOR_DRY_RUN env var
)
```

### Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
export OPERATOR_DRY_RUN="false"  # Set to "true" to disable sending
```

### Example Message Format

```
🔴 CRITICAL: Low Readiness

Your readiness is 48. You're at risk of burnout. Rest today.

Source: health monitor
Time: 2026-01-20 14:30:00

Dread it. Run from it. Destiny arrives all the same.
```

### Error Handling

- **No token/chat_id**: Alerter disabled, logs warning
- **Network timeout**: Retries with backoff (1s, 2s, 4s)
- **4xx errors**: No retry (bad request/auth)
- **5xx errors**: Retries up to 3 times
- **Rate limited**: Skips alert, logs warning

---

## NotificationAlerter

Sends native macOS notifications via `osascript`.

### Features

- **Native Notification Center** integration
- **Severity-based sounds**:
  - `info`: "Glass"
  - `warning`: "Basso"
  - `high`: "Funk"
  - `critical`: "Sosumi"
- **Platform detection**: Auto-disables on non-macOS
- **Timeout**: 5 seconds for osascript

### Configuration

```python
from Operator.alerters import NotificationAlerter

alerter = NotificationAlerter(
    min_severity="warning",   # Only send warning/high/critical
    dry_run=False
)
```

### Example

```python
alert = Alert(
    title="Deadline Alert",
    message="3 tasks due today",
    severity="high",
    source_type="task"
)

success = await alerter.send(alert)
```

### Error Handling

- **Non-macOS platform**: Alerter disabled automatically
- **osascript not found**: Returns False, logs error
- **Command timeout**: Kills process, returns False
- **Command failure**: Returns False, logs stderr

---

## JournalAlerter

Logs all alerts to database with fallback to file logging. **Never fails.**

### Features

- **Append-only audit trail** in `thanos_unified.db`
- **Fallback to file logging** if database unavailable
- **Never fails**: Always returns True
- **Logs all severities** (no filtering)
- **Full metadata capture**

### Configuration

```python
from Operator.alerters import JournalAlerter

alerter = JournalAlerter(
    thanos_root="/Users/jeremy/Projects/Thanos",  # Or THANOS_ROOT env var
    dry_run=False
)
```

### Database Schema

Logs to `journal` table via `Tools/journal.py`:

```sql
INSERT INTO journal (
    timestamp, event_type, source, severity,
    title, data, session_id, agent
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
```

### Fallback Logging

If database unavailable, logs to `logs/operator_alerts.log`:

```json
{"timestamp": "2026-01-20T14:30:00", "severity": "critical", "title": "...", ...}
```

### Error Handling

- **Database unavailable**: Falls back to file logging
- **File logging fails**: Logs to Python logger
- **All logging fails**: Still returns True (prevents cascading failures)

---

## Usage Examples

### Basic Usage

```python
from Operator.alerters import TelegramAlerter, NotificationAlerter, JournalAlerter, Alert

# Initialize alerters
telegram = TelegramAlerter(min_severity="warning")
notification = NotificationAlerter(min_severity="high")
journal = JournalAlerter()  # Always logs everything

# Create alert
alert = Alert(
    title="Low Readiness",
    message="Your readiness is 58. Take it easy today.",
    severity="warning",
    source_type="health",
    source_id="readiness_check"
)

# Send to all enabled alerters
results = await asyncio.gather(
    telegram.send(alert),
    notification.send(alert),
    journal.send(alert)
)

print(f"Sent: {sum(results)}/{len(results)} alerters")
```

### Routing by Severity

```python
async def route_alert(alert: Alert):
    """Route alert to appropriate channels based on severity."""

    # Journal: Always log
    await journal.send(alert)

    # Telegram: warning and above
    if alert.severity in ["warning", "high", "critical"]:
        await telegram.send(alert)

    # macOS: high and critical only
    if alert.severity in ["high", "critical"]:
        await notification.send(alert)
```

### Dry-Run Testing

```python
# Test without sending
telegram = TelegramAlerter(dry_run=True)
notification = NotificationAlerter(dry_run=True)
journal = JournalAlerter(dry_run=True)

alert = Alert(
    title="Test Alert",
    message="This won't actually send",
    severity="info",
    source_type="test"
)

await telegram.send(alert)  # Logs to console instead
```

---

## Testing

### Run All Tests

```bash
# Dry-run mode (no actual sending)
python3 Operator/alerters/test_alerters.py

# Test specific alerter
python3 Operator/alerters/test_alerters.py --alerter telegram
python3 Operator/alerters/test_alerters.py --alerter notification
python3 Operator/alerters/test_alerters.py --alerter journal

# Actual sending (requires credentials)
python3 Operator/alerters/test_alerters.py --no-dry-run
```

### Manual Testing

```python
import asyncio
from Operator.alerters import TelegramAlerter, Alert

async def test():
    alerter = TelegramAlerter(dry_run=True)

    alert = Alert(
        title="Test",
        message="Hello from Operator",
        severity="info",
        source_type="test"
    )

    success = await alerter.send(alert)
    print(f"Success: {success}")

asyncio.run(test())
```

---

## Integration with Daemon

The Operator daemon uses all three alerters:

```python
# In daemon.py
from Operator.alerters import TelegramAlerter, NotificationAlerter, JournalAlerter

# Initialize from config
telegram = TelegramAlerter(
    min_severity=config.alerters.telegram.min_priority
)
notification = NotificationAlerter(
    min_severity=config.alerters.macos.min_priority
)
journal = JournalAlerter()

# Send alerts
async def send_alerts(alerts: List[Alert]):
    for alert in alerts:
        # Journal: Always log
        await journal.send(alert)

        # Send to other channels based on their filtering
        await asyncio.gather(
            telegram.send(alert),
            notification.send(alert)
        )
```

---

## Error Handling Philosophy

**All alerters follow these principles:**

1. **Never raise exceptions** - Return False instead
2. **Log all errors** - Use Python logger for diagnostics
3. **Graceful degradation** - Continue operating when services unavailable
4. **Fail-safe defaults** - Prefer working with degraded functionality over crashing

### Example Error Flow

```
Telegram API call fails
  ↓
Retry with exponential backoff (3 attempts)
  ↓
Log error to Python logger
  ↓
Return False (alert not sent)
  ↓
Daemon continues with next alert
  ↓
Journal still logs for audit trail
```

---

## Performance Characteristics

| Alerter | Typical Latency | Failure Mode | Recovery |
|---------|----------------|--------------|----------|
| **Telegram** | 200-500ms (network) | Retry 3x, then fail | Auto-retry next cycle |
| **Notification** | 50-100ms (osascript) | Fail immediately | N/A (local) |
| **Journal** | 5-10ms (SQLite) | Fallback to file | Auto-recover when DB available |

---

## Dependencies

```python
# Required
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
import asyncio
import logging
import os

# Optional (feature flags)
import httpx  # For TelegramAlerter (pip install httpx)
```

### Install Dependencies

```bash
pip install httpx  # For Telegram support
```

---

## Future Enhancements

- [ ] Email alerter for critical alerts
- [ ] Slack integration
- [ ] Voice alerts (text-to-speech)
- [ ] Custom alert templates
- [ ] Alert batching for rate limiting
- [ ] Alert priority queue
- [ ] Webhook alerter for custom integrations

---

## Files

```
Operator/alerters/
├── __init__.py           # Exports all alerters
├── base.py               # Base interface and Alert class
├── telegram.py           # Telegram Bot API alerter
├── notification.py       # macOS Notification Center alerter
├── journal.py            # Database/file logging alerter
├── test_alerters.py      # Test suite
└── README.md             # This file
```

---

## Summary

All three alerters are implemented and tested:

- ✅ **TelegramAlerter**: Mobile alerts with retry and Thanos voice
- ✅ **NotificationAlerter**: Native macOS notifications with sound
- ✅ **JournalAlerter**: Audit trail with fallback logging

**Status**: Ready for integration with Operator daemon monitors.
