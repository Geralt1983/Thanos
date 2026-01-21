#!/usr/bin/env python3
"""
Tailscale VPN Manager for Thanos.

Provides zero-trust VPN integration with:
- Tailscale installation and authentication
- Connection state management (up/down)
- Device information and status
- ACL policy management
- Health monitoring
- Integration with ttyd and tmux

Usage:
    from Access.tailscale_manager import TailscaleManager

    manager = TailscaleManager()
    if manager.is_connected():
        url = manager.get_web_access_url()
"""

import json
import logging
import subprocess
import shutil
import platform
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class DeviceInfo:
    """Tailscale device information."""
    hostname: str
    tailscale_ip: str
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None
    os: Optional[str] = None
    online: bool = False
    last_seen: Optional[str] = None
    key_expiry: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class TailscaleStatus:
    """Tailscale connection status."""
    connected: bool
    backend_state: str  # NeedsLogin, Stopped, Starting, Running
    self_device: Optional[DeviceInfo] = None
    exit_node: Optional[str] = None
    magic_dns: bool = False
    peer_count: int = 0
    health_issues: Optional[List[str]] = None


class TailscaleManager:
    """Manages Tailscale VPN integration for Thanos."""

    # Paths
    BASE_DIR = Path(__file__).parent
    CONFIG_DIR = BASE_DIR / "config"
    STATE_FILE = BASE_DIR.parent / "State" / "tailscale_state.json"
    LOG_FILE = BASE_DIR.parent / "logs" / "tailscale.log"
    ACL_FILE = CONFIG_DIR / "tailscale-acl.json"

    # Tailscale executable paths by platform
    TAILSCALE_PATHS = {
        "darwin": "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
        "linux": "/usr/bin/tailscale"
    }

    def __init__(self):
        """Initialize Tailscale manager."""
        self.logger = self._setup_logging()
        self.platform = platform.system().lower()
        self.tailscale_available = self._check_tailscale_available()
        self.state = self._load_state()

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for Tailscale manager."""
        logger = logging.getLogger("thanos.tailscale")
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

    def _check_tailscale_available(self) -> bool:
        """Check if Tailscale is installed and available."""
        # Check system PATH first
        if shutil.which("tailscale"):
            return True

        # Check platform-specific paths
        platform_path = self.TAILSCALE_PATHS.get(self.platform)
        if platform_path and Path(platform_path).exists():
            return True

        return False

    def _run_tailscale(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run tailscale command with error handling.

        Args:
            *args: Tailscale command arguments
            check: Whether to check return code

        Returns:
            CompletedProcess result

        Raises:
            RuntimeError: If Tailscale is not available
        """
        if not self.tailscale_available:
            raise RuntimeError("Tailscale is not installed or not available")

        # Use system tailscale if available, otherwise platform-specific path
        cmd = shutil.which("tailscale")
        if not cmd:
            cmd = self.TAILSCALE_PATHS.get(self.platform)

        try:
            result = subprocess.run(
                [cmd] + list(args),
                capture_output=True,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Tailscale command failed: {e.stderr}")
            raise

    def _load_state(self) -> Dict[str, Any]:
        """Load Tailscale state from disk."""
        if not self.STATE_FILE.exists():
            return {}

        try:
            with open(self.STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load Tailscale state: {e}")
            return {}

    def _save_state(self) -> None:
        """Save Tailscale state to disk."""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self.state["last_updated"] = datetime.now().isoformat()
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save Tailscale state: {e}")

    def is_installed(self) -> bool:
        """Check if Tailscale is installed.

        Returns:
            True if Tailscale is installed
        """
        return self.tailscale_available

    def is_connected(self) -> bool:
        """Check if Tailscale is connected.

        Returns:
            True if connected and running
        """
        if not self.tailscale_available:
            return False

        try:
            result = self._run_tailscale("status", "--json", check=False)
            if result.returncode != 0:
                return False

            status_data = json.loads(result.stdout)
            backend_state = status_data.get("BackendState", "")
            return backend_state == "Running"

        except Exception as e:
            self.logger.warning(f"Error checking Tailscale status: {e}")
            return False

    def get_status(self) -> TailscaleStatus:
        """Get comprehensive Tailscale status.

        Returns:
            TailscaleStatus object
        """
        if not self.tailscale_available:
            return TailscaleStatus(
                connected=False,
                backend_state="NotInstalled"
            )

        try:
            result = self._run_tailscale("status", "--json", check=False)
            if result.returncode != 0:
                return TailscaleStatus(
                    connected=False,
                    backend_state="Error"
                )

            status_data = json.loads(result.stdout)
            backend_state = status_data.get("BackendState", "Unknown")
            self_data = status_data.get("Self", {})

            # Parse self device info
            self_device = None
            if self_data:
                self_device = DeviceInfo(
                    hostname=self_data.get("HostName", ""),
                    tailscale_ip=self_data.get("TailscaleIPs", [""])[0] if self_data.get("TailscaleIPs") else "",
                    ipv4=self_data.get("TailscaleIPs", [""])[0] if self_data.get("TailscaleIPs") else None,
                    os=self_data.get("OS", ""),
                    online=self_data.get("Online", False),
                    last_seen=self_data.get("LastSeen"),
                    key_expiry=self_data.get("KeyExpiry"),
                    tags=self_data.get("Tags", [])
                )

            # Count peers
            peer_count = len(status_data.get("Peer", {}))

            # Check for health issues
            health_issues = []
            if not status_data.get("MagicDNSSuffix"):
                health_issues.append("MagicDNS not enabled")

            return TailscaleStatus(
                connected=backend_state == "Running",
                backend_state=backend_state,
                self_device=self_device,
                magic_dns=bool(status_data.get("MagicDNSSuffix")),
                peer_count=peer_count,
                health_issues=health_issues if health_issues else None
            )

        except Exception as e:
            self.logger.error(f"Failed to get Tailscale status: {e}")
            return TailscaleStatus(
                connected=False,
                backend_state="Error"
            )

    def up(self, accept_routes: bool = False, accept_dns: bool = True) -> bool:
        """Bring Tailscale connection up.

        Args:
            accept_routes: Accept subnet routes from peers
            accept_dns: Accept DNS configuration

        Returns:
            True if successful
        """
        if not self.tailscale_available:
            self.logger.error("Tailscale is not installed")
            return False

        try:
            args = ["up"]

            if accept_routes:
                args.append("--accept-routes")

            if accept_dns:
                args.append("--accept-dns")

            self.logger.info("Bringing Tailscale up...")
            result = self._run_tailscale(*args)

            # Update state
            self.state["last_connected"] = datetime.now().isoformat()
            self.state["accept_routes"] = accept_routes
            self.state["accept_dns"] = accept_dns
            self._save_state()

            self.logger.info("Tailscale connection established")
            return True

        except Exception as e:
            self.logger.error(f"Failed to bring Tailscale up: {e}")
            return False

    def down(self) -> bool:
        """Bring Tailscale connection down.

        Returns:
            True if successful
        """
        if not self.tailscale_available:
            return False

        try:
            self.logger.info("Bringing Tailscale down...")
            self._run_tailscale("down")

            # Update state
            self.state["last_disconnected"] = datetime.now().isoformat()
            self._save_state()

            self.logger.info("Tailscale disconnected")
            return True

        except Exception as e:
            self.logger.error(f"Failed to bring Tailscale down: {e}")
            return False

    def get_ip(self) -> Optional[str]:
        """Get Tailscale IP address of this device.

        Returns:
            Tailscale IP address or None
        """
        status = self.get_status()
        if status.self_device:
            return status.self_device.tailscale_ip
        return None

    def get_hostname(self) -> Optional[str]:
        """Get Tailscale hostname (MagicDNS name).

        Returns:
            MagicDNS hostname or None
        """
        status = self.get_status()
        if status.self_device and status.magic_dns:
            # MagicDNS hostname format: hostname.tailnet-name.ts.net
            return status.self_device.hostname
        return None

    def get_web_access_url(self, port: int = 443, use_magicDNS: bool = True) -> Optional[str]:
        """Get HTTPS URL for web access via Tailscale.

        Args:
            port: Port number (default: 443 for HTTPS)
            use_magicDNS: Use MagicDNS hostname if available

        Returns:
            HTTPS URL or None if not connected
        """
        if not self.is_connected():
            return None

        status = self.get_status()
        if not status.self_device:
            return None

        # Prefer MagicDNS hostname if available and enabled
        if use_magicDNS and status.magic_dns:
            hostname = status.self_device.hostname
            return f"https://{hostname}:{port}/" if port != 443 else f"https://{hostname}/"

        # Fall back to IP address
        ip = status.self_device.tailscale_ip
        if ip:
            return f"https://{ip}:{port}/" if port != 443 else f"https://{ip}/"

        return None

    def get_ssh_command(self, user: str = "jeremy") -> Optional[str]:
        """Get SSH command for Tailscale access.

        Args:
            user: SSH username

        Returns:
            SSH command string or None
        """
        status = self.get_status()
        if not status.connected or not status.self_device:
            return None

        # Prefer MagicDNS hostname
        if status.magic_dns:
            host = status.self_device.hostname
        else:
            host = status.self_device.tailscale_ip

        return f"ssh {user}@{host}"

    def list_devices(self) -> List[DeviceInfo]:
        """List all devices in the Tailscale network.

        Returns:
            List of DeviceInfo objects
        """
        if not self.tailscale_available:
            return []

        try:
            result = self._run_tailscale("status", "--json", check=False)
            if result.returncode != 0:
                return []

            status_data = json.loads(result.stdout)
            devices = []

            # Add self
            if "Self" in status_data:
                self_data = status_data["Self"]
                devices.append(DeviceInfo(
                    hostname=self_data.get("HostName", ""),
                    tailscale_ip=self_data.get("TailscaleIPs", [""])[0] if self_data.get("TailscaleIPs") else "",
                    os=self_data.get("OS", ""),
                    online=True,
                    tags=self_data.get("Tags", [])
                ))

            # Add peers
            for peer_id, peer_data in status_data.get("Peer", {}).items():
                devices.append(DeviceInfo(
                    hostname=peer_data.get("HostName", ""),
                    tailscale_ip=peer_data.get("TailscaleIPs", [""])[0] if peer_data.get("TailscaleIPs") else "",
                    os=peer_data.get("OS", ""),
                    online=peer_data.get("Online", False),
                    last_seen=peer_data.get("LastSeen"),
                    tags=peer_data.get("Tags", [])
                ))

            return devices

        except Exception as e:
            self.logger.error(f"Failed to list devices: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check.

        Returns:
            Health status dictionary
        """
        health = {
            "installed": self.is_installed(),
            "connected": False,
            "backend_state": "Unknown",
            "tailscale_ip": None,
            "hostname": None,
            "magic_dns": False,
            "peer_count": 0,
            "issues": [],
            "timestamp": datetime.now().isoformat()
        }

        if not health["installed"]:
            health["issues"].append("Tailscale not installed")
            return health

        status = self.get_status()
        health["connected"] = status.connected
        health["backend_state"] = status.backend_state
        health["magic_dns"] = status.magic_dns
        health["peer_count"] = status.peer_count

        if status.self_device:
            health["tailscale_ip"] = status.self_device.tailscale_ip
            health["hostname"] = status.self_device.hostname

        if status.health_issues:
            health["issues"].extend(status.health_issues)

        if not status.connected:
            health["issues"].append(f"Not connected (state: {status.backend_state})")

        return health

    def load_acl_policy(self) -> Optional[Dict[str, Any]]:
        """Load ACL policy from config file.

        Returns:
            ACL policy dict or None
        """
        if not self.ACL_FILE.exists():
            self.logger.warning(f"ACL file not found: {self.ACL_FILE}")
            return None

        try:
            with open(self.ACL_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load ACL policy: {e}")
            return None

    def validate_acl_policy(self, policy: Optional[Dict[str, Any]] = None) -> bool:
        """Validate ACL policy format.

        Args:
            policy: ACL policy dict (loads from file if None)

        Returns:
            True if valid
        """
        if policy is None:
            policy = self.load_acl_policy()

        if not policy:
            return False

        # Basic validation
        required_keys = ["acls"]
        for key in required_keys:
            if key not in policy:
                self.logger.error(f"ACL policy missing required key: {key}")
                return False

        # Validate ACL structure
        if not isinstance(policy["acls"], list):
            self.logger.error("ACL 'acls' must be a list")
            return False

        for acl in policy["acls"]:
            if not all(k in acl for k in ["action", "src", "dst"]):
                self.logger.error("ACL entry missing required fields")
                return False

        return True

    def get_connection_info(self) -> Dict[str, Any]:
        """Get comprehensive connection information for other services.

        Returns:
            Connection info dict
        """
        status = self.get_status()

        info = {
            "connected": status.connected,
            "backend_state": status.backend_state,
            "tailscale_ip": None,
            "hostname": None,
            "magic_dns": status.magic_dns,
            "web_url": None,
            "ssh_command": None
        }

        if status.self_device:
            info["tailscale_ip"] = status.self_device.tailscale_ip
            info["hostname"] = status.self_device.hostname

        if status.connected:
            info["web_url"] = self.get_web_access_url()
            info["ssh_command"] = self.get_ssh_command()

        return info


def main():
    """Test Tailscale manager functionality."""
    manager = TailscaleManager()

    print("Tailscale Manager Status:")
    print("=" * 60)

    health = manager.health_check()
    print(f"Installed: {health['installed']}")
    print(f"Connected: {health['connected']}")
    print(f"Backend State: {health['backend_state']}")
    print(f"Tailscale IP: {health['tailscale_ip']}")
    print(f"Hostname: {health['hostname']}")
    print(f"MagicDNS: {health['magic_dns']}")
    print(f"Peer Count: {health['peer_count']}")

    if health['issues']:
        print(f"\nIssues:")
        for issue in health['issues']:
            print(f"  - {issue}")

    if health['connected']:
        print(f"\nAccess Information:")
        conn_info = manager.get_connection_info()
        print(f"  Web URL: {conn_info['web_url']}")
        print(f"  SSH: {conn_info['ssh_command']}")

        print(f"\nDevices in network:")
        for device in manager.list_devices():
            status_icon = "✓" if device.online else "✗"
            print(f"  {status_icon} {device.hostname} ({device.tailscale_ip})")

    print()


if __name__ == "__main__":
    main()
