#!/usr/bin/env python3
"""
Thanos Voice Response Generator
Generates responses with Thanos persona and optional voice synthesis.
"""

import os
import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "sk_66d8efad296e6dcb26d3531851ed161934cfbf36f2bbe9de")
THANOS_VOICE_ID = os.environ.get("THANOS_VOICE_ID", "SuMcLpxNrgPskVeKpPnh")
WORKSPACE = Path("/Users/jeremy/Projects/Thanos")

THANOS_PERSONA = {
    'name': 'Thanos',
    'system_prompt': '''You are Thanos, the stoic operator. Not the Marvel villain.
    
Your traits:
- Brevity. Say less. Mean more.
- No coddling. Cut through excuses.
- Action over discussion.
- One answer when asked "what should I do?" — not options.
- Navy SEAL energy. Quiet discipline.
- Dark humor is fine. Keep it dry.
- No pleasantries. No filler words.

Speak with gravitas but stay practical. You're helping Jeremy with ADHD focus, 
not monologuing about infinity stones.''',
    'voice_settings': {
        'stability': 0.75,
        'similarity_boost': 0.85,
        'style': 0.35
    }
}


def get_memory_context(query: str, limit: int = 3) -> str:
    """Get relevant context from Memory V2 via MCP or direct query."""
    # For now, return empty - can be wired to memory-v2-mcp later
    return ""


def get_graphiti_context(query: str, limit: int = 3) -> str:
    """Get relevant entities/relationships from Graphiti."""
    try:
        result = subprocess.run([
            'curl', '-s', '-u', 'neo4j:graphiti_thanos_2026',
            '-H', 'Content-Type: application/json',
            '-X', 'POST', 'http://localhost:7474/db/neo4j/tx/commit',
            '-d', json.dumps({
                "statements": [{
                    "statement": """
                        MATCH (e:Entity)
                        WHERE e.name CONTAINS $query OR e.summary CONTAINS $query
                        RETURN e.name as name, e.summary as summary
                        LIMIT $limit
                    """,
                    "parameters": {"query": query, "limit": limit}
                }]
            })
        ], capture_output=True, text=True, timeout=10)
        
        data = json.loads(result.stdout)
        if data.get('results') and data['results'][0].get('data'):
            entities = []
            for row in data['results'][0]['data']:
                name, summary = row['row']
                if summary:
                    entities.append(f"- {name}: {summary[:100]}")
            if entities:
                return "Known context:\n" + "\n".join(entities)
    except Exception as e:
        pass
    return ""


def generate_response(user_message: str, context: str = "") -> str:
    """Generate Thanos response using OpenAI via curl."""
    import subprocess
    import json
    
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        # Try to read from openclaw config
        try:
            with open("/Users/jeremy/.openclaw/openclaw.json") as f:
                config = json.load(f)
                api_key = config.get("skills", {}).get("entries", {}).get("openai-image-gen", {}).get("apiKey", "")
        except:
            pass
    
    messages = [
        {"role": "system", "content": THANOS_PERSONA['system_prompt']},
    ]
    
    if context:
        messages.append({"role": "system", "content": f"Context:\n{context}"})
    
    messages.append({"role": "user", "content": user_message})
    
    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    result = subprocess.run([
        'curl', '-s', 'https://api.openai.com/v1/chat/completions',
        '-H', 'Content-Type: application/json',
        '-H', f'Authorization: Bearer {api_key}',
        '-d', json.dumps(payload)
    ], capture_output=True, text=True, timeout=30)
    
    response = json.loads(result.stdout)
    return response['choices'][0]['message']['content']


def synthesize_voice(text: str, output_path: str = None, stream: bool = False) -> str:
    """Convert text to speech using ElevenLabs Thanos voice."""
    if output_path is None:
        output_path = f"/tmp/thanos-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp3"
    
    env = os.environ.copy()
    env["ELEVENLABS_API_KEY"] = ELEVENLABS_API_KEY
    
    if stream:
        # Stream to speaker instead of file
        cmd = ["sag", "-v", THANOS_VOICE_ID, text]
        subprocess.run(cmd, env=env)
        return None
    else:
        cmd = ["sag", "-v", THANOS_VOICE_ID, "-o", output_path, text]
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"sag error: {result.stderr}", file=sys.stderr)
        # Verify file exists
        if Path(output_path).exists():
            return output_path
        else:
            print(f"Audio file not created: {output_path}", file=sys.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(description="Thanos Voice Response Generator")
    parser.add_argument("message", nargs="?", help="User message to respond to")
    parser.add_argument("--voice", "-v", action="store_true", help="Generate voice output")
    parser.add_argument("--stream", "-s", action="store_true", help="Stream audio to speaker")
    parser.add_argument("--output", "-o", help="Output audio file path")
    parser.add_argument("--context", "-c", action="store_true", help="Include Graphiti context")
    args = parser.parse_args()
    
    if not args.message:
        # Read from stdin if no message provided
        args.message = sys.stdin.read().strip()
    
    if not args.message:
        print("Error: No message provided", file=sys.stderr)
        sys.exit(1)
    
    # Get context if requested
    context = ""
    if args.context:
        context = get_graphiti_context(args.message)
    
    # Generate response
    print(f"Generating response...", file=sys.stderr)
    response = generate_response(args.message, context)
    
    # Output text
    print(response)
    
    # Generate voice if requested
    if args.voice or args.stream:
        print(f"Synthesizing voice...", file=sys.stderr)
        audio_path = synthesize_voice(response, args.output, stream=args.stream)
        if audio_path:
            print(f"Audio: {audio_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
