#!/usr/bin/env python3
"""
ThanosInteractive - Interactive mode for Thanos with real-time token/cost display.

This module provides an interactive command-line interface for conversing with
Thanos agents. It displays real-time token usage and cost estimates in the prompt,
allowing users to monitor their API spend during sessions.

Key Features:
    - Interactive conversation loop with agent responses
    - Real-time token count and cost display in prompt
    - Slash command support via CommandRouter
    - Session management and persistence
    - Agent switching and context tracking
    - Graceful exit handling (Ctrl+C, Ctrl+D)

Key Classes:
    ThanosInteractive: Main interactive mode controller

Usage:
    from Tools.thanos_interactive import ThanosInteractive

    # Initialize with orchestrator
    interactive = ThanosInteractive(orchestrator)

    # Start interactive session
    interactive.run()

Example Session:
    Welcome to Thanos Interactive Mode
    Type /help for commands, /quit to exit

    (0 | $0.00) Thanos> Hello
    [Agent responds...]

    (1.2K | $0.04) Thanos> /usage
    [Shows detailed usage stats...]

    (1.2K | $0.04) Thanos> /quit
    Goodbye!

See Also:
    - Tools.prompt_formatter: Prompt formatting with token/cost display
    - Tools.command_router: Slash command routing and execution
    - Tools.session_manager: Session state and history management
"""

import sys
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

import asyncio
from Tools.command_router import CommandRouter, CommandAction, Colors
from Tools.context_manager import ContextManager
from Tools.prompt_formatter import PromptFormatter
from Tools.session_manager import SessionManager
from Tools.state_reader import StateReader
from Tools.memos import get_memos

# MCP Bridge imports for tool execution
from Tools.adapters.mcp_bridge import MCPBridge

logger = logging.getLogger(__name__)


