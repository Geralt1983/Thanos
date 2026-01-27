"""
Dashboard Configuration.

Provides configuration management for the Thanos dashboard, including
MCP server connections and dashboard settings.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class DashboardConfig(BaseModel):
    """Dashboard application configuration."""

    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8001, description="API server port")
    debug: bool = Field(default=False, description="Debug mode")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins"
    )


class MCPServerPaths(BaseModel):
    """Paths to MCP server executables."""

    workos_mcp: Path
    oura_mcp: Optional[Path] = None

    @classmethod
    def from_env(cls) -> "MCPServerPaths":
        """
        Create MCP server paths from environment or defaults.

        Returns:
            MCPServerPaths with resolved paths
        """
        # Get project root (parent of dashboard directory)
        project_root = Path(__file__).parent.parent

        # WorkOS MCP path
        workos_path = os.getenv("WORKOS_MCP_PATH")
        if workos_path:
            workos_mcp = Path(workos_path)
        else:
            workos_mcp = project_root / "mcp-servers" / "workos-mcp" / "dist" / "index.js"

        # Oura MCP path
        oura_path = os.getenv("OURA_MCP_PATH")
        if oura_path:
            oura_mcp = Path(oura_path)
        else:
            # Default Oura MCP location
            oura_mcp = Path.home() / "mcp-servers" / "oura-mcp" / "build" / "index.js"
            # Only set if it exists
            if not oura_mcp.exists():
                oura_mcp = None

        return cls(workos_mcp=workos_mcp, oura_mcp=oura_mcp)


class Config:
    """
    Global configuration for the dashboard application.

    Loads configuration from environment variables with sensible defaults.
    """

    def __init__(self):
        """Initialize configuration from environment."""
        self.dashboard = DashboardConfig(
            host=os.getenv("DASHBOARD_HOST", "0.0.0.0"),
            port=int(os.getenv("DASHBOARD_PORT", "8001")),
            debug=os.getenv("DEBUG", "false").lower() == "true",
            cors_origins=self._parse_cors_origins()
        )
        self.mcp_paths = MCPServerPaths.from_env()

    def _parse_cors_origins(self) -> list[str]:
        """
        Parse CORS origins from environment.

        Returns:
            List of allowed CORS origins
        """
        origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
        return [origin.strip() for origin in origins.split(",")]


# Global configuration instance
config = Config()
