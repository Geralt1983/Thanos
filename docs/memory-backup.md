# Memory Backup and Export System

## Overview

Thanos provides a comprehensive backup and export system for your Memory V2 data, ensuring you **never lose your accumulated context**. This system was built in response to ChatGPT's February 2025 memory data loss incident that affected thousands of users.

### What's Included

The backup system preserves:
- **Memory V2 data** from Neon pgvector (memories with embeddings)
- **Relationship Store** from SQLite (relationship graph)
- **Metadata** (timestamps, user IDs, counts)
- **Checksums** for verification

### Features

- ✅ **Multiple export formats**: JSON (complete), CSV (analysis), Markdown (human-readable)
- ✅ **Automated backups**: Schedule daily backups with retention policy
- ✅ **Integrity verification**: Checksum validation and schema checking
- ✅ **Safe restore**: Preview changes with dry-run mode before restoring
- ✅ **Conflict handling**: Choose how to handle duplicate data

---

## Quick Start

### 1. Export Your Memories

Export to JSON (complete backup with vectors):
```bash
python -m commands.memory.export --format json --output ./my-export
```

Export to Markdown (human-readable):
```bash
python -m commands.memory.export --format markdown --output ./my-export
```

### 2. Create a Backup

Create a timestamped backup (recommended for regular backups):
```bash
python -m commands.memory.backup
```

This creates a backup in `./backups/memory_YYYYMMDD_HHMMSS/` with automatic verification.

### 3. Set Up Automated Backups

Install daily automated backups at 2am:
```bash
bash scripts/schedule_memory_backup.sh
```

### 4. Restore from Backup

Preview what would be restored (safe):
```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000 --dry-run
```

Restore with confirmation:
```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000
```

---

## Export Command

### Basic Usage

```bash
python -m commands.memory.export [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--format` | Output format: `json`, `csv`, or `markdown` | `json` |
| `--output` | Output directory path | `./History/Exports/memory` |
| `--verify` | Verify export integrity after completion | `false` |
| `--no-vectors` | Exclude vector embeddings (smaller files) | `false` |
| `--user` | User ID to export memories for | `jeremy` |

### Export Formats

#### JSON Format
- **Best for**: Complete backups, restore operations
- **Includes**: All fields, vector embeddings, relationships, metadata
- **File size**: Largest (includes 1536-dimension vectors)

```bash
python -m commands.memory.export --format json --output ./backup-2024
```

**Output structure:**
```
backup-2024/
├── export.json          # Complete data
├── metadata.json        # Export metadata
└── checksums.json       # File checksums
```

#### CSV Format
- **Best for**: Data analysis, spreadsheet import
- **Includes**: Flattened data in separate files
- **File size**: Medium

```bash
python -m commands.memory.export --format csv --output ./analysis
```

**Output structure:**
```
analysis/
├── memories.csv         # Memory records
├── relationships.csv    # Relationship data
├── metadata.json        # Export metadata
└── checksums.json       # File checksums
```

#### Markdown Format
- **Best for**: Human-readable archive, documentation
- **Includes**: Formatted memories with heat indicators, relationship graph
- **File size**: Smallest

```bash
python -m commands.memory.export --format markdown --output ./archive
```

**Output structure:**
```
archive/
├── memories.md          # Formatted memories with Mermaid graph
├── metadata.json        # Export metadata
└── checksums.json       # File checksums
```

**Features:**
- Memories grouped by client/project
- Heat indicators: 🔥 hot (>0.7), • normal (0.3-0.7), ❄️ cold (<0.3)
- Mermaid graph visualization of relationships
- Complete metadata display

### Examples

Export everything with verification:
```bash
python -m commands.memory.export --format json --verify
```

Lightweight export without vectors:
```bash
python -m commands.memory.export --no-vectors --output ./lightweight-backup
```

Human-readable archive:
```bash
python -m commands.memory.export --format markdown --output ./memory-archive
```

---

## Backup Command

### Basic Usage

```bash
python -m commands.memory.backup [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--output` | Base backup directory | `./backups` |
| `--no-verify` | Skip verification after backup | Enabled by default |

### How It Works

The backup command:
1. Creates a timestamped directory: `memory_YYYYMMDD_HHMMSS`
2. Exports to JSON format with full vector embeddings
3. Generates checksums for all files
4. Verifies backup integrity (unless `--no-verify`)

### Examples

Standard backup:
```bash
python -m commands.memory.backup
```

Custom backup location:
```bash
python -m commands.memory.backup --output ./my-backups
```

Quick backup without verification:
```bash
python -m commands.memory.backup --no-verify
```

### Backup Location

Backups are stored in timestamped directories:
```
./backups/
├── memory_20240126_020000/    # Daily backup at 2am
├── memory_20240125_020000/
└── memory_20240124_020000/
```

