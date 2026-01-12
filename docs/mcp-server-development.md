# MCP Server Development Guide

Guide for developers to create custom MCP servers that integrate with Thanos.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Server Architecture](#server-architecture)
- [Implementation Guide](#implementation-guide)
- [Tool Development](#tool-development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Best Practices](#best-practices)

## Overview

### What is an MCP Server?

An MCP (Model Context Protocol) server is a standalone process that:
- Exposes tools/functions through standardized MCP protocol
- Communicates via stdio or Server-Sent Events (SSE)
- Can be written in any programming language
- Integrates seamlessly with Thanos adapter system

### Why Create a Custom Server?

Create custom MCP servers to:
- **Wrap Existing APIs**: Create typed interfaces for REST/GraphQL APIs
- **Access Private Data**: Connect to internal databases or services
- **Add Domain Logic**: Implement business-specific operations
- **Extend Ecosystem**: Share reusable integrations with community

## Prerequisites

### Required Knowledge

- Python 3.10+ (for Python servers) or Node.js 18+ (for TypeScript servers)
- Understanding of async/await programming
- Familiarity with JSON Schema
- Basic knowledge of MCP specification

### Required Tools

```bash
# For Python servers
pip install mcp

# For TypeScript servers
npm install @modelcontextprotocol/sdk

# For testing
pip install pytest pytest-asyncio  # Python
npm install jest  # TypeScript
```

## Quick Start

### Minimal Python Server

```python
# my_server.py
import asyncio
import logging
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server instance
app = Server("my-custom-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="greet",
            description="Greet someone by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name to greet"
                    }
                },
                "required": ["name"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    if name == "greet":
        person_name = arguments["name"]
        return [
            TextContent(
                type="text",
                text=f"Hello, {person_name}! Welcome to my custom MCP server."
            )
        ]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the server."""
    logger.info("Starting my-custom-server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
```

### Test the Server

```python
# test_integration.py
import asyncio
from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.mcp_config import MCPServerConfig

async def test_custom_server():
    # Configure server
    config = MCPServerConfig(
        name="my-custom-server",
        command="python",
        args=["my_server.py"],
        env={},
        transport="stdio"
    )

    # Create bridge
    bridge = MCPBridge(config)
    await bridge.connect()

    # Test tool
    result = await bridge.call_tool("greet", {"name": "World"})
    print(result.data)  # "Hello, World! ..."

    await bridge.close()

asyncio.run(test_custom_server())
```

## Server Architecture

### Component Structure

```
my-mcp-server/
├── src/
│   ├── __init__.py
│   ├── server.py        # Main server implementation
│   ├── tools/           # Tool implementations
│   │   ├── __init__.py
│   │   ├── data_tools.py
│   │   └── api_tools.py
│   ├── schemas/         # JSON schemas for tools
│   │   ├── __init__.py
│   │   └── tool_schemas.py
│   └── utils/           # Shared utilities
│       ├── __init__.py
│       └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── test_server.py
│   └── test_tools.py
├── README.md
├── pyproject.toml       # or package.json
└── config.example.json  # Example configuration
```

### Layered Design

```
┌─────────────────────────────────┐
│   MCP Protocol Layer            │  ← stdio/SSE communication
├─────────────────────────────────┤
│   Server Framework              │  ← Tool routing, error handling
├─────────────────────────────────┤
│   Tool Implementation Layer     │  ← Your business logic
├─────────────────────────────────┤
│   Data Access Layer             │  ← Database/API clients
└─────────────────────────────────┘
```

## Implementation Guide

### Step 1: Define Tool Schemas

Create clear, comprehensive JSON schemas for each tool:

```python
# src/schemas/tool_schemas.py
from typing import Dict, Any

def get_user_schema() -> Dict[str, Any]:
    """Schema for get_user tool."""
    return {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "integer",
                "description": "User ID to retrieve",
                "minimum": 1
            },
            "include_posts": {
                "type": "boolean",
                "description": "Whether to include user's posts",
                "default": False
            }
        },
        "required": ["user_id"]
    }

def create_post_schema() -> Dict[str, Any]:
    """Schema for create_post tool."""
    return {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Post title",
                "minLength": 1,
                "maxLength": 200
            },
            "content": {
                "type": "string",
                "description": "Post content",
                "minLength": 1
            },
            "tags": {
                "type": "array",
                "description": "Optional tags",
                "items": {"type": "string"},
                "maxItems": 10
            }
        },
        "required": ["title", "content"]
    }
```

### Step 2: Implement Tools

Separate tool logic from server infrastructure:

```python
# src/tools/data_tools.py
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

class DataTools:
    """Data access and manipulation tools."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        # Initialize database connection
        self.db = self._connect_database()

    def _connect_database(self):
        """Connect to database."""
        # Implementation
        pass

    async def get_user(self, user_id: int, include_posts: bool = False) -> Dict[str, Any]:
        """
        Retrieve user by ID.

        Args:
            user_id: User ID to retrieve
            include_posts: Whether to include user's posts

        Returns:
            User data with optional posts

        Raises:
            ValueError: If user not found
        """
        logger.info(f"Fetching user {user_id}")

        # Query database
        user = await self.db.fetch_one(
            "SELECT * FROM users WHERE id = $1",
            user_id
        )

        if not user:
            raise ValueError(f"User {user_id} not found")

        result = dict(user)

        if include_posts:
            posts = await self.db.fetch_all(
                "SELECT * FROM posts WHERE user_id = $1",
                user_id
            )
            result["posts"] = [dict(p) for p in posts]

        return result

    async def create_post(
        self,
        title: str,
        content: str,
        tags: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Create new post.

        Args:
            title: Post title
            content: Post content
            tags: Optional tags

        Returns:
            Created post data
        """
        logger.info(f"Creating post: {title}")

        post = await self.db.fetch_one(
            """
            INSERT INTO posts (title, content, tags, created_at)
            VALUES ($1, $2, $3, NOW())
            RETURNING *
            """,
            title,
            content,
            tags or []
        )

        return dict(post)
```

### Step 3: Build Server

Wire tools into MCP server:

```python
# src/server.py
import asyncio
import logging
import os
from typing import Any, Dict

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools.data_tools import DataTools
from .schemas.tool_schemas import get_user_schema, create_post_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server
app = Server("my-data-server")

# Get configuration from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/mydb")

# Initialize tool implementations
data_tools = DataTools(DATABASE_URL)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_user",
            description="Retrieve user by ID with optional posts",
            inputSchema=get_user_schema()
        ),
        Tool(
            name="create_post",
            description="Create a new post with title, content, and tags",
            inputSchema=create_post_schema()
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_user":
            result = await data_tools.get_user(
                user_id=arguments["user_id"],
                include_posts=arguments.get("include_posts", False)
            )
            return [TextContent(type="text", text=str(result))]

        elif name == "create_post":
            result = await data_tools.create_post(
                title=arguments["title"],
                content=arguments["content"],
                tags=arguments.get("tags")
            )
            return [TextContent(type="text", text=str(result))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        logger.error(f"Error calling {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Run the server."""
    logger.info("Starting my-data-server")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
```

## Tool Development

### Best Practices for Tool Design

#### 1. Clear Naming

Use descriptive, action-oriented names:

**Good:**
- `get_user_profile`
- `create_blog_post`
- `update_task_status`
- `search_products`

**Bad:**
- `user` (ambiguous)
- `post` (unclear action)
- `do_task` (vague)
- `query` (too generic)

#### 2. Comprehensive Schemas

Include detailed descriptions and validation:

```python
{
    "type": "object",
    "properties": {
        "email": {
            "type": "string",
            "description": "User email address for password reset",
            "format": "email",
            "examples": ["user@example.com"]
        },
        "priority": {
            "type": "string",
            "description": "Request priority level",
            "enum": ["low", "normal", "high", "urgent"],
            "default": "normal"
        }
    },
    "required": ["email"]
}
```

#### 3. Error Handling

Provide clear, actionable error messages:

```python
@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls with comprehensive error handling."""
    try:
        # Tool implementation
        result = await execute_tool(name, arguments)
        return [TextContent(type="text", text=str(result))]

    except ValueError as e:
        # Validation errors
        return [TextContent(
            type="text",
            text=f"Validation error: {str(e)}. Please check your input parameters."
        )]

    except ConnectionError as e:
        # Network/database errors
        return [TextContent(
            type="text",
            text=f"Connection error: {str(e)}. Service may be temporarily unavailable."
        )]

    except PermissionError as e:
        # Authorization errors
        return [TextContent(
            type="text",
            text=f"Permission denied: {str(e)}. Check your API key or credentials."
        )]

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error in {name}: {e}", exc_info=True)
        return [TextContent(
            type="text",
            text=f"Unexpected error: {str(e)}. Please try again or contact support."
        )]
```

#### 4. Input Validation

Validate all inputs before processing:

```python
def validate_user_id(user_id: int) -> None:
    """Validate user ID parameter."""
    if not isinstance(user_id, int):
        raise TypeError(f"user_id must be integer, got {type(user_id)}")
    if user_id < 1:
        raise ValueError(f"user_id must be positive, got {user_id}")

def validate_email(email: str) -> None:
    """Validate email format."""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValueError(f"Invalid email format: {email}")
```

#### 5. Output Formatting

Return structured, consistent responses:

```python
def format_success_response(data: Dict[str, Any]) -> list[TextContent]:
    """Format successful tool response."""
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    )]

def format_error_response(error: str) -> list[TextContent]:
    """Format error response."""
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": False,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }, indent=2)
    )]
```

## Testing

### Unit Tests

Test tool logic independently:

```python
# tests/test_tools.py
import pytest
from src.tools.data_tools import DataTools

@pytest.fixture
async def data_tools():
    """Create DataTools instance for testing."""
    tools = DataTools(database_url="postgresql://test:test@localhost/test_db")
    yield tools
    await tools.close()

@pytest.mark.asyncio
async def test_get_user(data_tools):
    """Test get_user tool."""
    # Setup test data
    user_id = 1

    # Call tool
    result = await data_tools.get_user(user_id)

    # Assertions
    assert result["id"] == user_id
    assert "email" in result
    assert "posts" not in result  # Not included by default

@pytest.mark.asyncio
async def test_get_user_with_posts(data_tools):
    """Test get_user with include_posts=True."""
    user_id = 1

    result = await data_tools.get_user(user_id, include_posts=True)

    assert result["id"] == user_id
    assert "posts" in result
    assert isinstance(result["posts"], list)

@pytest.mark.asyncio
async def test_get_user_not_found(data_tools):
    """Test get_user with invalid ID."""
    with pytest.raises(ValueError, match="User.*not found"):
        await data_tools.get_user(user_id=999999)
```

### Integration Tests

Test complete server functionality:

```python
# tests/test_integration.py
import asyncio
import pytest
from Tools.adapters.mcp_bridge import MCPBridge
from Tools.adapters.mcp_config import MCPServerConfig

@pytest.fixture
async def server_bridge():
    """Create bridge to test server."""
    config = MCPServerConfig(
        name="test-server",
        command="python",
        args=["-m", "src.server"],
        env={"DATABASE_URL": "postgresql://test:test@localhost/test_db"},
        transport="stdio"
    )

    bridge = MCPBridge(config)
    await bridge.connect()

    yield bridge

    await bridge.close()

@pytest.mark.asyncio
async def test_list_tools(server_bridge):
    """Test server lists tools correctly."""
    tools = server_bridge.list_tools()

    assert len(tools) > 0
    assert any(t["name"] == "get_user" for t in tools)
    assert any(t["name"] == "create_post" for t in tools)

@pytest.mark.asyncio
async def test_get_user_tool(server_bridge):
    """Test get_user tool through MCP protocol."""
    result = await server_bridge.call_tool(
        "get_user",
        {"user_id": 1}
    )

    assert result.success
    assert "id" in result.data

@pytest.mark.asyncio
async def test_error_handling(server_bridge):
    """Test error handling for invalid input."""
    result = await server_bridge.call_tool(
        "get_user",
        {"user_id": -1}  # Invalid ID
    )

    assert not result.success
    assert "error" in result.error.lower()
```

## Deployment

### Configuration

Create deployment configuration:

```json
// config/production.json
{
  "server": {
    "name": "my-data-server",
    "version": "1.0.0",
    "transport": "stdio",
    "log_level": "INFO"
  },
  "database": {
    "url": "${DATABASE_URL}",
    "pool_size": 10,
    "max_overflow": 5
  },
  "features": {
    "enable_caching": true,
    "cache_ttl": 300
  }
}
```

### Packaging

Create installable package:

```toml
# pyproject.toml
[project]
name = "my-mcp-server"
version = "1.0.0"
description = "Custom MCP server for data access"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "asyncpg>=0.29.0"
]

[project.scripts]
my-mcp-server = "src.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

# Copy source code
COPY src/ ./src/

# Set environment
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

# Run server
CMD ["python", "-m", "src.server"]
```

### Thanos Integration

Add to Thanos MCP configuration:

```json
{
  "mcpServers": {
    "my-data-server": {
      "command": "my-mcp-server",
      "args": [],
      "env": {
        "DATABASE_URL": "${DATABASE_URL}",
        "LOG_LEVEL": "INFO"
      },
      "transport": "stdio",
      "description": "Custom data access server"
    }
  }
}
```

## Best Practices

### 1. Server Design

- **Single Responsibility**: Each server should have a clear, focused purpose
- **Stateless**: Servers should not maintain state between calls
- **Idempotent**: Tools should be safe to retry
- **Versioned**: Use versioning for breaking changes

### 2. Performance

- **Connection Pooling**: Reuse database connections
- **Caching**: Cache expensive operations
- **Async Operations**: Use async/await throughout
- **Resource Limits**: Set limits on result sizes

### 3. Security

- **Input Validation**: Validate all inputs
- **Authentication**: Use API keys or tokens
- **Authorization**: Check permissions before operations
- **Data Sanitization**: Sanitize outputs to prevent leaks

### 4. Observability

- **Structured Logging**: Use JSON logging for analysis
- **Metrics**: Track performance and errors
- **Health Checks**: Implement health endpoints
- **Tracing**: Use request IDs for debugging

### 5. Documentation

- **README**: Clear installation and usage instructions
- **API Docs**: Document all tools and parameters
- **Examples**: Provide working examples
- **Changelog**: Track version changes

## Next Steps

- [MCP Integration Guide](./mcp-integration-guide.md)
- [Third-Party MCP Servers](./third-party-mcp-servers.md)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [Python SDK Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [TypeScript SDK Documentation](https://github.com/modelcontextprotocol/typescript-sdk)
