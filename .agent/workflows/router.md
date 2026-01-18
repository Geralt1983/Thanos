---
description: Select the most appropriate agent (skill) for the current task
---

1. Review the user's request and the current task.
2. Review available skills in `.gemini/skills/` and `Skills/`.
3. Select the SINGLE most appropriate skill for the task.
    - If it's a coding task, prefer specialized skills (Refactorer, Tester, etc.) over generic ones.
    - If it's a system/meta task, use Thanos (Archivist/Manager).
    - If uncertain, default to Architect for planning or Troubleshooter for fixing.
4. Announce your selection clearly:
   > **Agent Selected: [Skill Name]**
   > *[Brief reason for selection]*
5. Load the selected skill's context using `view_file`.
   - Path will be either `.gemini/skills/[skill]/SKILL.md` or `Skills/[Skill]/SKILL.md`.
