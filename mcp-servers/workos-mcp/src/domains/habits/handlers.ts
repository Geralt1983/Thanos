import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import {
  getESTNow,
  getESTTodayStart,
  getESTDateString,
  getYesterdayDateString,
  isWeekday,
  getExpectedPreviousDate,
} from "../../shared/utils.js";
import * as schema from "../../schema.js";
import { eq, and, gte, lte, desc, asc } from "drizzle-orm";
import {
  getCachedHabits,
  isCacheStale,
} from "../../cache/cache.js";

// =============================================================================
// HABIT DOMAIN HANDLERS
// =============================================================================

// Track cache initialization for read operations
let cacheInitialized = false;

/**
 * Ensure cache is initialized
 * @returns Promise<boolean> true if cache is available
 */
async function ensureCache(): Promise<boolean> {
  if (!cacheInitialized) {
    try {
      const { initCache, getCacheStats } = await import("../../cache/cache.js");
      const { syncAll } = await import("../../cache/sync.js");

      initCache();
      cacheInitialized = true;
      console.error("[Cache] SQLite cache initialized");

      // Check if cache is empty or stale
      const stats = getCacheStats();
      if (stats.habitCount === 0 || stats.isStale) {
        console.error("[Cache] Cache empty or stale, syncing from Neon...");
        await syncAll();
      }
    } catch (error) {
      console.error("[Cache] Failed to initialize cache:", error);
      return false;
    }
  }
  return true;
}

/**
 * Handler: workos_get_habits
 * Get all active habits with their current streaks
 */
export async function handleGetHabits(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  // Try cache first
  const cacheAvailable = await ensureCache();
  if (cacheAvailable && !isCacheStale()) {
    try {
      const cachedHabits = getCachedHabits();
      console.error(`[Cache] Served ${cachedHabits.length} habits from cache`);
      return {
        content: [{ type: "text", text: JSON.stringify(cachedHabits, null, 2) }],
      };
    } catch (cacheError) {
      console.error("[Cache] Error reading from cache, falling back to Neon:", cacheError);
    }
  }

  // Fallback to Neon
  const habits = await db
    .select()
    .from(schema.habits)
    .where(eq(schema.habits.isActive, 1))
    .orderBy(asc(schema.habits.sortOrder));

  return {
    content: [{ type: "text", text: JSON.stringify(habits, null, 2) }],
  };
}

/**
 * Handler: workos_create_habit
 * Create a new habit to track
 */
export async function handleCreateHabit(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { name, description, emoji, frequency = "daily", targetCount = 1, timeOfDay = "anytime", category } = args as any;

  const [newHabit] = await db
    .insert(schema.habits)
    .values({
      name,
      description: description || null,
      emoji: emoji || null,
      frequency,
      targetCount,
      timeOfDay,
      category: category || null,
    })
    .returning();

  return {
    content: [{ type: "text", text: JSON.stringify({ success: true, habit: newHabit }, null, 2) }],
  };
}

/**
 * Handler: workos_complete_habit
 * Mark a habit as completed for today
 */
