# ADR-003: Shell CLI Architecture with Classification Routing

**Status**: Implemented
**Date**: 2026-01-21
**Author**: System Architecture Designer
**Context**: Phase 2 - Shell CLI Integration

## Context

Thanos v2.0 requires a unified command interface that:
- Prevents casual thoughts from becoming tasks (ADHD-aware)
- Provides appropriate responses for different input types
- Integrates voice, visual, and notification feedback
- Maintains Thanos persona throughout interactions
- Supports energy-aware gating for cognitive load management

## Decision

Implement a classification-first Shell CLI wrapper that:

1. **Routes all inputs through classification gate** before execution
2. **Provides classification-specific handlers** for each input type
3. **Integrates multi-modal feedback** (voice, visuals, notifications)
4. **Maintains Thanos persona** throughout the experience
5. **Logs all activity** for accountability

## Architecture

### High-Level Flow

```
User Input
    ↓
Classification Gate (classifier.py)
    ├─ thinking    → Acknowledge, offer capture
    ├─ venting     → Validate, no action
    ├─ observation → Note, offer memory
    ├─ question    → Direct execution
    └─ task        → Full orchestration
         ↓
    Claude CLI Execution
         ↓
    Multi-Modal Feedback
         ├─ Voice (voice.py)
         ├─ Visuals (visuals.py)
         └─ Notifications (notifications.py)
```

### Component Responsibilities

#### 1. thanos-cli (Main Entry Point)

**Responsibilities:**
- Parse command-line arguments (--dry-run, --help)
- Call classification gate
- Route to appropriate handler
- Coordinate feedback mechanisms
- Log activity

**Key Functions:**
- `main()`: Entry point with argument parsing
- `classify_input()`: Invoke classification module
- `route_task()`: Task execution with full feedback
- `route_question()`: Direct Claude execution
- `route_thinking()`: Acknowledgment with capture option
- `route_venting()`: Validation without action
- `route_observation()`: Noting with memory option

#### 2. classifier.py (Classification Engine)

**Responsibilities:**
- Pattern-based input classification
- Priority ordering for overlapping patterns
- Confidence scoring (future use)

**Classification Logic:**
1. Venting (highest priority - emotional signals)
2. Task (explicit action patterns)
3. Question (? or question words)
4. Thinking (reflective patterns)
5. Observation (informational patterns)
6. Default → question (safest assumption)

**Pattern Examples:**
- Task: "add", "create", "can you help debug"
- Question: "?", "what", "how", "when"
- Thinking: "wondering", "what if", "considering"
- Venting: "tired", "frustrated", "this is so..."
- Observation: "noticed", "saw", "fyi"

#### 3. voice.py (Voice Synthesis)

**Responsibilities:**
- ElevenLabs API integration
- Async playback for non-blocking feedback
- Thanos persona voice configuration
- Error handling for missing API keys

**Key Methods:**
- `speak(message)`: Synthesize and play voice
- `speak_async(message)`: Non-blocking playback

#### 4. visuals.py (Visual State Manager)

**Responsibilities:**
- Kitty terminal wallpaper control
- State transition management
- Terminal compatibility checks

**States:**
- CHAOS: Morning/unsorted (nebula_storm.png)
- FOCUS: Deep work (infinity_gauntlet_fist.png)
- BALANCE: Daily goal achieved (farm_sunrise.png)

**Key Methods:**
- `set_state(state)`: Change visual state
- `check()`: Verify Kitty terminal availability

#### 5. notifications.py (Notification Manager)

**Responsibilities:**
- macOS notification center integration
- Telegram bot notifications (optional)
- Urgency level support

**Key Methods:**
- `send(title, message, urgency)`: Send notification

## Design Rationale

### Why Classification-First?

**Problem**: ADHD brains convert casual thoughts into tasks automatically.

**Solution**: Classification gate intercepts inputs and prevents inappropriate task creation.

**Benefits:**
- Reduces cognitive load
- Prevents task list bloat
- Allows emotional processing without guilt
- Maintains focus on actual work

### Why Separate Handlers?

**Problem**: One-size-fits-all responses feel robotic and miss context.

**Solution**: Classification-specific handlers provide appropriate responses.

**Benefits:**
- Thinking → Acknowledgment without action pressure
- Venting → Validation without forced problem-solving
- Observation → Optional capture without commitment
- Question → Direct answer without task creation
- Task → Full orchestration with feedback

### Why Multi-Modal Feedback?

**Problem**: Text-only interfaces lack immersion and motivation.

**Solution**: Voice + visuals + notifications create embodied experience.

**Benefits:**
- Voice: Thanos persona reinforcement
- Visuals: Ambient awareness of current state
- Notifications: Cross-device awareness
- Combined: Immersive, motivating experience

### Why Thanos Persona?

**Problem**: Generic AI responses lack character and motivation.

**Solution**: Consistent Thanos voice throughout interactions.

