# Example Workflow: Task Closure Learning in Action

This document demonstrates the complete Task Closure Learning Hook workflow with real examples.

## Scenario 1: High Confidence Task (Provider Matching)

### Task Details
```
Title: Fix VersaCare provider matching issue
Client: KY  
Tags: epic, interface, versacare
Status: done → complete
```

### Automatic Detection (Agent)

```
[WorkOS webhook fires: task_abc123 status changed to "done"]

Agent runs: task_closure_hook.py --task-id abc123 --auto-capture

Detection results:
✅ Epic task detected!
   Domain: interfaces
   Confidence: 90%

🤔 Solution confidence: 90%
   Educated guess: Fixed provider matching by using NPI instead of internal ID
```

### Agent Presentation to Jeremy

```
Agent: 📋 Task closed: "Fix VersaCare provider matching issue"

Agent: Let me capture this for learning. You fixed provider matching by 
using NPI instead of internal ID, right?
```

### Scenario 1a: Jeremy Confirms

```
Jeremy: "Yes, exactly"

Agent: ✅ Captured! 
   Domain: Interfaces
   Complexity: 4/5
   Your Interfaces expertise → Beginner (9 concepts learned)
   
   This solution is now searchable. Try: "How do I fix provider matching?"
```

**Stored in:**
- **Memory V2**: "Fix provider matching" → "Use NPI instead of internal ID for external systems"
- **Graphiti**: Jeremy → solved → VersaCare provider matching (reason: external system lacks Epic IDs)
- **Learning state**: interfaces domain +1 concept

### Scenario 1b: Jeremy Corrects

```
Jeremy: "Not quite - I actually had to add a custom identifier cross-reference table"

Agent: Got it! So the real solution was adding a custom identifier cross-reference 
table instead of using NPI directly?

Jeremy: "Correct"

Agent: ✅ Captured! Thanks for the correction.
   Domain: Interfaces  
   Complexity: 5/5 (more complex than I thought!)
   
   I'll remember: Provider matching sometimes needs custom identifier tables,
   not just NPI fallback.
```

**Stored in:**
- **Memory V2**: "Provider matching with custom identifiers" → "Use cross-reference table when NPI unavailable"
- **Graphiti**: Pattern learned: When NPI fails → try custom identifier cross-reference
- **Learning state**: interfaces domain +1 concept, knowledge gap updated

---

## Scenario 2: Medium Confidence Task (Orderset Build)

### Task Details
```
Title: Build cardiology orderset for new protocols
Client: KY
Tags: epic, orderset, cardiology  
Status: done
```

### Automatic Detection

```
Detection results:
✅ Epic task detected!
   Domain: orderset_builds
   Confidence: 85%

🤔 Solution confidence: 75%
   Educated guess: Built orderset with SmartGroups and appropriate defaults
```

### Agent Presentation

```
Agent: 📋 Task closed: "Build cardiology orderset for new protocols"

Agent: You built this orderset with SmartGroups and appropriate defaults, right?
Or did you use a different approach?

Jeremy: "SmartGroups yes, but I also set up preference list cascading 
for the different cardiology providers"

Agent: ✅ Captured!
   Domain: Orderset Builds
   Complexity: 4/5
   
   New concept learned: Preference list cascading in orderset builds
   
   This addresses your knowledge gap: "Preference list cascading logic"!
```

**Stored in:**
- **Memory V2**: "Cardiology orderset with preference cascading" → "Use SmartGroups + provider-specific preference lists"
- **Graphiti**: Jeremy → built → cardiology orderset (technique: preference list cascading)
- **Learning state**: orderset_builds +1 concept, knowledge gap "preference cascading" removed

---

## Scenario 3: Low Confidence Task (Generic Fix)

### Task Details
```
Title: Fix issue with patient data display
Client: KY
Tags: epic, bug
Status: done
```

### Automatic Detection

```
Detection results:
✅ Epic task detected!
   Domain: workflow_optimization (fallback)
   Confidence: 60%

🤔 Solution confidence: 40%
   Educated guess: None (too generic)
```

### Agent Presentation

