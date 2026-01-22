"""
StigChecklist Repository

Repository for StigChecklist aggregates.
"""

from typing import Optional, List
import uuid
from django.http import HttpRequest

from core.domain.repository import BaseRepository
from ..aggregates.stig_checklist import StigChecklist
from ..services.audit_service import audit_service


class StigChecklistRepository(BaseRepository[StigChecklist]):
    """
    Repository for StigChecklist aggregates.

    Provides methods for querying and managing STIG checklists.
    """

    def __init__(self):
        super().__init__(StigChecklist)

    def find_by_hostname_and_stig(self, hostname: str, stig_type: str) -> Optional[StigChecklist]:
        """Find checklist by hostname and STIG type"""
        try:
            return StigChecklist.objects.get(hostName=hostname, stigType=stig_type)
        except StigChecklist.DoesNotExist:
            return None

    def find_by_system_group(self, system_group_id: uuid.UUID) -> List[StigChecklist]:
        """Find all checklists for a system group"""
        return list(StigChecklist.objects.filter(systemGroupId=system_group_id))

    def find_active_checklists(self) -> List[StigChecklist]:
        """Find all active checklists"""
        return list(StigChecklist.objects.filter(lifecycle_state=StigChecklist.LifecycleState.ACTIVE))

    def find_checklists_by_stig_type(self, stig_type: str) -> List[StigChecklist]:
        """Find checklists by STIG type"""
        return list(StigChecklist.objects.filter(stigType=stig_type))

    def find_checklists_with_findings(self) -> List[StigChecklist]:
        """Find checklists that have vulnerability findings"""
        return list(StigChecklist.objects.exclude(vulnerabilityFindingIds=[]))

    def find_unassigned_checklists(self) -> List[StigChecklist]:
        """Find checklists not assigned to any system group"""
        return list(StigChecklist.objects.filter(systemGroupId__isnull=True))

    def count_checklists_by_lifecycle_state(self, lifecycle_state: str) -> int:
        """Count checklists by lifecycle state"""
        return StigChecklist.objects.filter(lifecycle_state=lifecycle_state).count()

    def search_checklists(self, query: str, system_group_id: Optional[uuid.UUID] = None) -> List[StigChecklist]:
        """Search checklists by hostname, STIG type, or description"""
        queryset = StigChecklist.objects.filter(
            hostName__icontains=query
        ) | StigChecklist.objects.filter(
            stigType__icontains=query
        )

        if system_group_id:
            queryset = queryset.filter(systemGroupId=system_group_id)

        return list(queryset.distinct())

    def get_checklists_with_open_findings(self, min_open_count: int = 1) -> List[StigChecklist]:
        """Get checklists with open findings (requires score data)"""
        # This would typically join with ChecklistScore, but for now we return all checklists
        # In a real implementation, you'd filter based on score data
        return list(StigChecklist.objects.all())

    def assign_to_system(self, checklist_id: uuid.UUID, system_group_id: uuid.UUID,
                         user_id: uuid.UUID, username: str, request: HttpRequest = None) -> bool:
        """Assign checklist to a system group with audit logging"""
        try:
            checklist = StigChecklist.objects.get(id=checklist_id)
            old_system_id = checklist.systemGroupId

            checklist.systemGroupId = system_group_id
            self.save(checklist, user_id, username, request)

            # Log the assignment
            audit_service.log_operation(
                user_id=user_id,
                username=username,
                action_type='assign_system',
                entity_type='stig_checklist',
                entity_id=checklist_id,
                entity_name=checklist.title,
                request=request,
                old_values={'systemGroupId': str(old_system_id) if old_system_id else None},
                new_values={'systemGroupId': str(system_group_id)}
            )

            return True
        except StigChecklist.DoesNotExist:
            return False

    def unassign_from_system(self, checklist_id: uuid.UUID, user_id: uuid.UUID,
                           username: str, request: HttpRequest = None) -> bool:
        """Remove checklist from its system group with audit logging"""
        try:
            checklist = StigChecklist.objects.get(id=checklist_id)
            old_system_id = checklist.systemGroupId

            checklist.systemGroupId = None
            self.save(checklist, user_id, username, request)

            # Log the unassignment
            audit_service.log_operation(
                user_id=user_id,
                username=username,
                action_type='remove_from_system',
                entity_type='stig_checklist',
                entity_id=checklist_id,
                entity_name=checklist.title,
                request=request,
                old_values={'systemGroupId': str(old_system_id) if old_system_id else None},
                new_values={'systemGroupId': None}
            )

            return True
        except StigChecklist.DoesNotExist:
            return False

    def import_ckl(self, checklist_id: uuid.UUID, ckl_content: str, parsed_data: dict,
                  user_id: uuid.UUID, username: str, request: HttpRequest = None) -> bool:
        """Import CKL content with audit logging"""
        try:
            checklist = StigChecklist.objects.get(id=checklist_id)

            # Store old values for audit
            old_values = {
                'raw_ckl_content': bool(checklist.raw_ckl_content),
                'stig_type': checklist.stig_type,
                'stig_release': checklist.stig_release,
                'host_name': checklist.host_name,
                'lifecycle_state': checklist.lifecycle_state
            }

            # Update checklist with parsed data
            checklist.raw_ckl_content = ckl_content
            checklist.title = parsed_data.get("title", checklist.title)
            checklist.stig_type = parsed_data.get("stig_type", checklist.stig_type)
            checklist.stig_release = parsed_data.get("stig_release", checklist.stig_release)
            checklist.stig_version = parsed_data.get("stig_version", checklist.stig_version)
            checklist.host_name = parsed_data.get("host_name", checklist.host_name)
            checklist.host_ip = parsed_data.get("host_ip", checklist.host_ip)
            checklist.host_fqdn = parsed_data.get("host_fqdn", checklist.host_fqdn)

            # Asset classification from parsed data
            asset_info = parsed_data.get("asset_info", {})
            checklist.is_web_database = asset_info.get("web_or_database", False)
            checklist.web_database_site = asset_info.get("web_db_site")
            checklist.web_database_instance = asset_info.get("web_db_instance")

            # Set asset type based on inference
            inferred_asset_type = asset_info.get("inferred_asset_type", "computing")
            if inferred_asset_type in dict(checklist.ASSET_TYPES):
                checklist.asset_type = inferred_asset_type
            else:
                checklist.asset_type = "computing"  # Default fallback

            checklist.lifecycle_state = StigChecklist.LifecycleState.IMPORTED

            self.save(checklist, user_id, username, request)

            # Log the import
            audit_service.log_operation(
                user_id=user_id,
                username=username,
                action_type='import_ckl',
                entity_type='stig_checklist',
                entity_id=checklist_id,
                entity_name=checklist.title,
                request=request,
                old_values=old_values,
                new_values={
                    'raw_ckl_content': True,
                    'stig_type': checklist.stig_type,
                    'stig_release': checklist.stig_release,
                    'host_name': checklist.host_name,
                    'lifecycle_state': checklist.lifecycle_state,
                    'ckl_size': len(ckl_content)
                }
            )

            return True
        except StigChecklist.DoesNotExist:
            return False

    def export_ckl(self, checklist_id: uuid.UUID, user_id: uuid.UUID,
                  username: str, request: HttpRequest = None) -> Optional[str]:
        """Export CKL content with audit logging"""
        try:
            checklist = StigChecklist.objects.get(id=checklist_id)

            if not checklist.raw_ckl_content:
                return None

            # Log the export
            audit_service.log_operation(
                user_id=user_id,
                username=username,
                action_type='export_ckl',
                entity_type='stig_checklist',
                entity_id=checklist_id,
                entity_name=checklist.title,
                request=request,
                old_values=None,
                new_values={'exported_at': str(checklist.updated_at)}
            )

            return checklist.raw_ckl_content
        except StigChecklist.DoesNotExist:
            return None

    def get_checklist_with_findings(self, checklist_id: uuid.UUID) -> Optional[StigChecklist]:
        """Get checklist with its vulnerability findings (for detailed view)"""
        try:
            return StigChecklist.objects.get(id=checklist_id)
        except StigChecklist.DoesNotExist:
            return None

    def bulk_update_lifecycle_state(self, checklist_ids: List[uuid.UUID],
                                   new_state: str) -> int:
        """Bulk update lifecycle state for multiple checklists"""
        return StigChecklist.objects.filter(
            id__in=checklist_ids
        ).update(lifecycle_state=new_state)

    def get_checklists_by_asset(self, asset_hostname: str) -> List[StigChecklist]:
        """Find checklists for a specific asset hostname"""
        return list(StigChecklist.objects.filter(hostName=asset_hostname))

    def get_recent_checklists(self, days: int = 30) -> List[StigChecklist]:
        """Get checklists created within the last N days"""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days)
        return list(StigChecklist.objects.filter(created_at__gte=cutoff_date))
