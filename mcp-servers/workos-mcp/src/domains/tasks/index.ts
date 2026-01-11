import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getTaskTools } from "./tools.js";
import {
  handleGetTodayMetrics,
  handleGetTasks,
  handleGetClients,
  handleCreateTask,
  handleCompleteTask,
  handlePromoteTask,
  handleGetStreak,
  handleGetClientMemory,
  handleDailySummary,
  handleUpdateTask,
  handleDeleteTask,
} from "./handlers.js";

// =============================================================================
// TASK DOMAIN MODULE
// =============================================================================

/**
 * Export task tools for registration with MCP server
 */
export const taskTools = getTaskTools();

/**
 * Routes task tool calls to appropriate handlers
 *
 * @param name - Task tool name
 * @param args - Tool-specific arguments
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export const handleTaskTool: ToolRouter = async (
  name: string,
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  switch (name) {
    case "workos_get_today_metrics":
      return handleGetTodayMetrics(args, db);
    case "workos_get_tasks":
      return handleGetTasks(args, db);
    case "workos_get_clients":
      return handleGetClients(args, db);
    case "workos_create_task":
      return handleCreateTask(args, db);
    case "workos_complete_task":
      return handleCompleteTask(args, db);
    case "workos_promote_task":
      return handlePromoteTask(args, db);
    case "workos_get_streak":
      return handleGetStreak(args, db);
    case "workos_get_client_memory":
      return handleGetClientMemory(args, db);
    case "workos_daily_summary":
      return handleDailySummary(args, db);
    case "workos_update_task":
      return handleUpdateTask(args, db);
    case "workos_delete_task":
      return handleDeleteTask(args, db);
    default:
      return errorResponse(`Unknown task tool: ${name}`);
  }
};
