"""
Configuration for Thanos Memory V2.

Integrates:
- mem0 for fact extraction and embedding generation
- OpenAI text-embedding-3-small for embeddings (1536 dimensions)
- Neon pgvector for storage
- Heat decay for ADHD-friendly memory surfacing
"""

import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)

# Database configuration
NEON_DATABASE_URL = os.getenv("THANOS_MEMORY_DATABASE_URL")

# Parse Neon URL into components for mem0
def parse_neon_url(url: str) -> dict:
    """Parse Neon connection URL into individual components."""
    if not url:
        return {}

    parsed = urlparse(url)
    return {
        "host": parsed.hostname,
        "port": str(parsed.port or 5432),
        "user": parsed.username,
        "password": parsed.password,
        "dbname": parsed.path.lstrip('/').split('?')[0],
    }

NEON_CONFIG = parse_neon_url(NEON_DATABASE_URL)

# API Keys
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# User configuration
DEFAULT_USER_ID = "jeremy"

# mem0 configuration
# Note: mem0 doesn't support Voyage embeddings natively, so we use OpenAI
# For Voyage, we use direct API calls in our custom implementation
MEM0_CONFIG = {
    "llm": {
        "provider": "openai",
        "config": {
            "model": "gpt-4o-mini",  # Cheap, fast for extraction
            "api_key": OPENAI_API_KEY
        }
    },
    "embedder": {
        "provider": "openai",
        "config": {
            "api_key": OPENAI_API_KEY,
            "model": "text-embedding-3-small"  # 1536 dimensions
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            **NEON_CONFIG,
            "collection_name": "memories"  # Must match setup_neon.sql table name
        }
    },
    "version": "v1.1"
}

# Heat decay configuration
HEAT_CONFIG = {
    "initial_heat": 1.0,          # New memories start here
    "decay_rate": 0.97,           # Multiply by this daily (3% decay)
    "access_boost": 0.15,         # Added when memory is retrieved
    "mention_boost": 0.10,        # Added when related entity mentioned
    "min_heat": 0.05,             # Floor - never fully forgotten
    "max_heat": 2.0,              # Ceiling - prevents runaway
    "decay_interval_hours": 24,   # How often decay runs
}

# Memory type mappings
MEMORY_TYPES = {
    "preference": "Likes, dislikes, how they want things",
    "personal": "Facts about self",
    "professional": "Work-related facts",
    "relationship": "People connections",
    "client": "Client-specific info",
    "project": "Project details",
    "goal": "Objectives",
    "pattern": "Observed behaviors",
    "health": "Health-related",
}

# Source mappings
SOURCES = {
    "hey_pocket": "Meeting transcripts from Hey Pocket",
    "telegram": "Voice dumps from Telegram bot",
    "manual": "Direct input",
    "claude_code": "Captured from Claude Code session",
    "brain_dump": "From brain dump processing",
}

def validate_config():
    """Validate that required configuration is present."""
    errors = []

    if not NEON_DATABASE_URL:
        errors.append("THANOS_MEMORY_DATABASE_URL not set in .env")

    if not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY not set in .env (needed for mem0 extraction)")

    if not VOYAGE_API_KEY:
        # Warning, not error - can fall back to OpenAI
        print("WARNING: VOYAGE_API_KEY not set, falling back to OpenAI embeddings")

    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(errors))

    return True


if __name__ == "__main__":
    # Test configuration
    print("Memory V2 Configuration")
    print("=" * 40)
    print(f"Database URL: {'✓ Set' if NEON_DATABASE_URL else '✗ Missing'}")
    print(f"Voyage API Key: {'✓ Set' if VOYAGE_API_KEY else '⚠ Missing (using OpenAI)'}")
    print(f"OpenAI API Key: {'✓ Set' if OPENAI_API_KEY else '✗ Missing'}")
    print()
    print("Embedder:", MEM0_CONFIG["embedder"]["config"]["model"])

    try:
        validate_config()
        print("\n✓ Configuration valid")
    except ValueError as e:
        print(f"\n✗ {e}")
