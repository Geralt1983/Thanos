# 🌙 Evening Briefing - {{ day_of_week }}, {{ today_date }}

Time to reflect and prepare for tomorrow.

---

## ✅ Today's Accomplishments
{% if accomplishments %}
{% for item in accomplishments %}
- {{ item }}
{% endfor %}
{% else %}
*Take a moment to note what you accomplished today, even small wins!*
{% endif %}

---

## 📊 Energy & Productivity Check
{% if energy_data %}
- Morning Energy: {{ energy_data.morning_energy }}/10
- Current Energy: {{ energy_data.evening_energy }}/10
- Energy Trend: {{ energy_data.trend }}
{% else %}
*How did your energy levels feel today?*
- Morning: ___/10
- Now: ___/10
{% endif %}

---

## 🤔 Reflection Prompts
1. **What went well today?**
   {% if reflection_notes.went_well %}{{ reflection_notes.went_well }}{% else %}_Your thoughts here..._{% endif %}

2. **What could have gone better?**
   {% if reflection_notes.could_improve %}{{ reflection_notes.could_improve }}{% else %}_Your thoughts here..._{% endif %}

3. **What did you learn?**
   {% if reflection_notes.learned %}{{ reflection_notes.learned }}{% else %}_Your thoughts here..._{% endif %}

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

---

*Generated at {{ generated_at }}*
*Briefing Type: Evening*
