# Thanos Setup Guide

Complete installation and configuration guide for the Thanos Personal AI Assistant.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Environment Configuration](#environment-configuration)
4. [Database Setup](#database-setup)
5. [Optional Integrations](#optional-integrations)
6. [Telegram Bot Setup](#telegram-bot-setup)
7. [Testing the Setup](#testing-the-setup)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Python Version

**Required:** Python 3.9 or higher (3.11+ recommended)

```bash
# Check your Python version
python3 --version

# On macOS, you may need to install via Homebrew
brew install python@3.11
```

### System Dependencies

**macOS:**
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Required dependencies
brew install python@3.11 git
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
```

**Windows:**
- Install Python 3.9+ from [python.org](https://www.python.org/downloads/)
- Install Git from [git-scm.com](https://git-scm.com/downloads)

---

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/thanos.git
cd thanos
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate it
# macOS/Linux:
source .venv/bin/activate

# Windows:
.venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt

# For running tests
pip install -r requirements-test.txt
```

### Step 4: Install Optional Dependencies

Depending on which features you want to use:

```bash
# For Telegram bot (voice transcription, mobile capture)
pip install python-telegram-bot openai httpx

# For Google Calendar integration
pip install google-auth google-auth-oauthlib google-api-python-client

# For WorkOS database sync (PostgreSQL)
pip install asyncpg

# For Neo4j knowledge graph (optional memory system)
pip install neo4j

# For ChromaDB vector search (optional memory system)
pip install chromadb
```

---

## Environment Configuration

### Step 1: Create Environment File

```bash
# Copy the example environment file
cp .env.example .env
```

### Step 2: Configure Environment Variables

Edit `.env` and configure the following variables:

#### Required Variables

| Variable | Description | How to Get |
|----------|-------------|------------|
| `ANTHROPIC_API_KEY` | Claude API key for AI responses | [console.anthropic.com](https://console.anthropic.com/) |
| `OPENAI_API_KEY` | OpenAI API key for Whisper transcription and embeddings | [platform.openai.com](https://platform.openai.com/api-keys) |

```bash
# Required for AI functionality
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
```

#### Telegram Bot (Mobile Capture)

| Variable | Description | How to Get |
|----------|-------------|------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather | See [Telegram Bot Setup](#telegram-bot-setup) |
| `TELEGRAM_ALLOWED_USERS` | Comma-separated Telegram user IDs | Get your ID from @userinfobot |

```bash
# Telegram configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIjKlmNoPqRsTuVwXyZ
TELEGRAM_ALLOWED_USERS=123456789,987654321
```

#### Google Calendar Integration

| Variable | Description | How to Get |
|----------|-------------|------------|
| `GOOGLE_CALENDAR_CLIENT_ID` | OAuth 2.0 client ID | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | OAuth 2.0 client secret | Same as above |
| `GOOGLE_CALENDAR_REDIRECT_URI` | OAuth redirect URI | Usually `http://localhost:8080/oauth2callback` |

```bash
# Google Calendar OAuth credentials
GOOGLE_CALENDAR_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxx
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback
```

**Setup Steps:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the Google Calendar API
4. Create OAuth 2.0 credentials (Desktop application type)
5. Download credentials and extract values to `.env`
6. Run the OAuth setup script:
   ```bash
   python scripts/setup_google_calendar.py
   ```

#### WorkOS Database Sync (Optional)

| Variable | Description | How to Get |
|----------|-------------|------------|
| `WORKOS_DATABASE_URL` | PostgreSQL connection URL | Your Neon/PostgreSQL provider |

```bash
# WorkOS sync (for task management integration)
WORKOS_DATABASE_URL=postgresql://user:password@host/database?sslmode=require
```

#### Oura Ring Integration (Optional)

| Variable | Description | How to Get |
|----------|-------------|------------|
| `OURA_ACCESS_TOKEN` | Oura personal access token | [cloud.ouraring.com](https://cloud.ouraring.com/) |

```bash
# Oura health metrics
OURA_ACCESS_TOKEN=xxxxxxxxxxxxx
```

#### MemOS Hybrid Memory (Optional)

| Variable | Description | How to Get |
|----------|-------------|------------|
| `NEO4J_URL` | Neo4j AuraDB connection URL | [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/) |
| `NEO4J_USERNAME` | Neo4j username (usually "neo4j") | Same as above |
| `NEO4J_PASSWORD` | Neo4j password | Same as above |
| `NEO4J_DATABASE` | Database name (usually "neo4j") | Same as above |

```bash
# Neo4j knowledge graph (optional)
NEO4J_URL=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=xxxxxxxxxxxxx
NEO4J_DATABASE=neo4j
```

#### Advanced Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `CALENDAR_DEFAULT_TIMEZONE` | Default timezone for calendar | America/New_York |
| `OURA_CACHE_DIR` | Directory for Oura cache | ~/.oura-cache |
| `CONTEXT7_API_KEY` | Context7 MCP integration | (optional) |
| `FETCH_USER_AGENT` | User agent for web fetching | (optional) |

### Complete .env Example

```bash
# =============================================================================
# REQUIRED: AI APIs
# =============================================================================
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxx

# =============================================================================
# OPTIONAL: Google Calendar
# =============================================================================
GOOGLE_CALENDAR_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxx
GOOGLE_CALENDAR_REDIRECT_URI=http://localhost:8080/oauth2callback

# =============================================================================
# OPTIONAL: Telegram Bot
# =============================================================================
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGhIjKlmNoPqRsTuVwXyZ
TELEGRAM_ALLOWED_USERS=123456789

# =============================================================================
# OPTIONAL: WorkOS Database Sync
# =============================================================================
# WORKOS_DATABASE_URL=postgresql://user:password@host/database?sslmode=require

# =============================================================================
# OPTIONAL: Oura Ring
# =============================================================================
# OURA_ACCESS_TOKEN=xxxxxxxxxxxxx

# =============================================================================
# OPTIONAL: MemOS (Neo4j Knowledge Graph)
# =============================================================================
# NEO4J_URL=neo4j+s://xxxxx.databases.neo4j.io
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=xxxxxxxxxxxxx
# NEO4J_DATABASE=neo4j
```

---

## Database Setup

Thanos uses SQLite databases that are created automatically on first run. No manual database setup is required.

### Database Locations

| Database | Location | Purpose |
|----------|----------|---------|
| `thanos.db` | `State/thanos.db` | Main state store (tasks, events, brain dumps) |
| `thanos_unified.db` | `State/thanos_unified.db` | Unified state (newer schema) |
| `operator_state.db` | `State/operator_state.db` | Orchestrator state |
| `relationships.db` | `State/relationships.db` | Memory relationship tracking |

### Automatic Initialization

The databases are automatically created with the correct schema when you first run Thanos:

```bash
# This will create all necessary databases
python thanos.py
```

### Manual Initialization (Optional)

If you need to initialize databases manually:

```python
from Tools.state_store import get_db

# This creates/initializes the database
db = get_db()
print(f"Database initialized at: {db.db_path}")
```

### Database Backups

Databases are stored in the `State/` directory. To backup:

```bash
# Create a backup
cp -r State/ State_backup_$(date +%Y%m%d)/
```

### Resetting Databases

To reset all data and start fresh:

```bash
# Remove all database files
rm -f State/*.db

# Restart Thanos to recreate them
python thanos.py
```

---

## Optional Integrations

### ChromaDB Vector Store

ChromaDB provides semantic search capabilities for the memory system.

**Installation:**
```bash
pip install chromadb
```

**Verification:**
```python
python -c "from chromadb import Client; print('ChromaDB OK')"
```

The ChromaDB server is managed automatically. If you need to start it manually:
```bash
# Start ChromaDB server (optional, auto-started by Thanos)
python -c "from Tools.server_manager import ServerManager; ServerManager.ensure_chroma_running()"
```

### Neo4j Knowledge Graph

Neo4j provides graph-based memory for tracking relationships between decisions, commitments, and outcomes.

**Installation:**
```bash
pip install neo4j
```

**Setup:**
1. Create a free Neo4j AuraDB instance at [neo4j.com/cloud/aura](https://neo4j.com/cloud/aura/)
2. Copy connection details to your `.env` file
3. Verify connection:
   ```python
   python -c "from Tools.adapters.neo4j_adapter import Neo4jAdapter; print('Neo4j OK')"
   ```

---

## Telegram Bot Setup

The Telegram bot enables mobile brain dump capture with voice message transcription.

### Step 1: Create Your Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Follow the prompts:
   - Choose a name (e.g., "My Thanos Assistant")
   - Choose a username (must end in "bot", e.g., "my_thanos_bot")
4. BotFather will give you a token like: `1234567890:ABCdefGhIjKlmNoPqRsTuVwXyZ`
5. Copy this token to your `.env` file as `TELEGRAM_BOT_TOKEN`

### Step 2: Get Your User ID

1. Open Telegram and search for [@userinfobot](https://t.me/userinfobot)
2. Send any message to it
3. It will reply with your user ID (a number like `123456789`)
4. Add this to your `.env` file as `TELEGRAM_ALLOWED_USERS`

### Step 3: Configure Bot Settings (Optional)

Talk to @BotFather and use these commands to configure your bot:

```
/setdescription - Set bot description
/setabouttext - Set "About" text
/setuserpic - Set bot profile picture
/setcommands - Set command menu:
  start - Start the bot
  status - View pending brain dumps
  clear - Clear processed items
```

### Step 4: Test the Bot

```bash
# Test the bot without Telegram (captures text locally)
python Tools/telegram_bot.py --test-capture "Test brain dump entry"

# Check pending entries
python Tools/telegram_bot.py --status
```

### Step 5: Run the Bot

```bash
# Start the Telegram bot
python Tools/telegram_bot.py
```

The bot will:
- Accept text messages (captured as brain dumps)
- Accept voice messages (transcribed via Whisper, then captured)
- Classify entries using AI (thinking, venting, idea, task, etc.)
- Optionally sync work tasks to WorkOS database

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Introduction and help |
| `/status` | View pending brain dump entries |
| `/clear` | Clear processed entries |

### Security Notes

- Only users listed in `TELEGRAM_ALLOWED_USERS` can use the bot
- Voice messages are transcribed via OpenAI Whisper API
- Brain dumps are stored locally in `State/brain_dumps.json`

---

## Testing the Setup

### Test 1: Basic CLI

```bash
# Show help and available commands
python thanos.py --help

# List available agents
python thanos.py agents

# List available commands
python thanos.py commands
```

### Test 2: Natural Language

```bash
# Test natural language routing
python thanos.py "What should I focus on today?"

# Test with a specific agent
python thanos.py agent coach "I'm feeling overwhelmed"
```

### Test 3: Interactive Mode

```bash
# Start interactive mode
python thanos.py interactive

# Type commands like:
#   /pa:daily
#   /pa:tasks
#   exit
```

### Test 4: Command Shortcuts

```bash
# These all run the daily briefing
python thanos.py daily
python thanos.py morning
python thanos.py brief
```

### Test 5: Database Connection

```python
# Test database is working
python -c "
from Tools.state_store import get_db
db = get_db()
print(f'Database: {db.db_path}')
print(f'Schema version: {db.get_schema_version()}')
"
```

### Test 6: API Keys

```python
# Test Anthropic API
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('ANTHROPIC_API_KEY', '')
print(f'Anthropic API key configured: {bool(key and key.startswith(\"sk-ant\"))}')
"

# Test OpenAI API
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
key = os.getenv('OPENAI_API_KEY', '')
print(f'OpenAI API key configured: {bool(key and key.startswith(\"sk-\"))}')
"
```

### Test 7: Telegram Bot (if configured)

```bash
# Test capture without Telegram
python Tools/telegram_bot.py --test-capture "Test brain dump"

# Check the entry was saved
python Tools/telegram_bot.py --status
```

### Test 8: Calendar Integration (if configured)

```bash
# Sync today's calendar
python Tools/calendar_sync.py --today

# Check the state file was created
cat State/calendar_today.json | head -20
```

---

## Troubleshooting

### Issue: "No module named 'anthropic'"

**Solution:** Install the required dependencies:
```bash
pip install -r requirements.txt
```

### Issue: "ANTHROPIC_API_KEY not found"

**Solution:**
1. Ensure `.env` file exists in project root
2. Check the key is set correctly:
   ```bash
   grep ANTHROPIC_API_KEY .env
   ```
3. Ensure dotenv is installed:
   ```bash
   pip install python-dotenv
   ```

### Issue: "Database locked" errors

**Solution:** This can happen if multiple processes access the database:
```bash
# Kill any hanging Python processes
pkill -f "python.*thanos"

# Try again
python thanos.py
```

### Issue: ChromaDB connection errors

**Solution:** The ChromaDB server may not be running:
```bash
# Check if ChromaDB is running
ps aux | grep chroma

# Manually start it
python -c "from Tools.server_manager import ServerManager; ServerManager.ensure_chroma_running()"
```

### Issue: Telegram bot not responding

**Solution:**
1. Check the bot token is correct:
   ```bash
   grep TELEGRAM_BOT_TOKEN .env
   ```
2. Ensure your user ID is in the allowed list:
   ```bash
   grep TELEGRAM_ALLOWED_USERS .env
   ```
3. Check the bot is running:
   ```bash
   ps aux | grep telegram_bot
   ```

### Issue: Google Calendar "Invalid credentials"

**Solution:**
1. Re-run the OAuth setup:
   ```bash
   rm State/calendar_credentials.json
   python scripts/setup_google_calendar.py
   ```
2. Ensure redirect URI matches:
   ```bash
   grep GOOGLE_CALENDAR_REDIRECT_URI .env
   ```

### Issue: Voice transcription failing

**Solution:**
1. Ensure OpenAI API key is set:
   ```bash
   grep OPENAI_API_KEY .env
   ```
2. Check httpx is installed:
   ```bash
   pip install httpx
   ```

### Issue: Interactive mode crashes

**Solution:**
1. Check all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```
2. Try running with debug output:
   ```bash
   python -c "from Tools.thanos_interactive import ThanosInteractive; print('OK')"
   ```

### Getting Help

If you encounter issues not covered here:

1. Check the logs in `State/` directory
2. Run with verbose output:
   ```bash
   python thanos.py daily 2>&1 | tee debug.log
   ```
3. Check related documentation:
   - [Calendar Integration Guide](./guides/calendar-integration.md)
   - [Architecture Overview](./architecture.md)
   - [Troubleshooting Guide](./TROUBLESHOOTING.md)

---

## Quick Reference

### Common Commands

| Command | Description |
|---------|-------------|
| `python thanos.py` | Show help |
| `python thanos.py interactive` | Start interactive mode |
| `python thanos.py daily` | Run daily briefing |
| `python thanos.py "question"` | Ask a question |
| `python thanos.py agent coach "message"` | Chat with specific agent |
| `python thanos.py run pa:tasks` | Run specific command |

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `State/` | SQLite databases and state files |
| `Tools/` | Core Python modules |
| `commands/` | Command implementations |
| `config/` | Configuration files |
| `docs/` | Documentation |

### Key Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, config) |
| `config/api.json` | API routing and model configuration |
| `config/calendar_filters.json` | Calendar event filtering rules |
| `State/brain_dumps.json` | Telegram brain dump entries |

---

*Last updated: 2026-01-18*
