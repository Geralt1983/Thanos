import type { ToolDefinition } from "../../shared/types.js";

// =============================================================================
// BRAIN DUMP DOMAIN - TOOL DEFINITIONS
// =============================================================================

/**
 * Returns all brain dump tool definitions for MCP server registration
 *
 * @returns Array of brain dump tool definitions
 */
export function getBrainDumpTools(): ToolDefinition[] {
  return [
    {
      name: "workos_brain_dump",
      description: "Quick capture a thought, idea, or worry. Low friction - just dump it.",
      inputSchema: {
        type: "object",
        properties: {
          content: { type: "string", description: "The thought to capture" },
          category: { type: "string", description: "thought, task, idea, worry", enum: ["thought", "task", "idea", "worry"] },
        },
        required: ["content"],
      },
    },
    {
      name: "workos_get_brain_dump",
      description: "Get unprocessed brain dump entries",
      inputSchema: {
        type: "object",
        properties: {
          includeProcessed: { type: "boolean", description: "Include already processed items" },
          limit: { type: "number", description: "Max entries (default 20)" },
        },
        required: [],
      },
    },
    {
      name: "workos_process_brain_dump",
      description: "Mark a brain dump entry as processed, optionally converting to a task",
      inputSchema: {
        type: "object",
        properties: {
          entryId: { type: "number", description: "Brain dump entry ID" },
          convertToTask: { type: "boolean", description: "Convert to a task" },
          taskCategory: { type: "string", description: "work or personal", enum: ["work", "personal"] },
        },
        required: ["entryId"],
      },
    },
  ];
}
