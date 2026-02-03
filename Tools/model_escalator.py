"""
ModelEscalator - Dynamic model switching based on conversation complexity.

Integrates with OpenClaw via session_status to automatically escalate
to more capable models when conversation complexity increases.

Usage:
    from Tools.model_escalator import ModelEscalator, model_escalation_hook
    
    # In message handling:
    recommended_model = model_escalation_hook(session_key, {
        'messages': conversation_history,
        'current_message': user_message,
        'token_count': total_tokens
    })
"""

import os
import json
import sqlite3
import time
import importlib.util
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass

@dataclass
class EscalationResult:
    """Result of model escalation check."""
    model: str
    escalated: bool
    reason: str
    complexity_score: float

class ModelEscalator:
    def __init__(self, config_path: str = None):
        """
        Initialize the ModelEscalator with configuration and state tracking
        """
        # Default configuration
        self.default_config = {
            "initial_model": "anthropic/claude-3-5-haiku-20241022",
            "escalation_models": [
                "anthropic/claude-sonnet-4-5",
                "anthropic/claude-opus-4-5"
            ],
            "complexity_thresholds": {
                "low": 0.3,
                "medium": 0.6,
                "high": 0.9
            },
            "hysteresis_cooldown": 300  # 5 minutes between model switches
        }
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize state tracking database
        self._init_state_db()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from file or use defaults
        """
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    return {**self.default_config, **user_config}
            except (json.JSONDecodeError, IOError):
                print(f"Warning: Could not load config from {config_path}. Using defaults.")
        
        return self.default_config
    
    def _init_state_db(self):
        """
        Initialize SQLite database for tracking model state
        """
        db_path = os.path.expanduser("~/Projects/Thanos/model_escalator_state.db")
        self.conn = sqlite3.connect(db_path)
        cursor = self.conn.cursor()
        
        # Create tables for tracking conversation state and model switches
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_state (
                conversation_id TEXT PRIMARY KEY,
                current_model TEXT,
                complexity_score REAL,
                last_model_switch_time REAL,
                total_complexity_score REAL,
                turn_count INTEGER
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS model_switch_log (
                timestamp REAL,
                conversation_id TEXT,
                from_model TEXT,
                to_model TEXT,
                complexity_score REAL
            )
        ''')
        
        self.conn.commit()
    
    def analyze_complexity(self, conversation_context: Dict[str, Any]) -> float:
        """
        Analyze conversation complexity.
        Uses built-in multi-factor analysis.
        """
        return self._simple_complexity_estimate(conversation_context)
    
    def _simple_complexity_estimate(self, conversation_context: Dict[str, Any]) -> float:
        """
        Multi-factor complexity estimation.
        """
        complexity = 0.0
        current_msg = conversation_context.get('current_message', '')
        messages = conversation_context.get('messages', [])
        token_count = conversation_context.get('token_count', 0)
        
        # Factor 1: Message length (0-0.2)
        msg_len = len(current_msg)
        if msg_len > 2000:
            complexity += 0.2
        elif msg_len > 1000:
            complexity += 0.15
        elif msg_len > 500:
            complexity += 0.1
        
        # Factor 2: Technical keywords (0-0.3)
        technical_keywords = {
            'high': ['algorithm', 'architecture', 'implement', 'optimize', 'refactor',
                     'debug', 'analyze', 'design pattern', 'system design', 'complexity'],
            'medium': ['code', 'function', 'class', 'api', 'database', 'query',
                       'logic', 'structure', 'framework', 'integration'],
            'low': ['explain', 'help', 'what is', 'how to', 'example']
        }
        
        msg_lower = current_msg.lower()
        for kw in technical_keywords['high']:
            if kw in msg_lower:
                complexity += 0.1
        for kw in technical_keywords['medium']:
            if kw in msg_lower:
                complexity += 0.05
        complexity = min(complexity, 0.5)  # Cap keyword contribution
        
        # Factor 3: Conversation depth (0-0.2)
        if len(messages) > 20:
            complexity += 0.2
        elif len(messages) > 10:
            complexity += 0.15
        elif len(messages) > 5:
            complexity += 0.1
        
        # Factor 4: Token usage (0-0.2)
        if token_count > 50000:
            complexity += 0.2
        elif token_count > 20000:
            complexity += 0.15
        elif token_count > 10000:
            complexity += 0.1
        
        # Factor 5: Multi-step indicators (0-0.1)
        multi_step_indicators = ['step 1', 'first,', 'then,', 'finally,', 'breakdown',
                                  'in detail', 'comprehensive', 'thorough']
        for indicator in multi_step_indicators:
            if indicator in msg_lower:
                complexity += 0.05
                break
        
        # Clamp complexity between 0 and 1
        return min(max(complexity, 0.0), 1.0)
    
    def determine_model(self, conversation_id: str, conversation_context: Dict[str, Any]) -> EscalationResult:
        """
        Determine the appropriate model based on conversation complexity
        """
        # Analyze complexity
        complexity_score = self.analyze_complexity(conversation_context)
        
        # Get current conversation state
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_model, last_model_switch_time, turn_count 
            FROM conversation_state 
            WHERE conversation_id = ?
        ''', (conversation_id,))
        
        result = cursor.fetchone()
        current_time = time.time()
        
        # Default to initial model if no state exists
        if not result:
            current_model = self.config['initial_model']
            cursor.execute('''
                INSERT INTO conversation_state 
                (conversation_id, current_model, complexity_score, last_model_switch_time, total_complexity_score, turn_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conversation_id, current_model, complexity_score, current_time, complexity_score, 1))
            self.conn.commit()
            return EscalationResult(
                model=current_model,
                escalated=False,
                reason="New conversation initialized",
                complexity_score=complexity_score
            )
        
        current_model, last_switch_time, turn_count = result
        
        # Check hysteresis (cooldown between model switches)
        if current_time - last_switch_time < self.config['hysteresis_cooldown']:
            return EscalationResult(
                model=current_model,
                escalated=False,
                reason="Cooldown period active",
                complexity_score=complexity_score
            )
        
        # Determine model based on complexity thresholds
        target_model = current_model
        if complexity_score > self.config['complexity_thresholds']['high']:
            # Escalate to most powerful model
            target_model = self.config['escalation_models'][-1]
        elif complexity_score > self.config['complexity_thresholds']['medium']:
            # Escalate to intermediate model
            target_model = self.config['escalation_models'][0]
        
        # Check for de-escalation if complexity is low
        if complexity_score < self.config['complexity_thresholds']['low']:
            # De-escalate to initial model if we're on a higher model
            if current_model != self.config['initial_model']:
                target_model = self.config['initial_model']
        
        # Update state if model changes
        if target_model != current_model:
            # Log model switch
            cursor.execute('''
                INSERT INTO model_switch_log 
                (timestamp, conversation_id, from_model, to_model, complexity_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_time, conversation_id, current_model, target_model, complexity_score))
            
            # Update conversation state
            cursor.execute('''
                UPDATE conversation_state 
                SET current_model = ?, 
                    complexity_score = ?, 
                    last_model_switch_time = ?,
                    total_complexity_score = total_complexity_score + ?,
                    turn_count = turn_count + 1
                WHERE conversation_id = ?
            ''', (target_model, complexity_score, current_time, complexity_score, conversation_id))
            
            self.conn.commit()
            
            # Return escalation result - caller handles the actual switch
            return EscalationResult(
                model=target_model,
                escalated=True,
                reason=f"Complexity {complexity_score:.2f} triggered {'escalation' if target_model != self.config['initial_model'] else 'de-escalation'}",
                complexity_score=complexity_score
            )
        
        # Update complexity for existing conversation
        cursor.execute('''
            UPDATE conversation_state 
            SET complexity_score = ?, 
                total_complexity_score = total_complexity_score + ?,
                turn_count = turn_count + 1
            WHERE conversation_id = ?
        ''', (complexity_score, complexity_score, conversation_id))
        self.conn.commit()
        
        return EscalationResult(
            model=current_model,
            escalated=False,
            reason="No escalation needed",
            complexity_score=complexity_score
        )

    def get_model_stats(self, conversation_id: str) -> Dict[str, Any]:
        """Get statistics for a conversation's model usage."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_model, complexity_score, total_complexity_score, turn_count
            FROM conversation_state WHERE conversation_id = ?
        ''', (conversation_id,))
        result = cursor.fetchone()
        
        if result:
            return {
                'current_model': result[0],
                'current_complexity': result[1],
                'avg_complexity': result[2] / result[3] if result[3] > 0 else 0,
                'turn_count': result[3]
            }
        return {}

    def get_switch_history(self, conversation_id: str, limit: int = 10) -> List[Dict]:
        """Get model switch history for a conversation."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT timestamp, from_model, to_model, complexity_score
            FROM model_switch_log 
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (conversation_id, limit))
        
        return [
            {
                'timestamp': row[0],
                'from_model': row[1],
                'to_model': row[2],
                'complexity': row[3]
            }
            for row in cursor.fetchall()
        ]

    def close(self):
        """Close database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()


# Singleton instance for reuse
_escalator_instance: Optional[ModelEscalator] = None

def get_escalator() -> ModelEscalator:
    """Get or create the ModelEscalator singleton."""
    global _escalator_instance
    if _escalator_instance is None:
        config_path = Path(__file__).parent.parent / "config" / "model_escalator.json"
        _escalator_instance = ModelEscalator(str(config_path) if config_path.exists() else None)
    return _escalator_instance


def model_escalation_hook(conversation_id: str, conversation_context: Dict[str, Any]) -> EscalationResult:
    """
    Hook for model escalation - call this before each response.
    
    Args:
        conversation_id: Unique identifier for the conversation (e.g., session key)
        conversation_context: Dict with:
            - messages: List of conversation messages
            - current_message: The current user message
            - token_count: Total tokens used (optional)
    
    Returns:
        EscalationResult with recommended model and escalation status
    
    Usage in thanos_orchestrator.py:
        result = model_escalation_hook(session_key, {
            'messages': history,
            'current_message': user_input,
            'token_count': total_tokens
        })
        
        if result.escalated:
            # Use OpenClaw's session_status to switch
            # This happens automatically if integrated with gateway
            logger.info(f"Model escalated to {result.model}: {result.reason}")
    """
    escalator = get_escalator()
    return escalator.determine_model(conversation_id, conversation_context)