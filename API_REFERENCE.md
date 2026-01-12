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

### LiteLLMClient

The main client class for unified multi-model API access. This class orchestrates API calls across 100+ model providers with intelligent features including automatic model routing, response caching, usage tracking, and fallback handling.

#### Class Description

`LiteLLMClient` is the central component of the LiteLLM package. It integrates several specialized components (ComplexityAnalyzer, ResponseCache, UsageTracker) to provide a production-ready API client with advanced features for cost optimization and reliability.

**Key Capabilities:**
- Automatic model selection based on prompt complexity analysis
- Response caching with TTL to reduce redundant API calls
- Comprehensive usage and cost tracking
- Configurable fallback chains for reliability
- Both streaming and non-streaming response modes
- Support for conversation history and system prompts

**Architecture:**
The client coordinates several components in the request flow:
1. **ComplexityAnalyzer**: Analyzes prompts to determine optimal model tier (simple/standard/complex)
2. **ResponseCache**: Checks for cached responses to avoid redundant API calls
3. **LiteLLM Library**: Makes the actual API calls to various providers
4. **UsageTracker**: Records token usage and costs for all API calls
5. **Fallback Chain**: Automatically retries with alternative models if the primary fails

#### Constructor

```python
LiteLLMClient(config_path: str = None)
```

Creates a new LiteLLMClient instance with the specified configuration.

**Parameters:**
- `config_path` (str, optional): Path to the configuration JSON file. If `None`, defaults to `config/api.json` in the project root. The path can be relative or absolute.

**Configuration File Structure:**
```json
{
  "litellm": {
    "default_model": "claude-opus-4-5-20251101",
    "fallback_chain": ["claude-opus-4-5-20251101", "claude-sonnet-4-20250514"],
    "timeout": 600,
    "max_retries": 3,
    "retry_delay": 1.0
  },
  "model_routing": {
    "rules": {
      "complex": {"model": "claude-opus-4-5-20251101", "min_complexity": 0.7},
      "standard": {"model": "claude-sonnet-4-20250514", "min_complexity": 0.3},
      "simple": {"model": "claude-3-5-haiku-20241022", "max_complexity": 0.3}
    }
  },
  "usage_tracking": {
    "enabled": true,
    "storage_path": "State/usage.json"
  },
  "caching": {
    "enabled": true,
    "ttl_seconds": 3600,
    "storage_path": "Memory/cache/",
    "max_cache_size_mb": 100
  },
  "defaults": {
    "max_tokens": 4096,
    "temperature": 1.0
  }
}
```

**Returns:**
- A configured `LiteLLMClient` instance ready to make API calls

**Raises:**
- `RuntimeError`: If neither litellm nor anthropic libraries are installed
- `FileNotFoundError`: If config_path is specified but doesn't exist (uses defaults if None)

**Example:**
```python
from Tools.litellm import LiteLLMClient

# Use default config path (config/api.json)
client = LiteLLMClient()

# Use custom config path
client = LiteLLMClient(config_path="path/to/custom/config.json")
```

---

#### Methods

##### `chat()`

```python
chat(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    system_prompt: Optional[str] = None,
    history: Optional[List[Dict]] = None,
    use_cache: bool = True,
    operation: str = "chat",
    metadata: Optional[Dict] = None
) -> str
```

Send a chat message and receive a complete response with intelligent model routing and caching.

**Parameters:**

- `prompt` (str, **required**): The user message/question to send to the model. This is the main input text.

- `model` (str, optional): Model name override to force a specific model. If `None`, the client automatically selects the most cost-effective model based on prompt complexity analysis. Examples: `"claude-opus-4-5-20251101"`, `"claude-sonnet-4-20250514"`, `"claude-3-5-haiku-20241022"`, `"gpt-4"`, `"gpt-3.5-turbo"`.

- `max_tokens` (int, optional): Maximum number of tokens in the response. If `None`, uses the value from config defaults (typically 4096). Higher values allow longer responses but increase cost.

- `temperature` (float, optional): Controls randomness in responses (0.0 to 2.0). Lower values (0.0-0.3) produce more focused, deterministic outputs. Higher values (0.7-1.0) produce more creative, varied outputs. If `None`, uses config default (typically 1.0).

