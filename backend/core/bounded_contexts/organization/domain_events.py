"""
Domain Events for Organization Bounded Context
"""

from core.domain.events import DomainEvent


class OrgUnitCreated(DomainEvent):
    """Raised when an organizational unit is created"""
    pass


class OrgUnitActivated(DomainEvent):
    """Raised when an organizational unit is activated"""
    pass


class OrgUnitRetired(DomainEvent):
    """Raised when an organizational unit is retired"""
    pass


class ChildOrgUnitAdded(DomainEvent):
    """Raised when a child organizational unit is added"""
    pass


class OwnerAssignedToOrgUnit(DomainEvent):
    """Raised when an owner is assigned to an organizational unit"""
    pass


class UserCreated(DomainEvent):
    """Raised when a user is created"""
    pass


class UserAssignedToGroup(DomainEvent):
    """Raised when a user is assigned to a group"""
    pass


class UserAssignedToOrgUnit(DomainEvent):
    """Raised when a user is assigned to an organizational unit"""
    pass


class UserActivated(DomainEvent):
    """Raised when a user is activated"""
    pass


class UserDisabled(DomainEvent):
    """Raised when a user is disabled"""
    pass


class GroupCreated(DomainEvent):
    """Raised when a group is created"""
    pass


class PermissionAddedToGroup(DomainEvent):
    """Raised when a permission is added to a group"""
    pass


class UserAddedToGroup(DomainEvent):
    """Raised when a user is added to a group"""
    pass


class ResponsibilityAssigned(DomainEvent):
    """Raised when a responsibility is assigned"""
    pass


class ResponsibilityRevoked(DomainEvent):
    """Raised when a responsibility is revoked"""
    pass


class UserRemovedFromGroup(DomainEvent):
    """Raised when a user is removed from a group"""
    pass


class UserRemovedFromOrgUnit(DomainEvent):
    """Raised when a user is removed from an organizational unit"""
    pass


class PermissionRemovedFromGroup(DomainEvent):
    """Raised when a permission is removed from a group"""
    pass


class OwnerRemovedFromOrgUnit(DomainEvent):
    """Raised when an owner is removed from an organizational unit"""
    pass

