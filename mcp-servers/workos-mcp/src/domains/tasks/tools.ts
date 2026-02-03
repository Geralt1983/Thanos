import type { ToolDefinition } from "../../shared/types.js";

// =============================================================================
// TASK DOMAIN TOOL DEFINITIONS
// =============================================================================

/**
 * Task tool definitions will be added in subtask-2.2
 * This file contains MCP tool definitions for the 12 task-related tools:
 * - workos_get_server_version
 * - workos_get_today_metrics
 * - workos_get_tasks
 * - workos_get_clients
 * - workos_create_task
 * - workos_complete_task
 * - workos_promote_task
 * - workos_get_streak
 * - workos_get_client_memory
 * - workos_daily_summary
 * - workos_update_task
 * - workos_delete_task
 */

/**
 * Returns all task tool definitions
 * @returns Array of task tool definitions for MCP protocol
 */
export function getTaskTools(): ToolDefinition[] {
  return [
    {
      name: "workos_get_server_version",
      description: "Get WorkOS MCP server version and compatibility metadata",
      inputSchema: {
        type: "object",
        properties: {},
        required: [],
      },
    },
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
      name: "workos_get_metrics_for_date",
      description: "Get work metrics for a specific date: points earned, tasks completed, clients touched. Use for historical lookups (e.g., 'what did I earn yesterday?')",
      inputSchema: {
        type: "object",
        properties: {
          date: {
            type: "string",
            description: "Date in YYYY-MM-DD format (e.g., '2026-01-30')",
          },
        },
        required: ["date"],
      },
    },
    {
      name: "workos_get_tasks",
      description: "Get tasks from WorkOS. Filter by status: 'active' (today), 'queued' (up next), 'backlog', or 'done'. Can filter by clientId (number) or clientName (string like 'Orlando')",
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
            description: "Filter by client ID (integer)",
          },
          clientName: {
            type: "string",
            description: "Filter by client name (case-insensitive, e.g., 'Orlando', 'Raleigh', 'Memphis')",
          },
          limit: {
            type: "number",
            description: "Max tasks to return (default 50)",
          },
          applyEnergyFilter: {
            type: "boolean",
            description: "Filter tasks based on current energy level - only show tasks with cognitive load matching current energy (default false)",
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
          cognitiveLoad: {
            type: "string",
            description: "Cognitive load: low (admin/simple), medium (standard work), high (complex/deep work)",
            enum: ["low", "medium", "high"],
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
      description: "Update a task's properties (clientId, title, description, status, valueTier, drainType, cognitiveLoad)",
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
          cognitiveLoad: {
            type: "string",
            description: "Cognitive load: low (admin/simple), medium (standard work), high (complex/deep work)",
            enum: ["low", "medium", "high"],
          },
          subtasks: {
            type: "array",
            description: "Array of subtask objects with title and done status",
            items: {
              type: "object",
              properties: {
                title: { type: "string" },
                done: { type: "boolean" },
              },
            },
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
    {
      name: "workos_get_energy_aware_tasks",
      description: "Get tasks prioritized by current energy level. Returns tasks ranked by energy-task match, with high-cognitive tasks suggested on high energy days and low-cognitive tasks on low energy days.",
      inputSchema: {
        type: "object",
        properties: {
          energy_level: {
            type: "string",
            description: "Override current energy level (default: auto-detect from Oura/manual logs)",
            enum: ["low", "medium", "high"],
          },
          limit: {
            type: "number",
            description: "Max tasks to return (default: unlimited)",
          },
        },
        required: [],
      },
    },
    {
      name: "workos_adjust_daily_goal",
      description: "Manually trigger daily goal adjustment based on current energy level. Adjusts target points based on readiness score: <70 reduces by 25%, 70-84 maintains target, 85+ increases by 15%. Returns explanation of adjustment and new target.",
      inputSchema: {
        type: "object",
        properties: {
          baseTarget: {
            type: "number",
            description: "Base daily target points (default: 18)",
          },
        },
        required: [],
      },
    },
  ];
}
