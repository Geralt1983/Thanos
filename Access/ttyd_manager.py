#!/usr/bin/env python3
"""
Ttyd Web Terminal Manager for Thanos.

Provides secure web-based terminal access with:
- HTTPS-only web terminal via ttyd
- Authentication and credential management
- SSL/TLS certificate handling
- Process lifecycle management
- Health monitoring and auto-restart
- Integration with tmux sessions
- Access logging and security

Usage:
    from Access.ttyd_manager import TtydManager

    manager = TtydManager()
    manager.start()
    url = manager.get_access_url()
"""

import json
import logging
import subprocess
import shutil
import signal
import time
import socket
import secrets
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import psutil


@dataclass
class TtydConfig:
    """Ttyd configuration."""
    port: int = 7681
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
    credential_file: Optional[str] = None
    writable: bool = True
    max_clients: int = 5
    check_origin: bool = True
    interface: str = "0.0.0.0"
    reconnect_timeout: int = 10
    client_timeout: int = 0
    terminal_type: str = "xterm-256color"


@dataclass
class DaemonStatus:
    """Daemon status information."""
    running: bool
    pid: Optional[int] = None
    port: int = 7681
    uptime_seconds: Optional[float] = None
    client_count: int = 0
    access_url: Optional[str] = None
    ssl_enabled: bool = False
    auth_enabled: bool = False
    started_at: Optional[str] = None
    last_health_check: Optional[str] = None


