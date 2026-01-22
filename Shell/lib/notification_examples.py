#!/usr/bin/env python3
"""
Real-world examples of using the Thanos Notification System.

These examples demonstrate common use cases and integration patterns.
"""

from notifications import notify, NotificationRouter

# ============================================================================
# Example 1: Task Completion Notification
# ============================================================================

def notify_task_completed(task_title: str, points_earned: int):
    """Send notification when a task is completed."""
    notify(
        title="Task Complete",
        message=f"'{task_title}' finished. +{points_earned} points earned.",
        priority="info"
    )


# ============================================================================
# Example 2: Energy Level Alert
# ============================================================================

def notify_low_energy(readiness_score: int):
    """Alert user when energy level is low."""
    if readiness_score < 60:
        notify(
            title="Low Energy Detected",
            message=f"Readiness: {readiness_score}/100. Consider lighter tasks or rest.",
            priority="warning"
        )


# ============================================================================
# Example 3: Daily Goal Achieved
# ============================================================================

def notify_daily_goal_achieved(points_today: int, target: int):
    """Celebrate reaching daily goal."""
    notify(
        title="Daily Goal Complete",
        message=f"You've earned {points_today}/{target} points today. Well done!",
        priority="info"
    )


# ============================================================================
# Example 4: System Daemon Failure
# ============================================================================

def notify_daemon_crashed(daemon_name: str, error_msg: str):
    """Alert on critical system failure."""
    notify(
        title=f"{daemon_name} Crashed",
        message=f"Daemon failed: {error_msg}\nImmediate attention required.",
        priority="critical",
        force=True  # Bypass rate limiting for critical system alerts
    )


# ============================================================================
# Example 5: Habit Streak Milestone
# ============================================================================

def notify_habit_milestone(habit_name: str, streak_days: int):
    """Celebrate habit streak milestones."""
    milestones = [7, 14, 30, 60, 90, 100, 365]

    if streak_days in milestones:
        notify(
            title="Habit Milestone",
            message=f"{habit_name}: {streak_days} day streak! Keep it up.",
            priority="info"
        )


# ============================================================================
# Example 6: Brain Dump Processed
# ============================================================================

def notify_brain_dump_processed(content: str, classification: str, routing: str):
    """Notify when brain dump has been classified and routed."""
    notify(
        title="Brain Dump Processed",
        message=f"'{content[:50]}...' classified as {classification}, routed to {routing}",
        priority="info"
    )


# ============================================================================
# Example 7: Meeting Reminder
# ============================================================================

def notify_meeting_soon(meeting_title: str, minutes_until: int):
    """Remind about upcoming meeting."""
    if minutes_until <= 5:
        priority = "warning"
    else:
        priority = "info"

    notify(
        title="Meeting Soon",
        message=f"'{meeting_title}' starts in {minutes_until} minutes",
        priority=priority
    )


# ============================================================================
# Example 8: Telegram Bot Integration
# ============================================================================

def notify_from_telegram_bot(user_id: int, action: str, details: str):
    """Send notification triggered by Telegram bot interaction."""
    notify(
        title=f"Telegram: {action}",
        message=f"User {user_id}: {details}",
        priority="info"
    )


# ============================================================================
# Example 9: Batch Processing with Rate Limiting
# ============================================================================

def notify_batch_results(items_processed: int, items_failed: int):
    """Notify about batch processing results, respecting rate limits."""
    # Only send if there are failures (avoid spam for successful batches)
    if items_failed > 0:
        notify(
            title="Batch Processing Complete",
            message=f"Processed: {items_processed}, Failed: {items_failed}",
            priority="warning"
        )


# ============================================================================
# Example 10: Custom Router for Background Service
# ============================================================================

class BackgroundServiceNotifier:
    """
    Example of creating a custom notifier for a long-running service.

    Maintains single router instance to preserve rate limiting and
    deduplication state across notifications.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.router = NotificationRouter()

    def notify_startup(self):
        """Service started."""
        self.router.send(
            title=f"{self.service_name} Started",
            message="Service initialized successfully",
            priority="info"
        )

    def notify_error(self, error: Exception):
        """Service error occurred."""
        self.router.send(
            title=f"{self.service_name} Error",
            message=str(error),
            priority="warning"
        )

    def notify_shutdown(self):
        """Service stopped."""
        self.router.send(
            title=f"{self.service_name} Stopped",
            message="Service shutdown gracefully",
            priority="info"
        )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=== Notification System Examples ===\n")

    # Example 1: Task completion
    print("1. Task completion:")
    notify_task_completed("Review pull request #42", points_earned=4)

    # Example 2: Low energy alert
    print("\n2. Low energy alert:")
    notify_low_energy(readiness_score=55)

    # Example 3: Daily goal
    print("\n3. Daily goal achieved:")
    notify_daily_goal_achieved(points_today=18, target=18)

    # Example 5: Habit milestone
    print("\n4. Habit milestone:")
    notify_habit_milestone("Morning meditation", streak_days=30)

    # Example 7: Meeting reminder
    print("\n5. Meeting reminder:")
    notify_meeting_soon("Sprint Planning", minutes_until=5)

    # Example 10: Background service
    print("\n6. Background service notifier:")
    service = BackgroundServiceNotifier("Vigilance Daemon")
    service.notify_startup()

    print("\n=== Examples Complete ===")
