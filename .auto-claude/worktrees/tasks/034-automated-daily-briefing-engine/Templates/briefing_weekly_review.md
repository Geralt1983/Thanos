# 📊 Weekly Pattern Review - Week of {{ week_start }} to {{ week_end }}

A look back at your productivity patterns and insights for next week.

---

## 📈 This Week's Summary

**Total Tasks Completed:** {{ total_completions }}

{% if most_productive_day %}
### 🌟 Most Productive Day
**{{ most_productive_day.day }}** - {{ most_productive_day.count }} tasks completed

This was your most productive day this week! Consider scheduling important tasks on {{ most_productive_day.day }}s in the future.
{% endif %}

{% if most_productive_time %}
### ⏰ Peak Productivity Time
**{{ most_productive_time.time|title }}** - {{ most_productive_time.count }} tasks completed

You were most active during the {{ most_productive_time.time }}. Try to schedule deep work or complex tasks during this time period.
{% endif %}

---

## 🎯 Task Category Breakdown

{% if category_breakdown %}
{% for category, data in category_breakdown.items() %}
- **{{ category.replace('_', ' ')|title }}**: {{ data.count }} tasks ({{ data.percentage }}%)
{% endfor %}

{% if category_breakdown|length > 1 %}
Your focus was well-distributed across multiple categories this week.
{% endif %}
{% else %}
No task category data available for this week.
{% endif %}

---

## 🔄 Pattern Changes

{% if pattern_changes %}
We noticed some shifts in your productivity patterns this week:

{% for change in pattern_changes %}
{% if change.type == 'productivity_shift' %}
📅 **{{ change.description }}**

This could indicate a change in your routine or workload. Pay attention to whether this shift continues.
{% elif change.type == 'category_shift' %}
🔀 **{{ change.description }}**

{% if 'increased' in change.description %}
You spent more time on {{ change.category.replace('_', ' ')|lower }} tasks than usual.
{% else %}
You spent less time on {{ change.category.replace('_', ' ')|lower }} tasks than usual.
{% endif %}
{% endif %}

{% endfor %}
{% else %}
No significant pattern changes detected this week. Your productivity patterns are consistent with your historical trends.
{% endif %}

---

## 💡 Insights

{% if insights %}
{% for insight in insights %}
- {{ insight }}
{% endfor %}
{% else %}
Keep tracking your task completions to build up pattern insights!
{% endif %}

---

## 🚀 Optimizations for Next Week

Based on this week's patterns, here are some suggestions to optimize your productivity:

{% if optimizations %}
{% for optimization in optimizations %}
{% if optimization.type == 'time_optimization' %}
### ⏰ Time Management
{{ optimization.suggestion }}

{% elif optimization.type == 'balance' %}
### ⚖️ Work-Life Balance
{{ optimization.suggestion }}

{% elif optimization.type == 'productivity' %}
### 📊 Productivity Boost
{{ optimization.suggestion }}

{% elif optimization.type == 'pacing' %}
### 🏃 Pacing
{{ optimization.suggestion }}

{% elif optimization.type == 'scheduling' %}
### 📅 Scheduling Strategy
{{ optimization.suggestion }}

{% endif %}
{% endfor %}
{% else %}
Continue with your current approach - your productivity patterns look healthy!
{% endif %}

---

## 🎯 Focus Areas for Next Week

Based on your patterns, consider prioritizing:

{% if most_productive_day %}
1. **Schedule critical tasks on {{ most_productive_day.day }}s** - your most productive day
{% endif %}
{% if most_productive_time %}
2. **Block {{ most_productive_time.time }} for deep work** - your peak productivity time
{% endif %}
{% if pattern_changes %}
3. **Monitor pattern changes** - Be aware of shifts in your productivity patterns
{% endif %}
4. **Maintain balance** - Ensure you're allocating time across work, personal, and health tasks

---

## 📝 Notes

{% if total_completions < 7 %}
💡 **Tip:** You completed fewer than one task per day on average. Consider breaking larger projects into smaller, trackable tasks to maintain momentum.
{% elif total_completions > 35 %}
⚠️ **Reminder:** You completed over 5 tasks per day! Great productivity, but don't forget to schedule rest and recovery to avoid burnout.
{% else %}
✅ Your task completion rate looks healthy - averaging {{ (total_completions / 7)|round(1) }} tasks per day.
{% endif %}

---

*Weekly review generated at {{ generated_at }}*
*Pattern learning helps improve your briefings over time*
