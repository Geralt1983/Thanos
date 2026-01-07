import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import { eq, desc } from "drizzle-orm";
import * as remoteSchema from "../schema.js";
import * as cacheSchema from "./schema.js";
import {
  getCacheDb,
  setLastSyncTime,
  clearCache,
} from "./cache.js";

// =============================================================================
// REMOTE DATABASE CONNECTION
// =============================================================================
function getRemoteDb() {
  const url = process.env.WORKOS_DATABASE_URL || process.env.DATABASE_URL;
  if (!url) {
    throw new Error("WORKOS_DATABASE_URL or DATABASE_URL environment variable required");
  }
  const sql = neon(url);
  return drizzle(sql, { schema: remoteSchema });
}

// =============================================================================
// SYNC UTILITIES
// =============================================================================

/**
 * Convert Date objects to ISO strings for SQLite storage
 */
function dateToIso(date: Date | null | undefined): string | null {
  if (!date) return null;
  return date instanceof Date ? date.toISOString() : date;
}

// =============================================================================
// SYNC OPERATIONS
// =============================================================================

/**
 * Sync all clients from Neon to SQLite cache
 */
export async function syncClients(): Promise<number> {
  const remoteDb = getRemoteDb();
  const cacheDb = getCacheDb();

  // Fetch all clients from Neon
  const clients = await remoteDb.select().from(remoteSchema.clients);

  // Clear existing cached clients
  cacheDb.delete(cacheSchema.cachedClients).run();

  // Insert all clients
  for (const client of clients) {
    cacheDb.insert(cacheSchema.cachedClients)
      .values({
        id: client.id,
        name: client.name,
        type: client.type,
        color: client.color,
        isActive: client.isActive,
        createdAt: dateToIso(client.createdAt) || new Date().toISOString(),
      })
      .run();
  }

  return clients.length;
}

/**
 * Sync all tasks from Neon to SQLite cache
 */
export async function syncTasks(): Promise<number> {
  const remoteDb = getRemoteDb();
  const cacheDb = getCacheDb();

  // Fetch all non-archived tasks from Neon
  // We exclude very old completed tasks to keep cache size manageable
  const tasks = await remoteDb.select().from(remoteSchema.tasks);

  // Clear existing cached tasks
  cacheDb.delete(cacheSchema.cachedTasks).run();

  // Insert all tasks
  for (const task of tasks) {
    cacheDb.insert(cacheSchema.cachedTasks)
      .values({
        id: task.id,
        clientId: task.clientId,
        title: task.title,
        description: task.description,
        status: task.status,
        category: task.category,
        valueTier: task.valueTier,
        effortEstimate: task.effortEstimate,
        effortActual: task.effortActual,
        drainType: task.drainType,
        sortOrder: task.sortOrder,
        subtasks: JSON.stringify(task.subtasks || []),
        createdAt: dateToIso(task.createdAt) || new Date().toISOString(),
        updatedAt: dateToIso(task.updatedAt) || new Date().toISOString(),
        completedAt: dateToIso(task.completedAt),
        backlogEnteredAt: dateToIso(task.backlogEnteredAt),
        pointsAiGuess: task.pointsAiGuess,
        pointsFinal: task.pointsFinal,
        pointsAdjustedAt: dateToIso(task.pointsAdjustedAt),
      })
      .run();
  }

  return tasks.length;
}

/**
 * Sync daily goals from Neon to SQLite cache
 */
export async function syncDailyGoals(): Promise<number> {
  const remoteDb = getRemoteDb();
  const cacheDb = getCacheDb();

  // Fetch recent daily goals (last 30 days)
  const goals = await remoteDb
    .select()
    .from(remoteSchema.dailyGoals)
    .orderBy(desc(remoteSchema.dailyGoals.date))
    .limit(30);

  // Clear existing cached goals
  cacheDb.delete(cacheSchema.cachedDailyGoals).run();

  // Insert all goals
  for (const goal of goals) {
    cacheDb.insert(cacheSchema.cachedDailyGoals)
      .values({
        id: goal.id,
        date: goal.date,
        targetPoints: goal.targetPoints,
        earnedPoints: goal.earnedPoints,
        taskCount: goal.taskCount,
        currentStreak: goal.currentStreak,
        longestStreak: goal.longestStreak,
        lastGoalHitDate: goal.lastGoalHitDate,
        dailyDebt: goal.dailyDebt,
        weeklyDebt: goal.weeklyDebt,
        pressureLevel: goal.pressureLevel,
        updatedAt: dateToIso(goal.updatedAt),
      })
      .run();
  }

  return goals.length;
}

/**
 * Sync habits from Neon to SQLite cache
 */
