# WorkOS Integration Guide

This guide explains how to integrate the Task Closure Learning Hook with WorkOS task events.

## Overview

When Jeremy closes a WorkOS task, the system should:
1. Detect if the task is Epic-related
2. Make an educated guess or ask for the solution
3. Capture the learning automatically

## Integration Methods

### Method 1: WorkOS Webhook (Recommended)

Set up a webhook in WorkOS to call the task closure hook when tasks are completed.

#### Setup

1. **Configure WorkOS webhook:**
   ```
   Event: task.status_changed
   Filter: status == "done" OR status == "complete"
   Endpoint: <your-webhook-endpoint>
   ```

2. **Create webhook handler:**
   ```python
   # webhook_handler.py
   from flask import Flask, request
   import subprocess
   import json
   
   app = Flask(__name__)
   
   @app.route('/workos/task-closure', methods=['POST'])
   def handle_task_closure():
       task_data = request.json
       
       # Save task data to temp file
       with open('/tmp/task.json', 'w') as f:
           json.dump(task_data, f)
       
       # Call task closure hook
       subprocess.run([
           'python3',
           'skills/epic-expert-learning/scripts/task_closure_hook.py',
           '--task-data', '/tmp/task.json',
           '--auto-capture'
       ])
       
       return {"status": "ok"}
   ```

3. **Agent integration:**
   The agent should listen for the hook output and:
   - If high confidence: Present the validated guess to Jeremy
   - If low confidence: Ask Jeremy directly for the solution

#### Webhook Payload Example

```json
{
  "id": "task_abc123",
  "title": "Fix VersaCare provider matching issue",
  "description": "Provider matching failing due to missing NPI in external system",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface", "versacare"],
  "assignee": "jeremy",
  "completed_at": "2026-02-01T20:00:00Z",
  "created_at": "2026-02-01T10:00:00Z"
}
```

### Method 2: Agent Polling

Agent periodically checks WorkOS for recently completed tasks.

#### Setup

```python
# In HEARTBEAT.md or agent cron job
Every 30 minutes:
  1. Query WorkOS API for tasks completed since last check
  2. Filter for Jeremy's tasks
  3. Run task_closure_hook.py for each Epic-related task
```

#### Pseudocode

```python
import requests
from datetime import datetime, timedelta

def check_completed_tasks():
    # Get tasks completed in last 30 min
    since = datetime.now() - timedelta(minutes=30)
    
    response = requests.get(
        'https://api.workos.com/tasks',
        params={
            'assignee': 'jeremy',
            'status': 'done',
            'completed_after': since.isoformat()
        }
    )
    
    tasks = response.json()
    
    for task in tasks:
        # Process each task
        hook = TaskClosureHook()
        is_epic, domain, confidence = hook.detect_epic_context(task)
        
        if is_epic:
            # Present to agent for capture
            process_task_closure(task, domain, confidence)
```

### Method 3: Manual Trigger

Jeremy or the agent manually triggers capture for specific tasks.

#### Usage

```
User: "Capture solution from task #abc123"

Agent: [Fetches task from WorkOS API]
Agent: [Runs task_closure_hook.py --task-id abc123]
Agent: "Task: Fix VersaCare interface. You solved this by using NPI instead of internal ID, right?"
```

## Agent Workflow Integration

### High Confidence Flow (>70%)

```
1. Webhook fires → task closed
2. Agent runs task_closure_hook.py
3. Script detects: 90% confidence
4. Script generates: "You solved this by using NPI instead of internal ID, right?"
5. Agent presents to Jeremy in chat
6. Jeremy responds: "Yes" or corrects
7. Agent captures and stores solution
```

### Low Confidence Flow (<70%)

```
1. Webhook fires → task closed
2. Agent runs task_closure_hook.py
3. Script detects: 50% confidence
4. Script generates: "How'd you solve this one?"
5. Agent asks Jeremy directly
6. Jeremy explains solution
7. Agent captures and stores
```

## Epic Detection Logic

### Task Fields Analyzed

| Field | Weight | Examples |
|-------|--------|----------|
| **Client** | High | "KY", "Epic", "VersaCare" |
| **Title** | High | "Fix orderset", "Configure interface" |
| **Tags** | Medium | ["epic", "interface", "hl7"] |
| **Description** | Low | Scanned for Epic keywords |

