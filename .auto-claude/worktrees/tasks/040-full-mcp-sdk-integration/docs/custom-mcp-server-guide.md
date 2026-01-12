# Adding Custom MCP Servers to Thanos

Complete guide for integrating your custom MCP server with Thanos.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Step-by-Step Integration](#step-by-step-integration)
- [Server Template](#server-template)
- [Configuration](#configuration)
- [Testing Your Integration](#testing-your-integration)
- [Deployment](#deployment)
- [Best Practices](#best-practices)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

---

## Overview

### What You'll Learn

This guide shows you how to:
1. Create a custom MCP server for your specific use case
2. Configure Thanos to discover and use your server
3. Test the integration end-to-end
4. Deploy your server for production use
5. Follow security best practices

### Prerequisites

Before starting, ensure you have:
- ✅ Thanos installed with MCP SDK integration
- ✅ Node.js 18+ or Python 3.8+ (depending on your server language)
- ✅ Basic understanding of MCP protocol (see [mcp-server-development.md](./mcp-server-development.md))
- ✅ Your use case and required tools identified

---

## Quick Start

The fastest way to get started is using our template:

```bash
# 1. Copy the example server template
cp -r examples/custom-mcp-server my-custom-server
cd my-custom-server

# 2. Install dependencies (Node.js example)
npm install

# 3. Customize your server
# Edit src/index.ts to add your tools

# 4. Build the server
npm run build

# 5. Configure Thanos
cat >> ~/.claude.json <<EOF
{
  "mcpServers": {
    "my-custom-server": {
      "command": "node",
      "args": ["$PWD/dist/index.js"],
      "env": {
        "API_KEY": "${MY_API_KEY}"
      }
    }
  }
}
EOF

# 6. Test with Thanos
python -c "
from Tools.adapters import get_default_manager
import asyncio

async def test():
    manager = await get_default_manager(enable_mcp=True)
    tools = await manager.list_tools()
    print([t['name'] for t in tools if 'my-custom' in t['name']])

asyncio.run(test())
"
```

---

## Step-by-Step Integration

### Step 1: Plan Your Server

Before writing code, define:

#### 1.1 Purpose and Scope
```plaintext
Example:
- Purpose: Integrate with internal project management API
- Scope: Read/write project tasks, get team metrics
- Use cases: Daily standup reports, task creation, progress tracking
```

#### 1.2 Required Tools
```plaintext
List tools you need:
1. list_projects - Get all active projects
2. get_project_details - Get details for a specific project
3. create_task - Create a new task in a project
4. update_task_status - Update task status
5. get_team_metrics - Get team performance metrics
```

#### 1.3 Authentication and Security
```plaintext
- Authentication method: API key
- Credentials storage: Environment variables
- Access control: Read-only by default, write requires explicit flag
- Rate limiting: 100 requests/minute
```

### Step 2: Create Your Server

Use the example template as a starting point:

#### 2.1 Initialize Project
```bash
mkdir my-project-server
cd my-project-server

# For Node.js/TypeScript
npm init -y
npm install @modelcontextprotocol/sdk zod
npm install -D typescript @types/node

# For Python
pip install mcp pydantic
```

#### 2.2 Project Structure
```
my-project-server/
├── src/
│   ├── index.ts (or main.py)
│   ├── tools/
│   │   ├── projects.ts
│   │   ├── tasks.ts
│   │   └── metrics.ts
│   ├── api/
│   │   └── client.ts
│   └── schemas/
│       └── types.ts
├── tests/
│   ├── unit/
│   └── integration/
├── package.json (or pyproject.toml)
├── tsconfig.json
└── README.md
```

#### 2.3 Implement Core Server (TypeScript Example)

```typescript
// src/index.ts
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Import your tool definitions
import { projectTools, handleProjectTool } from "./tools/projects.js";
import { taskTools, handleTaskTool } from "./tools/tasks.js";
import { metricTools, handleMetricTool } from "./tools/metrics.js";

// Initialize server
const server = new Server(
  {
    name: "my-project-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Register tool list handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      ...projectTools,
      ...taskTools,
      ...metricTools,
    ],
  };
});

// Register tool call handler
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    // Route to appropriate handler
    if (name.startsWith("project_")) {
      return await handleProjectTool(name, args);
    } else if (name.startsWith("task_")) {
      return await handleTaskTool(name, args);
    } else if (name.startsWith("metric_")) {
      return await handleMetricTool(name, args);
    }

    throw new Error(`Unknown tool: ${name}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [{ type: "text", text: `Error: ${message}` }],
      isError: true,
    };
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("My Project MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
```

#### 2.4 Implement Tool Handlers

```typescript
// src/tools/projects.ts
import { z } from "zod";
import { apiClient } from "../api/client.js";

// Define input schemas
const listProjectsSchema = z.object({
  status: z.enum(["active", "archived", "all"]).optional(),
  limit: z.number().min(1).max(100).optional(),
});

const getProjectSchema = z.object({
  project_id: z.string(),
});

// Export tool definitions
export const projectTools = [
  {
    name: "project_list",
    description: "List all projects with optional filtering",
    inputSchema: {
      type: "object",
      properties: {
        status: {
          type: "string",
          enum: ["active", "archived", "all"],
          description: "Filter by project status",
        },
        limit: {
          type: "number",
          description: "Maximum number of projects to return",
          minimum: 1,
          maximum: 100,
        },
      },
    },
  },
  {
    name: "project_get",
    description: "Get detailed information about a specific project",
    inputSchema: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          description: "The unique project identifier",
        },
      },
      required: ["project_id"],
    },
  },
];

// Implement handlers
export async function handleProjectTool(name: string, args: unknown) {
  switch (name) {
    case "project_list": {
      const params = listProjectsSchema.parse(args);
      const projects = await apiClient.listProjects(params);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(projects, null, 2),
          },
        ],
      };
    }

    case "project_get": {
      const params = getProjectSchema.parse(args);
      const project = await apiClient.getProject(params.project_id);
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(project, null, 2),
          },
        ],
      };
    }

    default:
      throw new Error(`Unknown project tool: ${name}`);
  }
}
```

#### 2.5 Implement API Client

```typescript
// src/api/client.ts
export class ProjectAPIClient {
  private apiKey: string;
  private baseUrl: string;