---

## Restore Command

### Basic Usage

```bash
python -m commands.memory.restore --source BACKUP_DIR [OPTIONS]
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--source` | Path to backup directory (required) | N/A |
| `--dry-run` | Preview restore without making changes | `false` |
| `--force` | Skip confirmation prompt | `false` |
| `--conflict-mode` | Handle duplicates: `skip` or `update` | `skip` |

### Safety Features

1. **Backup verification** - Validates backup before restore begins
2. **Dry-run mode** - Preview changes without modifying data
3. **Confirmation prompt** - Requires explicit confirmation (unless `--force`)
4. **Conflict handling** - Choose how to handle duplicate IDs

### Conflict Modes

#### Skip Mode (Default, Safest)
- Skips memories/relationships with duplicate IDs
- Preserves existing data
- Best for merging backups

```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000
```

#### Update Mode
- Updates existing memories/relationships with backup data
- Overwrites existing records
- Best for restoring from known-good backup

```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000 --conflict-mode update
```

### Examples

**Step 1: Preview restore (recommended first step)**
```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000 --dry-run
```

Output:
```
[DRY RUN] Restoring memory from backup...
   Source: ./backups/memory_20240126_120000
   Conflict mode: skip

🔍 Verifying backup integrity...
✓ Backup verified successfully

[DRY RUN] Restoring data...

[DRY RUN COMPLETE] Restore preview

  Memories:
    Restored: 38,664
    Skipped: 0 (duplicates)

  Relationships:
    Restored: 1,245
    Skipped: 0 (duplicates)

💡 This was a preview. Use without --dry-run to perform actual restore.
```

**Step 2: Restore with confirmation**
```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000
```

**Step 3: Automated restore (use with caution)**
```bash
python -m commands.memory.restore --source ./backups/memory_20240126_120000 --force
```

---

## Automated Backups

### Setup

Install daily automated backups:
```bash
bash scripts/schedule_memory_backup.sh
```

This creates a cron job that runs daily at 2:00 AM.

### Configuration

- **Schedule**: Daily at 2:00 AM
- **Script**: `scripts/backup_memory.sh`
- **Log**: `backups/backup.log`
- **Retention**: 7 daily + 4 weekly backups

### Retention Policy

The system automatically manages old backups:

| Type | Retention | Description |
|------|-----------|-------------|
| **Daily** | 7 days | All backups from last 7 days |
| **Weekly** | 4 weeks | One backup per week (Sundays) |

**Example retention:**
```
backups/
├── memory_20240126_020000/  # Today
├── memory_20240125_020000/  # Yesterday (daily)
├── memory_20240124_020000/  # 2 days ago (daily)
├── memory_20240123_020000/  # 3 days ago (daily)
├── memory_20240122_020000/  # 4 days ago (daily)
├── memory_20240121_020000/  # 5 days ago (daily - Sunday)
├── memory_20240120_020000/  # 6 days ago (daily)
├── memory_20240114_020000/  # Last week (weekly)
├── memory_20240107_020000/  # 2 weeks ago (weekly)
└── memory_20231231_020000/  # 3 weeks ago (weekly)
```

### Management

**Check backup schedule:**
```bash
crontab -l
```

**View backup logs:**
```bash
tail -f backups/backup.log
```

**Run backup manually:**
```bash
bash scripts/backup_memory.sh
```

**Uninstall automated backups:**
```bash
crontab -l | grep -v 'backup_memory.sh' | crontab -
```

---

## Best Practices

### Regular Backups

1. **Set up automated backups** - Install the cron job for daily backups
2. **Test restore periodically** - Verify backups are working with dry-run
3. **Keep off-site backups** - Copy important backups to external storage

### Before Major Changes

Before making significant changes to your memory system:

```bash
# 1. Create manual backup
python -m commands.memory.backup --output ./backups/pre-change

# 2. Verify backup
python -m commands.memory.restore --source ./backups/pre-change/memory_* --dry-run
```

### Data Portability

Export to multiple formats for different use cases:

```bash
# Complete backup
python -m commands.memory.export --format json --output ./complete-backup

# Analysis-friendly format
python -m commands.memory.export --format csv --output ./analysis

# Human-readable archive
python -m commands.memory.export --format markdown --output ./archive
```

### Disk Space Management

Monitor backup disk usage:

```bash
du -sh backups/
```

Adjust retention policy in `scripts/backup_memory.sh` if needed:
```bash
# Edit retention settings
nano scripts/backup_memory.sh

# Look for these lines:
# SEVEN_DAYS_AGO=$(date -v-7d +%Y%m%d)  # Daily retention
# for i in {1..4}; do                   # Weekly retention
```

---

## Troubleshooting

### Backup Fails

**Problem:** Backup command exits with error

