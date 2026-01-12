# swarm-monitor

Real-time monitoring of Claude Flow swarm activity.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tool:** `mcp__claude-flow__swarm_monitor`

## Parameters
```json
{
  "swarmId": "current",
  "interval": 1000
}
```

## Description
Monitor swarm activity in real-time with configurable update intervals.

## Details
Provides:
- Live agent activity tracking
- Task progress updates
- Resource utilization metrics
- Performance bottleneck alerts
- Coordination health indicators
- Memory usage statistics

## Example Usage

**In Claude Code:**
1. Start monitoring: `mcp__claude-flow__swarm_monitor` with `{"interval": 1000}`
2. Get performance report: `mcp__claude-flow__performance_report` with `{"timeframe": "24h", "format": "summary"}`
3. Analyze bottlenecks: `mcp__claude-flow__bottleneck_analyze` with `{"component": "swarm"}`
4. Check token usage: `mcp__claude-flow__token_usage` with `{"timeframe": "24h"}`

**CLI Fallback:**
```bash
npx claude-flow swarm monitor
npx claude-flow swarm monitor --interval 5000 --metrics
```

## Important Reminders
- ✅ This tool provides coordination and structure
- ✅ Claude Code performs all actual implementation
- ❌ The tool does NOT write code
- ❌ The tool does NOT access files directly
- ❌ The tool does NOT execute commands

## See Also
- [swarm-status](./swarm-status.md) - Point-in-time status
- [swarm-init](./swarm-init.md) - Initialize swarm
- [swarm-analysis](./swarm-analysis.md) - Deep analysis
