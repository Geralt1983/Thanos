#!/usr/bin/env node

/**
 * Custom MCP Server Template
 *
 * This is a complete example of an MCP server that can be customized
 * for your specific use case. It demonstrates:
 * - Proper MCP protocol implementation
 * - Tool definition and handling
 * - Input validation
 * - Error handling
 * - Environment configuration
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from "@modelcontextprotocol/sdk/types.js";

import { taskTools } from "./tools/index.js";
import { handleTaskTool } from "./tools/handlers.js";
import { logger } from "./utils/logger.js";

// Server configuration
const SERVER_NAME = "custom-task-server";
const SERVER_VERSION = "1.0.0";

// Initialize server with capabilities
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

/**
 * Handle tools/list request
 * Returns all available tools
 */
server.setRequestHandler(ListToolsRequestSchema, async () => {
  logger.debug("Listing available tools");

  return {
    tools: taskTools as Tool[],
  };
});

/**
 * Handle tools/call request
 * Routes to appropriate tool handler
 */
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  logger.info(`Tool called: ${name}`);
  logger.debug(`Arguments: ${JSON.stringify(args)}`);

  try {
    // Route to task handler
    if (name.startsWith("task_")) {
      return await handleTaskTool(name, args);
    }

    // Unknown tool
    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logger.error(`Tool execution failed: ${message}`, error);

    return {
      content: [
        {
          type: "text",
          text: `Error: ${message}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Handle server errors
 */
server.onerror = (error) => {
  logger.error("Server error:", error);
};

/**
 * Handle shutdown gracefully
 */
process.on("SIGINT", async () => {
  logger.info("Shutting down server...");
  await server.close();
  process.exit(0);
});

process.on("SIGTERM", async () => {
  logger.info("Shutting down server...");
  await server.close();
  process.exit(0);
});

/**
 * Start the server
 */
async function main() {
  // Validate required environment variables
  const apiKey = process.env.TASK_API_KEY;
  if (!apiKey && process.env.NODE_ENV !== "test") {
    logger.warn("TASK_API_KEY not set - running in demo mode");
  }

  // Connect to stdio transport
  const transport = new StdioServerTransport();
  await server.connect(transport);

  logger.info(`${SERVER_NAME} v${SERVER_VERSION} running on stdio`);
  logger.info(`Debug logging: ${process.env.DEBUG === "true" ? "enabled" : "disabled"}`);
  logger.info(`Write operations: ${process.env.ALLOW_WRITE === "true" ? "enabled" : "disabled"}`);
}

// Run server
main().catch((error) => {
  logger.error("Fatal error:", error);
  process.exit(1);
});
