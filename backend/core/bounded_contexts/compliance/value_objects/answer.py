"""
Answer Value Object

Immutable value object representing an answer to a question in an assessment.
"""

from typing import Optional, Union
from core.domain.value_object import ValueObject


class Answer(ValueObject):
    """
    Answer value object.
    
    Immutable value object representing an answer to a question.
    """
    
    def __init__(self, question_id: str, value: Union[str, int, float, bool, None],
                 notes: Optional[str] = None):
        """
        Initialize an answer.
        
        Args:
            question_id: ID of the question being answered
            value: Answer value (string, number, boolean, or null)
            notes: Optional notes about the answer
        """
        self.question_id = question_id
        self.value = value
        self.notes = notes
    
    def __repr__(self):
        return f"Answer(question_id={self.question_id}, value={self.value!r})"

