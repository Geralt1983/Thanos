/**
 * Tool handler implementations
 *
 * This file contains the actual logic for each tool.
 * In a real server, you would replace the mock data with actual API calls.
 */

import { z } from "zod";
import { logger } from "../utils/logger.js";
import { requireWriteAccess } from "../utils/validation.js";

// Mock task database (replace with real API client)
interface Task {
  id: string;
  title: string;
  description?: string;
  status: "active" | "completed";
  priority: "low" | "medium" | "high";
  created_at: string;
  completed_at?: string;
}

const mockTasks: Map<string, Task> = new Map([
  [
    "task-1",
    {
      id: "task-1",
      title: "Example task 1",
      description: "This is a sample task",
      status: "active",
      priority: "high",
      created_at: new Date().toISOString(),
    },
  ],
  [
    "task-2",
    {
      id: "task-2",
      title: "Example task 2",
      status: "completed",
      priority: "medium",
      created_at: new Date(Date.now() - 86400000).toISOString(),
      completed_at: new Date().toISOString(),
    },
  ],
]);

// Validation schemas
const listSchema = z.object({
  status: z.enum(["active", "completed", "all"]).optional().default("active"),
  limit: z.number().min(1).max(100).optional().default(10),
  priority: z.enum(["low", "medium", "high"]).optional(),
});

const getSchema = z.object({
  task_id: z.string().min(1),
});

const createSchema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().max(2000).optional(),
  priority: z.enum(["low", "medium", "high"]).optional().default("medium"),
});

const updateSchema = z.object({
  task_id: z.string().min(1),
  title: z.string().min(1).max(200).optional(),
  description: z.string().max(2000).optional(),
  status: z.enum(["active", "completed"]).optional(),
  priority: z.enum(["low", "medium", "high"]).optional(),
});

const deleteSchema = z.object({
  task_id: z.string().min(1),
});

/**
 * Main tool handler router
 */
export async function handleTaskTool(name: string, args: unknown) {
  switch (name) {
    case "task_list":
      return await handleTaskList(args);
    case "task_get":
      return await handleTaskGet(args);
    case "task_create":
      return await handleTaskCreate(args);
    case "task_update":
      return await handleTaskUpdate(args);
    case "task_delete":
      return await handleTaskDelete(args);
    default:
      throw new Error(`Unknown task tool: ${name}`);
  }
}

/**
 * List tasks with filtering
 */
async function handleTaskList(args: unknown) {
  const params = listSchema.parse(args);
  logger.debug(`Listing tasks with params:`, params);

  // Filter tasks
  let tasks = Array.from(mockTasks.values());

  // Filter by status
  if (params.status !== "all") {
    tasks = tasks.filter((t) => t.status === params.status);
  }

  // Filter by priority
  if (params.priority) {
    tasks = tasks.filter((t) => t.priority === params.priority);
  }

  // Apply limit
  tasks = tasks.slice(0, params.limit);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            tasks,
            count: tasks.length,
            filters: params,
          },
          null,
          2
        ),
      },
    ],
  };
}

/**
 * Get a specific task
 */
async function handleTaskGet(args: unknown) {
  const params = getSchema.parse(args);
  logger.debug(`Getting task: ${params.task_id}`);

  const task = mockTasks.get(params.task_id);
  if (!task) {
    throw new Error(`Task not found: ${params.task_id}`);
  }

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(task, null, 2),
      },
    ],
  };
}

/**
 * Create a new task
 */
async function handleTaskCreate(args: unknown) {
  requireWriteAccess();

  const params = createSchema.parse(args);
  logger.info(`Creating task: ${params.title}`);

  // Create task
  const task: Task = {
    id: `task-${Date.now()}`,
    title: params.title,
    description: params.description,
    status: "active",
    priority: params.priority,
    created_at: new Date().toISOString(),
  };

  // Save to database (mock)
  mockTasks.set(task.id, task);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            message: "Task created successfully",
            task,
          },
          null,
          2
        ),
      },
    ],
  };
}

/**
 * Update an existing task
 */
async function handleTaskUpdate(args: unknown) {
  requireWriteAccess();

  const params = updateSchema.parse(args);
  logger.info(`Updating task: ${params.task_id}`);

  // Get existing task
  const task = mockTasks.get(params.task_id);
  if (!task) {
    throw new Error(`Task not found: ${params.task_id}`);
  }

  // Update fields
  if (params.title !== undefined) {
    task.title = params.title;
  }
  if (params.description !== undefined) {
    task.description = params.description;
  }
  if (params.status !== undefined) {
    task.status = params.status;
    if (params.status === "completed" && !task.completed_at) {
      task.completed_at = new Date().toISOString();
    }
  }
  if (params.priority !== undefined) {
    task.priority = params.priority;
  }

  // Save to database (mock)
  mockTasks.set(task.id, task);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            message: "Task updated successfully",
            task,
          },
          null,
          2
        ),
      },
    ],
  };
}

/**
 * Delete a task
 */
async function handleTaskDelete(args: unknown) {
  requireWriteAccess();

  const params = deleteSchema.parse(args);
  logger.info(`Deleting task: ${params.task_id}`);

  // Check if task exists
  if (!mockTasks.has(params.task_id)) {
    throw new Error(`Task not found: ${params.task_id}`);
  }

  // Delete from database (mock)
  mockTasks.delete(params.task_id);

  return {
    content: [
      {
        type: "text",
        text: JSON.stringify({
          message: "Task deleted successfully",
          task_id: params.task_id,
        }),
      },
    ],
  };
}
