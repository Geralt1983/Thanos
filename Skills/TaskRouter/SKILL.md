# TaskRouter Skill

## Overview
Routes user inputs to appropriate handlers based on classification and context.

## USE WHEN
- User sends any message that needs classification
- Input type is ambiguous (could be task, question, or personal expression)
- Routing decision needed between personal and work contexts
- User mentions: "task", "todo", "need to", "have to", "should", "must", "deadline"
- User wants to: capture action item, create task, add to list
- User provides: brain dump, voice capture, stream of consciousness

## GATES
- **REQUIRES**: Classification workflow must complete before routing
- **BLOCKS IF**: Classification confidence < 0.6 (ask for clarification)

## IMPORTANT: Classification Gate
This skill MUST classify input before creating any task. Most brain dumps are processing, not actionable items.

## Classification Categories

| Category | Description | Example |
|----------|-------------|---------|
| `thinking` | User working through ideas | "I'm wondering if..." |
| `venting` | Emotional expression | "I'm so frustrated with..." |
| `observation` | Sharing information | "I noticed that..." |
| `question` | Seeking information | "What is...?" "How do I...?" |
| `task` | Actionable request | "Create a task for..." |

## Routing Logic

```
IF classification == "task":
    IF contains_work_keywords OR has_client_reference:
        ROUTE -> WorkOS MCP (workos_create_task)
    ELSE:
        ROUTE -> Personal task handler
ELIF classification == "question":
    IF health_related:
        ROUTE -> HealthInsight skill
    ELIF work_related:
        ROUTE -> WorkOS context lookup
    ELSE:
        ROUTE -> General response
ELIF classification in ["thinking", "venting", "observation"]:
    ROUTE -> Conversational response (acknowledge, don't action)
```

## Integration Points

### MCP Tools
- `workos_create_task` - Create work tasks
- `workos_get_tasks` - Query existing tasks
- `workos_get_clients` - Client context lookup
- `workos_brain_dump` - Capture raw thoughts

### Related Skills
- **HealthInsight** - For health-related queries
- **Orchestrator** - For planning and scheduling

## Workflows
- [Classify](workflows/Classify.md) - Input classification with OBSERVE/THINK/DECIDE/RESPOND phases
- [Route](workflows/Route.md) - Context-aware routing for personal vs work

## Tools
- `tools/workos_bridge.py` - WorkOS MCP wrapper
- `tools/personal_tasks.py` - Local task store for non-work items

## Examples

### Task Detection
```
User: "I need to follow up with Orlando about the API integration"
Classification: task (0.95)
Route: WorkOS -> workos_create_task(clientName: "Orlando", title: "Follow up on API integration")
```

### Venting Detection
```
User: "Ugh, I'm so tired of these meetings"
Classification: venting (0.88)
Route: Conversational -> Acknowledge feelings, no task created
```

### Question Detection
```
User: "How did I sleep last night?"
Classification: question (0.92)
Route: HealthInsight -> Oura data lookup
```

### Ambiguous Input
```
User: "The API might need some work"
Classification: ambiguous (0.52)
Action: Clarify -> "Would you like me to create a task for the API work, or were you just noting an observation?"
```

## Anti-Patterns to Avoid
- Creating task for every mention of future intent
- Treating "I should probably..." as commitment
- Converting exploration into obligation
- Routing complex tasks when energy is low

## Post-Route Actions
1. Log decision to history/decisions/
2. Update context/current_state.md if high-priority
3. Notify if deadline within 24h
4. Check energy state before routing complex tasks
