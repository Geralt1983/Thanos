# Automated Daily Briefing Engine - Architecture & Extension Guide

**For Developers & Contributors**

**Version:** 1.0
**Last Updated:** January 2026

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Extension Points](#extension-points)
5. [Adding Custom Sections](#adding-custom-sections)
6. [Creating Custom Delivery Channels](#creating-custom-delivery-channels)
7. [Extending Pattern Analysis](#extending-pattern-analysis)
8. [Configuration System](#configuration-system)
9. [Testing Strategy](#testing-strategy)
10. [Code Examples](#code-examples)

---

## Architecture Overview

### Design Principles

The Automated Daily Briefing Engine is built on these core principles:

1. **Modularity**: Components are loosely coupled and can be extended independently
2. **Configurability**: All behavior is configurable without code changes
3. **Extensibility**: Plugin-style architecture for sections, channels, and analyzers
4. **Reliability**: Graceful degradation when optional dependencies are unavailable
5. **Testability**: Comprehensive test coverage with clear separation of concerns

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────────┐         ┌─────────────────┐          │
│  │ briefing command │         │ briefing_config │          │
│  │  (manual runs)   │         │  (config mgmt)  │          │
│  └──────────────────┘         └─────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                   Orchestration Layer                        │
│  ┌───────────────────────────────────────────────┐          │
│  │         BriefingScheduler                     │          │
│  │  - Time-based execution                       │          │
│  │  - Duplicate prevention                       │          │
│  │  - Multi-channel delivery                     │          │
│  └───────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Core Engine Layer                         │
│  ┌───────────────────────────────────────────────┐          │
│  │           BriefingEngine                      │          │
│  │  ┌──────────────────────────────────────┐    │          │
│  │  │  Context Gathering                   │    │          │
│  │  │  - Read State files                  │    │          │
│  │  │  - Parse commitments & tasks         │    │          │
│  │  │  - Collect focus areas               │    │          │
│  │  └──────────────────────────────────────┘    │          │
│  │  ┌──────────────────────────────────────┐    │          │
│  │  │  Priority Ranking                    │    │          │
│  │  │  - Deadline urgency                  │    │          │
│  │  │  - Energy-aware sorting              │    │          │
│  │  │  - Pattern-based boosts              │    │          │
│  │  └──────────────────────────────────────┘    │          │
│  │  ┌──────────────────────────────────────┐    │          │
│  │  │  Section Management                  │    │          │
│  │  │  - Built-in sections                 │    │          │
│  │  │  - Custom section providers          │    │          │
│  │  │  - Conditional rendering             │    │          │
│  │  └──────────────────────────────────────┘    │          │
│  │  ┌──────────────────────────────────────┐    │          │
│  │  │  Template Rendering                  │    │          │
│  │  │  - Jinja2 templates                  │    │          │
│  │  │  - Fallback simple rendering         │    │          │
│  │  └──────────────────────────────────────┘    │          │
│  └───────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                  Intelligence Layer                          │
│  ┌──────────────────┐  ┌─────────────────┐                 │
│  │ HealthStateTrack │  │ PatternAnalyzer │                 │
│  │  - Energy levels │  │  - Completion   │                 │
│  │  - Sleep tracking│  │    history      │                 │
│  │  - Med timing   │  │  - Day/time     │                 │
│  │  - Trends       │  │    patterns     │                 │
│  └──────────────────┘  └─────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                    Delivery Layer                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   CLI    │  │   File   │  │  Notify  │  │StateSync │   │
│  │ Channel  │  │ Channel  │  │ Channel  │  │ Channel  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            ▲
                            │
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                              │
│  State Files           Config Files         History          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │Commitments.md│    │briefing_     │    │DailyBriefings│  │
│  │ThisWeek.md   │    │  schedule.json    │  /YYYY-MM-DD │  │
│  │CurrentFocus  │    │briefing_     │    │HealthLog.json│  │
│  │HealthLog.json│    │  config.json│     │BriefingPatter│  │
│  │BriefingPatter│    └──────────────┘    │  ns.json     │  │
│  │  ns.json     │                        └──────────────┘  │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. BriefingEngine

**Location:** `Tools/briefing_engine.py`

**Purpose:** Core engine that orchestrates briefing generation.

**Key Responsibilities:**
- Read and parse State files (Commitments.md, ThisWeek.md, CurrentFocus.md)
- Gather context from all data sources
- Rank priorities intelligently
- Manage section providers (built-in and custom)
- Render templates with Jinja2
- Provide structured data for delivery channels

**Key Methods:**

```python
class BriefingEngine:
    def __init__(self, state_dir, templates_dir, config):
        """Initialize with paths and configuration"""

    def gather_context(self) -> Dict[str, Any]:
        """Gather all context from State files"""

    def rank_priorities(self, tasks, briefing_type, energy_level) -> List[Dict]:
        """Intelligently rank tasks by priority"""

    def generate_briefing(self, briefing_type, energy_level) -> str:
        """Generate complete briefing content"""

    def register_section_provider(self, section_id, provider_func):
        """Register custom section data provider"""
```

**Extension Points:**
- Custom section providers via `register_section_provider()`
- Priority ranking algorithm can be extended via config
- Template system is fully customizable

---

### 2. BriefingScheduler

**Location:** `Tools/briefing_scheduler.py`

**Purpose:** Time-based orchestration and execution.

**Key Responsibilities:**
- Monitor time and trigger briefings at configured schedules
- Prevent duplicate execution within the same day
- Coordinate multi-channel delivery
- Manage run state tracking
- Handle health state prompts

**Key Methods:**

```python
class BriefingScheduler:
    def __init__(self, config_path, state_dir):
        """Initialize with configuration"""

    def should_run_briefing(self, briefing_type) -> bool:
        """Check if briefing should run now"""

    def run_briefing(self, briefing_type) -> bool:
        """Execute briefing generation and delivery"""

    def run_scheduler(self, mode='continuous'):
        """Main scheduler loop (continuous or once)"""
```

**Configuration:**
- `config/briefing_schedule.json` - Timing and day-of-week settings
- Run state tracked in `State/briefing_run_state.json`

---

### 3. HealthStateTracker

**Location:** `Tools/health_state_tracker.py`

**Purpose:** Track and analyze health metrics.

**Key Responsibilities:**
- Record daily energy levels (1-10 scale)
- Track sleep hours and medication timing
- Calculate 7-day trends and averages
- Provide energy-aware task recommendations
- Detect patterns and insights

**Key Methods:**

```python
class HealthStateTracker:
    def record_health_state(self, energy_level, sleep_hours, med_time):
        """Record today's health state"""

    def get_health_summary(self) -> Dict[str, Any]:
        """Get current health state and 7-day trends"""

    def get_energy_recommendations(self, tasks, energy_level) -> List[str]:
        """Recommend tasks based on current energy"""
```

**Data Format:**

```json
{
  "entries": [
    {
      "date": "2026-01-13",
      "energy_level": 7,
      "sleep_hours": 7.5,
      "medication_time": "07:15",
      "day_of_week": "Monday"
    }
  ]
}
```

---

### 4. PatternAnalyzer

**Location:** `Tools/pattern_analyzer.py`

**Purpose:** Learn from task completion patterns.

**Key Responsibilities:**
- Record task completion events
- Identify day-of-week patterns (e.g., "admin tasks on Fridays")
- Detect time-of-day preferences
- Calculate pattern-based priority boosts
- Generate weekly pattern summaries

**Key Methods:**

```python
class PatternAnalyzer:
    def record_task_completion(self, task_title, category, time, date):
        """Record a task completion event"""

    def get_task_patterns(self, task_title) -> Dict[str, Any]:
        """Get completion patterns for specific task"""

    def get_day_of_week_boost(self, task_title, day_of_week) -> float:
        """Calculate priority boost for day-of-week pattern"""

    def generate_weekly_summary(self) -> Dict[str, Any]:
        """Generate weekly pattern insights"""
```

**Data Format:**

```json
{
  "task_completions": [
    {
      "task_title": "Weekly team meeting prep",
      "task_category": "work",
      "completion_date": "2026-01-13",
      "completion_time": "09:30",
      "day_of_week": "Monday",
      "hour": 9,
      "time_of_day": "morning"
    }
  ]
}
```

---

### 5. Delivery Channels

**Location:** `Tools/delivery_channels.py`

**Purpose:** Abstract delivery mechanism for briefings.

**Architecture:** Plugin-style with base abstract class.

**Base Class:**

```python
class DeliveryChannel(ABC):
    @abstractmethod
    def deliver(self, content: str, briefing_type: str, metadata: Dict) -> bool:
        """Deliver briefing through this channel"""
        pass
```

**Built-in Channels:**

1. **CLIChannel** - Terminal output with ANSI colors
2. **FileChannel** - Save to `History/DailyBriefings/YYYY-MM-DD_TYPE.md`
3. **NotificationChannel** - Desktop notifications (macOS/Linux)
4. **StateSyncChannel** - Update `State/Today.md` with briefing content

**Extension:** See [Creating Custom Delivery Channels](#creating-custom-delivery-channels)

---

## Data Flow

### Morning Briefing Generation Flow

```
1. Scheduler triggers at configured time (e.g., 07:00)
   │
   ├─ Check: Has morning briefing run today?
   │   └─ If yes: Skip (duplicate prevention)
   │   └─ If no: Continue
   │
2. Prompt for health state (if enabled and no recent entry)
   │
   ├─ Energy level (1-10)
   ├─ Sleep hours
   └─ Medication time
   │
3. BriefingEngine.gather_context()
   │
   ├─ Read Commitments.md → Parse tasks and deadlines
   ├─ Read ThisWeek.md → Parse weekly goals
   ├─ Read CurrentFocus.md → Parse focus areas
   ├─ Get health state from HealthLog.json
   └─ Get patterns from BriefingPatterns.json
   │
4. BriefingEngine.rank_priorities()
   │
   ├─ Calculate deadline urgency (overdue > due today > due this week)
   ├─ Apply day-of-week boosts (e.g., Monday work boost)
   ├─ Apply pattern-based boosts (frequently done on this day)
   ├─ Apply energy-aware sorting (complex tasks for high energy)
   └─ Select top 3 priorities
   │
5. Execute section providers
   │
   ├─ priorities_section() → Top 3 with reasoning
   ├─ health_section() → Energy, sleep, trends
   ├─ commitments_section() → Active commitments
   ├─ quick_wins_section() → Low-effort tasks
   └─ [custom sections if registered]
   │
6. BriefingEngine.generate_briefing()
   │
   ├─ Load template: Templates/briefing_morning.md
   ├─ Render with Jinja2
   └─ Return formatted markdown
   │
7. Multi-channel delivery
   │
   ├─ CLIChannel.deliver() → Print to terminal
   ├─ FileChannel.deliver() → Save to History/DailyBriefings/
   ├─ NotificationChannel.deliver() → Show desktop notification
   └─ StateSyncChannel.deliver() → Update State/Today.md
   │
8. Update run state
   │
   └─ Record completion in briefing_run_state.json
```

### Evening Briefing Flow (Sunday)

Sunday evening briefings include an additional step:

```
[Steps 1-6 same as morning]
│
7. PatternAnalyzer.generate_weekly_summary()
   │
   ├─ Analyze task completions from past 7 days
   ├─ Identify most productive days/times
   ├─ Calculate category breakdown
   ├─ Detect pattern changes
   └─ Generate insights and recommendations
   │
8. Append weekly summary to briefing content
   │
9. Multi-channel delivery
   │
[Continue as morning flow]
```

---

## Extension Points

### 1. Custom Section Providers

**Use Case:** Add custom content to briefings (e.g., weather, stock prices, GitHub notifications)

**How it Works:**

Section providers are functions that return data for a specific section:

```python
def my_section_provider(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Custom section provider.

    Args:
        context: Full briefing context (commitments, tasks, health, etc.)

    Returns:
        Dict with keys:
        - 'title': Section title (str)
        - 'content': Section data (can be str, list, dict, etc.)
        - 'enabled': Whether to include section (bool, optional)
    """
    return {
        'title': '☁️ Weather Forecast',
        'content': fetch_weather_data(),
        'enabled': True
    }
```

**Registration:**

```python
from Tools.briefing_engine import BriefingEngine

engine = BriefingEngine()
engine.register_section_provider('weather', my_section_provider)
```

**Full Example:** See [Adding Custom Sections](#adding-custom-sections)

---

### 2. Custom Delivery Channels

**Use Case:** Deliver briefings via email, Slack, SMS, etc.

**How it Works:**

Subclass `DeliveryChannel` and implement the `deliver()` method:

```python
from Tools.delivery_channels import DeliveryChannel

class EmailChannel(DeliveryChannel):
    def deliver(self, content: str, briefing_type: str, metadata: Dict) -> bool:
        """Send briefing via email"""
        try:
            send_email(
                to=self.config['email'],
                subject=f"{briefing_type.title()} Briefing",
                body=content
            )
            self.log_delivery(briefing_type, True)
            return True
        except Exception as e:
            self.log_delivery(briefing_type, False, str(e))
            return False
```

**Full Example:** See [Creating Custom Delivery Channels](#creating-custom-delivery-channels)

---

### 3. Custom Priority Ranking

**Use Case:** Customize how tasks are ranked and prioritized

**How it Works:**

The priority ranking algorithm can be customized via configuration:

```json
{
  "priorities": {
    "max_items": 3,
    "weights": {
      "deadline": 1.0,
      "day_of_week": 0.3,
      "patterns": 0.4,
      "energy": 0.2
    }
  }
}
```

**Extending the Algorithm:**

For more complex customization, subclass `BriefingEngine` and override `rank_priorities()`:

```python
from Tools.briefing_engine import BriefingEngine

class CustomBriefingEngine(BriefingEngine):
    def rank_priorities(self, tasks, briefing_type, energy_level):
        """Custom priority ranking logic"""
        # Your custom algorithm here
        ranked = super().rank_priorities(tasks, briefing_type, energy_level)

        # Add custom scoring
        for task in ranked:
            task['custom_score'] = calculate_custom_score(task)

        return sorted(ranked, key=lambda t: t['custom_score'], reverse=True)
```

---

### 4. Pattern Analysis Extensions

**Use Case:** Track custom metrics or patterns

**How it Works:**

The `PatternAnalyzer` can be extended to track additional data:

```python
from Tools.pattern_analyzer import PatternAnalyzer

class ExtendedPatternAnalyzer(PatternAnalyzer):
    def record_task_with_duration(self, task_title, duration_minutes):
        """Track task completion with duration"""
        completion = {
            **self._create_base_completion(task_title),
            'duration_minutes': duration_minutes,
            'estimated_duration': self._estimate_duration(task_title)
        }
        self.patterns_data['task_completions'].append(completion)
        self._save_patterns()

    def get_average_duration(self, task_title) -> float:
        """Calculate average duration for task type"""
        completions = [
            c for c in self.patterns_data['task_completions']
            if c['task_title'] == task_title and 'duration_minutes' in c
        ]
        if not completions:
            return 0.0
        return sum(c['duration_minutes'] for c in completions) / len(completions)
```

---

### 5. Template System

**Use Case:** Customize briefing format and styling

**How it Works:**

Templates use Jinja2 syntax and have access to full context:

**Available Context Variables:**

```python
{
    # Date/time
    'today_date': '2026-01-13',
    'day_of_week': 'Monday',
    'is_weekend': False,

    # Priorities
    'top_priorities': [...],
    'priority_count': 3,

    # Tasks and commitments
    'commitments': [...],
    'active_commitments': [...],
    'this_week_tasks': [...],

    # Focus areas
    'current_focus': {...},

    # Health state
    'health_state': {
        'current': {...},
        'trend': {...},
        'recommendations': [...]
    },

    # Patterns (if enabled)
    'patterns': {
        'weekly_summary': {...},
        'insights': [...]
    },

    # Custom sections
    'custom_sections': {
        'section_id': {...}
    }
}
```

**Example Template:**

```jinja2
# {{ greeting }} - {{ day_of_week }}, {{ today_date | format_date }}

{% if health_state %}
## 🏥 Health State
**Energy:** {{ health_state.current.energy_level }}/10
**Sleep:** {{ health_state.current.sleep_hours }} hours

{{ health_state.trend.summary }}
{% endif %}

## 🎯 Top Priorities

{% for task in top_priorities %}
**{{ loop.index }}. {{ task.title }}**
   - {{ task.priority_reason }}
{% endfor %}

{% if custom_sections.weather %}
{{ custom_sections.weather.content }}
{% endif %}
```

---

## Adding Custom Sections

### Example: GitHub Activity Section

**Step 1: Create the section provider function**

```python
# custom_sections/github_section.py

import requests
from typing import Dict, Any

def github_activity_provider(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch recent GitHub activity for the user.

    Args:
        context: Full briefing context

    Returns:
        Section data with GitHub activity
    """
    # Get GitHub username from config or environment
    username = context.get('config', {}).get('github_username', 'myusername')

    try:
        # Fetch notifications from GitHub API
        response = requests.get(
            f'https://api.github.com/users/{username}/events',
            headers={'Accept': 'application/vnd.github.v3+json'},
            timeout=5
        )

        if response.status_code == 200:
            events = response.json()[:5]  # Get last 5 events

            activity_summary = []
            for event in events:
                event_type = event['type']
                repo = event['repo']['name']

                if event_type == 'PushEvent':
                    commits = len(event['payload']['commits'])
                    activity_summary.append(f"📝 Pushed {commits} commits to {repo}")
                elif event_type == 'PullRequestEvent':
                    action = event['payload']['action']
                    activity_summary.append(f"🔀 {action.title()} PR in {repo}")
                elif event_type == 'IssuesEvent':
                    action = event['payload']['action']
                    activity_summary.append(f"📋 {action.title()} issue in {repo}")

            return {
                'title': '💻 GitHub Activity (Last 24h)',
                'content': activity_summary if activity_summary else ['No recent activity'],
                'enabled': True
            }
        else:
            # API error - disable section
            return {'enabled': False}

    except Exception as e:
        print(f"Warning: Failed to fetch GitHub activity: {e}")
        return {'enabled': False}
```

**Step 2: Register the section provider**

```python
# custom_sections/__init__.py

from Tools.briefing_engine import BriefingEngine
from .github_section import github_activity_provider

def register_custom_sections(engine: BriefingEngine):
    """Register all custom section providers"""
    engine.register_section_provider('github_activity', github_activity_provider)
```

**Step 3: Enable in configuration**

```json
{
  "content": {
    "sections": {
      "enabled": [
        "priorities",
        "health",
        "commitments",
        "github_activity"
      ]
    }
  },
  "github_username": "yourname"
}
```

**Step 4: Add to template**

```jinja2
{% if custom_sections.github_activity %}
## {{ custom_sections.github_activity.title }}

{% for item in custom_sections.github_activity.content %}
- {{ item }}
{% endfor %}
{% endif %}
```

**Step 5: Use in briefing generation**

```python
from Tools.briefing_engine import BriefingEngine
from custom_sections import register_custom_sections

# Load config
with open('config/briefing_config.json') as f:
    config = json.load(f)

# Create engine
engine = BriefingEngine(config=config)

# Register custom sections
register_custom_sections(engine)

# Generate briefing
briefing = engine.generate_briefing('morning')
print(briefing)
```

---

## Creating Custom Delivery Channels

### Example: Slack Delivery Channel

**Step 1: Create the channel class**

```python
# custom_channels/slack_channel.py

import requests
from typing import Dict, Any, Optional
from Tools.delivery_channels import DeliveryChannel

class SlackChannel(DeliveryChannel):
    """
    Delivery channel that posts briefings to Slack.

    Configuration:
        webhook_url: Slack webhook URL
        channel: Channel name (optional)
        username: Bot username (optional)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # Validate required config
        if not self.config.get('webhook_url'):
            raise ValueError("SlackChannel requires 'webhook_url' in config")

    def deliver(self, content: str, briefing_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Post briefing to Slack channel.

        Args:
            content: Briefing content (markdown)
            briefing_type: Type of briefing ('morning', 'evening')
            metadata: Optional metadata

        Returns:
            True if posted successfully, False otherwise
        """
        try:
            # Format content for Slack
            formatted_content = self._format_for_slack(content)

            # Prepare Slack message
            payload = {
                'text': f"*{briefing_type.title()} Briefing*",
                'blocks': [
                    {
                        'type': 'header',
                        'text': {
                            'type': 'plain_text',
                            'text': f"{self._get_emoji(briefing_type)} {briefing_type.title()} Briefing"
                        }
                    },
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': formatted_content
                        }
                    }
                ]
            }

            # Add optional fields
            if self.config.get('channel'):
                payload['channel'] = self.config['channel']
            if self.config.get('username'):
                payload['username'] = self.config['username']

            # Post to Slack
            response = requests.post(
                self.config['webhook_url'],
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                self.log_delivery(briefing_type, True, "Posted to Slack")
                return True
            else:
                self.log_delivery(briefing_type, False, f"Slack API error: {response.status_code}")
                return False

        except Exception as e:
            self.log_delivery(briefing_type, False, f"Error: {e}")
            return False

    def _format_for_slack(self, content: str) -> str:
        """Convert markdown to Slack's mrkdwn format"""
        # Truncate if too long (Slack has limits)
        if len(content) > 3000:
            content = content[:2950] + "\n\n_[Truncated - see full briefing in History]_"

        # Convert markdown headers to bold
        content = content.replace('## ', '*')
        content = content.replace('\n*', '\n\n*')

        return content

    def _get_emoji(self, briefing_type: str) -> str:
        """Get appropriate emoji for briefing type"""
        emojis = {
            'morning': '☀️',
            'evening': '🌙',
            'weekly': '📊'
        }
        return emojis.get(briefing_type, '📋')
```

**Step 2: Configure the channel**

```json
{
  "delivery": {
    "channels": {
      "cli": {"enabled": true},
      "file": {"enabled": true},
      "slack": {
        "enabled": true,
        "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
        "channel": "#daily-briefings",
        "username": "Briefing Bot"
      }
    }
  }
}
```

**Step 3: Register and use in scheduler**

```python
# Tools/briefing_scheduler.py (modified)

from custom_channels.slack_channel import SlackChannel

class BriefingScheduler:
    def _setup_delivery_channels(self):
        """Initialize delivery channels from config"""
        channels = []

        # ... existing channels ...

        # Add Slack channel if enabled
        slack_config = self.config.get('delivery', {}).get('channels', {}).get('slack', {})
        if slack_config.get('enabled'):
            try:
                channels.append(SlackChannel(slack_config))
                print("✓ Slack delivery channel enabled")
            except Exception as e:
                print(f"Warning: Failed to initialize Slack channel: {e}")

        return channels
```

---

## Extending Pattern Analysis

### Example: Task Duration Tracking

**Step 1: Extend PatternAnalyzer**

```python
# extensions/duration_pattern_analyzer.py

from Tools.pattern_analyzer import PatternAnalyzer
from typing import Dict, Any, Optional
from datetime import datetime

class DurationPatternAnalyzer(PatternAnalyzer):
    """
    Extended pattern analyzer that tracks task durations.
    """

    def record_task_with_duration(
        self,
        task_title: str,
        duration_minutes: int,
        task_category: Optional[str] = None
    ) -> bool:
        """
        Record task completion with duration tracking.

        Args:
            task_title: Task title
            duration_minutes: How long the task took
            task_category: Optional category

        Returns:
            True if recorded successfully
        """
        # Create base completion record
        base_record = self.record_task_completion(task_title, task_category)

        if not base_record:
            return False

        # Add duration data to last completion
        last_completion = self.patterns_data['task_completions'][-1]
        last_completion['duration_minutes'] = duration_minutes

        # Calculate and store accuracy of estimates
        estimated = self.estimate_duration(task_title)
        if estimated:
            accuracy = abs(duration_minutes - estimated) / estimated
            last_completion['estimate_accuracy'] = 1.0 - min(accuracy, 1.0)

        self._save_patterns()
        return True

    def estimate_duration(self, task_title: str) -> Optional[float]:
        """
        Estimate task duration based on historical data.

        Args:
            task_title: Task to estimate

        Returns:
            Estimated duration in minutes, or None if no data
        """
        # Find similar tasks
        completions = [
            c for c in self.patterns_data['task_completions']
            if c.get('task_title') == task_title and 'duration_minutes' in c
        ]

        if not completions:
            # Try to find similar by category
            category = self._infer_task_category(task_title)
            completions = [
                c for c in self.patterns_data['task_completions']
                if c.get('task_category') == category and 'duration_minutes' in c
            ]

        if not completions:
            return None

        # Calculate weighted average (recent completions weighted more)
        total_weight = 0
        weighted_sum = 0

        for i, completion in enumerate(reversed(completions[:10])):
            weight = 1.0 / (i + 1)  # More recent = higher weight
            weighted_sum += completion['duration_minutes'] * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else None

    def get_duration_insights(self) -> Dict[str, Any]:
        """
        Generate insights about task durations.

        Returns:
            Dict with duration insights and statistics
        """
        completions_with_duration = [
            c for c in self.patterns_data['task_completions']
            if 'duration_minutes' in c
        ]

        if not completions_with_duration:
            return {'message': 'No duration data available'}

        # Calculate statistics
        durations = [c['duration_minutes'] for c in completions_with_duration]
        avg_duration = sum(durations) / len(durations)

        # Find patterns
        by_time_of_day = {}
        for completion in completions_with_duration:
            tod = completion.get('time_of_day', 'unknown')
            if tod not in by_time_of_day:
                by_time_of_day[tod] = []
            by_time_of_day[tod].append(completion['duration_minutes'])

        # Calculate averages by time of day
        tod_averages = {
            tod: sum(durations) / len(durations)
            for tod, durations in by_time_of_day.items()
        }

        return {
            'total_tasks_tracked': len(completions_with_duration),
            'average_duration_minutes': round(avg_duration, 1),
            'by_time_of_day': {
                tod: {
                    'count': len(durations),
                    'average_minutes': round(avg, 1)
                }
                for tod, avg in tod_averages.items()
            },
            'insights': self._generate_duration_insights(tod_averages, avg_duration)
        }

    def _generate_duration_insights(self, tod_averages: Dict, overall_avg: float) -> list:
        """Generate human-readable insights from duration data"""
        insights = []

        # Find best time of day
        if tod_averages:
            best_time = min(tod_averages.items(), key=lambda x: x[1])
            insights.append(
                f"You're fastest in the {best_time[0]} "
                f"({best_time[1]:.1f} min avg vs {overall_avg:.1f} overall)"
            )

        return insights
```

**Step 2: Use in briefing generation**

```python
# In BriefingEngine, add duration estimates to priorities

def rank_priorities(self, tasks, briefing_type, energy_level):
    """Rank priorities with duration estimates"""
    ranked = super().rank_priorities(tasks, briefing_type, energy_level)

    # Add duration estimates if available
    if isinstance(self.pattern_analyzer, DurationPatternAnalyzer):
        for task in ranked:
            estimate = self.pattern_analyzer.estimate_duration(task['title'])
            if estimate:
                task['estimated_duration'] = f"{int(estimate)} min"

    return ranked
```

---

## Configuration System

### Configuration Files

**1. `config/briefing_schedule.json`** - Scheduling configuration

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "days": {
        "monday": true,
        "tuesday": true,
        "wednesday": true,
        "thursday": true,
        "friday": true,
        "saturday": false,
        "sunday": false
      }
    },
    "evening": {
      "enabled": true,
      "time": "19:00",
      "days": {
        "sunday": true
      }
    }
  },
  "duplicate_prevention": {
    "enabled": true,
    "reset_time": "03:00"
  }
}
```

**2. `config/briefing_config.json`** - Content and behavior configuration

```json
{
  "priorities": {
    "max_items": 3,
    "include_reasoning": true,
    "energy_aware": true
  },
  "content": {
    "sections": {
      "enabled": [
        "priorities",
        "health",
        "commitments",
        "tasks",
        "quick_wins"
      ]
    },
    "day_of_week_content": {
      "enabled": true
    },
    "adaptive_content": {
      "enabled": true,
      "inactivity_threshold_days": 3
    }
  },
  "patterns": {
    "enabled": true,
    "minimum_days_required": 14,
    "influence_level": "medium"
  },
  "health": {
    "enabled": true,
    "prompts": {
      "enabled": true,
      "require_recent_entry": true,
      "hours_considered_recent": 12
    }
  },
  "delivery": {
    "channels": {
      "cli": {"enabled": true, "color": true},
      "file": {"enabled": true},
      "notifications": {"enabled": true},
      "state_sync": {"enabled": true}
    }
  }
}
```

### Configuration Validation

**Use `config_validator.py` to validate configuration:**

```bash
python3 -m Tools.config_validator config/briefing_schedule.json
python3 -m Tools.config_validator config/briefing_config.json
```

**Validation Rules:**
- Time format: `HH:MM` (24-hour)
- Boolean fields must be `true` or `false`
- Enums must match allowed values
- Required fields must be present

---

## Testing Strategy

### Test Structure

```
tests/
├── unit/
│   ├── test_briefing_engine.py       # 85+ tests
│   ├── test_health_state_tracker.py  # 45+ tests
│   ├── test_pattern_analyzer.py      # 50+ tests
│   ├── test_briefing_scheduler.py    # 25+ tests
│   └── test_briefing_command.py      # 28+ tests
├── integration/
│   ├── test_briefing_scheduler.py    # End-to-end tests
│   └── test_delivery_channels.py     # Multi-channel tests
└── fixtures/
    └── test_state/                    # Mock State files
```

### Running Tests

```bash
# All tests
python3 -m pytest tests/ -v

# Specific component
python3 -m pytest tests/unit/test_briefing_engine.py -v

# With coverage
python3 -m pytest tests/ --cov=Tools --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/
```

### Writing Tests for Extensions

**Example: Testing custom section provider**

```python
# tests/unit/test_custom_sections.py

import pytest
from custom_sections.github_section import github_activity_provider

def test_github_activity_provider_success():
    """Test GitHub section provider with successful API response"""
    context = {
        'config': {'github_username': 'testuser'}
    }

    result = github_activity_provider(context)

    assert result['enabled'] is True
    assert 'title' in result
    assert 'content' in result
    assert isinstance(result['content'], list)

def test_github_activity_provider_api_error():
    """Test GitHub section provider handles API errors gracefully"""
    context = {
        'config': {'github_username': 'nonexistent-user-xyz'}
    }

    result = github_activity_provider(context)

    # Should disable section on error
    assert result['enabled'] is False

def test_github_activity_integration():
    """Test GitHub section integrates with BriefingEngine"""
    from Tools.briefing_engine import BriefingEngine
    from custom_sections import register_custom_sections

    engine = BriefingEngine()
    register_custom_sections(engine)

    # Section should be registered
    assert 'github_activity' in engine._section_providers
```

---

## Code Examples

### Example 1: Generate Briefing Programmatically

```python
#!/usr/bin/env python3
"""
Example: Generate a briefing programmatically with custom config
"""

from Tools.briefing_engine import BriefingEngine
import json

# Load configuration
with open('config/briefing_config.json') as f:
    config = json.load(f)

# Override some settings
config['priorities']['max_items'] = 5
config['patterns']['enabled'] = True

# Create engine
engine = BriefingEngine(
    state_dir='./State',
    templates_dir='./Templates',
    config=config
)

# Generate morning briefing with energy level 8
briefing_content = engine.generate_briefing(
    briefing_type='morning',
    energy_level=8
)

# Print to console
print(briefing_content)

# Or save to file
with open('my_briefing.md', 'w') as f:
    f.write(briefing_content)
```

### Example 2: Custom CLI Command

```python
#!/usr/bin/env python3
"""
Example: Custom CLI command for specialized briefing
"""

import argparse
from Tools.briefing_engine import BriefingEngine
from Tools.health_state_tracker import HealthStateTracker

def generate_focus_session_briefing():
    """Generate a specialized briefing for focus sessions"""

    # Get current energy level
    tracker = HealthStateTracker()
    health = tracker.get_health_summary()
    energy = health.get('current', {}).get('energy_level', 5)

    # Create engine
    engine = BriefingEngine()

    # Gather context
    context = engine.gather_context()

    # Get deep work tasks (high priority + high energy required)
    all_tasks = context.get('this_week', {}).get('tasks', [])
    deep_work = [
        task for task in all_tasks
        if any(keyword in task.get('title', '').lower()
               for keyword in ['implement', 'design', 'write', 'create'])
    ]

    # Rank for current energy
    ranked = engine.rank_priorities(deep_work, 'morning', energy)[:3]

    # Create specialized output
    print("🎯 FOCUS SESSION BRIEFING")
    print("=" * 60)
    print(f"\n💪 Current Energy: {energy}/10")
    print(f"\n📋 Recommended Tasks for This Session:\n")

    for i, task in enumerate(ranked, 1):
        print(f"{i}. {task['title']}")
        print(f"   Category: {task.get('category', 'N/A')}")
        print(f"   Priority: {task.get('urgency', 'MEDIUM')}")
        print()

    print("⏱️  Set a timer and let's focus!\n")

if __name__ == '__main__':
    generate_focus_session_briefing()
```

### Example 3: Webhook-Triggered Briefing

```python
#!/usr/bin/env python3
"""
Example: Flask webhook endpoint for on-demand briefings
"""

from flask import Flask, request, jsonify
from Tools.briefing_engine import BriefingEngine
from Tools.delivery_channels import CLIChannel, FileChannel

app = Flask(__name__)

@app.route('/briefing/generate', methods=['POST'])
def generate_briefing():
    """
    Generate briefing via webhook

    POST /briefing/generate
    {
        "type": "morning",
        "energy_level": 7,
        "delivery": ["cli", "file"]
    }
    """
    data = request.json

    # Validate input
    briefing_type = data.get('type', 'morning')
    energy_level = data.get('energy_level', 5)
    delivery_methods = data.get('delivery', ['cli'])

    try:
        # Generate briefing
        engine = BriefingEngine()
        content = engine.generate_briefing(briefing_type, energy_level)

        # Deliver via requested channels
        results = {}

        if 'cli' in delivery_methods:
            cli = CLIChannel()
            results['cli'] = cli.deliver(content, briefing_type)

        if 'file' in delivery_methods:
            file_channel = FileChannel()
            results['file'] = file_channel.deliver(content, briefing_type)

        return jsonify({
            'success': True,
            'briefing_type': briefing_type,
            'delivery_results': results,
            'content_length': len(content)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Example 4: Integration with External Tools

```python
#!/usr/bin/env python3
"""
Example: Integrate briefing with Todoist API
"""

import requests
from Tools.briefing_engine import BriefingEngine

def fetch_todoist_tasks(api_token):
    """Fetch today's tasks from Todoist"""
    response = requests.get(
        'https://api.todoist.com/rest/v2/tasks',
        headers={'Authorization': f'Bearer {api_token}'},
        params={'filter': 'today'}
    )
    return response.json()

def sync_briefing_with_todoist():
    """Generate briefing using Todoist tasks"""

    # Fetch tasks from Todoist
    TODOIST_TOKEN = 'your_api_token_here'
    todoist_tasks = fetch_todoist_tasks(TODOIST_TOKEN)

    # Convert to briefing format
    tasks = []
    for task in todoist_tasks:
        tasks.append({
            'title': task['content'],
            'deadline': task.get('due', {}).get('date'),
            'priority': task['priority'],
            'category': task.get('project_id', 'personal')
        })

    # Create engine and add tasks to context
    engine = BriefingEngine()
    context = engine.gather_context()

    # Merge Todoist tasks with existing tasks
    context['todoist_tasks'] = tasks

    # Rank all tasks together
    all_tasks = context['this_week'].get('tasks', []) + tasks
    ranked = engine.rank_priorities(all_tasks, 'morning', 7)

    # Generate briefing
    print("📋 BRIEFING WITH TODOIST INTEGRATION\n")
    print("Top 3 Priorities (from all sources):\n")

    for i, task in enumerate(ranked[:3], 1):
        source = 'Todoist' if task in tasks else 'State files'
        print(f"{i}. {task['title']} [Source: {source}]")
        print(f"   Priority: {task.get('urgency', 'MEDIUM')}\n")

if __name__ == '__main__':
    sync_briefing_with_todoist()
```

---

## Best Practices

### For Extension Developers

1. **Graceful Degradation**
   - Always handle missing dependencies gracefully
   - Provide fallback behavior when optional features are unavailable
   - Use try/except blocks for external API calls

2. **Configuration Over Code**
   - Make behavior configurable via JSON
   - Provide sensible defaults
   - Validate configuration on startup

3. **Logging**
   - Use Python's logging module
   - Log errors with context
   - Avoid print() in production code (except CLI output)

4. **Testing**
   - Write unit tests for all new functionality
   - Test error conditions and edge cases
   - Use fixtures for consistent test data

5. **Documentation**
   - Document all public methods and classes
   - Provide code examples
   - Explain extension points clearly

### For Contributors

1. **Code Style**
   - Follow PEP 8
   - Use type hints for function signatures
   - Keep functions focused and small

2. **Error Handling**
   - Catch specific exceptions, not bare `except:`
   - Provide helpful error messages
   - Don't fail silently

3. **Backwards Compatibility**
   - Don't break existing configurations
   - Deprecate features gradually
   - Provide migration guides

4. **Performance**
   - Avoid blocking operations in main loop
   - Cache expensive computations
   - Use generators for large data sets

---

## Additional Resources

### Documentation
- [Complete User Guide](briefing_engine_guide.md)
- [Configuration Guide](BRIEFING_CONFIG_CLI.md)
- [Custom Sections Guide](CUSTOM_SECTIONS.md)
- [Delivery Channels Guide](DELIVERY_CHANNELS.md)
- [Pattern Analyzer Details](PATTERN_ANALYZER.md)

### Code Reference
- [BriefingEngine Source](../Tools/briefing_engine.py)
- [BriefingScheduler Source](../Tools/briefing_scheduler.py)
- [HealthStateTracker Source](../Tools/health_state_tracker.py)
- [PatternAnalyzer Source](../Tools/pattern_analyzer.py)
- [DeliveryChannels Source](../Tools/delivery_channels.py)

### Community
- Submit issues and feature requests on GitHub
- Contribute extensions and improvements
- Share your customizations and use cases

---

**Last Updated:** January 2026
**Contributors:** Development Team
**License:** MIT

---

Built with ❤️ for extensibility and developer happiness.
