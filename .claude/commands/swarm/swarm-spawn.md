# swarm-spawn

Spawn specialized agents in the Claude Flow swarm.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__agent_spawn` (single) or `mcp__claude-flow__agents_spawn_parallel` (batch)

## Parameters

**Single agent:**
```json
{
  "type": "researcher",
  "name": "Literature Analysis",
  "capabilities": ["deep-analysis", "web-search"]
}
```

**Parallel batch (10-20x faster):**
```json
{
  "agents": [
    {"type": "architect", "name": "sys-architect"},
    {"type": "code-analyzer", "name": "quality-checker"},
    {"type": "tester", "name": "test-generator"}
  ],
  "maxConcurrency": 5,
  "batchSize": 3
}
```

## Description
Create specialized agents that represent different cognitive approaches for task execution.

## Details
Agent types represent thinking patterns:
- **coordinator**: Task routing and workflow orchestration
- **architect**: System design and big-picture planning
- **researcher**: Systematic exploration and analysis
- **coder**: Implementation-focused thinking
- **code-analyzer**: Code quality and structure analysis
- **perf-analyzer**: Performance bottleneck detection
- **tester**: Test generation and validation
- **reviewer**: Quality and consistency checking
- **documenter**: Documentation generation
- **optimizer**: Performance optimization

## Example Usage

**In Claude Code:**
1. Single agent: `mcp__claude-flow__agent_spawn` with `{"type": "architect", "name": "sys-architect"}`
2. Batch spawn: `mcp__claude-flow__agents_spawn_parallel` with agents array
3. List agents: `mcp__claude-flow__agent_list`
4. Get metrics: `mcp__claude-flow__agent_metrics` with `{"agentId": "agent-123"}`

**CLI Fallback:**
```bash
npx claude-flow swarm spawn --type researcher --name "Analysis Agent"
```

## Important Reminders
- ✅ This tool provides coordination and structure
- ✅ Claude Code performs all actual implementation
- ✅ Use parallel spawn for multiple agents (10-20x faster)
- ❌ The tool does NOT write code
- ❌ The tool does NOT access files directly

## See Also
- [swarm-init](./swarm-init.md) - Initialize swarm first
- [swarm-status](./swarm-status.md) - Check agent status
- [swarm-monitor](./swarm-monitor.md) - Monitor agents
