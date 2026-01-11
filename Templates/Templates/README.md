# Briefing Templates

This directory contains Jinja2 templates for rendering morning and evening briefings.

## Available Templates

### briefing_morning.md
Morning briefing template with focus on:
- Top 3 priorities for the day
- Active commitments
- This week's tasks
- Current focus areas
- Quick wins (simple tasks to build momentum)
- Weekend/weekday context

### briefing_evening.md
Evening briefing template with focus on:
- Today's accomplishments
- Energy and productivity reflection
- Reflection prompts (what went well, could improve, learned)
- Tomorrow's preview
- Preparation checklist
- Commitment progress tracking

## Template Variables

### Common Variables (available in all templates)
- `today_date` - Today's date in ISO format (YYYY-MM-DD)
- `day_of_week` - Day name (Monday, Tuesday, etc.)
- `is_weekend` - Boolean indicating if today is Saturday or Sunday
- `generated_at` - Timestamp when briefing was generated
- `top_priorities` - List of top 3 priority items (see structure below)
- `active_commitments` - List of active commitments
- `pending_tasks` - List of pending tasks from ThisWeek.md
- `custom_sections` - List of custom sections (user-provided)

### Morning-Specific Variables
- `focus_areas` - List of current focus areas
- `quick_wins` - List of simple tasks that can be completed quickly

### Evening-Specific Variables
- `accomplishments` - List of accomplishments for the day
- `energy_data` - Dict with morning_energy, evening_energy, trend
- `reflection_notes` - Dict with went_well, could_improve, learned
- `tomorrow_priorities` - Preview of tomorrow's top priorities
- `prep_checklist` - List of items to prepare for tomorrow
- `commitment_progress` - Progress updates on commitments

## Priority Item Structure

Each item in `top_priorities` has:
```python
{
    "title": "Task title",
    "category": "Work" | "Personal" | etc.,
    "urgency_level": "critical" | "high" | "medium" | "low",
    "priority_score": float,
    "priority_reason": "Human-readable explanation"
}
```

## Customization Guide

### Basic Customization
Simply edit the `.md` files in this directory. The templates use Jinja2 syntax.

### Jinja2 Basics
```jinja2
{# Comments #}
{{ variable }}                    {# Print variable #}
{% if condition %}...{% endif %}  {# Conditional #}
{% for item in list %}...{% endfor %}  {# Loop #}
```

### Example: Adding a New Section

```jinja2
---

## 🎯 My Custom Section
{% if custom_field %}
{{ custom_field }}
{% else %}
Default content when custom_field not provided
{% endif %}
```

Then pass the data when rendering:
```python
engine.render_briefing(
    briefing_type="morning",
    custom_field="My custom content"
)
```

### Example: Reordering Sections
Simply cut and paste sections in the template file. The order in the file determines the output order.

### Example: Removing a Section
Delete or comment out the section:
```jinja2
{# Commented out - won't appear in output
## Section I Don't Want
...
#}
```

## Custom Sections

You can inject custom sections without modifying templates:

```python
custom_sections = [
    {
        "title": "🏋️ Health Goals",
        "content": "- 30 min workout\n- Drink water"
    },
    {
        "title": "📚 Learning",
        "content": "Continue Python course"
    }
]

engine.render_briefing(
    briefing_type="morning",
    custom_sections=custom_sections
)
```

## Tips

1. **Keep it scannable**: Use bullet points and clear headers
2. **ADHD-friendly**: Avoid overwhelming detail, focus on actionable items
3. **Use emojis**: Help sections stand out at a glance
4. **Test changes**: Run `example_template_rendering.py` to see your changes
5. **Backup originals**: Copy templates before major changes

## Troubleshooting

### Template not found
- Ensure template file exists in Templates/ directory
- Check filename matches `briefing_{type}.md` pattern
- Verify Templates directory is in the right location

### Variable not appearing
- Check variable name spelling
- Ensure variable is passed to `render_briefing()`
- Use `{% if variable %}` to handle optional variables

### Jinja2 errors
- Check for unclosed tags ({% if %} needs {% endif %})
- Check for typos in variable names
- Review Jinja2 syntax: https://jinja.palletsprojects.com/

## Advanced Usage

### Conditional Formatting Based on Energy
```jinja2
{% if energy_level %}
  {% if energy_level >= 7 %}
## ⚡ High Energy - Tackle Complex Tasks!
  {% else %}
## 🔋 Low Energy - Focus on Simple Wins
  {% endif %}
{% endif %}
```

### Day-Specific Content
```jinja2
{% if day_of_week == "Monday" %}
## 👋 Monday Morning - Week Kickoff!
{% elif day_of_week == "Friday" %}
## 🎉 Friday - Finish Strong!
{% endif %}
```

### Weekend vs Weekday
```jinja2
{% if is_weekend %}
## 🌴 Weekend Mode - Rest & Recharge
{% else %}
## 💼 Workday Focus
{% endif %}
```

## Creating New Template Types

To create a new briefing type (e.g., "weekly"):

1. Create `Templates/briefing_weekly.md`
2. Use any variables from the common set
3. Render with: `engine.render_briefing(briefing_type="weekly")`
4. Pass custom data via kwargs

## Reference

- Jinja2 Documentation: https://jinja.palletsprojects.com/
- BriefingEngine API: See `Tools/briefing_engine.py`
- Examples: See `example_template_rendering.py`
