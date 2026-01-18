"""
Unit tests for Thanos Core Services.
Tests AgentService, CommandService, and IntentService.
"""

import unittest
import shutil
import tempfile
from pathlib import Path
from Tools.core.agent_service import AgentService, Agent
from Tools.core.command_service import CommandService, Command
from Tools.core.intent_service import IntentService


class TestCoreServices(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    # ============================================================================
    # AgentService Tests
    # ============================================================================

    def test_agent_loading(self):
        """Test loading agents from markdown files."""
        agents_dir = self.test_dir / "Agents"
        agents_dir.mkdir()
        
        # Create a test agent file
        agent_file = agents_dir / "TestAgent.md"
        agent_file.write_text("""---
name: TestAgent
role: Tester
voice: analytical
triggers: ['test', 'check']
---
This is a test agent.
""", encoding='utf-8')
        
        service = AgentService()
        agents = service.load_agents(agents_dir)
        
        self.assertIn("testagent", agents)
        agent = agents["testagent"]
        self.assertEqual(agent.name, "TestAgent")
        self.assertEqual(agent.role, "Tester")
        self.assertEqual(agent.voice, "analytical")
        self.assertIn("test", agent.triggers)
        self.assertEqual(agent.content, "This is a test agent.")

    def test_agent_loading_malformed(self):
        """Test graceful handling of malformed agent files."""
        agents_dir = self.test_dir / "Agents"
        agents_dir.mkdir()
        (agents_dir / "Bad.md").write_text("Not a valid agent file", encoding='utf-8')
        
        service = AgentService()
        agents = service.load_agents(agents_dir)
        
        # Should load with defaults (name=Bad) even if no frontmatter
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents["bad"].name, "Bad")

    def test_get_agent(self):
        service = AgentService()
        service._agents = {
            "ops": Agent("Ops", "Role", "Voice", [], "Content", "path")
        }
        
        self.assertIsNotNone(service.get_agent("ops"))
        self.assertIsNotNone(service.get_agent("OPS"))  # Case insensitive
        self.assertIsNone(service.get_agent("unknown"))


    # ============================================================================
    # CommandService Tests
    # ============================================================================

    def test_command_loading(self):
        """Test loading commands from markdown files."""
        cmd_dir = self.test_dir / "commands"
        cmd_dir.mkdir()
        subdir = cmd_dir / "pa"
        subdir.mkdir()
        
        cmd_file = subdir / "daily.md"
        cmd_file.write_text("""# /pa:daily - Daily Briefing
Execute daily briefing.

## Parameters
- date: Optional date

## Workflow
1. Check schedule
""", encoding='utf-8')
        
        service = CommandService()
        commands = service.load_commands(cmd_dir)
        
        # Should be accessible by name and prefix:name
        self.assertIn("/pa:daily", commands)
        self.assertIn("daily", commands)
        self.assertIn("pa:daily", commands)

    def test_find_command(self):
        service = CommandService()
        cmd = Command("test:cmd", "Description", [], "Workflow", "Content", "path")
        service._commands = {
            "test:cmd": cmd,
            "cmd": cmd
        }
        
        # Direct match
        self.assertEqual(service.find_command("test:cmd"), cmd)
        
        # Fuzzy match
        self.assertEqual(service.find_command("st:cm"), cmd)  # "st:cm" in "test:cmd"


    # ============================================================================
    # IntentService Tests
    # ============================================================================

    def test_intent_matching(self):
        """Test basic keyword matching."""
        keywords = {
            "ops": {"high": ["task"], "medium": [], "low": []},
            "coach": {"high": ["habit"], "medium": [], "low": []}
        }
        service = IntentService(agent_keywords=keywords)
        service.initialize()
        
        # Exact match high priority
        scores = service.match_intent("I have a task")
        self.assertGreater(scores["ops"], 0)
        self.assertEqual(scores["coach"], 0)
        
        # Best agent
        self.assertEqual(service.find_best_agent("I have a task"), "ops")
        self.assertEqual(service.find_best_agent("I need to build a habit"), "coach")

    def test_intent_fallback(self):
        """Test heuristic fallback."""
        service = IntentService()
        # "what should i do" is hardcoded in fallback
        # Requires agents to be loaded in the service for return
        service._agents = {"ops": Agent("Ops", "", "", [], "", "")}
        
        agent = service.find_agent("What should I do?")
        
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "Ops")

if __name__ == '__main__':
    unittest.main()
