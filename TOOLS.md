# TOOLS.md - Local Notes

## Skills Reference
**CHECK FIRST:** https://github.com/VoltAgent/awesome-openclaw-skills
- 700+ community skills organized by category
- Install: `npx clawdhub@latest install <skill-slug>`

Skills define *how* tools work. This file is for *your* specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:
- Camera names and locations
- SSH hosts and aliases  
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## TTS / Voice

- **Thanos voice:** `SuMcLpxNrgPskVeKpPnh` (ElevenLabs)
- Use for key moments only — cosmic gravitas, not chatter

### Voice Triggers (Marvel Thanos style)

| Trigger | Examples |
|---------|----------|
| **Task start** | "Inevitable." / "It begins." |
| **Completion** | "Perfectly balanced." / "As it should be." |
| **Question** | "Do you understand?" / "What will you sacrifice?" |
| **Error** | "Reality is often disappointing." / "A setback. Nothing more." |

Keep it short. Philosophical weight. Destiny/balance themes.

## Google Calendar

Account: `jkimble1983@gmail.com`

| Calendar | ID | Notes |
|----------|-----|-------|
| MY PLANNED LIFE | `kimble.corin@gmail.com` | Shared (writer) |
| Primary | `jkimble1983@gmail.com` | Personal |
| Time Management | `9b3bba4f08c0a362e33910a9c372126404dc005a46085dec252867ce23f58faf@group.calendar.google.com` | |
| Work | `6138b022643cdc3f3c35656282ef4b2bc67e76bf3be77e403fe12f42524724aa@group.calendar.google.com` | |
| Family | `family12378744586345757418@group.calendar.google.com` | |

## Browser Automation

- **Profile:** `openclaw` (managed browser, isolated from personal Chrome)
- **Kimi:** Already logged in as Jeremy Kimble (Moderato plan)
- **Browser Use:** API key in `.env`, profile `Thanos-Main` created
- **Start:** `browser action=start profile=openclaw`

## Todoist

- **CLI:** `todoist` (todoist-ts-cli v0.2.0+)
- **Projects:** Inbox, Personal, Someday (personal only)
- **Commands:**
  - `todoist today` — today's tasks
  - `todoist add "task" --due "tomorrow"`
  - `todoist done <id>` — complete task
  - `todoist tasks` — list all tasks

## Examples

```markdown
### Cameras
- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH
- home-server → 192.168.1.100, user: admin
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