- `system_prompt` (str, optional): System-level instructions that guide the model's behavior and persona. This sets the context for how the model should respond. Example: `"You are a helpful coding assistant."` or `"You are a senior security engineer."`

- `history` (List[Dict], optional): Previous conversation messages for multi-turn conversations. Each dict should have `"role"` (either `"user"` or `"assistant"`) and `"content"` (the message text). This maintains context across multiple exchanges. Example: `[{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi there!"}]`

- `use_cache` (bool, optional): Whether to use response caching. When `True` (default), identical prompts return cached responses instantly (if not expired). When `False`, always makes a fresh API call. Cache helps reduce costs and latency for repeated queries.

- `operation` (str, optional): Operation name for usage tracking and analytics. Default is `"chat"`. Use descriptive names like `"code_review"`, `"translation"`, `"summarization"` to categorize API usage in reports.

- `metadata` (Dict, optional): Additional metadata to store with usage tracking. Can include any custom fields like `{"user_id": "123", "session_id": "abc", "feature": "autocomplete"}`. Useful for detailed analytics and debugging.

**Returns:**
- `str`: The model's response text content. This is a simple string containing the complete response.

**Raises:**
- `Exception`: If all models in the fallback chain fail
- `RuntimeError`: If no API client is available (missing dependencies)

**Example - Basic Usage:**
```python
from Tools.litellm import get_client

client = get_client()

# Simple question with auto-routing
response = client.chat("What is the capital of France?")
print(response)  # Output: "Paris"
```

**Example - Force Specific Model:**
```python
from Tools.litellm import get_client

client = get_client()

# Force Claude Opus for a complex task
response = client.chat(
    "Analyze the trade-offs between microservices and monolithic architecture",
    model="claude-opus-4-5-20251101",
    max_tokens=2048,
    temperature=0.7
)
print(f"Model: {response.model}")
```

**Example - With System Prompt:**
```python
from Tools.litellm import get_client

client = get_client()

response = client.chat(
    "Review this code for security vulnerabilities",
    system_prompt="You are a senior security engineer with expertise in code review and vulnerability assessment."
)
print(response)
```

**Example - Conversation History:**
```python
from Tools.litellm import get_client

client = get_client()

# First exchange
history = []
response1 = client.chat("What is Python?")
history.append({"role": "user", "content": "What is Python?"})
history.append({"role": "assistant", "content": response1})

# Continue conversation with context
response2 = client.chat("What are its main features?", history=history)
print(response2)  # Model knows we're still talking about Python
```

**Example - Disable Caching:**
```python
from Tools.litellm import get_client

client = get_client()

# Always get fresh response (useful for time-sensitive queries)
response = client.chat(
    "What's the current date and time?",
    use_cache=False
)
print(response)
```

**Example - With Metadata for Tracking:**
```python
from Tools.litellm import get_client

client = get_client()

response = client.chat(
    "Explain quantum computing",
    operation="knowledge_base_query",
    metadata={
        "user_id": "user_12345",
        "session_id": "sess_abc123",
        "category": "science",
        "priority": "high"
    }
)
```

---

##### `chat_stream()`

```python
chat_stream(
    prompt: str,
    model: Optional[str] = None,
    max_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
    system_prompt: Optional[str] = None,
    history: Optional[List[Dict]] = None,
    operation: str = "chat_stream",
    metadata: Optional[Dict] = None
) -> Generator[str, None, None]
```

Stream a chat response token-by-token for real-time output. This is ideal for long-form content where you want to display the response as it's generated rather than waiting for the complete response.

**Parameters:**

- `prompt` (str, **required**): The user message/question to send to the model.

- `model` (str, optional): Model name override to force a specific model. If `None`, auto-routes based on complexity.

- `max_tokens` (int, optional): Maximum number of tokens in the response. If `None`, uses config default.

- `temperature` (float, optional): Controls randomness (0.0 to 2.0). If `None`, uses config default.

- `system_prompt` (str, optional): System-level instructions to guide model behavior.

