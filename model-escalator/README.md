# OpenClaw ModelEscalator

## Overview

The ModelEscalator is a sophisticated gateway middleware designed for intelligent, adaptive model switching within the OpenClaw ecosystem. It provides dynamic model selection based on conversation complexity, domain-specific analysis, and runtime constraints.

## Key Features

1. **Intelligent Model Switching**
   - Dynamic escalation and de-escalation based on conversation complexity
   - Domain-specific complexity scoring (Code, Prose, Technical)
   - Runtime model availability checking

2. **Cost and Performance Optimization**
   - Configurable budget constraints
   - Telemetry and cost tracking
   - Performance-aware model selection

3. **Session State Preservation**
   - Maintains conversation context during model transitions
   - Seamless switching between models

## Configuration

The ModelEscalator is configured via `openclaw.yaml`. Key configuration sections:

- `complexity_thresholds`: Define domain-specific complexity levels
- `model_hierarchy`: Specify model progression
- `domain_weights`: Adjust complexity scoring by domain
- `budget`: Set cost limits and strategies
- `telemetry`: Configure logging and monitoring

## Complexity Detection

The complexity analysis uses a predictive algorithm that considers:
- Token count
- Domain-specific keyword presence
- Conversation trajectory

### Domains
- **Code**: Programming-related conversations
- **Prose**: Natural language, writing, communication
- **Technical**: Complex, specialized discussions

## Model Availability

Implements a fallback mechanism that:
- Checks model availability in real-time
- Gracefully degrades to alternative models
- Prevents session interruption

## Budget Enforcement

- Per-session cost tracking
- Soft and hard budget limits
- Automatic model downgrade to manage costs

## Integration

1. Gateway-level middleware
2. Session-initialization model selection
3. Continuous runtime adaptation

## Performance Considerations

- Minimal overhead
- Efficient complexity scoring
- Configurable telemetry

## Testing

Comprehensive test suite covering:
- Complexity analysis
- Model escalation/de-escalation
- Cost tracking
- Configuration validation

## Usage

```python
escalator = ModelEscalator('/path/to/openclaw.yaml')
recommended_model = escalator.determine_model(conversation, current_model, domain)
```

## Future Roadmap
- Machine learning-enhanced complexity prediction
- More granular domain classifications
- Enhanced telemetry and reporting

## License
[Your License Here]