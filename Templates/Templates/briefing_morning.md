# ☀️ Morning Briefing - {{ day_of_week }}, {{ today_date }}

Good morning! Here's your personalized briefing for today.

---

## 🎯 Top 3 Priorities
{% if top_priorities %}
{% for item in top_priorities %}
**{{ loop.index }}. {{ item.title }}**
   - Category: {{ item.category }}
   - Urgency: {{ item.urgency_level | upper }}
   - Why: {{ item.priority_reason }}
{% endfor %}
{% else %}
No urgent priorities found. Great time to focus on long-term goals!
{% endif %}

---

## 📋 Active Commitments
{% if active_commitments %}
{% for commitment in active_commitments %}
- {{ commitment.title }}{% if commitment.deadline %} (due: {{ commitment.deadline }}){% endif %}
  - Category: {{ commitment.category }}
{% endfor %}
{% else %}
No active commitments tracked.
{% endif %}

---

## 📅 This Week's Tasks
{% if pending_tasks %}
{% for task in pending_tasks %}
- {{ task.text }}
{% endfor %}
{% else %}
No pending tasks for this week.
{% endif %}

---

## 🎓 Current Focus Areas
{% if focus_areas %}
{% for area in focus_areas %}
- {{ area }}
{% endfor %}
{% else %}
No focus areas defined.
{% endif %}

---

## 💡 Quick Wins
{% if quick_wins %}
{% for win in quick_wins %}
- {{ win }}
{% endfor %}
{% else %}
Look for simple tasks you can complete in under 15 minutes to build momentum!
{% endif %}

---

{% if is_weekend %}
## 🌴 Weekend Mode
Remember, it's {{ day_of_week }}! Focus on personal time unless something is urgent.
{% else %}
## 💪 Weekday Focus
It's {{ day_of_week }} - let's make it productive! Consider your energy levels when tackling complex tasks.
{% endif %}

{% if custom_sections %}
{% for section in custom_sections %}
---

## {{ section.title }}
{{ section.content }}
{% endfor %}
{% endif %}

---

*Generated at {{ generated_at }}*
*Briefing Type: Morning*
