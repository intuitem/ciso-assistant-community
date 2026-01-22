"""
IncidentEvent Value Object

Immutable value object representing an event in an incident timeline.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class IncidentEvent:
    """
    Incident event value object.

    Immutable value object representing an event in an incident timeline.
    """

    at: str  # ISO format datetime string for JSON serialization
    action: str
    actor_user_id: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            "at": self.at,
            "action": self.action,
            "actorUserId": self.actor_user_id,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IncidentEvent":
        """Create from dictionary"""
        return cls(
            at=data.get("at"),
            action=data.get("action"),
            actor_user_id=data.get("actorUserId"),
            notes=data.get("notes"),
        )

    @classmethod
    def create(cls, action: str, actor_user_id: Optional[str] = None,
               notes: Optional[str] = None) -> "IncidentEvent":
        """Factory method to create an event with current timestamp"""
        from django.utils import timezone
        return cls(
            at=timezone.now().isoformat(),
            action=action,
            actor_user_id=actor_user_id,
            notes=notes,
        )

    def __repr__(self):
        return f"IncidentEvent(at={self.at}, action={self.action!r})"

