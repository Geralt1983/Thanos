import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getHabitTools } from "./tools.js";

// =============================================================================
// HABIT DOMAIN MODULE
// =============================================================================

/**
 * Export habit tools for registration with MCP server
 */
export const habitTools = getHabitTools();

/**
 * Routes habit tool calls to appropriate handlers
 * Router implementation will be completed in subtask-3.4
 *
 * @param name - Habit tool name
 * @param args - Tool-specific arguments
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export const handleHabitTool: ToolRouter = async (
  name: string,
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  // Router logic will be implemented in subtask-3.4
  return errorResponse(`Habit tool routing not yet implemented: ${name}`);
};
