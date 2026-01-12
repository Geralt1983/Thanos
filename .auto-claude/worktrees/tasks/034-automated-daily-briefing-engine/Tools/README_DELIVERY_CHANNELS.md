# Delivery Channels Module

## Overview

The `delivery_channels.py` module provides a flexible abstraction for delivering briefing content through multiple channels simultaneously. This allows briefings to be displayed in the terminal, saved to files, sent as notifications, or delivered through any custom channel you implement.

## Quick Start

```python
from Tools.delivery_channels import deliver_to_channels

# Configure channels
channels_config = {
    'cli': {
        'enabled': True,
        'color': True
    },
    'file': {
        'enabled': True,
        'output_dir': 'History/DailyBriefings',
        'filename_pattern': '{date}_{type}_briefing.md'
    }
}

# Deliver to all enabled channels
results = deliver_to_channels(
    content="# Morning Briefing\n\nYour content here...",
    briefing_type="morning",
    channels_config=channels_config,
    metadata={'date': '2026-01-11'}
)

# Check results
for channel, success in results.items():
    print(f"{channel}: {'✓' if success else '✗'}")
```

## Available Channels

### 1. CLIChannel
Prints briefings to stdout with optional ANSI color formatting.

**Configuration:**
```json
{
  "cli": {
    "enabled": true,
    "color": true
  }
}
```

**Features:**
- Automatic TTY detection (disables colors for piped output)
- Markdown header formatting with colors
- Clean, formatted output with separators

### 2. FileChannel
Saves briefings to the filesystem.

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

**Features:**
- Automatic directory creation
- Customizable filename patterns
- YAML frontmatter metadata
- UTF-8 encoding

### 3. NotificationChannel
Sends desktop notifications (macOS/Linux).

**Configuration:**
```json
{
  "notification": {
    "enabled": false,
    "summary_only": true
  }
}
```

**Features:**
- Platform detection (macOS/Linux)
- Graceful degradation when unavailable
- Summary mode (top 3 priorities)
- Multiple backend support

## Architecture

### Base Class

All channels inherit from `DeliveryChannel`:

```python
class DeliveryChannel(ABC):
    @abstractmethod
    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Deliver briefing content. Returns True on success."""
        pass
```

### Factory Function

Create channels dynamically:

```python
from Tools.delivery_channels import create_delivery_channel

cli = create_delivery_channel('cli', {'color': True})
file = create_delivery_channel('file', {'output_dir': 'output'})
notification = create_delivery_channel('notification', {'summary_only': True})
```

### Multi-Channel Delivery

Deliver to multiple channels at once:

```python
from Tools.delivery_channels import deliver_to_channels

results = deliver_to_channels(
    content=briefing_content,
    briefing_type='morning',
    channels_config={
        'cli': {'enabled': True, 'color': True},
        'file': {'enabled': True, 'output_dir': 'History/DailyBriefings'}
    }
)
```

## Integration

### With BriefingEngine

```python
from Tools.briefing_engine import BriefingEngine
from Tools.delivery_channels import deliver_to_channels

# Generate briefing
engine = BriefingEngine()
context = engine.gather_context()
content = engine.render_briefing('morning', context)

# Deliver through channels
deliver_to_channels(
    content=content,
    briefing_type='morning',
    channels_config=config['delivery']
)
```

### With BriefingScheduler

The scheduler automatically uses delivery channels based on configuration:

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "delivery_channels": ["cli", "file"]
    }
  },
  "delivery": {
    "cli": {"enabled": true, "color": true},
    "file": {"enabled": true, "output_dir": "History/DailyBriefings"}
  }
}
```

### With Manual Command

The `commands/pa/briefing.py` command uses delivery channels:

```bash
python -m commands.pa.briefing morning
# Automatically delivers via configured channels
```

## Extending with Custom Channels

Create a custom delivery channel by inheriting from `DeliveryChannel`:

```python
from Tools.delivery_channels import DeliveryChannel

class EmailChannel(DeliveryChannel):
    def deliver(self, content: str, briefing_type: str,
                metadata: Optional[Dict[str, Any]] = None) -> bool:
        try:
            # Your email delivery logic here
            send_email(content)
            self.log_delivery(briefing_type, True, "Email sent")
            return True
        except Exception as e:
            self.log_delivery(briefing_type, False, f"Error: {e}")
            return False
```

Register it in the factory:

```python
# In create_delivery_channel()
channels = {
    'cli': CLIChannel,
    'file': FileChannel,
    'notification': NotificationChannel,
    'email': EmailChannel,  # Add your channel
}
```

## Testing

### Run Unit Tests

```bash
python -m pytest tests/unit/test_delivery_channels.py -v
```

### Run Examples

```bash
python example_delivery_channels.py
```

## Files

- `Tools/delivery_channels.py` - Core implementation (500+ lines)
- `tests/unit/test_delivery_channels.py` - Unit tests (500+ lines)
- `example_delivery_channels.py` - Usage examples
- `docs/DELIVERY_CHANNELS.md` - Comprehensive documentation

## Acceptance Criteria

All acceptance criteria for subtask 4.1 have been met:

- ✅ DeliveryChannel base class with deliver() method
- ✅ CLIChannel prints to stdout with colors
- ✅ FileChannel writes to configured path
- ✅ Channels configurable in briefing_schedule.json
- ✅ Can enable multiple channels simultaneously
- ✅ Each channel logs successful delivery

## See Also

- [Comprehensive Documentation](../docs/DELIVERY_CHANNELS.md)
- [Briefing Engine](./briefing_engine.py)
- [Briefing Scheduler](./briefing_scheduler.py)
- [Configuration Guide](../config/README.md)