**Benefits:**
- Memorable and engaging
- Reinforces discipline and execution
- Reduces task avoidance
- Makes productivity fun

## Implementation Details

### File Structure

```
Shell/
├── thanos-cli              # Main CLI (407 lines)
└── lib/
    ├── classifier.py       # Classification (157 lines)
    ├── voice.py            # Voice synthesis (TBD)
    ├── visuals.py          # Visual state (TBD)
    └── notifications.py    # Notifications (TBD)
```

### Error Handling

- Classification failures → log and default to question
- Voice failures → silent (non-blocking)
- Visual failures → silent (non-blocking)
- Notification failures → silent (non-blocking)

**Rationale**: Core CLI functionality should never block on optional feedback.

### Logging

All activity logged to `State/shell_activity.log`:

```
[timestamp] [level] message
```

**Levels**: INFO, WARN, ERROR

## Alternatives Considered

### 1. LLM-Based Classification

**Pros:**
- More flexible
- Better context understanding
- Handles edge cases

**Cons:**
- Latency (100-500ms per call)
- Cost (API calls)
- Non-deterministic
- Requires network

**Decision**: Use pattern-based classification for speed and determinism.

### 2. Skills-Based Routing

**Pros:**
- More powerful
- Better orchestration
- Skill reuse

**Cons:**
- Overkill for simple routing
- Harder to debug
- Adds complexity

**Decision**: Use direct handlers for simplicity. Can migrate to skills later.

### 3. Interactive Classification Confirmation

**Pros:**
- User confirms classification
- Reduces misclassification impact

**Cons:**
- Adds friction
- Slows workflow
- Breaks flow state

**Decision**: Trust classification, offer capture options post-hoc.

## Consequences

### Positive

1. **ADHD-Optimized**: Classification gate prevents casual thoughts → tasks
2. **Fast**: Pattern-based classification is instant (<1ms)
3. **Immersive**: Multi-modal feedback creates engaging experience
4. **Maintainable**: Clear separation of concerns
5. **Extensible**: Easy to add new classifications or handlers

### Negative

1. **Pattern Maintenance**: Classification patterns require tuning
2. **False Positives**: Some inputs may misclassify
3. **Feedback Dependencies**: Voice/visuals require external tools
4. **Monolithic CLI**: Shell script growing in complexity

### Mitigations

1. **Pattern Testing**: Comprehensive test suite for classification
2. **Dry-Run Mode**: Allows testing classification without execution
3. **Graceful Degradation**: All feedback is optional and non-blocking
4. **Future Refactor**: Can migrate to Python CLI if bash becomes unwieldy

## Testing Strategy

### 1. Unit Tests

- Classification patterns (8 test cases)
- Edge cases (empty input, special chars)
- Confidence scoring

### 2. Integration Tests

- CLI with --dry-run
- Each classification handler
- Multi-modal feedback (when available)

### 3. Manual Tests

- Real-world input examples
- Edge cases and ambiguous inputs
- User experience validation

## Future Enhancements

### Phase 3 Integration

1. **Energy-Aware Gating**: Check Oura readiness before task execution
2. **Smart Routing**: Health questions → health-insight skill
3. **Brain Dump Integration**: Auto-capture thoughts/observations
4. **Completion Detection**: "Snap" celebration on daily goal
5. **Interactive Prompts**: Better Y/N capture experience

### Long-Term

1. **LLM Classification**: Hybrid pattern + LLM for edge cases
2. **Learning System**: Track misclassifications and improve
3. **Multi-Language Support**: Python CLI with better testing
4. **Plugin System**: Extensible feedback mechanisms

## Success Metrics

1. **Classification Accuracy**: >90% correct classification
2. **Response Time**: <100ms total (including classification)
3. **User Satisfaction**: Reduced task list bloat
4. **Completion Rate**: More tasks completed (better routing)

## References

- `/Users/jeremy/Projects/Thanos/CLAUDE.md` (Thanos OS specs)
- `/Users/jeremy/Projects/Thanos/Shell/README.md` (Shell CLI docs)
- ADR-001: Thanos v2.0 Architecture
- ADR-002: Classification and Routing Protocol

## Appendix: Classification Patterns

### Task Patterns

```regex
create|add|make|build|implement
complete|finish|done
can you help.*debug|fix
fix|solve|resolve
update|modify|change
delete|remove|clean
```

### Question Patterns

```regex
\?
^(what|when|where|who|why|how)
```

### Thinking Patterns

```regex
wondering
what if
thinking about
considering
```

### Venting Patterns

```regex
(tired|exhausted|frustrated)
this is.*frustrating
so frustrat
ugh|argh
```

### Observation Patterns

```regex
noticed
just saw
fyi|heads up
looks like
```

## Decision

Implement Shell CLI with classification-first routing as designed.

**Approved by**: System Architecture Designer
**Date**: 2026-01-21
