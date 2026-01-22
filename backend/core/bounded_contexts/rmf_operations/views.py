"""
DRF ViewSets for RMF Operations bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError
import uuid

from core.permissions import RBACPermissions
from ..aggregates.system_group import SystemGroup
from ..aggregates.stig_checklist import StigChecklist
from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..aggregates.checklist_score import ChecklistScore
from ..aggregates.nessus_scan import NessusScan
from ..aggregates.stig_template import StigTemplate
from ..aggregates.artifact import Artifact
from ..repositories.system_group_repository import SystemGroupRepository
from ..repositories.stig_checklist_repository import StigChecklistRepository
from ..repositories.vulnerability_finding_repository import VulnerabilityFindingRepository
from ..repositories.checklist_score_repository import ChecklistScoreRepository
from ..repositories.nessus_scan_repository import NessusScanRepository
from ..repositories.stig_template_repository import StigTemplateRepository
from ..repositories.artifact_repository import ArtifactRepository
from .serializers import (
    SystemGroupSerializer, StigChecklistSerializer,
    VulnerabilityFindingSerializer, ChecklistScoreSerializer,
    NessusScanSerializer, StigTemplateSerializer, ArtifactSerializer
)


class SystemGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for SystemGroup aggregates"""

    queryset = SystemGroup.objects.all()
    serializer_class = SystemGroupSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['lifecycle_state', 'name']
    search_fields = ['name', 'description']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return SystemGroup.objects.all()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a system group"""
        try:
            system = self.get_object()
            system.activate_system()
            system.save()

            serializer = self.get_serializer(system)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a system group"""
        try:
            system = self.get_object()
            system.archive_system()
            system.save()

            serializer = self.get_serializer(system)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_checklist(self, request, pk=None):
        """Add a checklist to the system"""
        system = self.get_object()
        checklist_id = request.data.get('checklist_id')

        if not checklist_id:
            return Response(
                {'error': 'checklist_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            checklist_uuid = uuid.UUID(checklist_id)
            system.add_checklist(checklist_uuid)
            system.save()

            serializer = self.get_serializer(system)
            return Response(serializer.data)
        except (ValueError, ValidationError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_checklist(self, request, pk=None):
        """Remove a checklist from the system"""
        system = self.get_object()
        checklist_id = request.data.get('checklist_id')

        if not checklist_id:
            return Response(
                {'error': 'checklist_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            checklist_uuid = uuid.UUID(checklist_id)
            system.remove_checklist(checklist_uuid)
            system.save()

            serializer = self.get_serializer(system)
            return Response(serializer.data)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def score(self, request, pk=None):
        """Get system-level compliance score"""
        system = self.get_object()
        repo = ChecklistScoreRepository()

        score_data = repo.get_system_level_score(system.id)
        return Response(score_data)

    @action(detail=True, methods=['get'])
    def compliance(self, request, pk=None):
        """Get system compliance summary"""
        system = self.get_object()
        repo = ChecklistScoreRepository()

        compliance_data = repo.get_compliance_summary(system.id)
        return Response(compliance_data)

    @action(detail=True, methods=['get'])
    def checklists(self, request, pk=None):
        """Get all checklists for this system group"""
        system = self.get_object()

        # Get checklists that belong to this system group
        checklists = StigChecklist.objects.filter(systemGroupId=system.id)

        # Apply any additional filters from query params
        lifecycle_state = request.query_params.get('lifecycle_state')
        if lifecycle_state:
            checklists = checklists.filter(lifecycle_state=lifecycle_state)

        stig_type = request.query_params.get('stigType')
        if stig_type:
            checklists = checklists.filter(stigType__icontains=stig_type)

        host_name = request.query_params.get('hostName')
        if host_name:
            checklists = checklists.filter(hostName__icontains=host_name)

        serializer = StigChecklistSerializer(checklists, many=True)
        return Response({
            'count': checklists.count(),
            'results': serializer.data
        })


class StigChecklistViewSet(viewsets.ModelViewSet):
    """ViewSet for StigChecklist aggregates"""

    queryset = StigChecklist.objects.all()
    serializer_class = StigChecklistSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['systemGroupId', 'lifecycle_state', 'stigType', 'hostName']
    search_fields = ['hostName', 'stigType']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return StigChecklist.objects.all()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a checklist"""
        try:
            checklist = self.get_object()
            checklist.activate_checklist()
            checklist.save()

            serializer = self.get_serializer(checklist)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a checklist"""
        try:
            checklist = self.get_object()
            checklist.archive_checklist()
            checklist.save()

            serializer = self.get_serializer(checklist)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def import_ckl(self, request, pk=None):
        """Import CKL data into checklist"""
        checklist = self.get_object()
        ckl_data = request.data.get('ckl_data')

        if not ckl_data:
            return Response(
                {'error': 'ckl_data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            checklist.import_from_ckl(ckl_data)
            checklist.save()

            serializer = self.get_serializer(checklist)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def export_ckl(self, request, pk=None):
        """Export checklist as CKL data"""
        checklist = self.get_object()
        ckl_data = checklist.export_to_ckl()

        return Response({'ckl_data': ckl_data})

    @action(detail=True, methods=['get'])
    def findings(self, request, pk=None):
        """Get vulnerability findings for this checklist"""
        checklist = self.get_object()
        repo = VulnerabilityFindingRepository()

        findings = repo.find_by_checklist(checklist.id)
        serializer = VulnerabilityFindingSerializer(findings, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def score(self, request, pk=None):
        """Get score for this checklist"""
        checklist = self.get_object()
        repo = ChecklistScoreRepository()

        score = repo.find_by_checklist(checklist.id)
        if score:
            serializer = ChecklistScoreSerializer(score)
            return Response(serializer.data)
        else:
            return Response(
                {'error': 'Score not found for this checklist'},
                status=status.HTTP_404_NOT_FOUND
            )


class VulnerabilityFindingViewSet(viewsets.ModelViewSet):
    """ViewSet for VulnerabilityFinding aggregates"""

    queryset = VulnerabilityFinding.objects.all()
    serializer_class = VulnerabilityFindingSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['checklistId', 'severity_category', 'stigId', 'vulnId']
    search_fields = ['vulnId', 'ruleTitle', 'stigId']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return VulnerabilityFinding.objects.all()

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update vulnerability status"""
        finding = self.get_object()

        status_data = request.data.get('status')
        finding_details = request.data.get('finding_details')
        comments = request.data.get('comments')

        if not status_data:
            return Response(
                {'error': 'status is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            finding.update_status(status_data, finding_details, comments)
            finding.save()

            serializer = self.get_serializer(finding)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def set_severity_override(self, request, pk=None):
        """Set severity override"""
        finding = self.get_object()

        severity_override = request.data.get('severity_override')
        justification = request.data.get('justification')

        if not justification:
            return Response(
                {'error': 'justification is required when setting override'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            finding.set_severity_override(severity_override, justification)
            finding.save()

            serializer = self.get_serializer(finding)
            return Response(serializer.data)
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_cci_reference(self, request, pk=None):
        """Add CCI reference"""
        finding = self.get_object()
        cci_id = request.data.get('cci_id')

        if not cci_id:
            return Response(
                {'error': 'cci_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        finding.add_cci_reference(cci_id)
        finding.save()

        serializer = self.get_serializer(finding)
        return Response(serializer.data)

    @action(methods=['post'], detail=False)
    def bulk_update_status(self, request):
        """Bulk update status for multiple findings"""
        finding_ids = request.data.get('finding_ids', [])
        new_status = request.data.get('status')
        finding_details = request.data.get('finding_details')
        comments = request.data.get('comments')

        if not finding_ids or not new_status:
            return Response(
                {'error': 'finding_ids and status are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            repo = VulnerabilityFindingRepository()
            updated_count = repo.bulk_update_status(
                finding_ids, new_status, finding_details, comments
            )

            return Response({'updated_count': updated_count})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ChecklistScoreViewSet(viewsets.ModelViewSet):
    """ViewSet for ChecklistScore aggregates"""

    queryset = ChecklistScore.objects.all()
    serializer_class = ChecklistScoreSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['checklistId', 'systemGroupId', 'stigType', 'hostName']
    search_fields = ['hostName', 'stigType']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return ChecklistScore.objects.all()

    @action(detail=True, methods=['post'])
    def recalculate(self, request, pk=None):
        """Recalculate score from current findings"""
        score = self.get_object()

        # Get findings for this checklist
        repo = VulnerabilityFindingRepository()
        findings_data = repo.get_finding_stats_for_checklist(score.checklistId)

        try:
            # Update score with findings data
            score_repo = ChecklistScoreRepository()
            success = score_repo.update_score_from_findings(
                score.checklistId,
                findings_data.get('details', {})
            )

            if success:
                # Re-fetch updated score
                updated_score = score_repo.find_by_checklist(score.checklistId)
                serializer = self.get_serializer(updated_score)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Failed to update score'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['get'], detail=False)
    def system_compliance(self, request):
        """Get compliance summary for all systems"""
        system_group_id = request.query_params.get('system_group_id')

        repo = ChecklistScoreRepository()
        compliance_data = repo.get_compliance_summary(system_group_id)

        return Response(compliance_data)

    @action(methods=['get'], detail=False)
    def compliance_distribution(self, request):
        """Get compliance distribution across all scores"""
        repo = ChecklistScoreRepository()
        distribution = repo.get_score_distribution()

        return Response(distribution)


class NessusScanViewSet(viewsets.ModelViewSet):
    """ViewSet for NessusScan aggregates"""

    queryset = NessusScan.objects.all()
    serializer_class = NessusScanSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['systemGroupId', 'processing_status', 'scan_date']
    search_fields = ['filename', 'policy_name']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return NessusScan.objects.all()

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Trigger processing of a Nessus scan"""
        try:
            scan = self.get_object()
            repo = NessusScanRepository()

            success = repo.process_scan_file(uuid.UUID(pk))
            if success:
                serializer = self.get_serializer(scan)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Processing failed'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get scan statistics"""
        try:
            repo = NessusScanRepository()
            scan = repo.get_by_id(uuid.UUID(pk))

            if scan:
                stats = repo.get_scan_statistics(scan.systemGroupId)
                return Response(stats)
            else:
                return Response(
                    {'error': 'Scan not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['get'], detail=False)
    def system_scans(self, request):
        """Get all scans for a system group"""
        system_group_id = request.query_params.get('system_group_id')
        if not system_group_id:
            return Response(
                {'error': 'system_group_id parameter required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            repo = NessusScanRepository()
            scans = repo.find_by_system_group(uuid.UUID(system_group_id))
            serializer = self.get_serializer(scans, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StigTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for StigTemplate aggregates"""

    queryset = StigTemplate.objects.all()
    serializer_class = StigTemplateSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['stig_type', 'template_type', 'is_active', 'is_official']
    search_fields = ['name', 'description', 'stig_type']

    def get_queryset(self):
        """Filter queryset based on user permissions - defaults to active only for list"""
        # For list action, show only active templates by default
        # For retrieve and other actions, show all
        if self.action == 'list':
            include_inactive = self.request.query_params.get('include_inactive', 'false').lower() == 'true'
            if not include_inactive:
                return StigTemplate.objects.filter(is_active=True)
        return StigTemplate.objects.all()

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a template"""
        try:
            template = self.get_object()
            template.activate()
            template.save()

            serializer = self.get_serializer(template)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a template"""
        try:
            template = self.get_object()
            template.deactivate()
            template.save()

            serializer = self.get_serializer(template)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def create_checklist(self, request, pk=None):
        """Create a checklist from this template"""
        try:
            template = self.get_object()
            repo = StigTemplateRepository()

            # Increment usage
            repo.increment_usage(uuid.UUID(pk))

            # Template instantiation would be implemented here
            # For now, return success
            return Response({'message': 'Checklist creation from template would be implemented here'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['get'], detail=False)
    def popular(self, request):
        """Get popular templates"""
        try:
            repo = StigTemplateRepository()
            templates = repo.find_popular_templates()
            serializer = self.get_serializer(templates, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['get'], detail=False)
    def usage_stats(self, request):
        """Get template usage statistics"""
        try:
            repo = StigTemplateRepository()
            stats = repo.get_template_usage_stats()
            return Response(stats)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ArtifactViewSet(viewsets.ModelViewSet):
    """ViewSet for Artifact aggregates"""

    queryset = Artifact.objects.all()
    serializer_class = ArtifactSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['system_group_id', 'artifact_type', 'security_level', 'is_active']
    search_fields = ['title', 'description', 'filename']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return Artifact.objects.filter(is_active=True)

    @action(detail=True, methods=['post'])
    def add_relationship(self, request, pk=None):
        """Add relationship to an artifact"""
        try:
            artifact = self.get_object()
            checklist_id = request.data.get('checklist_id')
            vulnerability_finding_id = request.data.get('vulnerability_finding_id')
            nessus_scan_id = request.data.get('nessus_scan_id')

            repo = ArtifactRepository()
            success = repo.add_relationship(
                uuid.UUID(pk),
                checklist_id=uuid.UUID(checklist_id) if checklist_id else None,
                vulnerability_finding_id=uuid.UUID(vulnerability_finding_id) if vulnerability_finding_id else None,
                nessus_scan_id=uuid.UUID(nessus_scan_id) if nessus_scan_id else None
            )

            if success:
                serializer = self.get_serializer(artifact)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Failed to add relationship'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def update_security(self, request, pk=None):
        """Update artifact security level"""
        try:
            security_level = request.data.get('security_level')
            access_list = request.data.get('access_list')

            if not security_level:
                return Response(
                    {'error': 'security_level is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            repo = ArtifactRepository()
            success = repo.update_security_level(uuid.UUID(pk), security_level, access_list)

            if success:
                artifact = self.get_object()
                serializer = self.get_serializer(artifact)
                return Response(serializer.data)
            else:
                return Response(
                    {'error': 'Failed to update security'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an artifact"""
        try:
            repo = ArtifactRepository()
            success = repo.deactivate_artifact(uuid.UUID(pk))

            if success:
                return Response({'message': 'Artifact deactivated successfully'})
            else:
                return Response(
                    {'error': 'Failed to deactivate artifact'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(methods=['get'], detail=False)
    def storage_stats(self, request):
        """Get artifact storage statistics"""
        try:
            system_group_id = request.query_params.get('system_group_id')
            system_group_uuid = uuid.UUID(system_group_id) if system_group_id else None

            repo = ArtifactRepository()
            stats = repo.get_storage_statistics(system_group_uuid)
            return Response(stats)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download artifact file"""
        try:
            artifact = self.get_object()

            # Check access (simplified)
            if not artifact.is_active:
                return Response(
                    {'error': 'Artifact is not active'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Return file URL or content
            if artifact.file_url:
                return Response({'download_url': artifact.file_url})
            else:
                return Response(
                    {'error': 'File not available'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
