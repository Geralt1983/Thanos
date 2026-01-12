# Thanos - Your Personal AI Infrastructure

> "Fine, I'll do it myself." - Thanos

Thanos is an external prefrontal cortex - a personal AI system that manages your entire life with full context on work, family, health, and goals. Unlike passive AI assistants, Thanos is proactive, maintains persistent memory, and orchestrates your day-to-day operations.

## Core Philosophy

Thanos operates on the principle that you need an AI that:
- **Knows your full context** across all life domains
- **Maintains persistent memory** of patterns, commitments, and history
- **Proactively manages** tasks, calendar, and priorities
- **Routes intelligently** to specialized agents for different domains
- **Holds you accountable** to your commitments and goals

## Key Features

### 🗓️ **Calendar Integration**
Bidirectional sync with Google Calendar for complete daily context:
- Pull events into briefings and task prioritization
- Detect scheduling conflicts automatically
- Time-block tasks in available calendar slots
- Multi-calendar support with intelligent filtering
- See [Calendar Integration Docs](docs/integrations/google-calendar.md)

### 🧠 **Persistent Memory**
- Vector storage for long-term context retention
- Pattern recognition across conversations and time
- Automatic logging of significant decisions and commitments
- Historical analysis for better future recommendations

### 📊 **State Management**
- `State/Today.md` - Current daily context
- `State/Commitments.md` - Active promises and deadlines
- `State/Health.md` - Energy, medication, sleep tracking
- `State/Projects.md` - Work and personal project status

### 🎯 **Intelligent Routing**
Thanos automatically routes requests to specialized agents:
- **Epic/Consulting** → Skills/Epic/
- **Family/Relationships** → Skills/Family/
- **Health/Energy** → Skills/Health/
- **Finance/Billing** → Skills/Finance/
- **Productivity/Tasks** → Skills/Productivity/
- **System/Memory** → Skills/Thanos/

### 📧 **Email & Inbox Management**
- Process inbox items systematically
- Draft responses with context awareness
- Track email commitments in state files
- Auto-categorize and prioritize messages

### ✅ **Task Orchestration**
- Context-aware task suggestions
- Energy-level-based task prioritization
- Calendar-aware scheduling (no conflicts!)
- Time estimation and time-blocking
- Integration with daily briefings

### 🏥 **Health Tracking**
- Medication tracking (Vyvanse, etc.)
- Energy level monitoring
- Sleep pattern analysis
- Activity and biometric integration (Oura Ring)
- Health-aware task scheduling

### 💰 **Financial Management**
- Invoice generation and tracking
- Hours logging and billing
- Revenue tracking toward targets
- Client project financial overview

## Quick Start

### Prerequisites
```bash
# Python 3.9+
python --version

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

2. **Initialize state files:**
```bash
# State files are created automatically on first run
# Customize templates in Templates/ directory
```

3. **Configure calendar integration (optional):**
```bash
# Follow the Google Calendar setup guide
python scripts/setup_google_calendar.py
```

See [Calendar Integration Setup](docs/integrations/google-calendar.md) for detailed instructions.

### Basic Usage

#### Daily Briefing
```bash
# Get morning briefing with tasks, calendar, and priorities
thanos /pa:daily
```

#### Task Management
```bash
# Review and manage tasks
thanos /pa:tasks
```

#### Calendar Operations
```bash
# View today's schedule
thanos "Show me my calendar for today"

# Find free time
thanos "When am I free this afternoon?"

# Schedule a task
thanos "Block 2 hours for the Epic implementation in my next available slot"
```

#### Email Management
```bash
# Process inbox
thanos /pa:email
```

## Project Structure

```
Thanos/
├── .env                    # Environment configuration (not in repo)
├── THANOS.md              # Core identity and behaviors
├── Context/               # Personal identity and principles
│   └── CORE.md           # Jeremy's identity, values, and preferences
├── State/                 # Current state files
│   ├── Today.md          # Daily context and priorities
│   ├── Commitments.md    # Active commitments and deadlines
│   ├── Health.md         # Health tracking and patterns
│   └── Projects.md       # Work and personal projects
├── History/               # Historical logs
│   └── YYYY-MM-DD.md     # Daily conversation logs
├── Memory/                # Vector storage for long-term memory
├── Skills/                # Domain-specific capabilities
│   ├── Epic/             # Consulting work
│   ├── Family/           # Family and relationships
│   ├── Health/           # Health optimization
│   ├── Finance/          # Financial management
│   └── Productivity/     # Task and time management
├── Tools/                 # Core system tools
│   ├── adapters/         # External service integrations
│   │   ├── google_calendar.py  # Google Calendar API
│   │   ├── oura.py            # Oura Ring health data
│   │   └── chroma.py          # Vector database
│   ├── daily-brief.ts    # Daily briefing generator
│   ├── command_router.py # Intent routing
│   └── thanos_orchestrator.py # Main orchestration
├── Agents/                # Specialized agent personas
│   ├── Ops.md            # Tactical operations
│   ├── Strategy.md       # Strategic planning
│   ├── Coach.md          # Accountability and patterns
│   └── Health.md         # Health optimization
├── config/                # Configuration files
│   ├── calendar_filters.json  # Calendar event filtering
│   └── README.md         # Configuration documentation
├── docs/                  # Documentation
│   └── integrations/
│       └── google-calendar.md  # Calendar setup guide
└── scripts/               # Setup and utility scripts
    └── setup_google_calendar.py