### Domain Detection Keywords

```python
{
  "orderset_builds": ["orderset", "smartset", "quick list", "preference"],
  "interfaces": ["interface", "hl7", "bridge", "provider matching"],
  "clindoc_configuration": ["smartphrase", "template", "clindoc"],
  "cardiac_rehab_integrations": ["versacare", "scottcare", "rehab"],
  "workflow_optimization": ["bpa", "workflow", "efficiency"],
  "cutover_procedures": ["cutover", "go-live", "migration"]
}
```

## Educated Guess Patterns

The system recognizes common task patterns and makes educated guesses:

| Task Pattern | Confidence | Educated Guess |
|--------------|------------|----------------|
| "Fix provider matching" | 90% | "Fixed by using NPI instead of internal ID" |
| "Build orderset for X" | 80% | "Built orderset with SmartGroups and defaults" |
| "Configure VersaCare interface" | 85% | "Configured VersaCare telemonitoring interface" |
| "Debug HL7 message" | 70% | "Fixed HL7 segment ordering or field mapping" |
| "Fix issue" | 50% | Ask directly |

### Pattern Matching

Patterns use regex and keyword detection:

```python
r"fix.*provider matching" → High confidence
r"build.*orderset" → Medium-high confidence
r"configure.*bridge" → Medium confidence
r"fix.*issue" → Low confidence (too generic)
```

## Configuration

### Settings in learning-state.json

```json
{
  "settings": {
    "task_closure_enabled": true,
    "task_closure_confidence_threshold": 0.7,
    "task_closure_auto_capture": true,
    "task_closure_sources": ["workos_webhook", "manual_trigger"]
  }
}
```

### Environment Variables

```bash
# WorkOS API credentials (if polling)
export WORKOS_API_KEY="your_api_key"
export WORKOS_BASE_URL="https://api.workos.com"

# Webhook secret (if using webhooks)
export WORKOS_WEBHOOK_SECRET="your_webhook_secret"
```

## Testing

### Test with Mock Task

```bash
# Create mock task
cat > /tmp/test_task.json <<EOF
{
  "id": "task_test123",
  "title": "Fix VersaCare provider matching issue",
  "description": "Provider matching failing in KY environment",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface", "versacare"]
}
EOF

# Run hook
python3 scripts/task_closure_hook.py \
  --task-data /tmp/test_task.json \
  --interactive
```

### Expected Output

```
✅ Epic task detected!
   Domain: interfaces
   Confidence: 85%

🤔 Solution confidence: 90%
   Educated guess: Fixed provider matching by using NPI instead of internal ID

📋 Task closed: "Fix VersaCare provider matching issue"

Let me capture this for learning. Fixed provider matching by using NPI instead of internal ID, right?

(Or tell me what you actually did)

→ Your solution: [wait for input]
```

## Monitoring

Track task closure captures in learning state:

```bash
# Check stats
python3 scripts/daily_review.py

# Should show:
# - task_closures_captured: X
# - last_task_closure_timestamp: YYYY-MM-DD
```

## Troubleshooting

### Task Not Detected as Epic

**Problem:** Task is Epic-related but not detected

**Solution:**
1. Check task title/description for Epic keywords
2. Add client tag if missing
3. Manually trigger with `--task-id <id>`

### Low Confidence on Obvious Tasks

**Problem:** "Fix provider matching" shows 50% confidence

**Solution:**
1. Check pattern matching in `task_closure_hook.py`
2. Add pattern to educated guess library
3. Increase domain keyword weight

### Educated Guess Always Wrong

**Problem:** System keeps guessing incorrectly

**Solution:**
1. Lower confidence threshold (require more certainty)
2. Update patterns based on Jeremy's actual solutions
3. Default to asking directly instead of guessing

## Future Enhancements

- [ ] Learn from correction patterns (when guesses are wrong)
- [ ] Client-specific patterns (KY vs other clients)
- [ ] Time-based complexity inference (longer tasks = higher complexity)
- [ ] Integration with calendar (task duration tracking)
- [ ] Automatic follow-up questions based on captured solutions