export async function handleCompleteHabit(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { habitId, note } = args as any;

  // Get habit first
  const [habit] = await db
    .select()
    .from(schema.habits)
    .where(eq(schema.habits.id, habitId));

  if (!habit) {
    return {
      content: [{ type: "text", text: `Error: Habit ${habitId} not found` }],
      isError: true,
    };
  }

  const todayStr = getESTDateString();
  const lastCompleted = habit.lastCompletedDate;

  // Check if already completed today
  if (lastCompleted === todayStr) {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          success: false,
          message: "Habit already completed today",
          habit: {
            id: habit.id,
            name: habit.name,
            currentStreak: habit.currentStreak,
            lastCompletedDate: lastCompleted,
          },
        }, null, 2),
      }],
    };
  }

  // Calculate new streak
  let newStreak = 1; // Default: reset to 1
  const expectedPrevDate = getExpectedPreviousDate(habit.frequency, getESTNow());

  if (lastCompleted && expectedPrevDate && lastCompleted === expectedPrevDate) {
    // Consecutive completion - increment streak
    newStreak = (habit.currentStreak ?? 0) + 1;
  } else if (lastCompleted === todayStr) {
    // Same day - keep current streak (shouldn't reach here due to check above)
    newStreak = habit.currentStreak ?? 1;
  }
  // Otherwise: gap detected, reset to 1

  // Record completion
  const [completion] = await db
    .insert(schema.habitCompletions)
    .values({
      habitId,
      note: note || null,
    })
    .returning();

  // Update habit with new streak and lastCompletedDate
  const [updatedHabit] = await db
    .update(schema.habits)
    .set({
      currentStreak: newStreak,
      longestStreak: Math.max(habit.longestStreak ?? 0, newStreak),
      lastCompletedDate: todayStr,
      updatedAt: new Date(),
    })
    .where(eq(schema.habits.id, habitId))
    .returning();

  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        success: true,
        completion,
        habit: updatedHabit,
        streakInfo: {
          previousStreak: habit.currentStreak ?? 0,
          newStreak,
          wasConsecutive: newStreak > 1,
        },
      }, null, 2),
    }],
  };
}

/**
 * Handler: workos_get_habit_streaks
 * Get habit completion history and streak info
 */
export async function handleGetHabitStreaks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { habitId, days = 7 } = args as any;
  const sinceDate = new Date();
  sinceDate.setDate(sinceDate.getDate() - days);

  const conditions = [gte(schema.habitCompletions.completedAt, sinceDate)];
  if (habitId) conditions.push(eq(schema.habitCompletions.habitId, habitId));

  const completions = await db
    .select({
      id: schema.habitCompletions.id,
      habitId: schema.habitCompletions.habitId,
      habitName: schema.habits.name,
      completedAt: schema.habitCompletions.completedAt,
      note: schema.habitCompletions.note,
    })
    .from(schema.habitCompletions)
    .leftJoin(schema.habits, eq(schema.habitCompletions.habitId, schema.habits.id))
    .where(and(...conditions))
    .orderBy(desc(schema.habitCompletions.completedAt));

  return {
    content: [{ type: "text", text: JSON.stringify(completions, null, 2) }],
  };
}

/**
 * Handler: workos_habit_checkin
 * Get habits due for check-in based on time of day
 */
export async function handleHabitCheckin(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { timeOfDay = "all", includeCompleted = false } = args as any;
  const todayStr = getESTDateString();

  // Get all active habits
  const allHabits = await db
    .select()
    .from(schema.habits)
    .where(eq(schema.habits.isActive, 1))
    .orderBy(asc(schema.habits.sortOrder));

  // Filter by timeOfDay
  let habits = allHabits;
  if (timeOfDay !== "all") {
    habits = allHabits.filter(h =>
      h.timeOfDay === timeOfDay || h.timeOfDay === "anytime"
    );
  }

  // Filter out completed if requested
  if (!includeCompleted) {
    habits = habits.filter(h => h.lastCompletedDate !== todayStr);
  }

  // Build response with status
  const result = habits.map(h => ({
    id: h.id,
    name: h.name,
    emoji: h.emoji,
    category: h.category,
    timeOfDay: h.timeOfDay,
    frequency: h.frequency,
    currentStreak: h.currentStreak ?? 0,
    longestStreak: h.longestStreak ?? 0,
    lastCompleted: h.lastCompletedDate,
    completedToday: h.lastCompletedDate === todayStr,
  }));

  const completedCount = allHabits.filter(h => h.lastCompletedDate === todayStr).length;

  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        checkin: {
          timeOfDay,
          date: todayStr,
          totalHabits: allHabits.length,
          completedToday: completedCount,
          pendingToday: allHabits.length - completedCount,
        },
        habits: result,
      }, null, 2),
    }],
  };
}

