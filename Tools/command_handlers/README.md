# Command Handlers - Modular Command Architecture

This directory contains the modular command handling system for Thanos Interactive Mode. The architecture separates command execution logic into focused, testable handler modules.

## Architecture Overview

The command system is built on three core components:

1. **Command Handlers** (`Tools/command_handlers/`) - Execute specific commands
2. **Routing System** (`Tools/routing/`) - Route commands to appropriate handlers
3. **Command Router** (`Tools/command_router.py`) - Orchestrates the entire system

```
┌─────────────────────────────────────────────────────────┐
│                   CommandRouter                         │
│  - Parses slash commands                                │
│  - Delegates to handlers via CommandRegistry            │
│  - Manages agent/model state                            │
└───────────────┬─────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
┌───────▼──────┐  ┌──────▼──────────┐
│ CommandRegistry │  │ PersonaRouter │
│ - Lookup         │  │ - Agent detection│
│ - Aliasing       │  │ - Trigger patterns│
└───────┬──────┘  └─────────────────┘
        │
        │ Delegates to handlers
        │
┌───────▼──────────────────────────────────────────────┐
│                  Handler Modules                      │
│                                                       │
│  AgentHandler  SessionHandler  StateHandler          │
│  MemoryHandler AnalyticsHandler ModelHandler         │
│  CoreHandler                                          │
└───────────────────────────────────────────────────────┘
```

## Directory Structure

```
Tools/
├── command_handlers/           # Command execution modules
│   ├── __init__.py            # Exports all handlers
│   ├── base.py                # BaseHandler, Colors, CommandResult
│   ├── agent_handler.py       # /agent, /agents
│   ├── session_handler.py     # /clear, /save, /sessions, /resume, /branch, /branches, /switch
│   ├── state_handler.py       # /state, /commitments, /context, /usage
│   ├── memory_handler.py      # /remember, /recall, /memory
│   ├── history_search_handler.py # /history-search
│   ├── analytics_handler.py   # /patterns
│   ├── model_handler.py       # /model, /m
│   └── core_handler.py        # /help, /quit, /run
│
├── routing/                    # Command routing system
│   ├── __init__.py            # Exports routing modules
│   ├── command_registry.py    # Command registration and lookup
│   └── persona_router.py      # Agent detection and routing
│
└── command_router.py          # Main orchestrator (235 lines, down from 1002)
```

## Core Components

### BaseHandler

All handlers inherit from `BaseHandler`, which provides:

- **Dependency Injection**: Access to orchestrator, session manager, context manager, state reader, and Thanos directory
- **Shared Utilities**:
  - `_get_memos()`: Access MemOS integration
  - `_run_async()`: Execute async operations synchronously
  - `_get_current_agent()`: Get active agent name
- **Standard Types**: `Colors`, `CommandAction`, `CommandResult`

```python
from Tools.command_handlers.base import BaseHandler, CommandResult, Colors

class MyHandler(BaseHandler):
    def handle_command(self, args: str) -> CommandResult:
        agent = self._get_current_agent()
        return CommandResult(success=True, message=f"Agent: {agent}")
```

### CommandRegistry

Manages command registration and lookup:

- **Registration**: `register(name, handler, description, args)` or `register_batch(commands)`
- **Lookup**: `get(command)` returns `(handler, description, args)`
- **Aliasing**: Multiple commands can point to the same handler
- **Case-insensitive**: Commands are normalized to lowercase

### PersonaRouter

Handles intelligent agent detection and routing:

- **Pattern Matching**: Builds regex patterns from agent triggers
- **Scoring**: Ranks agent matches for automatic switching
- **Auto-switch Modes**: Supports always/smart/never modes

## Available Handlers

