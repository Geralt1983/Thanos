# swarm-status

Check the current status and health of the Claude Flow swarm.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_status`

## Parameters
```json
{
  "swarmId": "current"
}
```

## Description
Monitor the effectiveness of current coordination patterns and swarm health.

## Details
Shows:
- Active coordination topologies
- Current cognitive patterns (agents) in use
- Task breakdown and progress
- Resource utilization for coordination
- Overall system health
- Agent metrics and performance

## Example Usage

**In Claude Code:**
1. Check swarm status: `mcp__claude-flow__swarm_status`
2. Monitor real-time: `mcp__claude-flow__swarm_monitor` with `{"interval": 1000}`
3. Get agent metrics: `mcp__claude-flow__agent_metrics` with `{"agentId": "agent-123"}`
4. Health check: `mcp__claude-flow__health_check` with `{"components": ["swarm", "memory", "neural"]}`

**CLI Fallback:**
```bash
npx claude-flow swarm status
npx claude-flow swarm status --verbose
```

## Important Reminders
- ✅ This tool provides coordination and structure
- ✅ Claude Code performs all actual implementation
- ❌ The tool does NOT write code
- ❌ The tool does NOT access files directly
- ❌ The tool does NOT execute commands

## See Also
- [swarm-init](./swarm-init.md) - Initialize swarm
- [swarm-monitor](./swarm-monitor.md) - Real-time monitoring
- [swarm-spawn](./swarm-spawn.md) - Create agents
