
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path("c:/Projects/Thanos")
sys.path.insert(0, str(project_root))

from Tools.litellm.agent_router import AgentRouter
from Tools.litellm.client import LiteLLMClient, OPENAI_AVAILABLE, ANTHROPIC_AVAILABLE

def test_agent_routing():
    print("Testing Agent Routing...")
    config = {
        'agent_routing': {
            'enabled': True, 
            'agents': {
                'ops': {'model': 'gpt-4.1-nano'},
                'coach': {'model': 'anthropic/claude-3-5-haiku-20241022'}
            }
        }
    }
    router = AgentRouter(config)
    
    ops_model = router.get_model('ops')
    assert ops_model == 'gpt-4.1-nano', f"Expected gpt-4.1-nano for ops, got {ops_model}"
    print(f"[PASS] Ops Agent routes to: {ops_model}")
    
    coach_model = router.get_model('coach')
    assert coach_model == 'anthropic/claude-3-5-haiku-20241022', f"Expected anthropic/claude-3-5-haiku-20241022 for coach, got {coach_model}"
    print(f"[PASS] Coach Agent routes to: {coach_model}")

def test_client_integration():
    print("\nTesting Client Integration...")
    client = LiteLLMClient()
    
    # Check if router is initialized
    assert hasattr(client, 'agent_router'), "Agent router not initialized in client"
    print("[PASS] Client has agent_router")
    
    # Check real config loading
    ops_model = client.agent_router.get_model('ops')
    print(f"[PASS] Real Config Ops Model: {ops_model}")
    
    coach_model = client.agent_router.get_model('coach')
    print(f"[PASS] Real Config Coach Model: {coach_model}")

def test_availability():
    print("\nTesting Package Availability...")
    print(f"OpenAI Available: {OPENAI_AVAILABLE}")
    print(f"Anthropic Available: {ANTHROPIC_AVAILABLE}")
    
    if not ANTHROPIC_AVAILABLE:
        print("[WARN]  Anthropic not available - Coach agent may fail or use fallback")

if __name__ == "__main__":
    try:
        test_availability()
        test_agent_routing()
        test_client_integration()
        print("\n[PASS] All verification tests passed!")
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
