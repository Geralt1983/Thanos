# Epic Expert Learning Skill

Iterative learning system for acquiring Epic EMR domain expertise through solution capture, targeted questioning, and progress tracking.

## Quick Start

### Agent Usage (Natural Language)

The skill triggers automatically when:
- User mentions Epic-related terms (orderset, interface, ClinDoc, etc.)
- User is working on Epic tasks
- User requests learning review or solution capture

**Examples:**
```
User: "Finally got that VersaCare interface working!"
Agent: "Can I capture how you solved this for learning?"

User: "Working on orderset builds today"
[30 mins later]
Agent: "Mind if I ask a quick question to learn?"
Agent: "When do you use redirector sections vs direct ordering?"

User: "Epic progress report"
Agent: [Generates daily summary with domain progress]
```

### Automatic Workflows

#### Task Closure Monitor (Primary Method)
**Script:** `scripts/task_closure_monitor.py`

Monitors WorkOS for task completions and automatically captures learnings:
- Detects Epic context from task title, description, tags
- Makes educated guess (high confidence >70%) or asks directly (low confidence <70%)
- Auto-captures high-confidence solutions
- Prompts user for low-confidence tasks

**Usage:**
```bash
# Webhook mode (recommended)
# Called by WorkOS webhook on task completion

# Polling mode
python3 scripts/task_closure_monitor.py --monitor --interval 300

# Single task
python3 scripts/task_closure_monitor.py --task-id task_123
python3 scripts/task_closure_monitor.py --task-json '{"id":"...","title":"..."}'
```

**Example:**
```
Task closed: "Fix VersaCare provider matching issue"
Monitor (90% confidence): Auto-capturing...
Agent: "You fixed provider matching by using NPI instead of internal ID, right?"
You: "Yes" 
Agent: "✅ Captured! Interfaces → Beginner (10 concepts)"
```

See `MONITOR_INTEGRATION.md` for complete setup guide.

### Manual Scripts

All scripts are in `scripts/` and can be run directly:

#### 1. Task Closure Monitor (Primary)
```bash
# Monitor mode (recommended for production)
python3 scripts/task_closure_monitor.py --monitor --interval 300

# Single task (webhook handler)
python3 scripts/task_closure_monitor.py --task-json '{"id":"task_123","title":"..."}'

# Interactive mode (validate guesses)
python3 scripts/task_closure_monitor.py --task-id task_123 --interactive

# Test suite
./scripts/test_monitor.sh
```

#### 2. Solution Capture
```bash
# Interactive guided capture
python scripts/capture_solution.py --interactive

# Auto-detect completion from message
python scripts/capture_solution.py --auto-detect "Fixed the provider matching issue!"
```

#### 3. Targeted Questioning
```bash
# Suggest question based on context
python scripts/ask_question.py --context "Working on KY orderset build"

# Suggest question for specific domain
python scripts/ask_question.py --domain interfaces --suggest-question
```

#### 4. Daily Review
```bash
# Daily summary
python scripts/daily_review.py

# Weekly summary
python scripts/daily_review.py --weekly

# Domain-specific progress
python scripts/daily_review.py --domain orderset_builds
```

## Directory Structure

```
skills/epic-expert-learning/
├── SKILL.md                          # Skill documentation and workflows
├── README.md                         # This file
├── references/
│   ├── learning-state.json           # Current learning progress
│   └── epic-domains.md               # Domain taxonomy and definitions
└── scripts/
    ├── task_closure_monitor.py       # PRIMARY: WorkOS task completion monitor
    ├── capture_solution.py           # Manual solution capture workflow
    ├── ask_question.py               # Targeted questioning logic
    ├── task_closure_hook.py          # Task closure hook (legacy/alternative)
    ├── daily_review.py               # Synthesis and progress tracking
    ├── test_monitor.sh               # Test suite for monitor
    └── test_task_closure.sh          # Test suite for hook
```

## Workflows

### 1. Task Closure Learning Hook (Automatic)

