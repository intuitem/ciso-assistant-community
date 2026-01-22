"""
Serializers for Risk Registers API
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError

from ..models.asset_risk import AssetRisk
from ..models.risk_register import RiskRegister


class AssetRiskSerializer(serializers.ModelSerializer):
    """Serializer for AssetRisk aggregate"""

    # Read-only computed fields
    risk_reduction_achieved = serializers.ReadOnlyField()
    is_treated = serializers.ReadOnlyField()
    requires_attention = serializers.ReadOnlyField()
    is_overdue_for_review = serializers.ReadOnlyField()
    treatment_completion_percentage = serializers.ReadOnlyField()

    # Custom field for CVSS scores
    cvss_scores = serializers.SerializerMethodField()

    class Meta:
        model = AssetRisk
        fields = [
            'id', 'asset_id', 'asset_name', 'risk_id', 'risk_title', 'risk_description',
            'risk_category', 'risk_subcategory', 'threat_source', 'threat_vector',
            'vulnerability_description', 'cve_ids', 'cwe_ids', 'cvss_base_score',
            'cvss_temporal_score', 'cvss_environmental_score', 'cvss_scores',
            'inherent_likelihood', 'inherent_impact', 'inherent_risk_score', 'inherent_risk_level',
            'residual_likelihood', 'residual_impact', 'residual_risk_score', 'residual_risk_level',
            'risk_appetite', 'risk_threshold', 'requires_treatment', 'treatment_strategy',
            'treatment_plan', 'treatment_owner_user_id', 'treatment_owner_username',
            'treatment_status', 'treatment_implemented_date', 'treatment_effective_date',
            'treatment_milestones', 'monitoring_frequency', 'last_review_date',
            'next_review_date', 'review_notes', 'risk_owner_user_id', 'risk_owner_username',
            'risk_manager_user_id', 'risk_manager_username', 'supporting_evidence',
            'related_findings', 'related_controls', 'tags', 'custom_fields',
            'assessed_by_user_id', 'assessed_by_username', 'assessment_methodology',
            'confidence_level', 'risk_reduction_achieved', 'is_treated', 'requires_attention',
            'is_overdue_for_review', 'treatment_completion_percentage',
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def get_cvss_scores(self, obj):
        """Return CVSS scores as a structured object"""
        return {
            'base': obj.cvss_base_score,
            'temporal': obj.cvss_temporal_score,
            'environmental': obj.cvss_environmental_score
        }

    def create(self, validated_data):
        """Create a new asset risk"""
        from ..services.risk_assessment_service import RiskAssessmentService

        service = RiskAssessmentService()
        risk = service.assess_asset_risk(
            asset_id=validated_data['asset_id'],
            assessment_data=validated_data,
            assessor_user_id=self.context['request'].user.id,
            assessor_username=self.context['request'].user.username
        )
        return risk

    def update(self, instance, validated_data):
        """Update an existing asset risk"""
        from ..services.risk_assessment_service import RiskAssessmentService

        service = RiskAssessmentService()
        risk = service.update_risk_assessment(
            risk_id=str(instance.id),
            update_data=validated_data,
            updated_by_user_id=self.context['request'].user.id,
            updated_by_username=self.context['request'].user.username
        )
        return risk


class RiskRegisterSerializer(serializers.ModelSerializer):
    """Serializer for RiskRegister aggregate"""

    # Read-only computed fields
    risk_distribution = serializers.ReadOnlyField()
    treatment_effectiveness = serializers.ReadOnlyField()
    risks_within_appetite = serializers.ReadOnlyField()
    risks_exceeding_appetite = serializers.ReadOnlyField()
    is_overdue_for_report = serializers.ReadOnlyField()
    is_overdue_for_review = serializers.ReadOnlyField()

    class Meta:
        model = RiskRegister
        fields = [
            'id', 'name', 'description', 'register_id', 'scope', 'owning_organization',
            'owner_user_id', 'owner_username', 'status', 'asset_risk_ids', 'third_party_risk_ids',
            'business_risk_ids', 'risk_scenario_ids', 'total_risks', 'critical_risks',
            'high_risks', 'moderate_risks', 'low_risks', 'risks_requiring_treatment',
            'risks_under_treatment', 'risks_effectively_treated', 'risk_appetite_statement',
            'risk_appetite_critical_threshold', 'risk_appetite_high_threshold',
            'risk_appetite_moderate_threshold', 'reporting_frequency', 'last_report_date',
            'next_report_date', 'last_review_date', 'next_review_date', 'risk_heat_map',
            'included_risk_categories', 'excluded_risk_categories', 'risk_scoring_methodology',
            'regulatory_requirements', 'compliance_frameworks', 'tags', 'custom_fields',
            'risk_distribution', 'treatment_effectiveness', 'risks_within_appetite',
            'risks_exceeding_appetite', 'is_overdue_for_report', 'is_overdue_for_review',
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def create(self, validated_data):
        """Create a new risk register"""
        risk_register = RiskRegister()
        risk_register.create_risk_register(
            register_id=validated_data['register_id'],
            name=validated_data['name'],
            scope=validated_data.get('scope', 'IT'),
            owner_user_id=validated_data.get('owner_user_id'),
            owner_username=validated_data.get('owner_username'),
            description=validated_data.get('description'),
            tags=validated_data.get('tags', [])
        )
        risk_register.save()
        return risk_register

    def update(self, instance, validated_data):
        """Update an existing risk register"""
        for attr in ['name', 'description', 'scope', 'owning_organization', 'status', 'tags']:
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])

        if 'owner_user_id' in validated_data:
            instance.owner_user_id = validated_data['owner_user_id']
            instance.owner_username = validated_data.get('owner_username')

        instance.save()
        return instance


class RiskAssessmentRequestSerializer(serializers.Serializer):
    """Serializer for risk assessment requests"""

    asset_id = serializers.UUIDField(required=True)
    asset_name = serializers.CharField(max_length=255, required=True)
    risk_title = serializers.CharField(max_length=500, required=True)
    risk_description = serializers.CharField(required=True)
    risk_category = serializers.ChoiceField(
        choices=[
            ('confidentiality', 'Confidentiality'),
            ('integrity', 'Integrity'),
            ('availability', 'Availability'),
            ('financial', 'Financial'),
            ('reputational', 'Reputational'),
            ('operational', 'Operational'),
            ('compliance', 'Compliance'),
            ('strategic', 'Strategic'),
        ],
        default='operational'
    )
    inherent_likelihood = serializers.IntegerField(min_value=1, max_value=5, default=3)
    inherent_impact = serializers.IntegerField(min_value=1, max_value=5, default=3)
    risk_threshold = serializers.IntegerField(min_value=1, max_value=25, default=3)
    risk_appetite = serializers.ChoiceField(
        choices=[
            ('very_low', 'Very Low'),
            ('low', 'Low'),
            ('moderate', 'Moderate'),
            ('high', 'High'),
            ('very_high', 'Very High'),
        ],
        default='moderate'
    )
    threat_source = serializers.CharField(max_length=255, required=False, allow_blank=True)
    threat_vector = serializers.CharField(max_length=255, required=False, allow_blank=True)
    vulnerability_description = serializers.CharField(required=False, allow_blank=True)
    cve_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    cwe_ids = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    cvss_base_score = serializers.FloatField(min_value=0.0, max_value=10.0, required=False)
    temporal_metrics = serializers.DictField(required=False)
    environmental_metrics = serializers.DictField(required=False)
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class ControlEffectivenessAssessmentSerializer(serializers.Serializer):
    """Serializer for control effectiveness assessments"""

    control_assessments = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )

    def validate_control_assessments(self, value):
        """Validate control assessment data"""
        for assessment in value:
            if 'effectiveness' not in assessment:
                raise serializers.ValidationError("Each control assessment must include 'effectiveness'")
            effectiveness = assessment['effectiveness']
            if not isinstance(effectiveness, (int, float)) or effectiveness < 0 or effectiveness > 100:
                raise serializers.ValidationError("'effectiveness' must be a number between 0 and 100")
        return value


class RiskTreatmentPlanSerializer(serializers.Serializer):
    """Serializer for risk treatment plan updates"""

    treatment_strategy = serializers.ChoiceField(
        choices=[
            ('accept', 'Accept'),
            ('avoid', 'Avoid'),
            ('mitigate', 'Mitigate'),
            ('transfer', 'Transfer'),
            ('monitor', 'Monitor Only'),
        ],
        required=True
    )
    treatment_plan = serializers.CharField(required=True)
    treatment_owner_user_id = serializers.UUIDField(required=True)
    treatment_owner_username = serializers.CharField(max_length=150, required=True)


class RiskMilestoneSerializer(serializers.Serializer):
    """Serializer for risk treatment milestones"""

    description = serializers.CharField(required=True)
    target_date = serializers.DateField(required=True)
    status = serializers.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )


class RiskReviewSerializer(serializers.Serializer):
    """Serializer for risk review updates"""

    review_notes = serializers.CharField(required=False, allow_blank=True)
    next_review_date = serializers.DateField(required=False)


class RiskOwnerAssignmentSerializer(serializers.Serializer):
    """Serializer for risk ownership assignments"""

    owner_user_id = serializers.UUIDField(required=True)
    owner_username = serializers.CharField(max_length=150, required=True)
    manager_user_id = serializers.UUIDField(required=False)
    manager_username = serializers.CharField(max_length=150, required=False, allow_blank=True)


class RiskStatusChangeSerializer(serializers.Serializer):
    """Serializer for risk status changes"""

    new_status = serializers.ChoiceField(
        choices=[
            ('planned', 'Planned'),
            ('in_progress', 'In Progress'),
            ('implemented', 'Implemented'),
            ('effective', 'Effective'),
            ('ineffective', 'Ineffective'),
        ],
        required=True
    )
    finding_details = serializers.CharField(required=False, allow_blank=True)
    comments = serializers.CharField(required=False, allow_blank=True)


class BulkRiskUpdateSerializer(serializers.Serializer):
    """Serializer for bulk risk updates"""

    risk_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )
    update_type = serializers.ChoiceField(
        choices=[
            ('treatment_status', 'Treatment Status'),
            ('owner_assignment', 'Owner Assignment'),
            ('risk_level', 'Risk Level Update'),
        ],
        required=True
    )
    update_data = serializers.DictField(required=True)


class RiskScenarioGenerationSerializer(serializers.Serializer):
    """Serializer for risk scenario generation"""

    threat_actors = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    attack_vectors = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )
    vulnerabilities = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )


class RiskDashboardSerializer(serializers.Serializer):
    """Serializer for risk dashboard requests"""

    scope = serializers.ChoiceField(
        choices=[
            ('enterprise', 'Enterprise'),
            ('asset', 'Asset'),
            ('register', 'Register'),
        ],
        default='enterprise'
    )
    asset_id = serializers.UUIDField(required=False)
    register_id = serializers.CharField(max_length=100, required=False)
    months = serializers.IntegerField(min_value=1, max_value=24, default=12)
    top_risks_limit = serializers.IntegerField(min_value=1, max_value=100, default=20)


class RiskReportSerializer(serializers.Serializer):
    """Serializer for risk report generation"""

    register_id = serializers.CharField(max_length=100, required=True)
    report_type = serializers.ChoiceField(
        choices=[
            ('comprehensive', 'Comprehensive'),
            ('executive', 'Executive'),
            ('technical', 'Technical'),
        ],
        default='comprehensive'
    )
    filters = serializers.DictField(required=False, default=dict)


class RiskHeatMapSerializer(serializers.Serializer):
    """Serializer for risk heat map requests"""

    scope = serializers.ChoiceField(
        choices=[
            ('enterprise', 'Enterprise'),
            ('asset', 'Asset'),
            ('register', 'Register'),
        ],
        default='enterprise'
    )
    asset_id = serializers.UUIDField(required=False)
    register_id = serializers.CharField(max_length=100, required=False)
