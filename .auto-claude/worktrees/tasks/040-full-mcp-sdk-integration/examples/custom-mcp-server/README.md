# Custom MCP Server Template

A template for creating custom MCP servers that integrate with Thanos.

## Overview

This is a complete, working example of a custom MCP server that you can use as a starting point for your own integrations. It demonstrates:

- ✅ Proper MCP protocol implementation
- ✅ Tool definition and handling
- ✅ Input validation with Zod schemas
- ✅ Error handling and logging
- ✅ Environment configuration
- ✅ Testing setup
- ✅ Best practices and patterns

## Quick Start

```bash
# 1. Clone this template
cp -r examples/custom-mcp-server my-custom-server
cd my-custom-server

# 2. Install dependencies
npm install

# 3. Build the server
npm run build

# 4. Test it works
npm test

# 5. Run manually to verify
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node dist/index.js
```

## What This Server Does

This example server provides tools for managing a simple task list:

### Tools

1. **task_list** - List all tasks with optional filtering
   - Parameters: `status` (active/completed/all), `limit` (max results)
   - Returns: Array of tasks

2. **task_get** - Get details of a specific task
   - Parameters: `task_id` (required)
   - Returns: Task object with full details

3. **task_create** - Create a new task
   - Parameters: `title` (required), `description`, `priority`
   - Returns: Created task with assigned ID

4. **task_update** - Update an existing task
   - Parameters: `task_id` (required), `status`, `title`, `description`
   - Returns: Updated task

5. **task_delete** - Delete a task
   - Parameters: `task_id` (required)
   - Returns: Success confirmation

## Configuration

### Environment Variables

```bash
# Required
TASK_API_KEY=your-api-key-here

# Optional
TASK_API_URL=https://api.example.com  # Default: mock API
DEBUG=true                             # Enable debug logging
ALLOW_WRITE=true                       # Enable create/update/delete (default: false)
```

### Thanos Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "custom-task-server": {
      "command": "node",
      "args": ["/path/to/my-custom-server/dist/index.js"],
      "env": {
        "TASK_API_KEY": "your-api-key",
        "ALLOW_WRITE": "true"
      }
    }
  }
}
```

Or add to project `.mcp.json`:

```json
{
  "custom-task-server": {
    "transport_type": "stdio",
    "stdio": {
      "command": "node",
      "args": ["${CUSTOM_TASK_SERVER_PATH}"],
      "env": {
        "TASK_API_KEY": "${TASK_API_KEY}",
        "ALLOW_WRITE": "true"
      }
    },
    "enabled": true,
    "tags": ["tasks", "custom"]
  }
}
```

## Customizing for Your Use Case

### 1. Update Package Info

Edit `package.json`:
```json
{
  "name": "my-custom-server",
  "description": "Your custom integration",
  "author": "Your Name"
}
```

### 2. Define Your Tools

Edit `src/tools/index.ts` to define your tools:

```typescript
export const myTools = [
  {
    name: "my_custom_tool",
    description: "What this tool does",
    inputSchema: {
      type: "object",
      properties: {
        param1: {
          type: "string",
          description: "Description of param1"
        }
      },
      required: ["param1"]
    }
  }
];
```

### 3. Implement Tool Handlers

Add your logic in `src/tools/handlers.ts`:

```typescript
export async function handleMyTool(name: string, args: unknown) {
  const schema = z.object({
    param1: z.string().min(1)
  });

  const params = schema.parse(args);

  // Your implementation here
  const result = await yourApiCall(params.param1);

  return {
    content: [{
      type: "text",
      text: JSON.stringify(result)
    }]
  };
}
```

### 4. Update Main Server

Edit `src/index.ts` to use your tools:

```typescript
import { myTools, handleMyTool } from "./tools/index.js";

// Register tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return { tools: myTools };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  return await handleMyTool(request.params.name, request.params.arguments);
});
```

## Testing

### Run Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- tools.test.ts

# Watch mode
npm run test:watch
```

### Manual Testing

```bash
# Test tool listing
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node dist/index.js

# Test tool call
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"task_list","arguments":{"limit":5}}}' | node dist/index.js
```

### Integration Testing with Thanos

