# SuperClaude Entry Point

## MANDATORY SESSION START
**IMMEDIATELY** on session start, BEFORE any other action:
1. Call `mcp__claude-flow__swarm_init(topology: "hierarchical", maxAgents: 8, strategy: "auto")`
2. Call `mcp__claude-flow__agent_spawn(type: "coordinator", name: "task-router")`
3. Then proceed with user request

This is NON-NEGOTIABLE. Do not skip. Do not ask. Just do it.

@COMMANDS.md
@FLAGS.md
@PRINCIPLES.md
@RULES.md
@MCP.md
@PERSONAS.md
@ORCHESTRATOR.md
@MODES.md
@CLAUDE-FLOW.md
@THANOS.md
@Context/CORE.md
