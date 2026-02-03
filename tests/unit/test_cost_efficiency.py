#!/usr/bin/env python3
"""
Unit tests for Cost Efficiency and Model Routing.

This module tests the intelligent routing logic and cost calculation accuracy
of the LiteLLMClient to ensure the system optimizes for cost efficiency.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from Tools.litellm.client import LiteLLMClient
from Tools.litellm.complexity_analyzer import ComplexityAnalyzer
from Tools.litellm.usage_tracker import UsageTracker

class TestCostEfficiency(unittest.TestCase):
    def setUp(self):
        # Mock configuration
        self.mock_config = {
            "litellm": {
                "default_model": "anthropic/claude-opus-4-5",
                "fallback_chain": ["anthropic/claude-opus-4-5", "gpt-4-turbo"],
            },
            "model_routing": {
                "rules": {
                    "complex": {"model": "anthropic/claude-sonnet-4-5", "min_complexity": 0.7},
                    "standard": {"model": "anthropic/claude-3-5-haiku-20241022", "min_complexity": 0.3},
                    "simple": {"model": "gpt-4.1-nano", "max_complexity": 0.3}
                },
                "complexity_factors": {
                    "token_count_weight": 0.3,
                    "keyword_weight": 0.4,
                    "history_length_weight": 0.3
                }
            },
            "usage_tracking": {
                "enabled": True, 
                "storage_path": "State/usage.json",
                "pricing": {
                    "gpt-4.1-nano": {"input": 0.0002, "output": 0.0008},
                    "anthropic/claude-sonnet-4-5": {"input": 0.003, "output": 0.015},
                    "anthropic/claude-opus-4-5": {"input": 0.015, "output": 0.075}
                }
            },
            "caching": {"enabled": False}  # Disable cache for these tests
        }
        
    def test_routing_simple_query(self):
        """Test that simple queries route to the cheapest model."""
        analyzer = ComplexityAnalyzer(self.mock_config["model_routing"])
        
        # Simple query: "What time is it?"
        # Keywords: None (neutral 0.5 * 0.4 = 0.2)
        # Length: Negligible
        # History: 0
        # Total: ~0.2 -> Simple (<0.3)
        complexity, tier = analyzer.analyze("What time is it?")
        
        self.assertEqual(tier, "simple")
        self.assertLess(complexity, 0.3)
        
        # Verify mapping
        rule = self.mock_config["model_routing"]["rules"][tier]
        self.assertEqual(rule["model"], "gpt-4.1-nano")

    def test_routing_complex_query(self):
        """Test that complex queries route to the most capable model."""
        analyzer = ComplexityAnalyzer(self.mock_config["model_routing"])
        
        # Complex query needs to hit >0.7
        # Keywords (weight 0.4): "analyze", "architecture", "comprehensive", "step by step"
        #   Score: (4 * 0.2) + 0.5 = 1.3 -> 1.0 * 0.4 = 0.4 contribution
        # To get > 0.7, we need 0.3 more from other factors.
        # Let's add history (weight 0.3). 10 messages = 1.0 * 0.3 = 0.3 contribution
        # Total = 0.4 + 0.3 = 0.7 -> Complex
        
        query = "Analyze the architectural differences and provide a step by step comprehensive plan."
        history = [{"role": "user", "content": "msg"}] * 10
        
        complexity, tier = analyzer.analyze(query, history)
        
        self.assertEqual(tier, "complex")
        self.assertGreaterEqual(complexity, 0.7)
        
        # Verify mapping
        rule = self.mock_config["model_routing"]["rules"][tier]
        self.assertEqual(rule["model"], "anthropic/claude-sonnet-4-5")

    def test_routing_standard_query(self):
        """Test that standard queries route to the balanced model."""
        analyzer = ComplexityAnalyzer(self.mock_config["model_routing"])
        
        # Standard query needs 0.3 <= score < 0.7
        # "Draft an email" -> keywords neutral (0.5 * 0.4 = 0.2)
        # Needs 0.1 more to reach 0.3.
        # Add some length? 
        # Or add a complex keyword: "explain" -> (1*0.2 + 0.5) = 0.7 * 0.4 = 0.28
        # Still just under. 
        # Let's use "explain" and some history.
        
        query = "Explain the meeting notes."
        # History: 2 messages -> 0.2 * 0.3 = 0.06
        # Total: 0.28 + 0.06 = 0.34 -> Standard
        
        history = [{"role": "user", "content": "msg"}] * 2
        complexity, tier = analyzer.analyze(query, history)
        
        self.assertEqual(tier, "standard")
        self.assertTrue(0.3 <= complexity < 0.7)
        
        # Verify mapping
        rule = self.mock_config["model_routing"]["rules"][tier]
        self.assertEqual(rule["model"], "anthropic/claude-3-5-haiku-20241022")

    def test_cost_calculation_accuracy(self):
        """Test that usage tracker calculates costs correctly with configured pricing."""
        with patch("pathlib.Path.mkdir"), patch("pathlib.Path.exists", return_value=True), patch("pathlib.Path.write_text"), patch("pathlib.Path.read_text", return_value='{"sessions": [], "daily_totals": {}}'):
            tracker = UsageTracker("State/usage.json", self.mock_config["usage_tracking"]["pricing"])
            
            # Case 1: Nano (Cheap)
            # 1000 in, 1000 out -> $0.0002 + $0.0008 = $0.001
            cost_nano = tracker.calculate_cost("gpt-4.1-nano", 1000, 1000)
            self.assertAlmostEqual(cost_nano, 0.001)
            
            # Case 2: Sonnet (Standard)
            # 1000 in, 1000 out -> $0.003 + $0.015 = $0.018
            cost_sonnet = tracker.calculate_cost("anthropic/claude-sonnet-4-5", 1000, 1000)
            self.assertAlmostEqual(cost_sonnet, 0.018)
            
            # Case 3: Opus (Expensive)
            # 1000 in, 1000 out -> $0.015 + $0.075 = $0.090
            cost_opus = tracker.calculate_cost("anthropic/claude-opus-4-5", 1000, 1000)
            self.assertAlmostEqual(cost_opus, 0.090)

    @patch("Tools.litellm.client.LiteLLMClient._load_config")
    @patch("Tools.litellm.client.LiteLLMClient._call_with_fallback")
    @patch("Tools.litellm.client.LITELLM_AVAILABLE", False) # Disable LiteLLM to avoid init issues
    def test_client_integration(self, mock_call, mock_load_config):
        """Integration test using the full client mock to verify end-to-end routing flow."""
        mock_load_config.return_value = self.mock_config
        
        # Setup mocks that Client initializes
        with patch("Tools.litellm.client.UsageTracker") as MockTracker, \
             patch("Tools.litellm.client.ResponseCache") as MockCache:
             
            client = LiteLLMClient(config_path="dummy.json")
            
            # Mock the API call return
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_call.return_value = mock_response
            
            # --- Scenario 1: Simple ---
            client.chat("Hi")
            # Verify it called _call_with_fallback with the simple model
            args, kwargs = mock_call.call_args
            self.assertEqual(kwargs['model'], "gpt-4.1-nano")
            
            # --- Scenario 2: Explicit Override ---
            client.chat("Hi", model="explicit-model")
            args, kwargs = mock_call.call_args
            self.assertEqual(kwargs['model'], "explicit-model")

    def test_agent_routing(self):
        """Test that agent-specific routing uses configured models."""
        # Update mock config to match what we just set in api.json for agents
        agent_config = self.mock_config.copy()
        agent_config["agent_routing"] = {
            "enabled": True,
            "agents": {
                "ops": {"model": "anthropic/claude-3-5-haiku-20241022"},
                "strategy": {"model": "anthropic/claude-sonnet-4-5"}
            }
        }
        
        with patch("Tools.litellm.client.LiteLLMClient._load_config", return_value=agent_config), \
             patch("Tools.litellm.client.LiteLLMClient._call_with_fallback") as mock_call, \
             patch("Tools.litellm.client.UsageTracker"), \
             patch("Tools.litellm.client.ResponseCache"), \
             patch("Tools.litellm.client.LITELLM_AVAILABLE", False):
             
            client = LiteLLMClient(config_path="dummy.json")
            
            # Mock the API call return
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Response"
            mock_call.return_value = mock_response
            
            # Test Ops Agent -> Haiku
            client.chat("Task", agent="ops")
            args, kwargs = mock_call.call_args
            self.assertEqual(kwargs['model'], "anthropic/claude-3-5-haiku-20241022")
            
            # Test Strategy Agent -> Sonnet
            client.chat("Plan", agent="strategy")
            args, kwargs = mock_call.call_args
            self.assertEqual(kwargs['model'], "anthropic/claude-sonnet-4-5")

if __name__ == '__main__':
    unittest.main()
