# Classify Workflow

## Purpose
Classify user input into one of five categories to determine appropriate handling.

## Phases

### 1. OBSERVE
Analyze the input for linguistic markers:

**Task Indicators**
- Imperative verbs: "create", "add", "schedule", "remind", "send"
- Future intent: "I need to", "I should", "I have to"
- Deadline references: "by Friday", "tomorrow", "this week"
- Client/project names
- Temporal markers (deadlines, "by Friday", "eventually")
- Action verbs vs. state descriptions

**Question Indicators**
- Question words: "what", "how", "why", "when", "where", "who"
- Question marks
- Seeking patterns: "can you tell me", "do you know"

**Thinking Indicators**
- Uncertainty markers: "maybe", "perhaps", "I wonder"
- Exploratory language: "what if", "I'm considering"
- Self-dialogue: "I think", "I believe"
- No action verb

**Venting Indicators**
- Emotional language: "frustrated", "annoyed", "stressed", "tired"
- Complaints without action requests
- Past tense grievances
- Emotional indicators (frustration, excitement, fatigue)

**Observation Indicators**
- Declarative statements about state
- "I noticed", "It seems", "There's a", "interesting that"
- No implied action needed

### 2. THINK
Apply the scoring matrix:

| Signal | Weight | Category |
|--------|--------|----------|
| No action verb | +2 | thinking |
| Emotional language, no request | +3 | venting |
| "I noticed", "interesting that" | +2 | observation |
| Question syntax | +3 | question |
| "Need to", "have to", deadline | +3 | task |
| "Should probably someday" | -2 | task (too vague) |

```
Score each category 0.0 - 1.0:

TASK_SCORE = (
    has_imperative_verb * 0.3 +
    has_deadline * 0.25 +
    has_actionable_object * 0.25 +
    has_assignment_language * 0.2
)

QUESTION_SCORE = (
    has_question_word * 0.4 +
    has_question_mark * 0.3 +
    seeks_information * 0.3
)

THINKING_SCORE = (
    has_uncertainty_marker * 0.35 +
    is_exploratory * 0.35 +
    no_action_implied * 0.3
)

VENTING_SCORE = (
    has_emotional_language * 0.4 +
    is_complaint * 0.3 +
    no_solution_sought * 0.3
)

OBSERVATION_SCORE = (
    is_declarative * 0.4 +
    shares_information * 0.3 +
    no_response_needed * 0.3
)
```

### 3. DECIDE
Select the highest scoring category:

```python
scores = {
    "task": TASK_SCORE,
    "question": QUESTION_SCORE,
    "thinking": THINKING_SCORE,
    "venting": VENTING_SCORE,
    "observation": OBSERVATION_SCORE
}

classification = max(scores, key=scores.get)
confidence = scores[classification]

# Confidence threshold
if confidence < 0.6:
    classification = "ambiguous"
    action = "ask_clarification"

# Task gate: Score >= 3 for task AND contains concrete action -> CREATE TASK
# Otherwise -> Acknowledge appropriately, DO NOT create task
```

### 4. RESPOND
Return classification result and appropriate response:

```json
{
    "classification": "task|question|thinking|venting|observation|ambiguous",
    "confidence": 0.0-1.0,
    "scores": {
        "task": 0.0,
        "question": 0.0,
        "thinking": 0.0,
        "venting": 0.0,
        "observation": 0.0
    },
    "markers_detected": ["imperative_verb", "deadline", ...],
    "suggested_action": "route|acknowledge|clarify"
}
```

**Response Templates for Non-Task Classifications:**
- `thinking`: "That's an interesting thread. Want to explore it more, or just noting it?"
- `venting`: "That sounds frustrating. Anything I can help with, or just needed to get it out?"
- `observation`: "Noted. [Log if pattern-relevant]"
- `question`: Route to appropriate skill or answer directly

## Edge Cases

### Mixed Intent
When input contains multiple intents:
```
"I'm frustrated with the Orlando project (venting), can you create a follow-up task? (task)"
```
- Primary: task (explicit request)
- Secondary: venting (acknowledged but not actioned)

### Implicit Tasks
```
"I should probably email the client"
```
- Could be thinking OR task
- Ask: "Would you like me to create a task for emailing the client?"

### Rhetorical Questions
```
"Why do meetings always run long?"
```
- Appears as question but is actually venting
- No information-seeking intent
- Route as venting

## Examples

### Clear Task
```
Input: "Create a task to review the Memphis proposal by Friday"
Output: {
    "classification": "task",
    "confidence": 0.95,
    "markers_detected": ["imperative_verb:create", "deadline:Friday", "client:Memphis"]
}
```

### Clear Venting
```
Input: "I'm so exhausted from all these back-to-back calls"
Output: {
    "classification": "venting",
    "confidence": 0.88,
    "markers_detected": ["emotional:exhausted", "complaint:back-to-back calls"]
}
```

### Ambiguous
```
Input: "The API might need some work"
Output: {
    "classification": "ambiguous",
    "confidence": 0.52,
    "suggested_action": "clarify",
    "clarification_prompt": "Would you like me to create a task for the API work, or were you just noting an observation?"
}
```

## Anti-Patterns to Avoid
- Creating task for every mention of future intent
- Treating "I should probably..." as commitment
- Converting exploration into obligation
