import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getHabitTools } from "./tools.js";
import {
  handleGetHabits,
  handleCreateHabit,
  handleCompleteHabit,
  handleGetHabitStreaks,
  handleHabitCheckin,
  handleHabitDashboard,
  handleRecalculateStreaks,
  handleDeleteHabit,
} from "./handlers.js";

// =============================================================================
// HABIT DOMAIN MODULE
// =============================================================================

/**
 * Export habit tools for registration with MCP server
 */
export const habitTools = getHabitTools();

/**
 * Routes habit tool calls to appropriate handlers
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
  switch (name) {
    case "workos_get_habits":
      return handleGetHabits(args, db);
    case "workos_create_habit":
      return handleCreateHabit(args, db);
    case "workos_complete_habit":
      return handleCompleteHabit(args, db);
    case "workos_get_habit_streaks":
      return handleGetHabitStreaks(args, db);
    case "workos_habit_checkin":
      return handleHabitCheckin(args, db);
    case "workos_habit_dashboard":
      return handleHabitDashboard(args, db);
    case "workos_recalculate_streaks":
      return handleRecalculateStreaks(args, db);
    case "workos_delete_habit":
      return handleDeleteHabit(args, db);
    default:
      return errorResponse(`Unknown habit tool: ${name}`);
  }
};
