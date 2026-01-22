#!/usr/bin/env python3
"""Thanos Voice Synthesis Hook - Plays voice for Claude Code responses."""

import sys
import re
from pathlib import Path
import subprocess

# Debug log
debug_log = Path.home() / ".thanos" / "voice-hook-debug.log"
debug_log.parent.mkdir(exist_ok=True)

def log_debug(msg):
    with open(debug_log, 'a') as f:
        from datetime import datetime
        f.write(f"{datetime.now().isoformat()} - {msg}\n")

log_debug("=== Hook triggered ===")

# Add Shell/lib to path for voice module
shell_lib_path = Path(__file__).parent.parent.parent / "Shell" / "lib"
sys.path.insert(0, str(shell_lib_path))

try:
    from voice import synthesize
    VOICE_AVAILABLE = True
    log_debug("Voice module loaded")
except ImportError as e:
    VOICE_AVAILABLE = False
    log_debug(f"Voice import failed: {e}")


def extract_voice_text(content: str, max_sentences: int = 2) -> str:
    """Extract clean text for voice synthesis."""
    if not content:
        return ""

    # Remove tool use blocks
    content = re.sub(r'<function_calls>[\s\S]*?</function_calls>', '', content)
    content = re.sub(r'<function_results>[\s\S]*?</function_results>', '', content)
    
    # Remove markdown code blocks
    content = re.sub(r'```[\s\S]*?```', '', content)
    
    # Remove inline code
    content = re.sub(r'`[^`]+`', '', content)
    
    # Remove URLs
    content = re.sub(r'http[s]?://\S+', '', content)
    
    # Remove tables
    content = re.sub(r'\|.*\|', '', content)
    
    # Split into sentences
    sentences = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith(('#', '-', '*', '>', '|', '=')):
            # Split by sentence endings
            for sent in re.split(r'[.!?]+\s+', line):
                sent = sent.strip()
                if sent and len(sent) > 10:
                    sentences.append(sent)
    
    # Take first N sentences
    voice_text = '. '.join(sentences[:max_sentences])
    if voice_text and not voice_text.endswith('.'):
        voice_text += '.'
    
    return voice_text


def main():
    """Main entry point - reads stdin and synthesizes voice."""
    log_debug("Main started")
    
    if not VOICE_AVAILABLE:
        log_debug("Voice not available, exiting")
        sys.exit(0)
    
    # Read response from stdin
    content = sys.stdin.read()
    log_debug(f"Read {len(content)} chars from stdin")
    
    # Extract clean text
    voice_text = extract_voice_text(content)
    log_debug(f"Extracted voice text: {voice_text[:100]}...")
    
    if not voice_text or len(voice_text) < 10:
        log_debug("Text too short, skipping")
        sys.exit(0)
    
    try:
        # Synthesize
        audio_path = synthesize(voice_text, play=False)
        log_debug(f"Synthesized to: {audio_path}")
        
        if audio_path and audio_path.exists():
            # Play with afplay directly
            result = subprocess.run(['afplay', str(audio_path)], 
                                   capture_output=True, 
                                   timeout=10)
            log_debug(f"afplay returned: {result.returncode}")
            if result.stderr:
                log_debug(f"afplay stderr: {result.stderr.decode()}")
        else:
            log_debug("Audio path invalid")
            
    except Exception as e:
        log_debug(f"Error: {e}")
        import traceback
        log_debug(traceback.format_exc())
    
    sys.exit(0)


if __name__ == "__main__":
    main()
