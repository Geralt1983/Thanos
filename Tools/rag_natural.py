#!/usr/bin/env python3
"""
Natural Language RAG Interface for Thanos.

Handles conversational queries by:
1. Detecting the target notebook from natural language
2. Routing the query to the appropriate vector store
3. Returning natural language responses

This is the interface that should be used from Telegram, OpenClaw, etc.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from Tools.openai_file_search import OpenAIFileSearchClient, _load_config, _get_defaults

# Default notebook when no pattern matches
DEFAULT_NOTEBOOK = "orders_hod"


def _build_routing_patterns() -> List[Tuple[str, str, float]]:
    """
    Build routing patterns from config routing_keywords.
    Returns list of (regex_pattern, notebook_key, specificity_score).
    Sorted by specificity (multi-word patterns first).
    """
    config = _load_config()
    notebooks = config.get("notebooks", {})
    patterns: List[Tuple[str, str, float]] = []

    for notebook_key, notebook_config in notebooks.items():
        keywords = notebook_config.get("routing_keywords", [])
        for keyword in keywords:
            # Convert keyword to regex pattern
            # Handle multi-word patterns with flexible spacing
            escaped = re.escape(keyword.lower())
            pattern = r"\b" + escaped.replace(r"\ ", r"\s*") + r"\b"

            # Higher specificity for longer/multi-word patterns
            specificity = len(keyword.split()) + len(keyword) / 20
            patterns.append((pattern, notebook_key, specificity))

    # Sort by specificity descending (most specific patterns first)
    patterns.sort(key=lambda x: x[2], reverse=True)
    return patterns


# Cache for routing patterns (rebuilt on first use)
_ROUTING_PATTERNS_CACHE: Optional[List[Tuple[str, str, float]]] = None


def _get_routing_patterns() -> List[Tuple[str, str, float]]:
    """Get routing patterns, building from config if not cached."""
    global _ROUTING_PATTERNS_CACHE
    if _ROUTING_PATTERNS_CACHE is None:
        _ROUTING_PATTERNS_CACHE = _build_routing_patterns()
    return _ROUTING_PATTERNS_CACHE


def clear_routing_cache() -> None:
    """Clear the routing patterns cache (call after config changes)."""
    global _ROUTING_PATTERNS_CACHE
    _ROUTING_PATTERNS_CACHE = None


def detect_notebook(query: str) -> Tuple[str, float]:
    """
    Detect which notebook to query based on natural language input.
    Uses routing_keywords from config/notebooklm.json.
    Returns (notebook_key, confidence_score).
    """
    query_lower = query.lower()
    patterns = _get_routing_patterns()

    for pattern, notebook, specificity in patterns:
        if re.search(pattern, query_lower):
            # Higher confidence for more specific patterns
            confidence = min(0.95, 0.5 + specificity / 10)
            return notebook, confidence

    return DEFAULT_NOTEBOOK, 0.3  # Low confidence for default


def format_natural_response(answer: str, sources: List[Dict[str, Any]], notebook: str) -> str:
    """
    Format the RAG response in a natural, conversational way.
    """
    if answer == "Not found in documents.":
        return f"I couldn't find specific information about that in the {notebook.replace('_', ' ')} documents. The notebook may not have relevant content, or you might want to try rephrasing your question."

    # Clean up the answer
    response = answer.strip()

    # Add source attribution if we have sources
    if sources and len(sources) > 0:
        source_names = []
        for src in sources[:3]:  # Max 3 sources
            filename = (
                src.get("filename")
                or (src.get("file") or {}).get("filename")
                or src.get("file_id")
            )
            if filename:
                # Clean up the filename for display
                clean_name = filename.split("__")[-1] if "__" in filename else filename
                clean_name = clean_name.replace(".pdf", "")
                if clean_name not in source_names:
                    source_names.append(clean_name)

        if source_names:
            response += f"\n\n📚 Sources: {', '.join(source_names)}"

    return response


def query_natural(query: str, notebook: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Execute a natural language query against the RAG system.

    Args:
        query: Natural language question
        notebook: Optional explicit notebook override
        verbose: Include debug info

    Returns:
        Dict with 'answer', 'notebook', 'confidence', 'sources'
    """
    # Detect notebook if not specified
    if notebook:
        detected_notebook = notebook
        confidence = 1.0
    else:
        detected_notebook, confidence = detect_notebook(query)

    # Load config
    config = _load_config()
    notebooks = config.get("notebooks", {})

    if detected_notebook not in notebooks:
        return {
            "answer": f"Unknown notebook: {detected_notebook}",
            "notebook": detected_notebook,
            "confidence": confidence,
            "sources": [],
            "error": True,
        }

    notebook_config = notebooks[detected_notebook]
    vector_store_id = notebook_config.get("vector_store_id")

    if not vector_store_id:
        return {
            "answer": f"The {detected_notebook} notebook doesn't have a vector store configured yet.",
            "notebook": detected_notebook,
            "confidence": confidence,
            "sources": [],
            "error": True,
        }

    # Get query hints
    hints = notebook_config.get("query_hints", [])
    enhanced_query = query
    if hints:
        hint_text = ", ".join(hints[:5])
        enhanced_query = f"{query}\n\nSearch focus: {hint_text}"

    # Query the vector store
    defaults = _get_defaults(config)

    try:
        client = OpenAIFileSearchClient(model="gpt-4.1-mini", timeout=120)
        ok, answer, sources = client.query(
            prompt=enhanced_query,
            vector_store_id=vector_store_id,
            max_results=defaults.get("max_results", 20),
            include_results=True,
            strict=defaults.get("strict", True),
            score_threshold=defaults.get("score_threshold", 0.25),
            context_results=defaults.get("context_results", 3),
            context_chars=defaults.get("context_chars", 4000),
        )

        if not ok:
            return {
                "answer": f"Query failed: {answer}",
                "notebook": detected_notebook,
                "confidence": confidence,
                "sources": [],
                "error": True,
            }

        formatted_answer = format_natural_response(answer, sources, detected_notebook)

        return {
            "answer": formatted_answer,
            "notebook": detected_notebook,
            "confidence": confidence,
            "sources": sources,
            "error": False,
        }

    except Exception as e:
        return {
            "answer": f"Error querying RAG: {str(e)}",
            "notebook": detected_notebook,
            "confidence": confidence,
            "sources": [],
            "error": True,
        }


def main():
    """CLI interface for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Natural Language RAG Query")
    parser.add_argument("query", nargs="?", help="Natural language question")
    parser.add_argument("--notebook", "-n", help="Force specific notebook")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")

    args = parser.parse_args()

    if not args.query:
        # Interactive mode
        print("Natural Language RAG Query")
        print("Type your questions naturally. Examples:")
        print("  - How does an order set work?")
        print("  - What is a SmartSet?")
        print("  - Tell me about preference lists")
        print()

        while True:
            try:
                query = input("Question: ").strip()
                if not query:
                    continue
                if query.lower() in ("quit", "exit", "q"):
                    break

                result = query_natural(query, args.notebook, args.verbose)

                if args.json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"\n[{result['notebook']}] (confidence: {result['confidence']:.0%})")
                    print(result['answer'])
                    print()

            except KeyboardInterrupt:
                break
            except EOFError:
                break
    else:
        result = query_natural(args.query, args.notebook, args.verbose)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if args.verbose:
                print(f"Notebook: {result['notebook']} (confidence: {result['confidence']:.0%})")
            print(result['answer'])


if __name__ == "__main__":
    main()
