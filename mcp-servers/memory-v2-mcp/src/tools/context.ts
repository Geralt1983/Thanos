// =============================================================================
// MEMORY CONTEXT TOOL
// Get formatted context for prompt injection
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memoryContextTool: ToolDefinition = {
  name: "thanos_memory_context",
  description:
    "Get formatted context for a query (for prompt injection). " +
    "Returns a formatted string of relevant memories suitable for " +
    "including in prompts. Each memory includes heat indicator: " +
    "fire = hot (active focus), bullet = warm (normal), snowflake = cold (neglected).",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "What context is needed for",
      },
      limit: {
        type: "number",
        description: "Maximum memories to include (default 10)",
      },
    },
    required: ["query"],
  },
};

// =============================================================================
// HANDLER
// =============================================================================

export async function handleMemoryContext(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_context", {
      query: args.query,
      limit: args.limit || 10,
    });

    // Result is already a formatted string
    return successResponse({
      query: args.query,
      context: result,
    });
  } catch (error: any) {
    return errorResponse("Failed to get memory context", {
      query: args.query,
      error: error.message,
    });
  }
}
