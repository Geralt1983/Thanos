// =============================================================================
// MEMORY PIN TOOL
// Pin a memory so it never decays
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memoryPinTool: ToolDefinition = {
  name: "thanos_memory_pin",
  description:
    "Pin a memory so it never decays (critical info). " +
    "Use for: important personal facts, critical client requirements, " +
    "key decisions that must not be forgotten. " +
    "Pinned memories maintain high heat regardless of access patterns.",
  inputSchema: {
    type: "object",
    properties: {
      memory_id: {
        type: "string",
        description: "UUID of the memory to pin",
      },
    },
    required: ["memory_id"],
  },
};

// =============================================================================
// HANDLER
// =============================================================================

export async function handleMemoryPin(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_pin", {
      memory_id: args.memory_id,
    });

    return successResponse({
      success: result.success,
      message: result.success
        ? `Memory ${args.memory_id} pinned successfully`
        : `Failed to pin memory ${args.memory_id}`,
      memory_id: args.memory_id,
    });
  } catch (error: any) {
    return errorResponse("Failed to pin memory", {
      memory_id: args.memory_id,
      error: error.message,
    });
  }
}