/**
 * Handler: workos_habit_dashboard
 * Get ASCII dashboard showing habit completion grid for the week
 */
export async function handleHabitDashboard(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { days = 7, format = "compact" } = args as any;

  // Get all active habits
  const habits = await db
    .select()
    .from(schema.habits)
    .where(eq(schema.habits.isActive, 1))
    .orderBy(asc(schema.habits.sortOrder));

  // Get completions for the period
  const sinceDate = new Date();
  sinceDate.setDate(sinceDate.getDate() - days);

  const completions = await db
    .select()
    .from(schema.habitCompletions)
    .where(gte(schema.habitCompletions.completedAt, sinceDate));

  // Build date range
  const dates: string[] = [];
  const now = getESTNow();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    dates.push(getESTDateString(d));
  }

  // Build completion map: habitId -> Set of date strings
  const completionMap = new Map<number, Set<string>>();
  for (const c of completions) {
    const dateStr = getESTDateString(new Date(c.completedAt));
    if (!completionMap.has(c.habitId)) {
      completionMap.set(c.habitId, new Set());
    }
    completionMap.get(c.habitId)!.add(dateStr);
  }

  // Calculate stats
  const todayStr = getESTDateString();
  const completedToday = habits.filter(h => h.lastCompletedDate === todayStr).length;
  let totalCompletions = 0;
  let possibleCompletions = 0;

  for (const habit of habits) {
    const habitCompletions = completionMap.get(habit.id) || new Set();
    for (const date of dates) {
      // Check if habit should count for this date based on frequency
      const dateObj = new Date(date + "T12:00:00");
      const dayOfWeek = dateObj.getDay();
      const isWeekdayDate = dayOfWeek !== 0 && dayOfWeek !== 6;

      let shouldCount = true;
      if (habit.frequency === "weekdays" && !isWeekdayDate) {
        shouldCount = false;
      }
      // For weekly, we'd need more complex logic - simplified here

      if (shouldCount) {
        possibleCompletions++;
        if (habitCompletions.has(date)) {
          totalCompletions++;
        }
      }
    }
  }

  const weekPercent = possibleCompletions > 0
    ? Math.round((totalCompletions / possibleCompletions) * 100)
    : 0;

  // Build ASCII dashboard
  const dayLabels = dates.map(d => {
    const date = new Date(d + "T12:00:00");
    return ["S", "M", "T", "W", "T", "F", "S"][date.getDay()];
  });

  let dashboard = "";
  const weekStart = dates[0];
  const weekEnd = dates[dates.length - 1];
  const headerDate = new Date(weekStart + "T12:00:00");
  const monthDay = headerDate.toLocaleDateString("en-US", { month: "short", day: "numeric" });

  dashboard += `HABITS WEEK OF ${monthDay.toUpperCase()}\n`;
  dashboard += "━".repeat(32) + "\n";
  dashboard += "            " + dayLabels.map(d => ` ${d}`).join(" ") + "\n";

  for (const habit of habits) {
    const habitCompletions = completionMap.get(habit.id) || new Set();
    const emoji = habit.emoji || "📌";
    const name = habit.name.substring(0, 8).padEnd(8);
    const marks = dates.map(d => habitCompletions.has(d) ? "✓" : "·").join("  ");
    dashboard += `${emoji} ${name} ${marks}\n`;
  }

  dashboard += "━".repeat(32) + "\n";
  dashboard += `Today: ${completedToday}/${habits.length} | Week: ${totalCompletions}/${possibleCompletions} (${weekPercent}%)\n`;

  // Streak summary
  const streaks = habits
    .filter(h => (h.currentStreak ?? 0) > 0)
    .map(h => `${h.emoji || "📌"}${h.currentStreak}`)
    .join(" ");
  if (streaks) {
    dashboard += `Streaks: ${streaks}\n`;
  }

  if (format === "detailed") {
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          dashboard,
          stats: {
            todayCompleted: completedToday,
            todayTotal: habits.length,
            weekCompleted: totalCompletions,
            weekPossible: possibleCompletions,
            weekPercent,
          },
          habits: habits.map(h => ({
            id: h.id,
            name: h.name,
            emoji: h.emoji,
            currentStreak: h.currentStreak,
            longestStreak: h.longestStreak,
            completedToday: h.lastCompletedDate === todayStr,
          })),
          dates,
          completionMap: Object.fromEntries(
            Array.from(completionMap.entries()).map(([k, v]) => [k, Array.from(v)])
          ),
        }, null, 2),
      }],
    };
  }

  return {
    content: [{ type: "text", text: dashboard }],
  };
}

