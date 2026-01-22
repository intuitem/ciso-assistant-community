"""
API Views for SecurityOperations bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.security_incident import SecurityIncident
from .aggregates.awareness_program import AwarenessProgram
from .associations.awareness_campaign import AwarenessCampaign
from .associations.awareness_completion import AwarenessCompletion
from .serializers import (
    SecurityIncidentSerializer,
    AwarenessProgramSerializer,
    AwarenessCampaignSerializer,
    AwarenessCompletionSerializer,
)


class SecurityIncidentViewSet(viewsets.ModelViewSet):
    """ViewSet for SecurityIncident aggregates"""
    
    queryset = SecurityIncident.objects.all()
    serializer_class = SecurityIncidentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'severity', 'detection_source']
    search_fields = ['title', 'description']
    ordering_fields = ['reported_at', 'severity']
    ordering = ['-reported_at']
    
    @action(detail=True, methods=['post'])
    def triage(self, request, pk=None):
        """Triage an incident"""
        incident = self.get_object()
        notes = request.data.get('notes')
        incident.triage(notes)
        incident.save()
        return Response({'status': 'triaged'})
    
    @action(detail=True, methods=['post'])
    def contain(self, request, pk=None):
        """Contain an incident"""
        incident = self.get_object()
        notes = request.data.get('notes')
        incident.contain(notes)
        incident.save()
        return Response({'status': 'contained'})
    
    @action(detail=True, methods=['post'])
    def eradicate(self, request, pk=None):
        """Eradicate an incident"""
        incident = self.get_object()
        notes = request.data.get('notes')
        incident.eradicate(notes)
        incident.save()
        return Response({'status': 'eradicated'})
    
    @action(detail=True, methods=['post'])
    def recover(self, request, pk=None):
        """Recover from an incident"""
        incident = self.get_object()
        notes = request.data.get('notes')
        incident.recover(notes)
        incident.save()
        return Response({'status': 'recovered'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an incident"""
        incident = self.get_object()
        notes = request.data.get('notes')
        incident.close(notes)
        incident.save()
        return Response({'status': 'closed'})
    
    @action(detail=True, methods=['post'])
    def add_timeline_event(self, request, pk=None):
        """Add a timeline event"""
        incident = self.get_object()
        action = request.data.get('action')
        actor_user_id = request.data.get('actor_user_id')
        notes = request.data.get('notes')
        if action:
            incident.add_timeline_event(action, actor_user_id, notes)
            incident.save()
            return Response({'status': 'event added'})
        return Response({'error': 'action required'}, status=status.HTTP_400_BAD_REQUEST)


class AwarenessProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for AwarenessProgram aggregates"""
    
    queryset = AwarenessProgram.objects.all()
    serializer_class = AwarenessProgramSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a program"""
        program = self.get_object()
        program.activate()
        program.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """Pause a program"""
        program = self.get_object()
        program.pause()
        program.save()
        return Response({'status': 'paused'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire a program"""
        program = self.get_object()
        program.retire()
        program.save()
        return Response({'status': 'retired'})


class AwarenessCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for AwarenessCampaign associations"""
    
    queryset = AwarenessCampaign.objects.all()
    serializer_class = AwarenessCampaignSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['programId', 'lifecycle_state']
    search_fields = ['name', 'description']
    ordering_fields = ['start_date', 'created_at']
    ordering = ['-start_date']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a campaign"""
        campaign = self.get_object()
        campaign.start()
        campaign.save()
        return Response({'status': 'started'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a campaign"""
        from datetime import date
        campaign = self.get_object()
        end_date = request.data.get('end_date')
        end_date_obj = None
        if end_date:
            from datetime import datetime
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
        campaign.complete(end_date_obj)
        campaign.save()
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a campaign"""
        campaign = self.get_object()
        campaign.cancel()
        campaign.save()
        return Response({'status': 'cancelled'})


class AwarenessCompletionViewSet(viewsets.ModelViewSet):
    """ViewSet for AwarenessCompletion associations"""
    
    queryset = AwarenessCompletion.objects.all()
    serializer_class = AwarenessCompletionSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['campaignId', 'userId', 'status']
    search_fields = ['notes']
    ordering_fields = ['completed_at', 'created_at']
    ordering = ['-completed_at']
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a completion"""
        completion = self.get_object()
        completion.start()
        completion.save()
        return Response({'status': 'started'})
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an awareness activity"""
        completion = self.get_object()
        score = request.data.get('score')
        notes = request.data.get('notes')
        completion.complete(score, notes)
        completion.save()
        return Response({'status': 'completed'})
    
    @action(detail=True, methods=['post'])
    def fail(self, request, pk=None):
        """Mark as failed"""
        completion = self.get_object()
        notes = request.data.get('notes')
        completion.fail(notes)
        completion.save()
        return Response({'status': 'failed'})

