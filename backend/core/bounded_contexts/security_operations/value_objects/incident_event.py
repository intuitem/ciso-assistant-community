"""
IncidentEvent Value Object

Immutable value object representing an event in an incident timeline.
"""

from typing import Optional
from datetime import datetime
from core.domain.value_object import ValueObject


class IncidentEvent(ValueObject):
    """
    Incident event value object.
    
    Immutable value object representing an event in an incident timeline.
    """
    
    def __init__(self, at: datetime, action: str, actor_user_id: Optional[str] = None,
                 notes: Optional[str] = None):
        """
        Initialize an incident event.
        
        Args:
            at: When the event occurred
            action: Description of the action taken
            actor_user_id: Optional ID of the user who performed the action
            notes: Optional additional notes
        """
        self.at = at
        self.action = action
        self.actor_user_id = actor_user_id
        self.notes = notes
    
    def __repr__(self):
        return f"IncidentEvent(at={self.at}, action={self.action!r})"