- `history` (List[Dict], optional): Previous conversation messages for context. Same format as `chat()`.

- `operation` (str, optional): Operation name for usage tracking. Default is `"chat_stream"`.

- `metadata` (Dict, optional): Additional metadata for usage tracking and analytics.

**Note:** Unlike `chat()`, this method does **NOT** have a `use_cache` parameter because streaming responses cannot be cached effectively.

**Yields:**
- `str`: Response text chunks as they arrive from the API. Each chunk is a small piece of the complete response (typically a few words or characters).

**Returns:**
- `Generator[str, None, None]`: A generator that yields text chunks. Iterate over it to receive the streaming response.

**Raises:**
- `Exception`: If all models in the fallback chain fail
- `RuntimeError`: If no API client is available

**Usage Pattern:**
The typical pattern is to iterate over the generator and print/display each chunk immediately.

**Example - Basic Streaming:**
```python
from Tools.litellm import get_client

client = get_client()

print("Assistant: ", end="", flush=True)
for chunk in client.chat_stream("Tell me a short story about a robot"):
    print(chunk, end="", flush=True)
print()  # Newline at end
```

**Example - Stream with Model Override:**
```python
from Tools.litellm import get_client

client = get_client()

# Force GPT-4 and stream the response
print("Response: ", end="", flush=True)
for chunk in client.chat_stream(
    "Explain the theory of relativity",
    model="gpt-4",
    max_tokens=1000,
    temperature=0.7
):
    print(chunk, end="", flush=True)
print()
```

**Example - Collect Stream into Full Response:**
```python
from Tools.litellm import get_client

client = get_client()

# Collect all chunks into a complete response
chunks = []
for chunk in client.chat_stream("What are the benefits of meditation?"):
    chunks.append(chunk)
    print(chunk, end="", flush=True)  # Still display in real-time

full_response = "".join(chunks)
print(f"\n\nComplete response length: {len(full_response)} characters")
```

**Example - Stream with Conversation History:**
```python
from Tools.litellm import get_client

client = get_client()

history = [
    {"role": "user", "content": "I'm learning Python"},
    {"role": "assistant", "content": "That's great! Python is a versatile language."}
]

print("Assistant: ", end="", flush=True)
for chunk in client.chat_stream(
    "Can you recommend some beginner projects?",
    history=history,
    system_prompt="You are a patient programming tutor."
):
    print(chunk, end="", flush=True)
print()
```

**Example - Stream with Metadata Tracking:**
```python
from Tools.litellm import get_client

client = get_client()

for chunk in client.chat_stream(
    "Generate a product description for noise-canceling headphones",
    operation="content_generation",
    metadata={
        "user_id": "writer_456",
        "content_type": "product_description",
        "category": "electronics"
    }
):
    print(chunk, end="", flush=True)
```

**Performance Notes:**
- First token typically arrives in 200-500ms
- Subsequent tokens stream continuously
- Usage tracking records the complete request after streaming finishes
- Token counts in streaming mode are estimated (less precise than non-streaming)

---

##### `get_usage_summary()`

```python
get_usage_summary(days: int = 30) -> Dict
```

Retrieve comprehensive usage statistics and cost analysis for a specified time period.

**Parameters:**

- `days` (int, optional): Number of days to include in the summary. Default is 30 days. Use `7` for weekly, `1` for today only, `365` for yearly, etc.

**Returns:**
- `Dict`: A dictionary containing detailed usage statistics with the following keys:
  - `total_calls` (int): Total number of API calls made
  - `total_input_tokens` (int): Total input/prompt tokens consumed
  - `total_output_tokens` (int): Total output/completion tokens generated
  - `total_tokens` (int): Sum of input and output tokens
  - `total_cost_usd` (float): Total cost in USD
  - `avg_cost_per_call` (float): Average cost per API call
  - `avg_tokens_per_call` (float): Average tokens per call
  - `projected_monthly_cost` (float): Estimated monthly cost based on current usage rate
  - `by_model` (Dict): Breakdown of usage per model
  - `by_operation` (Dict): Breakdown of usage per operation type
  - `by_day` (List[Dict]): Daily usage breakdown