**When:** WorkOS task status changes to "done" or "complete"

**Process:**
1. Detects Epic context from task data (90%+ accuracy)
2. Assesses solution confidence:
   - High (>70%): "You solved this by doing X, right?"
   - Low (<70%): "How'd you solve this one?"
3. Captures validated solution with domain tagging
4. Stores in Memory V2 + Graphiti + learning state

**Confidence Patterns:**
- "Fix provider matching" → 90% → "Used NPI instead of internal ID"
- "Build orderset" → 80% → "Built with SmartGroups and defaults"
- "Fix issue" → 50% → Ask directly

**Result:** Automatic learning from every Epic task completion

### 2. Solution Capture (Manual)

**When:** Jeremy solves an Epic problem

**Process:**
1. Agent detects completion signal ("fixed", "solved", "working")
2. Asks permission: "Can I capture how you solved this?"
3. Runs guided capture:
   - What was the problem?
   - How did you approach it?
   - Why did you choose X over Y?
   - What alternatives did you consider?
   - What would you do differently?
4. Tags with domain, complexity, client
5. Stores in Memory V2, Graphiti, and learning state

**Result:** Solution becomes searchable knowledge

### 3. Targeted Questioning

**When:** User is actively working on Epic tasks

**Process:**
1. Detect work context from messages or tasks
2. Check learning state for knowledge gaps in relevant domain
3. Ask permission: "Mind if I ask a quick question to learn?"
4. Ask 1-2 targeted questions focused on "why" and "how"
5. Capture response → Memory V2 + Graphiti
6. Update learning state

**Constraints:**
- Max 2 questions per session
- Min 30 minutes between questions
- Always ask permission first

### 4. Daily Review

**When:** End of workday or manual request

**Process:**
1. Synthesize day's learnings (solutions, questions, concepts)
2. Update domain strength scores
3. Identify knowledge gaps
4. Suggest next learning targets
5. Generate formatted summary

**Output Example:**
```
📊 Epic Learning Summary - Feb 1, 2026

✅ Solutions captured: 3
   - VersaCare interface debugging (Interfaces, complexity: 4)
   - Orderset phantom defaults (Orderset Builds, complexity: 3)

💡 Concepts learned: 5
   - OCC phantom default behavior
   - Provider matching NPI vs internal ID logic

📈 Domain progress:
   - Orderset Builds: Beginner → Intermediate (12 → 18 concepts)
   - Interfaces: Novice → Beginner (3 → 8 concepts)

🎯 Knowledge gaps identified:
   - Bridges configuration details
   - HL7 segment ordering rules

💭 Suggested next learning:
   - Ask about Bridges when next interface task comes up
```

## Domain Taxonomy

Six primary Epic domains tracked:

1. **Orderset Builds** - SmartSets, Quick Lists, panels, preferences
2. **Interfaces** - HL7, Bridges, provider matching, data mapping
3. **ClinDoc Configuration** - Templates, SmartTools, workflows
4. **Cardiac Rehab Integrations** - VersaCare, ScottCare
5. **Workflow Optimization** - Efficiency, BPAs, click reduction
6. **Cutover Procedures** - Go-live, migration, validation

**Strength Levels:**
- Novice (0-5 concepts)
- Beginner (6-15 concepts)
- Intermediate (16-30 concepts)
- Advanced (31-50 concepts)
- Expert (51+ concepts)

See `references/epic-domains.md` for full taxonomy.

## Integration Points

### Memory V2 (Vector Search)
Stores facts and solutions for semantic search:
```
"How do I configure redirector sections?"
→ Retrieves relevant past solutions
```

### Graphiti (Knowledge Graph)
Stores decision patterns and relationships:
```
"When does Jeremy use NPI for provider matching?"
→ Returns pattern: "When external system lacks Epic IDs"
```

### NotebookLM (Epic Notebooks)
Cross-references learned concepts with documented patterns:
```
Query Epic Orders HOD guide for "phantom defaults"
→ Compare Jeremy's explanation vs documentation
```

## Configuration

