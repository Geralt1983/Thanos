#!/usr/bin/env python3
"""
OpenClaw Harness for Thanos.

OpenClaw is the harness orchestrator. This module provides a single, stable
entrypoint so OpenClaw always routes through Thanos architecture and tools.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from Tools.thanos_orchestrator import ThanosOrchestrator
from Tools import memory_capture_router


logger = logging.getLogger(__name__)

# Output control via environment variables
QUIET_MODE = os.environ.get("THANOS_QUIET_MODE", "1") == "1"
STREAMING_ENABLED = os.environ.get("THANOS_STREAMING", "0") == "1"
SHOW_THINKING = os.environ.get("THANOS_SHOW_THINKING", "0") == "1"


class OpenClawHarness:
    """Thin wrapper that binds OpenClaw sessions to Thanos orchestration."""

    def __init__(self) -> None:
        self._orchestrator = ThanosOrchestrator()

    def refresh_state(self) -> None:
        """Refresh daily state (Calendar, WorkOS) before handling a session."""
        try:
            self._orchestrator.refresh_daily_state()
        except Exception as e:
            logger.warning("OpenClaw refresh_state failed: %s", e)

    def route_message(
        self,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        source: str = "openclaw",
        allow_llm_capture: bool = False,
    ) -> Dict[str, Any]:
        """
        Route a single message through Thanos, then capture learnings.

        Returns:
            Dict with content, usage, and capture stats.
        """
        session_id = session_id or f"openclaw-{uuid.uuid4().hex[:10]}"
        context = context or {}

        result = self._orchestrator.route(message)
        reply = result.get("content", "") if isinstance(result, dict) else str(result)

        messages = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        capture_stats = memory_capture_router.capture_exchange(
            messages=messages,
            context=context,
            session_id=session_id,
            source=source,
            allow_llm=allow_llm_capture,
        )

        return {
            "content": reply,
            "usage": result.get("usage") if isinstance(result, dict) else None,
            "capture": capture_stats,
        }

    def capture_session(
        self,
        messages: List[Dict[str, str]],
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        source: str = "openclaw",
        allow_llm_capture: bool = False,
    ) -> Dict[str, int]:
        """Capture a whole session exchange for learnings."""
        context = context or {}
        return memory_capture_router.capture_exchange(
            messages=messages,
            context=context,
            session_id=session_id,
            source=source,
            allow_llm=allow_llm_capture,
        )


def get_harness() -> OpenClawHarness:
    """Factory for OpenClaw harness."""
    return OpenClawHarness()


if __name__ == "__main__":
    harness = get_harness()
    harness.refresh_state()
    print("OpenClaw harness ready")
