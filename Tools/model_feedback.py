"""
Model feedback wrapper.

Provides the API referenced in AGENTS.md and delegates to ModelEscalator V2.
"""

from typing import Optional

from Tools.model_escalator_v2 import record_model_feedback


def record_feedback(
    conversation_id: str,
    message: str,
    model: str,
    complexity: float,
    rating: int,
    comment: Optional[str] = None,
) -> None:
    """Record user feedback on model choice."""
    record_model_feedback(
        conversation_id=conversation_id,
        message=message,
        model=model,
        complexity=complexity,
        rating=rating,
        comment=comment,
    )
