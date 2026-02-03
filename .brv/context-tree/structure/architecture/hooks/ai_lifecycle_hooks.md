## Relations
@code_style/operational_principles/codex_thanos_workflow.md

## Raw Concept
**Task:**
Implement and document Multi-Agent Routing (Haiku/Sonnet/Opus)

**Changes:**
- Implemented 3-tier agent routing (main/sonnet/think)
- Enabled model overrides in cron payloads

**Flow:**
User Request -> Select Agent (Main/Sonnet/Think) -> Execute in shared Thanos workspace -> Optional: Override model via Cron Payload

**Timestamp:** 2026-02-03

## Narrative
### Structure
- Tier 1: main (Haiku) - Default/Fast
- Tier 2: sonnet (Sonnet) - Moderate
- Tier 3: think (Opus) - Deep reasoning

### Dependencies
Requires Haiku, Sonnet, and Opus model availability. All agents share the Thanos workspace.

### Features
- 3-tier routing: main (Haiku), sonnet (Sonnet), think (Opus).
- Workspace sharing: All tiers operate within the Thanos workspace.
- Manual switching: Use `/agent <name>` to switch between tiers.
- Task overrides: Cron job payloads can specify model overrides.
- Configuration: Managed via `agents.list[].model` in the config file.
