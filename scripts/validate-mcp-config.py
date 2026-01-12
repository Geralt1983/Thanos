#!/usr/bin/env python3
"""
Thanos MCP Configuration Validator
===================================
Validates MCP server configuration for production deployment.

Usage:
    python scripts/validate-mcp-config.py [--config PATH] [--verbose]

Exit codes:
    0 - Configuration is valid
    1 - Configuration has errors
    2 - Configuration has warnings (but is usable)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import re

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    BOLD = '\033[1m'
    NC = '\033[0m'  # No Color


class ValidationResult:
    """Stores validation results"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.checks_passed = 0
        self.checks_total = 0

    def add_error(self, message: str):
        self.errors.append(message)

    def add_warning(self, message: str):
        self.warnings.append(message)

    def add_info(self, message: str):
        self.info.append(message)

    def check(self, condition: bool, success_msg: str, error_msg: str):
        """Track a validation check"""
        self.checks_total += 1
        if condition:
            self.checks_passed += 1
            self.add_info(success_msg)
        else:
            self.add_error(error_msg)

    def check_warning(self, condition: bool, success_msg: str, warning_msg: str):
        """Track a validation check that produces a warning instead of error"""
        self.checks_total += 1
        if condition:
            self.checks_passed += 1
            self.add_info(success_msg)
        else:
            self.add_warning(warning_msg)

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def print_summary(self):
        """Print validation summary"""
        print(f"\n{Colors.BLUE}{Colors.BOLD}Validation Summary{Colors.NC}")
        print("=" * 80)
        print(f"Checks passed: {self.checks_passed}/{self.checks_total}")
        print()

        if self.errors:
            print(f"{Colors.RED}{Colors.BOLD}Errors ({len(self.errors)}):{Colors.NC}")
            for error in self.errors:
                print(f"  {Colors.RED}✗{Colors.NC} {error}")
            print()

        if self.warnings:
            print(f"{Colors.YELLOW}{Colors.BOLD}Warnings ({len(self.warnings)}):{Colors.NC}")
            for warning in self.warnings:
                print(f"  {Colors.YELLOW}!{Colors.NC} {warning}")
            print()

        if self.info and '--verbose' in sys.argv:
            print(f"{Colors.GREEN}{Colors.BOLD}Successful Checks ({len(self.info)}):{Colors.NC}")
            for info in self.info:
                print(f"  {Colors.GREEN}✓{Colors.NC} {info}")
            print()

        if self.is_valid():
            if self.has_warnings():
                print(f"{Colors.YELLOW}Configuration is valid but has warnings{Colors.NC}")
            else:
                print(f"{Colors.GREEN}Configuration is valid!{Colors.NC}")
        else:
            print(f"{Colors.RED}Configuration has errors and needs to be fixed{Colors.NC}")


