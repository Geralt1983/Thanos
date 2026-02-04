#!/usr/bin/env python3
"""
Model Prefix Tracking System

Ensures conversation prefix ([H], [S], [O]) matches current active model.
Provides auto-correction and logging mechanisms.
"""

import os
import sqlite3
from typing import Dict, Optional
import logging
from datetime import datetime

class ModelPrefixTracker:
    def __init__(self, db_path: str = None):
        """
        Initialize Model Prefix Tracker
        
        Args:
            db_path: Path to SQLite database for tracking
        """
        self.db_path = db_path or os.path.expanduser("~/Projects/Thanos/model_prefix_state.db")
        self._init_db()
        self.logger = logging.getLogger('model_prefix_tracker')
        self.logger.setLevel(logging.INFO)
    
    def _init_db(self):
        """Create tracking database if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prefix_log (
                    timestamp REAL,
                    session_id TEXT,
                    detected_prefix TEXT,
                    actual_model TEXT,
                    correction_applied INTEGER
                )
            ''')
            conn.commit()
    
    def _log_prefix_issue(self, session_id: str, detected_prefix: str, actual_model: str):
        """Log prefix tracking discrepancy"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO prefix_log 
                (timestamp, session_id, detected_prefix, actual_model, correction_applied)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().timestamp(), 
                session_id, 
                detected_prefix, 
                actual_model, 
                0  # Not corrected yet
            ))
            conn.commit()
    
    MODEL_TO_PREFIX = {
        'anthropic/claude-3-5-haiku-20241022': '[H]',
        'anthropic/claude-sonnet-4-5': '[S]',
        'anthropic/claude-sonnet-4-5': '[S]',
        'anthropic/claude-opus-4-5': '[O]',
        # Add more models as needed
    }
    
    PREFIX_TO_MODEL = {v: k for k, v in MODEL_TO_PREFIX.items()}
    
    def get_correct_prefix(self, model: str) -> str:
        """
        Get the correct prefix for a given model
        
        Args:
            model: Full model name
        
        Returns:
            Correct prefix, defaults to '[H]' if unknown
        """
        return self.MODEL_TO_PREFIX.get(model, '[H]')
    
    def validate_prefix(self, current_prefix: str, current_model: str) -> bool:
        """
        Check if current prefix matches the model
        
        Args:
            current_prefix: Detected prefix
            current_model: Full model name
        
        Returns:
            True if prefix matches model, False otherwise
        """
        expected_prefix = self.get_correct_prefix(current_model)
        return current_prefix == expected_prefix
    
    def correct_prefix(self, session_id: str, current_prefix: str, current_model: str) -> Optional[str]:
        """
        Correct prefix if it doesn't match the model
        
        Args:
            session_id: Unique session identifier
            current_prefix: Currently used prefix
            current_model: Full model name
        
        Returns:
            Corrected prefix or None if no correction needed
        """
        if self.validate_prefix(current_prefix, current_model):
            return None
        
        # Log the discrepancy
        self._log_prefix_issue(session_id, current_prefix, current_model)
        
        # Return the correct prefix
        correct_prefix = self.get_correct_prefix(current_model)
        
        # Update database to mark as corrected
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE prefix_log 
                SET correction_applied = 1 
                WHERE session_id = ? AND detected_prefix = ? AND actual_model = ?
            ''', (session_id, current_prefix, current_model))
            conn.commit()
        
        return correct_prefix

def main():
    """Standalone testing of ModelPrefixTracker"""
    tracker = ModelPrefixTracker()
    
    # Test scenarios
    test_cases = [
        ('[H]', 'anthropic/claude-opus-4-5'),  # Mismatched
        ('[S]', 'anthropic/claude-3-5-haiku-20241022'),  # Mismatched
        ('[O]', 'anthropic/claude-sonnet-4-5'),  # Mismatched
        ('[O]', 'anthropic/claude-opus-4-5'),  # Matched
    ]
    
    for prefix, model in test_cases:
        correction = tracker.correct_prefix('test-session', prefix, model)
        if correction:
            print(f"Corrected: {prefix} → {correction} for model {model}")
        else:
            print(f"No correction needed for {prefix} with model {model}")

if __name__ == "__main__":
    main()