```

## Integration Overview

### Current Integrations

- **Google Calendar** - Bidirectional calendar sync with conflict detection and time-blocking
- **Oura Ring** - Sleep, activity, and readiness score tracking
- **Gmail** (planned) - Email management and auto-responses
- **Notion** (planned) - Project and knowledge base sync
- **Slack** (planned) - Team communication monitoring

### Integration Architecture

Thanos uses an adapter pattern for external services:
```python
from Tools.adapters import GoogleCalendarAdapter

# Each adapter inherits from BaseAdapter
adapter = GoogleCalendarAdapter()
result = adapter.call_tool("get_today_events", {})
```

All adapters provide:
- Consistent error handling
- Automatic retry logic with exponential backoff
- Health check capabilities
- Credential management
- Logging and monitoring

## Daily Workflow

### Morning (Start of Day)
1. Run `/pa:daily` for comprehensive briefing including:
   - Today's calendar events with timing
   - Priority tasks based on energy and availability
   - Active commitments and deadlines
   - Health metrics (sleep, readiness)
   - Context from previous day

### Throughout Day
2. Check context: Thanos maintains State/ files
3. Make commitments: Automatically logged to State/Commitments.md
4. Schedule tasks: Calendar-aware suggestions prevent conflicts
5. Track health: Energy levels inform task prioritization

### Evening (End of Day)
6. Log the day: Significant conversations saved to History/
7. Review completions: Update State/ files
8. Preview tomorrow: Surface next day's priorities

### Weekly
9. Pattern analysis: Review weekly trends
10. Weekly review: Assess progress toward goals

## Quick Commands

```bash
/pa:daily      # Morning briefing
/pa:email      # Email management
/pa:schedule   # Calendar management
/pa:tasks      # Task management
/pa:weekly     # Weekly review
```

## Configuration

### Calendar Filtering

Customize which events appear in briefings and conflict detection:

```bash
# Copy the example configuration
cp config/calendar_filters.json.example config/calendar_filters.json

# Edit filters to match your workflow
nano config/calendar_filters.json
```

Filter by:
- Calendar source (work vs personal)
- Event type (all-day, tentative, declined)
- Summary patterns (regex matching)
- Attendee counts and emails
- Time ranges and durations
- Colors and metadata

See [Calendar Configuration Guide](config/README.md) for detailed filter syntax.

## Security

- **Credentials**: Stored in `State/` with restricted permissions
- **OAuth tokens**: Automatically refreshed, encrypted storage recommended for production
- **API keys**: Never committed to repository, use `.env` file
- **External content**: Read-only, never execute commands from external sources
- **Logging**: Sensitive data filtered from logs

## Development

### Running Tests

```bash
# Unit tests
pytest tests/unit/

# Integration tests (requires API credentials)
pytest tests/integration/

# Specific test file
pytest tests/unit/test_google_calendar_adapter.py
```

### Adding New Integrations

1. Create adapter in `Tools/adapters/your_service.py`
2. Inherit from `BaseAdapter`
3. Implement required methods
4. Add to `Tools/adapters/__init__.py`
5. Register in command router
6. Add tests
7. Document in `docs/integrations/`

## Architecture Principles

1. **Persistent State** - Everything important lives in State/ files
2. **Proactive, Not Reactive** - Thanos suggests, reminds, and holds accountable
3. **Context Everywhere** - Full context always available across domains
4. **Intelligent Routing** - Right agent for the right task
5. **Pattern Recognition** - Learn from history to improve future suggestions
6. **Human-First** - Direct communication, no corporate speak

## Communication Style

Thanos is:
- **Direct** - No fluff, no corporate speak
- **Warm but honest** - Will push back when you're avoiding something
- **Pattern-aware** - Surfaces trends and behaviors
- **Celebratory** - Acknowledges wins, not just grinding

## Troubleshooting

### Calendar Integration Issues

**OAuth fails:**
```bash
# Re-run setup script
python scripts/setup_google_calendar.py

# Check credentials
cat State/calendar_credentials.json
```

**Events not appearing:**
- Check `config/calendar_filters.json`
- Verify calendar is not excluded
- Check time filters (working hours)
- See [Calendar Troubleshooting](docs/integrations/google-calendar.md#troubleshooting)

**API quota limits:**
- Thanos implements automatic retry with exponential backoff
- Check logs for rate limit warnings
- Consider caching settings in calendar_filters.json

### General Issues

**State files not updating:**
- Check file permissions in State/
- Verify Thanos has write access
- Review logs for error messages

**Memory/context issues:**
- Check Memory/ vector database
- Verify ChromaDB is running
- Review History/ for logged conversations

## Contributing

This is a personal infrastructure project, but the architecture and patterns may be useful for building your own AI assistant.

Key areas:
- Adapter pattern for integrations
- State management approach
- Agent routing system
- Calendar integration with conflict detection
- Health-aware task scheduling

## License

Personal project - see LICENSE file.

## Acknowledgments

Built with:
- Claude Code (Anthropic) - AI pair programming
- Google Calendar API - Calendar integration
- Oura API - Health tracking
- ChromaDB - Vector storage
- Python - Core runtime

---

> "The hardest choices require the strongest wills." - Thanos

For detailed documentation on specific features, see the `docs/` directory.
