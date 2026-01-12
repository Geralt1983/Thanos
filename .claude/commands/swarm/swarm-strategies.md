# swarm-strategies

Execution strategies for swarm task distribution.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__task_orchestrate`

## Parameters
```json
{
  "task": "Build authentication system",
  "strategy": "parallel",
  "priority": "high"
}
```

## Description
Control how tasks are distributed and executed across swarm agents.

## Available Strategies

### Parallel
- Execute independent tasks simultaneously
- Best for: Multi-file changes, batch operations
- MCP: `{"strategy": "parallel"}`

### Sequential
- Execute tasks in order, one at a time
- Best for: Dependent operations, ordered workflows
- MCP: `{"strategy": "sequential"}`

### Adaptive
- Dynamically adjust based on task complexity
- Best for: Unknown scope, varying complexity
- MCP: `{"strategy": "adaptive"}`

### Balanced
- Distribute work evenly across agents
- Best for: Large-scale operations, resource optimization
- MCP: `{"strategy": "balanced"}`

## Example Usage

**In Claude Code:**
1. Parallel execution: `mcp__claude-flow__task_orchestrate` with `{"task": "Analyze codebase", "strategy": "parallel"}`
2. Sequential execution: `mcp__claude-flow__task_orchestrate` with `{"task": "Database migration", "strategy": "sequential"}`
3. Adaptive: `mcp__claude-flow__task_orchestrate` with `{"task": "Build feature", "strategy": "adaptive"}`

**CLI Fallback:**
```bash
npx claude-flow swarm "Build API" --strategy parallel
npx claude-flow swarm "Deploy" --strategy sequential
```

## Important Reminders
- ✅ Use parallel for independent operations
- ✅ Use sequential for dependent operations
- ✅ Use adaptive when unsure

## See Also
- [swarm-modes](./swarm-modes.md) - Coordination modes
- [swarm-init](./swarm-init.md) - Initialize swarm