| Handler | Commands | Purpose |
|---------|----------|---------|
| **AgentHandler** | `/agent`, `/agents` | Switch agents, list available agents |
| **SessionHandler** | `/clear`, `/save`, `/sessions`, `/resume`, `/branch`, `/branches`, `/switch` | Session management with git-like branching |
| **StateHandler** | `/state`, `/commitments`, `/context`, `/usage` | View Thanos state and context information |
| **MemoryHandler** | `/remember`, `/recall`, `/memory` | MemOS integration for persistent memory |
| **HistorySearchHandler** | `/history-search` | Semantic search of conversation history using ChromaAdapter |
| **AnalyticsHandler** | `/patterns` | Analyze session patterns and usage |
| **ModelHandler** | `/model`, `/m` | Switch between Claude models (opus, sonnet, haiku) |
| **CoreHandler** | `/help`, `/quit`, `/run` | Core system commands |

## Adding New Commands

### Step 1: Choose or Create a Handler

**If the command fits an existing category**, add it to the appropriate handler.

**If it's a new category**, create a new handler:

```bash
# Create new handler file
touch Tools/command_handlers/my_handler.py
```

### Step 2: Implement the Handler Class

```python
#!/usr/bin/env python3
"""
MyHandler - Handles [category] commands in Thanos Interactive Mode.

Commands:
    /mycommand [args]  - Description of command
"""

from Tools.command_handlers.base import BaseHandler, CommandResult, Colors


class MyHandler(BaseHandler):
    """
    Handler for [category] commands.

    Provides functionality for:
    - Feature 1
    - Feature 2
    """

    def __init__(self, orchestrator, session_manager, context_manager,
                 state_reader, thanos_dir, **kwargs):
        """
        Initialize MyHandler with dependencies.

        Args:
            orchestrator: ThanosOrchestrator for system operations
            session_manager: SessionManager for session operations
            context_manager: ContextManager for context tracking
            state_reader: StateReader for state access
            thanos_dir: Path to Thanos root directory
            **kwargs: Additional arguments (e.g., current_agent_getter)
        """
        super().__init__(orchestrator, session_manager, context_manager,
                        state_reader, thanos_dir, **kwargs)

    def handle_mycommand(self, args: str) -> CommandResult:
        """
        Handle /mycommand execution.

        Args:
            args: Command arguments as string

        Returns:
            CommandResult with execution status and message
        """
        try:
            # Parse arguments
            if not args:
                return CommandResult(
                    success=False,
                    message=f"{Colors.RED}Usage: /mycommand <arg>{Colors.RESET}"
                )

            # Access shared utilities
            agent = self._get_current_agent()

            # Implement command logic
            output = f"{Colors.GREEN}Command executed by {agent}!{Colors.RESET}"

            return CommandResult(success=True, message=output)

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"{Colors.RED}Error: {e}{Colors.RESET}"
            )
```

### Step 3: Export the Handler

Update `Tools/command_handlers/__init__.py`:

```python
from .my_handler import MyHandler

__all__ = [
    # ... existing exports ...
    "MyHandler",
]
```

### Step 4: Register Commands in CommandRouter

Update `Tools/command_router.py`:

```python
# In __init__, instantiate your handler
self.my_handler = MyHandler(
    orchestrator, session_manager, context_manager, state_reader, thanos_dir,
    current_agent_getter=current_agent_getter
)

# In _register_commands(), register your commands
self.registry.register(
    "mycommand",
    self.my_handler.handle_mycommand,
    "Description of command",
    ["arg1", "arg2"]  # Optional argument names for help text
)

# Add aliases if needed
self.registry.register(
    "mc",  # Shortcut
    self.my_handler.handle_mycommand,
    "Description (alias)",
    ["arg1", "arg2"]
)
```

### Step 5: Add Tests

Create tests in `tests/unit/test_command_handlers.py`:

```python
class TestMyHandler:
    """Tests for MyHandler"""

    @pytest.fixture
    def handler(self, mock_orchestrator):
        """Create MyHandler instance for testing"""
        return MyHandler(
            mock_orchestrator,
            MagicMock(),  # session_manager
            MagicMock(),  # context_manager
            MagicMock(),  # state_reader
            Path("/fake/thanos")
        )

    def test_handle_mycommand_success(self, handler, capsys):
        """Test successful command execution"""
        result = handler.handle_mycommand("test_arg")

        assert result.success is True
        assert "executed" in result.message.lower()

    def test_handle_mycommand_no_args(self, handler):
        """Test command with missing arguments"""
        result = handler.handle_mycommand("")

        assert result.success is False
        assert "usage" in result.message.lower()

    def test_handle_mycommand_error(self, handler, monkeypatch):
        """Test command error handling"""
        # Mock to raise an exception
        monkeypatch.setattr(handler, "_get_current_agent",
                           lambda: (_ for _ in ()).throw(Exception("test error")))

        result = handler.handle_mycommand("test")

        assert result.success is False
        assert "error" in result.message.lower()
```

Run tests:

```bash
pytest tests/unit/test_command_handlers.py::TestMyHandler -v
```

### Step 6: Update Documentation

Add module docstring to your handler:

```python
"""
MyHandler - Handles [category] commands in Thanos Interactive Mode.

This module provides functionality for [detailed description].

Commands:
    /mycommand [args]  - Full command description

Classes:
    MyHandler: Handler for [category] commands

Dependencies:
    - BaseHandler: Provides shared utilities and dependency injection
    - CommandResult: Standard result format for command execution
    - Colors: ANSI color codes for formatted output

Architecture:
    [Explain how this handler fits into the system]

Example:
    handler = MyHandler(orchestrator, session_mgr, context_mgr,
                       state_reader, thanos_dir)

    result = handler.handle_mycommand("arg")

See Also:
    - Tools.command_handlers.base: Base handler infrastructure
    - Tools.routing.command_registry: Command registration system
"""
```

## Best Practices

### 1. Single Responsibility

Each handler should focus on a specific category of commands:

- ✅ **Good**: AgentHandler handles all agent operations
- ❌ **Bad**: Mixing agent, session, and state commands in one handler

### 2. Dependency Injection

Use `BaseHandler.__init__` for all dependencies:

```python
def __init__(self, orchestrator, session_manager, context_manager,
             state_reader, thanos_dir, **kwargs):
    super().__init__(orchestrator, session_manager, context_manager,
                    state_reader, thanos_dir, **kwargs)
    # Don't create dependencies here - use injected ones
```

### 3. Consistent Return Types

Always return `CommandResult`:

```python
# Success
return CommandResult(success=True, message="Done!")

# Failure
return CommandResult(success=False, message="Error: ...")

# With action
return CommandResult(success=True, message="Goodbye!",
                    action=CommandAction.QUIT)
```

### 4. Graceful Error Handling

Catch exceptions and return user-friendly errors:

```python
try:
    # Command logic
    result = some_operation()
    return CommandResult(success=True, message=result)
except FileNotFoundError:
    return CommandResult(success=False,
                        message=f"{Colors.RED}File not found{Colors.RESET}")
except Exception as e:
    return CommandResult(success=False,
                        message=f"{Colors.RED}Error: {e}{Colors.RESET}")
```

### 5. Graceful Degradation

Use feature flags for optional dependencies:

```python
from Tools.command_handlers.base import MEMOS_AVAILABLE

def handle_command(self, args: str) -> CommandResult:
    if not MEMOS_AVAILABLE:
        return CommandResult(
            success=False,
            message=f"{Colors.YELLOW}MemOS not available{Colors.RESET}"
        )
    # Use MemOS...
```

### 6. Formatted Output

Use `Colors` for readable terminal output:

```python
# Success (green)
message = f"{Colors.GREEN}✓ Operation successful{Colors.RESET}"

# Warning (yellow)
message = f"{Colors.YELLOW}⚠ Warning message{Colors.RESET}"

# Error (red)
message = f"{Colors.RED}✗ Error message{Colors.RESET}"

# Info (purple/cyan)
message = f"{Colors.PURPLE}Agent: ops{Colors.RESET}"
```

### 7. Keep Handlers Focused

Target: **< 500 lines per handler**

If a handler grows too large:
- Extract common utilities to `BaseHandler`
- Split into multiple handlers by sub-category
- Create helper functions within the handler

### 8. Document Everything

