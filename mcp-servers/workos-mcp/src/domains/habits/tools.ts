import type { ToolDefinition } from "../../shared/types.js";

// =============================================================================
// HABIT DOMAIN TOOL DEFINITIONS
// =============================================================================

/**
 * Habit tool definitions will be added in subtask-3.2
 * This file contains MCP tool definitions for the 7 habit-related tools:
 * - workos_get_habits
 * - workos_create_habit
 * - workos_complete_habit
 * - workos_get_habit_streaks
 * - workos_habit_checkin
 * - workos_habit_dashboard
 * - workos_recalculate_streaks
 */

/**
 * Returns all habit tool definitions
 * @returns Array of habit tool definitions for MCP protocol
 */
export function getHabitTools(): ToolDefinition[] {
  return [
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
  ];
}
