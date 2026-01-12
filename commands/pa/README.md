# Personal Assistant Commands (pa)

A suite of personal assistant commands for Claude Code to help manage your day, tasks, email, calendar, and more.

## Quick Start

```bash
# Morning briefing
/pa:daily

# Check email with priority triage
/pa:email summary

# View today's calendar
/pa:calendar view --today

# View today's schedule
/pa:schedule view

# Get next task recommendation
/pa:tasks focus

# Process brain dump entries
/pa:process

# Export data for analysis
/pa:export

# Weekly review
/pa:weekly
```

## Available Commands

| Command | Purpose | Quick Usage |
|---------|---------|-------------|
| `/pa:daily` | Morning briefing | `/pa:daily --quick` |
| `/pa:email` | Email management | `/pa:email summary --timeframe 24h` |
| `/pa:calendar` | Calendar sync & viewing | `/pa:calendar view --today` |
| `/pa:schedule` | Schedule management | `/pa:schedule find --duration 30m` |
| `/pa:tasks` | Task management | `/pa:tasks focus --energy high` |
| `/pa:brainstorm` | Ideation & planning | `/pa:brainstorm "topic" --mode solve` |
| `/pa:process` | Brain dump processing | `/pa:process --limit 20 --dry-run` |
| `/pa:export` | Data export | `/pa:export --format csv --type tasks` |
| `/pa:weekly` | Weekly review | `/pa:weekly review` |
| `/pa:epic` | Epic consulting work | `/pa:epic status` |

## Setup Requirements

### 1. Profile Configuration
Edit `~/.claude/profile.md` to add your:
- Work context and preferences
- Energy patterns and focus times
- Integration credentials
- Goals and key projects

### 2. Google Workspace Integration
Install the Google MCP server:
```bash
# Add to your MCP configuration
mcp-gsuite-enhanced
```

Configure OAuth credentials in your MCP settings.

### 3. Task System Integration
Configure your task management integration:
- ClickUp: Add API token
- Notion: Add integration token
- Or configure your preferred system

## Command Patterns

### Daily Workflow
```bash
# Morning: Start with briefing
/pa:daily

# View today's calendar
/pa:calendar view --today

# Throughout day: Task focus
/pa:tasks focus --duration 30m

# Check email periodically
/pa:email summary --timeframe 2h

# End of day: Process brain dumps and review
/pa:process --limit 5
/pa:tasks review
```

### Weekly Pattern
```bash
# Sunday/Monday: Weekly planning
/pa:weekly plan

# Mid-week: Check project status and process backlog
/pa:epic status
/pa:process --limit 20

# Friday: Export data and weekly reflection
/pa:export --format csv --type all
/pa:weekly reflect
```

### Ad-hoc Usage
```bash
# Need to schedule a meeting
/pa:schedule find --duration 1h --attendees "team"

# Sync and check calendar
/pa:calendar sync --week

# Find available time slots
/pa:calendar find "meeting slot"

# Brainstorm a problem
/pa:brainstorm "How to improve orderset adoption" --mode solve

# Process captured ideas before they pile up
/pa:process --dry-run  # Preview first
/pa:process           # Then process for real

# Export data for backup or analysis
/pa:export --format json --type all           # Full backup
/pa:export --format csv --type tasks          # Tasks for spreadsheet
/pa:export --type habits --output ~/Documents # Custom location

# Quick email check
/pa:email summary --urgent
```

## Customization

### Adding Custom Commands
Create new `.md` files in `~/.claude/commands/pa/` following the existing patterns.

### Modifying Existing Commands
Edit the command files to adjust:
- Output formats
- Priority rules
- Integration points
- Default behaviors

## Integration with SuperClaude

These commands work alongside the SuperClaude framework:
- Use `/sc:analyze` for code analysis
- Use `/pa:tasks` for task management
- Use `/pa:export` for data portability and analysis
- Combine with `--think` flags for complex planning

## File Structure
```
~/.claude/
├── commands/
│   ├── pa/                    # Personal Assistant
│   │   ├── README.md          # This file
│   │   ├── daily.md           # Morning briefing
│   │   ├── email.md           # Email management
│   │   ├── calendar.py        # Calendar sync & viewing
│   │   ├── schedule.md        # Schedule management
│   │   ├── tasks.md           # Task management
│   │   ├── brainstorm.md      # Ideation
│   │   ├── process.md         # Brain dump processing
│   │   ├── export.md          # Data export
│   │   ├── weekly.md          # Weekly review
│   │   └── epic.md            # Epic consulting
│   └── sc/                    # SuperClaude commands
└── profile.md                 # User profile & context
```

## Troubleshooting

### Commands not recognized
Ensure command files have correct frontmatter and are in the right directory.

### Integration not working
Check MCP server configuration and API credentials.

### Missing context
Update `profile.md` with relevant information for better personalization.
