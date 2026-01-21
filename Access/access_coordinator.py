#!/usr/bin/env python3
"""
Unified Access Coordinator for Thanos.

Orchestrates all access methods (tmux, ttyd, Tailscale) with:
- Context-aware access routing
- Health aggregation across components
- Smart access method recommendation
- Graceful fallback handling
- State aggregation and reporting

Usage:
    from Access.access_coordinator import AccessCoordinator

    coordinator = AccessCoordinator()
    recommendation = coordinator.recommend_access_method()
    status = coordinator.get_full_status()
"""

import json
import logging
import os
import socket
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Import component managers
from Access.tmux_manager import TmuxManager
from Access.ttyd_manager import TtydManager
from Access.tailscale_manager import TailscaleManager


class AccessContext(Enum):
    """Current access context."""
    LOCAL_TERMINAL = "local_terminal"  # Direct local terminal
    SSH_SESSION = "ssh_session"        # Connected via SSH
    WEB_BROWSER = "web_browser"        # Web-based access
    MOBILE = "mobile"                  # Mobile device
    UNKNOWN = "unknown"


class AccessMethod(Enum):
    """Available access methods."""
    TMUX_LOCAL = "tmux_local"          # Direct tmux attachment
    TMUX_SSH = "tmux_ssh"              # SSH + tmux
    TTYD_WEB = "ttyd_web"              # Web terminal via ttyd
    TTYD_TAILSCALE = "ttyd_tailscale"  # Web terminal via Tailscale
    SSH_TAILSCALE = "ssh_tailscale"    # SSH via Tailscale


@dataclass
class AccessRecommendation:
    """Access method recommendation."""
    method: AccessMethod
    url: Optional[str] = None
    command: Optional[str] = None
    reason: str = ""
    priority: int = 0
    requires_setup: List[str] = None


@dataclass
class ComponentHealth:
    """Health status for a component."""
    name: str
    available: bool
    running: bool
    healthy: bool
    issues: List[str]
    details: Dict[str, Any]


