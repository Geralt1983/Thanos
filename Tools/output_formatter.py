import shutil
import textwrap
from typing import List, Dict, Any, Optional

def get_terminal_width() -> int:
    """Get current terminal width."""
    return shutil.get_terminal_size().columns

def is_mobile() -> bool:
    """Return True if terminal is narrow (mobile/Termux)."""
    return get_terminal_width() < 80

def format_header(text: str) -> str:
    """Format section header - mobile uses ━━━, desktop uses ###"""
    if is_mobile():
        return f"━━━ {text} ━━━"
    return f"### {text}"

def format_table(headers: List[str], rows: List[Dict[str, Any]], title_key: str = None) -> str:
    """Format data as table (desktop) or cards (mobile)."""
    if is_mobile():
        return format_as_cards(headers, rows, title_key)
    return format_as_table(headers, rows)

def format_as_cards(headers: List[str], rows: List[Dict[str, Any]], title_key: str = None) -> str:
    """Vertical card layout for mobile."""
    # Use first header as title if not specified
    title_key = title_key or headers[0] if headers else 'title'
    output = []
    for row in rows:
        # Get title from first column or 'title' key
        title = row.get(title_key) or row.get(headers[0]) if headers else str(row)
        output.append(f"◆ {title}")
        # Add other fields
        for h in headers[1:] if headers else []:
            val = row.get(h)
            if val:
                output.append(f"  {val}")
        # Add notes if present
        if row.get('notes'):
            output.append(f"  → {row['notes']}")
        output.append("")
    return "\n".join(output)

def format_as_table(headers: List[str], rows: List[Dict[str, Any]]) -> str:
    """Standard markdown table for desktop."""
    if not headers or not rows:
        return ""

    # Calculate column widths
    widths = {h: len(h) for h in headers}
    for row in rows:
        for h in headers:
            val = str(row.get(h, ''))
            widths[h] = max(widths[h], len(val))

    # Build table
    lines = []
    # Header row
    header_row = "| " + " | ".join(h.ljust(widths[h]) for h in headers) + " |"
    lines.append(header_row)
    # Separator
    sep_row = "|" + "|".join("-" * (widths[h] + 2) for h in headers) + "|"
    lines.append(sep_row)
    # Data rows
    for row in rows:
        data_row = "| " + " | ".join(str(row.get(h, '')).ljust(widths[h]) for h in headers) + " |"
        lines.append(data_row)

    return "\n".join(lines)

def wrap_text(text: str, max_width: int = None) -> str:
    """Wrap text to terminal width."""
    if max_width is None:
        max_width = min(get_terminal_width() - 4, 76)
    return textwrap.fill(text, width=max_width)

def format_list(items: List[str], numbered: bool = False) -> str:
    """Format a list of items."""
    output = []
    for i, item in enumerate(items, 1):
        if is_mobile():
            prefix = f"{i}." if numbered else "•"
            wrapped = wrap_text(item, get_terminal_width() - 4)
            output.append(f"{prefix} {wrapped}")
        else:
            prefix = f"{i}." if numbered else "-"
            output.append(f"{prefix} {item}")
    return "\n".join(output)
