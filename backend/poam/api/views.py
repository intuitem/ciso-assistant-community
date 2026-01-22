"""
API Views for POAM module
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from ..models.poam_item import POAMItem
from .serializers import POAMItemSerializer, MilestoneSerializer, EvidenceSerializer


class POAMItemViewSet(viewsets.ModelViewSet):
    """ViewSet for POAMItem aggregates"""

    queryset = POAMItem.objects.all()
    serializer_class = POAMItemSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['system_group_id', 'status', 'risk_level', 'source_type', 'is_recurring']
    search_fields = ['weakness_id', 'title', 'description', 'control_id']
    ordering_fields = ['created_at', 'estimated_completion_date', 'risk_level', 'status']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit POAM item for approval"""
        poam = self.get_object()
        poam.submit_for_approval()
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve the POAM item"""
        poam = self.get_object()
        poam.approve_poam()
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject the POAM item"""
        poam = self.get_object()
        reason = request.data.get('reason', '')
        if not reason:
            return Response({'error': 'reason required'}, status=status.HTTP_400_BAD_REQUEST)
        poam.reject_poam(reason)
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def start_remediation(self, request, pk=None):
        """Start remediation"""
        poam = self.get_object()
        poam.start_remediation()
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def complete_remediation(self, request, pk=None):
        """Complete remediation"""
        poam = self.get_object()
        evidence = request.data.get('evidence', [])
        poam.complete_remediation(evidence)
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_milestone(self, request, pk=None):
        """Add a milestone"""
        poam = self.get_object()
        milestone_serializer = MilestoneSerializer(data=request.data)
        if milestone_serializer.is_valid():
            poam.add_milestone(
                description=milestone_serializer.validated_data['description'],
                target_date=milestone_serializer.validated_data['target_date'],
                status=milestone_serializer.validated_data.get('status', 'pending')
            )
            poam.save()
            serializer = self.get_serializer(poam)
            return Response(serializer.data)
        return Response(milestone_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def update_milestone(self, request, pk=None):
        """Update a milestone"""
        poam = self.get_object()
        milestone_id = request.data.get('milestone_id')
        milestone_status = request.data.get('status')
        actual_date = request.data.get('actual_date')
        if not milestone_id or not milestone_status:
            return Response(
                {'error': 'milestone_id and status required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        poam.update_milestone(milestone_id, milestone_status, actual_date)
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def request_deviation(self, request, pk=None):
        """Request a deviation"""
        poam = self.get_object()
        justification = request.data.get('justification')
        if not justification:
            return Response({'error': 'justification required'}, status=status.HTTP_400_BAD_REQUEST)
        poam.request_deviation(justification)
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve_deviation(self, request, pk=None):
        """Approve a deviation request"""
        poam = self.get_object()
        poam.approve_deviation()
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_evidence(self, request, pk=None):
        """Add evidence"""
        poam = self.get_object()
        evidence_serializer = EvidenceSerializer(data=request.data)
        if evidence_serializer.is_valid():
            poam.add_evidence(
                evidence_type=evidence_serializer.validated_data['evidence_type'],
                evidence_data=evidence_serializer.validated_data['evidence_data']
            )
            poam.save()
            serializer = self.get_serializer(poam)
            return Response(serializer.data)
        return Response(evidence_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def schedule_review(self, request, pk=None):
        """Schedule next review"""
        poam = self.get_object()
        review_date = request.data.get('review_date')
        if not review_date:
            return Response({'error': 'review_date required'}, status=status.HTTP_400_BAD_REQUEST)
        from datetime import datetime
        review_date_obj = datetime.fromisoformat(review_date).date()
        poam.schedule_review(review_date_obj)
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        """Mark as reviewed"""
        poam = self.get_object()
        poam.mark_reviewed()
        poam.save()
        serializer = self.get_serializer(poam)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue POAM items"""
        from django.utils import timezone
        overdue_items = POAMItem.objects.filter(
            estimated_completion_date__lt=timezone.now().date(),
            status__in=['draft', 'submitted', 'approved', 'in_progress']
        )
        serializer = self.get_serializer(overdue_items, many=True)
        return Response(serializer.data)
