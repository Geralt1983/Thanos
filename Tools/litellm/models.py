#!/usr/bin/env python3
"""
Shared data models for LiteLLM client.

This module provides standardized data structures used throughout the LiteLLM
package for representing API responses, tracking usage, and passing data between
components.

Key Classes:
    ModelResponse: Standardized response object containing content, usage metrics,
                   cost information, and metadata from any model provider.

Usage:
    from Tools.litellm.models import ModelResponse

    # Create a response object
    response = ModelResponse(
        content="Assistant response text",
        model="claude-sonnet-4-20250514",
        provider="anthropic",
        input_tokens=150,
        output_tokens=200,
        total_tokens=350,
        cost_usd=0.0025,
        latency_ms=1234.5,
        cached=False,
        metadata={"complexity": 0.6, "tier": "standard"}
    )

The ModelResponse dataclass provides a consistent interface across all model
providers (Anthropic, OpenAI, Google, etc.), allowing the client to work with
any backend uniformly. This abstraction layer enables seamless model switching
and comparison without code changes.
"""

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class ModelResponse:
    """Standardized response from any model provider."""
    content: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    latency_ms: float
    cached: bool = False
    metadata: Dict = field(default_factory=dict)
