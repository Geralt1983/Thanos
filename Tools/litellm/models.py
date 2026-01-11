#!/usr/bin/env python3
"""
Shared data models for LiteLLM client.

This module contains dataclasses and type definitions shared across
the LiteLLM package modules.
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
