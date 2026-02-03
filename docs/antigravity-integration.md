# Antigravity + OpenClaw Integration

**Status:** Researched, not implemented  
**Date:** 2026-02-03  
**Source:** https://youtu.be/1Jqaj1KN5vA

## What Antigravity Is

Google's Agentic IDE with specialized coding agents:
- **UX Designer Agent** - Frontend/UI work
- **Reviewer Agent** - Code review and refinement
- **Debugger Agent** - Error detection and fixes
- **Builder Agent** - Core implementation

**Primary Model:** Gemini 3 Pro (generous free tier)  
**Also Supports:** Claude models, open source models

## Integration Pattern

```
User (Telegram/WhatsApp/CLI)
    ↓
OpenClaw (orchestrator/command center)
    ↓
Antigravity (specialized agent execution)
    ↓
Results delivered back through OpenClaw
```

## Setup Commands

```bash
# Enable Antigravity OAuth plugin
openclaw plugins enable google-antigravity-auth

# Login to Google
openclaw models auth login --provider google-antigravity --set-default

# Use Antigravity models
openclaw models set google-antigravity/gemini-3-pro
```

## Model Pricing Reality

**Free Tier (Gemini):**
- Gemini 3 Flash: Free tier available
- Gemini 3 Pro: Generous free quotas

**NOT Free (Claude via Antigravity):**
- Opus 4.5: $5/M input, $25/M output
- Sonnet 4.5: $3/M input, $15/M output

Video claims about "free Opus 4.5" are misleading - you can access it *through* Antigravity OAuth, but still pay Anthropic pricing.

## Potential Use Cases

1. **Client demo/prototype work** - Use free Gemini tier for rapid prototyping
2. **Multi-agent workflows** - Leverage pre-tuned agent personas
3. **Phone-to-production pipeline** - WhatsApp → OpenClaw → Antigravity → deployed app
4. **Review/QA agent** - Dedicated reviewer agent for code quality

## Why Not Implemented (Yet)

**Current stack is sufficient:**
- Already have Codex CLI for agent orchestration
- Paying for Anthropic models anyway
- Codex proven faster than desktop app UI automation
- No immediate need for Gemini free tier

**Consider when:**
- Need specialized agent personas (UX/reviewer/debugger)
- Want to experiment with Google's agent coordination
- Client work benefits from free tier prototyping
- Multi-agent parallelization becomes a bottleneck

## Related Resources

- [OpenClaw Model Providers Docs](https://docs.openclaw.ai/concepts/model-providers)
- [Antigravity Kit](https://github.com/google/antigravity-kit) (check if exists)
- Video demo: https://youtu.be/1Jqaj1KN5vA

## Notes

- OAuth method is official (Google retweeted setup tutorials)
- Can wire up with cron jobs for autonomous execution
- Antigravity handles agent swapping/routing internally
- Integration adds authentication complexity vs direct Codex use