```
Agent: 📋 Task closed: "Fix issue with patient data display"

Agent: How'd you solve this one?

Jeremy: "Turned out to be a SmartText syntax error in the documentation template"

Agent: Interesting! So this was actually a ClinDoc configuration issue, 
not a workflow problem?

Jeremy: "Correct"

Agent: ✅ Captured!
   Domain: clindoc_configuration (corrected from initial guess)
   Complexity: 2/5
   
   New concept: SmartText syntax errors can cause display issues
   
   Your ClinDoc Configuration → Novice (4 concepts)
```

**Stored in:**
- **Memory V2**: "Patient data display issues" → "Check SmartText syntax in templates"
- **Graphiti**: Pattern: Display issues → check SmartText syntax before assuming workflow bug
- **Learning state**: clindoc_configuration +1 concept, domain corrected from initial detection

---

## Scenario 4: Non-Epic Task (Skipped)

### Task Details
```
Title: Update project documentation  
Client: Internal
Tags: documentation
Status: done
```

### Automatic Detection

```
Detection results:
❌ Task doesn't appear to be Epic-related (confidence: 0%)

[No capture triggered]
```

---

## Scenario 5: Batch Processing (Multiple Tasks)

### WorkOS Webhook Fires for Multiple Tasks

```
[5 tasks completed in the last hour]

Agent processes each:
  1. "Fix provider matching" → Interfaces (captured)
  2. "Build orderset" → Orderset Builds (captured)  
  3. "Update documentation" → Not Epic (skipped)
  4. "Configure ScottCare interface" → Cardiac Rehab (captured)
  5. "Optimize workflow" → Workflow Optimization (ask directly)

Agent: 📊 Captured learnings from 3 Epic tasks:
   - Interfaces: Provider matching fix
   - Orderset Builds: Cardiology orderset
   - Cardiac Rehab: ScottCare integration
   
   One task needs your input:
   
   📋 "Optimize workflow for ED physicians"
   How'd you solve this one?
```

---

## Learning Progression Example

### Week 1: Starting Point
```
Interfaces domain:
  Strength: Novice
  Concepts: 3
  Knowledge gaps: 5
```

### After Task Closures (Week 1)
```
Tasks captured:
  Mon: Fix VersaCare provider matching → +1 concept
  Tue: Configure Bridge interface → +1 concept  
  Wed: Debug HL7 segment issue → +1 concept
  Thu: Fix provider matching (different client) → +0 (duplicate pattern)
  Fri: Build custom identifier table → +1 concept
```

### Week 1: End Result
```
Interfaces domain:
  Strength: Beginner (7 concepts)
  Concepts: 7 (+4 new)
  Knowledge gaps: 3 (-2 addressed)
  
  Recent learnings:
    - Provider matching with NPI
    - Provider matching with custom identifiers
    - Bridge interface configuration basics
    - HL7 segment ordering debugging
```

### Projected Growth (4 weeks)
```
Week 1: 7 concepts (Beginner)
Week 2: 14 concepts (Beginner)  
Week 3: 22 concepts (Intermediate)
Week 4: 28 concepts (Intermediate)

At current pace of ~4 task closures/week:
  - Month 2: Advanced (35+ concepts)
  - Month 3: Expert (50+ concepts)
```

---

## Integration with Other Workflows

### Task Closure → Targeted Question Follow-Up

```
[Task closed: Configure ScottCare interface]

Agent (captures): "Configured ScottCare telemonitoring interface"

[2 hours later, during heartbeat]

Agent: Mind if I ask a quick question to learn?

Agent: You just configured ScottCare - what's the difference between 
ScottCare and VersaCare data structures?

Jeremy: [explains]

Agent: ✅ Logged! This fills a knowledge gap I had.
```

### Task Closure → Daily Review Summary

```
[End of day]

Jeremy: "Epic progress report"

Agent: 📊 Epic Learning Summary - Feb 1, 2026

✅ Solutions captured: 5 (3 from task closures, 2 manual)
   - VersaCare provider matching (Interfaces, task closure)
   - Cardiology orderset build (Orderset Builds, task closure)  
   - ScottCare interface (Cardiac Rehab, task closure)
   - SmartText syntax fix (ClinDoc, manual capture)
   - BPA optimization (Workflow, manual capture)

📈 Domain progress:
   - Interfaces: Beginner → Intermediate (16 concepts, +8 today!)
   - Orderset Builds: Beginner (12 concepts, +2)
   - Cardiac Rehab: Beginner (8 concepts, +1)

🎯 Knowledge gaps addressed: 2
   - Preference list cascading (now understood!)
   - ScottCare vs VersaCare differences (learned today)
```

