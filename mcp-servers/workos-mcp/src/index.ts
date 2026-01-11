#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Shared utilities
import { getDb } from "./shared/db.js";

// Cache imports
import {
  initCache,
  getCacheStats,
} from "./cache/cache.js";
import { syncAll } from "./cache/sync.js";

// Domain module imports
import { taskTools, handleTaskTool } from "./domains/tasks/index.js";
import { habitTools, handleHabitTool } from "./domains/habits/index.js";
import { energyTools, handleEnergyTool } from "./domains/energy/index.js";
import { brainDumpTools, handleBrainDumpTool } from "./domains/brain-dump/index.js";
import { personalTasksTools, handlePersonalTasksTool } from "./domains/personal-tasks/index.js";

// =============================================================================
// CACHE LAYER
// =============================================================================
let cacheInitialized = false;

async function ensureCache(): Promise<boolean> {
  if (!cacheInitialized) {
    try {
      initCache();
      cacheInitialized = true;
      console.error("[Cache] SQLite cache initialized");

      // Check if cache is empty or stale
      const stats = getCacheStats();
      if (stats.taskCount === 0 || stats.isStale) {
        console.error("[Cache] Cache empty or stale, syncing from Neon...");
        await syncAll();
      }
    } catch (error) {
      console.error("[Cache] Failed to initialize cache:", error);
      return false;
    }
  }
  return true;
}

// =============================================================================
// MCP SERVER SETUP
// =============================================================================
const server = new Server(
  {
    name: "workos-mcp",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// =============================================================================
// TOOL DEFINITIONS
// =============================================================================
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      ...taskTools,
      ...habitTools,
      ...energyTools,
      ...brainDumpTools,
      ...personalTasksTools,
    ],
  };
});

// =============================================================================
// TOOL HANDLERS
// =============================================================================
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args = {} } = request.params;
  const db = getDb();

  try {
    // Route to appropriate domain handler based on tool name
    if (name.includes("habit")) {
      return await handleHabitTool(name, args, db);
    } else if (name.includes("energy")) {
      return await handleEnergyTool(name, args, db);
    } else if (name.includes("brain") || name.includes("dump")) {
      return await handleBrainDumpTool(name, args, db);
    } else if (name.includes("personal_task")) {
      return await handlePersonalTasksTool(name, args, db);
    } else {
      // Default: route to task handler
      return await handleTaskTool(name, args, db);
    }
  } catch (error) {
    return {
      content: [
        {
          type: "text",
          text: `Error: ${error instanceof Error ? error.message : String(error)}`,
        },
      ],
    };
  }
});

// =============================================================================
// START SERVER
// =============================================================================
async function main() {
  // Initialize cache at startup (non-blocking)
  ensureCache().then(success => {
    if (success) {
      const stats = getCacheStats();
      console.error(`[Cache] Ready: ${stats.taskCount} tasks, ${stats.clientCount} clients, last sync: ${stats.lastSyncAt || "never"}`);
    }
  }).catch(err => {
    console.error("[Cache] Startup initialization failed:", err);
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("WorkOS MCP server running on stdio");
}

main().catch(console.error);