/**
 * Handler: workos_recalculate_streaks
 * Recalculate all habit streaks from completion history. Use to fix broken streak data.
 */
export async function handleRecalculateStreaks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  // Get all habits
  const habits = await db
    .select()
    .from(schema.habits)
    .where(eq(schema.habits.isActive, 1));

  const results: Array<{
    habitId: number;
    name: string;
    oldStreak: number;
    newStreak: number;
    lastCompletedDate: string | null;
  }> = [];

  for (const habit of habits) {
    // Get all completions for this habit, ordered by date desc
    const completions = await db
      .select()
      .from(schema.habitCompletions)
      .where(eq(schema.habitCompletions.habitId, habit.id))
      .orderBy(desc(schema.habitCompletions.completedAt));

    if (completions.length === 0) {
      // No completions - reset streak
      await db
        .update(schema.habits)
        .set({
          currentStreak: 0,
          lastCompletedDate: null,
          updatedAt: new Date(),
        })
        .where(eq(schema.habits.id, habit.id));

      results.push({
        habitId: habit.id,
        name: habit.name,
        oldStreak: habit.currentStreak ?? 0,
        newStreak: 0,
        lastCompletedDate: null,
      });
      continue;
    }

    // Group completions by date
    const completionDates = new Set<string>();
    for (const c of completions) {
      completionDates.add(getESTDateString(new Date(c.completedAt)));
    }

    // Sort dates descending
    const sortedDates = Array.from(completionDates).sort().reverse();
    const mostRecentDate = sortedDates[0];

    // Calculate streak by walking backwards from most recent
    let streak = 1;
    let currentDate = new Date(mostRecentDate + "T12:00:00");

    for (let i = 1; i < sortedDates.length; i++) {
      const expectedPrev = getExpectedPreviousDate(habit.frequency, currentDate);
      const actualPrev = sortedDates[i];

      if (expectedPrev === actualPrev) {
        streak++;
        currentDate = new Date(actualPrev + "T12:00:00");
      } else {
        // Gap detected, streak breaks here
        break;
      }
    }

    // Check if streak is still active (completed yesterday or today)
    const todayStr = getESTDateString();
    const yesterdayStr = getYesterdayDateString();

    if (mostRecentDate !== todayStr && mostRecentDate !== yesterdayStr) {
      // Streak is broken - last completion was before yesterday
      streak = 0;
    }

    // Update habit
    await db
      .update(schema.habits)
      .set({
        currentStreak: streak,
        longestStreak: Math.max(habit.longestStreak ?? 0, streak),
        lastCompletedDate: mostRecentDate,
        updatedAt: new Date(),
      })
      .where(eq(schema.habits.id, habit.id));

    results.push({
      habitId: habit.id,
      name: habit.name,
      oldStreak: habit.currentStreak ?? 0,
      newStreak: streak,
      lastCompletedDate: mostRecentDate,
    });
  }

  return {
    content: [{
      type: "text",
      text: JSON.stringify({
        success: true,
        recalculated: results.length,
        results,
      }, null, 2),
    }],
  };
}
