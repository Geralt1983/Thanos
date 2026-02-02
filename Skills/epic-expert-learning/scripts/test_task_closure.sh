#!/bin/bash
# Test script for Task Closure Learning Hook
# Demonstrates high and low confidence scenarios

echo "=== Task Closure Learning Hook - Test Suite ==="
echo ""

# Test 1: High confidence task (provider matching)
echo "Test 1: High Confidence Task (Provider Matching)"
echo "================================================"
cat > /tmp/test_task_high.json <<EOF
{
  "id": "task_001",
  "title": "Fix VersaCare provider matching issue",
  "description": "Provider matching failing due to missing NPI in external system",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface", "versacare"],
  "completed_at": "2026-02-01T20:00:00Z"
}
EOF

python3 scripts/task_closure_hook.py --task-data /tmp/test_task_high.json
echo ""
echo ""

# Test 2: Medium-high confidence (orderset build)
echo "Test 2: Medium-High Confidence Task (Orderset Build)"
echo "====================================================="
cat > /tmp/test_task_medium.json <<EOF
{
  "id": "task_002",
  "title": "Build cardiology orderset for new protocols",
  "description": "Create comprehensive orderset with cardiac medications and labs",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "orderset", "cardiology"],
  "completed_at": "2026-02-01T21:00:00Z"
}
EOF

python3 scripts/task_closure_hook.py --task-data /tmp/test_task_medium.json
echo ""
echo ""

# Test 3: Low confidence (generic fix)
echo "Test 3: Low Confidence Task (Generic Fix)"
echo "=========================================="
cat > /tmp/test_task_low.json <<EOF
{
  "id": "task_003",
  "title": "Fix issue with patient data display",
  "description": "Patient demographics not showing correctly",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "bug"],
  "completed_at": "2026-02-01T22:00:00Z"
}
EOF

python3 scripts/task_closure_hook.py --task-data /tmp/test_task_low.json
echo ""
echo ""

# Test 4: Non-Epic task (should skip)
echo "Test 4: Non-Epic Task (Should Skip)"
echo "===================================="
cat > /tmp/test_task_noepic.json <<EOF
{
  "id": "task_004",
  "title": "Update project documentation",
  "description": "Write README for new module",
  "status": "done",
  "client": "Internal",
  "tags": ["documentation"],
  "completed_at": "2026-02-01T23:00:00Z"
}
EOF

python3 scripts/task_closure_hook.py --task-data /tmp/test_task_noepic.json
echo ""
echo ""

# Test 5: Cardiac rehab specific
echo "Test 5: Cardiac Rehab Integration Task"
echo "======================================="
cat > /tmp/test_task_rehab.json <<EOF
{
  "id": "task_005",
  "title": "Configure ScottCare telemonitoring interface",
  "description": "Set up device data ingest from ScottCare system",
  "status": "done",
  "client": "KY",
  "tags": ["epic", "interface", "scottcare", "cardiac-rehab"],
  "completed_at": "2026-02-02T10:00:00Z"
}
EOF

python3 scripts/task_closure_hook.py --task-data /tmp/test_task_rehab.json
echo ""
echo ""

# Cleanup
rm -f /tmp/test_task_*.json

echo "=== Test Suite Complete ==="
echo ""
echo "Check learning progress:"
echo "  python3 scripts/daily_review.py"
