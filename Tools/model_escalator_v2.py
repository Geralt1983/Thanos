"""
ModelEscalator V2 - Enhanced dynamic model switching with ML and feedback.

New features:
- ML-ready complexity detection with feature extraction
- Comprehensive logging and metrics
- User feedback mechanism for model choice rating
- Historical pattern analysis
"""

import os
import json
import sqlite3
import time
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
import hashlib

@dataclass
class EscalationResult:
    """Result of model escalation check."""
    model: str
    escalated: bool
    reason: str
    complexity_score: float
    features: Dict[str, float]  # Feature breakdown for analysis
    
@dataclass
class FeedbackEntry:
    """User feedback on model choice."""
    timestamp: float
    conversation_id: str
    message_hash: str
    chosen_model: str
    complexity_score: float
    user_rating: int  # 1-5: 1=way too weak, 3=just right, 5=overkill
    comment: Optional[str] = None


class ComplexityAnalyzer:
    """Enhanced complexity analysis with ML-ready features."""
    
    def __init__(self):
        self.feature_weights = self._default_weights()
        
    def _default_weights(self) -> Dict[str, float]:
        """Default feature weights (can be trained)."""
        return {
            'message_length': 0.15,
            'technical_density': 0.25,
            'conversation_depth': 0.15,
            'token_usage': 0.15,
            'multi_step_indicators': 0.10,
            'code_present': 0.10,
            'question_complexity': 0.10
        }
    
    def extract_features(self, conversation_context: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract complexity features from conversation context.
        Returns normalized features (0-1) for ML consumption.
        """
        features = {}
        current_msg = conversation_context.get('current_message', '')
        messages = conversation_context.get('messages', [])
        token_count = conversation_context.get('token_count', 0)
        
        # Feature 1: Message length (normalized)
        msg_len = len(current_msg)
        features['message_length'] = min(msg_len / 2000, 1.0)
        
        # Feature 2: Technical density (keywords per 100 chars)
        technical_keywords = [
            'algorithm', 'architecture', 'implement', 'optimize', 'refactor',
            'debug', 'analyze', 'design', 'system', 'complexity', 'integrate',
            'deploy', 'scale', 'performance', 'security', 'api', 'database',
            'framework', 'infrastructure', 'distributed', 'concurrent'
        ]
        msg_lower = current_msg.lower()
        keyword_count = sum(1 for kw in technical_keywords if kw in msg_lower)
        features['technical_density'] = min(keyword_count / 5, 1.0)
        
        # Feature 3: Conversation depth
        features['conversation_depth'] = min(len(messages) / 20, 1.0)
        
        # Feature 4: Token usage
        features['token_usage'] = min(token_count / 50000, 1.0)
        
        # Feature 5: Multi-step indicators
        multi_step_indicators = [
            'step', 'first', 'then', 'next', 'finally', 'breakdown',
            'comprehensive', 'thorough', 'detailed', 'in-depth'
        ]
        multi_step_count = sum(1 for ind in multi_step_indicators if ind in msg_lower)
        features['multi_step_indicators'] = min(multi_step_count / 3, 1.0)
        
        # Feature 6: Code presence
        code_markers = ['```', 'def ', 'class ', 'function', 'import ', 'const ', 'let ']
        code_present = any(marker in current_msg for marker in code_markers)
        features['code_present'] = 1.0 if code_present else 0.0
        
        # Feature 7: Question complexity
        question_words = ['how', 'why', 'what', 'when', 'where', 'which']
        question_count = sum(1 for qw in question_words if qw in msg_lower)
        has_multiple_questions = current_msg.count('?') > 1
        features['question_complexity'] = min((question_count / 3) + (0.3 if has_multiple_questions else 0), 1.0)
        
        return features
    
    def calculate_complexity(self, features: Dict[str, float]) -> float:
        """Calculate weighted complexity score from features."""
        score = sum(
            features.get(feature, 0.0) * weight
            for feature, weight in self.feature_weights.items()
        )
        return min(max(score, 0.0), 1.0)
    
    def update_weights(self, feedback_data: List[Tuple[Dict[str, float], float]]):
        """
        Update feature weights based on feedback.
        Simple learning: adjust weights towards better predictions.
        
        Args:
            feedback_data: List of (features, target_complexity) tuples
        """
        # Simple gradient descent-like update
        learning_rate = 0.01
        
        for features, target in feedback_data:
            predicted = self.calculate_complexity(features)
            error = target - predicted
            
            # Adjust weights proportionally to feature values and error
            for feature_name in self.feature_weights:
                feature_value = features.get(feature_name, 0.0)
                self.feature_weights[feature_name] += learning_rate * error * feature_value
        
        # Normalize weights to sum to 1.0
        total_weight = sum(self.feature_weights.values())
        if total_weight > 0:
            self.feature_weights = {
                k: v / total_weight for k, v in self.feature_weights.items()
            }


class MetricsLogger:
    """Comprehensive logging and metrics tracking."""
    
    def __init__(self, log_dir: str = None):
        self.log_dir = Path(log_dir or os.path.expanduser("~/Projects/Thanos/logs"))
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup file logging
        log_file = self.log_dir / "model_escalator.log"
        self.logger = logging.getLogger('ModelEscalator')
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
    
    def log_escalation(self, conversation_id: str, result: EscalationResult, 
                       from_model: str = None):
        """Log model escalation event with full context."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'conversation_id': conversation_id,
            'from_model': from_model,
            'to_model': result.model,
            'escalated': result.escalated,
            'complexity_score': result.complexity_score,
            'reason': result.reason,
            'features': result.features
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_feedback(self, feedback: FeedbackEntry):
        """Log user feedback."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(feedback.timestamp).isoformat(),
            'conversation_id': feedback.conversation_id,
            'model': feedback.chosen_model,
            'complexity': feedback.complexity_score,
            'rating': feedback.user_rating,
            'comment': feedback.comment
        }
        self.logger.info(f"FEEDBACK: {json.dumps(log_entry)}")
    
    def get_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Aggregate metrics from logs."""
        log_file = self.log_dir / "model_escalator.log"
        
        if not log_file.exists():
            return {}
        
        metrics = {
            'total_escalations': 0,
            'total_de_escalations': 0,
            'model_usage': {},
            'avg_complexity': 0.0,
            'feedback_count': 0,
            'avg_rating': 0.0
        }
        
        complexity_sum = 0
        rating_sum = 0
        
        cutoff_time = time.time() - (days * 86400)
        
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    if 'FEEDBACK:' in line:
                        data = json.loads(line.split('FEEDBACK:')[1].strip())
                        metrics['feedback_count'] += 1
                        rating_sum += data['rating']
                    else:
                        # Parse log entry
                        parts = line.split(' - ')
                        if len(parts) >= 3:
                            json_part = ' - '.join(parts[2:])
                            data = json.loads(json_part)
                            
                            # Check if within time window
                            timestamp = datetime.fromisoformat(data['timestamp']).timestamp()
                            if timestamp < cutoff_time:
                                continue
                            
                            if data.get('escalated'):
                                if data.get('to_model') != data.get('from_model'):
                                    metrics['total_escalations'] += 1
                            
                            model = data.get('to_model', '')
                            metrics['model_usage'][model] = metrics['model_usage'].get(model, 0) + 1
                            
                            complexity_sum += data.get('complexity_score', 0)
                
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Calculate averages
        total_checks = sum(metrics['model_usage'].values())
        if total_checks > 0:
            metrics['avg_complexity'] = complexity_sum / total_checks
        
        if metrics['feedback_count'] > 0:
            metrics['avg_rating'] = rating_sum / metrics['feedback_count']
        
        return metrics


class ModelEscalatorV2:
    """Enhanced ModelEscalator with ML and feedback."""
    
    def __init__(self, config_path: str = None):
        self.default_config = {
            "initial_model": "anthropic/claude-3-5-haiku-20241022",
            "escalation_models": [
                "anthropic/claude-sonnet-4-5",
                "anthropic/claude-opus-4-5"
            ],
            "complexity_thresholds": {
                "low": 0.25,
                "medium": 0.5,
                "high": 0.75
            },
            "hysteresis_cooldown": 300
        }
        
        self.config = self._load_config(config_path)
        self.analyzer = ComplexityAnalyzer()
        self.metrics = MetricsLogger()
        self._init_state_db()
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    return {**self.default_config, **user_config}
            except (json.JSONDecodeError, IOError):
                pass
        return self.default_config
    
    def _init_state_db(self):
        db_path = os.path.expanduser("~/Projects/Thanos/model_escalator_state.db")
        self.conn = sqlite3.connect(db_path)
        cursor = self.conn.cursor()
        
        # Existing tables
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
                complexity_score REAL,
                features TEXT
            )
        ''')
        
        # New feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                conversation_id TEXT,
                message_hash TEXT,
                chosen_model TEXT,
                complexity_score REAL,
                user_rating INTEGER,
                comment TEXT,
                features TEXT
            )
        ''')
        
        self.conn.commit()
    
    def determine_model(self, conversation_id: str, 
                       conversation_context: Dict[str, Any]) -> EscalationResult:
        """Determine appropriate model with enhanced analysis."""
        
        # Extract features and calculate complexity
        features = self.analyzer.extract_features(conversation_context)
        complexity_score = self.analyzer.calculate_complexity(features)
        
        # Get current state
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT current_model, last_model_switch_time, turn_count 
            FROM conversation_state 
            WHERE conversation_id = ?
        ''', (conversation_id,))
        
        result = cursor.fetchone()
        current_time = time.time()
        
        if not result:
            current_model = self.config['initial_model']
            cursor.execute('''
                INSERT INTO conversation_state 
                (conversation_id, current_model, complexity_score, last_model_switch_time, 
                 total_complexity_score, turn_count)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (conversation_id, current_model, complexity_score, current_time, 
                  complexity_score, 1))
            self.conn.commit()
            
            escalation_result = EscalationResult(
                model=current_model,
                escalated=False,
                reason="New conversation initialized",
                complexity_score=complexity_score,
                features=features
            )
            self.metrics.log_escalation(conversation_id, escalation_result)
            return escalation_result
        
        current_model, last_switch_time, turn_count = result
        
        # Check cooldown
        if current_time - last_switch_time < self.config['hysteresis_cooldown']:
            return EscalationResult(
                model=current_model,
                escalated=False,
                reason="Cooldown period active",
                complexity_score=complexity_score,
                features=features
            )
        
        # Determine target model
        target_model = current_model
        if complexity_score > self.config['complexity_thresholds']['high']:
            target_model = self.config['escalation_models'][-1]
        elif complexity_score > self.config['complexity_thresholds']['medium']:
            target_model = self.config['escalation_models'][0]
        elif complexity_score < self.config['complexity_thresholds']['low']:
            if current_model != self.config['initial_model']:
                target_model = self.config['initial_model']
        
        # Log and update state if model changes
        if target_model != current_model:
            cursor.execute('''
                INSERT INTO model_switch_log 
                (timestamp, conversation_id, from_model, to_model, complexity_score, features)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (current_time, conversation_id, current_model, target_model, 
                  complexity_score, json.dumps(features)))
            
            cursor.execute('''
                UPDATE conversation_state 
                SET current_model = ?, complexity_score = ?, last_model_switch_time = ?,
                    total_complexity_score = total_complexity_score + ?, turn_count = turn_count + 1
                WHERE conversation_id = ?
            ''', (target_model, complexity_score, current_time, complexity_score, conversation_id))
            
            self.conn.commit()
            
            escalation_result = EscalationResult(
                model=target_model,
                escalated=True,
                reason=f"Complexity {complexity_score:.2f} triggered model change",
                complexity_score=complexity_score,
                features=features
            )
            self.metrics.log_escalation(conversation_id, escalation_result, current_model)
            return escalation_result
        
        # Update complexity for existing conversation
        cursor.execute('''
            UPDATE conversation_state 
            SET complexity_score = ?, total_complexity_score = total_complexity_score + ?,
                turn_count = turn_count + 1
            WHERE conversation_id = ?
        ''', (complexity_score, complexity_score, conversation_id))
        self.conn.commit()
        
        return EscalationResult(
            model=current_model,
            escalated=False,
            reason="No escalation needed",
            complexity_score=complexity_score,
            features=features
        )
    
    def record_feedback(self, conversation_id: str, message: str, 
                       model: str, complexity_score: float, 
                       rating: int, comment: str = None):
        """
        Record user feedback on model choice.
        
        Args:
            conversation_id: Session identifier
            message: The message that was processed
            model: Model that was chosen
            complexity_score: Calculated complexity
            rating: 1-5 (1=too weak, 3=just right, 5=overkill)
            comment: Optional comment
        """
        # Hash message for privacy
        message_hash = hashlib.sha256(message.encode()).hexdigest()[:16]
        
        feedback = FeedbackEntry(
            timestamp=time.time(),
            conversation_id=conversation_id,
            message_hash=message_hash,
            chosen_model=model,
            complexity_score=complexity_score,
            user_rating=rating,
            comment=comment
        )
        
        # Store in database
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO user_feedback 
            (timestamp, conversation_id, message_hash, chosen_model, 
             complexity_score, user_rating, comment, features)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (feedback.timestamp, feedback.conversation_id, feedback.message_hash,
              feedback.chosen_model, feedback.complexity_score, feedback.user_rating,
              feedback.comment, "{}"))  # Features can be added later
        
        self.conn.commit()
        self.metrics.log_feedback(feedback)
    
    def train_from_feedback(self, min_samples: int = 10):
        """
        Update complexity analyzer weights based on user feedback.
        
        Maps user ratings to target complexity:
        - rating 1-2: complexity should have been higher (underestimated)
        - rating 3: complexity was right
        - rating 4-5: complexity should have been lower (overestimated)
        """
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT complexity_score, user_rating, features 
            FROM user_feedback 
            ORDER BY timestamp DESC 
            LIMIT 100
        ''')
        
        feedback_data = []
        for row in cursor.fetchall():
            complexity, rating, features_json = row
            
            # Convert rating to target complexity adjustment
            if rating <= 2:
                # Model was too weak, complexity should have been higher
                target = min(complexity * 1.3, 1.0)
            elif rating >= 4:
                # Model was overkill, complexity should have been lower
                target = max(complexity * 0.7, 0.0)
            else:
                # Just right
                target = complexity
            
            try:
                features = json.loads(features_json) if features_json != "{}" else {}
                if features:
                    feedback_data.append((features, target))
            except json.JSONDecodeError:
                continue
        
        if len(feedback_data) >= min_samples:
            self.analyzer.update_weights(feedback_data)
            return True
        return False
    
    def get_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get aggregated metrics."""
        return self.metrics.get_metrics(days)
    
    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()


# Singleton
_escalator_v2_instance: Optional[ModelEscalatorV2] = None

def get_escalator_v2() -> ModelEscalatorV2:
    global _escalator_v2_instance
    if _escalator_v2_instance is None:
        config_path = Path(__file__).parent.parent / "config" / "model_escalator.json"
        _escalator_v2_instance = ModelEscalatorV2(
            str(config_path) if config_path.exists() else None
        )
    return _escalator_v2_instance


def model_escalation_hook_v2(conversation_id: str, 
                             conversation_context: Dict[str, Any]) -> EscalationResult:
    """Enhanced escalation hook with ML features."""
    escalator = get_escalator_v2()
    return escalator.determine_model(conversation_id, conversation_context)


def record_model_feedback(conversation_id: str, message: str, model: str,
                          complexity: float, rating: int, comment: str = None):
    """
    Record user feedback on model choice.
    
    Usage:
        # After user indicates model was wrong
        record_model_feedback(
            conversation_id="main-session",
            message="Implement authentication system",
            model="claude-haiku",
            complexity=0.3,
            rating=1,  # Too weak
            comment="Needed Opus for this"
        )
    """
    escalator = get_escalator_v2()
    escalator.record_feedback(conversation_id, message, model, complexity, rating, comment)


def get_escalation_metrics(days: int = 7) -> Dict[str, Any]:
    """Get escalation metrics."""
    escalator = get_escalator_v2()
    return escalator.get_metrics(days)
