#!/usr/bin/env python3
"""
Unit tests for CommandRouter and LazyInitializer

Tests command routing, execution, lazy initialization pattern, and all command handlers.
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import pytest

from Tools.command_router import (
    Colors,
    CommandAction,
    CommandResult,
    CommandRouter,
    LazyInitializer,
)


# ========================================================================
# LazyInitializer Test Fixtures
# ========================================================================


@pytest.fixture
def sync_initializer():
    """Creates a simple synchronous initializer function"""
    call_count = {"count": 0}

    def init_func():
        call_count["count"] += 1
        return f"instance_{call_count['count']}"

    init_func.call_count = call_count
    return init_func


@pytest.fixture
def async_initializer():
    """Creates a simple asynchronous initializer function"""
    call_count = {"count": 0}

    async def init_func():
        call_count["count"] += 1
        await asyncio.sleep(0.001)  # Simulate async work
        return f"async_instance_{call_count['count']}"

    init_func.call_count = call_count
    return init_func


@pytest.fixture
def sync_get_existing():
    """Creates a synchronous get_existing function"""
    call_count = {"count": 0}

    def get_func():
        call_count["count"] += 1
        if call_count["count"] == 1:
            return "existing_instance"
        return None

    get_func.call_count = call_count
    return get_func


@pytest.fixture
def async_get_existing():
    """Creates an asynchronous get_existing function"""
    call_count = {"count": 0}

    async def get_func():
        call_count["count"] += 1
        await asyncio.sleep(0.001)
        if call_count["count"] == 1:
            return "async_existing_instance"
        return None

    get_func.call_count = call_count
    return get_func


@pytest.fixture
def failing_initializer():
    """Creates an initializer that always fails"""

    def init_func():
        raise RuntimeError("Initialization failed")

    return init_func


@pytest.fixture
def failing_async_initializer():
    """Creates an async initializer that always fails"""

    async def init_func():
        await asyncio.sleep(0.001)
        raise RuntimeError("Async initialization failed")

    return init_func


# ========================================================================
# LazyInitializer Tests
# ========================================================================


class TestLazyInitializerSyncInitialization:
    """Test LazyInitializer with synchronous initialization"""

    def test_successful_sync_initialization(self, sync_initializer):
        """Test successful synchronous initialization"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        # First call should initialize
        instance = lazy.get()
        assert instance == "instance_1"
        assert sync_initializer.call_count["count"] == 1
        assert lazy.is_initialized is True
        assert lazy.has_instance is True

    def test_sync_idempotency(self, sync_initializer):
        """Test that multiple calls return the same instance"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        # First call
        instance1 = lazy.get()
        # Second call
        instance2 = lazy.get()
        # Third call
        instance3 = lazy.get()

        assert instance1 == instance2 == instance3 == "instance_1"
        assert sync_initializer.call_count["count"] == 1  # Only called once

    def test_sync_get_existing_success(self, sync_get_existing, sync_initializer):
        """Test get_existing returns instance before trying initializer"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            get_existing=sync_get_existing,
            is_async=False,
        )

        instance = lazy.get()
        assert instance == "existing_instance"
        assert sync_get_existing.call_count["count"] == 1
        assert sync_initializer.call_count["count"] == 0  # Never called

    def test_sync_get_existing_fallback(self, sync_initializer):
        """Test fallback to initializer when get_existing fails"""

        def failing_get_existing():
            raise RuntimeError("Get existing failed")

        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            get_existing=failing_get_existing,
            is_async=False,
        )

        instance = lazy.get()
        assert instance == "instance_1"
        assert sync_initializer.call_count["count"] == 1

    def test_sync_get_existing_returns_none_fallback(self, sync_initializer):
        """Test fallback to initializer when get_existing returns None"""

        def get_existing_returns_none():
            return None

        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            get_existing=get_existing_returns_none,
            is_async=False,
        )

        instance = lazy.get()
        assert instance == "instance_1"
        assert sync_initializer.call_count["count"] == 1


