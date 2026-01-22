// =============================================================================
// WHAT'S COLD TOOL
// Get lowest-heat memories (neglected)
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memoryWhatsColdTool: ToolDefinition = {
  name: "thanos_memory_whats_cold",
  description:
    "What am I neglecting? Returns lowest-heat memories. " +
    "Use for: 'What am I forgetting?', 'Neglected tasks/clients', " +
    "'Cold leads', 'Things I should revisit'. " +
    "Great for ADHD review - surfaces things that may have slipped through the cracks.",
  inputSchema: {
    type: "object",
    properties: {
      threshold: {
        type: "number",
        description: "Heat threshold (memories below this, default 0.2)",
      },
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

export async function handleMemoryWhatsCold(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_whats_cold", {
      threshold: args.threshold || 0.2,
      limit: args.limit || 10,
    });

    return successResponse({
      title: "What's Cold - Potentially Neglected",
      description: "Low-heat memories that may need attention",
      threshold: args.threshold || 0.2,
      memories: result,
      count: Array.isArray(result) ? result.length : 0,
    });
  } catch (error: any) {
    return errorResponse("Failed to get cold memories", {
      error: error.message,
    });
  }
}
