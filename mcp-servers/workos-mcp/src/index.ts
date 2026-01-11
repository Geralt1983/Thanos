#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { neon } from "@neondatabase/serverless";
import { drizzle } from "drizzle-orm/neon-http";
import { eq, and, gte, ne, desc, asc } from "drizzle-orm";
import * as schema from "./schema.js";

// Cache imports
import {
  initCache,
  getCachedTasks,
  getCachedTasksByClient,
  getCachedClients,
  getCachedHabits,
  getLatestCachedDailyGoal,
  isCacheStale,
  getCacheStats,
} from "./cache/cache.js";
import { syncAll, syncSingleTask, removeCachedTask } from "./cache/sync.js";
import { withCacheFirst } from "./cache/utils.js";

// =============================================================================
// DATABASE CONNECTION
// =============================================================================
function getDb() {
  const url = process.env.WORKOS_DATABASE_URL || process.env.DATABASE_URL;
  if (!url) {
    throw new Error("WORKOS_DATABASE_URL or DATABASE_URL environment variable required");
  }
  const sql = neon(url);
  return drizzle(sql, { schema });
}

// =============================================================================
// CACHE LAYER
// =============================================================================
let cacheInitialized = false;

async function ensureCache(): Promise<boolean> {
  if (!cacheInitialized) {
    try {
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

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================
function getESTNow(): Date {
  return new Date(new Date().toLocaleString("en-US", { timeZone: "America/New_York" }));
}

function getESTTodayStart(): Date {
  const est = getESTNow();
  est.setHours(0, 0, 0, 0);
  return est;
}

function getESTDateString(date: Date = new Date()): string {
  return date.toLocaleDateString("en-CA", { timeZone: "America/New_York" });
}

function getYesterdayDateString(): string {
  const yesterday = getESTNow();
  yesterday.setDate(yesterday.getDate() - 1);
  return getESTDateString(yesterday);
}

function isWeekday(date: Date): boolean {
  const day = date.getDay();
  return day !== 0 && day !== 6;
}

function getExpectedPreviousDate(frequency: string, currentDate: Date): string | null {
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

function calculatePoints(task: schema.Task): number {
  return task.pointsFinal ?? task.pointsAiGuess ?? task.effortEstimate ?? 2;
}

function calculateTotalPoints(tasks: schema.Task[]): number {
  return tasks.reduce((sum, task) => sum + calculatePoints(task), 0);
}

// =============================================================================
// MCP SERVER SETUP
// =============================================================================
const server = new Server(
  {
    name: "workos-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// =============================================================================
// TOOL DEFINITIONS
// =============================================================================
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "workos_get_today_metrics",
        description: "Get today's work progress: points earned, target, pace status, streak, and clients touched",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "workos_get_tasks",
        description: "Get tasks from WorkOS. Filter by status: 'active' (today), 'queued' (up next), 'backlog', or 'done'",
        inputSchema: {
          type: "object",
          properties: {
            status: {
              type: "string",
              description: "Filter by status: active, queued, backlog, done",
              enum: ["active", "queued", "backlog", "done"],
            },
            clientId: {
              type: "number",
              description: "Filter by client ID",
            },
            limit: {
              type: "number",
              description: "Max tasks to return (default 50)",
            },
          },
          required: [],
        },
      },
      {
        name: "workos_get_clients",
        description: "Get all active clients from WorkOS",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "workos_create_task",
        description: "Create a new task in WorkOS",
        inputSchema: {
          type: "object",
          properties: {
            title: {
              type: "string",
              description: "Task title (required)",
            },
            description: {
              type: "string",
              description: "Task description",
            },
            clientId: {
              type: "number",
              description: "Client ID to associate with",
            },
            status: {
              type: "string",
              description: "Initial status (default: backlog)",
              enum: ["active", "queued", "backlog"],
            },
            category: {
              type: "string",
              description: "Task category: work or personal (default: work)",
              enum: ["work", "personal"],
            },
            valueTier: {
              type: "string",
              description: "Value tier: checkbox, progress, deliverable, milestone",
              enum: ["checkbox", "progress", "deliverable", "milestone"],
            },
            drainType: {
              type: "string",
              description: "Energy drain type: deep, shallow, admin",
              enum: ["deep", "shallow", "admin"],
            },
          },
          required: ["title"],
        },
      },
      {
        name: "workos_complete_task",
        description: "Mark a task as completed",
        inputSchema: {
          type: "object",
          properties: {
            taskId: {
              type: "number",
              description: "Task ID to complete",
            },
          },
          required: ["taskId"],
        },
      },
      {
        name: "workos_promote_task",
        description: "Promote a task to 'active' (today) status",
        inputSchema: {
          type: "object",
          properties: {
            taskId: {
              type: "number",
              description: "Task ID to promote",
            },
          },
          required: ["taskId"],
        },
      },
      {
        name: "workos_get_streak",
        description: "Get current streak information and daily goal status",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "workos_get_client_memory",
        description: "Get AI-generated notes and status for a client",
        inputSchema: {
          type: "object",
          properties: {
            clientName: {
              type: "string",
              description: "Client name to look up",
            },
          },
          required: ["clientName"],
        },
      },
      {
        name: "workos_daily_summary",
        description: "Get a comprehensive daily summary for Life OS morning brief",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "workos_update_task",
        description: "Update a task's properties (clientId, title, description, status, valueTier, drainType)",
        inputSchema: {
          type: "object",
          properties: {
            taskId: {
              type: "number",
              description: "Task ID to update (required)",
            },
            clientId: {
              type: "number",
              description: "New client ID (use null to unassign)",
            },
            title: {
              type: "string",
              description: "New task title",
            },
            description: {
              type: "string",
              description: "New task description",
            },
            status: {
              type: "string",
              description: "New status",
              enum: ["active", "queued", "backlog", "done"],
            },
            valueTier: {
              type: "string",
              description: "New value tier",
              enum: ["checkbox", "progress", "deliverable", "milestone"],
            },
            drainType: {
              type: "string",
              description: "New drain type",
              enum: ["deep", "shallow", "admin"],
            },
          },
          required: ["taskId"],
        },
      },
      {
        name: "workos_delete_task",
        description: "Permanently delete a task (use for duplicates or cleanup)",
        inputSchema: {
          type: "object",
          properties: {
            taskId: {
              type: "number",
              description: "Task ID to delete (required)",
            },
          },
          required: ["taskId"],
        },
      },
      // =====================================================================
      // PERSONALOS INTEGRATION: HABITS
      // =====================================================================
      {
        name: "workos_get_habits",
        description: "Get all active habits with their current streaks",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "workos_create_habit",
        description: "Create a new habit to track",
        inputSchema: {
          type: "object",
          properties: {
            name: { type: "string", description: "Habit name (required)" },
            description: { type: "string", description: "Habit description" },
            emoji: { type: "string", description: "Emoji icon for the habit" },
            frequency: { type: "string", description: "daily, weekly, weekdays", enum: ["daily", "weekly", "weekdays"] },
            targetCount: { type: "number", description: "Times per period (default 1)" },
            timeOfDay: { type: "string", description: "When to do this habit", enum: ["morning", "evening", "anytime"] },
            category: { type: "string", description: "Habit category", enum: ["health", "productivity", "relationship", "personal"] },
          },
          required: ["name"],
        },
      },
      {
        name: "workos_complete_habit",
        description: "Mark a habit as completed for today",
        inputSchema: {
          type: "object",
          properties: {
            habitId: { type: "number", description: "Habit ID to complete" },
            note: { type: "string", description: "Optional note about the completion" },
          },
          required: ["habitId"],
        },
      },
      {
        name: "workos_get_habit_streaks",
        description: "Get habit completion history and streak info",
        inputSchema: {
          type: "object",
          properties: {
            habitId: { type: "number", description: "Habit ID (optional, all if omitted)" },
            days: { type: "number", description: "Number of days to look back (default 7)" },
          },
          required: [],
        },
      },
      {
        name: "workos_habit_checkin",
        description: "Get habits due for check-in based on time of day",
        inputSchema: {
          type: "object",
          properties: {
            timeOfDay: { type: "string", description: "morning, evening, or all", enum: ["morning", "evening", "all"] },
            includeCompleted: { type: "boolean", description: "Include habits already completed today (default false)" },
          },
          required: [],
        },
      },
      {
        name: "workos_habit_dashboard",
        description: "Get ASCII dashboard showing habit completion grid for the week",
        inputSchema: {
          type: "object",
          properties: {
            days: { type: "number", description: "Number of days to show (default 7)" },
            format: { type: "string", description: "Output format", enum: ["compact", "detailed", "weekly"] },
          },
          required: [],
        },
      },
      {
        name: "workos_recalculate_streaks",
        description: "Recalculate all habit streaks from completion history. Use to fix broken streak data.",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      // =====================================================================
      // PERSONALOS INTEGRATION: ENERGY STATE
      // =====================================================================
      {
        name: "workos_log_energy",
        description: "Log current energy state (high/medium/low). Can include Oura data.",
        inputSchema: {
          type: "object",
          properties: {
            level: { type: "string", description: "Energy level", enum: ["high", "medium", "low"] },
            note: { type: "string", description: "Optional note" },
            ouraReadiness: { type: "number", description: "Oura readiness score (0-100)" },
            ouraHrv: { type: "number", description: "Oura HRV" },
            ouraSleep: { type: "number", description: "Oura sleep score (0-100)" },
          },
          required: ["level"],
        },
      },
      {
        name: "workos_get_energy",
        description: "Get current/recent energy states",
        inputSchema: {
          type: "object",
          properties: {
            limit: { type: "number", description: "Number of entries (default 5)" },
          },
          required: [],
        },
      },
      // =====================================================================
      // PERSONALOS INTEGRATION: BRAIN DUMP
      // =====================================================================
      {
        name: "workos_brain_dump",
        description: "Quick capture a thought, idea, or worry. Low friction - just dump it.",
        inputSchema: {
          type: "object",
          properties: {
            content: { type: "string", description: "The thought to capture" },
            category: { type: "string", description: "thought, task, idea, worry", enum: ["thought", "task", "idea", "worry"] },
          },
          required: ["content"],
        },
      },
      {
        name: "workos_get_brain_dump",
        description: "Get unprocessed brain dump entries",
        inputSchema: {
          type: "object",
          properties: {
            includeProcessed: { type: "boolean", description: "Include already processed items" },
            limit: { type: "number", description: "Max entries (default 20)" },
          },
          required: [],
        },
      },
      {
        name: "workos_process_brain_dump",
        description: "Mark a brain dump entry as processed, optionally converting to a task",
        inputSchema: {
          type: "object",
          properties: {
            entryId: { type: "number", description: "Brain dump entry ID" },
            convertToTask: { type: "boolean", description: "Convert to a task" },
            taskCategory: { type: "string", description: "work or personal", enum: ["work", "personal"] },
          },
          required: ["entryId"],
        },
      },
      // =====================================================================
      // PERSONALOS INTEGRATION: PERSONAL TASKS
      // =====================================================================
      {
        name: "workos_get_personal_tasks",
        description: "Get personal (non-work) tasks",
        inputSchema: {
          type: "object",
          properties: {
            status: { type: "string", description: "Filter by status", enum: ["active", "queued", "backlog", "done"] },
            limit: { type: "number", description: "Max tasks (default 20)" },
          },
          required: [],
        },
      },
    ],
  };
});

// =============================================================================
// TOOL HANDLERS
// =============================================================================
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;
  const db = getDb();

  try {
    switch (name) {
      // -----------------------------------------------------------------------
      // GET TODAY METRICS
      // -----------------------------------------------------------------------
      case "workos_get_today_metrics": {
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

      // -----------------------------------------------------------------------
      // GET TASKS (Cache-first with Neon fallback)
      // -----------------------------------------------------------------------
      case "workos_get_tasks": {
        const { status, clientId, limit = 50 } = args as any;

        return withCacheFirst(
          // Cache reader function
          () => {
            // Get tasks from cache (with or without clientId filter)
            const cachedTasks = clientId
              ? getCachedTasksByClient(clientId, status, limit)
              : getCachedTasks(status, limit);

            // Enrich tasks with client names
            const cachedClients = getCachedClients();
            const clientMap = new Map(cachedClients.map(c => [c.id, c.name]));

            return cachedTasks.map(t => ({
              ...t,
              clientName: t.clientId ? clientMap.get(t.clientId) || null : null,
            }));
          },
          // Neon fallback function
          async () => {
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

            return conditions.length > 0
              ? await query.where(and(...conditions))
              : await query;
          },
          "tasks"
        );
      }

      // -----------------------------------------------------------------------
      // GET CLIENTS (Cache-first with Neon fallback)
      // -----------------------------------------------------------------------
      case "workos_get_clients": {
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

      // -----------------------------------------------------------------------
      // CREATE TASK (Write-through: Neon first, then cache)
      // -----------------------------------------------------------------------
      case "workos_create_task": {
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

      // -----------------------------------------------------------------------
      // COMPLETE TASK (Write-through: Neon first, then cache)
      // -----------------------------------------------------------------------
      case "workos_complete_task": {
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

      // -----------------------------------------------------------------------
      // PROMOTE TASK (Write-through: Neon first, then cache)
      // -----------------------------------------------------------------------
      case "workos_promote_task": {
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

      // -----------------------------------------------------------------------
      // GET STREAK
      // -----------------------------------------------------------------------
      case "workos_get_streak": {
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

      // -----------------------------------------------------------------------
      // GET CLIENT MEMORY
      // -----------------------------------------------------------------------
      case "workos_get_client_memory": {
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

      // -----------------------------------------------------------------------
      // DAILY SUMMARY (for Life OS morning brief)
      // -----------------------------------------------------------------------
      case "workos_daily_summary": {
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

      // -----------------------------------------------------------------------
      // UPDATE TASK (Write-through: Neon first, then cache)
      // -----------------------------------------------------------------------
      case "workos_update_task": {
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

      // -----------------------------------------------------------------------
      // DELETE TASK (Write-through: Neon first, then cache)
      // -----------------------------------------------------------------------
      case "workos_delete_task": {
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

      // =====================================================================
      // PERSONALOS: HABITS HANDLERS (Cache-first with Neon fallback)
      // =====================================================================
      case "workos_get_habits": {
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

      case "workos_create_habit": {
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

      case "workos_complete_habit": {
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

      case "workos_get_habit_streaks": {
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

      case "workos_habit_checkin": {
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

      case "workos_habit_dashboard": {
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

      case "workos_recalculate_streaks": {
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

      // =====================================================================
      // PERSONALOS: ENERGY STATE HANDLERS
      // =====================================================================
      case "workos_log_energy": {
        const { level, note, ouraReadiness, ouraHrv, ouraSleep } = args as any;

        const [entry] = await db
          .insert(schema.energyStates)
          .values({
            level,
            source: ouraReadiness ? "oura" : "manual",
            note: note || null,
            ouraReadiness: ouraReadiness || null,
            ouraHrv: ouraHrv || null,
            ouraSleep: ouraSleep || null,
          })
          .returning();

        return {
          content: [{ type: "text", text: JSON.stringify({ success: true, entry }, null, 2) }],
        };
      }

      case "workos_get_energy": {
        const { limit = 5 } = args as any;

        const entries = await db
          .select()
          .from(schema.energyStates)
          .orderBy(desc(schema.energyStates.recordedAt))
          .limit(limit);

        return {
          content: [{ type: "text", text: JSON.stringify(entries, null, 2) }],
        };
      }

      // =====================================================================
      // PERSONALOS: BRAIN DUMP HANDLERS
      // =====================================================================
      case "workos_brain_dump": {
        const { content, category } = args as any;

        const [entry] = await db
          .insert(schema.brainDump)
          .values({
            content,
            category: category || null,
          })
          .returning();

        return {
          content: [{ type: "text", text: JSON.stringify({ success: true, entry }, null, 2) }],
        };
      }

      case "workos_get_brain_dump": {
        const { includeProcessed = false, limit = 20 } = args as any;

        const conditions = includeProcessed ? [] : [eq(schema.brainDump.processed, 0)];

        const query = db
          .select()
          .from(schema.brainDump)
          .orderBy(desc(schema.brainDump.createdAt))
          .limit(limit);

        const entries = conditions.length > 0
          ? await query.where(and(...conditions))
          : await query;

        return {
          content: [{ type: "text", text: JSON.stringify(entries, null, 2) }],
        };
      }

      case "workos_process_brain_dump": {
        const { entryId, convertToTask = false, taskCategory = "personal" } = args as any;

        // Get the entry first
        const [entry] = await db
          .select()
          .from(schema.brainDump)
          .where(eq(schema.brainDump.id, entryId));

        if (!entry) {
          return {
            content: [{ type: "text", text: `Error: Entry ${entryId} not found` }],
            isError: true,
          };
        }

        let taskId = null;

        // Convert to task if requested
        if (convertToTask) {
          const [newTask] = await db
            .insert(schema.tasks)
            .values({
              title: entry.content.substring(0, 100),
              description: entry.content,
              status: "backlog",
              category: taskCategory,
            })
            .returning();
          taskId = newTask.id;
        }

        // Mark as processed
        await db
          .update(schema.brainDump)
          .set({
            processed: 1,
            processedAt: new Date(),
            convertedToTaskId: taskId,
          })
          .where(eq(schema.brainDump.id, entryId));

        return {
          content: [{ type: "text", text: JSON.stringify({ success: true, convertedToTaskId: taskId }, null, 2) }],
        };
      }

      // =====================================================================
      // PERSONALOS: PERSONAL TASKS HANDLER
      // =====================================================================
      case "workos_get_personal_tasks": {
        const { status, limit = 20 } = args as any;

        const conditions = [eq(schema.tasks.category, "personal")];
        if (status) conditions.push(eq(schema.tasks.status, status));

        const tasks = await db
          .select()
          .from(schema.tasks)
          .where(and(...conditions))
          .orderBy(asc(schema.tasks.sortOrder), desc(schema.tasks.createdAt))
          .limit(limit);

        return {
          content: [{ type: "text", text: JSON.stringify(tasks, null, 2) }],
        };
      }

      default:
        return {
          content: [{ type: "text", text: `Unknown tool: ${name}` }],
          isError: true,
        };
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
      isError: true,
    };
  }
});

// =============================================================================
// START SERVER
// =============================================================================
async function main() {
  // Initialize cache at startup (non-blocking)
  ensureCache().then(success => {
    if (success) {
      const stats = getCacheStats();
      console.error(`[Cache] Ready: ${stats.taskCount} tasks, ${stats.clientCount} clients, last sync: ${stats.lastSyncAt || "never"}`);
    }
  }).catch(err => {
    console.error("[Cache] Startup initialization failed:", err);
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("WorkOS MCP server running on stdio");
}

main().catch(console.error);