  constructor() {
    this.apiKey = process.env.PROJECT_API_KEY || "";
    this.baseUrl = process.env.PROJECT_API_URL || "https://api.example.com";

    if (!this.apiKey) {
      throw new Error("PROJECT_API_KEY environment variable required");
    }
  }

  async listProjects(params: { status?: string; limit?: number }) {
    const response = await fetch(`${this.baseUrl}/projects`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }

  async getProject(projectId: string) {
    const response = await fetch(`${this.baseUrl}/projects/${projectId}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`);
    }

    return response.json();
  }

  // Add more methods as needed...
}

export const apiClient = new ProjectAPIClient();
```

### Step 3: Configure for Thanos

#### 3.1 Create Bridge Module (Optional but Recommended)

```python
# Tools/adapters/myproject_mcp_bridge.py
"""
MCP bridge for My Project Server integration.
"""
from pathlib import Path
from typing import Optional
import os

from .mcp_bridge import MCPBridge, create_bridge_from_config
from .mcp_config import MCPServerConfig, StdioConfig


def create_myproject_config(
    server_path: Optional[str] = None,
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> MCPServerConfig:
    """
    Create configuration for My Project MCP server.

    Args:
        server_path: Path to server executable (default: auto-detect)
        api_key: API key for authentication (default: from env)
        api_url: API base URL (default: from env)
        tags: Tags for server filtering

    Returns:
        MCPServerConfig configured for My Project server
    """
    if server_path is None:
        server_path = get_default_server_path()

    if api_key is None:
        api_key = "${PROJECT_API_KEY}"

    if api_url is None:
        api_url = "${PROJECT_API_URL}"

    return MCPServerConfig(
        name="my-project-server",
        transport_type="stdio",
        stdio=StdioConfig(
            command="node",
            args=[server_path],
            env={
                "PROJECT_API_KEY": api_key,
                "PROJECT_API_URL": api_url,
            }
        ),
        enabled=True,
        tags=tags or ["projects", "custom"],
    )


def get_default_server_path() -> str:
    """Get default path to My Project MCP server."""
    # Check environment variable
    if path := os.getenv("MYPROJECT_MCP_PATH"):
        return path

    # Check standard locations
    candidates = [
        Path.home() / "Projects" / "my-project-server" / "dist" / "index.js",
        Path("./my-project-server/dist/index.js"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    # Return placeholder for config file
    return "${MYPROJECT_MCP_PATH}"


async def create_myproject_bridge(
    config: Optional[MCPServerConfig] = None,
) -> MCPBridge:
    """
    Create and initialize MCP bridge for My Project server.

    Args:
        config: Optional custom configuration

    Returns:
        Initialized MCPBridge instance
    """
    if config is None:
        config = create_myproject_config()

    return await create_bridge_from_config(config)


# Convenience alias
create_bridge = create_myproject_bridge
```

#### 3.2 Add Configuration File

**Option A: Global Configuration (~/.claude.json)**
```json
{
  "mcpServers": {
    "my-project-server": {
      "command": "node",
      "args": ["/path/to/my-project-server/dist/index.js"],
      "env": {
        "PROJECT_API_KEY": "your-api-key-here",
        "PROJECT_API_URL": "https://api.example.com"
      }
    }
  }
}
```

**Option B: Project Configuration (.mcp.json)**
```json
{
  "my-project-server": {
    "transport_type": "stdio",
    "stdio": {
      "command": "node",
      "args": ["${MYPROJECT_MCP_PATH}"],
      "env": {
        "PROJECT_API_KEY": "${PROJECT_API_KEY}",
        "PROJECT_API_URL": "${PROJECT_API_URL}"
      }
    },
    "enabled": true,
    "tags": ["projects", "custom"]
  }
}
```

#### 3.3 Set Environment Variables

```bash
# Add to ~/.bashrc or ~/.zshrc
export PROJECT_API_KEY="your-api-key"
export PROJECT_API_URL="https://api.example.com"
export MYPROJECT_MCP_PATH="$HOME/Projects/my-project-server/dist/index.js"
```

### Step 4: Testing Your Integration

#### 4.1 Unit Tests for Server

```typescript
// tests/unit/tools.test.ts
import { describe, it, expect } from "@jest/globals";
import { handleProjectTool } from "../../src/tools/projects";

describe("Project Tools", () => {
  it("should list projects", async () => {
    const result = await handleProjectTool("project_list", {
      status: "active",
      limit: 10,
    });

    expect(result.content).toHaveLength(1);
    expect(result.content[0].type).toBe("text");
  });

  it("should get project details", async () => {
    const result = await handleProjectTool("project_get", {
      project_id: "test-123",
    });

    expect(result.content).toHaveLength(1);
    const data = JSON.parse(result.content[0].text);
    expect(data.id).toBe("test-123");
  });

  it("should validate required parameters", async () => {
    await expect(
      handleProjectTool("project_get", {})
    ).rejects.toThrow();
  });
});
```

#### 4.2 Integration Tests with Thanos

```python
# tests/integration/test_myproject_integration.py
import pytest
from Tools.adapters.myproject_mcp_bridge import create_myproject_bridge


@pytest.mark.asyncio
async def test_bridge_creation():
    """Test that bridge can be created and initialized."""
    bridge = await create_myproject_bridge()
    assert bridge is not None
    assert bridge.name == "my-project-server"


@pytest.mark.asyncio
async def test_list_tools():
    """Test that server exposes expected tools."""
    bridge = await create_myproject_bridge()
    tools = await bridge.list_tools()

    tool_names = [t["name"] for t in tools]
    assert "project_list" in tool_names
    assert "project_get" in tool_names


@pytest.mark.asyncio
async def test_call_tool():
    """Test calling a tool through the bridge."""
    bridge = await create_myproject_bridge()

    result = await bridge.call_tool("project_list", {
        "status": "active",
        "limit": 5
    })

    assert result.success is True
    assert result.data is not None


@pytest.mark.asyncio
async def test_adapter_manager_integration():
    """Test integration with AdapterManager."""
    from Tools.adapters import get_default_manager

    manager = await get_default_manager(enable_mcp=True)

    # Check server is discovered
    tools = await manager.list_tools()
    project_tools = [t for t in tools if t["name"].startswith("project_")]
    assert len(project_tools) > 0

    # Test calling through manager
    result = await manager.call_tool("project_list", {"limit": 5})
    assert result.success is True
```

#### 4.3 Manual Testing

```python
# test_manual.py
import asyncio
from Tools.adapters.myproject_mcp_bridge import create_myproject_bridge


async def main():
    print("Creating bridge...")
    bridge = await create_myproject_bridge()

    print("\nListing tools...")
    tools = await bridge.list_tools()
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    print("\nCalling project_list...")
    result = await bridge.call_tool("project_list", {"limit": 3})
    print(f"Success: {result.success}")
    print(f"Data: {result.data}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Deployment

### Development Deployment

1. **Local Testing**
   ```bash
   # Run server in development mode
   npm run dev

   # Or for Python
   python -m my_server
   ```

2. **Configuration**
   - Use `.mcp.json` for project-specific config
   - Keep sensitive data in environment variables

### Production Deployment

#### Option 1: npm Package (Node.js)

```bash
# 1. Prepare for publishing
npm version 1.0.0

# 2. Publish to npm
npm publish

# 3. Users install via npm
npm install -g my-project-server

# 4. Configuration points to global install
{
  "command": "my-project-server",
  "args": []
}
```

#### Option 2: Docker Container

```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY dist ./dist

ENTRYPOINT ["node", "dist/index.js"]
```

```json
{
  "command": "docker",
  "args": ["run", "-i", "--rm", "my-project-server:latest"]
}
```

#### Option 3: System Install

```bash
# Install to system location
sudo cp dist/index.js /usr/local/bin/my-project-server
sudo chmod +x /usr/local/bin/my-project-server

# Configuration
{
  "command": "/usr/local/bin/my-project-server",
  "args": []
}
```

---

## Best Practices

### 1. Error Handling

```typescript
// Always wrap operations in try-catch
try {
  const data = await api.fetchData();
  return {
    content: [{ type: "text", text: JSON.stringify(data) }],
  };
} catch (error) {
  return {
    content: [
      {
        type: "text",
        text: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      },
    ],
    isError: true,
  };
}
```

### 2. Input Validation

```typescript
// Use Zod or similar for validation
import { z } from "zod";

const schema = z.object({
  id: z.string().min(1),
  limit: z.number().min(1).max(100).optional(),
});

// Validate before processing
try {
  const validated = schema.parse(args);
  // Use validated data
} catch (error) {
  throw new Error(`Invalid arguments: ${error}`);
}
```

### 3. Logging

```typescript
// Log to stderr (stdout is for protocol)
console.error(`[${new Date().toISOString()}] Tool called: ${name}`);
console.error(`Arguments:`, JSON.stringify(args));
```

### 4. Resource Cleanup

```typescript
// Handle shutdown gracefully
process.on("SIGINT", async () => {
  console.error("Shutting down...");
  await cleanup();
  process.exit(0);
});
```

### 5. Performance

```typescript
// Cache expensive operations
const cache = new Map<string, { data: unknown; expires: number }>();

async function getCachedData(key: string) {
  const cached = cache.get(key);
  if (cached && Date.now() < cached.expires) {
    return cached.data;
  }

  const data = await fetchData(key);
  cache.set(key, { data, expires: Date.now() + 60000 });
  return data;
}
```

### 6. Documentation

```typescript
// Document each tool clearly
{
  name: "project_list",
  description: "List all projects. Returns project ID, name, status, and creation date. " +
               "Use 'active' status to see only active projects. " +
               "Default limit is 10, maximum is 100.",
  inputSchema: {
    // Detailed schema with descriptions
  }
}
```

---

## Security Considerations

### 1. Credential Management

❌ **Don't:**
```typescript
// Never hardcode credentials
const API_KEY = "sk-1234567890";
```

✅ **Do:**
```typescript
// Use environment variables
const API_KEY = process.env.PROJECT_API_KEY;
if (!API_KEY) {
  throw new Error("PROJECT_API_KEY required");
}
```

### 2. Input Sanitization

```typescript
// Sanitize file paths
function sanitizePath(input: string): string {
  // Remove directory traversal attempts
  const normalized = input.replace(/\.\./g, "");
  // Ensure it's within allowed directory
  const resolved = path.resolve(allowedDir, normalized);
  if (!resolved.startsWith(allowedDir)) {
    throw new Error("Path outside allowed directory");
  }
  return resolved;
}
```

### 3. Rate Limiting

```typescript
// Implement rate limiting
import { RateLimiter } from "limiter";

const limiter = new RateLimiter({
  tokensPerInterval: 10,
  interval: "minute",
});

async function handleTool(name: string, args: unknown) {
  await limiter.removeTokens(1);
  // Process tool...
}
```

### 4. Access Control

```typescript
// Define read-only vs write tools
const WRITE_TOOLS = ["project_create", "project_delete", "task_update"];

function requireWriteAccess() {
  const writeEnabled = process.env.ALLOW_WRITE === "true";
  if (!writeEnabled) {
    throw new Error("Write access not enabled");
  }
}
```

### 5. Data Validation

```typescript
// Validate all outputs
function sanitizeOutput(data: unknown): unknown {
  // Remove sensitive fields
  const sanitized = { ...data };
  delete sanitized.apiKey;
  delete sanitized.password;
  delete sanitized.token;
  return sanitized;
}
```

### 6. Audit Logging

```typescript
// Log all operations for audit trail
function auditLog(action: string, user: string, details: unknown) {
  const entry = {
    timestamp: new Date().toISOString(),
    action,
    user,
    details,
  };
  console.error("[AUDIT]", JSON.stringify(entry));
  // Also write to audit log file
}
```

---

## Troubleshooting

### Common Issues

#### 1. Server Not Discovered

**Symptoms:**
- Server doesn't appear in tool list
- "Server not found" errors

**Solutions:**
```bash
# Check configuration file syntax
cat ~/.claude.json | jq .

# Verify server path
ls -l /path/to/server

# Test server manually
node /path/to/server/dist/index.js

# Check Thanos discovery
python -c "
from Tools.adapters.mcp_discovery import discover_servers
print(discover_servers())
"
```

#### 2. Authentication Failures

**Symptoms:**
- "Unauthorized" or "API key invalid" errors
- 401/403 HTTP responses

**Solutions:**
```bash
# Verify environment variables are set
echo $PROJECT_API_KEY

# Check variable interpolation in config
cat .mcp.json | jq .

# Test API directly
curl -H "Authorization: Bearer $PROJECT_API_KEY" \
  https://api.example.com/test
```

#### 3. Tool Execution Errors

**Symptoms:**
- Tools return errors
- "Tool failed" messages

**Solutions:**
```typescript
// Add detailed error logging
try {
  return await executeOperation();
} catch (error) {
  console.error("Tool error:", error);
  console.error("Stack:", error.stack);
  console.error("Args:", JSON.stringify(args));
  throw error;
}
```

#### 4. Performance Issues

**Symptoms:**
- Slow tool execution
- Timeouts

**Solutions:**
- Add caching for repeated calls
- Optimize API calls (batching, parallel requests)
- Increase timeout in bridge configuration
- Use connection pooling

#### 5. Version Conflicts

**Symptoms:**
- "Protocol version mismatch" errors
- Incompatibility warnings

**Solutions:**
```bash
# Check MCP SDK versions
npm list @modelcontextprotocol/sdk

# Update to compatible version
npm install @modelcontextprotocol/sdk@latest
```

### Debug Mode

Enable detailed logging:

```typescript
// Server side
const DEBUG = process.env.DEBUG === "true";

function debugLog(...args: unknown[]) {
  if (DEBUG) {
    console.error("[DEBUG]", ...args);
  }
}
```

```python
# Bridge side
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

1. **Check Documentation**
   - [MCP Server Development Guide](./mcp-server-development.md)
   - [MCP Integration Guide](./mcp-integration-guide.md)
   - [Third-Party Servers Guide](./third-party-mcp-servers.md)

2. **Review Examples**
   - `examples/custom-mcp-server/` - Complete example
   - `Tools/adapters/workos_mcp_bridge.py` - Production bridge
   - `Tools/adapters/third_party_bridges.py` - Multiple server examples

3. **Test with Known Working Servers**
   - Try workos-mcp or sequential-thinking first
   - Compare your implementation with working servers

4. **Enable Debug Logging**
   - Set `DEBUG=true` environment variable
   - Check server stderr output
   - Review Thanos debug logs

---

## Next Steps

After completing this guide:

1. ✅ **Test Thoroughly**
   - Unit tests for all tools
   - Integration tests with Thanos
   - Manual testing of common workflows

2. ✅ **Document Your Server**
   - README with setup instructions
   - API documentation for each tool
   - Example usage patterns

3. ✅ **Share Your Server**
   - Publish to npm or PyPI
   - Share configuration examples
   - Contribute to Thanos examples

4. ✅ **Monitor and Maintain**
   - Set up error monitoring
   - Track usage metrics
   - Keep dependencies updated

---

## Resources

### Documentation
- [MCP Server Development Guide](./mcp-server-development.md) - In-depth server development
- [MCP Integration Guide](./mcp-integration-guide.md) - Using MCP in Thanos
- [Third-Party Servers](./third-party-mcp-servers.md) - Integration examples

### Example Code
- `examples/custom-mcp-server/` - Complete working example
- `Tools/adapters/workos_mcp_bridge.py` - Production bridge example
- `Tools/adapters/third_party_bridges.py` - Multiple server patterns

### Tools
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) - Debug MCP servers
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

### Community
- MCP GitHub Discussions
- Thanos Discord Server
- Stack Overflow (tag: model-context-protocol)

---

## Checklist

Use this checklist to ensure your integration is complete:

### Planning
- [ ] Use case defined and documented
- [ ] Required tools identified
- [ ] Authentication method chosen
- [ ] Security requirements identified

### Development
- [ ] Server implementation complete
- [ ] All tools implemented with validation
- [ ] Error handling in place
- [ ] Unit tests written and passing

### Integration
- [ ] Bridge module created (if needed)
- [ ] Configuration file created
- [ ] Environment variables documented
- [ ] Integration tests passing

### Documentation
- [ ] README with setup instructions
- [ ] Tool documentation complete
- [ ] Example usage provided
- [ ] Troubleshooting guide included

### Deployment
- [ ] Build process documented
- [ ] Installation instructions clear
- [ ] Configuration examples provided
- [ ] Security review completed

### Testing
- [ ] Manual testing completed
- [ ] Integration with Thanos verified
- [ ] Error scenarios tested
- [ ] Performance acceptable

### Maintenance
- [ ] Version control set up
- [ ] CI/CD pipeline configured (optional)
- [ ] Monitoring in place
- [ ] Update process documented

---

**Congratulations!** You now have everything you need to create and integrate custom MCP servers with Thanos. Start with the example template and customize it for your use case.
