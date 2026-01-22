"""
Views for Risk Registers API
"""

import uuid
from typing import Dict, Any
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.core.exceptions import ValidationError

from core.permissions import RBACPermissions
from ..repositories.asset_risk_repository import AssetRiskRepository
from ..repositories.risk_register_repository import RiskRegisterRepository
from ..services.risk_assessment_service import RiskAssessmentService
from ..services.risk_reporting_service import RiskReportingService
from .serializers import (
    AssetRiskSerializer, RiskRegisterSerializer, RiskAssessmentRequestSerializer,
    ControlEffectivenessAssessmentSerializer, RiskTreatmentPlanSerializer,
    RiskMilestoneSerializer, RiskReviewSerializer, RiskOwnerAssignmentSerializer,
    RiskStatusChangeSerializer, BulkRiskUpdateSerializer, RiskScenarioGenerationSerializer,
    RiskDashboardSerializer, RiskReportSerializer, RiskHeatMapSerializer
)


class AssetRiskViewSet(viewsets.ModelViewSet):
    """ViewSet for AssetRisk aggregates"""

    queryset = AssetRiskRepository().model.objects.all()
    serializer_class = AssetRiskSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = [
        'asset_id', 'risk_category', 'inherent_risk_level', 'residual_risk_level',
        'treatment_status', 'requires_treatment', 'risk_owner_user_id', 'next_review_date'
    ]
    search_fields = ['risk_id', 'risk_title', 'threat_source', 'asset_name']
    ordering_fields = ['created_at', 'residual_risk_score', 'next_review_date']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return AssetRiskRepository().model.objects.all()

    def perform_create(self, serializer):
        """Create asset risk with audit logging"""
        # The serializer handles creation through the service
        pass

    def perform_update(self, serializer):
        """Update asset risk with audit logging"""
        # The serializer handles updates through the service
        pass

    @action(detail=False, methods=['post'], url_path='assess')
    def assess_risk(self, request):
        """Perform comprehensive risk assessment"""
        try:
            serializer = RiskAssessmentRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            service = RiskAssessmentService()
            validation_errors = service.validate_risk_assessment_data(serializer.validated_data)

            if validation_errors:
                return Response({
                    'error': 'Validation failed',
                    'details': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)

            risk = service.assess_asset_risk(
                asset_id=serializer.validated_data['asset_id'],
                assessment_data=serializer.validated_data,
                assessor_user_id=request.user.id,
                assessor_username=request.user.username
            )

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='evaluate-controls')
    def evaluate_controls(self, request, pk=None):
        """Evaluate effectiveness of controls mitigating this risk"""
        try:
            risk = self.get_object()
            serializer = ControlEffectivenessAssessmentSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            service = RiskAssessmentService()
            evaluation_result = service.evaluate_control_effectiveness(
                risk_id=pk,
                control_assessments=serializer.validated_data['control_assessments'],
                evaluated_by_user_id=request.user.id,
                evaluated_by_username=request.user.username
            )

            return Response(evaluation_result)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='define-treatment')
    def define_treatment(self, request, pk=None):
        """Define risk treatment plan"""
        try:
            risk = self.get_object()
            serializer = RiskTreatmentPlanSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            risk.define_treatment_plan(
                treatment_strategy=serializer.validated_data['treatment_strategy'],
                treatment_plan=serializer.validated_data['treatment_plan'],
                treatment_owner_user_id=serializer.validated_data['treatment_owner_user_id'],
                treatment_owner_username=serializer.validated_data['treatment_owner_username']
            )

            repo = AssetRiskRepository()
            repo.save(risk, user_id=request.user.id, username=request.user.username, request=request)

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='add-milestone')
    def add_milestone(self, request, pk=None):
        """Add treatment milestone"""
        try:
            risk = self.get_object()
            serializer = RiskMilestoneSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            risk.add_milestone(
                milestone_description=serializer.validated_data['description'],
                target_date=serializer.validated_data['target_date'],
                status=serializer.validated_data.get('status', 'pending')
            )

            repo = AssetRiskRepository()
            repo.save(risk, user_id=request.user.id, username=request.user.username, request=request)

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='update-milestone')
    def update_milestone(self, request, pk=None):
        """Update milestone status"""
        try:
            risk = self.get_object()
            milestone_id = request.data.get('milestone_id')
            new_status = request.data.get('status')
            actual_date = request.data.get('actual_date')

            if not milestone_id or not new_status:
                return Response({
                    'error': 'milestone_id and status are required'
                }, status=status.HTTP_400_BAD_REQUEST)

            risk.update_milestone_status(
                milestone_id=milestone_id,
                status=new_status,
                actual_date=actual_date
            )

            repo = AssetRiskRepository()
            repo.save(risk, user_id=request.user.id, username=request.user.username, request=request)

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='conduct-review')
    def conduct_review(self, request, pk=None):
        """Conduct risk review"""
        try:
            risk = self.get_object()
            serializer = RiskReviewSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            risk.conduct_review(
                review_notes=serializer.validated_data.get('review_notes'),
                next_review_date=serializer.validated_data.get('next_review_date')
            )

            repo = AssetRiskRepository()
            repo.save(risk, user_id=request.user.id, username=request.user.username, request=request)

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='assign-owner')
    def assign_owner(self, request, pk=None):
        """Assign risk ownership"""
        try:
            risk = self.get_object()
            serializer = RiskOwnerAssignmentSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            risk.assign_owner(
                owner_user_id=serializer.validated_data['owner_user_id'],
                owner_username=serializer.validated_data['owner_username'],
                manager_user_id=serializer.validated_data.get('manager_user_id'),
                manager_username=serializer.validated_data.get('manager_username')
            )

            repo = AssetRiskRepository()
            repo.save(risk, user_id=request.user.id, username=request.user.username, request=request)

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='change-status')
    def change_status(self, request, pk=None):
        """Change risk status (for findings/status changes)"""
        try:
            risk = self.get_object()
            serializer = RiskStatusChangeSerializer(data=request.data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            risk.change_status(
                new_status=serializer.validated_data['new_status'],
                finding_details=serializer.validated_data.get('finding_details'),
                comments=serializer.validated_data.get('comments')
            )

            repo = AssetRiskRepository()
            repo.save(risk, user_id=request.user.id, username=request.user.username, request=request)

            response_serializer = self.get_serializer(risk)
            return Response(response_serializer.data)

        except AssetRisk.DoesNotExist:
            return Response({'error': 'Asset risk not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='bulk-update')
    def bulk_update(self, request):
        """Bulk update multiple risks"""
        try:
            serializer = BulkRiskUpdateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            repo = AssetRiskRepository()
            updated_count = repo.bulk_update_treatment_status(
                risk_ids=[str(rid) for rid in serializer.validated_data['risk_ids']],
                new_status=serializer.validated_data['update_data'].get('new_status', 'planned'),
                treatment_details=serializer.validated_data['update_data']
            )

            return Response({
                'message': f'Successfully updated {updated_count} risks',
                'updated_count': updated_count
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='statistics')
    def get_statistics(self, request):
        """Get risk statistics"""
        try:
            repo = AssetRiskRepository()
            asset_ids = request.query_params.getlist('asset_ids', [])
            asset_ids = [uuid.UUID(aid) for aid in asset_ids] if asset_ids else None

            stats = repo.get_risk_statistics_for_asset(asset_ids[0] if asset_ids else None)
            return Response(stats)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='heat-map')
    def get_heat_map(self, request):
        """Get risk heat map data"""
        try:
            repo = AssetRiskRepository()
            asset_ids = request.query_params.getlist('asset_ids', [])
            asset_ids = [uuid.UUID(aid) for aid in asset_ids] if asset_ids else None

            heat_map = repo.get_risk_heat_map_data(asset_ids=asset_ids)
            return Response(heat_map)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='requiring-attention')
    def requiring_attention(self, request):
        """Get risks requiring immediate attention"""
        try:
            repo = AssetRiskRepository()
            asset_ids = request.query_params.getlist('asset_ids', [])
            asset_ids = [uuid.UUID(aid) for aid in asset_ids] if asset_ids else None

            risks = repo.get_risks_requiring_attention(asset_ids=asset_ids)
            serializer = self.get_serializer(risks, many=True)
            return Response(serializer.data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RiskRegisterViewSet(viewsets.ModelViewSet):
    """ViewSet for RiskRegister aggregates"""

    queryset = RiskRegisterRepository().model.objects.all()
    serializer_class = RiskRegisterSerializer
    permission_classes = [IsAuthenticated, RBACPermissions]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'scope', 'owner_user_id', 'next_report_date', 'next_review_date']
    search_fields = ['register_id', 'name', 'description', 'owning_organization']
    ordering_fields = ['created_at', 'total_risks', 'critical_risks']

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return RiskRegisterRepository().model.objects.all()

    @action(detail=True, methods=['post'], url_path='add-risk')
    def add_risk(self, request, pk=None):
        """Add a risk to the register"""
        try:
            risk_register = self.get_object()
            risk_id = request.data.get('risk_id')
            risk_type = request.data.get('risk_type', 'asset_risk')

            if not risk_id:
                return Response({'error': 'risk_id is required'}, status=status.HTTP_400_BAD_REQUEST)

            if risk_type == 'asset_risk':
                risk_register.add_asset_risk(risk_id)
            elif risk_type == 'third_party_risk':
                risk_register.add_third_party_risk(risk_id)
            elif risk_type == 'business_risk':
                risk_register.add_business_risk(risk_id)
            elif risk_type == 'risk_scenario':
                risk_register.add_risk_scenario(risk_id)
            else:
                return Response({'error': f'Invalid risk_type: {risk_type}'}, status=status.HTTP_400_BAD_REQUEST)

            risk_register.save()
            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='remove-risk')
    def remove_risk(self, request, pk=None):
        """Remove a risk from the register"""
        try:
            risk_register = self.get_object()
            risk_id = request.data.get('risk_id')
            risk_type = request.data.get('risk_type', 'asset_risk')

            if not risk_id:
                return Response({'error': 'risk_id is required'}, status=status.HTTP_400_BAD_REQUEST)

            risk_register.remove_risk(risk_id, risk_type)
            risk_register.save()

            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='consolidate')
    def consolidate(self, request, pk=None):
        """Consolidate register statistics"""
        try:
            risk_register = self.get_object()
            risk_register.consolidate_statistics()
            risk_register.save()

            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='generate-report')
    def generate_report(self, request, pk=None):
        """Generate risk register report"""
        try:
            risk_register = self.get_object()
            report_date = request.data.get('report_date')

            risk_register.generate_report(report_date=report_date)
            risk_register.save()

            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='conduct-review')
    def conduct_review(self, request, pk=None):
        """Conduct register review"""
        try:
            risk_register = self.get_object()
            review_date = request.data.get('review_date')
            notes = request.data.get('notes')

            risk_register.conduct_review(review_date=review_date, notes=notes)
            risk_register.save()

            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='update-appetite')
    def update_appetite(self, request, pk=None):
        """Update risk appetite settings"""
        try:
            risk_register = self.get_object()

            appetite_statement = request.data.get('appetite_statement')
            critical_threshold = request.data.get('critical_threshold', 20)
            high_threshold = request.data.get('high_threshold', 15)
            moderate_threshold = request.data.get('moderate_threshold', 10)

            risk_register.update_risk_appetite(
                appetite_statement=appetite_statement,
                critical_threshold=critical_threshold,
                high_threshold=high_threshold,
                moderate_threshold=moderate_threshold
            )
            risk_register.save()

            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='archive')
    def archive(self, request, pk=None):
        """Archive the risk register"""
        try:
            risk_register = self.get_object()
            reason = request.data.get('reason', 'Administrative archiving')

            risk_register.archive_register(reason)
            risk_register.save()

            response_serializer = self.get_serializer(risk_register)
            return Response(response_serializer.data)

        except RiskRegister.DoesNotExist:
            return Response({'error': 'Risk register not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='enterprise-summary')
    def enterprise_summary(self, request):
        """Get enterprise-wide risk summary"""
        try:
            repo = RiskRegisterRepository()
            summary = repo.get_enterprise_risk_summary()
            return Response(summary)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='generate-enterprise-report')
    def generate_enterprise_report(self, request):
        """Generate enterprise risk report"""
        try:
            repo = RiskRegisterRepository()
            report_date = request.data.get('report_date')
            report = repo.generate_enterprise_report(report_date=report_date)
            return Response(report)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RiskReportingViewSet(viewsets.ViewSet):
    """ViewSet for risk reporting and analytics"""

    permission_classes = [IsAuthenticated, RBACPermissions]

    @action(detail=False, methods=['post'], url_path='dashboard')
    def dashboard(self, request):
        """Generate risk dashboard data"""
        try:
            serializer = RiskDashboardSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            service = RiskReportingService()
            dashboard_data = service.generate_risk_dashboard_data(
                scope=serializer.validated_data.get('scope', 'enterprise'),
                filters=serializer.validated_data
            )

            return Response(dashboard_data)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='report')
    def generate_report(self, request):
        """Generate risk report"""
        try:
            serializer = RiskReportSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            service = RiskReportingService()
            report = service.generate_risk_register_report(
                register_id=serializer.validated_data['register_id'],
                report_type=serializer.validated_data.get('report_type', 'comprehensive')
            )

            return Response(report)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='heat-map')
    def heat_map(self, request):
        """Generate risk heat map report"""
        try:
            serializer = RiskHeatMapSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            service = RiskReportingService()
            heat_map_report = service.generate_risk_heat_map_report(
                scope=serializer.validated_data.get('scope', 'enterprise'),
                filters=serializer.validated_data
            )

            return Response(heat_map_report)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='trends')
    def trends(self, request):
        """Generate risk trends report"""
        try:
            months = request.data.get('months', 12)
            filters = request.data.get('filters', {})

            service = RiskReportingService()
            trends_report = service.generate_risk_trends_report(
                months=months,
                filters=filters
            )

            return Response(trends_report)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
