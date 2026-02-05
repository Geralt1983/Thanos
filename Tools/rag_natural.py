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

# Notebook routing patterns - order matters (most specific first)
NOTEBOOK_PATTERNS = [
    # NCDHHS / Radiology patterns
    (r"\bncdhhs\b", "ncdhhs_radiology"),
    (r"\bnc\s*dhhs\b", "ncdhhs_radiology"),
    (r"\bradiology\b", "ncdhhs_radiology"),
    (r"\bnorth\s*carolina.*health", "ncdhhs_radiology"),

    # Orders / Epic / HOD patterns
    (r"\border\s*set", "orders_hod"),
    (r"\bsmart\s*set", "orders_hod"),
    (r"\bsmart\s*group", "orders_hod"),
    (r"\bpreference\s*list", "orders_hod"),
    (r"\border\s*composer", "orders_hod"),
    (r"\bhod\b", "orders_hod"),
    (r"\bepic\b", "orders_hod"),
    (r"\bpatient\s*list", "orders_hod"),
    (r"\borders?\b", "orders_hod"),
    (r"\bpanel", "orders_hod"),
    (r"\bworkflow", "orders_hod"),
    (r"\bextension\s*record", "orders_hod"),
    (r"\bmanage\s*orders", "orders_hod"),
    (r"\bosq\b", "orders_hod"),

    # VersaCare / ScottCare patterns
    (r"\bversacare\b", "versacare"),
    (r"\bscottcare\b", "versacare"),
    (r"\bkentucky\b", "versacare"),
    (r"\bcardiac\s*rehab", "versacare"),
    (r"\btelemonitoring\b", "versacare"),

    # Harry patterns
    (r"\bharry", "harry"),

    # Drive inbox (default fallback for generic queries)
    (r"\binbox\b", "drive_inbox"),
    (r"\bdrive\b", "drive_inbox"),
]

# Default notebook when no pattern matches
DEFAULT_NOTEBOOK = "orders_hod"


def detect_notebook(query: str) -> Tuple[str, float]:
    """
    Detect which notebook to query based on natural language input.
    Returns (notebook_key, confidence_score).
    """
    query_lower = query.lower()

    for pattern, notebook in NOTEBOOK_PATTERNS:
        if re.search(pattern, query_lower):
            # Higher confidence for longer/more specific patterns
            confidence = min(0.9, 0.5 + len(pattern) / 50)
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
