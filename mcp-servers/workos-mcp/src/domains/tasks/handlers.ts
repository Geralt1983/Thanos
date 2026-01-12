import type { Database, ToolHandler, ContentResponse } from "../../shared/types.js";
import { successResponse, errorResponse } from "../../shared/types.js";
import {
  getESTNow,
  getESTTodayStart,
  calculatePoints,
  calculateTotalPoints,
} from "../../shared/utils.js";
import * as schema from "../../schema.js";
import type { EnergyLevel } from "../../schema.js";
import { eq, and, gte, ne, desc, asc, or, inArray } from "drizzle-orm";
import {
  getCachedTasks,
  getCachedTasksByClient,
  getCachedClients,
  isCacheStale,
  getLatestCachedDailyGoal,
} from "../../cache/cache.js";
import { syncSingleTask, removeCachedTask } from "../../cache/sync.js";
import {
  getEnergyContext,
  rankTasksByEnergy,
} from "../../services/energy-prioritization.js";

// =============================================================================
// TASK DOMAIN HANDLERS
// =============================================================================

// Track cache initialization for write-through operations
let cacheInitialized = false;

/**
 * Ensure cache is initialized for write-through operations
 * Initializes SQLite cache and syncs from Neon if empty or stale
 *
 * @returns Promise<boolean> true if cache is available, false on initialization failure
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
 * Get today's task completion metrics and progress toward daily goals
 * Calculates earned points, target progress, client diversity, pace status, and current streak
 *
 * @param args - Empty object (no arguments required)
 * @param db - Database instance for querying tasks, clients, and daily goals
 * @returns Promise resolving to MCP ContentResponse with metrics including completedCount, earnedPoints, targetPoints, percentOfTarget, paceStatus, streak, and clientsTouchedToday
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
 * Get tasks with optional filtering by status and client
 * Uses cache-first pattern for optimal performance, falling back to Neon on cache miss or staleness
 *
 * @param args - { status?: string, clientId?: number, limit?: number } - Optional filters and result limit (default: 50)
 * @param db - Database instance for querying tasks when cache is unavailable
 * @returns Promise resolving to MCP ContentResponse with array of tasks including client names
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
 * Get all active clients from the system
 * Uses cache-first pattern for optimal performance, falling back to Neon on cache miss or staleness
 *
 * @param args - Empty object (no arguments required)
 * @param db - Database instance for querying clients when cache is unavailable
 * @returns Promise resolving to MCP ContentResponse with array of active clients
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
 * Create a new task with specified properties
 * Uses write-through pattern: writes to Neon first, then syncs to cache
 * Automatically calculates sortOrder to place task at top of its status column
 *
 * @param args - { title: string, description?: string, clientId?: number, status?: string, category?: string, valueTier?: string, drainType?: string, cognitiveLoad?: string }
 * @param db - Database instance for creating the task
 * @returns Promise resolving to MCP ContentResponse with success status and created task object
 */
