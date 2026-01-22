// =============================================================================
// WHAT'S HOT TOOL
// Get highest-heat memories (current focus)
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memoryWhatsHotTool: ToolDefinition = {
  name: "thanos_memory_whats_hot",
  description:
    "What's top of mind? Returns highest-heat memories. " +
    "Use for: 'What am I focused on?', 'Current priorities', 'Recent context'. " +
    "Heat indicates recent activity and access frequency.",
  inputSchema: {
    type: "object",
    properties: {
      limit: {
        type: "number",
        description: "Maximum results (default 10)",
      },
    },
    required: [],
  },
};

// =============================================================================
// HANDLER
// =============================================================================

export async function handleMemoryWhatsHot(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_whats_hot", {
      limit: args.limit || 10,
    });

    return successResponse({
      title: "What's Hot - Current Focus",
      description: "Highest-heat memories (recently accessed/mentioned)",
      memories: result,
      count: Array.isArray(result) ? result.length : 0,
    });
  } catch (error: any) {
    return errorResponse("Failed to get hot memories", {
      error: error.message,
    });
  }
}
