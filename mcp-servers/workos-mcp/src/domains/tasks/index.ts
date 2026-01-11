import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getTaskTools } from "./tools.js";

// =============================================================================
// TASK DOMAIN MODULE
// =============================================================================

/**
 * Export task tools for registration with MCP server
 */
export const taskTools = getTaskTools();

/**
 * Routes task tool calls to appropriate handlers
 * Router implementation will be added in subtask-2.4
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
  // Router implementation will be added in subtask-2.4
  return errorResponse(`Task handler not yet implemented: ${name}`);
};
