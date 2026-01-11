import type { NeonHttpDatabase } from "drizzle-orm/neon-http";
import type { CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import * as schema from "../schema.js";

// =============================================================================
// DATABASE TYPES
// =============================================================================

/**
 * Database instance type with schema
 */
export type Database = NeonHttpDatabase<typeof schema>;

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
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export type ToolHandler = (
  args: Record<string, any>,
  db: Database
) => Promise<ContentResponse>;

/**
 * Tool Router Function Signature
 * Routes tool calls to appropriate handlers based on tool name
 * @param name - Tool name
 * @param args - Tool-specific arguments
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export type ToolRouter = (
  name: string,
  args: Record<string, any>,
  db: Database
) => Promise<ContentResponse>;

// =============================================================================
// COMMON ARGUMENT TYPES
// =============================================================================

/**
 * Common arguments for task filtering
 */
export interface TaskFilterArgs {
  status?: "active" | "queued" | "backlog" | "done";
  clientId?: number;
  limit?: number;
}

/**
 * Common arguments for creating/updating tasks
 */
export interface TaskMutationArgs {
  title?: string;
  description?: string;
  clientId?: number;
  status?: "active" | "queued" | "backlog";
  category?: "work" | "personal";
  valueTier?: "checkbox" | "progress" | "deliverable" | "milestone";
  drainType?: "deep" | "shallow" | "admin";
  effortEstimate?: number;
  pointsFinal?: number;
}

/**
 * Common arguments for habit operations
 */
export interface HabitArgs {
  name?: string;
  description?: string;
  emoji?: string;
  frequency?: "daily" | "weekdays" | "weekly";
  category?: string;
  timeOfDay?: "morning" | "evening" | "anytime";
}

// =============================================================================
// UTILITY TYPES
// =============================================================================

/**
 * Helper type to create a success response
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
 * Helper type to create an error response
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
