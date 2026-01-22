# Memory V2 MCP Server

MCP server exposing Thanos Memory V2 with heat-based ranking.

## Features

- **Semantic Search**: Search memories by meaning, not just keywords
- **Heat Ranking**: Recent/frequently-accessed memories rank higher
- **ADHD Helpers**: "What's hot" (focus) and "what's cold" (neglected)
- **Memory Pinning**: Mark critical memories to prevent decay

## Tools

| Tool | Description |
|------|-------------|
| `thanos_memory_search` | Search memories with heat ranking |
| `thanos_memory_add` | Add new memory with metadata |
| `thanos_memory_context` | Get formatted context for prompts |
| `thanos_memory_whats_hot` | Get current focus memories |
| `thanos_memory_whats_cold` | Get neglected memories |
| `thanos_memory_pin` | Pin a critical memory |
| `thanos_memory_stats` | Get system statistics |

## Setup

### 1. Install Python Dependencies

```bash
pip install -r ../../Tools/memory_v2/requirements.txt
```

### 2. Install Node Dependencies

```bash
npm install
```

### 3. Build

```bash
npm run build
```

### 4. Configure Environment

Ensure these environment variables are set in `/Users/jeremy/Projects/Thanos/.env`:

- `THANOS_MEMORY_DATABASE_URL` - Neon PostgreSQL URL
- `OPENAI_API_KEY` - For mem0 extraction

## Usage

### Direct Execution

```bash
npm start
```

### Claude Code MCP Configuration

Add to your MCP settings:

```json
{
  "mcpServers": {
    "memory-v2": {
      "command": "node",
      "args": ["/path/to/memory-v2-mcp/dist/index.js"]
    }
  }
}
```

## Architecture

```
MCP Server (TypeScript)
    |
    v
Python Bridge (child_process)
    |
    v
Memory V2 Service (Python)
    |
    +-- mem0 (fact extraction)
    +-- Neon pgvector (storage)
    +-- Heat decay system
```

## Development

```bash
npm run dev  # Run with tsx for hot reload
```
