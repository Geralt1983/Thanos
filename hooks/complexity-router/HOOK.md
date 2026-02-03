---
name: complexity-router
description: "Auto-escalate model based on message complexity (STUB - waiting for message:received event)"
metadata: { "openclaw": { "emoji": "🧠", "events": ["message:received"], "requires": { "config": ["workspace.dir"] } } }
---

# Complexity Router Hook

**STATUS: STUB** — Waiting for OpenClaw to implement `message:received` event.

## What It Will Do

When `message:received` becomes available:
1. Analyze incoming message for complexity signals
2. Score based on keywords, length, question type
3. Call `session_status(model=X)` to escalate before agent responds

## Complexity Scoring

| Score | Model | Triggers |
|-------|-------|----------|
| 0.0-0.3 | Haiku | Quick questions, yes/no, simple lookups |
| 0.3-0.7 | Sonnet | Code, explain, implement, debug |
| 0.7-1.0 | Opus | Analyze, architecture, strategic, deep dive |

## Current Workaround

Using SOUL.md keyword triggers until this hook is functional.
