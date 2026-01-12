# swarm-init

Initialize a Claude Flow swarm with specified topology and configuration.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_init`

## Parameters
```json
{
  "topology": "hierarchical",
  "maxAgents": 8,
  "strategy": "auto"
}
```

## Description
Initialize a new swarm with the specified topology for coordinated task execution.

## Details
Topologies:
- **hierarchical**: Tree structure with clear command chain (best for development)
- **mesh**: All agents connect to all others (best for research/exploration)
- **ring**: Agents connect in a circle (best for pipeline processing)
- **star**: Central coordinator with satellite agents (best for simple tasks)

Strategies:
- **auto**: Automatically select based on task complexity
- **balanced**: Distribute work evenly across agents
- **specialized**: Assign agents based on capabilities
- **adaptive**: Dynamically adjust during execution

## Example Usage

**In Claude Code:**
1. Initialize swarm: `mcp__claude-flow__swarm_init` with `{"topology": "hierarchical", "maxAgents": 8, "strategy": "auto"}`
2. Check status: `mcp__claude-flow__swarm_status`
3. Spawn agents: `mcp__claude-flow__agent_spawn` with `{"type": "coordinator", "name": "task-router"}`

**CLI Fallback:**
```bash
npx claude-flow swarm init --topology hierarchical --max-agents 8 --strategy auto
```

## Important Reminders
- ✅ This tool provides coordination and structure
- ✅ Claude Code performs all actual implementation
- ❌ The tool does NOT write code
- ❌ The tool does NOT access files directly
- ❌ The tool does NOT execute commands

## See Also
- [swarm-spawn](./swarm-spawn.md) - Create swarm agents
- [swarm-status](./swarm-status.md) - Check swarm state
- [swarm-monitor](./swarm-monitor.md) - Real-time monitoring
