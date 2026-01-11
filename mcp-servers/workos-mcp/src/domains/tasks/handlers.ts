import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import {
  getESTNow,
  getESTTodayStart,
  calculatePoints,
  calculateTotalPoints,
} from "../../shared/utils.js";
import * as schema from "../../schema.js";
import { eq, and, gte, ne, desc, asc } from "drizzle-orm";
import {
  getCachedTasks,
  getCachedTasksByClient,
  getCachedClients,
  isCacheStale,
  getLatestCachedDailyGoal,
} from "../../cache/cache.js";
import { syncSingleTask, removeCachedTask } from "../../cache/sync.js";

// =============================================================================
// TASK DOMAIN HANDLERS
// =============================================================================

// Track cache initialization for write-through operations
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
      if (stats.taskCount === 0 || stats.isStale) {
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
 * Handler: workos_get_today_metrics
 * Get today's task completion metrics and progress
 */
export async function handleGetTodayMetrics(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const todayStart = getESTTodayStart();

  const completedToday = await db
    .select()
    .from(schema.tasks)
    .where(
      and(
        eq(schema.tasks.status, "done"),
        gte(schema.tasks.completedAt, todayStart)
      )
    );

  const earnedPoints = calculateTotalPoints(completedToday);
  const targetPoints = 18;
  const minimumPoints = 12;

  const externalClients = await db
    .select({ id: schema.clients.id })
    .from(schema.clients)
    .where(ne(schema.clients.type, "internal"));

  const externalClientIds = new Set(externalClients.map((c) => c.id));
  const clientsTouchedToday = new Set(
    completedToday
      .filter((t) => t.clientId && externalClientIds.has(t.clientId))
      .map((t) => t.clientId)
  ).size;

  const percentOfTarget = Math.round((earnedPoints / targetPoints) * 100);
  const percentOfMinimum = Math.round((earnedPoints / minimumPoints) * 100);

  let paceStatus: string;
  if (percentOfTarget >= 100) paceStatus = "ahead";
  else if (percentOfMinimum >= 100) paceStatus = "minimum_only";
  else if (earnedPoints === 0) paceStatus = "behind";
  else {
    const estNow = getESTNow();
    const hour = estNow.getHours() + estNow.getMinutes() / 60;
    const dayProgress = Math.max(0, Math.min(100, ((hour - 9) / 9) * 100));
    paceStatus = percentOfTarget >= dayProgress ? "on_track" : "behind";
  }

  const [latestGoal] = await db
    .select({ currentStreak: schema.dailyGoals.currentStreak })
    .from(schema.dailyGoals)
    .orderBy(desc(schema.dailyGoals.date))
    .limit(1);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          completedCount: completedToday.length,
          earnedPoints,
          targetPoints,
          minimumPoints,
          percentOfTarget,
          percentOfMinimum,
          paceStatus,
          streak: latestGoal?.currentStreak ?? 0,
          clientsTouchedToday,
          totalExternalClients: externalClientIds.size,
        }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_get_tasks
 * Get tasks with optional filtering by status and client (cache-first)
 */
export async function handleGetTasks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { status, clientId, limit = 50 } = args as any;

  // Try cache first
  const cacheAvailable = await ensureCache();
  if (cacheAvailable && !isCacheStale()) {
    try {
      let cachedTasks;
      if (clientId) {
        cachedTasks = getCachedTasksByClient(clientId, status, limit);
      } else {
        cachedTasks = getCachedTasks(status, limit);
      }

      // Get client names for cached tasks
      const cachedClients = getCachedClients();
      const clientMap = new Map(cachedClients.map(c => [c.id, c.name]));

      const tasksWithClients = cachedTasks.map(t => ({
        ...t,
        clientName: t.clientId ? clientMap.get(t.clientId) || null : null,
      }));

      console.error(`[Cache] Served ${tasksWithClients.length} tasks from cache`);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(tasksWithClients, null, 2),
          },
        ],
      };
    } catch (cacheError) {
      console.error("[Cache] Error reading from cache, falling back to Neon:", cacheError);
    }
  }

  // Fallback to Neon
  const conditions = [];
  if (status) conditions.push(eq(schema.tasks.status, status));
  if (clientId) conditions.push(eq(schema.tasks.clientId, clientId));

  const query = db
    .select({
      id: schema.tasks.id,
      title: schema.tasks.title,
      description: schema.tasks.description,
      status: schema.tasks.status,
      valueTier: schema.tasks.valueTier,
      drainType: schema.tasks.drainType,
      pointsFinal: schema.tasks.pointsFinal,
      pointsAiGuess: schema.tasks.pointsAiGuess,
      clientId: schema.tasks.clientId,
      clientName: schema.clients.name,
      createdAt: schema.tasks.createdAt,
      completedAt: schema.tasks.completedAt,
    })
    .from(schema.tasks)
    .leftJoin(schema.clients, eq(schema.tasks.clientId, schema.clients.id))
    .orderBy(asc(schema.tasks.sortOrder), desc(schema.tasks.createdAt))
    .limit(limit);

  const tasks = conditions.length > 0
    ? await query.where(and(...conditions))
    : await query;

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(tasks, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_get_clients
 * Get all active clients (cache-first)
 */
export async function handleGetClients(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  // Try cache first
  const cacheAvailable = await ensureCache();
  if (cacheAvailable && !isCacheStale()) {
    try {
      const cachedClients = getCachedClients();
      console.error(`[Cache] Served ${cachedClients.length} clients from cache`);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(cachedClients, null, 2),
          },
        ],
      };
    } catch (cacheError) {
      console.error("[Cache] Error reading from cache, falling back to Neon:", cacheError);
    }
  }

  // Fallback to Neon
  const clients = await db
    .select()
    .from(schema.clients)
    .where(eq(schema.clients.isActive, 1));

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(clients, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_create_task
 * Create a new task (write-through: Neon first, then cache)
 */
export async function handleCreateTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { title, description, clientId, status = "backlog", category = "work", valueTier = "progress", drainType } = args as any;

  if (!title) {
    return {
      content: [{ type: "text", text: "Error: title is required" }],
      isError: true,
    };
  }

  const existingTasks = await db
    .select({ sortOrder: schema.tasks.sortOrder })
    .from(schema.tasks)
    .where(eq(schema.tasks.status, status));

  const minSortOrder = existingTasks.reduce((min, t) => Math.min(min, t.sortOrder ?? 0), 0);

  const [newTask] = await db
    .insert(schema.tasks)
    .values({
      title,
      description: description || null,
      clientId: clientId || null,
      status,
      category,
      valueTier,
      drainType: drainType || null,
      sortOrder: minSortOrder - 1,
      updatedAt: new Date(),
    })
    .returning();

  // Update cache (write-through)
  if (cacheInitialized) {
    try {
      await syncSingleTask(newTask.id);
      console.error(`[Cache] Synced new task ${newTask.id} to cache`);
    } catch (cacheError) {
      console.error("[Cache] Failed to sync new task to cache:", cacheError);
    }
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({ success: true, task: newTask }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_complete_task
 * Mark a task as complete (write-through: Neon first, then cache)
 */
export async function handleCompleteTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { taskId } = args as any;

  const [updatedTask] = await db
    .update(schema.tasks)
    .set({
      status: "done",
      completedAt: new Date(),
      updatedAt: new Date(),
    })
    .where(eq(schema.tasks.id, taskId))
    .returning();

  if (!updatedTask) {
    return {
      content: [{ type: "text", text: `Error: Task ${taskId} not found` }],
      isError: true,
    };
  }

  // Update cache (write-through)
  if (cacheInitialized) {
    try {
      await syncSingleTask(taskId);
      console.error(`[Cache] Synced completed task ${taskId} to cache`);
    } catch (cacheError) {
      console.error("[Cache] Failed to sync completed task to cache:", cacheError);
    }
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({ success: true, task: updatedTask }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_promote_task
 * Promote a task to active status (write-through: Neon first, then cache)
 */
export async function handlePromoteTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { taskId } = args as any;

  const [updatedTask] = await db
    .update(schema.tasks)
    .set({
      status: "active",
      updatedAt: new Date(),
    })
    .where(eq(schema.tasks.id, taskId))
    .returning();

  if (!updatedTask) {
    return {
      content: [{ type: "text", text: `Error: Task ${taskId} not found` }],
      isError: true,
    };
  }

  // Update cache (write-through)
  if (cacheInitialized) {
    try {
      await syncSingleTask(taskId);
      console.error(`[Cache] Synced promoted task ${taskId} to cache`);
    } catch (cacheError) {
      console.error("[Cache] Failed to sync promoted task to cache:", cacheError);
    }
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({ success: true, task: updatedTask }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_get_streak
 * Get the current daily goal streak
 */
export async function handleGetStreak(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const [latestGoal] = await db
    .select()
    .from(schema.dailyGoals)
    .orderBy(desc(schema.dailyGoals.date))
    .limit(1);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(latestGoal || { currentStreak: 0, longestStreak: 0 }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_get_client_memory
 * Get memory/notes for a specific client
 */
export async function handleGetClientMemory(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { clientName } = args as any;

  const [memory] = await db
    .select()
    .from(schema.clientMemory)
    .where(eq(schema.clientMemory.clientName, clientName))
    .limit(1);

  return {
    content: [
      {
        type: "text",
        text: memory
          ? JSON.stringify(memory, null, 2)
          : `No memory found for client: ${clientName}`,
      },
    ],
  };
}

/**
 * Handler: workos_daily_summary
 * Get comprehensive daily summary for Life OS morning brief
 */
export async function handleDailySummary(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const todayStart = getESTTodayStart();

  // Get today's completed tasks
  const completedToday = await db
    .select()
    .from(schema.tasks)
    .where(
      and(
        eq(schema.tasks.status, "done"),
        gte(schema.tasks.completedAt, todayStart)
      )
    );

  // Get active tasks
  const activeTasks = await db
    .select({
      id: schema.tasks.id,
      title: schema.tasks.title,
      clientName: schema.clients.name,
      valueTier: schema.tasks.valueTier,
      pointsFinal: schema.tasks.pointsFinal,
      pointsAiGuess: schema.tasks.pointsAiGuess,
    })
    .from(schema.tasks)
    .leftJoin(schema.clients, eq(schema.tasks.clientId, schema.clients.id))
    .where(eq(schema.tasks.status, "active"))
    .orderBy(asc(schema.tasks.sortOrder));

  // Get queued tasks
  const queuedTasks = await db
    .select({
      id: schema.tasks.id,
      title: schema.tasks.title,
      clientName: schema.clients.name,
    })
    .from(schema.tasks)
    .leftJoin(schema.clients, eq(schema.tasks.clientId, schema.clients.id))
    .where(eq(schema.tasks.status, "queued"))
    .orderBy(asc(schema.tasks.sortOrder))
    .limit(5);

  // Get streak
  const [latestGoal] = await db
    .select()
    .from(schema.dailyGoals)
    .orderBy(desc(schema.dailyGoals.date))
    .limit(1);

  const earnedPoints = calculateTotalPoints(completedToday);
  const activePoints = activeTasks.reduce((sum, t) => sum + (t.pointsFinal ?? t.pointsAiGuess ?? 2), 0);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          date: new Date().toISOString().split('T')[0],
          progress: {
            earnedPoints,
            targetPoints: 18,
            minimumPoints: 12,
            completedTasks: completedToday.length,
            streak: latestGoal?.currentStreak ?? 0,
          },
          today: {
            activeTasks: activeTasks.map(t => ({
              id: t.id,
              title: t.title,
              client: t.clientName,
              points: t.pointsFinal ?? t.pointsAiGuess ?? 2,
            })),
            activePoints,
            potentialTotal: earnedPoints + activePoints,
          },
          upNext: queuedTasks.map(t => ({
            id: t.id,
            title: t.title,
            client: t.clientName,
          })),
        }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_update_task
 * Update task properties (write-through: Neon first, then cache)
 */
export async function handleUpdateTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { taskId, clientId, title, description, status, valueTier, drainType } = args as any;

  if (!taskId) {
    return {
      content: [{ type: "text", text: "Error: taskId is required" }],
      isError: true,
    };
  }

  const updateData: any = { updatedAt: new Date() };
  if (clientId !== undefined) updateData.clientId = clientId;
  if (title !== undefined) updateData.title = title;
  if (description !== undefined) updateData.description = description;
  if (status !== undefined) updateData.status = status;
  if (valueTier !== undefined) updateData.valueTier = valueTier;
  if (drainType !== undefined) updateData.drainType = drainType;

  const [updatedTask] = await db
    .update(schema.tasks)
    .set(updateData)
    .where(eq(schema.tasks.id, taskId))
    .returning();

  if (!updatedTask) {
    return {
      content: [{ type: "text", text: `Error: Task ${taskId} not found` }],
      isError: true,
    };
  }

  // Update cache (write-through)
  if (cacheInitialized) {
    try {
      await syncSingleTask(taskId);
      console.error(`[Cache] Synced updated task ${taskId} to cache`);
    } catch (cacheError) {
      console.error("[Cache] Failed to sync updated task to cache:", cacheError);
    }
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({ success: true, task: updatedTask }, null, 2),
      },
    ],
  };
}

/**
 * Handler: workos_delete_task
 * Delete a task (write-through: Neon first, then cache)
 */
export async function handleDeleteTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { taskId } = args as any;

  if (!taskId) {
    return {
      content: [{ type: "text", text: "Error: taskId is required" }],
      isError: true,
    };
  }

  const [deletedTask] = await db
    .delete(schema.tasks)
    .where(eq(schema.tasks.id, taskId))
    .returning();

  if (!deletedTask) {
    return {
      content: [{ type: "text", text: `Error: Task ${taskId} not found` }],
      isError: true,
    };
  }

  // Update cache (write-through - remove deleted task)
  if (cacheInitialized) {
    try {
      removeCachedTask(taskId);
      console.error(`[Cache] Removed deleted task ${taskId} from cache`);
    } catch (cacheError) {
      console.error("[Cache] Failed to remove deleted task from cache:", cacheError);
    }
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({ success: true, deleted: deletedTask }, null, 2),
      },
    ],
  };
}
