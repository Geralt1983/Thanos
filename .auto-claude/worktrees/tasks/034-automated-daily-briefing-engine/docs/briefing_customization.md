# Briefing Template Customization Guide

This guide explains how to customize your daily briefing templates to match your personal preferences and workflow. Whether you want to reorder sections, change the formatting, or add completely custom content, this guide has you covered.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Understanding Jinja2 Templates](#understanding-jinja2-templates)
3. [Available Template Variables](#available-template-variables)
4. [Common Customizations](#common-customizations)
5. [Custom Sections](#custom-sections)
6. [Advanced Customization](#advanced-customization)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Quick Start

**Templates Location:** `Templates/`
- `briefing_morning.md` - Morning briefing template
- `briefing_evening.md` - Evening briefing template

**To customize:**
1. Edit the `.md` file in the `Templates/` directory
2. Use Jinja2 syntax for dynamic content
3. Test with: `python -m commands.pa.briefing morning --dry-run`
4. Backup originals before making major changes

**Related Documentation:**
- [Custom Sections Guide](./CUSTOM_SECTIONS.md) - Add/remove/reorder sections via config
- [Configuration Guide](./BRIEFING_CONFIG_COMPREHENSIVE.md) - Full config reference
- [Templates README](../Templates/README.md) - Quick reference

## Understanding Jinja2 Templates

Briefing templates use [Jinja2](https://jinja.palletsprojects.com/), a powerful templating language for Python. Here's everything you need to know:

### Basic Syntax

#### Variables
Print a variable's value:
```jinja2
{{ variable_name }}
```

Example:
```jinja2
Today is {{ day_of_week }}, {{ today_date }}
```

#### Comments
Add comments that won't appear in output:
```jinja2
{# This is a comment - it won't be rendered #}
```

#### Conditionals
Show content based on conditions:
```jinja2
{% if condition %}
  Content to show when condition is true
{% elif other_condition %}
  Alternative content
{% else %}
  Default content
{% endif %}
```

Example:
```jinja2
{% if is_weekend %}
## 🌴 Weekend Mode
Relax and recharge!
{% else %}
## 💼 Workday Focus
Let's be productive!
{% endif %}
```

#### Loops
Iterate over lists:
```jinja2
{% for item in list %}
  - {{ item }}
{% endfor %}
```

Example:
```jinja2
{% for priority in top_priorities %}
**{{ loop.index }}. {{ priority.title }}**
   - Urgency: {{ priority.urgency_level | upper }}
{% endfor %}
```

**Loop Variables:**
- `loop.index` - Current iteration (1-indexed)
- `loop.index0` - Current iteration (0-indexed)
- `loop.first` - True on first iteration
- `loop.last` - True on last iteration
- `loop.length` - Total number of items

#### Filters
Transform variables with filters:
```jinja2
{{ variable | filter }}
```

**Common Filters:**
- `upper` - Convert to uppercase: `{{ text | upper }}`
- `lower` - Convert to lowercase: `{{ text | lower }}`
- `title` - Title case: `{{ text | title }}`
- `round(n)` - Round number: `{{ number | round(2) }}`
- `default(value)` - Default if empty: `{{ variable | default('N/A') }}`
- `length` - Get length: `{{ list | length }}`

Example:
```jinja2
Average energy: {{ avg_energy | round(1) }}/10
```

#### Combining Conditions
```jinja2
{% if condition1 and condition2 %}
  Both are true
{% endif %}

{% if condition1 or condition2 %}
  At least one is true
{% endif %}

{% if not condition %}
  Condition is false
{% endif %}
```

#### Checking for Empty/None
```jinja2
{% if variable %}
  Variable exists and is not empty
{% endif %}

{% if not variable %}
  Variable is empty, None, or False
{% endif %}

{% if list %}
  List has items
{% else %}
  List is empty
{% endif %}
```

## Available Template Variables

All templates have access to these variables:

### Common Variables (All Templates)

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `today_date` | String | Today's date (ISO format) | `"2026-01-11"` |
| `day_of_week` | String | Day name | `"Monday"` |
| `is_weekend` | Boolean | True if Saturday/Sunday | `true` |
| `generated_at` | String | Timestamp when generated | `"2026-01-11 07:00:00"` |
| `top_priorities` | List[Dict] | Top 3 prioritized items | See structure below |
| `active_commitments` | List[Dict] | Active commitments | See structure below |
| `pending_tasks` | List[Dict] | This week's tasks | See structure below |
| `custom_sections` | List[Dict] | User-defined sections | See structure below |
| `sections_data` | List[Dict] | Structured section data | See advanced usage |

### Morning-Specific Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `focus_areas` | List[String] | Current focus areas | `["Learn Python", "Build app"]` |
| `quick_wins` | List[String] | Simple tasks (<15min) | `["Send email", "Schedule call"]` |
| `health_state` | Dict | Health tracking data | See structure below |
| `energy_level` | Integer | Current energy (1-10) | `7` |

### Evening-Specific Variables

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `reflection_data` | Dict | Evening reflection data | See structure below |
| `accomplishments` | List[String] | Today's accomplishments | `["Finished report"]` |
| `energy_data` | Dict | Energy comparison | See structure below |
| `tomorrow_priorities` | List[Dict] | Preview of tomorrow | Same as `top_priorities` |
| `prep_checklist` | List[String] | Tomorrow prep items | `["Review calendar"]` |
| `commitment_progress` | List[Dict] | Commitment updates | See structure below |

### Data Structures

#### Priority Item (`top_priorities`, `tomorrow_priorities`)
```python
{
    "title": "Complete project proposal",
    "category": "Work",
    "urgency_level": "high",  # critical, high, medium, low
    "priority_score": 85.5,
    "priority_reason": "due in 2 days",
    "deadline": "2026-01-13"  # ISO date or None
}
```

#### Commitment Item (`active_commitments`)
```python
{
    "title": "Finish quarterly report",
    "category": "Work",
    "deadline": "2026-01-15",
    "status": "active",
    "notes": "Focus on Q4 metrics"
}
```

#### Task Item (`pending_tasks`)
```python
{
    "text": "Update documentation",
    "completed": false,
    "notes": "Focus on API docs"
}
```

#### Health State (`health_state`)
```python
{
    "energy_level": 7,
    "sleep_hours": 7.5,
    "vyvanse_time": "07:30",  # HH:MM format
    "trend": {
        "avg_energy": 6.8,
        "avg_sleep": 7.2,
        "best_day": "Wednesday",
        "best_energy": 8
    }
}
```

#### Reflection Data (`reflection_data`)
```python
{
    "morning_energy": 7,
    "evening_energy": 5,
    "energy_change": -2,
    "trend": "↘️ Decreased by 2 points",
    "accomplishments": ["Completed 3 tasks", "Had productive meeting"],
    "wins": ["Finished early", "Helped colleague"],
    "energy_draining_activities": ["Long meeting", "Email overload"],
    "improvements_for_tomorrow": ["Take more breaks", "Start earlier"],
    "health_trend": {
        "avg_energy": 6.5,
        "avg_sleep": 7.0
    }
}
```

#### Custom Section
```python
{
    "title": "🏋️ Health Goals",
    "content": "- 30 min workout\n- Drink 8 glasses of water"
}
```

## Common Customizations

### 1. Reorder Sections

Simply cut and paste sections in the template file. The order in the file determines output order.

**Before:**
```jinja2
## 🎯 Top 3 Priorities
...

## 📋 Active Commitments
...

## 🏥 Health State
...
```

**After:**
```jinja2
## 🏥 Health State
...

## 🎯 Top 3 Priorities
...

## 📋 Active Commitments
...
```

### 2. Remove a Section

Comment out or delete the section:

```jinja2
{# Removed - I don't need this section
## 📅 This Week's Tasks
{% if pending_tasks %}
...
{% endif %}
#}
```

### 3. Change Section Titles

Edit the markdown header:

```jinja2
{# Change from "Top 3 Priorities" to "Today's Focus" #}
## 🎯 Today's Focus
{% if top_priorities %}
...
{% endif %}
```

### 4. Customize Priority Display

**Compact Format:**
```jinja2
## 🎯 Top 3 Priorities
{% if top_priorities %}
{% for item in top_priorities %}
{{ loop.index }}. **{{ item.title }}** ({{ item.urgency_level }})
{% endfor %}
{% endif %}
```

**Detailed Format:**
```jinja2
## 🎯 Top 3 Priorities
{% if top_priorities %}
{% for item in top_priorities %}

### Priority {{ loop.index }}: {{ item.title }}
- **Category:** {{ item.category }}
- **Urgency:** {{ item.urgency_level | upper }}
- **Why:** {{ item.priority_reason }}
{% if item.deadline %}- **Deadline:** {{ item.deadline }}{% endif %}
{% endfor %}
{% endif %}
```

**Emoji Indicators:**
```jinja2
## 🎯 Top 3 Priorities
{% if top_priorities %}
{% for item in top_priorities %}
{% if item.urgency_level == "critical" %}🔴{% elif item.urgency_level == "high" %}🟡{% else %}🟢{% endif %} **{{ item.title }}** - {{ item.priority_reason }}
{% endfor %}
{% endif %}
```

### 5. Day-Specific Content

**Different greeting by day:**
```jinja2
{% if day_of_week == "Monday" %}
# 👋 Monday Morning - Fresh Start!
Time to set the tone for the week.
{% elif day_of_week == "Friday" %}
# 🎉 Friday - Finish Strong!
One more day to make this week count.
{% elif is_weekend %}
# 🌴 {{ day_of_week }} - Weekend Mode
Relax, recharge, and enjoy!
{% else %}
# ☀️ Good {{ day_of_week }} Morning!
{% endif %}
```

**Friday-specific section:**
```jinja2
{% if day_of_week == "Friday" %}
---

## 🧹 Week Wrap-Up
- [ ] Review accomplishments this week
- [ ] Plan priorities for next week
- [ ] Clean up workspace
{% endif %}
```

### 6. Energy-Based Recommendations

```jinja2
{% if health_state and health_state.energy_level %}
---

## ⚡ Energy-Optimized Schedule
{% if health_state.energy_level >= 8 %}
**High Energy Day!** 🚀
- Perfect for: Complex problem-solving, creative work, important meetings
- Schedule: Tackle your hardest task first
{% elif health_state.energy_level >= 6 %}
**Good Energy Level** ✅
- Perfect for: Steady work, meetings, moderate tasks
- Schedule: Balance challenging and routine tasks
{% elif health_state.energy_level >= 4 %}
**Moderate Energy** 🔋
- Perfect for: Admin tasks, emails, light work
- Schedule: Take frequent breaks, avoid complex tasks
{% else %}
**Low Energy Day** 😴
- Perfect for: Simple tasks, planning, reading
- Schedule: Be gentle with yourself, reschedule non-urgent items
{% endif %}
{% endif %}
```

### 7. Conditional Health Section

Only show health section when data is available:

```jinja2
{% if health_state %}
---

## 🏥 Health Check
**Energy:** {{ health_state.energy_level }}/10{% if health_state.sleep_hours %} | **Sleep:** {{ health_state.sleep_hours }}h{% endif %}

{% if health_state.vyvanse_time %}
**Medication:** Taken at {{ health_state.vyvanse_time }}
⏰ Peak focus window: {{ health_state.vyvanse_time }} + 2-4 hours
{% endif %}

{% if health_state.trend %}
**7-Day Average:** {{ health_state.trend.avg_energy | round(1) }}/10 energy, {{ health_state.trend.avg_sleep | round(1) }}h sleep
{% if health_state.trend.best_day %}💪 Best day: {{ health_state.trend.best_day }}{% endif %}
{% endif %}
{% endif %}
```

### 8. Minimal Morning Briefing

Streamlined version for quick scanning:

```jinja2
# ☀️ {{ day_of_week }}, {{ today_date }}

## Top 3 Priorities
{% if top_priorities %}
{% for item in top_priorities %}
{{ loop.index }}. {{ item.title }} ({{ item.urgency_level }})
{% endfor %}
{% else %}
No urgent items - focus on long-term goals.
{% endif %}

## Quick Wins
{% if quick_wins %}
{% for win in quick_wins[:3] %}
- {{ win }}
{% endfor %}
{% endif %}

{% if is_weekend %}
🌴 Weekend - Rest & Recharge
{% endif %}
```

### 9. Detailed Evening Reflection

Expanded evening briefing with more reflection prompts:

```jinja2
# 🌙 Evening Reflection - {{ day_of_week }}, {{ today_date }}

## 📊 Energy Analysis
{% if reflection_data %}
Morning: {{ reflection_data.morning_energy }}/10 → Evening: {{ reflection_data.evening_energy }}/10 {{ reflection_data.trend }}

{% if reflection_data.energy_change <= -3 %}
⚠️ **Significant energy drop** - What drained your energy today?
{% endif %}
{% endif %}

## ✅ Wins & Accomplishments
{% if reflection_data and reflection_data.accomplishments %}
{% for item in reflection_data.accomplishments %}
- {{ item }}
{% endfor %}

{% if reflection_data.wins %}
🌟 **Special Wins:**
{% for win in reflection_data.wins %}
- {{ win }}
{% endfor %}
{% endif %}
{% else %}
*What did you accomplish today? Don't forget small wins!*
{% endif %}

## 💭 Reflection Questions
1. **What went well today?**
   _Your answer:_

2. **What could have gone better?**
   _Your answer:_

3. **What did you learn?**
   _Your answer:_

4. **What are you grateful for?**
   _Your answer:_

## 📅 Tomorrow Preparation
{% if tomorrow_priorities %}
**Top 3 for tomorrow:**
{% for item in tomorrow_priorities %}
- {{ item.title }}
{% endfor %}
{% endif %}

**Prep checklist:**
- [ ] Review calendar
- [ ] Set out essentials
- [ ] Note morning priorities
- [ ] Clear workspace

---
*{{ generated_at }}*
```

## Custom Sections

You can add custom content to briefings in two ways:

### Method 1: Edit Template Directly

Add your custom section to the template file:

```jinja2
---

## 🏋️ Fitness Goals
- [ ] 30 min workout
- [ ] Stretch for 10 min
- [ ] Drink 8 glasses of water
```

**Pros:** Simple, always appears
**Cons:** Not dynamic, same content every day

### Method 2: Configure Custom Sections

Define custom sections in `config/briefing_config.json`:

```json
{
  "content": {
    "sections": {
      "enabled": ["daily_quote", "priorities", "tasks"],
      "order": ["daily_quote", "priorities", "tasks"],
      "custom": [
        {
          "id": "daily_quote",
          "title": "💭 Daily Inspiration",
          "template": "{{ custom_quote | default('Today is a new beginning.') }}",
          "enabled_by_default": true
        }
      ]
    }
  }
}
```

Then pass data when generating:

```python
engine.render_briefing(
    briefing_type="morning",
    custom_quote="Focus on progress, not perfection."
)
```

**Pros:** Dynamic, configurable, can use data providers
**Cons:** Requires configuration

For detailed information on custom sections (data providers, conditional sections, etc.), see the [Custom Sections Guide](./CUSTOM_SECTIONS.md).

### Method 3: Inject at Runtime

Pass custom sections directly when calling the briefing command:

```python
from Tools.briefing_engine import BriefingEngine

engine = BriefingEngine()
context = engine.gather_context()

custom_sections = [
    {
        "title": "📚 Learning Goals",
        "content": "- Complete Python tutorial Chapter 5\n- Review documentation"
    }
]

briefing = engine.render_briefing(
    briefing_type="morning",
    custom_sections=custom_sections
)
```

## Advanced Customization

### 1. Create a New Briefing Type

Create `Templates/briefing_weekly.md`:

```jinja2
# 📊 Weekly Review - Week of {{ today_date }}

## 🎯 This Week's Wins
{% if weekly_accomplishments %}
{% for item in weekly_accomplishments %}
- {{ item }}
{% endfor %}
{% endif %}

## 📈 Pattern Insights
{% if weekly_patterns %}
- Most productive day: {{ weekly_patterns.best_day }}
- Average energy: {{ weekly_patterns.avg_energy }}/10
- Total focused hours: {{ weekly_patterns.total_hours }}
{% endif %}

## 🔮 Next Week's Focus
{% if next_week_priorities %}
{% for priority in next_week_priorities %}
- {{ priority }}
{% endfor %}
{% endif %}
```

Render with:

```python
briefing = engine.render_briefing(
    briefing_type="weekly",
    weekly_accomplishments=["Launched feature", "Hit sprint goals"],
    weekly_patterns={"best_day": "Wednesday", "avg_energy": 7.2, "total_hours": 32},
    next_week_priorities=["Plan Q2", "Team offsite"]
)
```

### 2. Structured Sections Data

Use the `sections_data` variable for programmatic section rendering:

```jinja2
{% for section in sections_data %}
---

## {{ section.title }}

{% if section.enabled %}
  {% if section.id == "priorities" %}
    {# Custom rendering for priorities #}
    {% for item in section.data.top_priorities %}
    ⭐ {{ item.title }} - {{ item.priority_reason }}
    {% endfor %}
  {% elif section.id == "health" %}
    {# Custom rendering for health #}
    Energy: {{ section.data.health_state.energy_level }}/10
  {% else %}
    {# Default rendering #}
    {{ section.data }}
  {% endif %}
{% endif %}
{% endfor %}
```

### 3. Macros for Reusable Content

Define macros at the top of your template:

```jinja2
{% macro render_priority(item, index) %}
**{{ index }}. {{ item.title }}**
   Category: {{ item.category }}
   Urgency: {{ item.urgency_level | upper }}
   {{ item.priority_reason }}
{% endmacro %}

---

## 🎯 Top Priorities
{% for priority in top_priorities %}
{{ render_priority(priority, loop.index) }}
{% endfor %}
```

### 4. Template Inheritance (Advanced)

Create a base template `Templates/briefing_base.md`:

```jinja2
# {{ briefing_emoji }} {{ briefing_title }} - {{ day_of_week }}, {{ today_date }}

{% block intro %}
{{ briefing_intro }}
{% endblock %}

{% block content %}
{# Child templates override this #}
{% endblock %}

---

*Generated at {{ generated_at }}*
```

Then extend it in `briefing_morning.md`:

```jinja2
{% extends "briefing_base.md" %}

{% set briefing_emoji = "☀️" %}
{% set briefing_title = "Morning Briefing" %}
{% set briefing_intro = "Good morning! Here's your personalized briefing." %}

{% block content %}
## 🎯 Top Priorities
...
{% endblock %}
```

## Troubleshooting

### Template Not Rendering

**Symptom:** Briefing command returns empty or error

**Solutions:**
1. **Check file location:** Template must be in `Templates/` directory
2. **Check filename:** Must follow pattern `briefing_{type}.md`
3. **Check Jinja2 syntax:** Ensure all tags are closed properly
4. **Check permissions:** File must be readable

```bash
# Verify file exists
ls -la Templates/briefing_morning.md

# Test with dry-run
python -m commands.pa.briefing morning --dry-run --verbose
```

### Variable Not Displaying

**Symptom:** `{{ variable }}` shows nothing or shows literally

**Solutions:**
1. **Check variable name:** Case-sensitive, check spelling
2. **Check if None:** Use `{% if variable %}...{% endif %}`
3. **Use default:** `{{ variable | default('N/A') }}`
4. **Print for debugging:** `DEBUG: {{ variable }}`

```jinja2
{# Debugging example #}
{% if top_priorities %}
  Count: {{ top_priorities | length }}
  {% for item in top_priorities %}
    DEBUG: {{ item }}
  {% endfor %}
{% else %}
  No priorities found (variable is empty/None)
{% endif %}
```

### Jinja2 Syntax Errors

**Common errors:**

1. **Unclosed tags:**
   ```jinja2
   {# WRONG #}
   {% if condition %}
   Content
   {# Missing {% endif %} #}

   {# CORRECT #}
   {% if condition %}
   Content
   {% endif %}
   ```

2. **Invalid filter:**
   ```jinja2
   {# WRONG #}
   {{ number | roundup }}

   {# CORRECT #}
   {{ number | round(0) }}
   ```

3. **Accessing missing dict keys:**
   ```jinja2
   {# WRONG - errors if key missing #}
   {{ item.nonexistent_key }}

   {# CORRECT - safe access #}
   {{ item.get('nonexistent_key', 'default') }}
   ```

### Jinja2 Not Installed

**Symptom:** Error about Jinja2 not available

**Solution:**
```bash
pip install jinja2
```

Or template will fall back to simple string substitution (limited features).

### Section Not Appearing

**Symptom:** Expected section doesn't show in briefing

**Solutions:**
1. **Check if section has data:** Many sections only appear if data exists
2. **Check configuration:** Section might be disabled in config
3. **Check conditions:** Section might have day/type conditions
4. **Check template logic:** Verify `{% if %}` conditions

```jinja2
{# Debug section visibility #}
{% if quick_wins %}
  Quick wins available: {{ quick_wins | length }}
{% else %}
  No quick wins (empty list or None)
{% endif %}
```

### Formatting Issues

**Symptom:** Output looks wrong (spacing, line breaks)

**Solutions:**
1. **Check whitespace control:**
   ```jinja2
   {# Remove whitespace before #}
   {%- if condition %}

   {# Remove whitespace after #}
   {% if condition -%}

   {# Remove both #}
   {%- if condition -%}
   ```

2. **Use raw blocks for literal content:**
   ```jinja2
   {% raw %}
   This {{ won't }} be {{processed}}
   {% endraw %}
   ```

### Health State Not Showing

**Symptom:** Health section is empty

**Solutions:**
1. **Enable health prompts:** Remove `--no-prompts` flag
2. **Check HealthLog.json:** Ensure data exists in `State/HealthLog.json`
3. **Log health data:** Use morning briefing to log energy/sleep
4. **Debug template:**
   ```jinja2
   Health state provided: {% if health_state %}YES{% else %}NO{% endif %}
   {% if health_state %}
     Energy: {{ health_state.energy_level }}
     Sleep: {{ health_state.sleep_hours }}
   {% endif %}
   ```

## Best Practices

### 1. ADHD-Friendly Design

✅ **Do:**
- Use clear visual hierarchy (headers, bullets, emojis)
- Keep it scannable (short paragraphs, clear sections)
- Limit top priorities to 3 (avoid overwhelm)
- Use emojis for quick visual scanning
- Highlight urgent items clearly

❌ **Don't:**
- Create walls of text
- Include too much detail
- List more than 5-7 items per section
- Use subtle differences (bold is better than italics)

**Example:**
```jinja2
{# ADHD-Friendly #}
## 🎯 Top 3 Priorities

1. **🔴 URGENT: Submit proposal** (due today)
2. **🟡 Call client** (due tomorrow)
3. **🟢 Review PRs** (this week)

{# Too Overwhelming #}
## Priorities for Today

Here are the fifteen items you should consider working on today, ordered by importance and urgency, taking into account various factors such as deadlines, dependencies, and estimated effort...
```

### 2. Progressive Enhancement

Start simple, add complexity gradually:

```jinja2
{# Version 1: Simple #}
## Top Priorities
{% for p in top_priorities %}
- {{ p.title }}
{% endfor %}

{# Version 2: Add urgency #}
## Top Priorities
{% for p in top_priorities %}
- {{ p.title }} ({{ p.urgency_level }})
{% endfor %}

{# Version 3: Add emojis and formatting #}
## 🎯 Top Priorities
{% for p in top_priorities %}
**{{ loop.index }}.** {{ p.title }}
   _{{ p.priority_reason }}_
{% endfor %}
```

### 3. Consistent Formatting

Use consistent patterns throughout your template:

```jinja2
{# Consistent section format #}
---

## 🎯 Section Title
{% if section_data %}
{% for item in section_data %}
- {{ item }}
{% endfor %}
{% else %}
No items found.
{% endif %}
```

### 4. Graceful Degradation

Handle missing data elegantly:

```jinja2
{# Good: Graceful handling #}
{% if top_priorities %}
  {% for p in top_priorities %}
  - {{ p.title }}
  {% endfor %}
{% else %}
  No urgent priorities - great time for long-term planning!
{% endif %}

{# Bad: Assumes data exists #}
{% for p in top_priorities %}
- {{ p.title }}
{% endfor %}
{# If top_priorities is None, this breaks #}
```

### 5. Test Changes

Always test template changes before relying on them:

```bash
# Dry-run to see output without saving
python -m commands.pa.briefing morning --dry-run

# Verbose mode for debugging
python -m commands.pa.briefing morning --dry-run --verbose

# Test with specific energy level
python -m commands.pa.briefing morning --energy-level 5 --dry-run
```

### 6. Backup Before Major Changes

```bash
# Backup current templates
cp Templates/briefing_morning.md Templates/briefing_morning.md.backup
cp Templates/briefing_evening.md Templates/briefing_evening.md.backup

# Make changes...

# Restore if needed
mv Templates/briefing_morning.md.backup Templates/briefing_morning.md
```

### 7. Comment Your Customizations

Add comments to explain custom logic:

```jinja2
{# Custom section: Only show on Monday mornings to plan the week #}
{% if day_of_week == "Monday" and briefing_type == "morning" %}
## 📅 Week Planning
- Review calendar for entire week
- Identify key deadlines
- Plan deep work blocks
{% endif %}

{# Energy-based task filtering: Show only admin tasks on low energy days #}
{% if energy_level and energy_level < 4 %}
## 🔋 Low Energy - Focus on Simple Tasks
Stick to admin work and planning today. Reschedule complex tasks.
{% endif %}
```

### 8. Use Examples for Inspiration

Check out the example scripts to see templates in action:

```bash
# Template rendering examples
python example_template_rendering.py

# Custom sections examples
python example_custom_sections.py

# Evening reflection examples
python example_evening_reflection.py
```

## Related Documentation

- **[Custom Sections Guide](./CUSTOM_SECTIONS.md)** - Detailed guide for custom sections with data providers
- **[Configuration Guide](./BRIEFING_CONFIG_COMPREHENSIVE.md)** - Complete configuration reference
- **[Templates README](../Templates/README.md)** - Quick reference for template variables
- **[BriefingEngine API](../Tools/briefing_engine.py)** - Source code and API documentation
- **[Jinja2 Documentation](https://jinja.palletsprojects.com/)** - Official Jinja2 docs

## Need Help?

1. **Check examples:** Run example scripts in the project root
2. **Enable verbose mode:** `--verbose` flag shows detailed output
3. **Review logs:** Check `logs/briefing_scheduler.log` for errors
4. **Test in dry-run:** Use `--dry-run` to preview without saving
5. **Read Jinja2 docs:** https://jinja.palletsprojects.com/

## Summary

**Key Takeaways:**
- Templates use Jinja2 syntax (variables, conditionals, loops)
- All variables are documented in this guide
- Start with simple changes, add complexity gradually
- Always test with `--dry-run` before committing
- Keep it ADHD-friendly: scannable, visual, not overwhelming
- Backup templates before major changes

**Quick Reference:**
```jinja2
{{ variable }}                    {# Print variable #}
{% if condition %}...{% endif %}  {# Conditional #}
{% for item in list %}...{% endfor %}  {# Loop #}
{# Comment #}                     {# Won't appear in output #}
{{ value | filter }}              {# Apply filter #}
```

Happy customizing! 🎨
