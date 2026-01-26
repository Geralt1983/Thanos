"""
Entity Extractor Module

Detects client/project/topic mentions in user input by scanning text
for entities defined in State/critical_facts.json.

Pattern: Keyword matching similar to classify_input.py
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any


def load_entities() -> Dict[str, List[str]]:
    """Load entities from critical_facts.json"""
    facts_path = Path(__file__).parent.parent / "State" / "critical_facts.json"

    if not facts_path.exists():
        return {"clients": [], "projects": []}

    try:
        with open(facts_path, 'r') as f:
            facts = json.load(f)

        clients = facts.get("work", {}).get("active_clients", [])
        projects = facts.get("work", {}).get("primary_projects", [])

        return {
            "clients": clients,
            "projects": projects
        }
    except (json.JSONDecodeError, IOError):
        return {"clients": [], "projects": []}


def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Extract client/project entities from text.

    Args:
        text: Input text to scan for entities

    Returns:
        List of detected entities with format:
        [
            {
                'text': 'Orlando',
                'type': 'client',
                'start': 15,
                'end': 22,
                'confidence': 1.0
            },
            ...
        ]
    """
    if not text or not text.strip():
        return []

    entities = load_entities()
    results = []
    text_lower = text.lower()

    # Detect clients
    for client in entities.get("clients", []):
        # Case-insensitive search with word boundaries
        pattern = re.compile(r'\b' + re.escape(client.lower()) + r'\b')
        for match in pattern.finditer(text_lower):
            results.append({
                'text': client,  # Return original casing from critical_facts
                'type': 'client',
                'start': match.start(),
                'end': match.end(),
                'confidence': 1.0
            })

    # Detect projects
    for project in entities.get("projects", []):
        # Case-insensitive search with word boundaries
        pattern = re.compile(r'\b' + re.escape(project.lower()) + r'\b')
        for match in pattern.finditer(text_lower):
            # Skip if already found as client (avoid duplicates)
            if not any(r['text'] == project and r['type'] == 'client' for r in results):
                results.append({
                    'text': project,  # Return original casing from critical_facts
                    'type': 'project',
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 1.0
                })

    # Sort by position in text
    results.sort(key=lambda x: x['start'])

    return results


def get_entity_context(entity: Dict[str, Any]) -> str:
    """
    Generate a description of the entity for context surfacing.

    Args:
        entity: Entity dict from extract_entities()

    Returns:
        Human-readable description
    """
    entity_type = entity.get('type', 'entity')
    entity_text = entity.get('text', 'unknown')

    type_descriptions = {
        'client': f"Client: {entity_text}",
        'project': f"Project: {entity_text}",
        'topic': f"Topic: {entity_text}"
    }

    return type_descriptions.get(entity_type, f"{entity_text}")
