# 🌙 Evening Briefing - {{ day_of_week }}, {{ today_date }}

Time to reflect and prepare for tomorrow.

{% if adaptive_mode %}
---

## 🔄 Briefing Adaptation

**{{ adaptive_mode.reasoning }}**

{% if adaptive_mode.days_inactive %}💤 **Last activity:** {{ adaptive_mode.days_inactive }} day(s) ago
{% endif %}{% if adaptive_mode.recent_activities %}📊 **Recent activity:** {{ adaptive_mode.recent_activities }} activities in last 7 days
{% endif %}{% if adaptive_mode.overdue_tasks %}⚠️ **Overdue tasks:** {{ adaptive_mode.overdue_tasks }} items need attention
{% endif %}
{% if adaptive_mode.recommendations %}
**Recommendations:**
{% for rec in adaptive_mode.recommendations %}
- {{ rec }}
{% endfor %}
{% endif %}
{% endif %}

---

## 📊 Energy & Productivity Check
{% if reflection_data %}
{% if reflection_data.morning_energy and reflection_data.evening_energy %}
- **Morning Energy:** {{ reflection_data.morning_energy }}/10
- **Evening Energy:** {{ reflection_data.evening_energy }}/10
- **Change:** {{ reflection_data.trend }}

{% if reflection_data.energy_change <= -3 %}
⚠️ **Significant energy drain detected** - Consider reviewing your task distribution and break frequency.
{% elif reflection_data.energy_change >= 2 %}
🎉 **Energy increased** - Great job pacing yourself today!
{% else %}
✅ **Energy stable** - Good energy management throughout the day.
{% endif %}
{% else %}
- **Evening Energy:** {{ reflection_data.evening_energy }}/10
{% endif %}

{% if reflection_data.health_trend %}
📈 **7-Day Trend:** Avg energy {{ reflection_data.health_trend.avg_energy|round(1) }}/10, avg sleep {{ reflection_data.health_trend.avg_sleep|round(1) }} hrs
{% endif %}
{% else %}
*How did your energy levels feel today?*
- Morning: ___/10
- Evening: ___/10
{% endif %}

---

## ✅ Today's Accomplishments
{% if reflection_data and reflection_data.accomplishments %}
{% for item in reflection_data.accomplishments %}
- {{ item }}
{% endfor %}

{% if reflection_data.wins %}
🌟 **Wins:**
{% for win in reflection_data.wins %}
- {{ win }}
{% endfor %}
{% endif %}
{% elif accomplishments %}
{% for item in accomplishments %}
- {{ item }}
{% endfor %}
{% else %}
*Take a moment to note what you accomplished today, even small wins!*
{% endif %}

---

{% if reflection_data and reflection_data.energy_draining_activities %}
## ⚡ Energy-Draining Activities
{% for activity in reflection_data.energy_draining_activities %}
- {{ activity }}
{% endfor %}

💡 **Consider:** Can any of these be delegated, automated, or scheduled for your peak energy times?

---

{% endif %}
## 💡 Improvements for Tomorrow
{% if reflection_data and reflection_data.improvements_for_tomorrow %}
{% for improvement in reflection_data.improvements_for_tomorrow %}
- {{ improvement }}
{% endfor %}
{% else %}
*What could make tomorrow better?*
- _Your ideas here..._
{% endif %}

---

## 🔮 Tomorrow's Preview
{% if tomorrow_priorities %}
**Top priorities for tomorrow:**
{% for item in tomorrow_priorities %}
{{ loop.index }}. {{ item.title }} ({{ item.urgency_level }})
{% endfor %}
{% else %}
Tomorrow's priorities will be calculated in the morning briefing.
{% endif %}

---

## 📝 Tomorrow Prep Checklist
{% if prep_checklist %}
{% for item in prep_checklist %}
- [ ] {{ item }}
{% endfor %}
{% else %}
- [ ] Review calendar for tomorrow
- [ ] Set out tomorrow's essentials
- [ ] Note any important morning tasks
- [ ] Clear workspace for fresh start
{% endif %}

---

## 💭 Commitment Progress
{% if commitment_progress %}
{% for commitment in commitment_progress %}
- {{ commitment.title }}: {{ commitment.progress }}
{% endfor %}
{% else %}
*Track progress on active commitments here.*
{% endif %}

---

{% if is_weekend %}
## 🌟 Weekend Reflection
How did you balance rest and productivity this weekend?
{% else %}
## 🌟 Weekday Wrap-Up
{{ day_of_week }} is done! Time to rest and recharge for tomorrow.
{% endif %}

{% if custom_sections %}
{% for section in custom_sections %}
---

## {{ section.title }}
{{ section.content }}
{% endfor %}
{% endif %}

{% if weekly_review and weekly_review.has_data %}
---

# 📊 Weekly Pattern Review

{% if weekly_review.total_completions > 0 %}
**Week of {{ weekly_review.week_start }} to {{ weekly_review.week_end }}**

## 📈 This Week's Summary

**Total Tasks Completed:** {{ weekly_review.total_completions }}

{% if weekly_review.most_productive_day %}
### 🌟 Most Productive Day
**{{ weekly_review.most_productive_day.day }}** - {{ weekly_review.most_productive_day.count }} tasks completed
{% endif %}

{% if weekly_review.most_productive_time %}
### ⏰ Peak Productivity Time
**{{ weekly_review.most_productive_time.time|title }}** - {{ weekly_review.most_productive_time.count }} tasks completed
{% endif %}

---

## 🎯 Task Category Breakdown

{% if weekly_review.category_breakdown %}
{% for category, data in weekly_review.category_breakdown.items() %}
- **{{ category.replace('_', ' ')|title }}**: {{ data.count }} tasks ({{ data.percentage }}%)
{% endfor %}
{% endif %}

---

## 💡 Key Insights

{% if weekly_review.insights %}
{% for insight in weekly_review.insights %}
- {{ insight }}
{% endfor %}
{% endif %}

{% if weekly_review.pattern_changes %}

---

## 🔄 Pattern Changes

{% for change in weekly_review.pattern_changes %}
- {{ change.description }}
{% endfor %}
{% endif %}

---

## 🚀 Optimizations for Next Week

{% if weekly_review.optimizations %}
{% for optimization in weekly_review.optimizations %}
- {{ optimization.suggestion }}
{% endfor %}
{% else %}
Continue with your current approach - your patterns look healthy!
{% endif %}

{% else %}
**Week of {{ weekly_review.week_start }} to {{ weekly_review.week_end }}**

No task completions recorded this week. Consider tracking your completed tasks to build productivity insights!
{% endif %}

---
{% endif %}

---

*Generated at {{ generated_at }}*
*Briefing Type: Evening*
{% if weekly_review and weekly_review.has_data %}*Includes Weekly Pattern Review*{% endif %}
