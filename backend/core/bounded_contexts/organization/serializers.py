"""
Serializers for Organization bounded context
"""

from rest_framework import serializers
from .aggregates.org_unit import OrgUnit
from .aggregates.user import User
from .aggregates.group import Group
from .associations.responsibility_assignment import ResponsibilityAssignment


class OrgUnitSerializer(serializers.ModelSerializer):
    """Serializer for OrgUnit aggregate"""
    
    class Meta:
        model = OrgUnit
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description', 'ref_id',
            'lifecycle_state',
            'parentOrgUnitId', 'childOrgUnitIds', 'ownerUserIds',
            'tags',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User aggregate"""
    
    class Meta:
        model = User
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'email', 'display_name', 'first_name', 'last_name',
            'lifecycle_state',
            'groupIds', 'orgUnitIds',
            'preferences', 'expiry_date', 'observation',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']
        extra_kwargs = {
            'password': {'write_only': True, 'required': False}
        }


class GroupSerializer(serializers.ModelSerializer):
    """Serializer for Group aggregate"""
    
    class Meta:
        model = Group
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'name', 'description',
            'lifecycle_state',
            'permissionIds', 'userIds',
            'builtin',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class ResponsibilityAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for ResponsibilityAssignment association"""
    
    class Meta:
        model = ResponsibilityAssignment
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'subject_type', 'subject_id',
            'userId', 'role',
            'start_date', 'end_date',
            'notes',
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']

