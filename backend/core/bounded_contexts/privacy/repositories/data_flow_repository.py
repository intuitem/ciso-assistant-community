"""
Repository for DataFlow aggregates
"""

from typing import Optional, List
from uuid import UUID
from core.domain.repository import Repository
from ..aggregates.data_flow import DataFlow


class DataFlowRepository(Repository[DataFlow]):
    """Repository for DataFlow aggregates"""
    
    def __init__(self):
        super().__init__(DataFlow)
    
    def find_by_name(self, name: str) -> Optional[DataFlow]:
        """Find data flow by name"""
        return DataFlow.objects.filter(name=name).first()
    
    def find_by_source(self, source_asset_id: UUID) -> List[DataFlow]:
        """Find all flows from a source asset"""
        return list(DataFlow.objects.filter(source_system_asset_id=source_asset_id))
    
    def find_by_destination(self, destination_asset_id: UUID) -> List[DataFlow]:
        """Find all flows to a destination asset"""
        return list(DataFlow.objects.filter(destination_system_asset_id=destination_asset_id))
    
    def find_active(self) -> List[DataFlow]:
        """Find all active data flows"""
        return list(
            DataFlow.objects.filter(lifecycle_state=DataFlow.LifecycleState.ACTIVE)
        )
    
    def find_without_encryption(self) -> List[DataFlow]:
        """Find all flows without encryption in transit"""
        return list(
            DataFlow.objects.filter(encryption_in_transit=False)
        )

