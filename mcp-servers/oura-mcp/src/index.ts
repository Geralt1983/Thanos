#!/usr/bin/env node
// =============================================================================
// OURA MCP SERVER - MAIN ENTRY POINT
// Exposes Oura Ring health metrics through Model Context Protocol
// =============================================================================

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Import tool definitions and handlers
import {
  getTodayReadinessTool,
  handleGetTodayReadiness,
} from "./tools/readiness.js";
import {
  getSleepSummaryTool,
  handleGetSleepSummary,
} from "./tools/sleep.js";
import {
  getWeeklyTrendsTool,
  handleGetWeeklyTrends,
} from "./tools/trends.js";
import {
  healthCheckTool,
  handleHealthCheck,
} from "./tools/health-check.js";

// Import error response helper
import { errorResponse } from "./shared/types.js";

// Import database utilities for graceful shutdown
import { registerShutdownHandlers } from "./cache/db.js";

// =============================================================================
// SERVER CONFIGURATION
// =============================================================================

const SERVER_NAME = "oura-mcp";
const SERVER_VERSION = "1.0.0";

// =============================================================================
// SERVER INITIALIZATION
// =============================================================================

/**
 * Initialize and start the MCP server
 */
async function main() {
  // Create MCP server instance
  const server = new Server(
    {
      name: SERVER_NAME,
      version: SERVER_VERSION,
    },
    {
      capabilities: {
        tools: {},
      },
    }
  );

  // =============================================================================
  // TOOL LISTING HANDLER
  // =============================================================================

  /**
   * Handle list_tools request
   * Returns all available tools this server provides
   */
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        getTodayReadinessTool,
        getSleepSummaryTool,
        getWeeklyTrendsTool,
        healthCheckTool,
      ],
    };
  });

  // =============================================================================
  // TOOL EXECUTION HANDLER
  // =============================================================================

  /**
   * Handle call_tool request
   * Routes to appropriate tool handler based on tool name
   */
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      // Route to appropriate handler
      switch (name) {
        case "oura_get_today_readiness":
          return await handleGetTodayReadiness(args || {});

        case "oura_get_sleep_summary":
          return await handleGetSleepSummary(args || {});

        case "oura_get_weekly_trends":
          return await handleGetWeeklyTrends(args || {});

        case "oura_health_check":
          return await handleHealthCheck(args || {});

        default:
          return errorResponse(`Unknown tool: ${name}`, { toolName: name });
      }
    } catch (error: any) {
      // Catch any unexpected errors during tool execution
      return errorResponse(
        `Error executing tool ${name}`,
        {
          toolName: name,
          error: error.message,
          stack: error.stack,
        }
      );
    }
  });

  // =============================================================================
  // TRANSPORT SETUP
  // =============================================================================

  /**
   * Set up stdio transport for communication
   * MCP uses stdio for server-client communication
   */
  const transport = new StdioServerTransport();

  // Connect server to transport
  await server.connect(transport);

  // Log server start (to stderr to not interfere with stdio communication)
  console.error(
    `${SERVER_NAME} v${SERVER_VERSION} running on stdio`
  );
  console.error(`Available tools: 4`);
  console.error(`  - oura_get_today_readiness`);
  console.error(`  - oura_get_sleep_summary`);
  console.error(`  - oura_get_weekly_trends`);
  console.error(`  - oura_health_check`);
}

// =============================================================================
// ERROR HANDLING & STARTUP
// =============================================================================

// Register graceful shutdown handlers (closes database on SIGINT/SIGTERM)
registerShutdownHandlers();

// Start the server
main().catch((error) => {
  console.error("Fatal error starting server:", error);
  process.exit(1);
});
