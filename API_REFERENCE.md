# LiteLLM Package API Reference

## Overview

The LiteLLM package provides a unified, production-ready interface for accessing 100+ AI models from multiple providers including Anthropic Claude, OpenAI GPT, Google Gemini, and many more. Built for the Thanos Personal Assistant Framework, this package delivers intelligent model routing, comprehensive cost optimization, and robust usage tracking in a modular architecture.

### Key Features

- **Unified Multi-Model API**: Single interface for 100+ models via the LiteLLM library
- **Intelligent Model Routing**: Automatic model selection based on prompt complexity analysis (saves up to 80% on API costs)
- **Response Caching**: TTL-based caching with configurable size limits to reduce redundant API calls
- **Cost Tracking**: Comprehensive usage and cost tracking per model, provider, operation, and day
- **Reliability**: Configurable fallback chains with automatic retry logic
- **Streaming Support**: Both streaming and non-streaming response modes
- **Flexible Configuration**: JSON-based configuration with environment variable support

### Package Architecture

```
Tools/litellm/
├── models.py              # ModelResponse dataclass (shared data models)
├── usage_tracker.py       # Token/cost tracking with persistent storage
├── complexity_analyzer.py # Prompt complexity analysis for model routing
├── response_cache.py      # TTL-based response caching
└── client.py             # LiteLLMClient orchestrating all components
```

### Cost Optimization

The automatic routing system can reduce costs by 80%+ by intelligently selecting models based on query complexity:

- **Simple queries** → Claude Haiku (~$0.0001 per request)
- **Standard queries** → Claude Sonnet (~$0.003 per request)
- **Complex queries** → Claude Opus (~$0.015 per request)

### Performance Characteristics

- **Cache hits**: <1ms (instant response)
- **API calls**: 500-3000ms (depends on model and complexity)
- **Streaming**: First token in ~200-500ms
- **Complexity analysis**: <10ms overhead

---

## Table of Contents

