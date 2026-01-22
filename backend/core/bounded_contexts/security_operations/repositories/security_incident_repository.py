"""
Repository for SecurityIncident aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.security_incident import SecurityIncident


class SecurityIncidentRepository(Repository[SecurityIncident]):
    """Repository for SecurityIncident aggregates"""
    
    def __init__(self):
        super().__init__(SecurityIncident)
    
    def find_by_title(self, title: str) -> Optional[SecurityIncident]:
        """Find incident by title"""
        return SecurityIncident.objects.filter(title=title).first()
    
    def find_open(self) -> List[SecurityIncident]:
        """Find all open incidents (not closed)"""
        return list(
            SecurityIncident.objects.exclude(
                lifecycle_state=SecurityIncident.LifecycleState.CLOSED
            )
        )
    
    def find_by_severity(self, severity: str) -> List[SecurityIncident]:
        """Find incidents by severity"""
        return list(SecurityIncident.objects.filter(severity=severity))
    
    def find_by_asset(self, asset_id: UUID) -> List[SecurityIncident]:
        """Find incidents affecting a specific asset"""
        return list(SecurityIncident.objects.filter(affectedAssetIds__contains=[asset_id]))

