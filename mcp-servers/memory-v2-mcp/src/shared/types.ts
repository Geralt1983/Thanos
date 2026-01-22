import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";

// =============================================================================
// MCP TOOL TYPES
// =============================================================================

/**
 * MCP Tool Definition
 */
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, any>;
    required: string[];
  };
}

/**
 * MCP Content Response
 */
export type ContentResponse = CallToolResult;

/**
 * Tool Handler Function Signature
 */
export type ToolHandler = (
  args: Record<string, any>
) => Promise<ContentResponse>;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Helper function to create a success response
 */
export function successResponse(data: any): ContentResponse {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(data, null, 2),
      },
    ],
  };
}

/**
 * Helper function to create an error response
 */
export function errorResponse(message: string, details?: any): ContentResponse {
  return {
    content: [
      {
        type: "text",
        text: JSON.stringify(
          {
            error: message,
            ...(details && { details }),
          },
          null,
          2
        ),
      },
    ],
  };
}
