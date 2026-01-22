// =============================================================================
// MEMORY ADD TOOL
// Add new memory with metadata
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memoryAddTool: ToolDefinition = {
  name: "thanos_memory_add",
  description:
    "Add a new memory directly. Content will be processed for fact extraction " +
    "and stored with automatic embedding generation. Use for capturing important " +
    "information, decisions, facts, or patterns.",
  inputSchema: {
    type: "object",
    properties: {
      content: {
        type: "string",
        description: "The content to remember",
      },
      source: {
        type: "string",
        description: "Where this came from (manual, observation, hey_pocket, telegram)",
      },
      memory_type: {
        type: "string",
        description: "Category (note, fact, goal, decision, pattern)",
      },
      client: {
        type: "string",
        description: "Optional client association",
      },
      project: {
        type: "string",
        description: "Optional project association",
      },
      importance: {
        type: "number",
        description: "Manual importance multiplier (0.5 - 2.0)",
      },
    },
    required: ["content"],
  },
};

// =============================================================================
// HANDLER
// =============================================================================

export async function handleMemoryAdd(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_add", {
      content: args.content,
      source: args.source || "manual",
      memory_type: args.memory_type || "note",
      client: args.client || null,
      project: args.project || null,
      importance: args.importance || 1.0,
    });

    return successResponse({
      success: true,
      message: "Memory added successfully",
      result,
    });
  } catch (error: any) {
    return errorResponse("Failed to add memory", {
      content: args.content?.substring(0, 100),
      error: error.message,
    });
  }
}
