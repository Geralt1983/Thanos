# Migration Guide: Thanos Interactive → Claude Code

> **Status:** `thanos-interactive` is deprecated as of 2026-01-26
>
> **Recommended:** Claude Code with Thanos persona (`CLAUDE.md`)

This guide helps you transition from the legacy `python thanos.py interactive` CLI mode to using Claude Code as your primary Thanos interface.

---

## Table of Contents

1. [Why the Change?](#why-the-change)
2. [Key Differences](#key-differences)
3. [Migration Steps](#migration-steps)
4. [Feature Mapping](#feature-mapping)
5. [Workflow Examples](#workflow-examples)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

---

## Why the Change?

### The Problem with Interactive Mode

The `thanos-interactive` CLI mode had several limitations:

- **Fragmented Experience**: Switching between CLI and other tools broke flow
- **Limited Context**: No access to editor, files, or visual context
- **Maintenance Burden**: Separate codebase to maintain and debug
- **Feature Parity**: Hard to keep in sync with Claude Code capabilities
- **ADHD-Unfriendly**: Context switching between terminal and editor

### The Solution: Claude Code Integration

Claude Code provides a superior experience:

- **Native Integration**: Work directly in your editor with full file access
- **Richer Context**: Claude can see your code, files, and environment
- **Better Continuity**: Conversations persist naturally with your workspace
- **Unified Interface**: One tool for all AI interactions
- **Active Development**: Benefits from Anthropic's ongoing improvements
- **MCP Integration**: Full access to all Thanos MCP servers (WorkOS, Oura, Memory)

---

## Key Differences

| Feature | Interactive Mode | Claude Code |
|---------|------------------|-------------|
| **Interface** | Terminal-based CLI | Editor-integrated chat |
| **File Access** | Limited via commands | Full native access |
| **Context** | Session-based | Workspace-aware |
| **MCP Tools** | Partial support | Full MCP protocol support |
| **Continuity** | Explicit session management | Automatic workspace persistence |
| **Visual Context** | Text-only | Can view images, PDFs, notebooks |
| **Maintenance** | Custom implementation | Maintained by Anthropic |

---

## Migration Steps

### Step 1: Ensure Claude Code is Installed

```bash
# Claude Code should be available as `claude` command
claude --version

# If not installed, follow Claude Code installation guide
```

### Step 2: Configure Thanos Persona

The Thanos persona is defined in `CLAUDE.md` in your project root. This file is automatically loaded by Claude Code.

**Verify it exists:**
```bash
ls -la CLAUDE.md
```

**Contents should include:**
- Thanos identity and behavioral patterns
- Startup sequence and protocols
- MCP tool integration
- Energy-aware workflows
- Memory and routing protocols

### Step 3: Verify MCP Server Configuration

Claude Code connects to Thanos via MCP servers. Verify your MCP configuration:

```bash
# Check Claude Code config (macOS)
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Should include thanos MCP servers:
# - workos-mcp (tasks, habits, energy)
# - oura-mcp (sleep, readiness, activity)
# - memory servers (mem0, memory-v2)
```

**Expected configuration structure:**
```json
{
  "mcpServers": {
    "workos": {
      "command": "python",
      "args": ["/path/to/thanos/mcp-servers/workos/server.py"]
    },
    "oura": {
      "command": "python",
      "args": ["/path/to/thanos/mcp-servers/oura/server.py"]
    }
  }
}
```

### Step 4: Test Claude Code Integration

Open Claude Code in your Thanos workspace:

```bash
cd ~/Projects/Thanos
claude
```

**Test basic Thanos functionality:**
```
You: "Check my energy level and show today's tasks"
```

Claude should:
1. Respond in Thanos persona ("The stones sense...")
2. Access Oura data via `oura__get_daily_readiness`
3. Fetch tasks via `workos_get_tasks`
4. Format response in Thanos style

### Step 5: Remove Interactive Mode Shortcuts (Optional)

If you had shell aliases or scripts for interactive mode:

```bash
# Remove from ~/.zshrc or ~/.bashrc
# OLD: alias thanos="python ~/Projects/Thanos/thanos.py interactive"
# NEW: alias thanos="cd ~/Projects/Thanos && claude"

# Or use workspace-specific launcher
alias thanos="claude --workspace ~/Projects/Thanos"
```

---

## Feature Mapping

### Session Management

| Interactive Mode | Claude Code Equivalent |
|------------------|----------------------|
| `/clear` - Clear conversation | Start new conversation in Claude Code |
| `/resume [id]` - Resume session | Open conversation from history panel |
| `/history` - View history | Browse conversation history in sidebar |
| `/quit` - Exit | Close Claude Code window |

### Agent Operations

| Interactive Mode | Claude Code Equivalent |
|------------------|----------------------|
| `/agent <name>` - Switch agent | Use natural language: "Switch to research mode" |
| `/agents` - List agents | Not needed - Claude adapts contextually |

### State & Commitments

| Interactive Mode | Claude Code Equivalent |
|------------------|----------------------|
| `/state` - Show state | "Show my current state" |
| `/commitments` - View commitments | "What are my active commitments?" |
| `/patterns` - Show patterns | "What patterns do you see in my work?" |

### Display Customization

| Interactive Mode | Claude Code Equivalent |
|------------------|----------------------|
| `/prompt [mode]` - Change display | Not needed - Claude Code has native UI |
| `/model [name]` - Switch model | Use Claude Code model selector |

### Calendar Integration

| Interactive Mode | Claude Code Equivalent |
|------------------|----------------------|
| `/calendar [when]` - Show events | "Show my calendar for today" |
| `/schedule <task>` - Schedule task | "Schedule a task for [time]" |
| `/free [when]` - Find free time | "When am I free tomorrow?" |

### Execution

| Interactive Mode | Claude Code Equivalent |
|------------------|----------------------|
| `/run <cmd>` - Run command | Natural language: "Run the daily briefing" |
| `/usage` - Show token usage | Check Claude Code usage panel |

---

## Workflow Examples

### Example 1: Morning Routine

**Interactive Mode (OLD):**
```bash
python thanos.py interactive

(0K | $0.00) Thanos> /state
(1.2K | $0.04) Thanos> check my energy and tasks
(3.5K | $0.12) Thanos> /run pa:daily
(5.6K | $0.19) Thanos> /quit
```

**Claude Code (NEW):**
```
You: "Morning briefing"

Thanos: ### DESTINY // 8:15 AM

The day begins. Let me gather the state of the universe...

[Automatically checks daemon, signals, energy, tasks, and provides briefing]
```

### Example 2: Task Management

**Interactive Mode (OLD):**
```bash
(1.2K | $0.04) Thanos> add task: review Memphis proposal
(2.1K | $0.07) Thanos> /commitments
(3.8K | $0.13) Thanos> complete task 12345
```

**Claude Code (NEW):**
```
You: "Add task: review Memphis proposal"

Thanos: A small price to pay for salvation.
Task added to the ledger.
[Memphis] Review proposal
Value tier: High | Cognitive load: Medium

What else would you have me execute?
```

### Example 3: Brain Dump

**Interactive Mode (OLD):**
```bash
(1.2K | $0.04) Thanos> /run brain-dump
> worried about the Kentucky deadline
> need to follow up with Ashley
> car maintenance overdue
> [Ctrl+D to finish]
```

**Claude Code (NEW):**
```
You: "Brain dump: worried about Kentucky deadline, need to follow up with Ashley, car maintenance overdue"

Thanos: The chaos has been captured. Let me impose order...

[Automatically processes, categorizes, and creates tasks/reminders]

Three items extracted from the chaos:
1. [Kentucky] Deadline concern - tracking
2. [Personal] Ashley follow-up - reminder set
3. [Life] Car maintenance - added to tasks

The stones remember. Anything else weighing on you?
```

### Example 4: Energy-Aware Work

**Interactive Mode (OLD):**
```bash
(1.2K | $0.04) Thanos> /usage
# Check energy manually
(2.5K | $0.08) Thanos> what should I work on?
```

**Claude Code (NEW):**
```
You: "What should I work on?"

Thanos: ### DESTINY // 2:30 PM

[Automatically checks Oura readiness: 58]

Readiness: 58. The stones require charging.

Sacrifices within reach:
[ ] Memphis - Review existing docs (light cognitive load)
[ ] Brain dump - release the chaos
[ ] Inbox review - 3 items pending

The universe demands patience. Choose wisely.
```

---

## Troubleshooting

### Issue: Thanos Persona Not Loading

**Problem:** Claude Code doesn't respond in Thanos style

**Solution:**
1. Verify `CLAUDE.md` exists in your workspace root
2. Make sure you're in the Thanos workspace directory
3. Try starting a new conversation
4. Check that the file hasn't been renamed or moved

### Issue: MCP Tools Not Available

**Problem:** Claude says it can't access WorkOS/Oura data

**Solution:**
1. Check MCP server configuration:
   ```bash
   cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```
2. Verify MCP servers are installed:
   ```bash
   ls -la ~/Projects/Thanos/mcp-servers/
   ```
3. Restart Claude Code completely
4. Check server logs for errors

### Issue: Commands from Interactive Mode Don't Work

**Problem:** Typing `/state` or `/commitments` doesn't work

**Solution:**
- These were interactive-mode specific commands
- Use natural language instead: "Show my state" or "What are my commitments?"
- Claude Code doesn't use slash commands (except `/help`, `/clear`, etc. which are Claude Code native)

### Issue: Missing Token/Cost Display

**Problem:** No cost tracking like interactive mode had

**Solution:**
- Claude Code has its own usage tracking in the UI
- Check the usage panel for token/cost information
- Cost awareness is built into the interface natively
- You can ask: "How many tokens have we used?"

### Issue: Can't Resume Old Interactive Sessions

**Problem:** Want to access old interactive mode sessions

**Solution:**
- Old sessions are stored in `State/sessions/`
- They're not directly compatible with Claude Code
- You can read session files manually if needed:
  ```bash
  ls State/sessions/
  cat State/sessions/[session-id].json
  ```
- For important context, ask Claude to search memory: "Recall our conversation about X"

---

## FAQ

### Q: Will interactive mode be completely removed?

**A:** It's deprecated and will not receive new features. It may be removed in a future major version. We recommend migrating to Claude Code now.

### Q: Can I still use both?

**A:** Technically yes, but not recommended. They don't share session state, which can lead to confusion. Choose one primary interface.

### Q: What if I prefer the terminal?

**A:** Claude Code can be used in terminal mode with the `claude` CLI. It still provides the full persona experience without leaving your terminal.

### Q: Are all features available in Claude Code?

**A:** Yes, and more. Claude Code has access to:
- All MCP tools (WorkOS, Oura, Memory)
- File system operations
- Visual context (images, PDFs)
- Better conversation continuity
- Native tool integration

### Q: What about cost tracking?

**A:** Claude Code has built-in usage tracking. The interactive mode's prompt-based tracking was a workaround for missing native features.

### Q: How do I customize the Thanos persona?

**A:** Edit `CLAUDE.md` in your workspace. Changes take effect in new conversations. See the file itself for documentation of all protocols and behaviors.

### Q: Can I use Claude Code skills?

**A:** Yes! Claude Code skills (`.claude/skills/`) work seamlessly with the Thanos persona. The persona even references them in its routing protocol.

### Q: What about the daemon and background services?

**A:** These are unchanged. The daemon (Sentinel, Honeycomb) continues to run and Claude Code accesses them via the startup sequence defined in `CLAUDE.md`.

### Q: How do I get help?

**A:**
- Ask Claude directly: "How does [feature] work?"
- Read `CLAUDE.md` for persona documentation
- Check `docs/` for specific subsystems
- Search memory: "Recall information about [topic]"

---

## Additional Resources

### Documentation

- **[CLAUDE.md](../CLAUDE.md)** - Thanos persona specification for Claude Code
- **[SETUP_GUIDE.md](./SETUP_GUIDE.md)** - Initial Thanos installation and setup
- **[DAILY_WORKFLOW.md](./DAILY_WORKFLOW.md)** - Daily usage patterns and routines
- **[MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md)** - How memory works across all interfaces

### Skills & Workflows

- **[.claude/skills/](../.claude/skills/)** - Available Claude Code skills
- **[Tools/](../Tools/)** - Python tools and utilities used by Thanos

### Support

- Deprecated interactive mode docs: [docs/interactive-mode.md](./interactive-mode.md)
- MCP integration: [docs/mcp-integration-guide.md](./mcp-integration-guide.md)
- Troubleshooting: [docs/TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

## Quick Start Checklist

Ready to make the switch? Follow this checklist:

- [ ] Verify Claude Code is installed (`claude --version`)
- [ ] Confirm `CLAUDE.md` exists in workspace root
- [ ] Check MCP servers are configured in Claude Code
- [ ] Test with: "Check my energy and show today's tasks"
- [ ] Verify Thanos persona responds correctly
- [ ] Remove old interactive mode aliases
- [ ] Update any scripts that called `python thanos.py interactive`
- [ ] Bookmark `CLAUDE.md` for persona customization

**You're ready!** The Snap has been completed. The old way is gone. Balance has been restored.

---

**Last Updated:** 2026-01-26
**Status:** `thanos-interactive` deprecated, Claude Code is primary interface