class TtydManager:
    """Manages ttyd web terminal daemon for Thanos."""

    # Paths
    BASE_DIR = Path(__file__).parent
    CONFIG_DIR = BASE_DIR / "config"
    STATE_FILE = BASE_DIR.parent / "State" / "ttyd_daemon.json"
    PID_FILE = BASE_DIR.parent / "State" / "ttyd.pid"
    LOG_FILE = BASE_DIR.parent / "logs" / "ttyd.log"
    ACCESS_LOG = BASE_DIR.parent / "logs" / "ttyd_access.log"

    # SSL paths
    SSL_DIR = CONFIG_DIR / "ssl"
    SSL_CERT = SSL_DIR / "ttyd-cert.pem"
    SSL_KEY = SSL_DIR / "ttyd-key.pem"

    # Credentials
    CREDS_FILE = CONFIG_DIR / "ttyd-credentials.json"

    # Default session
    DEFAULT_SESSION = "thanos-main"

    def __init__(self, config_file: Optional[Path] = None):
        """Initialize ttyd manager.

        Args:
            config_file: Optional path to configuration file
        """
        self.logger = self._setup_logging()
        self.config_file = config_file or (self.CONFIG_DIR / "ttyd.conf")
        self.config = self._load_config()
        self.ttyd_available = self._check_ttyd_available()
        self.daemon_state = self._load_state()
        self._process = None

    def _setup_logging(self) -> logging.Logger:
        """Setup logging for ttyd manager."""
        logger = logging.getLogger("thanos.ttyd")
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

    def _check_ttyd_available(self) -> bool:
        """Check if ttyd is installed and available."""
        return shutil.which("ttyd") is not None

    def _load_config(self) -> TtydConfig:
        """Load ttyd configuration from file."""
        if not self.config_file.exists():
            self.logger.info("No config file found, using defaults")
            return TtydConfig()

        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                return TtydConfig(**data)
        except Exception as e:
            self.logger.warning(f"Failed to load config: {e}, using defaults")
            return TtydConfig()

    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
            self.logger.info(f"Saved config to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")

    def _load_state(self) -> Dict[str, Any]:
        """Load daemon state from disk."""
        if not self.STATE_FILE.exists():
            return {}

        try:
            with open(self.STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Failed to load daemon state: {e}")
            return {}

    def _save_state(self) -> None:
        """Save daemon state to disk."""
        try:
            self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.STATE_FILE, 'w') as f:
                json.dump(self.daemon_state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save daemon state: {e}")

    def _get_pid(self) -> Optional[int]:
        """Get PID of running ttyd process."""
        if not self.PID_FILE.exists():
            return None

        try:
            with open(self.PID_FILE, 'r') as f:
                pid = int(f.read().strip())

            # Verify process is actually running
            if psutil.pid_exists(pid):
                proc = psutil.Process(pid)
                if 'ttyd' in proc.name().lower():
                    return pid

            # Stale PID file
            self.PID_FILE.unlink()
            return None

        except (ValueError, psutil.NoSuchProcess, ProcessLookupError):
            if self.PID_FILE.exists():
                self.PID_FILE.unlink()
            return None

    def _save_pid(self, pid: int) -> None:
        """Save PID to file."""
        try:
            self.PID_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.PID_FILE, 'w') as f:
                f.write(str(pid))
        except Exception as e:
            self.logger.error(f"Failed to save PID: {e}")

    def _port_in_use(self, port: int) -> bool:
        """Check if port is in use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return False
            except OSError:
                return True

    def generate_credentials(self, username: Optional[str] = None) -> Tuple[str, str]:
        """Generate authentication credentials.

        Args:
            username: Optional username (default: thanos)

        Returns:
            Tuple of (username, password)
        """
        username = username or "thanos"
        password = secrets.token_urlsafe(32)

        # Save credentials
        try:
            self.CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.CREDS_FILE, 'w') as f:
                json.dump({
                    "username": username,
                    "password": password,
                    "generated_at": datetime.now().isoformat()
                }, f, indent=2)

            # Secure permissions
            self.CREDS_FILE.chmod(0o600)
            self.logger.info(f"Generated credentials for user: {username}")

        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")

        return username, password

    def get_credentials(self) -> Optional[Tuple[str, str]]:
        """Get existing credentials.

        Returns:
            Tuple of (username, password) or None
        """
        if not self.CREDS_FILE.exists():
            return None

        try:
            with open(self.CREDS_FILE, 'r') as f:
                data = json.load(f)
            return data.get("username"), data.get("password")
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            return None

    def generate_ssl_cert(self, days: int = 365) -> bool:
        """Generate self-signed SSL certificate.

        Args:
            days: Certificate validity in days

        Returns:
            True if successful
        """
        try:
            self.SSL_DIR.mkdir(parents=True, exist_ok=True)

            # Generate using openssl
            cmd = [
                "openssl", "req", "-x509", "-newkey", "rsa:4096",
                "-keyout", str(self.SSL_KEY),
                "-out", str(self.SSL_CERT),
                "-days", str(days),
                "-nodes",
                "-subj", "/CN=localhost/O=Thanos/C=US"
            ]

            subprocess.run(cmd, check=True, capture_output=True)

            # Secure permissions
            self.SSL_KEY.chmod(0o600)
            self.SSL_CERT.chmod(0o644)

            self.logger.info(f"Generated SSL certificate (valid for {days} days)")
            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to generate SSL cert: {e.stderr.decode()}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to generate SSL cert: {e}")
            return False

    def _build_command(self, session_name: str = None) -> list:
        """Build ttyd command with all options.

        Args:
            session_name: Tmux session to attach to

        Returns:
            Command as list
        """
        session_name = session_name or self.DEFAULT_SESSION

        cmd = [
            "ttyd",
            "--port", str(self.config.port),
            "--interface", self.config.interface,
            "--max-clients", str(self.config.max_clients),
            "--terminal-type", self.config.terminal_type,
        ]

        # SSL configuration
        if self.SSL_CERT.exists() and self.SSL_KEY.exists():
            cmd.extend([
                "--ssl",
                "--ssl-cert", str(self.SSL_CERT),
                "--ssl-key", str(self.SSL_KEY)
            ])
            self.config.ssl_cert = str(self.SSL_CERT)
            self.config.ssl_key = str(self.SSL_KEY)

        # Authentication
        creds = self.get_credentials()
        if creds:
            username, password = creds
            cmd.extend(["--credential", f"{username}:{password}"])

        # Writable mode
        if self.config.writable:
            cmd.append("--writable")

        # Origin checking
        if self.config.check_origin:
            cmd.append("--check-origin")

        # Reconnect timeout
        if self.config.reconnect_timeout > 0:
            cmd.extend(["--reconnect", str(self.config.reconnect_timeout)])

        # Client timeout
        if self.config.client_timeout > 0:
            cmd.extend(["--timeout", str(self.config.client_timeout)])

        # Terminal command - attach to tmux session
        cmd.extend(["tmux", "attach", "-t", session_name])

        return cmd

    def start(self, session_name: Optional[str] = None) -> bool:
        """Start ttyd daemon.

        Args:
            session_name: Tmux session to attach to

        Returns:
            True if started successfully
        """
        if not self.ttyd_available:
            self.logger.error("ttyd is not installed")
            return False

        # Check if already running
        pid = self._get_pid()
        if pid:
            self.logger.info(f"Ttyd already running (PID: {pid})")
            return True

        # Check if port is available
        if self._port_in_use(self.config.port):
            self.logger.error(f"Port {self.config.port} is already in use")
            return False

        # Ensure SSL cert exists
        if not (self.SSL_CERT.exists() and self.SSL_KEY.exists()):
            self.logger.info("Generating SSL certificate...")
            if not self.generate_ssl_cert():
                return False

        # Ensure credentials exist
        if not self.get_credentials():
            self.logger.info("Generating authentication credentials...")
            self.generate_credentials()

        try:
            # Build command
            cmd = self._build_command(session_name)
            self.logger.info(f"Starting ttyd: {' '.join(cmd)}")

            # Start process
            log_file = open(self.LOG_FILE, 'a')
            self._process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )

            # Save PID
            self._save_pid(self._process.pid)

            # Wait a moment and verify it's running
            time.sleep(1)
            if self._process.poll() is not None:
                self.logger.error("Ttyd process exited immediately")
                return False

            # Update state
            self.daemon_state = {
                "pid": self._process.pid,
                "port": self.config.port,
                "started_at": datetime.now().isoformat(),
                "session_name": session_name or self.DEFAULT_SESSION,
                "ssl_enabled": self.SSL_CERT.exists(),
                "auth_enabled": self.get_credentials() is not None
            }
            self._save_state()

            self.logger.info(f"Ttyd started successfully (PID: {self._process.pid})")
            self.logger.info(f"Access URL: {self.get_access_url()}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to start ttyd: {e}")
            return False

    def stop(self, timeout: int = 10) -> bool:
        """Stop ttyd daemon gracefully.

        Args:
            timeout: Seconds to wait before force kill

        Returns:
            True if stopped successfully
        """
        pid = self._get_pid()
        if not pid:
            self.logger.info("Ttyd is not running")
            return True

        try:
            proc = psutil.Process(pid)

            # Send SIGTERM
            self.logger.info(f"Stopping ttyd (PID: {pid})...")
            proc.terminate()

            # Wait for graceful shutdown
            try:
                proc.wait(timeout=timeout)
                self.logger.info("Ttyd stopped gracefully")
            except psutil.TimeoutExpired:
                self.logger.warning("Ttyd did not stop gracefully, forcing...")
                proc.kill()
                proc.wait(timeout=5)
                self.logger.info("Ttyd force killed")

            # Cleanup
            if self.PID_FILE.exists():
                self.PID_FILE.unlink()

            self.daemon_state = {}
            self._save_state()

            return True

        except psutil.NoSuchProcess:
            self.logger.info("Ttyd process already stopped")
            if self.PID_FILE.exists():
                self.PID_FILE.unlink()
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop ttyd: {e}")
            return False

    def restart(self, session_name: Optional[str] = None) -> bool:
        """Restart ttyd daemon.

        Args:
            session_name: Tmux session to attach to

        Returns:
            True if restarted successfully
        """
        self.logger.info("Restarting ttyd...")
        if self.stop():
            time.sleep(2)
            return self.start(session_name)
        return False

    def get_status(self) -> DaemonStatus:
        """Get current daemon status.

        Returns:
            DaemonStatus object
        """
        pid = self._get_pid()
        running = pid is not None

        status = DaemonStatus(
            running=running,
            pid=pid,
            port=self.config.port,
            ssl_enabled=self.SSL_CERT.exists() and self.SSL_KEY.exists(),
            auth_enabled=self.get_credentials() is not None
        )

        if running and pid:
            try:
                proc = psutil.Process(pid)
                status.uptime_seconds = time.time() - proc.create_time()
                status.started_at = datetime.fromtimestamp(proc.create_time()).isoformat()

                # Count client connections
                connections = [c for c in proc.connections() if c.status == 'ESTABLISHED']
                status.client_count = len(connections)

            except psutil.NoSuchProcess:
                status.running = False
                status.pid = None

        if running:
            status.access_url = self.get_access_url()
            status.last_health_check = datetime.now().isoformat()

        return status

    def get_access_url(self) -> Optional[str]:
        """Get web access URL.

        Returns:
            HTTPS URL or None if not running
        """
        if not self._get_pid():
            return None

        protocol = "https" if self.SSL_CERT.exists() else "http"

        # Use localhost by default, or actual interface if specified
        if self.config.interface == "0.0.0.0":
            host = "localhost"
        else:
            host = self.config.interface

        return f"{protocol}://{host}:{self.config.port}/"

    def health_check(self) -> bool:
        """Perform health check on daemon.

        Returns:
            True if healthy
        """
        pid = self._get_pid()
        if not pid:
            return False

        try:
            proc = psutil.Process(pid)

            # Check if process is responsive
            if proc.status() == psutil.STATUS_ZOMBIE:
                self.logger.error("Ttyd process is zombie")
                return False

            # Check if port is listening
            if not self._port_in_use(self.config.port):
                self.logger.error(f"Ttyd not listening on port {self.config.port}")
                return False

            return True

        except psutil.NoSuchProcess:
            return False

    def auto_restart_if_unhealthy(self) -> bool:
        """Auto-restart daemon if unhealthy.

        Returns:
            True if healthy or restarted successfully
        """
        if self.health_check():
            return True

        self.logger.warning("Ttyd health check failed, attempting restart...")
        return self.restart()


def main():
    """Test ttyd manager functionality."""
    manager = TtydManager()

    print("Ttyd Manager Status:")
    print("=" * 60)

    status = manager.get_status()
    print(f"Running: {status.running}")
    print(f"PID: {status.pid}")
    print(f"Port: {status.port}")
    print(f"SSL Enabled: {status.ssl_enabled}")
    print(f"Auth Enabled: {status.auth_enabled}")

    if status.running:
        print(f"Uptime: {status.uptime_seconds:.1f}s")
        print(f"Clients: {status.client_count}")
        print(f"Access URL: {status.access_url}")

    print()

    # Show credentials if available
    creds = manager.get_credentials()
    if creds:
        username, password = creds
        print(f"Username: {username}")
        print(f"Password: {password}")
        print()


if __name__ == "__main__":
    main()
