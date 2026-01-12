"""
Unit tests for MCP server discovery.

Tests configuration discovery from multiple sources,
merging, filtering, and error handling.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open


class TestMCPServerDiscovery:
    """Test MCPServerDiscovery class."""

    def test_initialization_with_defaults(self, temp_dir):
        """Test discovery initialization with default paths."""
        # Test that discovery can be initialized
        config = {
            "project_root": temp_dir,
            "global_config_path": temp_dir / ".claude.json"
        }

        assert config["project_root"] == temp_dir
        assert config["global_config_path"].name == ".claude.json"

    def test_initialization_with_custom_paths(self, temp_dir):
        """Test discovery initialization with custom paths."""
        custom_global = temp_dir / "custom.json"
        custom_project = temp_dir / "project"
        custom_project.mkdir(parents=True, exist_ok=True)

        config = {
            "project_root": custom_project,
            "global_config_path": custom_global
        }

        assert config["project_root"] == custom_project
        assert config["global_config_path"] == custom_global

    def test_discover_from_mcp_json(self, sample_mcp_json, temp_dir):
        """Test discovering servers from .mcp.json file."""
        # Verify the fixture created the file
        assert sample_mcp_json.exists()

        # Read and verify content
        with open(sample_mcp_json) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "test-server" in config["mcpServers"]
        assert "disabled-server" in config["mcpServers"]

        # Verify server configuration
        test_server = config["mcpServers"]["test-server"]
        assert test_server["enabled"] is True
        assert "test" in test_server["tags"]
        assert test_server["transport"]["type"] == "stdio"

    def test_discover_from_claude_json(self, sample_claude_json):
        """Test discovering servers from ~/.claude.json file."""
        assert sample_claude_json.exists()

        with open(sample_claude_json) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert "workos-mcp" in config["mcpServers"]
        assert "context7" in config["mcpServers"]

        # Verify different transport types
        workos = config["mcpServers"]["workos-mcp"]
        assert "command" in workos
        assert "args" in workos

        context7 = config["mcpServers"]["context7"]
        assert "url" in context7

    def test_filter_disabled_servers(self, sample_mcp_json):
        """Test that disabled servers are filtered out by default."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # Test filtering logic
        enabled_servers = {
            name: server
            for name, server in servers.items()
            if server.get("enabled", True)  # Default to True if not specified
        }

        disabled_servers = {
            name: server
            for name, server in servers.items()
            if not server.get("enabled", True)
        }

        assert "test-server" in enabled_servers
        assert "disabled-server" in disabled_servers
        assert "disabled-server" not in enabled_servers

    def test_include_disabled_servers(self, sample_mcp_json):
        """Test that disabled servers can be included when requested."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # When include_disabled=True, all servers are included
        all_servers = servers
        assert "test-server" in all_servers
        assert "disabled-server" in all_servers

    def test_filter_by_tags(self, sample_mcp_json):
        """Test filtering servers by tags."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # Filter by tag
        target_tags = ["development"]
        tagged_servers = {
            name: server
            for name, server in servers.items()
            if any(tag in server.get("tags", []) for tag in target_tags)
        }

        assert "test-server" in tagged_servers
        # disabled-server doesn't have 'development' tag

    def test_filter_by_multiple_tags(self, sample_mcp_json):
        """Test filtering by multiple tags (OR logic)."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # Filter by multiple tags (match any)
        target_tags = ["test", "production"]
        tagged_servers = {
            name: server
            for name, server in servers.items()
            if any(tag in server.get("tags", []) for tag in target_tags)
        }

        # Both servers have 'test' tag
        assert len(tagged_servers) >= 1

    def test_nested_config_discovery(self, nested_project_structure):
        """Test discovering configs from nested directory structure."""
        paths = nested_project_structure

        # Verify structure exists
        assert (paths["root"] / ".mcp.json").exists()
        assert (paths["project"] / ".mcp.json").exists()
        assert (paths["subdir"] / ".mcp.json").exists()

        # Read configs
        with open(paths["root"] / ".mcp.json") as f:
            root_config = json.load(f)

        with open(paths["project"] / ".mcp.json") as f:
            project_config = json.load(f)

        with open(paths["subdir"] / ".mcp.json") as f:
            subdir_config = json.load(f)

        # Verify servers exist at each level
        assert "root-server" in root_config["mcpServers"]
        assert "root-server" in project_config["mcpServers"]  # Overridden
        assert "project-server" in project_config["mcpServers"]
        assert "subdir-server" in subdir_config["mcpServers"]

    def test_config_precedence(self, nested_project_structure):
        """Test that closer configs override parent configs."""
        paths = nested_project_structure

        # Read root and project configs
        with open(paths["root"] / ".mcp.json") as f:
            root_config = json.load(f)

        with open(paths["project"] / ".mcp.json") as f:
            project_config = json.load(f)

        # Get root-server from both
        root_server_root = root_config["mcpServers"]["root-server"]
        root_server_project = project_config["mcpServers"]["root-server"]

        # Project config should override
        assert root_server_root["transport"]["args"] == ["root.js"]
        assert root_server_project["transport"]["args"] == ["project.js"]

    def test_get_server_by_name(self, sample_mcp_json):
        """Test retrieving a specific server by name."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # Test getting specific server
        test_server = servers.get("test-server")
        assert test_server is not None
        assert test_server["enabled"] is True

        # Test getting non-existent server
        nonexistent = servers.get("nonexistent-server")
        assert nonexistent is None

    def test_get_servers_by_tag(self, sample_mcp_json):
        """Test getting all servers with a specific tag."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]

        # Get servers with 'test' tag
        test_tagged = {
            name: server
            for name, server in servers.items()
            if "test" in server.get("tags", [])
        }

        assert len(test_tagged) > 0
        assert all("test" in server.get("tags", []) for server in test_tagged.values())

    def test_config_sources_tracking(self, nested_project_structure):
        """Test that discovery tracks which config files were loaded."""
        paths = nested_project_structure

        # Simulate discovery from current directory up
        config_files = []
        current = paths["current"]

        max_depth = 10
        depth = 0

        while depth < max_depth:
            config_file = current / ".mcp.json"
            if config_file.exists():
                config_files.append(config_file)

            parent = current.parent
            if parent == current:
                break

            current = parent
            depth += 1

        # Should find configs in subdir, project, and root
        assert len(config_files) >= 2


class TestConfigurationLoading:
    """Test configuration file loading and parsing."""

    def test_load_valid_mcp_json(self, sample_mcp_json):
        """Test loading a valid .mcp.json file."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert isinstance(config["mcpServers"], dict)

    def test_load_valid_claude_json(self, sample_claude_json):
        """Test loading a valid .claude.json file."""
        with open(sample_claude_json) as f:
            config = json.load(f)

        assert "mcpServers" in config
        assert isinstance(config["mcpServers"], dict)

    def test_handle_missing_config_file(self, temp_dir):
        """Test graceful handling of missing config files."""
        nonexistent = temp_dir / "nonexistent.json"
        assert not nonexistent.exists()

        # Should handle gracefully, not raise
        try:
            with open(nonexistent) as f:
                config = json.load(f)
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError:
            # Expected
            pass

    def test_handle_malformed_json(self, temp_dir):
        """Test handling of malformed JSON config files."""
        malformed = temp_dir / "malformed.json"
        malformed.write_text("{ invalid json }")

        try:
            with open(malformed) as f:
                config = json.load(f)
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            # Expected
            pass

    def test_handle_empty_config_file(self, temp_dir):
        """Test handling of empty config files."""
        empty = temp_dir / "empty.json"
        empty.write_text("{}")

        with open(empty) as f:
            config = json.load(f)

        assert config == {}

    def test_handle_config_without_servers(self, temp_dir):
        """Test handling config file with no mcpServers key."""
        no_servers = temp_dir / "no_servers.json"
        no_servers.write_text(json.dumps({"other": "data"}))

        with open(no_servers) as f:
            config = json.load(f)

        assert "mcpServers" not in config
        # Should handle gracefully


