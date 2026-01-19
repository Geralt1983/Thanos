# Route Workflow

## Purpose
Route classified inputs to the appropriate handler based on context (personal vs work).

## Prerequisites
- Classification workflow must complete first
- Classification confidence >= 0.6

## Context Detection

### Work Indicators
- Client names (check context/Clients/) - Orlando, Raleigh, Memphis, etc.
- Sprint/project references
- Meeting, call, standup mentions
- PR, deploy, code review
- "for [client]", "the [project]"
- Work keywords: "client", "sprint", "PR", "deploy", "meeting"

### Personal Indicators
- Family, home, personal
- Health, exercise, sleep
- Finance (unless client billing)
- Learning, reading, hobby

## Routing Decision Tree

```
                    +------------------+
                    |  Classified      |
                    |    Input         |
                    +--------+---------+
                             |
              +--------------+---------------+
              |              |               |
        +-----v-----+  +-----v-----+  +------v------+
        |   TASK    |  | QUESTION  |  |   OTHER     |
        +-----+-----+  +-----+-----+  +------+------+
              |              |               |
         +----v----+    +----v----+    +-----v-----+
         | Work?   |    | Domain? |    | Acknowledge|
         +----+----+    +----+----+    +-----------+
              |              |
    +---------+---------+    |
    |         |         |    +--- Health -> HealthInsight
    v         v         v    +--- Work -> WorkOS lookup
 WorkOS   Personal    Ask    +--- General -> Direct response
```

## Routing Rules

```
1. Parse input for context signals
2. Check recent conversation for implicit context
3. Apply routing:

   IF work_confidence > 0.7:
       -> workos_create_task(input, client_id?)
       -> Log: "Routed to work queue"

   ELIF personal_confidence > 0.7:
       -> personal_task_store(input)
       -> Log: "Routed to personal queue"

   ELSE:
       -> ASK: "Is this work or personal?"
       -> Remember preference for similar future inputs
```

## Energy Gating

Before routing complex tasks, check:
```
readiness = get_oura_readiness()

IF readiness < 40:
    -> "Captured for later. You're in recovery mode."
    -> Store in backlog, don't surface today

IF readiness 40-60:
    -> "Added to queue. Consider tackling when energy improves."
    -> Mark as low-priority for today

IF readiness > 60:
    -> Normal routing and prioritization
```

## Routing Handlers

### Work Task
```python
def route_work_task(input, classification):
    # Extract task components
    client = extract_client(input)
    title = extract_title(input)
    deadline = extract_deadline(input)

    # Create via WorkOS MCP
    return {
        "handler": "workos_create_task",
        "params": {
            "title": title,
            "clientId": client.id if client else None,
            "clientName": client.name if client else None,
            "status": "backlog",
            "valueTier": infer_value_tier(input),
            "cognitiveLoad": infer_cognitive_load(input)
        }
    }
```

### Personal Task
```python
def route_personal_task(input, classification):
    return {
        "handler": "workos_create_task",
        "params": {
            "title": extract_title(input),
            "category": "personal",
            "status": "backlog"
        }
    }
```

### Health Question
```python
def route_health_question(input):
    return {
        "handler": "HealthInsight",
        "workflow": "query",
        "params": {
            "query": input,
            "data_sources": ["oura_sleep", "oura_readiness", "oura_activity"]
        }
    }
```

### Work Question
```python
def route_work_question(input):
    # Determine what context is needed
    if "task" in input or "todo" in input:
        return {"handler": "workos_get_tasks", "params": {"status": "active"}}
    elif "client" in input:
        return {"handler": "workos_get_client_memory", "params": extract_client(input)}
    else:
        return {"handler": "workos_daily_summary"}
```

### Non-Actionable (Conversational)
```python
def route_conversational(input, classification):
    """Handle thinking, venting, observations"""

    responses = {
        "thinking": {
            "style": "supportive",
            "action": "reflect_back",
            "offer_help": True
        },
        "venting": {
            "style": "empathetic",
            "action": "acknowledge",
            "offer_help": False  # Don't immediately try to fix
        },
        "observation": {
            "style": "engaged",
            "action": "acknowledge_or_expand",
            "offer_help": "if_relevant"
        }
    }

    return {
        "handler": "conversational_response",
        "params": responses[classification]
    }
```

## Examples

### Work Task Detection and Routing
```
Input: "Follow up with Orlando about the dashboard"
Classification: task (0.92)

Context Check:
- "Orlando" matches client_names -> +0.4
- "dashboard" is project-related -> +0.2
- Score: 0.6 -> Work context

Route: workos_create_task
Params: {
    "title": "Follow up about the dashboard",
    "clientName": "Orlando",
    "status": "backlog"
}
```

### Personal Task Routing
```
Input: "Remind me to pick up groceries"
Classification: task (0.89)

Context Check:
- No client references
- "groceries" is personal keyword
- Score: 0.0 -> Personal context

Route: workos_create_task
Params: {
    "title": "Pick up groceries",
    "category": "personal"
}
```

### Health Question Routing
```
Input: "How was my sleep?"
Classification: question (0.94)

Domain Check:
- "sleep" -> health domain

Route: HealthInsight skill
Workflow: DailyBriefing (sleep focus)
```

### Venting Acknowledgment
```
Input: "These meetings are killing my productivity"
Classification: venting (0.85)

Route: conversational_response
Style: empathetic
Response: "That sounds frustrating. Back-to-back meetings can really fragment your focus time."
(No task created, no solution offered unless asked)
```

## Post-Route Actions
1. Log decision to history/decisions/
2. Update context/current_state.md if high-priority
3. Notify if deadline within 24h
