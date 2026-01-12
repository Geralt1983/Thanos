# swarm

Main Claude Flow swarm orchestration command.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Primary Tools:**
- `mcp__claude-flow__swarm_init` - Initialize swarm
- `mcp__claude-flow__agent_spawn` - Create agents
- `mcp__claude-flow__task_orchestrate` - Coordinate tasks
- `mcp__claude-flow__swarm_status` - Check status

## Quick Start

**Initialize and run a swarm in Claude Code:**
```
1. mcp__claude-flow__swarm_init with {"topology": "hierarchical", "maxAgents": 8, "strategy": "auto"}
2. mcp__claude-flow__agent_spawn with {"type": "coordinator", "name": "task-router"}
3. mcp__claude-flow__task_orchestrate with {"task": "Your objective", "strategy": "adaptive"}
```

## Parameters

**swarm_init:**
```json
{
  "topology": "hierarchical|mesh|ring|star",
  "maxAgents": 8,
  "strategy": "auto|balanced|specialized|adaptive"
}
```

**task_orchestrate:**
```json
{
  "task": "Task description",
  "strategy": "parallel|sequential|adaptive|balanced",
  "priority": "low|medium|high|critical"
}
```

## Common Workflows

### Development Swarm
```
swarm_init(topology: "hierarchical", maxAgents: 6)
agents_spawn_parallel([architect, coder, tester, reviewer])
task_orchestrate(task: "Build feature", strategy: "adaptive")
```

### Research Swarm
```
swarm_init(topology: "mesh", maxAgents: 4)
agent_spawn(type: "researcher", capabilities: ["web-search", "analysis"])
task_orchestrate(task: "Research topic", strategy: "parallel")
```

### Analysis Swarm
```
swarm_init(topology: "hierarchical", maxAgents: 5)
agents_spawn_parallel([code-analyzer, perf-analyzer, reviewer])
task_orchestrate(task: "Analyze codebase", strategy: "parallel")
```

**CLI Fallback:**
```bash
npx claude-flow swarm "Build REST API" --strategy development
npx claude-flow swarm "Research AI patterns" --strategy research --mode mesh
```

## Important Reminders
- ✅ Always initialize swarm before spawning agents
- ✅ Use hierarchical topology for most development tasks
- ✅ Use parallel spawn for multiple agents (10-20x faster)
- ❌ The swarm does NOT write code - Claude Code does
- ❌ The swarm does NOT access files directly

## See Also
- [swarm-init](./swarm-init.md) - Initialize swarm
- [swarm-spawn](./swarm-spawn.md) - Create agents
- [swarm-status](./swarm-status.md) - Check status
- [swarm-monitor](./swarm-monitor.md) - Real-time monitoring
- [swarm-strategies](./swarm-strategies.md) - Execution strategies
- [swarm-modes](./swarm-modes.md) - Coordination modes
