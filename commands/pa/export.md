# /pa:export - Data Export Command

Export tasks, habits, goals, and metrics to CSV or JSON format for analysis and backup.

## Usage
```
/pa:export [--format FORMAT] [--type TYPE] [--output DIR]
```

## Parameters
- `--format` (optional): Export format (csv | json) - defaults to csv
- `--type` (optional): Data type to export (tasks | habits | goals | metrics | all) - defaults to all
- `--output` (optional): Output directory path - defaults to History/Exports/

## Workflow

### 1. Database Connection
- Connect to WorkOS database (Neon PostgreSQL)
- Verify connection and authentication
- Prepare data retrieval queries

### 2. Data Retrieval
Based on the `--type` parameter, retrieve the specified data:
- **tasks**: All tasks (active, queued, backlog, done) with metadata
- **habits**: All habits with completion data and streaks
- **goals**: Daily goals data with points and streak information
- **metrics**: Calculated metrics including progress and targets
- **all**: All of the above data types

### 3. Data Formatting
- Convert database records to exportable format
- Handle nested data structures appropriately
- Convert timestamps to ISO format strings
- Prepare field headers and organize columns

### 4. Export Generation
**CSV Format:**
- Create separate CSV files for each data type
- Include proper headers with column names
- Flatten or JSON-encode nested fields
- Ensure proper escaping of special characters

**JSON Format:**
- Create separate JSON files for each data type
- Maintain nested data structure integrity
- Use proper indentation for readability
- Handle datetime serialization

### 5. Save and Report
- Save files to output directory (create if needed)
- Generate export summary with statistics
- Save summary to History/Exports/ directory
- Display file locations and sizes

## Output Format
```markdown
## Data Export

Connecting to WorkOS database...
✓ Connected to database

Retrieving data...
✓ Retrieved [X] tasks
✓ Retrieved [Y] habits
✓ Retrieved [Z] goal records
✓ Retrieved metrics data

Exporting to [CSV/JSON]...
✓ Exported [data_type]: [N] records ([file_size])

## Export Summary

**Date:** [YYYY-MM-DD HH:MM:SS]
**Format:** [CSV/JSON]
**Data Types:** [types exported]

### Files Created
- [file_path] - [X] records ([file_size])
- [file_path] - [Y] records ([file_size])

### Total Records Exported
[Total count across all data types]

Export summary saved to: History/Exports/export_summary_[timestamp].md
```

## Data Fields

### Tasks
- id, title, description, status
- client_id, client_name
- sort_order, effort_estimate
- points_final, points_ai_guess
- created_at, completed_at, updated_at

### Habits
- id, title, description, is_active
- sort_order
- current_streak, longest_streak
- last_completed_date, last_completion
- created_at, updated_at

### Goals (Daily)
- date
- current_streak, earned_points, target_points
- goal_met

### Metrics
- completed_count, active_count, queued_count
- earned_points, target_points, minimum_points
- progress_percentage, streak
- goal_met, target_met

## Integration Points
- WorkOS Database (Neon PostgreSQL) via WorkOSAdapter
- File System for CSV/JSON file creation
- History/Exports/ directory for summary storage

## Flags
- `--format csv`: Export as CSV files (default)
- `--format json`: Export as JSON files
- `--type tasks`: Export only tasks
- `--type habits`: Export only habits
- `--type goals`: Export only daily goals
- `--type metrics`: Export only calculated metrics
- `--type all`: Export all data types (default)
- `--output /path/to/dir`: Specify custom output directory

## Examples

### Export all data as CSV (default)
```
/pa:export
```

### Export tasks as JSON
```
/pa:export --format json --type tasks
```

### Export habits to custom directory
```
/pa:export --type habits --output ~/Documents/exports
```

### Export all data as JSON
```
/pa:export --format json --type all
```

## Use Cases

### Data Backup
Export all data regularly for backup purposes:
```
/pa:export --format json --type all
```

### Task Analysis
Export tasks to CSV for spreadsheet analysis:
```
/pa:export --format csv --type tasks
```

### Habit Tracking Review
Export habit data to review patterns and streaks:
```
/pa:export --format csv --type habits
```

### Goal Progress Reporting
Export goals and metrics for progress reports:
```
/pa:export --format csv --type goals
/pa:export --format csv --type metrics
```

## Notes
- Export files are timestamped to prevent overwrites
- Large datasets may take a few moments to export
- CSV format is recommended for spreadsheet import
- JSON format preserves nested data structures
- Export summary is automatically saved to History/Exports/
- Requires active WorkOS database connection
