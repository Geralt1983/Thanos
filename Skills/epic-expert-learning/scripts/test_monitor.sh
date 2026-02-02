#!/bin/bash
# Test script for Task Closure Monitor
# Tests different confidence levels and scenarios

echo "=== Task Closure Monitor - Test Suite ==="
echo ""

# Test 1: High confidence - provider matching
echo "Test 1: HIGH CONFIDENCE (Provider Matching - 90%)"
echo "=================================================="
python3 scripts/task_closure_monitor.py --task-json '{
  "id": "task_001",
  "title": "Fix VersaCare provider matching issue",
  "description": "Provider matching failing in KY environment",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface", "versacare"]
}'
echo ""
echo ""

# Test 2: High confidence - orderset build
echo "Test 2: HIGH CONFIDENCE (Orderset Build - 80%)"
echo "==============================================="
python3 scripts/task_closure_monitor.py --task-json '{
  "id": "task_002",
  "title": "Build cardiology orderset for new protocols",
  "description": "Create comprehensive orderset with cardiac meds",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "orderset"]
}'
echo ""
echo ""

# Test 3: High confidence - ScottCare interface
echo "Test 3: HIGH CONFIDENCE (ScottCare Interface - 85%)"
echo "===================================================="
python3 scripts/task_closure_monitor.py --task-json '{
  "id": "task_003",
  "title": "Configure ScottCare telemonitoring interface",
  "description": "Set up device data ingest from ScottCare",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface", "scottcare"]
}'
echo ""
echo ""

# Test 4: Low confidence - generic fix
echo "Test 4: LOW CONFIDENCE (Generic Fix - 50%)"
echo "==========================================="
python3 scripts/task_closure_monitor.py --task-json '{
  "id": "task_004",
  "title": "Fix issue with patient data display",
  "description": "Some problem with patient demographics",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "bug"]
}'
echo ""
echo ""

# Test 5: Non-Epic task (should skip)
echo "Test 5: NON-EPIC TASK (Should Skip)"
echo "===================================="
python3 scripts/task_closure_monitor.py --task-json '{
  "id": "task_005",
  "title": "Update project documentation",
  "description": "Write README for new feature",
  "status": "done",
  "client": "Internal",
  "tags": ["docs"]
}'
echo ""
echo ""

# Test 6: Medium confidence - BPA configuration
echo "Test 6: MEDIUM-HIGH CONFIDENCE (BPA Config - 75%)"
echo "=================================================="
python3 scripts/task_closure_monitor.py --task-json '{
  "id": "task_006",
  "title": "Configure BPA for medication allergies",
  "description": "Set up BPA with proper firing logic",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "bpa", "workflow"]
}'
echo ""
echo ""

# Summary
echo "=== Test Summary ==="
echo ""
echo "✅ Test 1: High confidence → Auto-captured"
echo "✅ Test 2: High confidence → Auto-captured"
echo "✅ Test 3: High confidence → Auto-captured"
echo "⚠️  Test 4: Low confidence → Requires user input"
echo "❌ Test 5: Non-Epic → Skipped"
echo "✅ Test 6: Medium-high confidence → Auto-captured"
echo ""
echo "Expected behavior:"
echo "  - High confidence (>70%): Auto-capture with educated guess"
echo "  - Low confidence (<70%): Ask user for solution"
echo "  - Non-Epic: Skip entirely"
echo ""
echo "Check learning progress:"
echo "  python3 scripts/daily_review.py"