export async function syncHabits(): Promise<number> {
  const remoteDb = getRemoteDb();
  const cacheDb = getCacheDb();

  // Fetch all habits
  const habits = await remoteDb.select().from(remoteSchema.habits);

  // Clear existing cached habits
  cacheDb.delete(cacheSchema.cachedHabits).run();

  // Insert all habits
  for (const habit of habits) {
    cacheDb.insert(cacheSchema.cachedHabits)
      .values({
        id: habit.id,
        name: habit.name,
        description: habit.description,
        emoji: habit.emoji,
        frequency: habit.frequency,
        targetCount: habit.targetCount,
        currentStreak: habit.currentStreak,
        longestStreak: habit.longestStreak,
        isActive: habit.isActive,
        sortOrder: habit.sortOrder,
        createdAt: dateToIso(habit.createdAt) || new Date().toISOString(),
        updatedAt: dateToIso(habit.updatedAt) || new Date().toISOString(),
      })
      .run();
  }

  return habits.length;
}

/**
 * Full sync: Pull all data from Neon and refresh SQLite cache
 */
export async function syncAll(): Promise<{
  clients: number;
  tasks: number;
  dailyGoals: number;
  habits: number;
  syncedAt: string;
}> {
  const startTime = Date.now();

  // Run all syncs
  const [clientCount, taskCount, goalCount, habitCount] = await Promise.all([
    syncClients(),
    syncTasks(),
    syncDailyGoals(),
    syncHabits(),
  ]);

  // Update sync timestamp
  const syncedAt = new Date();
  setLastSyncTime(syncedAt);

  const duration = Date.now() - startTime;
  console.error(`[Cache Sync] Completed in ${duration}ms: ${clientCount} clients, ${taskCount} tasks, ${goalCount} goals, ${habitCount} habits`);

  return {
    clients: clientCount,
    tasks: taskCount,
    dailyGoals: goalCount,
    habits: habitCount,
    syncedAt: syncedAt.toISOString(),
  };
}

/**
 * Sync a single task after a write operation (write-through)
 */
export async function syncSingleTask(taskId: number): Promise<void> {
  const remoteDb = getRemoteDb();
  const cacheDb = getCacheDb();

  const [task] = await remoteDb
    .select()
    .from(remoteSchema.tasks)
    .where(eq(remoteSchema.tasks.id, taskId));

  if (!task) {
    // Task was deleted, remove from cache
    cacheDb.delete(cacheSchema.cachedTasks)
      .where(eq(cacheSchema.cachedTasks.id, taskId))
      .run();
    return;
  }

  // Upsert the task
  cacheDb.insert(cacheSchema.cachedTasks)
    .values({
      id: task.id,
      clientId: task.clientId,
      title: task.title,
      description: task.description,
      status: task.status,
      category: task.category,
      valueTier: task.valueTier,
      effortEstimate: task.effortEstimate,
      effortActual: task.effortActual,
      drainType: task.drainType,
      sortOrder: task.sortOrder,
      subtasks: JSON.stringify(task.subtasks || []),
      createdAt: dateToIso(task.createdAt) || new Date().toISOString(),
      updatedAt: dateToIso(task.updatedAt) || new Date().toISOString(),
      completedAt: dateToIso(task.completedAt),
      backlogEnteredAt: dateToIso(task.backlogEnteredAt),
      pointsAiGuess: task.pointsAiGuess,
      pointsFinal: task.pointsFinal,
      pointsAdjustedAt: dateToIso(task.pointsAdjustedAt),
    })
    .onConflictDoUpdate({
      target: cacheSchema.cachedTasks.id,
      set: {
        clientId: task.clientId,
        title: task.title,
        description: task.description,
        status: task.status,
        category: task.category,
        valueTier: task.valueTier,
        effortEstimate: task.effortEstimate,
        effortActual: task.effortActual,
        drainType: task.drainType,
        sortOrder: task.sortOrder,
        subtasks: JSON.stringify(task.subtasks || []),
        updatedAt: dateToIso(task.updatedAt) || new Date().toISOString(),
        completedAt: dateToIso(task.completedAt),
        backlogEnteredAt: dateToIso(task.backlogEnteredAt),
        pointsAiGuess: task.pointsAiGuess,
        pointsFinal: task.pointsFinal,
        pointsAdjustedAt: dateToIso(task.pointsAdjustedAt),
      },
    })
    .run();
}

/**
 * Remove a task from cache (after remote delete)
 */
export function removeCachedTask(taskId: number): void {
  const cacheDb = getCacheDb();
  cacheDb.delete(cacheSchema.cachedTasks)
    .where(eq(cacheSchema.cachedTasks.id, taskId))
    .run();
}
