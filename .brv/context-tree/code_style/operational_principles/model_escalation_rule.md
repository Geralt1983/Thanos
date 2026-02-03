## Relations
@code_style/operational_principles/automation_first_directive.md
@structure/architecture/hooks/ai_lifecycle_hooks.md

## Raw Concept
**Task:**
Define Model Escalation Rule for Haiku.

**Changes:**
- Haiku is restricted from performing technical tasks (debugging, API errors, troubleshooting, configuration, installation).
- Mandatory immediate escalation to Sonnet for these tasks.

**Files:**
- .brv/context-tree/code_style/operational_principles/model_escalation_rule.md

**Flow:**
Haiku identifies technical task -> immediate escalation to Sonnet.

**Timestamp:** 2026-02-03

## Narrative
### Structure
.brv/context-tree/code_style/operational_principles/model_escalation_rule.md

### Dependencies
Hard constraint on agent task execution and routing.

### Features
Enforces strict escalation from Haiku to Sonnet for any technical tasks including debugging, API errors, troubleshooting, configuration, or installation.
