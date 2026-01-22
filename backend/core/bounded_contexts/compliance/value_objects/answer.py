"""
Answer Value Object

Immutable value object representing an answer to a question in an assessment.
"""

from typing import Optional, Union, Dict, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class Answer:
    """
    Answer value object.

    Immutable value object representing an answer to a question.
    """

    question_id: str
    value: Union[str, int, float, bool, None]
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with camelCase keys for JSON serialization"""
        return {
            "questionId": self.question_id,
            "value": self.value,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Answer":
        """Create from dictionary (accepts both camelCase and snake_case)"""
        return cls(
            question_id=data.get("questionId") or data.get("question_id"),
            value=data.get("value"),
            notes=data.get("notes"),
        )

    def __repr__(self):
        return f"Answer(question_id={self.question_id}, value={self.value!r})"

