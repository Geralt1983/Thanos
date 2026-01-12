import type { ToolDefinition } from "../../shared/types.js";

// =============================================================================
// ENERGY DOMAIN TOOL DEFINITIONS
// =============================================================================

/**
 * Returns all energy tool definitions
 * @returns Array of energy tool definitions for MCP protocol
 */
export function getEnergyTools(): ToolDefinition[] {
  return [
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
    {
      name: "workos_override_energy_suggestion",
      description: "Manually override auto-detected energy level or task suggestions. Records override reason for learning and algorithm improvement.",
      inputSchema: {
        type: "object",
        properties: {
          energyLevel: {
            type: "string",
            description: "Manual energy level override (high/medium/low)",
            enum: ["high", "medium", "low"],
          },
          reason: {
            type: "string",
            description: "Why are you overriding? (e.g. 'Feel more energized than readiness suggests', 'Need to push through despite low energy', 'Readiness doesn't account for coffee/medication')",
          },
          taskId: {
            type: "number",
            description: "Optional task ID if overriding a specific task suggestion",
          },
          adjustDailyGoal: {
            type: "boolean",
            description: "Whether to recalculate today's daily goal based on the manual energy level (default: true)",
          },
        },
        required: ["energyLevel", "reason"],
      },
    },
  ];
}
