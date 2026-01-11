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
  ];
}
