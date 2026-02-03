## Relations
@code_style/operational_principles/automation_first_directive.md

## Raw Concept
**Task:**
Establish Agent Workflow: Codex (Execution) + Thanos (Review)

**Changes:**
- Formalized the delegation of implementation tasks to Codex CLI
- Positioned Thanos as the validation and review layer for Codex's work

**Flow:**
Task -> Delegate to Codex -> Codex Implementation -> Thanos Review -> Final Validation

**Timestamp:** 2026-02-03

## Narrative
### Structure
- Implementation Agent: Codex
- Review/Validation Agent: Thanos
- Handoff: Codex implements -> Thanos reviews completion

### Dependencies
Requires Codex CLI for implementation. Thanos acts as the orchestrator and reviewer.

### Features
- Delegation: All code discovery and implementation should be delegated to Codex.
- Oversight: Thanos is responsible for reviewing and validating the changes made by Codex.
- Efficiency: Leverages Codex's speed and thoroughness for technical execution while maintaining human-aligned oversight via Thanos.