```python
# test_integration.py
import asyncio
from Tools.adapters import get_default_manager

async def test():
    manager = await get_default_manager(enable_mcp=True)

    # List tools
    tools = await manager.list_tools()
    task_tools = [t for t in tools if t['name'].startswith('task_')]
    print(f"Found {len(task_tools)} task tools")

    # Call a tool
    result = await manager.call_tool('task_list', {'limit': 5})
    print(f"Result: {result.data}")

asyncio.run(test())
```

## Project Structure

```
custom-mcp-server/
├── src/
│   ├── index.ts           # Main server entry point
│   ├── tools/
│   │   ├── index.ts       # Tool definitions
│   │   └── handlers.ts    # Tool implementation
│   ├── api/
│   │   └── client.ts      # API client (if needed)
│   └── utils/
│       ├── logger.ts      # Logging utilities
│       └── validation.ts  # Validation helpers
├── tests/
│   ├── tools.test.ts      # Tool tests
│   └── integration.test.ts
├── docs/
│   └── API.md             # Tool documentation
├── dist/                  # Build output
├── package.json
├── tsconfig.json
├── jest.config.js
└── README.md
```

## Development Workflow

### 1. Make Changes

```bash
# Edit source files
vim src/tools/handlers.ts

# Build
npm run build

# Or use watch mode
npm run dev
```

### 2. Test Changes

```bash
# Run tests
npm test

# Test manually
node dist/index.js
```

### 3. Update Documentation

```bash
# Update README.md with new tools
# Update docs/API.md with tool documentation
```

## Deployment

### Option 1: Local Development

```bash
# Build and point Thanos to dist/index.js
npm run build
# Update ~/.claude.json with path to dist/index.js
```

### Option 2: npm Package

```bash
# 1. Update version
npm version patch

# 2. Publish
npm publish

# 3. Install globally
npm install -g my-custom-server

# 4. Use in config
{
  "command": "my-custom-server",
  "args": []
}
```

### Option 3: Docker

```bash
# Build image
docker build -t my-custom-server .

# Run with Thanos
{
  "command": "docker",
  "args": ["run", "-i", "--rm", "my-custom-server"]
}
```

## Best Practices

### 1. Error Handling
- Always wrap async operations in try-catch
- Return structured errors with `isError: true`
- Log errors to stderr, not stdout

### 2. Input Validation
- Use Zod schemas for all inputs
- Validate before processing
- Provide clear error messages

### 3. Security
- Store secrets in environment variables
- Validate and sanitize all inputs
- Implement rate limiting for write operations
- Use read-only by default, require explicit write enable

### 4. Performance
- Cache expensive operations
- Use connection pooling for APIs
- Set reasonable timeouts
- Implement pagination for large results

### 5. Logging
- Log to stderr (stdout is for protocol)
- Use structured logging (JSON)
- Include request IDs for tracing
- Log at appropriate levels (debug/info/warn/error)

### 6. Testing
- Unit test each tool handler
- Integration test with Thanos
- Test error scenarios
- Test with invalid inputs

## Troubleshooting

### Server Not Starting

```bash
# Check Node version
node --version  # Should be 18+

# Check dependencies
npm install

# Check build
npm run build
ls -l dist/

# Test manually
node dist/index.js
```

### Tools Not Appearing

```bash
# Check configuration
cat ~/.claude.json | jq .

# Check server path
ls -l /path/to/dist/index.js

# Test tool listing
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node dist/index.js
```

### Authentication Errors

```bash
# Check environment variables
echo $TASK_API_KEY

# Test API directly
curl -H "Authorization: Bearer $TASK_API_KEY" https://api.example.com/test
```

## Resources

- [MCP Server Development Guide](../../docs/mcp-server-development.md)
- [Custom MCP Server Guide](../../docs/custom-mcp-server-guide.md)
- [MCP Integration Guide](../../docs/mcp-integration-guide.md)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)

## License

MIT - Feel free to use this template for your own projects.

## Support

- GitHub Issues: Report bugs or request features
- Documentation: See docs/ directory
- Examples: See other adapters in Tools/adapters/

---

**Happy building!** 🚀
