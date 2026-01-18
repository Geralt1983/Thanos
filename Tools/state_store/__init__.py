"""
SQLite-based state store for Thanos orchestrator.
Provides persistent storage for daily plans, scoreboards, reminders, and turn logs.
"""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime


class SQLiteStateStore:
    """SQLite-backed state storage for orchestrator state."""
    
    def __init__(self, db_path: Path):
        """Initialize the state store with a SQLite database.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # State table for key-value storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Turn logs for tracking API usage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turn_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    model TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    latency_ms REAL DEFAULT 0.0,
                    tool_call_count INTEGER DEFAULT 0,
                    state_size INTEGER DEFAULT 0,
                    prompt_bytes INTEGER DEFAULT 0,
                    response_bytes INTEGER DEFAULT 0
                )
            """)
            
            # Tool summaries for recent actions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tool_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tool_name TEXT,
                    summary TEXT,
                    result_type TEXT
                )
            """)
            
            conn.commit()
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value by key.
        
        Args:
            key: The state key to retrieve.
            default: Default value if key doesn't exist.
            
        Returns:
            The stored value or default.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM state WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return default
        except (sqlite3.Error, json.JSONDecodeError):
            return default
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a state value.
        
        Args:
            key: The state key to set.
            value: The value to store (will be JSON serialized).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO state (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, json.dumps(value)))
                conn.commit()
        except (sqlite3.Error, TypeError):
            pass  # Silently fail on serialization errors
    
    def get_state_size(self) -> int:
        """Get the total size of stored state in bytes.
        
        Returns:
            Total size of all state values in bytes.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(LENGTH(value)) FROM state")
                row = cursor.fetchone()
                return row[0] or 0
        except sqlite3.Error:
            return 0
    
    def record_turn_log(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        tool_call_count: int = 0,
        state_size: int = 0,
        prompt_bytes: int = 0,
        response_bytes: int = 0,
    ) -> None:
        """Record a turn log entry for API usage tracking.
        
        Args:
            model: The model used for the turn.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            cost_usd: Estimated cost in USD.
            latency_ms: Response latency in milliseconds.
            tool_call_count: Number of tool calls made.
            state_size: Size of state at time of turn.
            prompt_bytes: Size of prompt in bytes.
            response_bytes: Size of response in bytes.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO turn_logs (
                        model, input_tokens, output_tokens, cost_usd,
                        latency_ms, tool_call_count, state_size,
                        prompt_bytes, response_bytes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    model, input_tokens, output_tokens, cost_usd,
                    latency_ms, tool_call_count, state_size,
                    prompt_bytes, response_bytes
                ))
                conn.commit()
        except sqlite3.Error:
            pass
    
    def get_recent_summaries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent tool summaries.
        
        Args:
            limit: Maximum number of summaries to return.
            
        Returns:
            List of summary dictionaries.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT tool_name, summary, result_type, timestamp
                    FROM tool_summaries
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                return [
                    {
                        "tool_name": row[0],
                        "summary": row[1],
                        "result_type": row[2],
                        "timestamp": row[3],
                    }
                    for row in rows
                ]
        except sqlite3.Error:
            return []
    
    def add_tool_summary(
        self,
        tool_name: str,
        summary: str,
        result_type: str = "success"
    ) -> None:
        """Add a tool execution summary.
        
        Args:
            tool_name: Name of the tool executed.
            summary: Summary of the tool's result.
            result_type: Type of result (success, error, etc.).
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tool_summaries (tool_name, summary, result_type)
                    VALUES (?, ?, ?)
                """, (tool_name, summary, result_type))
                conn.commit()
        except sqlite3.Error:
            pass
