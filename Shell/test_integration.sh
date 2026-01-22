#!/usr/bin/env bash
# Thanos Shell Identity Integration Test Suite
# Tests: Voice, Visuals, Notifications, CLI routing

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

echo "╔════════════════════════════════════════════════╗"
echo "║  THANOS SHELL IDENTITY INTEGRATION TEST SUITE  ║"
echo "╚════════════════════════════════════════════════╝"
echo

# Helper functions
print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

print_skip() {
    echo -e "${YELLOW}[SKIP]${NC} $1"
    ((TESTS_SKIPPED++))
}

print_section() {
    echo
    echo "═══════════════════════════════════════════════"
    echo "  $1"
    echo "═══════════════════════════════════════════════"
    echo
}

# Check dependencies
check_dependencies() {
    print_section "DEPENDENCY CHECK"

    # Python 3
    if command -v python3 &> /dev/null; then
        print_pass "Python 3 installed: $(python3 --version)"
    else
        print_fail "Python 3 not found"
        exit 1
    fi

    # Python modules
    print_test "Checking Python dependencies..."
    python3 -c "import json, os, sys, subprocess, datetime" 2>/dev/null && \
        print_pass "Core Python modules available" || \
        print_fail "Missing core Python modules"

    # Optional: say command (macOS)
    if command -v say &> /dev/null; then
        print_pass "macOS 'say' command available"
    else
        print_skip "macOS 'say' command not available (voice will be skipped)"
    fi

    # Optional: Kitty
    if command -v kitty &> /dev/null; then
        print_pass "Kitty terminal available"
    else
        print_skip "Kitty terminal not available (visuals will be limited)"
    fi

    # Optional: osascript (macOS notifications)
    if command -v osascript &> /dev/null; then
        print_pass "macOS osascript available (notifications supported)"
    else
        print_skip "macOS osascript not available (notifications limited)"
    fi
}

# Test 1: Voice Synthesis
test_voice() {
    print_section "TEST 1: VOICE SYNTHESIS"

    if ! command -v say &> /dev/null; then
        print_skip "Voice synthesis test (macOS 'say' command not available)"
        return
    fi

    print_test "Testing VoiceSynthesizer initialization..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.voice import VoiceSynthesizer
    voice = VoiceSynthesizer()
    print("VoiceSynthesizer initialized")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "VoiceSynthesizer initialization"
    else
        print_fail "VoiceSynthesizer initialization"
        return
    fi

    print_test "Testing voice cache stats..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.voice import VoiceSynthesizer
    voice = VoiceSynthesizer()
    stats = voice.cache_stats()
    print(f"Voice cache: {stats['file_count']} files, {stats['total_size_mb']:.2f} MB")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Voice cache stats"
    else
        print_fail "Voice cache stats"
    fi

    print_test "Testing voice synthesize function (dry run)..."
    python3 <<EOF
import sys, os
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.voice import synthesize
    # Don't actually synthesize without API key
    api_key = os.getenv('ELEVENLABS_API_KEY')
    if api_key:
        result = synthesize("Test", play=False)
        print(f"Voice synthesis completed: {result}")
    else:
        print("Voice synthesis skipped (no API key) - this is expected")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Voice synthesize function"
    else
        print_fail "Voice synthesize function"
    fi
}

# Test 2: Visual State System
test_visuals() {
    print_section "TEST 2: VISUAL STATE SYSTEM"

    print_test "Testing ThanosVisualState initialization..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.visuals import ThanosVisualState
    vsm = ThanosVisualState()
    print(f"ThanosVisualState initialized, current state: {vsm.get_current_state()}")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "ThanosVisualState initialization"
    else
        print_fail "ThanosVisualState initialization"
        return
    fi

    print_test "Testing state transitions..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.visuals import ThanosVisualState
    vsm = ThanosVisualState()

    states = ['CHAOS', 'FOCUS', 'BALANCE']
    for state in states:
        result = vsm.set_state(state)
        current = vsm.get_current_state()
        if current != state:
            print(f"State mismatch: expected {state}, got {current}")
            sys.exit(1)
        print(f"✓ Transitioned to {state}")

    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "State transitions (CHAOS → FOCUS → BALANCE)"
    else
        print_fail "State transitions"
    fi

    print_test "Testing wallpaper file resolution..."
    python3 <<EOF
import sys, os
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.visuals import ThanosVisualState
    vsm = ThanosVisualState()

    wallpapers = {
        'CHAOS': 'nebula_storm.png',
        'FOCUS': 'infinity_gauntlet_fist.png',
        'BALANCE': 'farm_sunrise.png'
    }

    wallpaper_dir = os.path.expanduser('~/.thanos/wallpapers')
    missing = []
    for state, filename in wallpapers.items():
        path = os.path.join(wallpaper_dir, filename)
        if not os.path.exists(path):
            missing.append(filename)

    if missing:
        print(f"Missing wallpapers: {', '.join(missing)}")
        print("Run ./Shell/setup_wallpapers.sh to create placeholders")
        sys.exit(1)
    else:
        print("All wallpaper files present")
        sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Wallpaper file resolution"
    else
        print_fail "Wallpaper files missing (run ./Shell/setup_wallpapers.sh)"
    fi
}

