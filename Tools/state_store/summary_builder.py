"""
Summary builder for Thanos orchestrator.
Builds formatted state summaries within token/character limits.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class StateSummary:
    """A formatted state summary with metadata."""
    text: str
    char_count: int
    truncated: bool = False


class SummaryBuilder:
    """Builds formatted summaries of orchestrator state."""
    
    def __init__(self, max_chars: int = 2000):
        """Initialize the summary builder.
        
        Args:
            max_chars: Maximum characters for summaries.
        """
        self.max_chars = max_chars
    
    def build_state_summary(self, state: Dict[str, Any]) -> StateSummary:
        """Build a summary of the current state.
        
        Args:
            state: Dictionary containing state components:
                - today: Dict with focus, energy, blockers, top3
                - daily_plan: List of planned items
                - scoreboard: Dict with wins, misses, streak
                - reminders: List of reminders
                - tool_summaries: List of recent tool results
                
        Returns:
            StateSummary with formatted text.
        """
        parts = []
        
        # Today's state
        today = state.get("today", {})
        if today:
            today_parts = []
            if today.get("focus"):
                today_parts.append(f"Focus: {today['focus']}")
            if today.get("energy"):
                today_parts.append(f"Energy: {today['energy']}")
            if today.get("top3"):
                top3 = today["top3"]
                if isinstance(top3, list):
                    today_parts.append(f"Top 3: {', '.join(str(t) for t in top3[:3])}")
                else:
                    today_parts.append(f"Top 3: {top3}")
            if today.get("blockers"):
                blockers = today["blockers"]
                if isinstance(blockers, list):
                    today_parts.append(f"Blockers: {', '.join(str(b) for b in blockers)}")
                else:
                    today_parts.append(f"Blockers: {blockers}")
            if today_parts:
                parts.append("## Today\n" + "\n".join(today_parts))
        
        # Daily plan
        daily_plan = state.get("daily_plan", [])
        if daily_plan:
            plan_items = daily_plan[-5:]  # Last 5 items
            parts.append("## Plan\n" + "\n".join(f"- {item}" for item in plan_items))
        
        # Scoreboard
        scoreboard = state.get("scoreboard", {})
        if scoreboard:
            wins = scoreboard.get("wins", 0)
            misses = scoreboard.get("misses", 0)
            streak = scoreboard.get("streak", 0)
            parts.append(f"## Score\nWins: {wins} | Misses: {misses} | Streak: {streak}")
        
        # Reminders
        reminders = state.get("reminders", [])
        if reminders:
            reminder_items = reminders[:3]  # Top 3 reminders
            parts.append("## Reminders\n" + "\n".join(f"- {r}" for r in reminder_items))
        
        # Tool summaries
        tool_summaries = state.get("tool_summaries", [])
        if tool_summaries:
            summary_lines = []
            for ts in tool_summaries[:3]:
                tool_name = ts.get("tool_name", "unknown")
                summary = ts.get("summary", "")[:100]
                summary_lines.append(f"- {tool_name}: {summary}")
            if summary_lines:
                parts.append("## Recent Actions\n" + "\n".join(summary_lines))
        
        # Combine and truncate if needed
        full_text = "\n\n".join(parts)
        truncated = False
        
        if len(full_text) > self.max_chars:
            full_text = full_text[:self.max_chars - 3] + "..."
            truncated = True
        
        return StateSummary(
            text=full_text,
            char_count=len(full_text),
            truncated=truncated
        )
    
    def build_context_summary(
        self,
        context_items: List[Dict[str, Any]],
        max_items: int = 5
    ) -> str:
        """Build a summary from context items.
        
        Args:
            context_items: List of context dictionaries.
            max_items: Maximum items to include.
            
        Returns:
            Formatted summary string.
        """
        if not context_items:
            return ""
        
        lines = []
        for item in context_items[:max_items]:
            title = item.get("title", item.get("name", "Item"))
            desc = item.get("description", item.get("summary", ""))[:100]
            lines.append(f"- **{title}**: {desc}")
        
        return "\n".join(lines)
