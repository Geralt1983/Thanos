#!/usr/bin/env node
// =============================================================================
// MEMORY V2 MCP SERVER - MAIN ENTRY POINT
// Exposes Thanos Memory V2 with heat-based ranking through MCP
// =============================================================================

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Import tool definitions and handlers
import { memorySearchTool, handleMemorySearch } from "./tools/search.js";
import { memoryAddTool, handleMemoryAdd } from "./tools/add.js";
import { memoryContextTool, handleMemoryContext } from "./tools/context.js";
import { memoryWhatsHotTool, handleMemoryWhatsHot } from "./tools/hot.js";
import { memoryWhatsColdTool, handleMemoryWhatsCold } from "./tools/cold.js";
import { memoryPinTool, handleMemoryPin } from "./tools/pin.js";
import { memoryStatsTool, handleMemoryStats } from "./tools/stats.js";

// Import error response helper
import { errorResponse } from "./shared/types.js";

// =============================================================================
// SERVER CONFIGURATION
// =============================================================================

const SERVER_NAME = "memory-v2-mcp";
const SERVER_VERSION = "1.0.0";

// =============================================================================
// SERVER INITIALIZATION
// =============================================================================

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

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    return {
      tools: [
        memorySearchTool,
        memoryAddTool,
        memoryContextTool,
        memoryWhatsHotTool,
        memoryWhatsColdTool,
        memoryPinTool,
        memoryStatsTool,
      ],
    };
  });

  // =============================================================================
  // TOOL EXECUTION HANDLER
  // =============================================================================

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case "thanos_memory_search":
          return await handleMemorySearch(args || {});

        case "thanos_memory_add":
          return await handleMemoryAdd(args || {});

        case "thanos_memory_context":
          return await handleMemoryContext(args || {});

        case "thanos_memory_whats_hot":
          return await handleMemoryWhatsHot(args || {});

        case "thanos_memory_whats_cold":
          return await handleMemoryWhatsCold(args || {});

        case "thanos_memory_pin":
          return await handleMemoryPin(args || {});

        case "thanos_memory_stats":
          return await handleMemoryStats(args || {});

        default:
          return errorResponse(`Unknown tool: ${name}`, { toolName: name });
      }
    } catch (error: any) {
      return errorResponse(`Error executing tool ${name}`, {
        toolName: name,
        error: error.message,
        stack: error.stack,
      });
    }
  });

  // =============================================================================
  // TRANSPORT SETUP
  // =============================================================================

  const transport = new StdioServerTransport();
  await server.connect(transport);

  // Log server start (to stderr to not interfere with stdio communication)
  console.error(`${SERVER_NAME} v${SERVER_VERSION} running on stdio`);
  console.error(`Available tools: 7`);
  console.error(`  - thanos_memory_search`);
  console.error(`  - thanos_memory_add`);
  console.error(`  - thanos_memory_context`);
  console.error(`  - thanos_memory_whats_hot`);
  console.error(`  - thanos_memory_whats_cold`);
  console.error(`  - thanos_memory_pin`);
  console.error(`  - thanos_memory_stats`);
}

// =============================================================================
// ERROR HANDLING & STARTUP
// =============================================================================

main().catch((error) => {
  console.error("Fatal error starting server:", error);
  process.exit(1);
});