class MCPConfigValidator:
    """Validates MCP configuration"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.result = ValidationResult()

    def validate_all(self) -> ValidationResult:
        """Run all validation checks"""
        print(f"{Colors.BLUE}Validating MCP Configuration{Colors.NC}")
        print("=" * 80)
        print()

        self.validate_environment()
        self.validate_config_files()
        self.validate_mcp_servers()
        self.validate_security()
        self.validate_dependencies()

        return self.result

    def validate_environment(self):
        """Validate environment variables"""
        print(f"{Colors.BLUE}1. Checking Environment Variables{Colors.NC}")
        print("-" * 80)

        # Check .env file exists
        env_file = self.project_root / '.env'
        self.result.check(
            env_file.exists(),
            ".env file exists",
            ".env file not found. Copy .env.example to .env and fill in your credentials"
        )

        if not env_file.exists():
            print()
            return

        # Load .env file
        env_vars = self.load_env_file(env_file)

        # Required variables
        required_vars = [
            ('ANTHROPIC_API_KEY', 'Claude AI API key'),
            ('NEO4J_URI', 'Neo4j database URI'),
            ('NEO4J_USERNAME', 'Neo4j username'),
            ('NEO4J_PASSWORD', 'Neo4j password'),
            ('OPENAI_API_KEY', 'OpenAI API key for embeddings'),
        ]

        for var, description in required_vars:
            value = env_vars.get(var) or os.getenv(var)
            self.result.check(
                bool(value and value.strip() and not value.startswith('your-') and not value.startswith('sk-ant-api03-...')),
                f"{var} is set",
                f"{var} is not set or has placeholder value ({description})"
            )

        # Optional but recommended for WorkOS
        workos_db = env_vars.get('WORKOS_DATABASE_URL') or env_vars.get('DATABASE_URL')
        self.result.check_warning(
            bool(workos_db and workos_db.strip() and not 'user:password@host' in workos_db),
            "WORKOS_DATABASE_URL is configured",
            "WORKOS_DATABASE_URL not configured. WorkOS MCP server will not work."
        )

        # Check for accidentally committed secrets
        for var_name, var_value in env_vars.items():
            if var_value and ('sk-' in var_value or 'neo4j+s://' in var_value):
                self.result.add_warning(
                    f"Ensure {var_name} is not committed to version control"
                )

        print()

    def validate_config_files(self):
        """Validate MCP configuration files"""
        print(f"{Colors.BLUE}2. Checking Configuration Files{Colors.NC}")
        print("-" * 80)

        # Check .mcp.json
        mcp_config = self.project_root / '.mcp.json'
        if not mcp_config.exists():
            # Check for example file
            example = self.project_root / '.mcp.json.example'
            self.result.check_warning(
                False,
                ".mcp.json exists",
                ".mcp.json not found. Copy .mcp.json.example to .mcp.json to configure MCP servers"
            )
            print()
            return

        self.result.add_info(".mcp.json file found")

        # Validate JSON syntax
        try:
            with open(mcp_config, 'r') as f:
                config = json.load(f)
            self.result.add_info(".mcp.json has valid JSON syntax")
        except json.JSONDecodeError as e:
            self.result.add_error(f".mcp.json has invalid JSON: {e}")
            print()
            return

        # Validate structure
        self.result.check(
            'mcpServers' in config,
            ".mcp.json has 'mcpServers' section",
            ".mcp.json missing 'mcpServers' section"
        )

        if 'mcpServers' in config:
            servers = config['mcpServers']
            self.result.add_info(f"Found {len(servers)} MCP server(s) configured")

            # Check each server
            for server_name, server_config in servers.items():
                self.validate_server_config(server_name, server_config)

        # Check global config section
        if 'config' in config:
            global_config = config['config']
            self.validate_global_config(global_config)

        print()

    def validate_server_config(self, name: str, config: Dict[str, Any]):
        """Validate individual server configuration"""
        # Required fields
        if 'type' not in config:
            self.result.add_error(f"Server '{name}': missing 'type' field")
            return

        transport_type = config['type']
        if transport_type not in ['stdio', 'sse', 'http']:
            self.result.add_error(
                f"Server '{name}': invalid transport type '{transport_type}'. "
                f"Must be 'stdio', 'sse', or 'http'"
            )

        # Validate stdio transport
        if transport_type == 'stdio':
            if 'command' not in config:
                self.result.add_error(f"Server '{name}': stdio transport missing 'command'")
            else:
                self.result.add_info(f"Server '{name}': stdio transport configured")

        # Validate SSE transport
        elif transport_type == 'sse':
            if 'url' not in config:
                self.result.add_error(f"Server '{name}': SSE transport missing 'url'")
            else:
                url = config['url']
                if not url.startswith('http://') and not url.startswith('https://'):
                    self.result.add_warning(f"Server '{name}': URL should use https:// in production")
                self.result.add_info(f"Server '{name}': SSE transport configured")

        # Check enabled status
        enabled = config.get('enabled', False)
        if enabled:
            self.result.add_info(f"Server '{name}': enabled")
        else:
            self.result.add_info(f"Server '{name}': disabled")

    def validate_global_config(self, config: Dict[str, Any]):
        """Validate global configuration section"""
        # Security settings
        if 'security' in config:
            security = config['security']

            # Check SSL validation
            validate_ssl = security.get('validate_ssl', True)
            if not validate_ssl:
                self.result.add_warning(
                    "SSL validation is disabled. This is insecure for production!"
                )
            else:
                self.result.add_info("SSL validation enabled")

            # Check remote servers
            allow_remote = security.get('allow_remote_servers', True)
            if allow_remote:
                self.result.add_info("Remote MCP servers allowed")
            else:
                self.result.add_info("Remote MCP servers disabled (local only)")

        # Logging settings
        if 'logging' in config:
            logging = config['logging']

            # Check sensitive data sanitization
            sanitize = logging.get('sanitize_sensitive_data', True)
            if not sanitize:
                self.result.add_warning(
                    "Sensitive data sanitization disabled. Credentials may leak into logs!"
                )
            else:
                self.result.add_info("Sensitive data sanitization enabled")

    def validate_mcp_servers(self):
        """Validate MCP server installations"""
        print(f"{Colors.BLUE}3. Checking MCP Server Installations{Colors.NC}")
        print("-" * 80)

        # Check WorkOS MCP server
        workos_path = self.project_root / 'mcp-servers' / 'workos-mcp' / 'dist' / 'index.js'
        if workos_path.exists():
            self.result.add_info("WorkOS MCP server is built and ready")
        else:
            self.result.check_warning(
                False,
                "WorkOS MCP server built",
                "WorkOS MCP server not built. Run: cd mcp-servers/workos-mcp && npm install && npm run build"
            )

        # Check Node.js for third-party servers
        import subprocess
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.result.add_info(f"Node.js installed: {version}")
            else:
                self.result.add_warning("Node.js not working properly")
        except (subprocess.SubprocessError, FileNotFoundError):
            self.result.add_warning(
                "Node.js not found. Third-party MCP servers will not work."
            )

        # Check npx
        try:
            result = subprocess.run(['npx', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.result.add_info("npx is available for third-party servers")
            else:
                self.result.add_warning("npx not working properly")
        except (subprocess.SubprocessError, FileNotFoundError):
            self.result.add_warning("npx not found. Some MCP servers may not work.")

        print()

    def validate_security(self):
        """Validate security configuration"""
        print(f"{Colors.BLUE}4. Checking Security Configuration{Colors.NC}")
        print("-" * 80)

        # Check .gitignore
        gitignore = self.project_root / '.gitignore'
        if gitignore.exists():
            with open(gitignore, 'r') as f:
                gitignore_content = f.read()

            # Check important patterns
            patterns = {
                '.env': '.env file',
                '*.log': 'log files',
                '.mcp.json': 'MCP configuration (if contains secrets)',
            }

            for pattern, description in patterns.items():
                if pattern in gitignore_content or pattern.replace('*', '') in gitignore_content:
                    self.result.add_info(f"gitignore includes {description}")
                elif pattern == '.env':
                    self.result.add_error(f".gitignore missing '{pattern}' - {description} may be committed!")
                else:
                    self.result.add_warning(f".gitignore missing '{pattern}' - {description} may be committed")
        else:
            self.result.add_warning(".gitignore not found")

        # Check file permissions on sensitive files
        env_file = self.project_root / '.env'
        if env_file.exists():
            import stat
            mode = env_file.stat().st_mode
            # Check if readable by others
            if mode & stat.S_IROTH:
                self.result.add_warning(".env file is readable by others. Run: chmod 600 .env")
            else:
                self.result.add_info(".env file has secure permissions")

        print()

    def validate_dependencies(self):
        """Validate Python dependencies"""
        print(f"{Colors.BLUE}5. Checking Python Dependencies{Colors.NC}")
        print("-" * 80)

        # Check MCP SDK
        try:
            import mcp
            version = getattr(mcp, '__version__', 'unknown')
            self.result.add_info(f"MCP Python SDK installed (version: {version})")
        except ImportError:
            self.result.add_error(
                "MCP Python SDK not installed. Run: pip install mcp>=1.0.0"
            )

        # Check other required packages
        required_packages = [
            ('pydantic', 'Data validation'),
            ('jsonschema', 'JSON Schema validation'),
        ]

        for package, description in required_packages:
            try:
                __import__(package)
                self.result.add_info(f"{package} installed ({description})")
            except ImportError:
                self.result.add_error(
                    f"{package} not installed ({description}). Run: pip install -r requirements.txt"
                )

        print()

    def load_env_file(self, path: Path) -> Dict[str, str]:
        """Load environment variables from .env file"""
        env_vars = {}
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        return env_vars


def main():
    """Main validation entry point"""
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check for --config argument
    if '--config' in sys.argv:
        idx = sys.argv.index('--config')
        if idx + 1 < len(sys.argv):
            project_root = Path(sys.argv[idx + 1])

    print(f"Project root: {project_root}\n")

    # Run validation
    validator = MCPConfigValidator(project_root)
    result = validator.validate_all()

    # Print summary
    result.print_summary()

    # Exit with appropriate code
    if not result.is_valid():
        sys.exit(1)
    elif result.has_warnings():
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