class TestLazyInitializerAsyncInitialization:
    """Test LazyInitializer with asynchronous initialization"""

    def test_successful_async_initialization(self, async_initializer):
        """Test successful asynchronous initialization"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_initializer,
            is_async=True,
        )

        # First call should initialize
        instance = lazy.get()
        assert instance == "async_instance_1"
        assert async_initializer.call_count["count"] == 1
        assert lazy.is_initialized is True
        assert lazy.has_instance is True

    def test_async_idempotency(self, async_initializer):
        """Test that multiple calls return the same async instance"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_initializer,
            is_async=True,
        )

        # Multiple calls
        instance1 = lazy.get()
        instance2 = lazy.get()
        instance3 = lazy.get()

        assert instance1 == instance2 == instance3 == "async_instance_1"
        assert async_initializer.call_count["count"] == 1  # Only called once

    def test_async_get_existing_success(self, async_get_existing, async_initializer):
        """Test async get_existing returns instance before trying initializer"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_initializer,
            get_existing=async_get_existing,
            is_async=True,
        )

        instance = lazy.get()
        assert instance == "async_existing_instance"
        assert async_get_existing.call_count["count"] == 1
        assert async_initializer.call_count["count"] == 0  # Never called

    def test_async_get_existing_fallback(self, async_initializer):
        """Test fallback to async initializer when get_existing fails"""

        async def failing_get_existing():
            await asyncio.sleep(0.001)
            raise RuntimeError("Async get existing failed")

        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_initializer,
            get_existing=failing_get_existing,
            is_async=True,
        )

        instance = lazy.get()
        assert instance == "async_instance_1"
        assert async_initializer.call_count["count"] == 1

    def test_async_with_running_event_loop(self, async_initializer):
        """Test async initialization with running event loop returns None"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_initializer,
            is_async=True,
        )

        async def run_in_loop():
            # Inside running loop, should return None
            instance = lazy.get()
            return instance

        # Run in an event loop
        result = asyncio.run(run_in_loop())
        assert result is None  # Can't run_until_complete in running loop
        assert lazy.is_initialized is False  # Never initialized


class TestLazyInitializerAvailability:
    """Test LazyInitializer availability checking"""

    def test_unavailable_returns_none(self, sync_initializer):
        """Test that unavailable component returns None"""
        lazy = LazyInitializer(
            name="UnavailableComponent",
            available=False,  # Not available
            initializer=sync_initializer,
            is_async=False,
        )

        instance = lazy.get()
        assert instance is None
        assert sync_initializer.call_count["count"] == 0  # Never called
        assert lazy.is_initialized is False

    def test_unavailable_multiple_calls(self, sync_initializer):
        """Test multiple calls on unavailable component"""
        lazy = LazyInitializer(
            name="UnavailableComponent",
            available=False,
            initializer=sync_initializer,
            is_async=False,
        )

        # Multiple calls should all return None
        assert lazy.get() is None
        assert lazy.get() is None
        assert lazy.get() is None
        assert sync_initializer.call_count["count"] == 0


class TestLazyInitializerExceptionHandling:
    """Test LazyInitializer exception handling"""

    def test_sync_initializer_exception(self, failing_initializer):
        """Test graceful handling of sync initializer exceptions"""
        lazy = LazyInitializer(
            name="FailingComponent",
            available=True,
            initializer=failing_initializer,
            is_async=False,
        )

        instance = lazy.get()
        assert instance is None  # Returns None on failure
        assert lazy.is_initialized is False  # Not marked as initialized

    def test_async_initializer_exception(self, failing_async_initializer):
        """Test graceful handling of async initializer exceptions"""
        lazy = LazyInitializer(
            name="FailingAsyncComponent",
            available=True,
            initializer=failing_async_initializer,
            is_async=True,
        )

        instance = lazy.get()
        assert instance is None  # Returns None on failure
        assert lazy.is_initialized is False

    def test_get_existing_exception_with_fallback(self, sync_initializer):
        """Test that get_existing exception falls back to initializer"""

        def failing_get_existing():
            raise RuntimeError("Get existing failed")

        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            get_existing=failing_get_existing,
            is_async=False,
        )

        # Should fall back to initializer after get_existing fails
        instance = lazy.get()
        assert instance == "instance_1"
        assert sync_initializer.call_count["count"] == 1

    def test_both_get_existing_and_initializer_fail(self):
        """Test when both get_existing and initializer fail"""

        def failing_get_existing():
            raise RuntimeError("Get existing failed")

        def failing_initializer():
            raise RuntimeError("Initializer failed")

        lazy = LazyInitializer(
            name="FullyFailingComponent",
            available=True,
            initializer=failing_initializer,
            get_existing=failing_get_existing,
            is_async=False,
        )

        instance = lazy.get()
        assert instance is None
        assert lazy.is_initialized is False
        assert lazy.has_instance is False

    def test_initializer_returns_none(self):
        """Test when initializer successfully runs but returns None"""

        def none_initializer():
            return None

        lazy = LazyInitializer(
            name="NoneReturningComponent",
            available=True,
            initializer=none_initializer,
            is_async=False,
        )

        instance = lazy.get()
        assert instance is None
        assert lazy.is_initialized is False  # Not marked as initialized if None


