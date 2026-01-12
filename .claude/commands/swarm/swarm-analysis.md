# swarm-analysis

Deep analysis of swarm performance and coordination effectiveness.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tools:**
- `mcp__claude-flow__bottleneck_analyze` - Identify performance bottlenecks
- `mcp__claude-flow__performance_report` - Generate performance reports
- `mcp__claude-flow__cognitive_analyze` - Analyze cognitive patterns

## Parameters
```json
{
  "component": "swarm",
  "metrics": ["throughput", "latency", "utilization"]
}
```

## Description
Analyze swarm coordination effectiveness and identify optimization opportunities.

## Details
Analysis capabilities:
- **Bottleneck Detection**: Identify performance constraints
- **Throughput Analysis**: Measure task completion rates
- **Coordination Efficiency**: Evaluate agent collaboration
- **Resource Utilization**: Track memory and CPU usage
- **Pattern Recognition**: Identify recurring issues

## Example Usage

**In Claude Code:**
1. Analyze bottlenecks: `mcp__claude-flow__bottleneck_analyze` with `{"component": "swarm"}`
2. Performance report: `mcp__claude-flow__performance_report` with `{"timeframe": "24h", "format": "detailed"}`
3. Token analysis: `mcp__claude-flow__token_usage` with `{"operation": "swarm"}`
4. Cognitive analysis: `mcp__claude-flow__cognitive_analyze` with `{"behavior": "coordination"}`

**CLI Fallback:**
```bash
npx claude-flow swarm analysis --metrics
npx claude-flow swarm analysis --export json
```

## Important Reminders
- ✅ This tool provides coordination and structure
- ✅ Claude Code performs all actual implementation
- ❌ The tool does NOT write code
- ❌ The tool does NOT access files directly

## See Also
- [swarm-monitor](./swarm-monitor.md) - Real-time monitoring
- [swarm-status](./swarm-status.md) - Current status
