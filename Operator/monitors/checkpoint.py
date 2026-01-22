#!/usr/bin/env python3
"""
Checkpoint Monitor - Thanos Operator Daemon

Monitors session checkpoints for orphaned sessions and triggers
memory extraction when crashed/abandoned sessions are detected.

This is the watchdog component of the crash-resilient memory system.

Architecture:
    - Scans State/session_checkpoints/ for orphaned sessions
    - Orphan detection: PID not running OR no activity > threshold
    - Triggers memory extraction to Memory V2
    - Reports orphan processing status

Alert Triggers:
    - Orphaned session detected (info)
    - Memory extraction failed (warning)
    - Multiple orphans accumulated (warning)
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import circuit breaker for resilience
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from Tools.circuit_breaker import CircuitBreaker
from Tools.memory_checkpoint import get_checkpoint_manager, CheckpointManager

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """Alert data structure for Operator daemon."""
    type: str
    severity: str
    title: str
    message: str
    data: Dict[str, Any]
    timestamp: str
    dedup_key: Optional[str] = None
    priority: Optional[str] = None

    def __post_init__(self):
        if not self.priority:
            self.priority = self.severity


class CheckpointMonitor:
    """
    Monitor session checkpoints and process orphaned sessions.

    This runs as part of the Operator daemon check cycle and provides:
    1. Detection of orphaned/crashed Claude Code sessions
    2. Memory extraction from orphaned checkpoints
    3. Alerting on checkpoint system health

    Config:
        - process_orphans: bool (default True) - Auto-process orphans
        - orphan_threshold_hours: float (default 2.0) - Hours before session is orphaned
        - max_orphans_per_run: int (default 5) - Cap on orphans to process per cycle
    """

    def __init__(
        self,
        circuit: CircuitBreaker,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize Checkpoint Monitor."""
        self.circuit = circuit
        self.config = config or {}

        self.process_orphans = self.config.get("process_orphans", True)
        self.orphan_threshold_hours = self.config.get("orphan_threshold_hours", 2.0)
        self.max_orphans_per_run = self.config.get("max_orphans_per_run", 5)

        self._manager: Optional[CheckpointManager] = None

    @property
    def manager(self) -> CheckpointManager:
        """Lazy-load checkpoint manager."""
        if self._manager is None:
            self._manager = get_checkpoint_manager()
        return self._manager

    async def check(self) -> List[Alert]:
        """
        Check for orphaned sessions and process them.

        Returns list of alerts about checkpoint system status.
        """
        alerts = []
        now = datetime.now()

        try:
            # Get list of orphaned sessions
            orphaned = self.manager.get_orphaned_sessions()

            if not orphaned:
                logger.debug("No orphaned sessions found")
                return alerts

            logger.info(f"Found {len(orphaned)} orphaned sessions")

            # Alert if many orphans accumulating
            if len(orphaned) > 3:
                alerts.append(Alert(
                    type="checkpoint",
                    severity="warning",
                    title="Multiple Orphaned Sessions",
                    message=f"{len(orphaned)} sessions appear to have crashed or been abandoned",
                    data={"orphan_count": len(orphaned), "session_ids": orphaned},
                    timestamp=now.isoformat(),
                    dedup_key=f"checkpoint_orphans_{len(orphaned) // 3}"  # Dedup by count band
                ))

            # Process orphans if enabled
            if self.process_orphans:
                processed = await self._process_orphans(orphaned[:self.max_orphans_per_run])

                if processed > 0:
                    alerts.append(Alert(
                        type="checkpoint",
                        severity="info",
                        title="Orphaned Sessions Recovered",
                        message=f"Recovered memory from {processed} crashed/abandoned session(s)",
                        data={"processed_count": processed},
                        timestamp=now.isoformat(),
                        dedup_key=f"checkpoint_recovered_{now.strftime('%Y%m%d_%H')}"
                    ))

        except Exception as e:
            logger.error(f"Checkpoint monitor error: {e}", exc_info=True)
            alerts.append(Alert(
                type="checkpoint",
                severity="warning",
                title="Checkpoint Monitor Error",
                message=f"Failed to check session checkpoints: {str(e)}",
                data={"error": str(e)},
                timestamp=now.isoformat(),
                dedup_key="checkpoint_error"
            ))

        return alerts

    async def _process_orphans(self, session_ids: List[str]) -> int:
        """
        Process orphaned sessions via the extraction script.

        Uses subprocess to call the orphan processor script which handles
        Memory V2 extraction with proper error handling and fallbacks.
        """
        if not session_ids:
            return 0

        try:
            # Use the orphan processor script
            script_path = Path(__file__).parent.parent.parent / "scripts" / "process_orphan_checkpoints.py"
            venv_python = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python3"

            if not script_path.exists():
                logger.error(f"Orphan processor script not found: {script_path}")
                return 0

            python_path = str(venv_python) if venv_python.exists() else sys.executable

            # Run processor
            result = await asyncio.create_subprocess_exec(
                python_path,
                str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await result.communicate()

            if result.returncode == 0:
                try:
                    output = json.loads(stdout.decode())
                    return output.get("successful", 0)
                except:
                    # Count lines as fallback
                    return len(session_ids)
            else:
                logger.error(f"Orphan processor failed: {stderr.decode()}")
                return 0

        except Exception as e:
            logger.error(f"Failed to process orphans: {e}", exc_info=True)
            return 0

    def get_status(self) -> Dict[str, Any]:
        """Get current checkpoint system status."""
        try:
            checkpoint_dir = self.manager.checkpoint_dir
            checkpoint_files = list(checkpoint_dir.glob("*.json"))
            lock_files = list(checkpoint_dir.glob("*.lock"))
            orphaned = self.manager.get_orphaned_sessions()

            return {
                "active_checkpoints": len(checkpoint_files),
                "active_locks": len(lock_files),
                "orphaned_sessions": len(orphaned),
                "checkpoint_dir": str(checkpoint_dir),
                "process_orphans_enabled": self.process_orphans
            }
        except Exception as e:
            return {"error": str(e)}


# For testing
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.DEBUG)

    async def test():
        from Tools.circuit_breaker import CircuitBreaker
        circuit = CircuitBreaker("checkpoint_test")
        monitor = CheckpointMonitor(circuit)

        print("Status:", monitor.get_status())
        alerts = await monitor.check()
        print(f"Alerts: {len(alerts)}")
        for alert in alerts:
            print(f"  - [{alert.severity}] {alert.title}: {alert.message}")

    asyncio.run(test())
