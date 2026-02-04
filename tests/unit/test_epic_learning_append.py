#!/usr/bin/env python3
"""
Regression tests for Epic learning append behavior in ThanosOrchestrator.

Ensures Epic Learning Check is appended even when routing executes a tool
instead of falling back to chat.
"""

from pathlib import Path

import pytest

from Tools.thanos_orchestrator import ThanosOrchestrator
from Tools.router_executor import RoutingResult, ExecutionResult


def test_route_appends_epic_learning_for_tool_path(monkeypatch, tmp_path: Path):
    """Epic learning should append when a tool route succeeds."""
    (tmp_path / "State").mkdir(parents=True, exist_ok=True)
    orchestrator = ThanosOrchestrator(base_dir=str(tmp_path))

    def fake_route(message: str) -> RoutingResult:
        return RoutingResult(
            tool_name="memory_context",
            confidence=0.9,
            parameters={"action": "context", "query": message},
        )

    def fake_execute(tool_name: str, parameters: dict) -> ExecutionResult:
        return ExecutionResult(
            success=True,
            output="TOOL OUTPUT",
            tool_name=tool_name,
        )

    called = {}

    def fake_append(message: str, reply: str) -> str:
        called["message"] = message
        called["reply"] = reply
        return f"{reply}\n\n---\nEpic Learning Check:\nTEST"

    monkeypatch.setattr(orchestrator.router, "route", fake_route)
    monkeypatch.setattr(orchestrator.executor, "execute", fake_execute)
    monkeypatch.setattr(orchestrator, "_maybe_append_epic_learning", fake_append)

    result = orchestrator.route("Need help debugging the VersaCare interface")

    assert "Epic Learning Check" in result["content"]
    assert "TOOL OUTPUT" in result["content"]
    assert called["message"] == "Need help debugging the VersaCare interface"
    assert called["reply"] == "TOOL OUTPUT"


def test_route_appends_epic_learning_for_chat_path(monkeypatch, tmp_path: Path):
    """Epic learning should append when routing falls back to chat."""
    (tmp_path / "State").mkdir(parents=True, exist_ok=True)
    orchestrator = ThanosOrchestrator(base_dir=str(tmp_path))

    def fake_route(message: str) -> RoutingResult:
        return RoutingResult(confidence=0.2)

    def fake_chat(message: str, agent: str = "default", model: str = None):
        return {"content": "CHAT OUTPUT", "usage": None}

    called = {}

    def fake_append(message: str, reply: str) -> str:
        called["message"] = message
        called["reply"] = reply
        return f"{reply}\n\n---\nEpic Learning Check:\nTEST"

    monkeypatch.setattr(orchestrator.router, "route", fake_route)
    monkeypatch.setattr(orchestrator, "chat", fake_chat)
    monkeypatch.setattr(orchestrator, "_maybe_append_epic_learning", fake_append)

    result = orchestrator.route("Need help with orderset build in HOD")

    assert "Epic Learning Check" in result["content"]
    assert "CHAT OUTPUT" in result["content"]
    assert called["message"] == "Need help with orderset build in HOD"
    assert called["reply"] == "CHAT OUTPUT"