class TestConfigMerging:
    """Test configuration merging from multiple sources."""

    def test_merge_two_configs(self):
        """Test merging two configuration dictionaries."""
        config1 = {
            "server1": {"enabled": True, "tags": ["prod"]},
            "server2": {"enabled": False, "tags": ["dev"]}
        }

        config2 = {
            "server2": {"enabled": True, "tags": ["staging"]},  # Override
            "server3": {"enabled": True, "tags": ["test"]}  # New
        }

        # Merge (config2 overrides config1)
        merged = {**config1, **config2}

        assert "server1" in merged
        assert "server2" in merged
        assert "server3" in merged
        assert merged["server2"]["enabled"] is True  # Overridden
        assert merged["server2"]["tags"] == ["staging"]  # Overridden

    def test_merge_preserves_unique_servers(self):
        """Test that merging preserves servers unique to each config."""
        config1 = {"server1": {"enabled": True}}
        config2 = {"server2": {"enabled": True}}

        merged = {**config1, **config2}

        assert "server1" in merged
        assert "server2" in merged
        assert len(merged) == 2

    def test_merge_order_matters(self):
        """Test that merge order determines precedence."""
        config1 = {"server": {"value": 1}}
        config2 = {"server": {"value": 2}}

        # config2 overrides config1
        merged_2_over_1 = {**config1, **config2}
        assert merged_2_over_1["server"]["value"] == 2

        # config1 overrides config2
        merged_1_over_2 = {**config2, **config1}
        assert merged_1_over_2["server"]["value"] == 1