---

## Success Metrics

### Capture Rate
```
Tasks closed this week: 25
Epic tasks: 12 (48%)
Captured automatically: 10 (83% of Epic tasks)
Required user input: 2 (17%)

High confidence guesses: 8
  Validated correct: 7 (87.5%)
  Corrected by user: 1 (12.5%)
```

### Learning Velocity
```
Before task closure hook:
  Concepts/week: 8-10 (manual capture only)
  
After task closure hook:
  Concepts/week: 15-20 (50% automatic, 50% manual)
  
Projected time to expert:
  Before: 15 weeks
  After: 8 weeks (47% faster)
```

### Knowledge Quality
```
Confidence distribution:
  High (solution validated): 70%
  Medium (educated guess confirmed): 20%
  Low (user correction): 10%

Real-world solutions captured: 100%
Textbook knowledge: 0% (captures Jeremy's actual approach)
```

---

## Common Edge Cases

### Edge Case 1: Task Reopened Then Closed Again

```
Task: "Fix provider matching"
Status: done → reopened → done

First closure:
  Agent: "Fixed with NPI, right?"
  Jeremy: "Yes"
  
[Task reopened - fix didn't work]
[Task closed again]

Second closure:
  Agent: "I see you closed this again. Different solution this time?"
  Jeremy: "Yeah, NPI didn't work - needed custom identifier table"
  
Agent: ✅ Updated learning!
   Previous: Use NPI for provider matching
   Correction: NPI doesn't always work - custom identifier table is more reliable
   
   This is a valuable learning - when initial solution fails, document why!
```

### Edge Case 2: Bulk Task Closure (Sprint Complete)

```
[Jeremy closes 15 tasks at once after sprint demo]

Agent: 📊 Detected 15 task closures (8 Epic-related)

Instead of asking about all 8, I'll batch them:

High confidence (5 tasks): Auto-captured ✅
Medium confidence (2 tasks): Will ask about these in our next chat
Low confidence (1 task): Need your input

Summary captured:
  - 2x provider matching fixes (Interfaces)
  - 2x orderset builds (Orderset Builds)  
  - 1x BPA configuration (Workflow)
  
When you have a moment, how'd you solve these 3:
  1. "Optimize ED workflow"
  2. "Fix mysterious display issue"  
  3. "Configure new integration"
```

---

## Best Practices

### For Jeremy

1. **Write descriptive task titles** - Helps detection accuracy
   - ✅ Good: "Fix VersaCare provider matching using NPI"
   - ❌ Bad: "Fix issue"

2. **Use client tags** - Improves Epic detection  
   - ✅ Good: Tags: ["epic", "ky", "interface"]
   - ❌ Bad: Tags: ["bug"]

3. **Correct educated guesses** - Teaches the system
   - When agent guesses wrong, explain the real solution
   - Improves future guess accuracy

4. **Review weekly summaries** - Track learning progress
   - Identifies knowledge gaps
   - Shows domain strength growth
   - Motivates continued learning

### For the Agent

1. **Don't interrupt flow** - Wait for task closure event
2. **Batch similar tasks** - Don't ask about 5 provider matching fixes separately
3. **Learn from corrections** - Update patterns when guesses are wrong
4. **Respect uncertainty** - When confidence <70%, always ask
5. **Celebrate progress** - Show Jeremy his domain growth

---

## Summary

The Task Closure Learning Hook provides:

✅ **Automatic capture** - 83% of Epic tasks captured without manual effort  
✅ **High accuracy** - 87.5% of educated guesses are correct
✅ **Fast learning** - 2x learning velocity vs manual capture only
✅ **Real-world knowledge** - Captures actual solutions, not theory
✅ **Minimal interruption** - Only asks when necessary
✅ **Progressive growth** - Visible domain strength progression

Result: **Agent matches Jeremy's Epic expertise in 8 weeks instead of 15.**
