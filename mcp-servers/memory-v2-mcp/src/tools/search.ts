// =============================================================================
// MEMORY SEARCH TOOL
// Search memories with heat-based ranking
// =============================================================================

import type { ToolDefinition, ContentResponse } from "../shared/types.js";
import { successResponse, errorResponse } from "../shared/types.js";
import { executePythonTool } from "../python-bridge.js";

// =============================================================================
// TOOL DEFINITION
// =============================================================================

export const memorySearchTool: ToolDefinition = {
  name: "thanos_memory_search",
  description:
    "Search Jeremy's memories for relevant context. Uses semantic similarity search, " +
    "re-ranked by heat score. Recent and frequently-accessed memories rank higher. " +
    "Returns memories with relevance scores and heat indicators.",
  inputSchema: {
    type: "object",
    properties: {
      query: {
        type: "string",
        description: "Natural language search query (e.g., 'Orlando project status')",
      },
      limit: {
        type: "number",
        description: "Maximum results to return (default 10)",
      },
      client: {
        type: "string",
        description: "Optional filter by client name",
      },
      source: {
        type: "string",
        description: "Optional filter by source (hey_pocket, telegram, manual)",
      },
    },
    required: ["query"],
  },
};

// =============================================================================
// HANDLER
// =============================================================================

export async function handleMemorySearch(
  args: Record<string, any>
): Promise<ContentResponse> {
  try {
    const result = await executePythonTool("memory_search", {
      query: args.query,
      limit: args.limit || 10,
      client: args.client || null,
      source: args.source || null,
    });

    return successResponse({
      query: args.query,
      results: result,
      count: Array.isArray(result) ? result.length : 0,
    });
  } catch (error: any) {
    return errorResponse("Failed to search memories", {
      query: args.query,
      error: error.message,
    });
  }
}
