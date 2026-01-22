#!/usr/bin/env python3
"""
Security Utilities

Credential masking and security helpers for Thanos.
"""

import re
from typing import Any, Dict


def mask_credential(value: str, visible_chars: int = 4) -> str:
    """
    Mask a credential string, showing only the last N characters.

    Args:
        value: The credential to mask
        visible_chars: Number of characters to show at the end

    Returns:
        Masked string like "sk-ant-***kTJw" or "***" if too short

    Examples:
        >>> mask_credential("sk-ant-api03-93h6HgR_UGP2mytFeUpA8YG...")
        'sk-ant-***kTJw'
        >>> mask_credential("secret123", 3)
        '***123'
    """
    if not value or len(value) <= visible_chars:
        return "***"

    # For API keys with prefixes (sk-ant-, sk-proj-, etc.)
    if value.startswith(("sk-", "npg_", "neo4j+s://")):
        # Keep prefix and last N chars
        parts = value.split("-", 2)
        if len(parts) >= 2:
            prefix = "-".join(parts[:2])
            suffix = value[-visible_chars:]
            return f"{prefix}-***{suffix}"

    # Default: mask everything except last N chars
    return f"***{value[-visible_chars:]}"


def mask_dict(data: Dict[str, Any], sensitive_keys: list = None) -> Dict[str, Any]:
    """
    Mask sensitive values in a dictionary for safe logging.

    Args:
        data: Dictionary to mask
        sensitive_keys: List of key names to mask (case-insensitive)

    Returns:
        Dictionary with masked values

    Examples:
        >>> mask_dict({"api_key": "secret123", "name": "Jeremy"})
        {'api_key': '***123', 'name': 'Jeremy'}
    """
    if sensitive_keys is None:
        sensitive_keys = [
            "api_key", "apikey", "api-key",
            "password", "passwd", "pwd",
            "secret", "token", "bearer",
            "access_token", "refresh_token",
            "client_secret", "private_key",
            "database_url", "connection_string",
        ]

    sensitive_keys_lower = [k.lower() for k in sensitive_keys]
    masked = {}

    for key, value in data.items():
        if key.lower() in sensitive_keys_lower:
            if isinstance(value, str):
                masked[key] = mask_credential(value)
            else:
                masked[key] = "***"
        else:
            masked[key] = value

    return masked


def sanitize_log_message(message: str) -> str:
    """
    Remove potential credentials from log messages.

    Args:
        message: Log message to sanitize

    Returns:
        Message with credentials masked

    Examples:
        >>> sanitize_log_message("Bearer sk-ant-api03-93h6HgR...")
        'Bearer sk-ant-***...'
    """
    patterns = [
        # Anthropic API keys
        (r'sk-ant-api\d+-[A-Za-z0-9_-]{95}', r'sk-ant-***'),
        # OpenAI API keys
        (r'sk-proj-[A-Za-z0-9_-]{48,}', r'sk-proj-***'),
        # Generic bearer tokens
        (r'Bearer\s+([A-Za-z0-9_-]{20,})', r'Bearer ***'),
        # Database URLs with passwords
        (r'postgresql://([^:]+):([^@]+)@', r'postgresql://\1:***@'),
        # Neo4j passwords
        (r'neo4j\+s://([^:]+):([^@]+)@', r'neo4j+s://\1:***@'),
        # Generic API keys in URLs
        (r'[?&](api_key|apikey|key|token)=([^&\s]+)', r'\1=***'),
    ]

    result = message
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)

    return result


def safe_repr(obj: Any, max_length: int = 100) -> str:
    """
    Safe representation of objects for logging.

    Truncates long strings and masks potential credentials.

    Args:
        obj: Object to represent
        max_length: Maximum string length before truncation

    Returns:
        Safe string representation
    """
    if isinstance(obj, dict):
        # Mask sensitive dictionary keys
        masked = mask_dict(obj)
        repr_str = str(masked)
    else:
        repr_str = str(obj)

    # Sanitize any credentials in the string
    repr_str = sanitize_log_message(repr_str)

    # Truncate if too long
    if len(repr_str) > max_length:
        repr_str = repr_str[:max_length] + "..."

    return repr_str


if __name__ == "__main__":
    # Test the functions
    print("Testing credential masking:")
    print()

    # Test mask_credential
    test_keys = [
        "sk-ant-api03-EXAMPLE_KEY_FOR_TESTING_ONLY_NOT_REAL_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890",
        "sk-proj-EXAMPLE_KEY_FOR_TESTING_ONLY_NOT_REAL_12345678",
        "npg_EXAMPLE_PASS",
        "secret123",
    ]

    for key in test_keys:
        print(f"Original: {key[:30]}...")
        print(f"Masked:   {mask_credential(key)}")
        print()

    # Test mask_dict
    config = {
        "api_key": "sk-ant-secret123",
        "name": "Jeremy",
        "database_url": "postgresql://user:password@host/db",
        "timeout": 30
    }
    print("Original dict:", config)
    print("Masked dict:", mask_dict(config))
    print()

    # Test sanitize_log_message
    messages = [
        "API call with Bearer sk-ant-api03-93h6HgR_UGP2m...",
        "Connecting to postgresql://user:password@localhost/db",
        "Request failed: api_key=sk-proj-A9pzvVWMFbbK",
    ]

    for msg in messages:
        print(f"Original: {msg}")
        print(f"Sanitized: {sanitize_log_message(msg)}")
        print()