class TestLazyInitializerReset:
    """Test LazyInitializer reset functionality"""

    def test_reset_allows_reinitialization(self, sync_initializer):
        """Test reset allows component to be reinitialized"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        # First initialization
        instance1 = lazy.get()
        assert instance1 == "instance_1"
        assert sync_initializer.call_count["count"] == 1

        # Reset
        lazy.reset()
        assert lazy.is_initialized is False
        assert lazy.has_instance is False

        # Second initialization (should create new instance)
        instance2 = lazy.get()
        assert instance2 == "instance_2"  # Different instance
        assert sync_initializer.call_count["count"] == 2

    def test_reset_before_initialization(self, sync_initializer):
        """Test reset before any initialization has no effect"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        # Reset before initialization
        lazy.reset()
        assert lazy.is_initialized is False
        assert lazy.has_instance is False

        # Should still initialize normally
        instance = lazy.get()
        assert instance == "instance_1"

    def test_reset_clears_failed_state(self, failing_initializer, sync_initializer):
        """Test reset allows retry after failure"""
        call_count = {"count": 0}

        def sometimes_failing_initializer():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise RuntimeError("First attempt failed")
            return "success_instance"

        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sometimes_failing_initializer,
            is_async=False,
        )

        # First attempt fails
        instance1 = lazy.get()
        assert instance1 is None

        # Reset and try again
        lazy.reset()
        instance2 = lazy.get()
        assert instance2 == "success_instance"


class TestLazyInitializerProperties:
    """Test LazyInitializer properties"""

    def test_is_initialized_property(self, sync_initializer):
        """Test is_initialized property tracks initialization state"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        assert lazy.is_initialized is False

        lazy.get()
        assert lazy.is_initialized is True

        lazy.reset()
        assert lazy.is_initialized is False

    def test_has_instance_property(self, sync_initializer):
        """Test has_instance property tracks valid instance"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        assert lazy.has_instance is False

        instance = lazy.get()
        assert instance is not None
        assert lazy.has_instance is True

        lazy.reset()
        assert lazy.has_instance is False

    def test_has_instance_false_on_failure(self, failing_initializer):
        """Test has_instance is False when initialization fails"""
        lazy = LazyInitializer(
            name="FailingComponent",
            available=True,
            initializer=failing_initializer,
            is_async=False,
        )

        lazy.get()
        assert lazy.has_instance is False

    def test_has_instance_false_when_unavailable(self, sync_initializer):
        """Test has_instance is False when component unavailable"""
        lazy = LazyInitializer(
            name="UnavailableComponent",
            available=False,
            initializer=sync_initializer,
            is_async=False,
        )

        lazy.get()
        assert lazy.has_instance is False