Include comprehensive docstrings:

- **Module**: Purpose, commands, dependencies, examples
- **Class**: What it handles, responsibilities
- **Methods**: Parameters, return values, behavior

## Testing Guidelines

### Unit Tests

Test each handler method independently:

```python
# Test success cases
def test_command_success(handler):
    result = handler.handle_command("valid_args")
    assert result.success is True

# Test error cases
def test_command_invalid_args(handler):
    result = handler.handle_command("")
    assert result.success is False

# Test edge cases
def test_command_special_characters(handler):
    result = handler.handle_command("arg with spaces")
    assert result.success is True
```

### Integration Tests

Test command registration and routing:

```python
def test_command_registered(command_router):
    """Test command is registered correctly"""
    handler_info = command_router.registry.get("mycommand")
    assert handler_info is not None

def test_command_execution(command_router):
    """Test end-to-end command execution"""
    result = command_router.route_command("/mycommand test")
    assert result.success is True
```

### Coverage Target

Aim for **>80% coverage** on handlers:

```bash
pytest tests/unit/test_command_handlers.py --cov=Tools/command_handlers --cov-report=term-missing
```

## Common Patterns

### Accessing MemOS

```python
from Tools.command_handlers.base import MEMOS_AVAILABLE

memos = self._get_memos()
if memos:
    # Use MemOS
    result = memos.search(query)
else:
    # Fallback behavior
    return CommandResult(success=False,
                        message="MemOS unavailable")
```

### Running Async Code

```python
async def async_operation():
    # Async code here
    return result

# In handler method
result = self._run_async(async_operation())
```

### Accessing Current Agent

```python
agent = self._get_current_agent()
print(f"Current agent: {agent}")
```

### Parsing Arguments

```python
def handle_command(self, args: str) -> CommandResult:
    # Split arguments
    parts = args.strip().split(maxsplit=1)

    if not parts:
        return CommandResult(success=False, message="Missing arguments")

    action = parts[0]
    value = parts[1] if len(parts) > 1 else ""

    # Use parsed values
    if action == "show":
        return self._show_info()
    elif action == "set":
        return self._set_value(value)
```

## Migration Guide

If you're updating existing code from the old monolithic `command_router.py`:

### Before (Old)

```python
# In command_router.py (1000+ lines)
def _cmd_mycommand(self, args: str) -> CommandResult:
    # Command logic here
    pass

def _register_commands(self):
    self.commands["mycommand"] = (
        self._cmd_mycommand,
        "Description",
        ["args"]
    )
```

### After (New)

```python
# In Tools/command_handlers/my_handler.py
class MyHandler(BaseHandler):
    def handle_mycommand(self, args: str) -> CommandResult:
        # Same command logic
        pass

# In Tools/command_router.py
def __init__(self, ...):
    self.my_handler = MyHandler(...)

def _register_commands(self):
    self.registry.register(
        "mycommand",
        self.my_handler.handle_mycommand,
        "Description",
        ["args"]
    )
```

## Performance Considerations

### Handler Instantiation

Handlers are instantiated once during `CommandRouter.__init__`. This means:

- **Fast command execution** - no object creation overhead
- **Shared state** - handlers can maintain state between commands
- **Memory efficient** - single instance per handler type

### Command Lookup

`CommandRegistry` uses a dictionary for O(1) command lookup:

```python
# Fast lookup
handler_info = registry.get("command")  # O(1)
```

### Lazy Loading

Optional dependencies use lazy imports for faster startup:

```python
try:
    from Tools.memos import MemOS
    MEMOS_AVAILABLE = True
except ImportError:
    MEMOS_AVAILABLE = False
```

## Troubleshooting

### Command Not Found

1. Check registration in `command_router.py`:
   ```python
   self.registry.register("mycommand", handler.handle_mycommand, ...)
   ```

2. Verify export in `__init__.py`:
   ```python
   from .my_handler import MyHandler
   ```

3. Check handler instantiation:
   ```python
   self.my_handler = MyHandler(...)
   ```

### Import Errors

