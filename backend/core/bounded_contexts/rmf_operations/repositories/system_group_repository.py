"""
SystemGroup Repository

Repository for SystemGroup aggregates.
"""

from typing import Optional, List
import uuid
from django.http import HttpRequest

from core.domain.repository import BaseRepository
from ..aggregates.system_group import SystemGroup
from ..services.audit_service import audit_service


class SystemGroupRepository(BaseRepository[SystemGroup]):
    """
    Repository for SystemGroup aggregates.

    Provides methods for querying and managing system groups.
    """

    def __init__(self):
        super().__init__(SystemGroup)

    def find_by_name(self, name: str) -> Optional[SystemGroup]:
        """Find system group by name"""
        try:
            return SystemGroup.objects.get(name=name)
        except SystemGroup.DoesNotExist:
            return None

    def find_active_systems(self) -> List[SystemGroup]:
        """Find all active system groups"""
        return list(SystemGroup.objects.filter(lifecycle_state=SystemGroup.LifecycleState.ACTIVE))

    def find_systems_with_checklists(self) -> List[SystemGroup]:
        """Find systems that have checklists assigned"""
        return list(SystemGroup.objects.exclude(checklistIds=[]))

    def find_systems_by_asset(self, asset_id: uuid.UUID) -> List[SystemGroup]:
        """Find systems that contain a specific asset"""
        # Using PostgreSQL array contains operator
        return list(SystemGroup.objects.filter(assetIds__contains=[str(asset_id)]))

    def find_systems_by_checklist(self, checklist_id: uuid.UUID) -> List[SystemGroup]:
        """Find systems that contain a specific checklist"""
        return list(SystemGroup.objects.filter(checklistIds__contains=[str(checklist_id)]))

    def count_systems_by_lifecycle_state(self, lifecycle_state: str) -> int:
        """Count systems by lifecycle state"""
        return SystemGroup.objects.filter(lifecycle_state=lifecycle_state).count()

    def get_system_with_stats(self, system_id: uuid.UUID) -> Optional[SystemGroup]:
        """Get system with computed statistics"""
        try:
            return SystemGroup.objects.get(id=system_id)
        except SystemGroup.DoesNotExist:
            return None

    def search_systems(self, query: str, lifecycle_state: Optional[str] = None) -> List[SystemGroup]:
        """Search systems by name or description"""
        queryset = SystemGroup.objects.filter(
            name__icontains=query
        ) | SystemGroup.objects.filter(
            description__icontains=query
        )

        if lifecycle_state:
            queryset = queryset.filter(lifecycle_state=lifecycle_state)

        return list(queryset.distinct())

    def get_systems_with_open_vulnerabilities(self, min_open_count: int = 1) -> List[SystemGroup]:
        """Get systems with open vulnerabilities above threshold"""
        return list(SystemGroup.objects.filter(
            totalOpenVulnerabilities__gte=min_open_count
        ))

    def get_systems_with_critical_findings(self) -> List[SystemGroup]:
        """Get systems with critical (CAT I) open vulnerabilities"""
        return list(SystemGroup.objects.filter(totalCat1Open__gt=0))

    def update_system_stats(self, system_id: uuid.UUID,
                           total_checklists: int = None,
                           total_open: int = None,
                           cat1_open: int = None,
                           cat2_open: int = None,
                           cat3_open: int = None) -> bool:
        """Update computed statistics for a system"""
        try:
            system = SystemGroup.objects.get(id=system_id)
            old_values = {
                'totalChecklists': system.totalChecklists,
                'totalOpenVulnerabilities': system.totalOpenVulnerabilities,
                'totalCat1Open': system.totalCat1Open,
                'totalCat2Open': system.totalCat2Open,
                'totalCat3Open': system.totalCat3Open
            }

            if total_checklists is not None:
                system.totalChecklists = total_checklists
            if total_open is not None:
                system.totalOpenVulnerabilities = total_open
            if cat1_open is not None:
                system.totalCat1Open = cat1_open
            if cat2_open is not None:
                system.totalCat2Open = cat2_open
            if cat3_open is not None:
                system.totalCat3Open = cat3_open

            system.save()

            # Log the statistics update (system operation)
            audit_service.log_system_operation(
                action_type='update',
                entity_type='system_group',
                entity_id=system_id,
                entity_name=system.name,
                details={
                    'operation': 'statistics_update',
                    'old_values': old_values,
                    'new_values': {
                        'totalChecklists': system.totalChecklists,
                        'totalOpenVulnerabilities': system.totalOpenVulnerabilities,
                        'totalCat1Open': system.totalCat1Open,
                        'totalCat2Open': system.totalCat2Open,
                        'totalCat3Open': system.totalCat3Open
                    }
                }
            )

            return True
        except SystemGroup.DoesNotExist:
            return False

    def activate_system(self, system_id: uuid.UUID, user_id: uuid.UUID,
                       username: str, request: HttpRequest = None) -> bool:
        """Activate a system with audit logging"""
        try:
            system = SystemGroup.objects.get(id=system_id)
            if system.lifecycle_state == SystemGroup.LifecycleState.DRAFT:
                system.lifecycle_state = SystemGroup.LifecycleState.ACTIVE
                self.save(system, user_id, username, request)

                # Log the activation
                audit_service.log_operation(
                    user_id=user_id,
                    username=username,
                    action_type='activate',
                    entity_type='system_group',
                    entity_id=system_id,
                    entity_name=system.name,
                    request=request,
                    old_values={'lifecycle_state': 'draft'},
                    new_values={'lifecycle_state': 'active'}
                )

                return True
        except SystemGroup.DoesNotExist:
            return False
        return False

    def archive_system(self, system_id: uuid.UUID, user_id: uuid.UUID,
                      username: str, request: HttpRequest = None) -> bool:
        """Archive a system with audit logging"""
        try:
            system = SystemGroup.objects.get(id=system_id)
            if system.lifecycle_state == SystemGroup.LifecycleState.ACTIVE:
                system.lifecycle_state = SystemGroup.LifecycleState.ARCHIVED
                self.save(system, user_id, username, request)

                # Log the archival
                audit_service.log_operation(
                    user_id=user_id,
                    username=username,
                    action_type='archive',
                    entity_type='system_group',
                    entity_id=system_id,
                    entity_name=system.name,
                    request=request,
                    old_values={'lifecycle_state': 'active'},
                    new_values={'lifecycle_state': 'archived'}
                )

                return True
        except SystemGroup.DoesNotExist:
            return False
        return False

    def add_checklist_to_system(self, system_id: uuid.UUID, checklist_id: uuid.UUID,
                               user_id: uuid.UUID, username: str,
                               request: HttpRequest = None) -> bool:
        """Add checklist to system with audit logging"""
        try:
            system = SystemGroup.objects.get(id=system_id)
            checklist_id_str = str(checklist_id)

            if checklist_id_str not in system.checklistIds:
                old_checklist_ids = system.checklistIds.copy()
                system.checklistIds.append(checklist_id_str)
                self.save(system, user_id, username, request)

                # Log the assignment
                audit_service.log_operation(
                    user_id=user_id,
                    username=username,
                    action_type='assign_system',
                    entity_type='stig_checklist',
                    entity_id=checklist_id,
                    entity_name=f"Checklist assigned to {system.name}",
                    request=request,
                    old_values={'system_group_id': None},
                    new_values={'system_group_id': str(system_id)}
                )

                return True
        except SystemGroup.DoesNotExist:
            return False
        return False

    def remove_checklist_from_system(self, system_id: uuid.UUID, checklist_id: uuid.UUID,
                                    user_id: uuid.UUID, username: str,
                                    request: HttpRequest = None) -> bool:
        """Remove checklist from system with audit logging"""
        try:
            system = SystemGroup.objects.get(id=system_id)
            checklist_id_str = str(checklist_id)

            if checklist_id_str in system.checklistIds:
                old_checklist_ids = system.checklistIds.copy()
                system.checklistIds.remove(checklist_id_str)
                self.save(system, user_id, username, request)

                # Log the removal
                audit_service.log_operation(
                    user_id=user_id,
                    username=username,
                    action_type='remove_from_system',
                    entity_type='stig_checklist',
                    entity_id=checklist_id,
                    entity_name=f"Checklist removed from {system.name}",
                    request=request,
                    old_values={'system_group_id': str(system_id)},
                    new_values={'system_group_id': None}
                )

                return True
        except SystemGroup.DoesNotExist:
            return False
        return False
