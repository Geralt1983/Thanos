import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getPersonalTasksTools } from "./tools.js";
import { handleGetPersonalTasks } from "./handlers.js";

// =============================================================================
// PERSONAL TASKS DOMAIN MODULE
// =============================================================================

/**
 * Export personal tasks tools for registration with MCP server
 */
export const personalTasksTools = getPersonalTasksTools();

/**
 * Routes personal tasks tool calls to appropriate handlers
 *
 * @param name - Personal tasks tool name
 * @param args - Tool-specific arguments
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export const handlePersonalTasksTool: ToolRouter = async (
  name: string,
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  switch (name) {
    case "life_get_personal_tasks":
      return handleGetPersonalTasks(args, db);
    default:
      return errorResponse(`Unknown personal tasks tool: ${name}`);
  }
};
