# Manual Interactive Mode Test Guide

**Purpose:** Test the `/run pa:export` command in Thanos interactive mode

---

## Test Procedure

### Step 1: Launch Interactive Mode

```bash
python thanos.py interactive
```

**Expected Output:**
```
Thanos Interactive Mode
Type '/help' for available commands, '/exit' to quit
>
```

---

### Step 2: Test Help Command

**Input:**
```
/run pa:export --help
```

**Expected Output:**
```
usage: pa:export [-h] [--format {csv,json}]
                 [--type {tasks,habits,goals,metrics,all}] [--output OUTPUT]

Export productivity data to CSV or JSON format

optional arguments:
  -h, --help            show this help message and exit
  --format {csv,json}   Output format (default: csv)
  --type {tasks,habits,goals,metrics,all}
                        Data type to export (default: all)
  --output OUTPUT       Output directory (default: History/Exports/)
```

✅ **Verify:** Help text displays correctly with all parameters

---

### Step 3: Test CSV Export

**Input:**
```
/run pa:export --format csv --type tasks
```

**Expected Output:**
```
📦 Data Export
============================================================
Format: CSV
Type: tasks
Output: History/Exports/
============================================================

🔄 Starting data retrieval...

🔌 Connecting to database...
📥 Retrieving tasks...
✅ Retrieved [N] tasks

💾 Exporting to CSV format...
✅ CSV export complete

📊 Export Summary
============================================================
Exported Files:
- tasks.csv ([size]) - [N] records

Export saved to History/Exports/
============================================================
```

✅ **Verify:**
- Command executes without errors
- Progress messages display
- CSV file is created
- Same output as direct invocation

---

### Step 4: Test JSON Export

**Input:**
```
/run pa:export --format json --type all
```

**Expected Output:**
```
📦 Data Export
============================================================
Format: JSON
Type: all
Output: History/Exports/
============================================================

🔄 Starting data retrieval...

🔌 Connecting to database...
📥 Retrieving tasks...
✅ Retrieved [N] tasks
📥 Retrieving habits...
✅ Retrieved [N] habits
📥 Retrieving goals...
✅ Retrieved [N] goals
📥 Retrieving metrics...
✅ Retrieved metrics

💾 Exporting to JSON format...
✅ JSON export complete

📊 Export Summary
============================================================
Exported Files:
- tasks.json ([size]) - [N] records
- habits.json ([size]) - [N] records
- goals.json ([size]) - [N] records
- metrics.json ([size]) - 1 record

Export saved to History/Exports/
============================================================
```

✅ **Verify:**
- Command executes without errors
- All data types retrieved
- JSON files created
- Same output as direct invocation

---

### Step 5: Test Error Handling

**Input:**
```
/run pa:export --format xml
```

**Expected Output:**
```
usage: pa:export [-h] [--format {csv,json}]
                 [--type {tasks,habits,goals,metrics,all}] [--output OUTPUT]
pa:export: error: argument --format: invalid choice: 'xml' (choose from 'csv', 'json')
```

✅ **Verify:**
- Error message displays clearly
- Valid options shown
- Same error as direct invocation

---

### Step 6: Exit Interactive Mode

**Input:**
```
/exit
```

**Expected Output:**
```
Goodbye!
```

---

## Acceptance Criteria Checklist

| Criteria | Status | Notes |
|----------|--------|-------|
| Interactive mode launches | ⏳ | Run `python thanos.py interactive` |
| `/run pa:export --help` shows help | ⏳ | Must display full help text |
| `/run pa:export` executes command | ⏳ | Must execute without errors |
| Output matches direct invocation | ⏳ | Compare with `python -m commands.pa.export` |
| Error messages are clear | ⏳ | Test invalid arguments |
| Progress messages display | ⏳ | Verify streaming output |

---

## Quick Test Script

Copy and paste these commands one at a time in interactive mode:

```bash
# Start interactive mode
python thanos.py interactive

# Then run these commands in the interactive prompt:
/run pa:export --help
/run pa:export --format csv --type tasks
/run pa:export --format json --type habits
/run pa:export --format xml
/exit
```

---

## Notes

- **Database Connection:** Tests may fail if DATABASE_URL is not configured
- **Output Directory:** Files will be created in `History/Exports/` by default
- **Consistency:** All invocation methods should produce identical output
- **Error Handling:** Invalid arguments should show clear error messages

---

## Automated Testing Note

Interactive mode requires human interaction and cannot be fully automated without expect/pexpect. The automated test suite (`test_invocation_methods.py`) covers all non-interactive invocation methods successfully.

---

**Status:** ⏳ PENDING MANUAL VERIFICATION

Once completed, mark subtask 3.3 as complete and commit results.