Returns empty dict `{}` if usage tracking is disabled.

**Example - 30-Day Summary:**
```python
from Tools.litellm import get_client

client = get_client()

summary = client.get_usage_summary(days=30)

print(f"30-Day Usage Summary:")
print(f"  Total calls: {summary['total_calls']}")
print(f"  Total cost: ${summary['total_cost_usd']:.2f}")
print(f"  Projected monthly: ${summary['projected_monthly_cost']:.2f}")
print(f"  Average per call: ${summary['avg_cost_per_call']:.4f}")
print(f"  Total tokens: {summary['total_tokens']:,}")
```

**Example - Weekly Summary:**
```python
from Tools.litellm import get_client

client = get_client()

# Get last 7 days
weekly = client.get_usage_summary(days=7)

print(f"Weekly Summary:")
print(f"  Calls: {weekly['total_calls']}")
print(f"  Cost: ${weekly['total_cost_usd']:.2f}")

# Show breakdown by model
print("\nUsage by Model:")
for model, stats in weekly.get('by_model', {}).items():
    print(f"  {model}: {stats['calls']} calls, ${stats['cost']:.4f}")
```

**Example - Yearly Analysis:**
```python
from Tools.litellm import get_client

client = get_client()

yearly = client.get_usage_summary(days=365)

print(f"Yearly Analysis:")
print(f"  Total cost: ${yearly['total_cost_usd']:.2f}")
print(f"  Average monthly: ${yearly['total_cost_usd'] / 12:.2f}")
print(f"  Total API calls: {yearly['total_calls']:,}")
```

---

##### `get_today_usage()`

```python
get_today_usage() -> Dict
```

Get usage statistics for the current day only. This is a convenience method equivalent to `get_usage_summary(days=1)` but returns a simplified format.

**Parameters:**
- None

**Returns:**
- `Dict`: A dictionary with today's usage:
  - `tokens` (int): Total tokens used today (input + output)
  - `cost` (float): Total cost in USD for today
  - `calls` (int): Number of API calls made today

Returns `{"tokens": 0, "cost": 0.0, "calls": 0}` if usage tracking is disabled or no calls were made today.

**Example - Check Today's Usage:**
```python
from Tools.litellm import get_client

client = get_client()

today = client.get_today_usage()

print(f"Today's Usage:")
print(f"  Calls: {today['calls']}")
print(f"  Tokens: {today['tokens']:,}")
print(f"  Cost: ${today['cost']:.4f}")
```

**Example - Monitor Daily Budget:**
```python
from Tools.litellm import get_client

client = get_client()

DAILY_BUDGET = 5.00  # $5 per day limit

today = client.get_today_usage()

if today['cost'] > DAILY_BUDGET:
    print(f"⚠️ Warning: Daily budget exceeded!")
    print(f"Budget: ${DAILY_BUDGET:.2f}, Spent: ${today['cost']:.2f}")
else:
    remaining = DAILY_BUDGET - today['cost']
    print(f"✓ Budget OK: ${remaining:.2f} remaining today")
```

**Example - Real-time Cost Tracking:**
```python
from Tools.litellm import get_client

client = get_client()

# Make several API calls
client.chat("Hello")
client.chat("What's the weather?")
client.chat("Tell me a joke")

# Check accumulated cost
today = client.get_today_usage()
print(f"Total cost after 3 calls: ${today['cost']:.4f}")
```

---

##### `analyze_complexity()`

```python
analyze_complexity(
    prompt: str,
    history: Optional[List[Dict]] = None
) -> Dict
```

Analyze prompt complexity and determine which model would be selected for routing, without making an actual API call. This is useful for understanding routing decisions and estimating costs before execution.

**Parameters:**

- `prompt` (str, **required**): The user message to analyze for complexity.

- `history` (List[Dict], optional): Previous conversation messages for context. The complexity analyzer considers conversation history when determining complexity.

