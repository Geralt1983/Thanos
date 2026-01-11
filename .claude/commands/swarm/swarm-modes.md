# swarm-modes

Swarm coordination modes for different execution patterns.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_init` with mode configuration

## Parameters
```json
{
  "topology": "hierarchical",
  "strategy": "adaptive"
}
```

## Description
Configure how the swarm coordinates agents for different task types.

## Available Modes

### Centralized
- Single coordinator manages all agents
- Best for: Simple tasks, clear workflows
- MCP: `mcp__claude-flow__swarm_init` with `{"topology": "star"}`

### Distributed
- Agents collaborate as peers
- Best for: Research, exploration, brainstorming
- MCP: `mcp__claude-flow__swarm_init` with `{"topology": "mesh"}`

### Hierarchical
- Tree structure with clear command chain
- Best for: Development, structured projects
- MCP: `mcp__claude-flow__swarm_init` with `{"topology": "hierarchical"}`

### Pipeline
- Sequential processing through agent chain
- Best for: Data processing, staged workflows
- MCP: `mcp__claude-flow__swarm_init` with `{"topology": "ring"}`

## Example Usage

**In Claude Code:**
1. Hierarchical mode: `mcp__claude-flow__swarm_init` with `{"topology": "hierarchical", "maxAgents": 8}`
2. Mesh mode: `mcp__claude-flow__swarm_init` with `{"topology": "mesh", "maxAgents": 5}`
3. Check current mode: `mcp__claude-flow__swarm_status`

**CLI Fallback:**
```bash
npx claude-flow swarm init --mode hierarchical
npx claude-flow swarm init --mode distributed
```

## Important Reminders
- ✅ Choose mode based on task complexity
- ✅ Hierarchical is best for most development tasks
- ❌ Don't use mesh for simple tasks (overhead)

## See Also
- [swarm-init](./swarm-init.md) - Initialize with mode
- [swarm-strategies](./swarm-strategies.md) - Execution strategies