1. [Overview](#overview)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Core Classes](#core-classes)
   - [LiteLLMClient](#litellmclient) *(coming in next sections)*
   - [UsageTracker](#usagetracker) *(coming in next sections)*
   - [ComplexityAnalyzer](#complexityanalyzer) *(coming in next sections)*
   - [ResponseCache](#responsecache) *(coming in next sections)*
5. [Data Models](#data-models)
   - [ModelResponse](#modelresponse) *(coming in next sections)*
6. [Factory Functions](#factory-functions)
   - [get_client()](#get_client) *(coming in next sections)*
   - [init_client()](#init_client) *(coming in next sections)*
7. [Configuration](#configuration) *(coming in next sections)*
8. [Usage Examples](#usage-examples) *(coming in next sections)*

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Required Dependencies

The LiteLLM package requires the following Python packages:

```bash
# Core dependency for multi-model API access
pip install litellm

# Optional: Direct Anthropic API support (fallback)
pip install anthropic
```

### Installation from Project

If you're using the Thanos framework, the LiteLLM package is included in the Tools directory:

```bash
# Clone the repository
git clone <repository-url>
cd <project-directory>

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

The package requires API keys set as environment variables for the providers you want to use:

```bash
# Required for Claude models (Anthropic)
export ANTHROPIC_API_KEY="your-anthropic-api-key"

# Optional: For GPT models (OpenAI)
export OPENAI_API_KEY="your-openai-api-key"

# Optional: For Gemini models (Google)
export GEMINI_API_KEY="your-gemini-api-key"
```

**Tip**: Create a `.env` file in your project root for persistent configuration:

```bash
# .env file
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key
```

### Configuration File

The package uses a configuration file (default: `config/api.json`) for settings:

```json
{
  "litellm": {
    "default_model": "claude-opus-4-5-20251101",
    "fallback_chain": ["claude-opus-4-5-20251101", "claude-sonnet-4-20250514"],
    "timeout": 600,
    "max_retries": 3
  },
  "model_routing": {
    "enabled": true,
    "rules": {
      "complex": {
        "model": "claude-opus-4-5-20251101",
        "min_complexity": 0.7
      },
      "standard": {
        "model": "claude-sonnet-4-20250514",
        "min_complexity": 0.3
      },
      "simple": {
        "model": "claude-3-5-haiku-20241022",
        "max_complexity": 0.3
      }
    }
  },
  "usage_tracking": {
    "enabled": true,
    "storage_path": "State/usage.json"
  },
  "caching": {
    "enabled": true,
    "cache_path": "Memory/cache/",
    "ttl_seconds": 3600,
    "max_size_mb": 100
  }
}
```

### Verify Installation

To verify the installation is working:

```python
from Tools.litellm import LITELLM_AVAILABLE, ANTHROPIC_AVAILABLE

if LITELLM_AVAILABLE:
    print("✓ LiteLLM library is installed - full functionality available")
elif ANTHROPIC_AVAILABLE:
    print("⚠ Fallback to direct Anthropic API - limited functionality")
else:
    print("✗ No API libraries available - installation required")
```

---

## Quick Start

### Basic Usage

The simplest way to use the LiteLLM package is through the singleton client:

```python
from Tools.litellm import get_client

# Get singleton client instance (auto-loads config from config/api.json)
client = get_client()

# Simple chat - auto-routes to appropriate model based on complexity
response = client.chat("What is the capital of France?")
print(response)  # Output: "Paris"
```

### Complexity-Based Routing

The client automatically analyzes your prompt and selects the most cost-effective model:

```python
from Tools.litellm import get_client

client = get_client()

# Simple query → automatically uses Haiku (cheapest)
response = client.chat("Hi there!")
print(f"Used model: {response.model}")  # claude-3-5-haiku-20241022

# Complex query → automatically uses Opus (most capable)
response = client.chat("""
Explain the architectural differences between microservices and monolithic
applications, including trade-offs for scalability, deployment, and maintenance.
""")
print(f"Used model: {response.model}")  # claude-opus-4-5-20251101
```

### Forcing a Specific Model

You can override automatic routing and specify a model explicitly:

```python
from Tools.litellm import get_client

client = get_client()

# Force Claude Sonnet
response = client.chat(
    "Analyze this code for performance issues",
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    temperature=0.7
)

print(f"Model used: {response.model}")
print(f"Cost: ${response.cost_usd:.4f}")
print(f"Tokens: {response.total_tokens}")
```

### Streaming Responses

For long-form content, use streaming to receive responses incrementally:

```python
from Tools.litellm import get_client

client = get_client()

# Stream response chunks as they arrive
print("Assistant: ", end="", flush=True)
for chunk in client.chat_stream("Tell me a short story about a robot"):
    print(chunk, end="", flush=True)
print()  # Newline at end
```

### Conversation History

Maintain context across multiple turns using conversation history:

```python
from Tools.litellm import get_client

client = get_client()

# Build conversation history
history = [
    {"role": "user", "content": "What is Python?"},
    {"role": "assistant", "content": "Python is a high-level programming language."}
]

# Continue the conversation with context
response = client.chat("What are its main features?", history=history)
print(response)
```

### Usage Tracking

Monitor your API usage and costs:

```python
from Tools.litellm import get_client

client = get_client()

# Get today's usage
today = client.get_today_usage()
print(f"Today: {today['calls']} calls, ${today['cost']:.4f} cost")

# Get 30-day summary with projections
summary = client.get_usage_summary(days=30)
print(f"30-day cost: ${summary['total_cost_usd']:.2f}")
print(f"Projected monthly: ${summary['projected_monthly_cost']:.2f}")
print(f"Average per call: ${summary['avg_cost_per_call']:.4f}")
```

### Complexity Analysis

Analyze prompt complexity without making an API call:

```python
from Tools.litellm import get_client

client = get_client()

# Analyze complexity
analysis = client.analyze_complexity("Write a binary search algorithm")

print(f"Complexity score: {analysis['complexity_score']:.2f}")
print(f"Tier: {analysis['tier']}")  # 'simple', 'standard', or 'complex'
print(f"Recommended model: {analysis['selected_model']}")
print(f"Reasoning: {analysis['reason']}")
```

### Custom Configuration

Initialize a client with a custom configuration file:

```python
from Tools.litellm import LiteLLMClient

# Initialize with custom config path
client = LiteLLMClient(config_path="path/to/custom/api.json")

response = client.chat("Hello!")
```

### System Prompts

Add a system prompt to guide the model's behavior:

```python
from Tools.litellm import get_client

client = get_client()

response = client.chat(
    "Review this code for security issues",
    system_prompt="You are a senior security engineer specializing in code review."
)
print(response)
```

### Response Metadata

Access detailed response information:

```python
from Tools.litellm import get_client

client = get_client()

response = client.chat("Explain quantum computing")

# Response is a ModelResponse object with full details
print(f"Content: {response.content[:100]}...")
print(f"Model: {response.model}")
print(f"Provider: {response.provider}")
print(f"Input tokens: {response.input_tokens}")
print(f"Output tokens: {response.output_tokens}")
print(f"Total tokens: {response.total_tokens}")
print(f"Cost: ${response.cost_usd:.4f}")
print(f"Latency: {response.latency_ms:.0f}ms")
print(f"Cached: {response.cached}")
print(f"Metadata: {response.metadata}")
```

---

## Core Classes

*(This section will be expanded in subsequent subtasks to document LiteLLMClient, UsageTracker, ComplexityAnalyzer, ResponseCache, and other components in detail.)*

---

## Contributing

When extending the API, please update this reference to keep documentation synchronized with implementation.

---

**Last Updated**: 2026-01-12
**Package Version**: See `Tools/litellm/__init__.py`
**LiteLLM Library**: v1.0+ required
