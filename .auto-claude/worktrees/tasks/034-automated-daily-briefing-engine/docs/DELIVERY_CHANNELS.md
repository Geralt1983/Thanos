# Delivery Channels Documentation

The Delivery Channels system provides a flexible abstraction for delivering briefing content through multiple channels simultaneously. This allows briefings to be displayed in the terminal, saved to files, sent as notifications, or any combination thereof.

## Table of Contents
- [Architecture](#architecture)
- [Available Channels](#available-channels)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Extending the System](#extending-the-system)

---

## Architecture

### Base Class: `DeliveryChannel`

All delivery channels inherit from the abstract `DeliveryChannel` base class, which provides:
- Common initialization with configuration support
- Abstract `deliver()` method that subclasses must implement
- Built-in logging for delivery attempts
- Consistent error handling interface

### Channel Implementations

1. **CLIChannel** - Terminal output with optional ANSI colors
2. **FileChannel** - Save briefings to filesystem
3. **NotificationChannel** - Desktop notifications (macOS/Linux)
4. **StateSyncChannel** - Update State/Today.md with briefing content

---

## Available Channels

### 1. CLIChannel

Prints briefings to stdout with optional color formatting using ANSI escape codes.

**Features:**
- Automatic color detection (disabled for non-TTY outputs)
- Markdown header formatting with colors
- Configurable color enable/disable
- Clean, formatted output with separators

**Configuration:**
```json
{
  "cli": {
    "enabled": true,
    "color": true
  }
}
```

**Example Output:**
```
================================================================================
MORNING BRIEFING
================================================================================

# Top Priorities
1. Complete project design
2. Review team PRs
3. Update documentation

================================================================================
```

### 2. FileChannel

Saves briefings to the filesystem with customizable paths and filenames.

**Features:**
- Automatic directory creation
- Customizable filename patterns with variables
- Metadata headers (YAML frontmatter)
- ISO 8601 timestamps
- UTF-8 encoding support

**Configuration:**
```json
{
  "file": {
    "enabled": true,
    "output_dir": "History/DailyBriefings",
    "filename_pattern": "{date}_{type}_briefing.md"
  }
}
```

**Filename Pattern Variables:**
- `{date}` - Date in YYYY-MM-DD format
- `{type}` - Briefing type (morning, evening, etc.)

**Example Saved File:**
```markdown
---
type: morning
date: 2026-01-11
generated_at: 2026-01-11T07:00:00.123456
---

# Morning Briefing
...
```

### 3. NotificationChannel

Sends desktop notifications using platform-specific notification systems.

**Features:**
- Automatic platform detection (macOS/Linux)
- Graceful degradation when notifications unavailable
- Summary mode (top 3 priorities only)
- Support for multiple notification backends

**Supported Systems:**
- **macOS:** terminal-notifier or osascript
- **Linux:** notify-send (libnotify)
- **Windows:** Not yet supported

**Configuration:**
```json
{
  "notification": {
    "enabled": false,
    "summary_only": true
  }
}
```

**Installation Requirements:**

macOS:
```bash
# Option 1: terminal-notifier (recommended)
brew install terminal-notifier

# Option 2: osascript (built-in, less features)
# No installation needed
```

Linux:
```bash
# Ubuntu/Debian
sudo apt-get install libnotify-bin

# Fedora/RHEL
sudo dnf install libnotify
```

### 4. StateSyncChannel

Updates State/Today.md with briefing content, intelligently merging sections while preserving existing content.

**Features:**
- Creates State/Today.md if it doesn't exist
- Updates specific sections (## Morning Brief, ## Evening Brief)
- Preserves existing content in other sections
- Adds timestamps to track when sections were updated
- Maintains consistent section order
- Non-destructive updates

**Configuration:**
```json
{
  "state_sync": {
    "enabled": true,
    "state_file": "State/Today.md"
  }
}
```

**How It Works:**
1. Reads existing State/Today.md content
2. Parses content into sections based on level-2 headers (`##`)
3. Updates only the matching section (e.g., `## Morning Brief`)
4. Preserves all other sections unchanged
5. Adds timestamp to updated section
6. Maintains section order: Morning → Evening → Other sections

**Example State/Today.md:**
```markdown
# Today
*Date: 2026-01-11*

## Morning Brief
*Updated: 2026-01-11 08:00 AM*

**Top 3 Priorities:**
1. Fix critical bug
2. Review PRs
3. Update documentation

## Evening Brief
*Updated: 2026-01-11 08:00 PM*

**Today's Accomplishments:**
✅ Fixed critical bug
✅ Reviewed 3 PRs

## Notes
<!-- Custom notes preserved here -->
```

**Use Cases:**
- Maintain a daily State file with both morning and evening briefs
- Version control your daily progress with Git
- Reference previous briefings without searching history files
- Integrate briefings with your existing State management workflow

**See Also:** [StateSyncChannel Detailed Documentation](./STATE_SYNC_CHANNEL.md)

---

## Configuration

### In briefing_schedule.json

The delivery channels are configured in `config/briefing_schedule.json`:

```json
{
  "delivery": {
    "cli": {
      "enabled": true,
      "color": true
    },
    "file": {
      "enabled": true,
      "output_dir": "History/DailyBriefings",
      "filename_pattern": "{date}_{type}_briefing.md"
    },
    "notification": {
      "enabled": false,
      "summary_only": true
    },
    "state_sync": {
      "enabled": true,
      "state_file": "State/Today.md"
    }
  }
}
```

### Per-Briefing Configuration

Individual briefings can specify which channels to use:

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "template": "briefing_morning.md",
      "delivery_channels": ["cli", "file", "state_sync"]
    },
    "evening": {
      "enabled": false,
      "time": "19:00",
      "template": "briefing_evening.md",
      "delivery_channels": ["cli", "file", "state_sync", "notification"]
    }
  }
}
```

---

## Usage Examples

### Example 1: Single Channel Delivery

```python
from Tools.delivery_channels import CLIChannel