class AccessCoordinator:
    """Coordinates all access methods for Thanos."""

    # Paths
    BASE_DIR = Path(__file__).parent
    STATE_FILE = BASE_DIR.parent / "State" / "access_coordinator.json"
    LOG_FILE = BASE_DIR.parent / "logs" / "access_coordinator.log"

    def __init__(self):
        """Initialize access coordinator."""
        self.logger = self._setup_logging()

        # Initialize component managers
        self.tmux = TmuxManager()
        self.ttyd = TtydManager()
        self.tailscale = TailscaleManager()

        # Detect context
        self.context = self._detect_context()

        # Load state
        self.state = self._load_state()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for access coordinator."""
        logger = logging.getLogger("thanos.access")
        logger.setLevel(logging.INFO)

        # Ensure log directory exists
        self.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # File handler
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            file_handler = logging.FileHandler(self.LOG_FILE)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(file_handler)

        # Console handler
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(
                '%(levelname)s: %(message)s'
            ))
            logger.addHandler(console_handler)

        return logger

    def _detect_context(self) -> AccessContext:
        """Detect current access context.

        Returns:
            AccessContext enum value
        """
        # Check if in SSH session
        if os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"):
            return AccessContext.SSH_SESSION

        # Check if in tmux session
        if os.environ.get("TMUX"):
            return AccessContext.LOCAL_TERMINAL

        # Check terminal type for potential mobile
        term = os.environ.get("TERM", "")
        if "screen" in term or "tmux" in term:
            return AccessContext.LOCAL_TERMINAL

        # Default to local terminal if we have a TTY
        if os.isatty(0):
            return AccessContext.LOCAL_TERMINAL

        return AccessContext.UNKNOWN

    def _load_state(self) -> Dict[str, Any]:
        """Load coordinator state from disk."""
        if not self.STATE_FILE.exists():
            return {}

        try:
            with open(self.STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")
            return {}

    def _save_state(self) -> None:
        """Save coordinator state to disk."""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.state["last_updated"] = datetime.now().isoformat()
            self.state["context"] = self.context.value
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def get_component_health(self, component: str) -> ComponentHealth:
        """Get health status for a specific component.

        Args:
            component: Component name (tmux, ttyd, tailscale)

        Returns:
            ComponentHealth object
        """
        if component == "tmux":
            status = self.tmux.get_status()
            return ComponentHealth(
                name="tmux",
                available=status["tmux_available"],
                running=len(status["active_sessions"]) > 0,
                healthy=status["tmux_available"] and len(status["active_sessions"]) > 0,
                issues=[] if status["tmux_available"] else ["tmux not installed"],
                details=status
            )

        elif component == "ttyd":
            status = self.ttyd.get_status()
            issues = []
            if not self.ttyd.ttyd_available:
                issues.append("ttyd not installed")
            elif not status.running:
                issues.append("ttyd daemon not running")

            return ComponentHealth(
                name="ttyd",
                available=self.ttyd.ttyd_available,
                running=status.running,
                healthy=status.running and self.ttyd.health_check(),
                issues=issues,
                details=asdict(status)
            )

        elif component == "tailscale":
            health = self.tailscale.health_check()
            return ComponentHealth(
                name="tailscale",
                available=health["installed"],
                running=health["connected"],
                healthy=health["connected"] and len(health["issues"]) == 0,
                issues=health["issues"],
                details=health
            )

        else:
            return ComponentHealth(
                name=component,
                available=False,
                running=False,
                healthy=False,
                issues=[f"Unknown component: {component}"],
                details={}
            )

    def get_full_status(self) -> Dict[str, Any]:
        """Get comprehensive status across all components.

        Returns:
            Full status dictionary
        """
        tmux_health = self.get_component_health("tmux")
        ttyd_health = self.get_component_health("ttyd")
        tailscale_health = self.get_component_health("tailscale")

        # Aggregate health
        all_healthy = all([
            tmux_health.healthy or not tmux_health.available,
            ttyd_health.healthy or not ttyd_health.available,
            tailscale_health.healthy or not tailscale_health.available
        ])

        # Collect all issues
        all_issues = (
            tmux_health.issues +
            ttyd_health.issues +
            tailscale_health.issues
        )

        return {
            "context": self.context.value,
            "healthy": all_healthy,
            "issues": all_issues,
            "components": {
                "tmux": asdict(tmux_health),
                "ttyd": asdict(ttyd_health),
                "tailscale": asdict(tailscale_health)
            },
            "timestamp": datetime.now().isoformat()
        }

    def recommend_access_method(self) -> List[AccessRecommendation]:
        """Recommend best access methods based on current state.

        Returns:
            List of AccessRecommendation objects, sorted by priority
        """
        recommendations = []

        # Get component health
        tmux_health = self.get_component_health("tmux")
        ttyd_health = self.get_component_health("ttyd")
        tailscale_health = self.get_component_health("tailscale")

        # Local terminal context
        if self.context == AccessContext.LOCAL_TERMINAL:
            if tmux_health.available:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.TMUX_LOCAL,
                    command="thanos-tmux",
                    reason="Direct local tmux access (best performance)",
                    priority=10
                ))

        # SSH session context
        elif self.context == AccessContext.SSH_SESSION:
            if tmux_health.available:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.TMUX_SSH,
                    command="tmux attach -t thanos-main",
                    reason="SSH + tmux (native terminal)",
                    priority=9
                ))

        # Tailscale-based access (remote scenarios)
        if tailscale_health.running:
            # Web access via Tailscale
            if ttyd_health.running:
                ts_url = self.tailscale.get_web_access_url(port=7681)
                if ts_url:
                    recommendations.append(AccessRecommendation(
                        method=AccessMethod.TTYD_TAILSCALE,
                        url=ts_url,
                        reason="Secure web terminal via Tailscale VPN",
                        priority=8
                    ))

            # SSH via Tailscale
            ssh_cmd = self.tailscale.get_ssh_command()
            if ssh_cmd:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.SSH_TAILSCALE,
                    command=ssh_cmd,
                    reason="SSH via Tailscale (secure remote access)",
                    priority=7
                ))

        # Local web access (fallback)
        if ttyd_health.running:
            url = self.ttyd.get_access_url()
            if url:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.TTYD_WEB,
                    url=url,
                    reason="Local web terminal (browser-based)",
                    priority=6,
                    requires_setup=["Network access to localhost:7681"]
                ))

        # Setup recommendations (if nothing is available)
        if not recommendations:
            if not tmux_health.available:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.TMUX_LOCAL,
                    reason="Install tmux for terminal access",
                    priority=1,
                    requires_setup=["brew install tmux"]
                ))

            if not ttyd_health.available:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.TTYD_WEB,
                    reason="Install ttyd for web access",
                    priority=1,
                    requires_setup=["Run: Access/install_ttyd.sh"]
                ))

            if not tailscale_health.available:
                recommendations.append(AccessRecommendation(
                    method=AccessMethod.TTYD_TAILSCALE,
                    reason="Install Tailscale for remote access",
                    priority=1,
                    requires_setup=["Run: Access/install_tailscale.sh"]
                ))

        # Sort by priority (highest first)
        recommendations.sort(key=lambda r: r.priority, reverse=True)

        return recommendations

    def get_access_urls(self) -> Dict[str, Optional[str]]:
        """Get all available access URLs.

        Returns:
            Dictionary of access URLs by type
        """
        urls = {
            "local_web": None,
            "tailscale_web": None,
            "tailscale_ssh": None
        }

        # Local web URL
        if self.ttyd.get_status().running:
            urls["local_web"] = self.ttyd.get_access_url()

        # Tailscale URLs
        if self.tailscale.is_connected():
            urls["tailscale_web"] = self.tailscale.get_web_access_url(port=7681)
            urls["tailscale_ssh"] = self.tailscale.get_ssh_command()

        return urls

    def ensure_access_ready(self, method: AccessMethod) -> Tuple[bool, List[str]]:
        """Ensure specified access method is ready.

        Args:
            method: AccessMethod to prepare

        Returns:
            Tuple of (ready: bool, issues: List[str])
        """
        issues = []

        if method == AccessMethod.TMUX_LOCAL:
            if not self.tmux.tmux_available:
                issues.append("tmux not installed")
                return False, issues

            # Ensure session exists
            if not self.tmux.session_exists("thanos-main"):
                if not self.tmux.create_session("thanos-main"):
                    issues.append("Failed to create tmux session")
                    return False, issues

            return True, []

        elif method in [AccessMethod.TTYD_WEB, AccessMethod.TTYD_TAILSCALE]:
            if not self.ttyd.ttyd_available:
                issues.append("ttyd not installed")
                return False, issues

            # Ensure ttyd is running
            if not self.ttyd.get_status().running:
                if not self.ttyd.start():
                    issues.append("Failed to start ttyd")
                    return False, issues

            # For Tailscale access, ensure VPN is up
            if method == AccessMethod.TTYD_TAILSCALE:
                if not self.tailscale.is_connected():
                    issues.append("Tailscale not connected")
                    return False, issues

            return True, []

        elif method in [AccessMethod.SSH_TAILSCALE, AccessMethod.TMUX_SSH]:
            if not self.tailscale.is_connected():
                issues.append("Tailscale not connected")
                return False, issues

            return True, []

        else:
            issues.append(f"Unknown access method: {method}")
            return False, issues

    def generate_qr_code(self, url: str) -> Optional[str]:
        """Generate QR code for URL (for mobile access).

        Args:
            url: URL to encode

        Returns:
            ASCII QR code or None if qrencode not available
        """
        try:
            import subprocess
            result = subprocess.run(
                ["qrencode", "-t", "ANSIUTF8", url],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.debug("qrencode not available for QR code generation")
            return None

    def get_context_info(self) -> Dict[str, Any]:
        """Get information about current access context.

        Returns:
            Context information dictionary
        """
        return {
            "context": self.context.value,
            "in_tmux": bool(os.environ.get("TMUX")),
            "in_ssh": bool(os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY")),
            "terminal": os.environ.get("TERM", "unknown"),
            "user": os.environ.get("USER", "unknown"),
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "tty": os.ttyname(0) if os.isatty(0) else None
        }


def main():
    """Test access coordinator functionality."""
    coordinator = AccessCoordinator()

    print("Access Coordinator Status")
    print("=" * 70)
    print()

    # Context info
    context_info = coordinator.get_context_info()
    print("Current Context:")
    print(f"  Type: {context_info['context']}")
    print(f"  In tmux: {context_info['in_tmux']}")
    print(f"  In SSH: {context_info['in_ssh']}")
    print(f"  Terminal: {context_info['terminal']}")
    print(f"  Hostname: {context_info['hostname']}")
    print()

    # Component health
    status = coordinator.get_full_status()
    print("Component Health:")
    for name, health in status["components"].items():
        status_icon = "✓" if health["healthy"] else "✗"
        print(f"  {status_icon} {name.upper()}")
        print(f"      Available: {health['available']}")
        print(f"      Running: {health['running']}")
        if health["issues"]:
            for issue in health["issues"]:
                print(f"      Issue: {issue}")
    print()

    # Access recommendations
    recommendations = coordinator.recommend_access_method()
    print("Recommended Access Methods:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec.method.value} (priority: {rec.priority})")
        print(f"     Reason: {rec.reason}")
        if rec.url:
            print(f"     URL: {rec.url}")
        if rec.command:
            print(f"     Command: {rec.command}")
        if rec.requires_setup:
            print(f"     Setup needed: {', '.join(rec.requires_setup)}")
        print()

    # Available URLs
    urls = coordinator.get_access_urls()
    print("Available Access URLs:")
    for url_type, url in urls.items():
        if url:
            print(f"  {url_type}: {url}")
    print()


if __name__ == "__main__":
    main()