class ThanosInteractive:
    """
    Interactive mode controller for Thanos conversations.

    Manages the interactive session loop, integrating prompt formatting,
    command routing, session management, and orchestrator communication.

    Attributes:
        orchestrator: ThanosOrchestrator instance for agent communication
        session_manager: SessionManager for conversation history
        context_manager: ContextManager for context window tracking
        state_reader: StateReader for Thanos state access
        command_router: CommandRouter for slash command handling
        prompt_formatter: PromptFormatter for prompt display
        thanos_dir: Path to Thanos project root
    """

    def __init__(self, orchestrator, startup_command: Optional[str] = None):
        """
        Initialize ThanosInteractive with orchestrator.

        Args:
            orchestrator: ThanosOrchestrator instance for agent communication
            startup_command: Optional command to execute immediately on startup
        """
        # Ensure stdout handles UTF-8 (crucial for Windows console)
        if sys.platform == "win32":
            sys.stdout.reconfigure(encoding='utf-8')
        
        self.orchestrator = orchestrator

        # Determine Thanos directory (parent of Tools)
        self.thanos_dir = Path(__file__).parent.parent
        
        # Load default startup command from config if not provided
        if startup_command is None:
            # Try to get config from orchestrator, or load from file
            if hasattr(self.orchestrator, "config"):
                config = self.orchestrator.config
            else:
                config_path = self.thanos_dir / "config" / "api.json"
                if config_path.exists():
                    try:
                        config = json.loads(config_path.read_text(encoding='utf-8'))
                    except Exception:
                        config = {}
                else:
                    config = {}

            startup_config = config.get("startup", {})
            startup_command = startup_config.get("default_command")
            
        self.startup_command = startup_command

        # Initialize components
        self.session_manager = SessionManager(
            history_dir=self.thanos_dir / "History" / "Sessions"
        )
        self.context_manager = ContextManager()
        self.state_reader = StateReader(self.thanos_dir / "State")

        # Initialize command router with dependencies
        self.command_router = CommandRouter(
            orchestrator=orchestrator,
            session_manager=self.session_manager,
            context_manager=self.context_manager,
            state_reader=self.state_reader,
            thanos_dir=self.thanos_dir,
        )

        # Initialize prompt formatter (loads config from config/api.json)
        self.prompt_formatter = PromptFormatter()

        # Initialize MCP bridges for tool execution
        self.mcp_bridges: Dict[str, MCPBridge] = {}
        self.mcp_tools: List[Dict[str, Any]] = []
        self._init_mcp_bridges()

    def _init_mcp_bridges(self) -> None:
        """
        Initialize MCP bridges from config/api.json mcp_servers section.

        Only loads servers explicitly configured in the project's api.json,
        not from global ~/.claude.json to avoid loading unrelated servers.
        """
        try:
            # Load MCP servers from config/api.json
            config_path = self.thanos_dir / "config" / "api.json"
            if not config_path.exists():
                logger.debug("No config/api.json found")
                return

            config = json.loads(config_path.read_text())
            mcp_servers = config.get("mcp_servers", {})

            if not mcp_servers:
                logger.debug("No MCP servers configured in api.json")
                return

            # Import config types
            from Tools.adapters.mcp_config import StdioConfig, MCPServerConfig

            # Create bridges for each configured server
            for name, server_config in mcp_servers.items():
                if not server_config.get("enabled", True):
                    logger.debug(f"Skipping disabled MCP server: {name}")
                    continue

                try:
                    # Build MCPServerConfig from json config
                    # StdioConfig has type="stdio" which discriminates the transport
                    # Use cwd from config if specified, otherwise project root
                    cwd = server_config.get("cwd") or str(self.thanos_dir)
                    transport_config = StdioConfig(
                        command=server_config["command"],
                        args=server_config.get("args", []),
                        env=server_config.get("env") or {},
                        cwd=cwd
                    )
                    mcp_config = MCPServerConfig(
                        name=name,
                        transport=transport_config
                    )
                    bridge = MCPBridge(mcp_config)
                    self.mcp_bridges[name] = bridge
                    logger.info(f"Created MCP bridge for server: {name}")
                except Exception as e:
                    logger.warning(f"Failed to create bridge for server '{name}': {e}")

            # Refresh tools from all bridges (async operation)
            if self.mcp_bridges:
                asyncio.run(self._refresh_mcp_tools())

        except Exception as e:
            logger.warning(f"Failed to initialize MCP bridges: {e}")

    async def _refresh_mcp_tools(self) -> None:
        """Refresh and cache tools from all MCP bridges."""
        self.mcp_tools = []

        for name, bridge in self.mcp_bridges.items():
            try:
                tools = await bridge.refresh_tools()
                for tool in tools:
                    # Add server prefix to tool name to avoid collisions
                    # Format: mcp__servername__toolname
                    prefixed_name = f"mcp__{name}__{tool['name']}"
                    self.mcp_tools.append({
                        "type": "function",
                        "function": {
                            "name": prefixed_name,
                            "description": tool.get("description", ""),
                            "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                        },
                        "_mcp_server": name,
                        "_mcp_tool": tool["name"]
                    })
                logger.info(f"Loaded {len(tools)} tools from MCP server '{name}'")
            except Exception as e:
                logger.warning(f"Failed to refresh tools from server '{name}': {e}")

    def _sanitize_schema(self, schema: Any) -> Any:
        """
        Sanitize a JSON schema to fix invalid values from MCP servers.

        Some MCP servers (like gsuite) return invalid schemas with False
        where arrays or objects are expected. This fixes those issues.

        Args:
            schema: The schema value to sanitize (can be dict, list, or primitive)

        Returns:
            Sanitized schema value
        """
        if schema is False:
            # False in place of array means empty array
            return []
        elif schema is True:
            # True in place of object means empty object (additionalProperties: true)
            return {}
        elif isinstance(schema, dict):
            sanitized = {}
            for key, value in schema.items():
                if key == "required":
                    # required must be an array of strings
                    if value is False or value is None:
                        sanitized[key] = []
                    elif isinstance(value, list):
                        sanitized[key] = value
                    else:
                        sanitized[key] = []
                elif key == "properties":
                    # properties must be an object
                    if isinstance(value, dict):
                        sanitized[key] = {
                            k: self._sanitize_schema(v)
                            for k, v in value.items()
                        }
                    else:
                        sanitized[key] = {}
                elif key == "additionalProperties":
                    # Can be boolean or schema object
                    if isinstance(value, bool):
                        sanitized[key] = value
                    elif isinstance(value, dict):
                        sanitized[key] = self._sanitize_schema(value)
                    else:
                        sanitized[key] = True
                else:
                    sanitized[key] = self._sanitize_schema(value)
            return sanitized
        elif isinstance(schema, list):
            return [self._sanitize_schema(item) for item in schema]
        else:
            return schema

    def _get_tools_for_api(self) -> List[Dict[str, Any]]:
        """
        Get tools in the format expected by LiteLLM/OpenAI API.

        Sanitizes schemas to fix invalid values from some MCP servers.

        Returns:
            List of tool definitions with type, function name, description, parameters
        """
        sanitized_tools = []
        for tool in self.mcp_tools:
            function = tool["function"]
            sanitized_function = {
                "name": function.get("name", ""),
                "description": function.get("description", ""),
            }
            # Sanitize parameters schema if present
            if "parameters" in function:
                sanitized_function["parameters"] = self._sanitize_schema(function["parameters"])

            sanitized_tools.append({
                "type": tool["type"],
                "function": sanitized_function
            })
        return sanitized_tools

    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single tool call via the appropriate MCP bridge.

        Args:
            tool_call: Tool call dict with id, function.name, function.arguments

        Returns:
            Dict with tool_call_id and result content
        """
        function = tool_call.get("function", {})
        tool_name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")
        tool_call_id = tool_call.get("id", "")

        # Parse arguments
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            arguments = {}

        # Find the MCP tool definition to get server and original tool name
        mcp_tool = None
        for tool in self.mcp_tools:
            if tool["function"]["name"] == tool_name:
                mcp_tool = tool
                break

        if not mcp_tool:
            return {
                "tool_call_id": tool_call_id,
                "content": json.dumps({"error": f"Tool not found: {tool_name}"})
            }

        server_name = mcp_tool["_mcp_server"]
        original_tool_name = mcp_tool["_mcp_tool"]

        bridge = self.mcp_bridges.get(server_name)
        if not bridge:
            return {
                "tool_call_id": tool_call_id,
                "content": json.dumps({"error": f"MCP server not found: {server_name}"})
            }

        # Execute the tool
        try:
            result = await bridge.call_tool(original_tool_name, arguments)

            if result.success:
                content = json.dumps(result.data) if result.data is not None else "{}"
            else:
                content = json.dumps({"error": result.error})

            return {
                "tool_call_id": tool_call_id,
                "content": content
            }
        except Exception as e:
            logger.error(f"Error executing tool {original_tool_name}: {e}")
            return {
                "tool_call_id": tool_call_id,
                "content": json.dumps({"error": str(e)})
            }

    async def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Execute multiple tool calls and collect results.

        Args:
            tool_calls: List of tool call dicts

        Returns:
            List of tool result dicts with tool_call_id and content
        """
        results = []
        for tool_call in tool_calls:
            result = await self._execute_tool_call(tool_call)
            results.append(result)
        return results

    def _run_agentic_loop(
        self,
        message: str,
        agent: Optional[str] = None,
        model: Optional[str] = None,
        history: Optional[List[Dict]] = None,
        max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Run the agentic loop with MCP tool execution.

        This method handles the complete agentic workflow:
        1. Send initial message with available tools
        2. If response contains tool_calls, execute them via MCP
        3. Send tool results back to LLM
        4. Repeat until no more tool_calls or max iterations reached
        5. Return final text response

        Args:
            message: User message to process
            agent: Optional agent name for routing
            model: Optional model override
            history: Previous conversation messages
            max_iterations: Maximum tool execution iterations (default 5)

        Returns:
            Dict with 'content' (final text) and 'usage' (token usage)
        """
        # Build system prompt
        agent_obj = None
        if agent:
            agent_obj = self.orchestrator.agents.get(agent.lower())
        else:
            agent_obj = self.orchestrator.find_agent(message)

        system_prompt = self.orchestrator._build_system_prompt(agent=agent_obj)

        # Ensure API client is initialized
        self.orchestrator._ensure_client()

        # Get tools in API format
        tools = self._get_tools_for_api() if self.mcp_tools else None

        # Initialize conversation with history
        messages = list(history) if history else []
        if not messages or messages[-1].get("content") != message:
            messages.append({"role": "user", "content": message})

        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0.0
        final_content = ""

        iteration = 0
        while iteration < max_iterations:
            iteration += 1

            # Call LLM with tools
            response = self.orchestrator.api_client.chat(
                prompt=message if iteration == 1 else "",  # First iteration uses prompt
                model=model,
                system_prompt=system_prompt,
                history=messages if iteration > 1 else history,
                tools=tools,
                tool_choice={"type": "auto"} if tools else None,  # Enable tool use
                operation=f"chat:{agent_obj.name if agent_obj else 'default'}"
            )

            # Handle tool calls response
            if isinstance(response, dict) and response.get("type") == "tool_calls":
                tool_calls = response.get("tool_calls", [])
                assistant_content = response.get("content", "")

                # Show thinking indicator
                print(f"{Colors.DIM}[Executing {len(tool_calls)} tool(s)...]{Colors.RESET}")

                # Add assistant message with tool calls to conversation
                assistant_message = {
                    "role": "assistant",
                    "content": assistant_content,
                    "tool_calls": tool_calls
                }
                messages.append(assistant_message)

                # Execute tool calls
                try:
                    tool_results = asyncio.run(self._execute_tool_calls(tool_calls))
                except RuntimeError:
                    # Handle case where event loop is already running
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        tool_results = loop.run_until_complete(self._execute_tool_calls(tool_calls))
                    finally:
                        loop.close()

                # Add tool results to conversation
                # Format depends on model - Anthropic uses different structure
                # LiteLLM should convert, but we support both formats for reliability
                for result in tool_results:
                    # OpenAI format (works with gpt-* and should be converted by LiteLLM)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "content": result["content"]
                    })

                # Continue loop to get next response
                continue

            # No tool calls - this is the final response
            if isinstance(response, dict):
                final_content = response.get("content", "")
                usage = response.get("usage", {})
                if usage:
                    total_input_tokens += usage.get("input_tokens", 0)
                    total_output_tokens += usage.get("output_tokens", 0)
                    total_cost += usage.get("cost_usd", 0.0)
            else:
                final_content = response if isinstance(response, str) else ""

            # Print the final response
            if final_content:
                print(final_content)

            break

        # Return standardized response format
        return {
            "content": final_content,
            "usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "cost_usd": total_cost
            } if total_input_tokens or total_output_tokens else None
        }

    def run(self) -> None:
        """
        Start the interactive session loop.

        This is the main entry point for interactive mode. It displays a welcome
        message, then enters a loop that:
        1. Displays prompt with current token/cost stats
        2. Gets user input
        3. Routes commands or sends messages to orchestrator
        4. Updates session stats
        5. Repeats until user quits

        The loop handles Ctrl+C and Ctrl+D gracefully for clean exits.
        """
        # Display welcome message
        self._show_welcome()

        # Main interaction loop
        first_turn = True
        
        while True:
            try:
                # Handle startup command on first turn
                if first_turn and self.startup_command:
                    user_input = self.startup_command
                    # Print it to simulate user typing
                    stats = self.session_manager.get_stats()
                    prompt_mode = self.command_router.current_prompt_mode
                    prompt = self.prompt_formatter.format(stats, mode=prompt_mode)
                    print(f"{prompt}{user_input}")
                    first_turn = False
                else:
                    # Get current session stats for prompt
                    stats = self.session_manager.get_stats()
    
                    # Format prompt with stats (uses mode from command router or config default)
                    prompt_mode = self.command_router.current_prompt_mode
                    prompt = self.prompt_formatter.format(stats, mode=prompt_mode)
    
                    # Get user input
                    user_input = input(prompt).strip()
    
                    # Skip empty input
                    if not user_input:
                        continue

                # Handle slash commands
                if user_input.startswith("/"):
                    # Handle /tools command locally (MCP tool listing)
                    if user_input.lower().startswith("/tools"):
                        self._show_mcp_tools()
                        continue

                    result = self.command_router.route_command(user_input)
                    if result.action == CommandAction.QUIT:
                        break
                    continue

                # Check for intelligent agent routing
                suggested_agent = self.command_router.detect_agent(user_input, auto_switch=False)
                if suggested_agent and suggested_agent != self.command_router.current_agent:
                    agent_name = self.orchestrator.agents[suggested_agent].name
                    print(f"{Colors.DIM}[Routing to {agent_name}]{Colors.RESET}")
                    self.command_router.current_agent = suggested_agent

                # Add user message to session (token count will be updated after API call)
                self.session_manager.add_user_message(user_input, tokens=0)

                # Send message to orchestrator
                current_agent = self.command_router.current_agent
                model = self.command_router.get_current_model()

                # Get history for context
                history = self.session_manager.get_messages_for_api()

                try:
                    # Determine if we should use MCP tools (non-streaming for tool calls)
                    use_mcp_tools = bool(self.mcp_tools)

                    if use_mcp_tools:
                        # Use agentic loop with tools (non-streaming)
                        response = self._run_agentic_loop(
                            message=user_input,
                            agent=current_agent,
                            model=model,
                            history=history
                        )
                    else:
                        # Original streaming path (no tools)
                        response = self.orchestrator.chat(
                            message=user_input,
                            agent=current_agent,
                            model=model,
                            stream=True,
                            history=history
                        )

                    
                    # Process response structure
                    content = ""
                    usage = None
                    api_error = False

                    if isinstance(response, dict):
                        content = response.get("content", "")
                        usage = response.get("usage")
                        api_error = response.get("api_error", False)

                        # Check for error indicators: api_error flag or empty usage with no content
                        if api_error or (not usage and not content):
                            self.session_manager.session.error_count = getattr(
                                self.session_manager.session, 'error_count', 0
                            ) + 1
                            error_msg = response.get("error_message", "Request failed")
                            print(f"{Colors.DIM}[API Error: {error_msg} - will retry automatically]{Colors.RESET}")
                            continue
                    else:
                        content = response

                    # Add assistant response to session
                    if content:
                        output_tokens = usage.get("output_tokens", 0) if usage else 0
                        input_tokens = usage.get("input_tokens", 0) if usage else 0
                        cost = usage.get("cost_usd", 0.0) if usage else 0.0
                        
                        # Update the last user message with actual input tokens
                        if usage:
                             # Find the last message (which is the user message we just added)
                             if self.session_manager.session.history:
                                 last_msg = self.session_manager.session.history[-1]
                                 if last_msg.role == "user":
                                     # Adjust total input tokens (remove old estimate, add new actual)
                                     self.session_manager.session.total_input_tokens -= last_msg.tokens
                                     last_msg.tokens = input_tokens
                                     self.session_manager.session.total_input_tokens += input_tokens
                                 elif len(self.session_manager.session.history) >= 2:
                                     # Try second to last (if we have async issues or other messages)
                                     prev_msg = self.session_manager.session.history[-2]
                                     if prev_msg.role == "user":
                                         self.session_manager.session.total_input_tokens -= prev_msg.tokens
                                         prev_msg.tokens = input_tokens
                                         self.session_manager.session.total_input_tokens += input_tokens

                        # Add assistant message with output tokens
                        self.session_manager.add_assistant_message(content, tokens=output_tokens)
                        
                        # Update total session cost
                        if usage:
                            # If usage dict has cost, use it directly as the increment
                            self.session_manager.session.total_cost += cost
                        elif self.orchestrator.api_client.usage_tracker:
                            # Fallback: estimate cost if usage dict is missing but tracker exists
                            # Note: This is an estimation fallback
                            est_cost = self.orchestrator.api_client.usage_tracker.calculate_cost(
                                model or "default", input_tokens, output_tokens
                            )
                            self.session_manager.session.total_cost += est_cost

                        # Update last interaction time after each successful chat
                        self.state_reader.update_last_interaction(
                            interaction_type="chat",
                            agent=current_agent
                        )

                except Exception as e:
                    # Track error count
                    self.session_manager.session.error_count = getattr(
                        self.session_manager.session, 'error_count', 0
                    ) + 1

                    # Provide informative error messages based on error type
                    error_msg = str(e)
                    if "404" in error_msg:
                        print(f"{Colors.DIM}[API endpoint not found - check model name]{Colors.RESET}")
                    elif "rate" in error_msg.lower() or "429" in error_msg:
                        print(f"{Colors.DIM}[Rate limited - waiting...]{Colors.RESET}")
                    elif "401" in error_msg or "unauthorized" in error_msg.lower():
                        print(f"{Colors.DIM}[Authentication failed - check API key]{Colors.RESET}")
                    elif "timeout" in error_msg.lower():
                        print(f"{Colors.DIM}[Request timed out - will retry]{Colors.RESET}")
                    elif "connection" in error_msg.lower():
                        print(f"{Colors.DIM}[Connection error - check network]{Colors.RESET}")
                    else:
                        print(f"{Colors.DIM}[Error: {e}]{Colors.RESET}")
                    continue

            except (KeyboardInterrupt, EOFError):
                # Handle Ctrl+C or Ctrl+D gracefully
                print("\n")
                break
            except Exception as e:
                # Catch any other errors to prevent crash
                print(f"{Colors.DIM}Unexpected error: {e}{Colors.RESET}")
                continue

        # Show goodbye message
        self._show_goodbye()

    def _show_mcp_tools(self) -> None:
        """Display available MCP tools."""
        if not self.mcp_tools:
            print(f"{Colors.DIM}No MCP tools available.{Colors.RESET}")
            print(f"{Colors.DIM}Configure MCP servers in .mcp.json or ~/.claude.json{Colors.RESET}")
            return

        print(f"\n{Colors.CYAN}Available MCP Tools ({len(self.mcp_tools)} tools){Colors.RESET}")
        print(f"{Colors.DIM}{'='*50}{Colors.RESET}")

        # Group tools by server
        tools_by_server: Dict[str, List[Dict]] = {}
        for tool in self.mcp_tools:
            server = tool.get("_mcp_server", "unknown")
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)

        for server, tools in tools_by_server.items():
            print(f"\n{Colors.GREEN}{server}{Colors.RESET} ({len(tools)} tools)")
            for tool in tools[:10]:  # Show first 10 tools per server
                func = tool.get("function", {})
                name = func.get("name", "").replace(f"mcp__{server}__", "")
                desc = func.get("description", "")[:60]
                if len(func.get("description", "")) > 60:
                    desc += "..."
                print(f"  {Colors.DIM}{name}{Colors.RESET}: {desc}")

            if len(tools) > 10:
                print(f"  {Colors.DIM}... and {len(tools) - 10} more{Colors.RESET}")

        print()

    def _show_welcome(self) -> None:
        """Display welcome message when starting interactive mode."""
        print(f"\n{Colors.CYAN}Welcome to Thanos Interactive Mode{Colors.RESET}")
        print(f"{Colors.DIM}Type /help for commands, /quit to exit{Colors.RESET}")

        # Show MCP tools info if available
        if self.mcp_tools:
            tool_count = len(self.mcp_tools)
            server_count = len(self.mcp_bridges)
            print(f"{Colors.DIM}MCP: {tool_count} tools from {server_count} server(s) available{Colors.RESET}")

        print()  # Extra newline after info

        # Update last interaction time for cross-session awareness
        self.state_reader.update_last_interaction(
            interaction_type="session_start",
            agent=self.command_router.current_agent
        )

        # Show current state context
        ctx = self.state_reader.get_quick_context()
        if ctx.get("focus"):
            print(f"{Colors.DIM}Current focus: {ctx['focus']}{Colors.RESET}")
        if ctx.get("top3"):
            print(f"{Colors.DIM}Today's top 3: {', '.join(ctx['top3'][:2])}...{Colors.RESET}")
        if ctx["focus"] or ctx["top3"]:
            print()

    def _show_goodbye(self) -> None:
        """Display goodbye message when exiting interactive mode."""
        # Update last interaction time for session end
        self.state_reader.update_last_interaction(
            interaction_type="session_end",
            agent=self.command_router.current_agent
        )

        stats = self.session_manager.get_stats()

        print(f"\n{Colors.CYAN}Session Summary:{Colors.RESET}")
        print(f"  Messages: {stats['message_count']}")
        print(f"  Total tokens: {stats['total_input_tokens'] + stats['total_output_tokens']:,}")
        print(f"  Estimated cost: ${stats['total_cost']:.4f}")
        print(f"  Duration: {stats['duration_minutes']} minutes")

        # Offer to save session if there were messages
        # Auto-save session if there were messages
        if stats['message_count'] > 0:
            try:
                filepath = self.session_manager.save()
                print(f"\n{Colors.DIM}Session saved: {filepath}{Colors.RESET}")
                
                # Auto-ingest into MemOS logic
                print(f"{Colors.DIM}Indexing memory...{Colors.RESET}", end="", flush=True)
                asyncio.run(self._ingest_session(filepath))
                print(f" {Colors.GREEN}Done{Colors.RESET}")
            except Exception as e:
                print(f"\n{Colors.RED}Auto-save failed: {e}{Colors.RESET}")



        # Close MCP bridges
        if self.mcp_bridges:
            print(f"{Colors.DIM}Closing MCP connections...{Colors.RESET}", end="", flush=True)
            try:
                asyncio.run(self._close_mcp_bridges())
                print(f" {Colors.GREEN}Done{Colors.RESET}")
            except Exception as e:
                print(f" {Colors.RED}Error: {e}{Colors.RESET}")

        print(f"\n{Colors.CYAN}Goodbye!{Colors.RESET}\n")

    async def _close_mcp_bridges(self) -> None:
        """Close all MCP bridge connections."""
        for name, bridge in self.mcp_bridges.items():
            try:
                await bridge.close()
            except Exception as e:
                logger.warning(f"Error closing MCP bridge '{name}': {e}")

    async def _ingest_session(self, filepath: Path) -> None:
        """Ingest saved session into MemOS vector store."""
        memos = get_memos()
        content = filepath.read_text(encoding='utf-8')
        
        # Store as observation/session_log
        await memos.remember(
            content=content,
            memory_type="observation",
            domain="personal",
            metadata={
                "source": "session_import", 
                "filename": filepath.name,
                "type": "session_log"
            }
        )
