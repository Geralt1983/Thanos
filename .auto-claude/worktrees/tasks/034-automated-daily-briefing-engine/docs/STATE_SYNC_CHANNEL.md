# StateSyncChannel - State File Update Delivery

The `StateSyncChannel` is a delivery channel that automatically updates `State/Today.md` with briefing content. This provides a persistent, markdown-based record of your daily briefings that integrates seamlessly with your State management workflow.

## Overview

### What It Does

- **Creates `State/Today.md`** if it doesn't exist
- **Updates specific sections** (e.g., `## Morning Brief`, `## Evening Brief`)
- **Preserves existing content** in other sections
- **Adds timestamps** to track when each section was last updated
- **Maintains consistent section order** (Morning → Evening → Other sections)

### Why Use It

1. **Persistent Record**: Your briefings are saved in a markdown file you can reference anytime
2. **Integration**: Works with existing State file workflows
3. **Non-Destructive**: Updates only the relevant section, preserving other content
4. **Timestamped**: Track when each briefing was generated
5. **Version Control Friendly**: Markdown format works well with Git

## Configuration

### Basic Configuration

```json
{
  "state_sync": {
    "enabled": true,
    "state_file": "State/Today.md"
  }
}
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable the channel |
| `state_file` | string | `"State/Today.md"` | Path to the state file to update |

## Usage

### Python API

#### Basic Usage

```python
from Tools.delivery_channels import StateSyncChannel

# Create channel
channel = StateSyncChannel(config={'state_file': 'State/Today.md'})

# Deliver morning briefing
morning_content = """**Top 3 Priorities:**
1. Fix critical bug
2. Review PRs
3. Update documentation
"""

success = channel.deliver(morning_content, 'morning')
```

#### With Multi-Channel Delivery

```python
from Tools.delivery_channels import deliver_to_channels

channels_config = {
    'cli': {'enabled': True, 'color': True},
    'state_sync': {'enabled': True, 'state_file': 'State/Today.md'},
    'file': {'enabled': True, 'output_dir': 'History/DailyBriefings'}
}

results = deliver_to_channels(
    content="Your briefing content here",
    briefing_type='morning',
    channels_config=channels_config
)
```

### Command Line

The StateSyncChannel is automatically used when configured in `config/briefing_schedule.json`:

```bash
# Manual briefing (reads config for delivery channels)
python -m commands.pa.briefing morning

# Scheduled briefing (configured in briefing_schedule.json)
# Runs automatically via cron/systemd
```

## File Structure

### Created File Format

When StateSyncChannel creates a new `State/Today.md` file:

```markdown
# Today
*Date: 2026-01-11*

## Morning Brief
*Updated: 2026-01-11 08:00 AM*

**Top 3 Priorities:**
1. Fix critical bug
2. Review PRs
3. Update documentation
```

### Updated File Format

When updating an existing file with multiple sections:

```markdown
# Today
*Date: 2026-01-11*

## Morning Brief
*Updated: 2026-01-11 08:00 AM*

Morning content here...

## Evening Brief
*Updated: 2026-01-11 08:00 PM*

Evening reflection here...

## Notes

Any other sections are preserved here...
```

## Section Management

### How Sections Work

1. **Section Detection**: Sections are identified by level-2 headers (`## Section Name`)
2. **Section Update**: When delivering a briefing, only the matching section is updated
3. **Section Order**: Sections are ordered as: Morning Brief → Evening Brief → Other sections
4. **Section Preservation**: Unrelated sections remain untouched

### Supported Briefing Types

| Briefing Type | Section Header | When Used |
|---------------|----------------|-----------|
| `morning` | `## Morning Brief` | Morning briefings |
| `evening` | `## Evening Brief` | Evening briefings |
| `custom` | `## Custom Brief` | Custom briefing types |

### Custom Sections

You can add custom sections to `State/Today.md` manually, and they will be preserved:

```markdown
# Today

## Morning Brief
*Updated: 2026-01-11 08:00 AM*
...

## Evening Brief
*Updated: 2026-01-11 08:00 PM*
...

## Notes
<!-- Your custom notes -->

## Goals for Tomorrow
<!-- Your goals -->

## Learnings
<!-- What you learned today -->
```

## Examples

### Example 1: Create New File

```python
from Tools.delivery_channels import StateSyncChannel

channel = StateSyncChannel()

briefing = """**Top 3 Priorities:**
1. Task A
2. Task B
3. Task C
"""

channel.deliver(briefing, 'morning')
# Creates State/Today.md with morning brief section
```

### Example 2: Update Existing Section

```python
# First delivery
channel.deliver("Initial morning content", 'morning')

# Later update (replaces morning content, preserves other sections)
channel.deliver("Updated morning content", 'morning')
```

### Example 3: Add Evening Brief

```python
# Morning brief already exists
channel.deliver("Morning priorities...", 'morning')

# Add evening brief (morning brief preserved)
channel.deliver("Evening reflection...", 'evening')
```

### Example 4: Custom State File

