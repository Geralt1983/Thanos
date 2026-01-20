import type { ToolDefinition } from "../../shared/types.js";

// =============================================================================
// PERSONAL TASKS DOMAIN TOOL DEFINITIONS
// =============================================================================

/**
 * Returns all personal tasks tool definitions
 * @returns Array of personal tasks tool definitions for MCP protocol
 */
export function getPersonalTasksTools(): ToolDefinition[] {
  return [
    {
      name: "life_get_personal_tasks",
      description: "Get personal (non-work) tasks",
      inputSchema: {
        type: "object",
        properties: {
          status: { type: "string", description: "Filter by status", enum: ["active", "queued", "backlog", "done"] },
          limit: { type: "number", description: "Max tasks (default 20)" },
        },
        required: [],
      },
    },
  ];
}
