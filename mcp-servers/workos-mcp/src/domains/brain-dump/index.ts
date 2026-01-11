import type { ToolRouter, Database, ContentResponse } from "../../shared/types.js";
import { errorResponse } from "../../shared/types.js";
import { getBrainDumpTools } from "./tools.js";
import {
  handleBrainDump,
  handleGetBrainDump,
  handleProcessBrainDump,
} from "./handlers.js";

// =============================================================================
// BRAIN DUMP DOMAIN MODULE
// =============================================================================

/**
 * Export brain dump tools for registration with MCP server
 */
export const brainDumpTools = getBrainDumpTools();

/**
 * Routes brain dump tool calls to appropriate handlers
 *
 * @param name - Brain dump tool name
 * @param args - Tool-specific arguments
 * @param db - Database instance
 * @returns Promise resolving to MCP ContentResponse
 */
export const handleBrainDumpTool: ToolRouter = async (
  name: string,
  args: Record<string, any>,
  db: Database
): Promise<ContentResponse> => {
  switch (name) {
    case "workos_brain_dump":
      return handleBrainDump(args, db);
    case "workos_get_brain_dump":
      return handleGetBrainDump(args, db);
    case "workos_process_brain_dump":
      return handleProcessBrainDump(args, db);
    default:
      return errorResponse(`Unknown brain dump tool: ${name}`);
  }
};
