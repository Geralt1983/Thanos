#!/usr/bin/env python3
"""
Gemini CLI - Unified interface for Gemini + NotebookLM research.

Usage:
    # Web search via NotebookLM research (adds sources)
    ./gemini_cli.py search "query" --notebook <id>

    # Deep research via NotebookLM (adds sources, deeper search)
    ./gemini_cli.py search "query" --notebook <id> --deep

    # One-shot generation via Gemini API
    ./gemini_cli.py generate "prompt"

    # Query NotebookLM sources
    ./gemini_cli.py query "question" --notebook <id>
"""

import os
import sys
import argparse
import json
import subprocess
from typing import List, Dict, Any, Optional
import requests
from pathlib import Path

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class GeminiCLI:
    """Unified Gemini + NotebookLM interface."""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def search(self, query: str, notebook_id: str, deep: bool = False) -> Dict[str, Any]:
        """
        Web search via NotebookLM research.
        
        Args:
            query: Search query
            notebook_id: NotebookLM notebook ID
            deep: Use deep research mode (slower, more thorough)
        
        Returns:
            Research results
        """
        cmd = ['nlm', 'source', 'add-research', query, '--notebook', notebook_id]
        if deep:
            cmd.extend(['--mode', 'deep'])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Research timed out (10 min)'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def query(self, question: str, notebook_id: str) -> Dict[str, Any]:
        """
        Query NotebookLM sources.
        
        Args:
            question: Question to ask
            notebook_id: NotebookLM notebook ID
        
        Returns:
            Query response
        """
        cmd = ['nlm', 'ask', '-n', notebook_id, '--new', question]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return {
                'success': result.returncode == 0,
                'answer': result.stdout.strip(),
                'error': result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Generate text via Gemini API.
        
        Args:
            prompt: Generation prompt
            max_tokens: Maximum tokens
        
        Returns:
            Generated text
        """
        if not self.api_key:
            return "Error: GEMINI_API_KEY not set"
        
        url = f"{self.base_url}/models/gemini-pro:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens}
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        except requests.RequestException as e:
            return f"Error: {e}"
    
    def list_notebooks(self) -> List[Dict[str, str]]:
        """List available NotebookLM notebooks."""
        try:
            result = subprocess.run(
                ['nlm', 'list', '--json'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            return []
        except Exception:
            return []


def main():
    parser = argparse.ArgumentParser(description="Gemini + NotebookLM CLI")
    subparsers = parser.add_subparsers(dest='command')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Web search via NotebookLM')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--notebook', '-n', required=True, help='Notebook ID')
    search_parser.add_argument('--deep', action='store_true', help='Deep research mode')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Query NotebookLM sources')
    query_parser.add_argument('question', help='Question to ask')
    query_parser.add_argument('--notebook', '-n', required=True, help='Notebook ID')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='One-shot generation')
    gen_parser.add_argument('prompt', help='Generation prompt')
    gen_parser.add_argument('--max-tokens', type=int, default=1000)
    
    # List notebooks command
    subparsers.add_parser('notebooks', help='List NotebookLM notebooks')
    
    args = parser.parse_args()
    gemini = GeminiCLI()
    
    if args.command == 'search':
        result = gemini.search(args.query, args.notebook, args.deep)
        if result['success']:
            print(result['output'])
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'query':
        result = gemini.query(args.question, args.notebook)
        if result['success']:
            print(result['answer'])
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'generate':
        response = gemini.generate(args.prompt, args.max_tokens)
        print(response)
    
    elif args.command == 'notebooks':
        notebooks = gemini.list_notebooks()
        if notebooks:
            for nb in notebooks:
                print(f"{nb.get('id', 'N/A')}: {nb.get('title', 'Untitled')}")
        else:
            print("No notebooks found or not authenticated")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
