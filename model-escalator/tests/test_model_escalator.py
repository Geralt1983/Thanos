import pytest
import yaml
from src.model_escalator import ModelEscalator, Domain, ModelSession

@pytest.fixture
def model_escalator():
    """Fixture to create ModelEscalator instance for testing."""
    config_path = 'config/openclaw.yaml'
    return ModelEscalator(config_path)

def test_complexity_analysis(model_escalator):
    """Test complexity analysis for different domains."""
    test_cases = [
        # Low complexity prose
        {
            'conversation': ['Hi', 'How are you?'],
            'domain': Domain.PROSE,
            'expected_complexity_range': (0.0, 0.3)
        },
        # High complexity technical conversation
        {
            'conversation': ['Describe the architectural principles of a distributed system', 'Explain microservices design patterns'],
            'domain': Domain.TECHNICAL,
            'expected_complexity_range': (0.7, 1.0)
        },
        # Code complexity
        {
            'conversation': ['Write a recursive fibonacci implementation in Python'],
            'domain': Domain.CODE,
            'expected_complexity_range': (0.6, 0.9)
        }
    ]
    
    for case in test_cases:
        complexity = model_escalator.determine_model(
            case['conversation'], 
            'claude-3-haiku', 
            case['domain']
        )
        
        assert complexity is not None, "Model determination failed"

def test_model_escalation(model_escalator):
    """Test model escalation based on complexity."""
    # High complexity technical conversation should escalate
    high_complexity_conv = [
        'Design a complex distributed caching system',
        'Implement a multi-tier architecture with load balancing',
        'Discuss advanced concurrency patterns'
    ]
    
    escalated_model = model_escalator.determine_model(
        high_complexity_conv, 
        'claude-3-haiku', 
        Domain.TECHNICAL
    )
    
    assert escalated_model == 'claude-3-sonnet', "Failed to escalate to more capable model"

def test_session_cost_tracking(model_escalator):
    """Test session cost tracking and budget enforcement."""
    session = ModelSession(
        model_name='claude-3-haiku',
        session_id='test_session_123',
        domain=Domain.CODE
    )
    
    # Simulate multiple interactions
    interactions = [
        {'tokens': 100},
        {'tokens': 500},
        {'tokens': 1000}
    ]
    
    for interaction in interactions:
        result = model_escalator.track_session_cost(session, interaction['tokens'])
        assert result is True, f"Session terminated prematurely at {session.cost}"
    
    # Verify cost is tracked correctly
    assert session.tokens_used == 1600, "Incorrect token usage tracking"

def test_model_availability(model_escalator):
    """Test model availability fallback."""
    # Simulate unavailable model scenario
    unavailable_conv = ['Complex task that requires high-end model']
    fallback_model = model_escalator.determine_model(
        unavailable_conv, 
        'claude-3-opus',  # Assuming this is currently unavailable
        Domain.TECHNICAL
    )
    
    assert fallback_model in ['claude-3-sonnet', 'claude-3-haiku'], "Failed to provide fallback model"

def test_config_validation():
    """Validate the OpenClaw configuration schema."""
    with open('config/openclaw.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Validate key sections exist
    assert 'model_escalator' in config, "Missing model_escalator configuration"
    
    sections = [
        'complexity_thresholds',
        'model_hierarchy',
        'domain_weights',
        'budget',
        'telemetry'
    ]
    
    for section in sections:
        assert section in config['model_escalator'], f"Missing {section} in model_escalator config"

if __name__ == '__main__':
    pytest.main()