
# Custom Sections Guide

This guide explains how to customize briefing sections in the Automated Daily Briefing Engine. You can enable/disable sections, reorder them, and create entirely custom sections with your own data providers.

## Table of Contents

1. [Overview](#overview)
2. [Built-in Sections](#built-in-sections)
3. [Enabling and Disabling Sections](#enabling-and-disabling-sections)
4. [Reordering Sections](#reordering-sections)
5. [Creating Custom Sections](#creating-custom-sections)
6. [Conditional Sections](#conditional-sections)
7. [Custom Data Providers](#custom-data-providers)
8. [Advanced Usage](#advanced-usage)
9. [Examples](#examples)

## Overview

The briefing engine uses a flexible section-based architecture that allows you to:

- **Enable/Disable** any built-in section
- **Reorder** sections to match your preferences
- **Create custom** sections with your own content
- **Add conditions** so sections only appear on certain days or briefing types
- **Register data providers** to fetch dynamic content for sections

All configuration is done via the `config/briefing_config.json` file or programmatically when creating a `BriefingEngine` instance.

## Built-in Sections

The following sections are available by default:

| Section ID    | Title                     | Description                                    |
|---------------|---------------------------|------------------------------------------------|
| `priorities`  | 🎯 Top 3 Priorities       | Top-ranked tasks based on urgency and context  |
| `commitments` | 📋 Active Commitments     | Active commitments from Commitments.md         |
| `tasks`       | 📅 This Week's Tasks      | Pending tasks from ThisWeek.md                 |
| `focus`       | 🎓 Current Focus Areas    | Focus areas from CurrentFocus.md               |
| `quick_wins`  | 💡 Quick Wins             | Simple tasks that can be completed quickly     |
| `calendar`    | 📆 Calendar               | Calendar events (placeholder for integration)  |
| `health`      | 🏥 Health State           | Energy level, sleep, medication timing         |

## Enabling and Disabling Sections

Configure which sections appear in your briefings by editing the `content.sections.enabled` array in `config/briefing_config.json`:

```json
{
  "content": {
    "sections": {
      "enabled": [
        "priorities",
        "commitments",
        "tasks",
        "quick_wins"
      ]
    }
  }
}
```

**Only the sections listed in `enabled` will appear** in your briefings. Sections not listed will be hidden.

### Default Behavior

If you don't specify an `enabled` list, all built-in sections are enabled by default:

```json
// Default if not specified
"enabled": [
  "priorities",
  "commitments",
  "tasks",
  "focus",
  "quick_wins",
  "calendar",
  "health"
]
```

## Reordering Sections

Control the order in which sections appear using the `content.sections.order` array:

```json
{
  "content": {
    "sections": {
      "enabled": [
        "health",
        "priorities",
        "commitments",
        "tasks"
      ],
      "order": [
        "health",
        "priorities",
        "commitments",
        "tasks"
      ]
    }
  }
}
```

**Important Notes:**

1. Sections appear in the order specified in the `order` array
2. If a section is in `enabled` but not in `order`, it will be appended at the end
3. If a section is in `order` but not in `enabled`, it won't appear

### Example: Partial Ordering

```json
{
  "content": {
    "sections": {
      "enabled": ["priorities", "tasks", "commitments", "focus"],
      "order": ["priorities", "focus"]
    }
  }
}
```

This will produce the order: `priorities`, `focus`, `tasks`, `commitments`

## Creating Custom Sections

You can define custom sections in your configuration that will appear alongside built-in sections.

### Basic Custom Section

```json
{
  "content": {
    "sections": {
      "enabled": ["priorities", "daily_quote", "commitments"],
      "order": ["daily_quote", "priorities", "commitments"],
      "custom": [
        {
          "id": "daily_quote",
          "title": "💭 Daily Inspiration",
          "enabled_by_default": true
        }
      ]
    }
  }
}
```

### Custom Section with Template

You can provide inline content or a template for custom sections:

```json
{
  "content": {
    "sections": {
      "custom": [
        {
          "id": "affirmation",
          "title": "✨ Daily Affirmation",
          "template": "Today, I choose to focus on {{ focus_areas[0] }} with clarity and purpose.",
          "enabled_by_default": true
        }
      ]
    }
  }
}
```

### Custom Section Schema

```json
{
  "id": "string (required)",          // Unique section identifier
  "title": "string (required)",        // Display title for section
  "data_provider": "string (optional)", // Python module path for data provider
  "template": "string (optional)",     // Inline Jinja2 template
  "enabled_by_default": "boolean",     // Default: true
  "conditions": {                      // Optional conditions
    "days": ["monday", "tuesday", ...],     // Only show on these days
    "briefing_types": ["morning", "evening"] // Only show for these types
  }
}
```

## Conditional Sections

Sections can be configured to only appear under certain conditions.

### Day-Specific Sections

Show a section only on specific days of the week:

```json
{
  "content": {
    "sections": {
      "custom": [
        {
          "id": "weekly_review",
          "title": "📊 Weekly Review",
          "conditions": {
            "days": ["sunday", "monday"]
          }
        }
      ]
    }
  }
}
```

This section will only appear on Sundays and Mondays.

### Briefing Type-Specific Sections

Show a section only in morning or evening briefings:

```json
{
  "content": {
    "sections": {
      "custom": [
        {
          "id": "morning_motivation",
          "title": "☀️ Morning Motivation",
          "conditions": {
            "briefing_types": ["morning"]
          }
        },
        {
          "id": "evening_reflection",
          "title": "🌙 Evening Reflection",
          "conditions": {
            "briefing_types": ["evening"]
          }
        }
      ]
    }
  }
}
```

### Combined Conditions

You can combine both day and briefing type conditions:

```json
{
  "content": {
    "sections": {
      "custom": [
        {
          "id": "friday_review",
          "title": "🎉 Friday Wrap-Up",
          "conditions": {
            "days": ["friday"],
            "briefing_types": ["evening"]
          }
        }
      ]
    }
  }
}
```

This section only appears on Friday evenings.

## Custom Data Providers

For dynamic content, you can create Python functions that provide data for your custom sections.

### Creating a Data Provider

1. Create a Python file (e.g., `Tools/custom_providers.py`):

```python
def weather_provider(context, briefing_type, **kwargs):
    """
    Fetch and return weather data.

    Args:
        context: Briefing context dict (includes date, day, weekend flag, etc.)
        briefing_type: "morning" or "evening"
        **kwargs: Additional arguments passed to section

    Returns:
        Dict with data for the section
    """
    # Fetch weather data (example - would use real API in practice)
    return {
        "temperature": "72°F",
        "conditions": "Partly Cloudy",
        "humidity": "45%",
        "recommendation": "Great day for outdoor activities!"
    }
```

2. Reference it in your configuration:

```json
{
  "content": {
    "sections": {
      "custom": [
        {
          "id": "weather",
          "title": "🌤️ Weather",
          "data_provider": "Tools.custom_providers.weather_provider"
        }
      ]
    }
  }
}
```

### Programmatic Registration

You can also register providers programmatically:

```python
from Tools.briefing_engine import BriefingEngine

def habits_provider(context, briefing_type, **kwargs):
    return {
        "habits": [
            {"name": "Meditation", "completed": False},
            {"name": "Exercise", "completed": False}
        ]
    }

# Create engine
engine = BriefingEngine()

# Register provider
engine.register_section_provider("habits", habits_provider)

# Now the "habits" section is available
```

### Data Provider Best Practices

1. **Handle errors gracefully** - Your provider should not raise exceptions
2. **Return consistent structure** - Always return a dict
3. **Be performant** - Providers are called on every briefing generation
4. **Use caching** - Cache expensive operations (API calls, file reads)
5. **Document your data structure** - Other users may want to customize templates

## Advanced Usage

### Overriding Built-in Section Providers

You can override built-in sections with your own implementations:

```python
def custom_priorities_provider(context, briefing_type, **kwargs):
    """Custom logic for determining priorities."""
    # Your custom prioritization logic here
    return {
        "title": "🎯 My Custom Priorities",
        "data": {
            "top_priorities": [
                {"title": "Custom priority 1", "score": 100},
                {"title": "Custom priority 2", "score": 90}
            ]
        }
    }

engine = BriefingEngine()
engine.register_section_provider("priorities", custom_priorities_provider)
```

### Accessing Section Data in Templates

Section data is available in templates in two ways:

1. **Individual variables** (backward compatible):
```jinja2
{% for priority in top_priorities %}
  - {{ priority.title }}
{% endfor %}
```

2. **Structured sections_data** (recommended for custom templates):
```jinja2
{% for section in sections_data %}
  ## {{ section.title }}

  {% if section.id == 'priorities' %}
    {% for item in section.data.top_priorities %}
      - {{ item.title }}
    {% endfor %}
  {% endif %}
{% endfor %}
```

### Per-Briefing Section Configuration

You can override section configuration for specific briefing types in `briefings` config:

```json
{
  "briefings": {
    "morning": {
      "enabled": true,
      "time": "07:00",
      "content": {
        "sections": {
          "enabled": ["health", "priorities", "quick_wins"],
          "order": ["health", "priorities", "quick_wins"]
        }
      }
    },
    "evening": {
      "enabled": true,
      "time": "19:00",
      "content": {
        "sections": {
          "enabled": ["accomplishments", "tomorrow_prep"],
          "order": ["accomplishments", "tomorrow_prep"]
        }
      }
    }
  }
}
```

## Examples

### Example 1: Minimal Morning Briefing

Only show the essentials:

```json
{
  "content": {
    "sections": {
      "enabled": ["priorities", "quick_wins"],
      "order": ["priorities", "quick_wins"]
    }
  }
}
```

### Example 2: Comprehensive Morning Briefing

Show everything in a specific order:

```json
{
  "content": {
    "sections": {
      "enabled": [
        "health",
        "priorities",
        "calendar",
        "commitments",
        "tasks",
        "focus",
        "quick_wins"
      ],
      "order": [
        "health",
        "priorities",
        "calendar",
        "commitments",
        "tasks",
        "focus",
        "quick_wins"
      ]
    }
  }
}
```

### Example 3: Custom Habit Tracking Section

```json
{
  "content": {
    "sections": {
      "enabled": ["habits", "priorities", "tasks"],
      "order": ["habits", "priorities", "tasks"],
      "custom": [
        {
          "id": "habits",
          "title": "✅ Daily Habits",
          "data_provider": "Tools.habits_tracker.get_daily_habits",
          "enabled_by_default": true
        }
      ]
    }
  }
}
```

### Example 4: Day-Specific Sections

Different content for different days:

```json
{
  "content": {
    "sections": {
      "enabled": [
        "priorities",
        "commitments",
        "weekly_planning",
        "weekend_ideas"
      ],
      "order": [
        "weekly_planning",
        "priorities",
        "commitments",
        "weekend_ideas"
      ],
      "custom": [
        {
          "id": "weekly_planning",
          "title": "📅 Week Ahead",
          "conditions": {
            "days": ["sunday", "monday"]
          }
        },
        {
          "id": "weekend_ideas",
          "title": "🌴 Weekend Ideas",
          "conditions": {
            "days": ["friday", "saturday"]
          }
        }
      ]
    }
  }
}
```

## Troubleshooting

### Section not appearing?

1. **Check if enabled**: Make sure the section ID is in the `enabled` array
2. **Check conditions**: If using conditions, verify today matches the criteria
3. **Check data provider**: If using a custom provider, ensure it returns data (not None)
4. **Check logs**: Look for errors in `logs/briefing_scheduler.log`

### Section appears in wrong order?

1. **Check order array**: Ensure the section is in the correct position in `order`
2. **Verify enabled**: Section must be in both `enabled` and `order`

### Custom provider not working?

1. **Check module path**: Ensure `data_provider` path is correct
2. **Check function signature**: Must accept `(context, briefing_type, **kwargs)`
3. **Check return value**: Must return a dict
4. **Check imports**: Ensure the module can be imported

### Health section not showing?

The health section only appears when `health_state` is provided to the template rendering. Make sure health tracking is enabled in your configuration.

## See Also

- [Configuration Guide](./BRIEFING_CONFIG_COMPREHENSIVE.md) - Complete configuration reference
- [Template Customization](../Templates/README.md) - How to customize templates
- [BriefingEngine API](./BRIEFING_ENGINE_API.md) - Full API documentation