**Returns:**
- `Dict`: A dictionary containing complexity analysis results:
  - `complexity_score` (float): Numerical complexity score (0.0 to 1.0). Higher values indicate more complex prompts.
  - `tier` (str): Complexity tier classification - one of `"simple"`, `"standard"`, or `"complex"`.
  - `selected_model` (str): The model that would be selected based on routing rules (e.g., `"claude-3-5-haiku-20241022"` for simple, `"claude-sonnet-4-20250514"` for standard, `"claude-opus-4-5-20251101"` for complex).
  - `routing_rules` (Dict): The complete routing rules configuration showing complexity thresholds for each tier.

**Complexity Tiers:**
- **Simple** (score < 0.3): Short, straightforward queries → Routed to Haiku (cheapest)
- **Standard** (0.3 ≤ score < 0.7): Medium complexity tasks → Routed to Sonnet (balanced)
- **Complex** (score ≥ 0.7): Advanced reasoning, long contexts → Routed to Opus (most capable)

**Example - Basic Complexity Analysis:**
```python
from Tools.litellm import get_client

client = get_client()

# Analyze a simple query
simple = client.analyze_complexity("Hi there!")
print(f"Complexity: {simple['complexity_score']:.2f}")  # ~0.1
print(f"Tier: {simple['tier']}")  # 'simple'
print(f"Model: {simple['selected_model']}")  # 'claude-3-5-haiku-20241022'

# Analyze a complex query
complex = client.analyze_complexity("""
Explain the differences between supervised, unsupervised, and reinforcement
learning in machine learning, including specific algorithms and use cases.
""")
print(f"Complexity: {complex['complexity_score']:.2f}")  # ~0.8
print(f"Tier: {complex['tier']}")  # 'complex'
print(f"Model: {complex['selected_model']}")  # 'claude-opus-4-5-20251101'
```

**Example - Compare Prompts:**
```python
from Tools.litellm import get_client

client = get_client()

prompts = [
    "Hello",
    "What is Python?",
    "Analyze the architectural trade-offs between event-driven and request-response patterns"
]

for prompt in prompts:
    analysis = client.analyze_complexity(prompt)
    print(f"Prompt: {prompt[:50]}...")
    print(f"  Score: {analysis['complexity_score']:.2f}")
    print(f"  Tier: {analysis['tier']}")
    print(f"  Model: {analysis['selected_model']}")
    print()
```

**Example - With Conversation History:**
```python
from Tools.litellm import get_client

client = get_client()

history = [
    {"role": "user", "content": "I need help with a complex architecture decision"},
    {"role": "assistant", "content": "I'd be happy to help with architecture."}
]

# History context increases complexity score
analysis = client.analyze_complexity(
    "What should I do?",  # Simple by itself
    history=history  # But complex with context
)

print(f"Complexity with history: {analysis['complexity_score']:.2f}")
print(f"Tier: {analysis['tier']}")
```

**Example - Cost Estimation Before Execution:**
```python
from Tools.litellm import get_client

client = get_client()

prompt = "Explain quantum computing in detail"

analysis = client.analyze_complexity(prompt)
print(f"Analysis Results:")
print(f"  Complexity: {analysis['complexity_score']:.2f} ({analysis['tier']})")
print(f"  Would use model: {analysis['selected_model']}")

# Now decide whether to proceed
if analysis['tier'] == 'complex':
    print("Warning: This will use the expensive Opus model")
    # User can decide to simplify prompt or proceed

# Proceed with the call
response = client.chat(prompt)
```

---

##### `list_available_models()`

```python
list_available_models() -> List[str]
```

List all models configured in the client's configuration file. This shows which models are available for use.

**Parameters:**
- None

**Returns:**
- `List[str]`: A list of model names (strings) that are configured and available. Examples: `["claude-opus-4-5-20251101", "claude-sonnet-4-20250514", "gpt-4", "gpt-3.5-turbo"]`

**Example:**
```python
from Tools.litellm import get_client

client = get_client()

models = client.list_available_models()
print(f"Available models ({len(models)}):")
for model in models:
    print(f"  - {model}")
```

**Example - Check if Model is Available:**
```python
from Tools.litellm import get_client

client = get_client()

desired_model = "claude-opus-4-5-20251101"
available = client.list_available_models()

if desired_model in available:
    print(f"✓ {desired_model} is available")
    response = client.chat("Hello", model=desired_model)
else:
    print(f"✗ {desired_model} is not configured")
```