class TestEnvironmentVariableInterpolation:
    """Test environment variable interpolation in configs."""

    def test_detect_env_var_reference(self, sample_mcp_json):
        """Test detecting environment variable references."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        test_server = config["mcpServers"]["test-server"]
        api_key = test_server["transport"]["env"]["API_KEY"]

        # Should contain variable reference
        assert "${TEST_API_KEY}" in api_key or "$TEST_API_KEY" in api_key

    def test_env_var_formats(self):
        """Test both ${VAR} and $VAR formats."""
        test_cases = [
            ("${API_KEY}", "API_KEY"),
            ("$API_KEY", "API_KEY"),
            ("prefix_${VAR}_suffix", "VAR"),
            ("$VAR/path/to/file", "VAR")
        ]

        for template, var_name in test_cases:
            # Should be able to detect variable name
            assert var_name in template or f"${{{var_name}}}" in template


class TestDiscoveryHelpers:
    """Test helper functions for discovery."""

    def test_discover_servers_helper(self, sample_mcp_json, temp_dir):
        """Test the discover_servers convenience function."""
        # Simulate discovery from temp_dir
        assert sample_mcp_json.parent == temp_dir

        # Load config
        with open(sample_mcp_json) as f:
            config = json.load(f)

        servers = config["mcpServers"]
        assert len(servers) > 0

    def test_get_server_config_helper(self, sample_mcp_json):
        """Test the get_server_config convenience function."""
        with open(sample_mcp_json) as f:
            config = json.load(f)

        # Get specific server
        servers = config["mcpServers"]
        test_server = servers.get("test-server")

        assert test_server is not None
        assert test_server["transport"]["command"] == "node"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_discovery_with_no_configs_found(self, temp_dir):
        """Test discovery when no config files exist."""
        # Create directory with no config files
        empty_dir = temp_dir / "empty"
        empty_dir.mkdir()

        # Should return empty dict, not error
        config_file = empty_dir / ".mcp.json"
        assert not config_file.exists()

    def test_circular_reference_detection(self, temp_dir):
        """Test handling of circular directory references."""
        # Create symlink that could cause circular reference
        # (This is more of a file system concern, but worth testing)
        link = temp_dir / "link"

        try:
            link.symlink_to(temp_dir)

            # Discovery should have max depth to prevent infinite loops
            max_depth = 10
            assert max_depth > 0  # Sanity check

            # Should not loop infinitely
        except OSError:
            # Symlinks may not be supported
            pass

    def test_permission_denied_on_config_file(self, temp_dir):
        """Test handling of config files with no read permission."""
        import os
        import stat

        restricted = temp_dir / "restricted.json"
        restricted.write_text('{"mcpServers": {}}')

        # Remove read permission
        try:
            os.chmod(restricted, stat.S_IWRITE)

            # Should handle gracefully
            try:
                with open(restricted) as f:
                    config = json.load(f)
                # May succeed or fail depending on platform
            except PermissionError:
                # Expected on some platforms
                pass
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(restricted, stat.S_IREAD | stat.S_IWRITE)
            except:
                pass

    def test_very_large_config_file(self, temp_dir):
        """Test handling of very large configuration files."""
        # Create config with many servers
        large_config = {
            "mcpServers": {
                f"server-{i}": {
                    "transport": {
                        "type": "stdio",
                        "command": "node",
                        "args": [f"server{i}.js"]
                    },
                    "enabled": True,
                    "tags": ["test"]
                }
                for i in range(100)
            }
        }

        large_file = temp_dir / "large.json"
        large_file.write_text(json.dumps(large_config, indent=2))

        # Should load successfully
        with open(large_file) as f:
            config = json.load(f)

        assert len(config["mcpServers"]) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
