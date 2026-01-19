import type { Task } from "../schema.js";

// =============================================================================
// DATE/TIME UTILITIES
// =============================================================================

/**
 * Returns the current date/time in EST timezone
 */
export function getESTNow(): Date {
  return new Date(new Date().toLocaleString("en-US", { timeZone: "America/New_York" }));
}

/**
 * Returns today's date at 00:00:00 in EST timezone
 */
export function getESTTodayStart(): Date {
  const est = getESTNow();
  est.setHours(0, 0, 0, 0);
  return est;
}

/**
 * Formats a date as YYYY-MM-DD in EST timezone
 */
export function getESTDateString(date: Date = new Date()): string {
  return date.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

/**
 * Returns yesterday's date as YYYY-MM-DD string in EST timezone
 */
export function getYesterdayDateString(): string {
  const yesterday = getESTNow();
  yesterday.setDate(yesterday.getDate() - 1);
  return getESTDateString(yesterday);
}

// =============================================================================
// FREQUENCY/STREAK UTILITIES
// =============================================================================

/**
 * Checks if a date falls on a weekday (Monday-Friday)
 */
export function isWeekday(date: Date): boolean {
  const day = date.getDay();
  return day !== 0 && day !== 6;
}

/**
 * Calculates the expected previous date based on habit frequency
 * @param frequency - The habit frequency: 'daily', 'weekdays', or 'weekly'
 * @param currentDate - The current date to calculate from
 * @returns The expected previous date string, or null if frequency is invalid
 */
export function getExpectedPreviousDate(frequency: string, currentDate: Date): string | null {
  const prev = new Date(currentDate);
  prev.setDate(prev.getDate() - 1);

  if (frequency === "daily") {
    return getESTDateString(prev);
  } else if (frequency === "weekdays") {
    // Skip weekends backwards
    while (!isWeekday(prev)) {
      prev.setDate(prev.getDate() - 1);
    }
    return getESTDateString(prev);
  } else if (frequency === "weekly") {
    // For weekly, previous expected is 7 days ago
    prev.setDate(prev.getDate() - 6); // -1 already done, so -6 more
    return getESTDateString(prev);
  }
  return null;
}

// =============================================================================
// POINTS CALCULATION
// =============================================================================

/**
 * Points mapping by value tier (must match handlers.ts POINTS_BY_TIER)
 */
const POINTS_BY_TIER: Record<string, number> = {
  checkbox: 2,
  progress: 4,
  deliverable: 6,
  milestone: 8,
};

/**
 * Calculates the points value for a task using the priority order:
 * pointsFinal > valueTier-based > pointsAiGuess > effortEstimate > default (2)
 */
export function calculatePoints(task: Task): number {
  if (task.pointsFinal != null) return task.pointsFinal;
  if (task.valueTier && POINTS_BY_TIER[task.valueTier] != null) {
    return POINTS_BY_TIER[task.valueTier];
  }
  return task.pointsAiGuess ?? task.effortEstimate ?? 2;
}

/**
 * Calculates the total points for an array of tasks
 */
export function calculateTotalPoints(tasks: Task[]): number {
  return tasks.reduce((sum, task) => sum + calculatePoints(task), 0);
}