---

#### Advanced Usage Examples

**Example - Complete Workflow with All Features:**
```python
from Tools.litellm import get_client

client = get_client()

# 1. Check available models
models = client.list_available_models()
print(f"Available models: {len(models)}")

# 2. Analyze complexity before making call
prompt = "Design a scalable microservices architecture"
analysis = client.analyze_complexity(prompt)
print(f"Complexity: {analysis['complexity_score']:.2f} ({analysis['tier']})")
print(f"Will use: {analysis['selected_model']}")

# 3. Make the call with full configuration
response = client.chat(
    prompt=prompt,
    max_tokens=2048,
    temperature=0.7,
    system_prompt="You are a senior software architect",
    operation="architecture_consultation",
    metadata={
        "user_id": "architect_001",
        "project": "ecommerce_platform",
        "phase": "design"
    }
)

print(f"Response: {response[:200]}...")

# 4. Check usage
today = client.get_today_usage()
print(f"Today: {today['calls']} calls, ${today['cost']:.4f}")

summary = client.get_usage_summary(days=7)
print(f"Weekly: ${summary['total_cost_usd']:.2f}")
```

**Example - Multi-turn Conversation with Streaming:**
```python
from Tools.litellm import get_client

client = get_client()

history = []

def chat_turn(user_message):
    """Handle a single conversation turn with streaming."""
    history.append({"role": "user", "content": user_message})

    print("User:", user_message)
    print("Assistant: ", end="", flush=True)

    chunks = []
    for chunk in client.chat_stream(
        prompt=user_message,
        history=history[:-1],  # Exclude current message
        system_prompt="You are a helpful assistant"
    ):
        print(chunk, end="", flush=True)
        chunks.append(chunk)

    assistant_message = "".join(chunks)
    history.append({"role": "assistant", "content": assistant_message})
    print("\n")

# Conduct multi-turn conversation
chat_turn("What is machine learning?")
chat_turn("Can you give me an example?")
chat_turn("How do I get started?")

# Review usage
today = client.get_today_usage()
print(f"Conversation cost: ${today['cost']:.4f}")
```

---

#### Error Handling

The `LiteLLMClient` automatically handles several error scenarios:

**Fallback Chain**: If the primary model fails (rate limit, timeout, error), the client automatically tries the next model in the configured fallback chain.

**Retry Logic**: API connection errors trigger automatic retries with exponential backoff (configured via `max_retries` and `retry_delay`).

**Common Exceptions**:
- `RuntimeError`: Raised if no API client libraries are installed
- `Exception`: Raised if all models in fallback chain fail

**Example - Graceful Error Handling:**
```python
from Tools.litellm import get_client

client = get_client()

try:
    response = client.chat("Hello, world!")
    print(response)
except RuntimeError as e:
    print(f"Configuration error: {e}")
    print("Please install litellm or anthropic package")
except Exception as e:
    print(f"API error: {e}")
    print("All models in fallback chain failed")
```

---

#### Performance Characteristics

- **Cache hits**: <1ms (instant response from cache)
- **API calls**: 500-3000ms (varies by model and prompt complexity)
- **Streaming**: First token in ~200-500ms, then continuous stream
- **Complexity analysis**: <10ms overhead per request

---

#### Configuration Best Practices

1. **Set appropriate fallback chains**: Include multiple models of similar capability
2. **Enable caching**: Reduces costs for repeated queries
3. **Configure routing rules**: Adjust complexity thresholds based on your use case
4. **Set reasonable defaults**: Choose balanced `max_tokens` and `temperature` values
5. **Enable usage tracking**: Monitor costs and optimize over time

---

*(This section will be expanded in subsequent subtasks to document UsageTracker, ComplexityAnalyzer, ResponseCache, and other components in detail.)*

---

## Contributing

When extending the API, please update this reference to keep documentation synchronized with implementation.

---

**Last Updated**: 2026-01-12
**Package Version**: See `Tools/litellm/__init__.py`
**LiteLLM Library**: v1.0+ required
