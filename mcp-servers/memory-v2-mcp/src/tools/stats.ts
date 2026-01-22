// =============================================================================
// MEMORY STATS TOOL
// Get memory system statistics
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memoryStatsTool: ToolDefinition = {
  name: "thanos_memory_stats",
  description:
    "Get memory system statistics including total memories, " +
    "average heat, hot/cold counts, and unique clients/projects. " +
    "Useful for understanding the current state of the memory system.",
  inputSchema: {
    type: "object",
    properties: {},
    required: [],
  },
};

// =============================================================================
// HANDLER
// =============================================================================

export async function handleMemoryStats(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_stats", {});

    return successResponse({
      title: "Memory System Statistics",
      stats: result,
    });
  } catch (error: any) {
    return errorResponse("Failed to get memory stats", {
      error: error.message,
    });
  }
}