# Create a CLI channel
cli_channel = CLIChannel(config={'color': True})

# Deliver content
content = "# Morning Briefing\n\nTop priorities..."
success = cli_channel.deliver(content, "morning")

if success:
    print("Briefing delivered successfully!")
```

### Example 2: File Channel with Custom Path

```python
from Tools.delivery_channels import FileChannel

# Create a file channel with custom configuration
file_channel = FileChannel(config={
    'output_dir': 'custom/path/to/briefings',
    'filename_pattern': '{date}_daily_{type}.md'
})

# Deliver content
metadata = {'date': '2026-01-11'}
success = file_channel.deliver(content, "morning", metadata)
```

### Example 3: Using the Factory Function

```python
from Tools.delivery_channels import create_delivery_channel

# Create channels using the factory
cli = create_delivery_channel('cli', {'color': True})
file = create_delivery_channel('file', {
    'output_dir': 'History/DailyBriefings'
})

# Deliver to both
cli.deliver(content, "morning")
file.deliver(content, "morning", {'date': '2026-01-11'})
```

### Example 4: Multi-Channel Delivery

```python
from Tools.delivery_channels import deliver_to_channels

# Configure multiple channels
channels_config = {
    'cli': {
        'enabled': True,
        'color': True
    },
    'file': {
        'enabled': True,
        'output_dir': 'History/DailyBriefings',
        'filename_pattern': '{date}_{type}_briefing.md'
    },
    'notification': {
        'enabled': True,
        'summary_only': True
    }
}

# Deliver to all enabled channels at once
metadata = {
    'date': '2026-01-11',
    'priorities': [
        {'title': 'First priority'},
        {'title': 'Second priority'},
        {'title': 'Third priority'}
    ]
}

results = deliver_to_channels(
    content="# Morning Briefing\n...",
    briefing_type="morning",
    channels_config=channels_config,
    metadata=metadata
)

# Check results
for channel, success in results.items():
    print(f"{channel}: {'✓' if success else '✗'}")
```

### Example 5: Integration with BriefingEngine

```python
from Tools.briefing_engine import BriefingEngine
from Tools.delivery_channels import deliver_to_channels
import json

# Initialize briefing engine
engine = BriefingEngine()

# Gather context and render briefing
context = engine.gather_context()
content = engine.render_briefing('morning', context)

# Load delivery configuration
with open('config/briefing_schedule.json') as f:
    config = json.load(f)

# Deliver through configured channels
delivery_config = config.get('delivery', {})
results = deliver_to_channels(
    content=content,
    briefing_type='morning',
    channels_config=delivery_config,
    metadata={'date': context['today_date']}
)
```

---

## API Reference

### DeliveryChannel (Abstract Base Class)

```python
class DeliveryChannel(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None)

    @abstractmethod
    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool

    def log_delivery(self, briefing_type: str, success: bool,
                     details: str = "")
```

### CLIChannel

```python
class CLIChannel(DeliveryChannel):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    # Config: {'color': bool}

    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool
```

### FileChannel

```python
class FileChannel(DeliveryChannel):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    # Config: {
    #   'output_dir': str,
    #   'filename_pattern': str  # Variables: {date}, {type}
    # }

    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool
```

### NotificationChannel

```python
class NotificationChannel(DeliveryChannel):
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    # Config: {'summary_only': bool}

    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool
```

### Factory Function

```python
def create_delivery_channel(
    channel_type: str,  # 'cli', 'file', 'notification'
    config: Optional[Dict[str, Any]] = None
) -> Optional[DeliveryChannel]
```

### Multi-Channel Delivery

```python
def deliver_to_channels(
    content: str,
    briefing_type: str,
    channels_config: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, bool]  # Returns {channel_type: success_status}
```

---

## Extending the System

### Creating a Custom Channel

To create a new delivery channel, inherit from `DeliveryChannel` and implement the `deliver()` method:

```python
from Tools.delivery_channels import DeliveryChannel

class EmailChannel(DeliveryChannel):
    """Send briefings via email."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.smtp_server = self.config.get('smtp_server', 'localhost')
        self.from_addr = self.config.get('from_addr')
        self.to_addr = self.config.get('to_addr')

    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send briefing via email."""
        try:
            # Email sending logic here
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(content)
            msg['Subject'] = f"{briefing_type.capitalize()} Briefing"
            msg['From'] = self.from_addr
            msg['To'] = self.to_addr

            with smtplib.SMTP(self.smtp_server) as server:
                server.send_message(msg)

            self.log_delivery(briefing_type, True, f"Sent to {self.to_addr}")
            return True

        except Exception as e:
            self.log_delivery(briefing_type, False, f"Error: {e}")
            return False
```

### Registering Custom Channels

Update the `create_delivery_channel` factory function:

```python
# In Tools/delivery_channels.py

def create_delivery_channel(channel_type: str, config: Optional[Dict[str, Any]] = None):
    channels = {
        'cli': CLIChannel,
        'file': FileChannel,
        'notification': NotificationChannel,
        'email': EmailChannel,  # Add your custom channel
    }

    channel_class = channels.get(channel_type.lower())
    if channel_class:
        return channel_class(config)
    return None
```

---

## Testing

### Manual Testing

Run the example script to test all channels:

```bash
python example_delivery_channels.py
```

### Unit Tests

Run the comprehensive test suite:

```bash
python -m pytest tests/unit/test_delivery_channels.py -v
```

### Integration Testing

Test with the briefing scheduler:

```bash
# Test morning briefing delivery
python -m commands.pa.briefing morning

# Check configured channels
cat config/briefing_schedule.json | grep -A 10 "delivery"
```

---

## Troubleshooting

### Issue: CLI output has no colors

**Cause:** Either `color: false` in config, or output is not a TTY (e.g., piped to file)

**Solution:**
- Enable color in config: `{"cli": {"color": true}}`
- Run directly in terminal (not piped)

### Issue: File channel fails to create files

**Cause:** Permission issues or invalid path

**Solution:**
- Check directory permissions
- Ensure parent directories exist or let FileChannel create them
- Verify path in config is valid

### Issue: Notifications don't appear

**Cause:** Notification system not installed or not available

**Solution:**
- macOS: Install `terminal-notifier` via Homebrew
- Linux: Install `libnotify-bin` or `notify-send`
- Check `notification_available` property

### Issue: Multi-channel delivery partially fails

**Cause:** One or more channels have configuration issues

**Solution:**
- Check the return value dictionary to see which channels failed
- Review logs for specific error messages
- Test each channel individually to isolate the issue

---

## Best Practices

1. **Always handle delivery failures gracefully**
   - Check return values from `deliver()` calls
   - Log failures for debugging
   - Don't fail the entire briefing if one channel fails

2. **Use configuration files for channel settings**
   - Keep channel configs in `briefing_schedule.json`
   - Makes it easy to enable/disable channels
   - Supports environment-specific configurations

3. **Test notifications before relying on them**
   - Check `notification_available` property
   - Provide fallbacks (CLI or File) if notifications fail

4. **Use metadata for enhanced delivery**
   - Pass priorities for notification summaries
   - Include dates for accurate file naming
   - Add custom metadata for future channel extensions

5. **Consider user experience**
   - CLI: Use colors for important information
   - File: Include metadata headers for searching
   - Notifications: Keep summaries brief and actionable

---

## Future Enhancements

Potential additions to the delivery channel system:

- **EmailChannel**: Send briefings via SMTP or email API
- **SlackChannel**: Post to Slack channels or DMs
- **WebhookChannel**: POST to custom webhooks
- **AudioChannel**: Text-to-speech announcements
- **MobileChannel**: Push notifications to mobile devices

All of these would follow the same `DeliveryChannel` interface and integrate seamlessly with the existing system.

---

## Related Documentation

- [Briefing Engine Guide](./BRIEFING_COMMAND.md)
- [Configuration Guide](../config/README.md)
- [Scheduler Documentation](./SCHEDULER_GUIDE.md)
- [Template Customization](../Templates/README.md)
