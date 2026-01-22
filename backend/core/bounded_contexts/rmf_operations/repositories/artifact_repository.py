"""
Artifact Repository

Repository for Artifact aggregates with specialized methods
for file management, security, and access control.
"""

from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

from core.domain.repository import BaseRepository
from ..aggregates.artifact import Artifact


class ArtifactRepository(BaseRepository[Artifact]):
    """
    Repository for Artifact aggregates.

    Provides methods for managing file artifacts with security,
    access control, and relationship management.
    """

    def __init__(self):
        super().__init__(Artifact)

    def find_by_system_group(self, system_group_id: uuid.UUID) -> List[Artifact]:
        """Find all artifacts for a system group"""
        return list(Artifact.objects.filter(system_group_id=system_group_id, is_active=True))

    def find_by_checklist(self, checklist_id: uuid.UUID) -> List[Artifact]:
        """Find all artifacts associated with a checklist"""
        return list(Artifact.objects.filter(checklist_id=checklist_id, is_active=True))

    def find_by_vulnerability_finding(self, finding_id: uuid.UUID) -> List[Artifact]:
        """Find all artifacts associated with a vulnerability finding"""
        return list(Artifact.objects.filter(vulnerability_finding_id=finding_id, is_active=True))

    def find_by_nessus_scan(self, scan_id: uuid.UUID) -> List[Artifact]:
        """Find all artifacts associated with a Nessus scan"""
        return list(Artifact.objects.filter(nessus_scan_id=scan_id, is_active=True))

    def find_by_control(self, control_id: str) -> List[Artifact]:
        """Find artifacts associated with a specific RMF control"""
        return list(Artifact.objects.filter(control_id=control_id, is_active=True))

    def find_by_type(self, artifact_type: str, system_group_id: Optional[uuid.UUID] = None) -> List[Artifact]:
        """Find artifacts by type, optionally filtered by system group"""
        queryset = Artifact.objects.filter(artifact_type=artifact_type, is_active=True)
        if system_group_id:
            queryset = queryset.filter(system_group_id=system_group_id)
        return list(queryset.order_by('-created_at'))

    def find_by_security_level(self, security_level: str) -> List[Artifact]:
        """Find artifacts by security classification level"""
        return list(Artifact.objects.filter(security_level=security_level, is_active=True))

    def find_expired_artifacts(self) -> List[Artifact]:
        """Find artifacts that have expired"""
        return list(Artifact.objects.filter(
            expires_at__isnull=False,
            expires_at__lt=datetime.now(),
            is_active=True
        ))

    def search_artifacts(self, query: str, system_group_id: Optional[uuid.UUID] = None) -> List[Artifact]:
        """Search artifacts by title, description, or filename"""
        queryset = Artifact.objects.filter(is_active=True).filter(
            title__icontains=query
        ) | Artifact.objects.filter(
            description__icontains=query
        ) | Artifact.objects.filter(
            filename__icontains=query
        )

        if system_group_id:
            queryset = queryset.filter(system_group_id=system_group_id)

        return list(queryset.distinct().order_by('-created_at'))

    def get_storage_statistics(self, system_group_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Get artifact storage statistics"""
        queryset = Artifact.objects.filter(is_active=True)
        if system_group_id:
            queryset = queryset.filter(system_group_id=system_group_id)

        total_files = queryset.count()
        total_size = queryset.aggregate(
            total_size=Sum('file_size')
        )['total_size'] or 0

        # Type distribution
        type_stats = queryset.values('artifact_type').annotate(
            count=models.Count('id'),
            total_size=Sum('file_size')
        ).order_by('-count')

        # Security level distribution
        security_stats = queryset.values('security_level').annotate(
            count=models.Count('id')
        ).order_by('-count')

        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'type_distribution': list(type_stats),
            'security_distribution': list(security_stats),
            'expired_count': len(self.find_expired_artifacts())
        }

    def add_relationship(self, artifact_id: uuid.UUID,
                        checklist_id: Optional[uuid.UUID] = None,
                        vulnerability_finding_id: Optional[uuid.UUID] = None,
                        nessus_scan_id: Optional[uuid.UUID] = None) -> bool:
        """Add relationship to an artifact"""
        try:
            artifact = self.get_by_id(artifact_id)
            if artifact:
                artifact.add_relationship(
                    checklist_id=checklist_id,
                    vulnerability_finding_id=vulnerability_finding_id,
                    nessus_scan_id=nessus_scan_id
                )
                self.save(artifact)
                return True
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error adding artifact relationship: {e}")
            return False

    def update_security_level(self, artifact_id: uuid.UUID,
                            security_level: str,
                            access_list: Optional[List[str]] = None) -> bool:
        """Update artifact security classification"""
        try:
            artifact = self.get_by_id(artifact_id)
            if artifact:
                artifact.set_security_level(security_level, access_list)
                self.save(artifact)
                return True
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating artifact security: {e}")
            return False

    def add_cci_reference(self, artifact_id: uuid.UUID, cci_id: str) -> bool:
        """Add CCI reference to artifact"""
        try:
            artifact = self.get_by_id(artifact_id)
            if artifact:
                artifact.add_cci_reference(cci_id)
                self.save(artifact)
                return True
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error adding CCI reference: {e}")
            return False

    def deactivate_artifact(self, artifact_id: uuid.UUID) -> bool:
        """Deactivate an artifact"""
        try:
            artifact = self.get_by_id(artifact_id)
            if artifact:
                artifact.deactivate()
                # Note: Physical file deletion would be handled by a background task
                self.save(artifact)
                return True
            return False
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error deactivating artifact: {e}")
            return False

    def cleanup_expired_artifacts(self) -> int:
        """Deactivate expired artifacts"""
        expired_artifacts = self.find_expired_artifacts()
        count = 0

        for artifact in expired_artifacts:
            artifact.deactivate()
            self.save(artifact)
            count += 1

        return count

    def validate_artifact_access(self, artifact_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Validate user access to an artifact"""
        try:
            artifact = self.get_by_id(artifact_id)
            if not artifact:
                return {'has_access': False, 'reason': 'Artifact not found'}

            if not artifact.is_active:
                return {'has_access': False, 'reason': 'Artifact is inactive'}

            if artifact.is_expired():
                return {'has_access': False, 'reason': 'Artifact has expired'}

            # Check public access
            if artifact.is_public:
                return {'has_access': True}

            # Check access list (simplified - would need proper user/group resolution)
            if artifact.access_list and str(user_id) in artifact.access_list:
                return {'has_access': True}

            return {'has_access': False, 'reason': 'Access denied'}

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error validating artifact access: {e}")
            return {'has_access': False, 'reason': 'Access validation error'}

    def get_artifacts_for_bulk_operation(self, system_group_id: uuid.UUID,
                                       artifact_type: Optional[str] = None,
                                       security_level: Optional[str] = None) -> List[Artifact]:
        """Get artifacts suitable for bulk operations"""
        queryset = Artifact.objects.filter(system_group_id=system_group_id, is_active=True)

        if artifact_type:
            queryset = queryset.filter(artifact_type=artifact_type)

        if security_level:
            queryset = queryset.filter(security_level=security_level)

        return list(queryset.order_by('-created_at'))

    def duplicate_artifact_relationships(self, source_artifact_id: uuid.UUID,
                                       target_artifact_id: uuid.UUID) -> bool:
        """Copy relationships from one artifact to another"""
        try:
            source = self.get_by_id(source_artifact_id)
            target = self.get_by_id(target_artifact_id)

            if not source or not target:
                return False

            # Copy relationships
            target.system_group_id = source.system_group_id
            target.checklist_id = source.checklist_id
            target.vulnerability_finding_id = source.vulnerability_finding_id
            target.nessus_scan_id = source.nessus_scan_id
            target.control_id = source.control_id
            target.cci_ids = source.cci_ids.copy()

            self.save(target)
            return True

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error duplicating artifact relationships: {e}")
            return False
