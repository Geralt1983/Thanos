# /pa:email - Email Management Command

Intelligent email inbox management with prioritization and action recommendations.

## Usage
```
/pa:email [action] [options]
```

## Actions

### summary (default)
Triage inbox with smart prioritization.
```
/pa:email summary --timeframe 24h
```

### draft
Draft a response with context awareness.
```
/pa:email draft --to "recipient" --subject "topic"
```

### search
Find emails with natural language.
```
/pa:email search "Epic ordersets from last week"
```

### followup
Identify emails needing follow-up.
```
/pa:email followup --overdue
```

## Priority Classification

### P1 - Immediate (Red)
- Direct requests from key stakeholders
- Time-sensitive deadlines (< 24h)
- Client escalations
- Epic production issues

### P2 - Today (Orange)
- Action items with this-week deadlines
- Meeting requests requiring response
- Project updates needing review

### P3 - This Week (Yellow)
- FYI items from important senders
- Non-urgent requests
- Newsletters worth reading

### P4 - Archive/Skip (Gray)
- Marketing emails
- Automated notifications
- Low-priority FYIs

## Output Format - Summary
```markdown
## Email Triage - [Timeframe]

### Immediate Action (P1)
- [Sender]: [Subject] - [Recommended action]

### Today (P2)
- [Sender]: [Subject] - [Summary]

### This Week (P3)
- [Count] emails - [Categories]

### Stats
- Unread: [X]
- Action needed: [Y]
- Can archive: [Z]
```

## Output Format - Draft
```markdown
## Draft Response

**To:** [Recipient]
**Subject:** [Subject]
**Context:** [Thread summary]

---
[Draft content]
---

**Tone:** [Professional/Casual/Formal]
**Actions mentioned:** [Any commitments made]
```

## Flags
- `--timeframe [1h|24h|7d]`: Time range for summary
- `--unread-only`: Only unread messages
- `--from [sender]`: Filter by sender
- `--epic`: Only Epic-related emails
- `--urgent`: Only P1 items
