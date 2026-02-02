#!/usr/bin/env python3
"""
Grok Web Search Tool

Uses xAI's server-side agentic tools for real-time web and X/Twitter search.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from xai_sdk import Client
from xai_sdk.chat import user, system
from xai_sdk.tools import web_search, x_search


def grok_search(query: str, include_x: bool = True, verbose: bool = False) -> dict:
    """
    Search using Grok's server-side agentic tools.
    
    Args:
        query: Search query string
        include_x: Include X/Twitter search
        verbose: Print real-time tool calls
        
    Returns:
        Dictionary with search results and citations
    """
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return {"error": "XAI_API_KEY not set"}
    
    try:
        client = Client(api_key=api_key, timeout=120)
        
        # Configure tools
        tools = [web_search()]
        if include_x:
            tools.append(x_search())
        
        chat = client.chat.create(
            model="grok-4-0709",  # grok-4 required for server-side tools
            tools=tools,
        )
        
        chat.append(user(query))
        
        # Collect response
        full_content = ""
        tool_calls_made = []
        citations = []
        
        for response, chunk in chat.stream():
            # Track tool calls
            for tool_call in chunk.tool_calls:
                tool_calls_made.append({
                    "name": tool_call.function.name,
                    "args": tool_call.function.arguments
                })
                if verbose:
                    print(f"🔧 {tool_call.function.name}: {tool_call.function.arguments}", file=sys.stderr)
            
            if chunk.content:
                full_content += chunk.content
        
        # Get citations from final response
        if hasattr(response, 'citations') and response.citations:
            citations = response.citations
        
        return {
            "query": query,
            "content": full_content,
            "citations": citations,
            "tool_calls": tool_calls_made,
            "model": "grok-4",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Search the web using Grok with X/Twitter access")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("--no-x", action="store_true", help="Disable X/Twitter search")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show tool calls")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    query = " ".join(args.query)
    
    result = grok_search(query, include_x=not args.no_x, verbose=args.verbose)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"Error: {result['error']}")
            sys.exit(1)
        
        print(f"🔍 {query}\n")
        print(result.get("content", "No results"))
        
        if result.get("citations"):
            print("\n📚 Sources:")
            for i, url in enumerate(result["citations"][:8], 1):
                print(f"  {i}. {url}")


if __name__ == "__main__":
    main()
