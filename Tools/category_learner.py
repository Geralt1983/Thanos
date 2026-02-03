#!/usr/bin/env python3
"""
Category Learning System

Learns from manual category corrections and updates categorization rules.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

THANOS_ROOT = Path(__file__).parent.parent
RULES_FILE = THANOS_ROOT / "skills" / "monarch-money" / "references" / "categorization-rules.json"
LEARNINGS_FILE = THANOS_ROOT / "memory" / "category-learnings.json"


def load_rules() -> dict:
    """Load categorization rules."""
    if RULES_FILE.exists():
        with open(RULES_FILE) as f:
            return json.load(f)
    return {"rules": {}}


def save_rules(rules: dict):
    """Save categorization rules."""
    rules["lastUpdated"] = datetime.now().strftime("%Y-%m-%d")
    with open(RULES_FILE, "w") as f:
        json.dump(rules, f, indent=2)


def load_learnings() -> list:
    """Load learning history."""
    if LEARNINGS_FILE.exists():
        with open(LEARNINGS_FILE) as f:
            return json.load(f)
    return []


def save_learnings(learnings: list):
    """Save learning history."""
    LEARNINGS_FILE.parent.mkdir(exist_ok=True)
    with open(LEARNINGS_FILE, "w") as f:
        json.dump(learnings[-100:], f, indent=2)  # Keep last 100


def extract_pattern(merchant_name: str) -> Optional[str]:
    """Extract a useful pattern from merchant name."""
    # Clean up the name
    name = merchant_name.lower().strip()
    
    # Remove common prefixes
    prefixes = ["l date ", "l time ", "l time date ", "online ", "pos ", "ach "]
    for prefix in prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):]
    
    # Remove trailing numbers and dates
    name = re.sub(r'\s+\d+.*$', '', name)
    name = re.sub(r'\s+\d{2}/\d{2}.*$', '', name)
    
    # Get first 2-3 meaningful words
    words = name.split()
    if len(words) >= 2:
        return " ".join(words[:2])
    elif words:
        return words[0]
    
    return None


def find_rule_for_category(rules: dict, category_name: str) -> Optional[str]:
    """Find which rule key handles a given category."""
    for key, rule in rules.get("rules", {}).items():
        if rule.get("category", "").lower() == category_name.lower():
            return key
    return None


def learn_correction(merchant_name: str, old_category: str, new_category: str, 
                     category_id: Optional[str] = None) -> dict:
    """
    Learn from a category correction.
    
    Args:
        merchant_name: The merchant name that was miscategorized
        old_category: What it was incorrectly categorized as
        new_category: What it should be
        category_id: Optional Monarch category ID
    
    Returns:
        dict with result info
    """
    result = {
        "merchant": merchant_name,
        "old_category": old_category,
        "new_category": new_category,
        "learned": False,
        "message": ""
    }
    
    # Extract pattern from merchant name
    pattern = extract_pattern(merchant_name)
    if not pattern or len(pattern) < 3:
        result["message"] = f"Could not extract useful pattern from '{merchant_name}'"
        return result
    
    # Load current rules
    rules = load_rules()
    
    # Find or create rule for this category
    rule_key = find_rule_for_category(rules, new_category)
    
    if rule_key:
        # Add pattern to existing rule
        existing_patterns = rules["rules"][rule_key].get("patterns", [])
        if pattern not in existing_patterns:
            existing_patterns.append(pattern)
            rules["rules"][rule_key]["patterns"] = existing_patterns
            result["learned"] = True
            result["message"] = f"Added '{pattern}' to {rule_key} rule"
    else:
        # Create new rule
        rule_key = new_category.lower().replace(" ", "_").replace("&", "and")
        rules["rules"][rule_key] = {
            "category": new_category,
            "patterns": [pattern]
        }
        if category_id:
            rules["rules"][rule_key]["categoryId"] = category_id
        result["learned"] = True
        result["message"] = f"Created new rule '{rule_key}' with pattern '{pattern}'"
    
    if result["learned"]:
        save_rules(rules)
        
        # Log learning
        learnings = load_learnings()
        learnings.append({
            "timestamp": datetime.now().isoformat(),
            "merchant": merchant_name,
            "pattern": pattern,
            "old_category": old_category,
            "new_category": new_category,
            "rule_key": rule_key
        })
        save_learnings(learnings)
    
    return result


def main():
    """CLI interface for category learning."""
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: category_learner.py <merchant_name> <old_category> <new_category> [category_id]")
        print("\nExample:")
        print("  category_learner.py 'Stokes County Court' 'Gas' 'Financial & Legal Services'")
        sys.exit(1)
    
    merchant = sys.argv[1]
    old_cat = sys.argv[2]
    new_cat = sys.argv[3]
    cat_id = sys.argv[4] if len(sys.argv) > 4 else None
    
    result = learn_correction(merchant, old_cat, new_cat, cat_id)
    
    if result["learned"]:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['message']}")


if __name__ == "__main__":
    main()
