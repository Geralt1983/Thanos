# ModelEscalator V2 - User Guide

Enhanced model escalation with ML-ready complexity detection, comprehensive logging, and user feedback.

## What's New in V2

### 1. Enhanced Complexity Detection
- **7 features** instead of simple heuristics:
  - Message length
  - Technical density (keyword analysis)
  - Conversation depth
  - Token usage
  - Multi-step indicators
  - Code presence
  - Question complexity

- **ML-ready architecture**: Features are extracted and weighted, making it easy to train a proper ML model later

### 2. Comprehensive Logging & Metrics
- File-based logging to `~/Projects/Thanos/logs/model_escalator.log`
- Detailed JSON logs for each escalation event
- Aggregate metrics via CLI

### 3. User Feedback Mechanism
- Rate model choices: 1-5 scale
  - **1-2**: Model too weak (should have escalated)
  - **3**: Just right
  - **4-5**: Model overkill (should have de-escalated)
- Feedback trains the complexity analyzer
- Improves future model selection

## Installation

V2 is drop-in compatible with V1. No config changes needed.

```bash
# Optional: Switch to V2 in your code
# Canonical:
from Tools.model_escalator_v2 import model_escalation_hook_v2 as model_escalation_hook
```

## Usage

### Recording Feedback

After I respond to your message, if the model choice felt wrong:

```bash
# Via CLI
cd ~/Projects/Thanos
python Tools/escalator_cli.py feedback --rating 1 --comment "Needed Opus for this complex task"

# Ratings guide:
# 1 = Way too weak (should have used much more powerful model)
# 2 = Slightly too weak
# 3 = Perfect choice
# 4 = Slightly overkill
# 5 = Way overkill (wasted resources)
```

**Or ask me to record it:**
> "That model choice was too weak, rate it 2"

I'll log it automatically.

### Viewing Metrics

```bash
# Last 7 days (default)
python Tools/escalator_cli.py metrics

# Last 30 days
python Tools/escalator_cli.py metrics --days 30

# Output:
# 📊 Model Escalation Metrics (last 7 days)
# Total escalations: 15
# Average complexity: 0.542
# Feedback count: 8
# Average rating: 3.2/5.0
# 
# Model usage:
#   anthropic/claude-3-5-haiku-20241022: 45
#   claude-sonnet-4-5: 28
#   claude-opus-4-5: 12
```

### Training from Feedback

```bash
# Train complexity analyzer from your feedback
python Tools/escalator_cli.py train

# Requires 10+ feedback samples by default
# Minimum can be adjusted:
python Tools/escalator_cli.py train --min-samples 5
```

This updates the feature weights to better match your preferences.

### Viewing Switch History

```bash
# See model switches for a conversation
python Tools/escalator_cli.py history --conversation main-session

# Output:
# 📜 Model Switch History: main-session
# 2026-02-01 16:00:32
#   anthropic/claude-3-5-haiku-20241022 → claude-sonnet-4-5
#   Complexity: 0.623
```

### Current Status

```bash
python Tools/escalator_cli.py status

# Shows active conversations and their current models
```

## Integration with AGENTS.md

The self-check in AGENTS.md works the same way. V2 just makes the complexity calculation more sophisticated.

### Inline Feedback

Add to AGENTS.md or SOUL.md:

```markdown
## Model Feedback

After complex tasks, ask: "Was that model choice right?"

If user says:
- "Too weak" / "should have used Opus" → record_model_feedback(rating=1-2)
- "Perfect" / "good choice" → record_model_feedback(rating=3)
- "Overkill" / "Haiku would have worked" → record_model_feedback(rating=4-5)
```

## Feature Weights

Current default weights (can be trained from feedback):

| Feature | Weight | Description |
|---------|--------|-------------|
| message_length | 0.15 | Longer messages → more complex |
| technical_density | 0.25 | Technical keywords per 100 chars |
| conversation_depth | 0.15 | More turns → more context needed |
| token_usage | 0.15 | Higher token count → more complex |
| multi_step_indicators | 0.10 | "First", "then", "finally" |
| code_present | 0.10 | Code blocks detected |
| question_complexity | 0.10 | Multiple/complex questions |

After training with feedback, these weights adjust to match your preferences.

## Migration from V1

V2 uses the same database schema with additional tables. Migration is automatic.

**To switch:**
1. Update imports (see Installation above)
2. Existing state and logs preserved
3. Start using feedback mechanism

**Rollback:**
Just switch imports back. Database remains compatible.

## Performance

- Feature extraction: <1ms
- Complexity calculation: <1ms
- Database operations: <5ms
- Total overhead: <10ms per message

## Future Enhancements

Potential additions:
- Proper ML model (scikit-learn RandomForest)
- Historical pattern analysis (time-of-day, user energy)
- Multi-user support (different users = different preferences)
- Integration with cost tracking
- Automatic A/B testing of thresholds

## Troubleshooting

**Feedback not improving accuracy:**
- Need 10+ samples minimum
- Try explicit training: `python Tools/escalator_cli.py train`
- Check metrics to see if ratings are varied enough

**Logs growing too large:**
- Log rotation coming in future version
- For now: `truncate -s 0 ~/Projects/Thanos/logs/model_escalator.log`

**Database issues:**
- Location: `~/Projects/Thanos/model_escalator_state.db`
- SQLite browser: `sqlite3 model_escalator_state.db`
- Reset: Delete DB file (will recreate on next run)

---

**Questions?** Ask me to explain any part of this system.