1. Ensure circular imports are avoided
2. Use relative imports within `command_handlers/`:
   ```python
   from .base import BaseHandler  # Good
   from Tools.command_handlers.base import BaseHandler  # Also fine
   ```

### Tests Failing

1. Verify mock objects match handler dependencies
2. Check test fixtures are properly configured
3. Ensure test imports match module structure

## Command Usage Examples

### /history-search - Semantic Search of Conversation History

The `/history-search` command enables semantic search across all indexed conversation history using ChromaAdapter's vector search capabilities. Unlike keyword search, it finds messages that are semantically similar to your query, enabling natural language "what did we discuss about X?" queries.

#### Basic Usage

```bash
# Simple search
/history-search authentication

# Multi-word query
/history-search API implementation patterns

# Context-aware search
/history-search what did we decide about testing strategy
```

#### Filter Syntax

Search results can be filtered using these optional filters:

| Filter | Syntax | Description | Example |
|--------|--------|-------------|---------|
| **Agent** | `agent:<name>` | Filter by agent name | `agent:architect` |
| **Date** | `date:<YYYY-MM-DD>` | Filter by specific date | `date:2026-01-11` |
| **Session** | `session:<id>` | Filter by session ID (prefix matching) | `session:abc123` |
| **After** | `after:<YYYY-MM-DD>` | Messages on or after date | `after:2026-01-01` |
| **Before** | `before:<YYYY-MM-DD>` | Messages on or before date | `before:2026-01-31` |

#### Advanced Examples

```bash
# Search with agent filter
/history-search database schema agent:architect

# Search with date filter
/history-search API decisions date:2026-01-11

# Search with session filter
/history-search error handling session:abc123

# Search with date range
/history-search API work after:2026-01-01 before:2026-01-31

# Combine multiple filters
/history-search authentication agent:ops after:2026-01-10
```

#### Result Format

Results include:

- **Session Context**: Date, time, agent name, session ID
- **Similarity Score**: Percentage showing relevance (higher = more relevant)
- **Role**: User or assistant message
- **Content Preview**: Excerpt with query terms highlighted in bold
- **Helpful Tips**: Usage guidance and filter syntax

#### How It Works

1. **Message Indexing**: SessionManager automatically indexes messages to ChromaAdapter's 'conversations' collection with metadata (session_id, timestamp, role, agent, date)
2. **Vector Search**: ChromaAdapter uses OpenAI embeddings to create vector representations of messages
3. **Semantic Matching**: Query is embedded and compared to stored messages using cosine similarity
4. **Filtered Results**: Optional filters are applied using ChromaDB's where clause syntax
5. **Ranked Output**: Results are ranked by similarity score and displayed with context

#### Prerequisites

- **ChromaAdapter**: Must be configured with OpenAI embeddings
- **Indexed Sessions**: Messages must be indexed (automatic for new sessions, use `scripts/index_sessions.py` for existing sessions)

#### Related Commands

- `/recall <query>` - Search MemOS hybrid memory (Neo4j + ChromaDB) for stored knowledge
- `/memory` - Show memory system info including ChromaDB status
- `/sessions` - List all saved sessions
- `/resume <id>` - Resume a specific session

## Additional Resources

- **Main Router**: `Tools/command_router.py` - Orchestration logic
- **Routing System**: `Tools/routing/` - PersonaRouter and CommandRegistry
- **Base Infrastructure**: `Tools/command_handlers/base.py` - Shared utilities
- **Tests**: `tests/unit/test_command_handlers.py` - Handler unit tests
- **Integration Tests**: `tests/unit/test_routing.py` - Routing tests

## Architecture Benefits

This modular architecture provides:

1. **Maintainability**: Small, focused files (< 500 lines each)
2. **Testability**: Each handler tested independently
3. **Extensibility**: Add new commands without touching existing code
4. **Readability**: Clear separation of concerns
5. **Reusability**: Shared utilities in BaseHandler
6. **Scalability**: Easy to add new handlers as system grows

---

**Questions?** Check existing handlers for examples or see the test suite for usage patterns.
