import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getEnergyTools } from "./tools.js";
import {
  handleLogEnergy,
  handleGetEnergy,
  handleOverrideEnergySuggestion,
  handleProvideEnergyFeedback,
} from "./handlers.js";

// =============================================================================
// ENERGY DOMAIN MODULE
// =============================================================================

/**
 * Export energy tools for registration with MCP server
 */
export const energyTools = getEnergyTools();

/**
 * Routes energy tool calls to appropriate handlers
 *
 * @param name - Energy tool name
 * @param args - Tool-specific arguments
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export const handleEnergyTool: ToolRouter = async (
  name: string,
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  switch (name) {
    case "workos_log_energy":
      return handleLogEnergy(args, db);
    case "workos_get_energy":
      return handleGetEnergy(args, db);
    case "workos_override_energy_suggestion":
      return handleOverrideEnergySuggestion(args, db);
    case "workos_provide_energy_feedback":
      return handleProvideEnergyFeedback(args, db);
    default:
      return errorResponse(`Unknown energy tool: ${name}`);
  }
};