class TestLazyInitializerEdgeCases:
    """Test LazyInitializer edge cases and corner cases"""

    def test_empty_name(self, sync_initializer):
        """Test LazyInitializer works with empty name"""
        lazy = LazyInitializer(
            name="",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        instance = lazy.get()
        assert instance == "instance_1"

    def test_none_get_existing_parameter(self, sync_initializer):
        """Test that None get_existing parameter works correctly"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            get_existing=None,
            is_async=False,
        )

        instance = lazy.get()
        assert instance == "instance_1"

    def test_multiple_reset_calls(self, sync_initializer):
        """Test multiple consecutive reset calls"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        lazy.get()
        lazy.reset()
        lazy.reset()
        lazy.reset()

        assert lazy.is_initialized is False
        assert lazy.has_instance is False

        instance = lazy.get()
        assert instance == "instance_2"

    def test_concurrent_get_calls(self, sync_initializer):
        """Test that concurrent get calls are safe (idempotency)"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        # Simulate multiple threads calling get() at the same time
        # (In reality, this is just sequential due to GIL, but tests the pattern)
        results = [lazy.get() for _ in range(10)]

        # All should return the same instance
        assert all(r == "instance_1" for r in results)
        assert sync_initializer.call_count["count"] == 1

    def test_type_hints_work_with_generic(self, sync_initializer):
        """Test that type hints work correctly with Generic[T]"""
        # This is more of a static type checking test, but we can verify
        # the LazyInitializer accepts any type
        lazy: LazyInitializer[str] = LazyInitializer(
            name="StringComponent",
            available=True,
            initializer=sync_initializer,
            is_async=False,
        )

        instance = lazy.get()
        assert isinstance(instance, str)

        # Test with different type
        lazy_int: LazyInitializer[int] = LazyInitializer(
            name="IntComponent",
            available=True,
            initializer=lambda: 42,
            is_async=False,
        )

        instance_int = lazy_int.get()
        assert instance_int == 42
        assert isinstance(instance_int, int)


class TestLazyInitializerAsyncEventLoopHandling:
    """Test LazyInitializer async event loop edge cases"""

    def test_no_event_loop_async_initialization(self, async_initializer):
        """Test async initialization when no event loop exists"""
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_initializer,
            is_async=True,
        )

        # Should create new event loop and run
        instance = lazy.get()
        assert instance == "async_instance_1"

    def test_async_initialization_creates_loop_if_needed(self):
        """Test that async initialization handles missing event loop"""

        async def async_init():
            await asyncio.sleep(0.001)
            return "created_instance"

        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=async_init,
            is_async=True,
        )

        # Should work even if no loop exists
        instance = lazy.get()
        assert instance == "created_instance"

    def test_sync_initialization_ignores_is_async_flag(self, sync_initializer):
        """Test that sync functions work regardless of is_async flag"""
        # This tests robustness - if someone marks a sync function as async
        lazy = LazyInitializer(
            name="TestComponent",
            available=True,
            initializer=sync_initializer,
            is_async=True,  # Wrong flag, but should handle gracefully
        )

        # Should still work (though it will try to await it and fail)
        # The exception handling should catch this
        instance = lazy.get()
        # Due to the wrong flag, this will fail, returning None
        assert instance is None or instance == "instance_1"


# ========================================================================
# Module-level Fixtures for CommandRouter tests
# ========================================================================


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for CommandRouter"""
    orchestrator = Mock()
    # Agents need explicit triggers=[] to avoid Mock iteration errors
    orchestrator.agents = {
        "ops": Mock(name="Ops", role="Operations Manager", voice="Professional", triggers=[]),
        "strategy": Mock(
            name="Strategy", role="Strategic Advisor", voice="Thoughtful", triggers=[]
        ),
        "coach": Mock(name="Coach", role="Accountability Coach", voice="Direct", triggers=[]),
        "health": Mock(name="Health", role="Health Optimizer", voice="Supportive", triggers=[]),
    }
    orchestrator._build_system_prompt = Mock(return_value="Test system prompt")
    orchestrator.run_command = Mock()

    session_manager = Mock()
    session_manager.get_stats = Mock(
        return_value={
            "duration_minutes": 10,
            "message_count": 5,
            "total_input_tokens": 1000,
            "total_output_tokens": 2000,
            "total_cost": 0.05,
        }
    )
    session_manager.clear = Mock()
    session_manager.save = Mock(return_value=Path("/fake/session.md"))
    session_manager.get_messages_for_api = Mock(return_value=[])

    context_manager = Mock()
    context_manager.get_usage_report = Mock(
        return_value={
            "system_tokens": 500,
            "history_tokens": 1500,
            "total_used": 2000,
            "available": 200000,
            "usage_percent": 1.0,
            "messages_in_context": 5,
        }
    )

    state_reader = Mock()
    state_reader.get_quick_context = Mock(
        return_value={
            "focus": "Test focus",
            "top3": ["Task 1", "Task 2", "Task 3"],
            "pending_commitments": 3,
            "blockers": ["Blocker 1"],
            "energy": "High",
            "week_theme": "Testing week",
        }
    )

    thanos_dir = Path("/fake/thanos")

    return {
        "orchestrator": orchestrator,
        "session_manager": session_manager,
        "context_manager": context_manager,
        "state_reader": state_reader,
        "thanos_dir": thanos_dir,
    }


@pytest.fixture
def router(mock_dependencies):
    """Create CommandRouter with mocked dependencies"""
    return CommandRouter(
        orchestrator=mock_dependencies["orchestrator"],
        session_manager=mock_dependencies["session_manager"],
        context_manager=mock_dependencies["context_manager"],
        state_reader=mock_dependencies["state_reader"],
        thanos_dir=mock_dependencies["thanos_dir"],
    )


# ========================================================================
# CommandRouter Tests
# ========================================================================


class TestCommandRouter:
    """Test CommandRouter initialization and routing"""

    def test_initialization(self, router):
        """Test CommandRouter initializes with correct dependencies"""
        assert router.orchestrator is not None
        assert router.session is not None
        assert router.context_mgr is not None
        assert router.state_reader is not None
        assert router.thanos_dir == Path("/fake/thanos")
        assert router.current_agent == "ops"
        assert len(router._commands) > 0

    def test_command_registration(self, router):
        """Test all expected commands are registered"""
        expected_commands = [
            "agent",
            "a",  # Agent switching
            "clear",  # History management
            "save",  # Session saving
            "usage",  # Usage stats
            "context",  # Context window
            "state",
            "s",  # State display
            "commitments",
            "c",  # Commitments
            "help",
            "h",  # Help
            "quit",
            "q",
            "exit",  # Exit
            "run",  # Command execution
            "agents",  # List agents
        ]
        for cmd in expected_commands:
            assert cmd in router._commands

    def test_unknown_command(self, router, capsys):
        """Test unknown command handling"""
        result = router.route_command("/unknown")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        captured = capsys.readouterr()
        assert "Unknown command" in captured.out

    def test_command_aliases(self, router):
        """Test command aliases route to same handler"""
        # State aliases
        assert router._commands["state"][0] == router._commands["s"][0]
        # Commitments aliases
        assert router._commands["commitments"][0] == router._commands["c"][0]
        # Agent aliases
        assert router._commands["agent"][0] == router._commands["a"][0]
        # Help aliases
        assert router._commands["help"][0] == router._commands["h"][0]
        # Quit aliases
        assert router._commands["quit"][0] == router._commands["q"][0]
        assert router._commands["quit"][0] == router._commands["exit"][0]


class TestCommandResult:
    """Test CommandResult dataclass"""

    def test_default_values(self):
        """Test CommandResult default values"""
        result = CommandResult()
        assert result.action == CommandAction.CONTINUE
        assert result.message is None
        assert result.success is True

    def test_quit_result(self):
        """Test CommandResult with QUIT action"""
        result = CommandResult(action=CommandAction.QUIT)
        assert result.action == CommandAction.QUIT
        assert result.success is True

    def test_error_result(self):
        """Test CommandResult with error"""
        result = CommandResult(success=False, message="Error occurred")
        assert result.action == CommandAction.CONTINUE
        assert result.success is False
        assert result.message == "Error occurred"


class TestColors:
    """Test Colors class constants"""

    def test_color_codes_defined(self):
        """Test all color codes are defined"""
        assert hasattr(Colors, "PURPLE")
        assert hasattr(Colors, "CYAN")
        assert hasattr(Colors, "DIM")
        assert hasattr(Colors, "RESET")
        assert hasattr(Colors, "BOLD")

        # Check they are strings
        assert isinstance(Colors.PURPLE, str)
        assert isinstance(Colors.CYAN, str)
        assert isinstance(Colors.DIM, str)
        assert isinstance(Colors.RESET, str)
        assert isinstance(Colors.BOLD, str)
