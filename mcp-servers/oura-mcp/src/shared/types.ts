import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";

// =============================================================================
// MCP TOOL TYPES
// =============================================================================

/**
 * MCP Tool Definition
 * Defines the structure of a tool that can be called via MCP protocol
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
 * Standard response format for MCP tool handlers
 * Using the official CallToolResult type from the MCP SDK
 */
export type ContentResponse = CallToolResult;

/**
 * Tool Handler Function Signature
 * Standard signature for all tool handler functions
 * @param args - Tool-specific arguments
 * @returns Promise resolving to MCP ContentResponse
 */
export type ToolHandler = (
  args: Record<string, any>
) => Promise<ContentResponse>;

/**
 * Tool Router Function Signature
 * Routes tool calls to appropriate handlers based on tool name
 * @param name - Tool name
 * @param args - Tool-specific arguments
 * @returns Promise resolving to MCP ContentResponse
 */
export type ToolRouter = (
  name: string,
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
