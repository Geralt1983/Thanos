
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(os.getcwd())))

from Tools.thanos_orchestrator import ThanosOrchestrator, Command

def test_prompt_content():
    orchestrator = ThanosOrchestrator()
    # Mock context loading implies we should see CORE.md content
    # We need to make sure the orchestrator loaded the updated CORE.md
    # Since we are initializing a new instance, it should load from disk
    
    # We need a command to generate prompt
    cmd = Command(
        name="pa:daily",
        description="Daily Briefing",
        parameters=[],
        workflow="Workflow steps",
        content="Content",
        file_path="mock_path"
    )
    
    prompt = orchestrator._build_system_prompt(command=cmd)
    
    print("--- PROMPT CHECK ---")
    
    # Check 1: Source Attribution
    if "## About Jeremy (Source: Context/CORE.md)" in prompt:
        print("[PASS] Source attribution for CORE.md found")
    else:
        print("[FAIL] Source attribution for CORE.md NOT found")
        
    if "## Today's State (Source: State/Today.md)" in prompt:
        print("[PASS] Source attribution for Today.md found")
    else:
        print("[FAIL] Source attribution for Today.md NOT found")

    # Check 2: Content
    if "Current focus: Thanos Development" in prompt:
        print("[PASS] Updated Current Focus found")
    else:
        print("[FAIL] Updated Current Focus NOT found")
        
    if "Current focus: Memphis" not in prompt:
         print("[PASS] 'Current focus: Memphis' NOT found (Correct)")
    else:
         print(f"[FAIL] Found stale 'Current focus: Memphis' in prompt")

    # Check 3: Reference existence
    if "Active clients: Memphis" in prompt:
        print("[PASS] Memphis still listed in Active Clients (Reference) as requested")
    else:
        print("[FAIL] Memphis removed from Active Clients (Should have been kept)")

if __name__ == "__main__":
    test_prompt_content()