```python
# Use a different state file
channel = StateSyncChannel(config={'state_file': 'State/WorkLog.md'})
channel.deliver("Development notes...", 'development')
```

## Integration with BriefingScheduler

The StateSyncChannel integrates seamlessly with the automated briefing scheduler. Configure it in `config/briefing_schedule.json`:

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "delivery_channels": ["cli", "state_sync", "file"]
    },
    "evening": {
      "enabled": true,
      "time": "19:00",
      "delivery_channels": ["cli", "state_sync"]
    }
  },
  "delivery_channels": {
    "state_sync": {
      "enabled": true,
      "state_file": "State/Today.md"
    }
  }
}
```

## Acceptance Criteria

All acceptance criteria from the implementation plan are met:

✅ **StateSyncChannel updates State/Today.md**
- Implemented in `deliver()` method with section-based updates

✅ **Preserves existing content (doesn't overwrite)**
- Section parsing preserves all non-updated sections
- File header preserved across updates

✅ **Updates specific sections (e.g., ## Morning Brief)**
- Section headers based on briefing type
- Only matching section is replaced

✅ **Creates Today.md if doesn't exist**
- File and directory creation handled gracefully
- Default header added for new files

✅ **Adds timestamp to updates**
- Timestamp format: `*Updated: YYYY-MM-DD HH:MM AM/PM*`
- Added automatically to each section

## Technical Details

### Section Parsing Algorithm

1. **Split by Level-2 Headers**: Content is split at `## ` markers
2. **Group into Sections**: Each section includes its header and all content until the next header
3. **Preserve Order**: Sections are stored in a dictionary for easy updates
4. **Rebuild with Order**: Sections are reassembled in defined order (Morning → Evening → Other)

### Error Handling

- **Missing File**: Returns empty content, creates new file
- **Read Errors**: Logs warning, treats as empty file
- **Write Errors**: Returns `False`, logs error with details
- **Invalid Paths**: Catches and handles exceptions gracefully

### Logging

All delivery attempts are logged:

```
[2026-01-11T08:00:00] StateSyncChannel - morning - SUCCESS - Updated State/Today.md
[2026-01-11T20:00:00] StateSyncChannel - evening - SUCCESS - Updated State/Today.md
```

## Troubleshooting

### State/Today.md Not Being Created

**Problem**: File doesn't exist after delivery

**Solutions**:
- Check that `State/` directory exists or channel has permission to create it
- Verify file path in configuration
- Check logs for error messages

### Existing Content Being Overwritten

**Problem**: Content in other sections is lost

**Solutions**:
- Ensure sections use level-2 headers (`##` not `#` or `###`)
- Verify section names don't match briefing types
- Check file encoding (should be UTF-8)

### Sections in Wrong Order

**Problem**: Sections appear in unexpected order

**Solutions**:
- Morning and Evening briefs are always ordered first
- Other sections appear in the order they were added
- Rebuild order is: Header → Morning → Evening → Other sections

### Timestamps Not Appearing

**Problem**: Section updates don't show timestamps

**Solutions**:
- Timestamps are added automatically by `deliver()` method
- Check that you're using the StateSyncChannel (not manual file writing)
- Verify the section header matches the pattern

## Best Practices

1. **Use Consistent Section Names**: Stick to standard names (Morning Brief, Evening Brief)
2. **Don't Manually Edit Timestamps**: They're auto-generated on each update
3. **Keep Custom Sections Separate**: Add custom sections below briefing sections
4. **Version Control**: Consider committing `State/Today.md` to track daily progress
5. **Daily Archives**: Move previous day's content to archive before new day starts

## Related Documentation

- [Delivery Channels Overview](./DELIVERY_CHANNELS.md)
- [Briefing Scheduler Guide](./SCHEDULER_GUIDE.md)
- [Configuration Guide](../config/README.md)

## API Reference

### StateSyncChannel Class

#### `__init__(config: Optional[Dict[str, Any]] = None)`

Initialize the channel with optional configuration.

**Parameters**:
- `config`: Dictionary with `state_file` key (default: `{'state_file': 'State/Today.md'}`)

#### `deliver(content: str, briefing_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool`

Update the state file with briefing content.

**Parameters**:
- `content`: Briefing content (markdown string)
- `briefing_type`: Type of briefing (e.g., 'morning', 'evening')
- `metadata`: Optional metadata (currently unused)

**Returns**:
- `True` if delivery successful, `False` otherwise

#### `_read_existing_content() -> str`

Read existing content from state file.

**Returns**:
- File content as string, or empty string if file doesn't exist

#### `_parse_sections(content: str) -> Dict[str, str]`

Parse markdown content into sections.

**Parameters**:
- `content`: Markdown content to parse

**Returns**:
- Dictionary mapping section headers to their content

#### `_rebuild_content(sections: Dict[str, str]) -> str`

Rebuild file content from sections with consistent ordering.

**Parameters**:
- `sections`: Dictionary of section headers to content

**Returns**:
- Reconstructed markdown content

---

*Last Updated: 2026-01-11*
