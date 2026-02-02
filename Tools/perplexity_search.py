#!/usr/bin/env python3
"""
Perplexity Web Search Tool

Uses Perplexity API for AI-powered web search with citations.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

import requests


def perplexity_search(query: str, detailed: bool = False) -> dict:
    """
    Search the web using Perplexity API.
    
    Args:
        query: Search query string
        detailed: Return more detailed results
        
    Returns:
        Dictionary with search results and citations
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return {"error": "PERPLEXITY_API_KEY not set", "results": []}
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Use sonar model for web search
    payload = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a research assistant. Provide concise, factual answers with sources. Focus on recent information."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.2,
        "return_citations": True,
        "return_related_questions": False
    }
    
    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=45
        )
        response.raise_for_status()
        data = response.json()
        
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])
        
        return {
            "query": query,
            "content": content,
            "citations": citations,
            "model": data.get("model", "sonar"),
            "timestamp": datetime.now().isoformat()
        }
        
    except requests.RequestException as e:
        return {"error": str(e), "results": []}


def main():
    parser = argparse.ArgumentParser(description="Search the web using Perplexity")
    parser.add_argument("query", nargs="+", help="Search query")
    parser.add_argument("-d", "--detailed", action="store_true", help="Detailed output")
    parser.add_argument("-j", "--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    query = " ".join(args.query)
    
    result = perplexity_search(query, detailed=args.detailed)
    
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
            for i, url in enumerate(result["citations"][:5], 1):
                print(f"  {i}. {url}")


if __name__ == "__main__":
    main()
