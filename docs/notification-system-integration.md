# Notification System Integration Guide

## Overview

The enhanced notification system (`Shell/lib/notifications.py`) can be integrated throughout Thanos for unified alert delivery.

## Integration with Telegram Bot

The existing Telegram bot (`Tools/telegram_bot.py`) can use the notification system to send alerts:

### Example: Brain Dump Captured

```python
# In Tools/telegram_bot.py

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "Shell" / "lib"))
from notifications import notify

# After capturing brain dump
entry = await self.capture_entry(content, 'text', user_id)

# Send confirmation notification via unified system
notify(
    title="Brain Dump Captured",
    message=f"{entry.classification} captured and routed successfully",
    priority="info"
)
```

### Example: Command Query Results

```python
# In Telegram bot command handlers

async def handle_command(self, command_type: str, params: dict) -> str:
    try:
        response = await self._get_tasks_response('active')

        # Also send notification for important queries
        if command_type in ['health', 'status']:
            notify(
                title=f"Telegram Query: {command_type}",
                message="Query processed successfully",
                priority="info"
            )

        return response
    except Exception as e:
        # Send error notification
        notify(
            title="Telegram Bot Error",
            message=f"Failed to handle {command_type}: {str(e)}",
            priority="warning"
        )
        raise
```

## Integration with Daily Brief

The daily brief tool can use notifications to alert when the brief is ready:

```typescript
// In tools/daily-brief.ts

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function sendNotification(title: string, message: string, priority: string) {
  const command = `python3 Shell/lib/notifications.py ${priority} "${title}" "${message}"`;
  await execAsync(command);
}

// After generating daily brief
await generateDailyBrief();

await sendNotification(
  "Daily Brief Ready",
  "Your morning brief has been generated and saved",
  "info"
);
```

## Integration with WorkOS MCP

The WorkOS MCP server can send notifications for important events:

```typescript
// In mcp-servers/workos-mcp/src/index.ts

import { exec } from 'child_process';

function notifyTaskComplete(taskTitle: string, pointsEarned: number) {
  const command = `python3 ../../Shell/lib/notifications.py info "Task Complete" "${taskTitle} (+${pointsEarned} points)"`;
  exec(command, (error) => {
    if (error) {
      console.error('Notification failed:', error);
    }
  });
}

// In task completion handler
async workos_complete_task(args) {
  const result = await completeTask(args.taskId);

  // Send notification
  notifyTaskComplete(result.title, result.points_earned);

  return result;
}
```

## Integration with Energy Monitoring

Monitor energy levels and send alerts when low:

```python
# In Tools/energy_monitor.py

from Shell.lib.notifications import notify
import os

def check_oura_readiness():
    """Check Oura readiness and alert if low."""
    # Get readiness from Oura cache
    readiness = get_readiness_score()

    if readiness < 60:
        notify(
            title="Low Energy Alert",
            message=f"Readiness: {readiness}/100. Consider lighter tasks or rest.",
            priority="warning"
        )
    elif readiness >= 85:
        notify(
            title="High Energy",
            message=f"Readiness: {readiness}/100. Great day for deep work!",
            priority="info"
        )
```

## Integration with Habit Tracking

Celebrate habit milestones:

```python
# In habit completion handler

from Shell.lib.notifications import notify

def on_habit_completed(habit_name: str, new_streak: int):
    """Called when habit is marked complete."""

    # Check for milestone streaks
    milestones = [7, 14, 30, 60, 90, 100, 365]

    if new_streak in milestones:
        notify(
            title="Habit Milestone",
            message=f"🔥 {habit_name}: {new_streak} day streak!",
            priority="info"
        )
```

## Integration with System Daemons

Background services can use notifications for health monitoring:

```python
# In daemon script (e.g., vigilance daemon)

from Shell.lib.notifications import NotificationRouter
import time

class VigilanceDaemon:
    def __init__(self):
        # Create single router instance for the daemon lifetime
        self.notifier = NotificationRouter()

    def start(self):
        """Start the daemon."""
        self.notifier.send(
            title="Vigilance Daemon Started",
            message="System monitoring active",
            priority="info"
        )

        while self.running:
            try:
                self.check_system_health()
            except Exception as e:
                self.notifier.send(
                    title="Daemon Error",
                    message=str(e),
                    priority="critical",
                    force=True  # Critical errors bypass rate limiting
                )

    def check_system_health(self):
        """Monitor system health."""
        # Check various metrics
        if cpu_usage > 90:
            self.notifier.send(
                title="High CPU Usage",
                message=f"CPU: {cpu_usage}%",
                priority="warning"
            )
```

## Integration with Task Completion

Celebrate task completions:

