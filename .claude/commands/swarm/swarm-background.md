# swarm-background

Run swarm operations in the background.

## 🎯 Key Principle
**This tool coordinates Claude Code's actions. It does NOT write code or create content.**

## MCP Tool Usage in Claude Code

**Tools:**
- `mcp__claude-flow__task_orchestrate` - Background task execution
- `mcp__claude-flow__task_status` - Check background task status
- `mcp__claude-flow__task_results` - Get completed task results

## Parameters
```json
{
  "task": "Long-running analysis",
  "strategy": "adaptive",
  "priority": "medium"
}
```

## Description
Execute swarm tasks in the background while continuing other work.

## Details
Background operations allow:
- Long-running analysis tasks
- Parallel research operations
- Non-blocking task execution
- Progress monitoring
- Result retrieval when complete

## Example Usage

**In Claude Code:**
1. Start background task: `mcp__claude-flow__task_orchestrate` with `{"task": "Analyze security", "strategy": "adaptive"}`
2. Check progress: `mcp__claude-flow__task_status` with `{"taskId": "task-123"}`
3. Get results: `mcp__claude-flow__task_results` with `{"taskId": "task-123", "format": "detailed"}`

**CLI Fallback:**
```bash
npx claude-flow swarm "Research patterns" --background
npx claude-flow task status task-123
npx claude-flow task results task-123
```

## Important Reminders
- ✅ Use for long-running operations
- ✅ Monitor progress with task_status
- ✅ Retrieve results when complete
- ❌ Don't forget to check results

## See Also
- [swarm-status](./swarm-status.md) - Check swarm status
- [swarm-monitor](./swarm-monitor.md) - Real-time monitoring
