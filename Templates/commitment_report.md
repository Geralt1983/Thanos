# 📊 Weekly Commitment Review

**Week of {{week_start}} to {{week_end}}**

---

## 🎯 Overall Performance

<div style="text-align: center; padding: 20px; background: #f5f5f5; border-radius: 8px; margin: 10px 0;">

### {{grade_emoji}} Grade: **{{completion_grade}}**

**Completion Rate: {{completion_rate}}%**

{{progress_bar}}

</div>

### 💭 Coach's Take

> {{summary_message}}

---

## 🏆 Wins & Highlights

{{#if wins}}
{{#each wins}}
✓ {{this}}
{{/each}}
{{else}}
Keep pushing forward. Every day is a chance to build momentum.
{{/if}}

---

## 🔍 Areas for Improvement

{{#if struggles}}
{{#each struggles}}
→ {{this}}
{{/each}}
{{else}}
No major struggles this week - keep up the excellent work!
{{/if}}

---

## 📈 This Week's Statistics

| Metric | Count | Rate |
|--------|-------|------|
| **Active Commitments** | {{total_commitments}} | — |
| **Completed** | {{completed_count}} | {{completion_rate}}% |
| **Missed** | {{missed_count}} | {{missed_rate}}% |
| **Expected Total** | {{expected_count}} | — |

### Breakdown by Type

{{#each by_type}}
**{{type_emoji}} {{type_name}}**
- Commitments: {{total_commitments}}
- Expected: {{expected_completions}}
- Completed: {{completed}} ({{completion_rate}}%)
- Performance: {{performance_indicator}}

{{/each}}

---

## 📊 Trend Analysis

**Direction:** {{trend_emoji}} **{{trend_direction}}**

- Change from previous weeks: {{trend_change}}
- 4-week average: {{avg_completion_rate}}%

### Streak Statistics

- 🔥 Active streaks: **{{total_active_streaks}}**
- 📏 Average streak length: **{{avg_streak_length}} days**
- 🏆 Longest current streak: **{{longest_streak}} days**
  {{#if longest_streak_commitment}}
  → *{{longest_streak_commitment_title}}*
  {{/if}}
- 💎 Personal records: **{{personal_records_count}}**

---

{{#if streak_milestones}}
## 🎯 Streak Milestones Achieved

{{#each streak_milestones}}
{{milestone_emoji}} **{{commitment_title}}**
   → Reached {{milestone}}-day milestone! (Current: {{current_streak}} days)

{{/each}}
{{/if}}

---

## 🧠 Reflection Prompts

Take a few minutes to reflect on these questions. They're designed to help you understand your patterns and improve your follow-through.

{{#each reflection_prompts}}
### {{priority_emoji}} {{question}}

*Why this matters:* {{context}}

**Your answer:**

---

{{/each}}

---

## 💡 Key Insights

{{#each insights}}
{{type_emoji}} **{{message}}**
   {{#if data}}
   *{{data_context}}*
   {{/if}}

{{/each}}

---

## 🎯 Next Steps

Based on this week's performance, here's what to focus on:

1. **Review** your reflection questions honestly
2. **Identify** one commitment to improve or redesign
3. **Celebrate** your wins - progress compounds
4. **Adjust** commitments that aren't working
5. **Protect** your active streaks

---

## 📅 Quick Reference

### Visual Performance Indicators

```
Completion Rate Legend:
🌟 A+ / A  (90-100%) - Exceptional consistency
✅ B+ / B  (75-89%)  - Solid performance
⚠️  C      (60-74%)  - Room for improvement
🚨 D      (50-59%)  - Needs attention
❌ F      (0-49%)   - Time to reassess
```

### Streak Milestones

```
💎 100+ days - Diamond tier
🏆 30-99 days - Champion tier
⭐ 14-29 days - Star tier
🔥 7-13 days  - Fire tier
✨ 3-6 days   - Spark tier
```

### Trend Indicators

```
📈 Improving  - Completion rate up by 10+ points
➡️  Stable     - Completion rate within ±10 points
📉 Declining  - Completion rate down by 10+ points
```

---

## 📝 Notes & Observations

*Use this space for any personal notes, patterns you've noticed, or thoughts about your commitments:*





---

*Generated: {{generated_at}}*
*Review Period: {{week_start}} to {{week_end}}*

---

<div style="text-align: center; padding: 15px; border-top: 2px solid #ddd;">

**Remember:** Consistency beats perfection. Every completion builds the habit, every reflection builds awareness, and every week is a fresh start.

*— Your commitment accountability system*

</div>
