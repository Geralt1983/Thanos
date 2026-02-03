## Relations
@structure/architecture/hooks/ai_lifecycle_hooks.md

## Raw Concept
**Task:**
Enforce Automation-First Directive for Jeremy

**Changes:**
- Established "Automation First" as a core operational directive

**Flow:**
Task Received -> Attempt Automation (min 2 hours) -> If failed: Exhaust all tool combos -> Only then: Suggest manual work

**Timestamp:** 2026-02-03

## Narrative
### Structure
- Directive: Never suggest manual work first.
- Threshold: 2+ hours of automation attempts.
- Scope: All tasks including configuration, data extraction, and system management.

### Features
- Strict prohibition against suggesting manual work unless 2+ hours of automation effort have been exhausted.
- Full utilization of all available tools (bash_exec, skills, browser, coding) is expected.
- Priority: Write scripts, chain tools, and build custom solutions over manual tasks.
- Mandatory Rule: Automation > Manual. Always.