```python
# In task completion handler

from Shell.lib.notifications import notify

def on_task_completed(task_id: int):
    """Called when a task is marked complete."""

    task = get_task(task_id)

    # Send notification
    notify(
        title="Task Complete",
        message=f"{task.title} (+{task.points} points)",
        priority="info"
    )

    # Check if daily goal achieved
    if check_daily_goal_achieved():
        notify(
            title="Daily Goal Achieved",
            message=f"You've earned your {get_daily_target()} points today!",
            priority="info"
        )
```

## Best Practices

### 1. Use Single Router Instance for Long-Running Services

```python
# Good: Maintains rate limiting and deduplication state
class MyDaemon:
    def __init__(self):
        self.notifier = NotificationRouter()

    def send_alert(self, title, message):
        self.notifier.send(title, message, "warning")

# Bad: Creates new router for each notification (loses state)
def send_alert(title, message):
    notify(title, message, "warning")  # OK for one-off scripts
```

### 2. Choose Appropriate Priority Levels

```python
# Info: Routine updates (macOS only)
notify("Task Complete", "Review finished", priority="info")

# Warning: Important but not urgent (macOS + Telegram)
notify("Low Energy", "Readiness: 55", priority="warning")

# Critical: Urgent attention needed (all channels including voice)
notify("System Failure", "Daemon crashed", priority="critical")
```

### 3. Use Force Flag for Critical System Alerts

```python
# Critical system alerts should bypass rate limiting
notify(
    title="Database Connection Lost",
    message="Unable to connect to database. Immediate attention required.",
    priority="critical",
    force=True  # Bypass rate limiting for critical alerts
)
```

### 4. Use Dry-Run for Testing

```python
# Test notifications without actually sending
notify(
    title="Test Alert",
    message="Testing notification system",
    priority="info",
    dry_run=True
)
```

## Example: Complete Integration

Here's a complete example showing integration across multiple Thanos components:

```python
#!/usr/bin/env python3
"""
Thanos Event Notifier - Unified notification integration.
"""

from Shell.lib.notifications import NotificationRouter
from typing import Dict, Any

class ThanosNotifier:
    """Centralized notification hub for Thanos."""

    def __init__(self):
        self.router = NotificationRouter()

    # Task Events
    def task_completed(self, task_title: str, points: int):
        self.router.send(
            title="Task Complete",
            message=f"{task_title} (+{points} points)",
            priority="info"
        )

    # Energy Events
    def energy_alert(self, readiness: int):
        if readiness < 60:
            self.router.send(
                title="Low Energy",
                message=f"Readiness: {readiness}/100. Take it easy.",
                priority="warning"
            )

    # Habit Events
    def habit_milestone(self, habit: str, streak: int):
        if streak in [7, 14, 30, 60, 90]:
            self.router.send(
                title="Habit Milestone",
                message=f"🔥 {habit}: {streak} day streak!",
                priority="info"
            )

    # System Events
    def system_error(self, component: str, error: str):
        self.router.send(
            title=f"{component} Error",
            message=error,
            priority="critical",
            force=True
        )

    # Brain Dump Events
    def brain_dump_captured(self, classification: str):
        self.router.send(
            title="Brain Dump Captured",
            message=f"{classification} captured and routed",
            priority="info"
        )

# Global instance
_notifier = None

def get_notifier() -> ThanosNotifier:
    """Get global notifier instance."""
    global _notifier
    if _notifier is None:
        _notifier = ThanosNotifier()
    return _notifier
```

## Testing Integration

Test your integration:

```bash
# Test notification system
python3 Shell/lib/test_notifications.py

# Test with dry-run
python3 Shell/lib/notifications.py --dry-run info "Test" "Testing integration"

# Test actual notification
python3 Shell/lib/notifications.py info "Integration Test" "System working correctly"
```

## Troubleshooting

### Import Errors

If you get import errors, add the Shell/lib directory to Python path:

```python
import sys
from pathlib import Path

# Add Shell/lib to path
shell_lib = Path(__file__).parent.parent / "Shell" / "lib"
sys.path.insert(0, str(shell_lib))

from notifications import notify
```

### Telegram Not Sending

Check environment variables:
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID
```

### Rate Limiting Issues

Use `force=True` for critical alerts that must send immediately:
```python
notify(title="Critical", message="Must send", priority="critical", force=True)
```

## Conclusion

The unified notification system provides a consistent interface for alerts across all Thanos components. Use it to:

- Notify on task completion
- Alert on low energy
- Celebrate habit milestones
- Monitor system health
- Confirm brain dump captures
- Send meeting reminders

For more examples, see `Shell/lib/notification_examples.py`.
