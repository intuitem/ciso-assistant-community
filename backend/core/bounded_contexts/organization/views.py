"""
API Views for Organization bounded context
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .aggregates.org_unit import OrgUnit
from .aggregates.user import User
from .aggregates.group import Group
from .associations.responsibility_assignment import ResponsibilityAssignment
from .serializers import (
    OrgUnitSerializer,
    UserSerializer,
    GroupSerializer,
    ResponsibilityAssignmentSerializer,
)


class OrgUnitViewSet(viewsets.ModelViewSet):
    """ViewSet for OrgUnit aggregates"""
    
    queryset = OrgUnit.objects.all()
    serializer_class = OrgUnitSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'parentOrgUnitId']
    search_fields = ['name', 'ref_id', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an organizational unit"""
        org_unit = self.get_object()
        org_unit.activate()
        org_unit.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def retire(self, request, pk=None):
        """Retire an organizational unit"""
        org_unit = self.get_object()
        org_unit.retire()
        org_unit.save()
        return Response({'status': 'retired'})
    
    @action(detail=True, methods=['post'])
    def add_child(self, request, pk=None):
        """Add a child organizational unit"""
        org_unit = self.get_object()
        child_id = request.data.get('child_id')
        if child_id:
            org_unit.add_child(child_id)
            org_unit.save()
            return Response({'status': 'child added'})
        return Response({'error': 'child_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def assign_owner(self, request, pk=None):
        """Assign an owner to organizational unit"""
        org_unit = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            org_unit.assign_owner(user_id)
            org_unit.save()
            return Response({'status': 'owner assigned'})
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for User aggregates"""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state']
    search_fields = ['email', 'display_name', 'first_name', 'last_name']
    ordering_fields = ['email', 'display_name', 'created_at']
    ordering = ['email']
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user"""
        user = self.get_object()
        user.activate()
        user.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """Disable a user"""
        user = self.get_object()
        user.disable()
        user.save()
        return Response({'status': 'disabled'})
    
    @action(detail=True, methods=['post'])
    def assign_to_group(self, request, pk=None):
        """Assign user to a group"""
        user = self.get_object()
        group_id = request.data.get('group_id')
        if group_id:
            user.assign_to_group(group_id)
            user.save()
            return Response({'status': 'assigned to group'})
        return Response({'error': 'group_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def assign_to_org_unit(self, request, pk=None):
        """Assign user to an organizational unit"""
        user = self.get_object()
        org_unit_id = request.data.get('org_unit_id')
        if org_unit_id:
            user.assign_to_org_unit(org_unit_id)
            user.save()
            return Response({'status': 'assigned to org unit'})
        return Response({'error': 'org_unit_id required'}, status=status.HTTP_400_BAD_REQUEST)


class GroupViewSet(viewsets.ModelViewSet):
    """ViewSet for Group aggregates"""
    
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['lifecycle_state', 'builtin']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        """Add a permission to a group"""
        group = self.get_object()
        permission_id = request.data.get('permission_id')
        if permission_id:
            group.add_permission(permission_id)
            group.save()
            return Response({'status': 'permission added'})
        return Response({'error': 'permission_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        """Add a user to a group"""
        group = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            group.add_user(user_id)
            group.save()
            return Response({'status': 'user added'})
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)


class ResponsibilityAssignmentViewSet(viewsets.ModelViewSet):
    """ViewSet for ResponsibilityAssignment associations"""
    
    queryset = ResponsibilityAssignment.objects.all()
    serializer_class = ResponsibilityAssignmentSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject_type', 'userId', 'role']
    search_fields = ['role', 'notes']
    ordering_fields = ['created_at', 'start_date']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke a responsibility assignment"""
        assignment = self.get_object()
        assignment.revoke()
        assignment.save()
        return Response({'status': 'revoked'})