**Solutions:**
1. Check database connection:
   ```bash
   # Verify Neon connection
   python -c "from Tools.memory_v2.service import MemoryService; m = MemoryService(); print('OK')"
   ```

2. Check disk space:
   ```bash
   df -h .
   ```

3. Check permissions:
   ```bash
   mkdir -p ./backups && touch ./backups/test.txt && rm ./backups/test.txt
   ```

### Verification Fails

**Problem:** Export verification fails with checksum mismatch

**Solutions:**
1. Re-export with verification:
   ```bash
   python -m commands.memory.export --format json --verify --output ./backup-verified
   ```

2. Check file integrity:
   ```bash
   ls -la ./backups/memory_*/
   cat ./backups/memory_*/metadata.json
   ```

### Restore Fails

**Problem:** Restore command exits with error

**Solutions:**
1. Verify backup first:
   ```bash
   python -c "from Tools.memory_export import MemoryExporter; e = MemoryExporter(); print('Valid' if e.verify_export('./backups/memory_20240126_120000') else 'Invalid')"
   ```

2. Check for conflicts in dry-run:
   ```bash
   python -m commands.memory.restore --source ./backups/memory_20240126_120000 --dry-run
   ```

3. Use update mode if needed:
   ```bash
   python -m commands.memory.restore --source ./backups/memory_20240126_120000 --conflict-mode update
   ```

### Cron Job Not Running

**Problem:** Automated backups not executing

**Solutions:**
1. Check cron job exists:
   ```bash
   crontab -l | grep backup_memory
   ```

2. Check script is executable:
   ```bash
   ls -la scripts/backup_memory.sh
   chmod +x scripts/backup_memory.sh
   ```

3. Check logs for errors:
   ```bash
   tail -50 backups/backup.log
   ```

4. Test script manually:
   ```bash
   bash scripts/backup_memory.sh
   ```

5. Verify cron is running:
   ```bash
   # macOS
   launchctl list | grep cron

   # Linux
   systemctl status cron
   ```

### Large File Sizes

**Problem:** Backup files are too large

**Solutions:**
1. Export without vectors:
   ```bash
   python -m commands.memory.export --no-vectors --output ./lightweight
   ```

2. Use CSV format (smaller than JSON):
   ```bash
   python -m commands.memory.export --format csv --output ./smaller
   ```

3. Compress backups:
   ```bash
   tar -czf backup.tar.gz backups/memory_20240126_120000/
   ```

---

## Technical Details

### Database Sources

| Component | Storage | Contents |
|-----------|---------|----------|
| **Memory V2** | Neon pgvector | Memories with 1536-dim embeddings |
| **Relationships** | SQLite | Relationship graph |

### File Formats

#### JSON Export Structure
```json
{
  "metadata": {
    "version": "1.0",
    "timestamp": "2024-01-26T12:00:00Z",
    "user_id": "jeremy",
    "memory_count": 38664,
    "relationship_count": 1245
  },
  "memories": [
    {
      "id": "mem_abc123",
      "content": "Memory content",
      "embedding": [0.1, 0.2, ...],  // 1536 dimensions
      "metadata": {...},
      "created_at": "2024-01-26T12:00:00Z",
      "heat": 0.85
    }
  ],
  "relationships": [
    {
      "source_id": "mem_abc123",
      "target_id": "mem_def456",
      "rel_type": "caused",
      "strength": 0.9,
      "metadata": {...}
    }
  ]
}
```

#### CSV Export Structure

**memories.csv:**
```csv
id,content,user_id,metadata,created_at,heat
mem_abc123,"Memory content",jeremy,{...},2024-01-26T12:00:00Z,0.85
```

**relationships.csv:**
```csv
source_id,target_id,rel_type,strength,metadata
mem_abc123,mem_def456,caused,0.9,{...}
```

### Checksums

Each export includes SHA-256 checksums:
- Individual file checksums
- Combined checksum for verification
- Stored in `checksums.json`

### API Reference

For programmatic use:

```python
from Tools.memory_export import MemoryExporter

# Initialize exporter
exporter = MemoryExporter(user_id="jeremy")

# Export to JSON
result = exporter.export_all(
    output_path="./backup",
    format="json",
    include_vectors=True
)

# Verify export
is_valid = exporter.verify_export("./backup")

# Restore from backup
restore_result = exporter.restore_from_backup(
    backup_path="./backup",
    dry_run=False,
    conflict_mode="skip"
)
```

---

## Support

### Questions?

- Check [MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md) for memory architecture
- Review [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues
- Check logs: `backups/backup.log`

### Data Loss Prevention

**Your data is precious.** This backup system ensures:
- ✅ Complete data preservation
- ✅ Automatic scheduled backups
- ✅ Verification of backup integrity
- ✅ Safe restore with dry-run preview
- ✅ Multiple export formats for portability

**Never lose your context again.**