# Test 3: Notification System
test_notifications() {
    print_section "TEST 3: NOTIFICATION SYSTEM"

    print_test "Testing NotificationRouter initialization..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.notifications import NotificationRouter
    nm = NotificationRouter()
    print("NotificationRouter initialized")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "NotificationRouter initialization"
    else
        print_fail "NotificationRouter initialization"
        return
    fi

    print_test "Testing notification routing..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.notifications import NotificationRouter
    nm = NotificationRouter()

    # Test sending notifications
    result = nm.notify("Test", "Testing notification routing", level="info")
    print(f"✓ Notification sent: {result}")

    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Notification routing"
    else
        print_fail "Notification routing"
    fi

    print_test "Testing notification backends..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.notifications import NotificationRouter
    nm = NotificationRouter()

    backends = nm.get_available_backends()
    print(f"Available backends: {', '.join(backends)}")

    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Notification backends detection"
    else
        print_fail "Notification backends detection"
    fi
}

# Test 4: CLI Routing
test_cli_routing() {
    print_section "TEST 4: CLI ROUTING & CLASSIFICATION"

    print_test "Testing classifier initialization..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.classifier import classify_input
    result = classify_input("test")
    print(f"Classifier initialized, test classification: {result}")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Classifier initialization"
    else
        print_fail "Classifier initialization"
        return
    fi

    print_test "Testing classification patterns..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.classifier import classify_input

    tests = [
        ("what's my energy level?", "question"),
        ("I'm thinking about changing careers", "thinking"),
        ("I'm so tired today", "venting"),
        ("create task to review Q4 planning", "task"),
        ("I noticed the API is slow", "observation"),
    ]

    failed = []
    for text, expected in tests:
        result = classify_input(text)
        if result != expected:
            failed.append(f"{text[:30]}... expected {expected}, got {result}")
        else:
            print(f"✓ '{text[:30]}...' → {result}")

    if failed:
        print("Classification mismatches:")
        for f in failed:
            print(f"  - {f}")
        sys.exit(1)
    else:
        sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "Classification patterns (question, thinking, venting, task, observation)"
    else
        print_fail "Classification patterns"
    fi

    print_test "Testing thanos-cli wrapper..."
    if [ -f "$SCRIPT_DIR/thanos-cli" ]; then
        if [ -x "$SCRIPT_DIR/thanos-cli" ]; then
            print_pass "thanos-cli wrapper exists and is executable"
        else
            print_fail "thanos-cli wrapper is not executable"
        fi
    else
        print_fail "thanos-cli wrapper not found"
    fi
}

# Test 5: End-to-End Integration
test_e2e() {
    print_section "TEST 5: END-TO-END INTEGRATION"

    print_test "Testing complete workflow: State → Voice → Notification..."
    python3 <<EOF
import sys
sys.path.insert(0, '$PROJECT_ROOT')
try:
    from Shell.lib.visuals import ThanosVisualState
    from Shell.lib.voice import VoiceSynthesizer
    from Shell.lib.notifications import NotificationRouter

    # Initialize all systems
    vsm = ThanosVisualState()
    voice = VoiceSynthesizer()
    nm = NotificationRouter()

    print("✓ All systems initialized")

    # Simulate task workflow
    print("Simulating task workflow...")

    # 1. Start day (CHAOS)
    vsm.set_state('CHAOS')
    print("✓ State: CHAOS")

    # 2. Begin work (FOCUS)
    vsm.set_state('FOCUS')
    print("✓ State: FOCUS")

    # 3. Complete task
    nm.notify("Task Complete", "Integration Test Task completed (+2 points)", level="info")
    print("✓ Task complete notification sent")

    # 4. End day (BALANCE)
    vsm.set_state('BALANCE')
    stats = voice.cache_stats()
    print(f"✓ State: BALANCE, voice cache: {stats['file_count']} files")

    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

    if [ $? -eq 0 ]; then
        print_pass "End-to-end workflow (State → Voice → Notification)"
    else
        print_fail "End-to-end workflow"
    fi
}

# Run all tests
main() {
    check_dependencies
    test_voice
    test_visuals
    test_notifications
    test_cli_routing
    test_e2e

    # Summary
    print_section "TEST SUMMARY"

    TOTAL=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))

    echo "Total Tests: $TOTAL"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo -e "${YELLOW}Skipped: $TESTS_SKIPPED${NC}"
    echo

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}╔═════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  ALL TESTS PASSED - INTEGRATION OK  ║${NC}"
        echo -e "${GREEN}╚═════════════════════════════════════╝${NC}"
        exit 0
    else
        echo -e "${RED}╔════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  SOME TESTS FAILED - CHECK LOGS ABOVE  ║${NC}"
        echo -e "${RED}╚════════════════════════════════════════╝${NC}"
        exit 1
    fi
}

# Run
main
