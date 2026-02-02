#!/usr/bin/env python3
"""
Unified Web Search Tool

Primary: Perplexity for web search
Secondary: Grok X search for social-relevant queries (cost-conscious)
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Import our search tools
from perplexity_search import perplexity_search
from grok_search import grok_search

# Keywords that suggest X/Twitter search would add value
X_RELEVANT_KEYWORDS = [
    'ai', 'artificial intelligence', 'llm', 'gpt', 'claude', 'gemini', 'grok',
    'openai', 'anthropic', 'google', 'meta', 'microsoft', 'nvidia', 'apple',
    'trending', 'news', 'breaking', 'announcement', 'launch', 'release',
    'twitter', 'x.com', 'elon', 'musk', 'zuckerberg', 'altman', 'pichai',
    'tech', 'startup', 'vc', 'funding', 'crypto', 'bitcoin', 'ethereum',
    'openclaw', 'moltbot', 'agent', 'automation', 'workflow',
    'controversy', 'debate', 'opinion', 'reaction', 'community',
]


def should_search_x(query: str) -> bool:
    """Determine if query would benefit from X/Twitter search."""
    query_lower = query.lower()
    
    # Check for relevant keywords
    for keyword in X_RELEVANT_KEYWORDS:
        if keyword in query_lower:
            return True
    
    # Check for time-sensitive patterns
    time_patterns = ['today', 'this week', 'latest', 'recent', 'new', 'just', 'breaking']
    for pattern in time_patterns:
        if pattern in query_lower:
            return True
    
    return False


def unified_search(query: str, force_x: bool = False, skip_x: bool = False, verbose: bool = False) -> dict:
    """
    Run unified web search with optional X enhancement.
    
    Args:
        query: Search query
        force_x: Always include X search
        skip_x: Never include X search
        verbose: Print progress
        
    Returns:
        Combined results dictionary
    """
    results = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "sources": []
    }
    
    # Always run Perplexity
    if verbose:
        print("🔍 Searching Perplexity...", file=sys.stderr)
    
    pplx_result = perplexity_search(query)
    
    if "error" in pplx_result:
        results["perplexity_error"] = pplx_result["error"]
    else:
        results["content"] = pplx_result.get("content", "")
        results["citations"] = pplx_result.get("citations", [])
        results["sources"].append("perplexity")
    
    # Conditionally run Grok X search
    run_x = (force_x or (should_search_x(query) and not skip_x))
    
    if run_x:
        if verbose:
            print("🐦 Query is X-relevant, searching Twitter...", file=sys.stderr)
        
        # Craft X-specific query
        x_query = f"Latest discussion and reactions on X/Twitter about: {query}"
        grok_result = grok_search(x_query, include_x=True, verbose=verbose)
        
        if "error" not in grok_result and grok_result.get("content"):
            results["x_supplement"] = {
                "content": grok_result.get("content", ""),
                "citations": grok_result.get("citations", []),
                "tool_calls": grok_result.get("tool_calls", [])
            }
            results["sources"].append("grok_x")
            
            if verbose:
                print("✅ X search added supplementary data", file=sys.stderr)
        elif verbose:
            print("⚠️ X search returned no useful data", file=sys.stderr)
    elif verbose:
        print("⏭️ Skipping X search (not relevant for this query)", file=sys.stderr)
    
    return results


def format_output(results: dict) -> str:
    """Format results for display."""
    output = []
    
    output.append(f"🔍 {results['query']}\n")
    
    # Main content from Perplexity
    if results.get("content"):
        output.append(results["content"])
    
    # Citations
    if results.get("citations"):
        output.append("\n📚 Sources:")
        for i, url in enumerate(results["citations"][:5], 1):
            output.append(f"  {i}. {url}")
    
    # X Supplement
    if results.get("x_supplement"):
        output.append("\n" + "─" * 40)
        output.append("🐦 **X/Twitter Pulse:**")
        x_content = results["x_supplement"]["content"]
        # Truncate if too long
        if len(x_content) > 800:
            x_content = x_content[:800] + "..."
        output.append(x_content)
        
        if results["x_supplement"].get("citations"):
            output.append("\n🔗 X Sources:")
            for i, url in enumerate(results["x_supplement"]["citations"][:3], 1):
                output.append(f"  {i}. {url}")
    
    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description="Unified web search (Perplexity + optional Grok X)")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("--force-x", action="store_true", help="Always include X search")
    parser.add_argument("--skip-x", action="store_true", help="Never include X search")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show progress")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    query = " ".join(args.query)
    
    results = unified_search(
        query, 
        force_x=args.force_x, 
        skip_x=args.skip_x, 
        verbose=args.verbose
    )
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_output(results))


if __name__ == "__main__":
    main()
