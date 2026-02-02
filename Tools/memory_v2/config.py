"""
Configuration for Thanos Memory V2.

Integrates:
- mem0 for fact extraction
- Voyage AI voyage-3 for embeddings (1024 dimensions)
- Neon pgvector for storage
- Heat decay for ADHD-friendly memory surfacing

Embedding Migration:
- Old: OpenAI text-embedding-3-small (1536 dimensions)
- New: Voyage AI voyage-3 (1024 dimensions)
- Set USE_VOYAGE=false to use OpenAI (backward compatibility)
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

# Embedding provider selection
USE_VOYAGE = os.getenv("USE_VOYAGE", "true").lower() == "true"
EMBEDDING_DIMENSIONS = 1024 if USE_VOYAGE else 1536
EMBEDDING_MODEL = "voyage-3" if USE_VOYAGE else "text-embedding-3-small"

# User configuration
DEFAULT_USER_ID = "jeremy"

# mem0 configuration
# Note: mem0 is used for fact extraction only
# It always uses OpenAI embeddings internally (mem0 doesn't support Voyage)
# Our direct search/add operations use Voyage when USE_VOYAGE=true
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
            "model": "text-embedding-3-small"  # mem0 requires OpenAI models
        }
    },
    "vector_store": {
        "provider": "pgvector",
        "config": {
            **NEON_CONFIG,
            "collection_name": "thanos_memories"  # mem0 creates its own table
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

    if USE_VOYAGE and not VOYAGE_API_KEY:
        print("WARNING: VOYAGE_API_KEY not set but USE_VOYAGE=true, falling back to OpenAI embeddings")
        # Auto-switch to OpenAI if Voyage key missing
        globals()['USE_VOYAGE'] = False
        globals()['EMBEDDING_DIMENSIONS'] = 1536
        globals()['EMBEDDING_MODEL'] = "text-embedding-3-small"

    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(errors))

    return True


if __name__ == "__main__":
    # Test configuration
    print("Memory V2 Configuration")
    print("=" * 40)
    print(f"Database URL: {'✓ Set' if NEON_DATABASE_URL else '✗ Missing'}")
    print(f"Voyage API Key: {'✓ Set' if VOYAGE_API_KEY else '⚠ Missing'}")
    print(f"OpenAI API Key: {'✓ Set' if OPENAI_API_KEY else '✗ Missing'}")
    print()
    print(f"Embedding Provider: {'Voyage AI' if USE_VOYAGE else 'OpenAI'}")
    print(f"Embedding Model: {EMBEDDING_MODEL}")
    print(f"Embedding Dimensions: {EMBEDDING_DIMENSIONS}")

    try:
        validate_config()
        print("\n✓ Configuration valid")
    except ValueError as e:
        print(f"\n✗ {e}")