Edit settings in `references/learning-state.json`:

```json
{
  "settings": {
    "daily_review_time": "18:00",
    "max_questions_per_session": 2,
    "min_question_interval_minutes": 30,
    "auto_capture_enabled": true,
    "ask_permission_for_questions": true,
    "learning_session_cooldown_hours": 2,
    "priority_domains": [
      "orderset_builds",
      "interfaces",
      "cardiac_rehab_integrations"
    ]
  }
}
```

## Learning State Schema

```json
{
  "domains": {
    "orderset_builds": {
      "strength": "beginner",
      "strength_level": 1,
      "concepts_learned": 12,
      "solutions_captured": 5,
      "questions_asked": 8,
      "knowledge_gaps": ["Preference list cascading logic"],
      "recent_concepts": [...]
    }
  },
  "recent_learnings": [...],
  "knowledge_gaps": [...],
  "global_stats": {
    "total_concepts_learned": 36,
    "total_solutions_captured": 15,
    "avg_concepts_per_day": 4.5
  }
}
```

## Testing

### Task Closure Hook Tests

Run the comprehensive test suite:

```bash
cd skills/epic-expert-learning
./scripts/test_task_closure.sh
```

This tests:
1. High confidence task (provider matching) → 90% → makes educated guess
2. Medium confidence task (orderset build) → 80% → makes educated guess
3. Low confidence task (generic fix) → 50% → asks directly
4. Non-Epic task → skips
5. Cardiac rehab task → domain-specific guess

### Manual Testing

Test individual scenarios:

```bash
# High confidence - auto-capture
python3 scripts/task_closure_hook.py --task-id test-123 --auto-capture

# Interactive mode
python3 scripts/task_closure_hook.py --task-id test-123 --interactive

# Custom task data
cat > task.json <<EOF
{
  "id": "task_xyz",
  "title": "Your task title",
  "description": "Task description",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface"]
}
EOF

python3 scripts/task_closure_hook.py --task-data task.json --interactive
```

## Development

### Adding New Domains

1. Add domain to `references/epic-domains.md`
2. Add domain entry to `learning-state.json`
3. Add domain questions to `ask_question.py` question bank
4. Add domain keywords to context detection in `capture_solution.py`

### Adding Questions

Edit `scripts/ask_question.py` question bank:

```python
"your_domain": [
    {
        "question": "Your question here?",
        "targets": ["knowledge_gap_1", "knowledge_gap_2"],
        "follow_ups": ["Follow-up question?"],
        "priority": 4  # 1-5
    }
]
```

### Integration with Memory V2

Replace TODO blocks in scripts:

```python
# In capture_solution.py and ask_question.py
from memory_v2 import store_fact, search_facts

store_fact(
    content="Your fact here",
    tags=["epic", domain, "tag"],
    source=f"solution_{timestamp}",
    confidence=0.9
)
```

### Integration with Graphiti

Replace TODO blocks in scripts:

```python
# In capture_solution.py
from graphiti import add_relationship

add_relationship(
    subject="Jeremy",
    predicate="solved",
    object="Problem description",
    context={
        "solution": "Solution details",
        "reasoning": "Why it works",
        "date": timestamp
    }
)
```

## Timeline & Goals

**Goal:** Match Jeremy's Epic expertise within ~1 month

**Current Pace:** ~4.5 concepts/day

**Projected:** Expert level (150+ concepts) in ~30 days

**Strategy:**
1. Capture every solution (real-world knowledge)
2. Ask targeted questions (fill gaps)
3. Daily synthesis (reinforce learning)
4. Weekly review (track progress)

## Tips for Effective Learning

1. **Capture > Explain** - Store Jeremy's actual approach, not textbook Epic
2. **Ask "Why" not "What"** - Reasoning > facts
3. **Non-intrusive** - Respect flow, ask permission
4. **Track uncertainty** - Note confidence levels
5. **Progress visibility** - Regular summaries show growth

## Questions?

See `SKILL.md` for detailed workflow documentation.
