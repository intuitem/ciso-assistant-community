"""
DRF Serializers for POAM module
"""

from rest_framework import serializers
from ..models.poam_item import POAMItem


class POAMItemSerializer(serializers.ModelSerializer):
    """Serializer for POAMItem aggregate"""

    # Computed fields
    is_overdue = serializers.ReadOnlyField()
    days_overdue = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()
    upcoming_milestones = serializers.ReadOnlyField()
    overdue_milestones = serializers.ReadOnlyField()

    class Meta:
        model = POAMItem
        fields = [
            'id', 'version', 'created_at', 'updated_at',
            'weakness_id', 'title', 'description',
            'source_type', 'source_reference',
            'system_group_id', 'assessment_id', 'vulnerability_finding_id',
            'control_id', 'cci_ids',
            'risk_level', 'impact_description', 'likelihood',
            'status',
            'identified_date', 'submitted_date', 'approved_date',
            'estimated_completion_date', 'actual_completion_date',
            'responsible_organization', 'point_of_contact',
            'contact_email', 'contact_phone',
            'remediation_plan', 'resources_required', 'estimated_cost',
            'milestones',
            'has_deviation', 'deviation_justification',
            'deviation_approved', 'deviation_approval_date',
            'evidence_before', 'evidence_after', 'supporting_documents',
            'comments', 'tags',
            'last_reviewed_date', 'next_review_date',
            'is_recurring',
            'is_overdue', 'days_overdue', 'completion_percentage',
            'upcoming_milestones', 'overdue_milestones',
        ]
        read_only_fields = [
            'id', 'version', 'created_at', 'updated_at',
            'submitted_date', 'approved_date', 'actual_completion_date',
            'deviation_approval_date',
        ]

    def create(self, validated_data):
        """Create a new POAM item"""
        poam = POAMItem()
        poam.create_poam_item(
            weakness_id=validated_data['weakness_id'],
            title=validated_data['title'],
            description=validated_data['description'],
            system_group_id=validated_data['system_group_id'],
            risk_level=validated_data.get('risk_level', 'moderate'),
            source_type=validated_data.get('source_type', 'assessment'),
            tags=validated_data.get('tags', [])
        )

        # Set additional fields
        for field in ['source_reference', 'assessment_id', 'vulnerability_finding_id',
                     'control_id', 'cci_ids', 'impact_description', 'likelihood',
                     'estimated_completion_date', 'responsible_organization',
                     'point_of_contact', 'contact_email', 'contact_phone',
                     'remediation_plan', 'resources_required', 'estimated_cost',
                     'is_recurring', 'comments']:
            if field in validated_data:
                setattr(poam, field, validated_data[field])

        poam.save()
        return poam

    def update(self, instance, validated_data):
        """Update an existing POAM item"""
        for field in ['title', 'description', 'source_type', 'source_reference',
                     'control_id', 'cci_ids', 'risk_level', 'impact_description',
                     'likelihood', 'estimated_completion_date',
                     'responsible_organization', 'point_of_contact',
                     'contact_email', 'contact_phone', 'remediation_plan',
                     'resources_required', 'estimated_cost', 'comments', 'tags',
                     'is_recurring']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance


class MilestoneSerializer(serializers.Serializer):
    """Serializer for milestone data"""
    description = serializers.CharField()
    target_date = serializers.DateField()
    status = serializers.CharField(default='pending')


class EvidenceSerializer(serializers.Serializer):
    """Serializer for evidence data"""
    evidence_type = serializers.ChoiceField(
        choices=['before_remediation', 'after_remediation', 'supporting']
    )
    evidence_data = serializers.JSONField()