export async function handleCreateTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { title, description, clientId, status = "backlog", category = "work", valueTier = "progress", drainType, cognitiveLoad } = args as any;

  if (!title) {
    return {
      content: [{ type: "text", text: "Error: title is required" }],
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
      cognitiveLoad: cognitiveLoad || null,
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
 * Mark a task as complete with timestamp
 * Uses write-through pattern: updates Neon first, then syncs to cache
 * Sets status to "done" and records completedAt timestamp
 *
 * @param args - { taskId: number } - ID of the task to complete
 * @param db - Database instance for updating the task
 * @returns Promise resolving to MCP ContentResponse with success status and updated task, or error if task not found
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
 * Promote a task from queued/backlog to active status
 * Uses write-through pattern: updates Neon first, then syncs to cache
 * Moves task into active work column for immediate focus
 *
 * @param args - { taskId: number } - ID of the task to promote
 * @param db - Database instance for updating the task
 * @returns Promise resolving to MCP ContentResponse with success status and updated task, or error if task not found
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
 * Get the current daily goal streak information
 * Returns the latest daily goal record with current and longest streaks
 *
 * @param args - Empty object (no arguments required)
 * @param db - Database instance for querying daily goals
 * @returns Promise resolving to MCP ContentResponse with currentStreak and longestStreak values
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
 * Get stored memory/notes for a specific client
 * Returns contextual information and notes about client preferences, history, and important details
 *
 * @param args - { clientName: string } - Name of the client to retrieve memory for
 * @param db - Database instance for querying client memory
 * @returns Promise resolving to MCP ContentResponse with client memory object or message if not found
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
 * Get comprehensive daily summary for Life OS morning brief
 * Provides complete overview of progress, active tasks, points, and queued work
 * Designed for daily planning and decision-making
 *
 * @param args - Empty object (no arguments required)
 * @param db - Database instance for querying tasks, daily goals, and progress
 * @returns Promise resolving to MCP ContentResponse with date, progress metrics, active tasks with points, potential total, and up-next queued tasks
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
 * Update task properties with partial updates
 * Uses write-through pattern: updates Neon first, then syncs to cache
 * Allows updating any combination of task fields
 *
 * @param args - { taskId: number, clientId?: number, title?: string, description?: string, status?: string, valueTier?: string, drainType?: string }
 * @param db - Database instance for updating the task
 * @returns Promise resolving to MCP ContentResponse with success status and updated task, or error if task not found or taskId missing
 */
export async function handleUpdateTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { taskId, clientId, title, description, status, valueTier, drainType } = args as any;

  if (!taskId) {
    return {
      content: [{ type: "text", text: "Error: taskId is required" }],
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
 * Delete a task permanently from the system
 * Uses write-through pattern: deletes from Neon first, then removes from cache
 * This action cannot be undone
 *
 * @param args - { taskId: number } - ID of the task to delete
 * @param db - Database instance for deleting the task
 * @returns Promise resolving to MCP ContentResponse with success status and deleted task object, or error if task not found or taskId missing
 */
export async function handleDeleteTask(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { taskId } = args as any;

  if (!taskId) {
    return {
      content: [{ type: "text", text: "Error: taskId is required" }],
    };
  }

  const [deletedTask] = await db
    .delete(schema.tasks)
    .where(eq(schema.tasks.id, taskId))
    .returning();

  if (!deletedTask) {
    return {
      content: [{ type: "text", text: `Error: Task ${taskId} not found` }],
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

/**
 * Get tasks prioritized by current energy level
 * Uses energy-aware prioritization algorithm to match tasks to current energy state
 * Returns tasks ranked by energy score with explanations
 *
 * @param args - { energy_level?: string, limit?: number } - Optional energy override and result limit
 * @param db - Database instance for querying tasks and energy context
 * @returns Promise resolving to MCP ContentResponse with ranked tasks, energy context, and match explanations
 */
export async function handleGetEnergyAwareTasks(
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> {
  const { energy_level, limit } = args as {
    energy_level?: EnergyLevel;
    limit?: number;
  };

  // Step 1: Get current energy context (unless overridden)
  let energyLevel: EnergyLevel;
  let energyContext;

  if (energy_level) {
    // User manually overrode energy level
    energyLevel = energy_level;
    energyContext = {
      energyLevel: energy_level,
      readinessScore: null,
      sleepScore: null,
      source: "manual_override",
      timestamp: new Date(),
    };
  } else {
    // Auto-detect energy from Oura/manual logs
    energyContext = await getEnergyContext(db);
    energyLevel = energyContext.energyLevel;
  }

  // Step 2: Get tasks that are actionable (active, queued, backlog)
  // Don't include completed tasks
  const tasksWithClients = await db
    .select({
      task: schema.tasks,
      clientName: schema.clients.name,
    })
    .from(schema.tasks)
    .leftJoin(schema.clients, eq(schema.tasks.clientId, schema.clients.id))
    .where(
      or(
        eq(schema.tasks.status, "active"),
        eq(schema.tasks.status, "queued"),
        eq(schema.tasks.status, "backlog")
      )
    )
    .orderBy(asc(schema.tasks.sortOrder), desc(schema.tasks.createdAt));

  // Extract tasks for ranking
  const tasks = tasksWithClients.map(row => row.task);

  // Step 3: Rank tasks by energy match
  const rankedTasks = rankTasksByEnergy(tasks, energyLevel, limit);

  // Create a map of task IDs to client names
  const clientNameMap = new Map(
    tasksWithClients.map(row => [row.task.id, row.clientName])
  );

  // Step 4: Format response with energy context and ranked tasks
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            energyContext: {
              energyLevel: energyContext.energyLevel,
              readinessScore: energyContext.readinessScore,
              sleepScore: energyContext.sleepScore,
              source: energyContext.source,
              timestamp: energyContext.timestamp,
            },
            taskCount: rankedTasks.length,
            tasks: rankedTasks.map((task) => ({
              id: task.id,
              title: task.title,
              description: task.description,
              status: task.status,
              category: task.category,
              valueTier: task.valueTier,
              drainType: task.drainType,
              cognitiveLoad: task.cognitiveLoad,
              effortEstimate: task.effortEstimate,
              points: task.pointsFinal ?? task.pointsAiGuess ?? 2,
              clientName: clientNameMap.get(task.id) || null,
              energyScore: task.energyScore,
              matchReason: task.matchReason,
            })),
          },
          null,
          2
        ),
      },
    ],
  };
}
