## Relations
@structure/integrations/openclaw_skills/openclaw_skills_reference.md

## Raw Concept
**Task:**
Fix invalid tool name for Anthropic tool schema compliance

**Changes:**
- Renamed OpenClaw plugin tool from `thanos.route` to `thanos_route`
- Updated SKILL.md to reflect the new tool name

**Files:**
- Tools/openclaw-thanos-plugin/index.ts
- Tools/openclaw-thanos-plugin/skills/thanos-harness/SKILL.md

**Flow:**
User message -> OpenClaw -> thanos_route tool -> openclaw_cli.py -> Thanos Orchestrator

**Timestamp:** 2026-02-03

## Narrative
### Structure
- Tools/openclaw-thanos-plugin/index.ts: `api.registerTool({ name: "thanos_route", ... })`
- Tools/openclaw-thanos-plugin/skills/thanos-harness/SKILL.md: Updated instructions to use `thanos_route`.

### Dependencies
- OpenClaw plugin: Tools/openclaw-thanos-plugin/index.ts
- OpenClaw Skill: Tools/openclaw-thanos-plugin/skills/thanos-harness/SKILL.md

### Features
- Renamed tool from `thanos.route` (dot notation) to `thanos_route` (underscore) to comply with Anthropic tool schema requirements (`^[a-zA-Z0-9_-]+$`).
- Resolves tool schema rejection errors (logged as `tools.22.custom.name`).
