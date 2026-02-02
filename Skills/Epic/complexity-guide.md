# Epic Task Complexity Guide

Learned from actual work tasks (2026-02-01).

## Simple Tasks (●)
**Characteristics:**
- Email-based (send, respond, forward)
- Finding/gathering information
- Converting formats (email → PDF)
- Looking up data
- Simple confirmations (no build/spec work)
- Surveys/questionnaires

**Examples:**
- Import Harry emails into NotebookLM
- Look for and do Orlando surveys
- Send status update email
- Find provider contact info

**Effort:** <30 min, low cognitive load

---

## Moderate Tasks (●●)
**Characteristics:**
- Checking against available info + adding notes
- Writing tickets/documentation
- Coordinating transfers or migrations (records, not code)
- Updates that require research
- Troubleshooting with clear scope
- Tasks with deadlines that add pressure

**Examples:**
- Orion updates - check Lab/Rad info, add notes
- PCT: Migrate Alabama records to TST (coordination, documentation)
- Solve and respond to Provider Group ticket (if you have access)
- Document interface configuration

**Effort:** 1-3 hours, moderate cognitive load

**Warning signs it might be complex:**
- Missing access/permissions
- Requires architectural decisions
- Involves multiple stakeholders
- No clear path to completion

---

## Complex Tasks (●●●)
**Characteristics:**
- Building anything (orderset, SmartText, ClinDoc)
- Tasks involving specs/specifications
- Old tasks with accumulated complexity
- Requires cross-team communication
- Multi-step with dependencies
- Clinical builds with safety implications

**Examples:**
- Confirm MORA Organ Donor OS with Beverly (build + old task + specs + comms)
- New orderset build
- ClinDoc optimization with workflow changes
- Interface build with HL7 spec review

**Effort:** 4+ hours, high cognitive load, often spans multiple days

**Epic-specific complexity triggers:**
- "Build" + "spec"
- "Orderset" anything
- "SmartText" configuration
- "ClinDoc" builds
- "Organ donor" workflows (high stakes)
- Old tasks that have been sitting (accumulated unknowns)

---

## Classification Keywords

### Simple
import, find, look for, survey, convert, email, call, schedule, review, check, organize, file, send, respond

### Moderate
update, migrate, move records, transfer, write, analyze, document, investigate, troubleshoot, coordinate, plan, research, prepare

### Complex
build, develop, implement, architect, design, integrate, optimize, orderset, smarttext, spec, clindoc build, interface build

### Context Matters
- **"Confirm" alone** = simple
- **"Confirm" + build/spec** = complex
- **"Migrate" alone** = moderate (coordination)
- **"Migrate" + code/system** = complex (implementation)

---

## Energy Matching

| Energy State | Can Handle |
|--------------|------------|
| Low (<50) | Simple only - stick to emails, lookups, quick confirmations |
| Moderate (50-69) | Simple + Moderate - updates, tickets, coordination work |
| High (70+) | All tasks - tackle builds, specs, complex problem-solving |

---

## Tips for Jeremy's Work

1. **Builds always go last** - defer to high-energy days
2. **Start day with simple wins** - email, surveys, quick updates
3. **Moderate tasks in mid-morning** - after caffeine, before lunch slump
4. **Complex tasks need 3+ hour blocks** - don't start if you can't finish
5. **Old tasks are complex** - accumulated unknowns = cognitive overhead

---

*Updated: 2026-02-01 based on live task feedback*
