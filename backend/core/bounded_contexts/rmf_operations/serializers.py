"""
DRF Serializers for RMF Operations bounded context
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError

from ..aggregates.system_group import SystemGroup
from ..aggregates.stig_checklist import StigChecklist
from ..aggregates.vulnerability_finding import VulnerabilityFinding
from ..aggregates.checklist_score import ChecklistScore
from ..aggregates.nessus_scan import NessusScan
from ..aggregates.stig_template import StigTemplate
from ..aggregates.artifact import Artifact
from ..value_objects.vulnerability_status import VulnerabilityStatus
from ..value_objects.severity_category import SeverityCategory


class SystemGroupSerializer(serializers.ModelSerializer):
    """Serializer for SystemGroup aggregate"""

    # Computed fields
    totalOpenVulnerabilities = serializers.ReadOnlyField()
    totalCat1Open = serializers.ReadOnlyField()
    totalCat2Open = serializers.ReadOnlyField()
    totalCat3Open = serializers.ReadOnlyField()
    totalChecklists = serializers.ReadOnlyField()

    class Meta:
        model = SystemGroup
        fields = [
            'id', 'name', 'description', 'lifecycle_state',
            'checklistIds', 'assetIds', 'nessusScanIds', 'tags',
            'asset_hierarchy', 'last_compliance_check',
            'totalChecklists', 'totalOpenVulnerabilities',
            'totalCat1Open', 'totalCat2Open', 'totalCat3Open',
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def create(self, validated_data):
        """Create a new system group"""
        name = validated_data['name']
        description = validated_data.get('description', '')

        system = SystemGroup()
        system.create_system(name, description)

        # Set additional fields if provided
        if 'tags' in validated_data:
            system.tags = validated_data['tags']

        system.save()
        return system

    def update(self, instance, validated_data):
        """Update an existing system group"""
        if 'name' in validated_data:
            instance.name = validated_data['name']
        if 'description' in validated_data:
            instance.description = validated_data['description']
        if 'tags' in validated_data:
            instance.tags = validated_data['tags']

        instance.save()
        return instance


class StigChecklistSerializer(serializers.ModelSerializer):
    """Serializer for StigChecklist aggregate"""

    # Computed fields from asset info
    assetHostname = serializers.SerializerMethodField()
    assetIpAddresses = serializers.SerializerMethodField()
    assetMacAddresses = serializers.SerializerMethodField()

    class Meta:
        model = StigChecklist
        fields = [
            'id', 'systemGroupId', 'hostName', 'stigType', 'stigRelease', 'version',
            'lifecycle_state', 'assetInfo', 'rawCklData', 'isWebDatabase', 'webDatabaseSite',
            'webDatabaseInstance', 'asset_type', 'vulnerabilityFindingIds', 'tags',
            'assetHostname', 'assetIpAddresses', 'assetMacAddresses',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_assetHostname(self, obj):
        return obj.get_asset_hostname()

    def get_assetIpAddresses(self, obj):
        return obj.get_asset_ip_addresses()

    def get_assetMacAddresses(self, obj):
        return obj.get_asset_mac_addresses()

    def create(self, validated_data):
        """Create a new STIG checklist"""
        checklist = StigChecklist()
        checklist.create_checklist(
            host_name=validated_data['hostName'],
            stig_type=validated_data['stigType'],
            stig_release=validated_data.get('stigRelease', ''),
            version=validated_data.get('version', '1.0'),
            system_group_id=validated_data.get('systemGroupId')
        )

        # Set additional fields
        for field in ['isWebDatabase', 'webDatabaseSite', 'webDatabaseInstance', 'tags']:
            if field in validated_data:
                setattr(checklist, field, validated_data[field])

        checklist.save()
        return checklist

    def update(self, instance, validated_data):
        """Update an existing checklist"""
        for field in ['hostName', 'stigType', 'stigRelease', 'version',
                     'isWebDatabase', 'webDatabaseSite', 'webDatabaseInstance', 'tags']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance


class VulnerabilityStatusField(serializers.Field):
    """Custom field for VulnerabilityStatus value object"""

    def to_representation(self, value):
        if isinstance(value, VulnerabilityStatus):
            return {
                'status': value.status,
                'finding_details': value.finding_details,
                'comments': value.comments,
                'severity_override': value.severity_override,
                'severity_justification': value.severity_justification
            }
        return value

    def to_internal_value(self, data):
        if isinstance(data, dict):
            try:
                return VulnerabilityStatus(**data)
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
        return data


class SeverityCategoryField(serializers.Field):
    """Custom field for SeverityCategory value object"""

    def to_representation(self, value):
        if isinstance(value, SeverityCategory):
            return {
                'category': value.category,
                'name': value.name,
                'description': value.description,
                'weight': value.weight
            }
        return value

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                return SeverityCategory(data)
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
        return data


class VulnerabilityFindingSerializer(serializers.ModelSerializer):
    """Serializer for VulnerabilityFinding aggregate"""

    # Value object fields
    vulnerability_status = VulnerabilityStatusField()
    severity = SeverityCategoryField()

    # Computed fields
    effective_severity = serializers.SerializerMethodField()
    display_status = serializers.SerializerMethodField()
    display_severity = serializers.SerializerMethodField()

    class Meta:
        model = VulnerabilityFinding
        fields = [
            'id', 'checklistId', 'vulnId', 'stigId', 'ruleId', 'ruleTitle',
            'ruleDiscussion', 'checkContent', 'fixText', 'vulnerability_status',
            'severity', 'ruleVersion', 'cciIds', 'tags',
            'effective_severity', 'display_status', 'display_severity',
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def get_effective_severity(self, obj):
        return obj.get_effective_severity().category

    def get_display_status(self, obj):
        return obj.get_display_status()

    def get_display_severity(self, obj):
        return obj.get_display_severity()

    def create(self, validated_data):
        """Create a new vulnerability finding"""
        finding = VulnerabilityFinding()
        finding.create_finding(
            checklist_id=validated_data['checklistId'],
            vuln_id=validated_data['vulnId'],
            stig_id=validated_data['stigId'],
            rule_id=validated_data['ruleId'],
            rule_title=validated_data['ruleTitle'],
            severity_category=validated_data['severity'].category
        )

        # Set additional fields
        for field in ['ruleDiscussion', 'checkContent', 'fixText', 'ruleVersion', 'cciIds', 'tags']:
            if field in validated_data:
                setattr(finding, field, validated_data[field])

        # Update status if provided
        if 'vulnerability_status' in validated_data:
            status = validated_data['vulnerability_status']
            finding.update_status(
                status.status,
                status.finding_details,
                status.comments
            )
            if status.severity_override:
                finding.set_severity_override(
                    status.severity_override,
                    status.severity_justification
                )

        finding.save()
        return finding

    def update(self, instance, validated_data):
        """Update an existing finding"""
        for field in ['vulnId', 'stigId', 'ruleId', 'ruleTitle', 'ruleDiscussion',
                     'checkContent', 'fixText', 'ruleVersion', 'cciIds', 'tags']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Update severity if provided
        if 'severity' in validated_data:
            instance.severity = validated_data['severity']

        # Update status if provided
        if 'vulnerability_status' in validated_data:
            status = validated_data['vulnerability_status']
            instance.update_status(
                status.status,
                status.finding_details,
                status.comments
            )
            if status.severity_override:
                instance.set_severity_override(
                    status.severity_override,
                    status.severity_justification
                )

        instance.save()
        return instance


class ChecklistScoreSerializer(serializers.ModelSerializer):
    """Serializer for ChecklistScore aggregate"""

    # Computed fields
    totalOpen = serializers.ReadOnlyField()
    totalNotAFinding = serializers.ReadOnlyField()
    totalNotApplicable = serializers.ReadOnlyField()
    totalNotReviewed = serializers.ReadOnlyField()
    totalCat1 = serializers.ReadOnlyField()
    totalCat2 = serializers.ReadOnlyField()
    totalCat3 = serializers.ReadOnlyField()
    totalVulnerabilities = serializers.ReadOnlyField()
    compliance_percentage = serializers.SerializerMethodField()
    score_summary = serializers.SerializerMethodField()

    class Meta:
        model = ChecklistScore
        fields = [
            'id', 'checklistId', 'systemGroupId', 'hostName', 'stigType',
            'totalCat1Open', 'totalCat1NotAFinding', 'totalCat1NotApplicable', 'totalCat1NotReviewed',
            'totalCat2Open', 'totalCat2NotAFinding', 'totalCat2NotApplicable', 'totalCat2NotReviewed',
            'totalCat3Open', 'totalCat3NotAFinding', 'totalCat3NotApplicable', 'totalCat3NotReviewed',
            'totalOpen', 'totalNotAFinding', 'totalNotApplicable', 'totalNotReviewed',
            'totalCat1', 'totalCat2', 'totalCat3', 'totalVulnerabilities',
            'compliance_percentage', 'score_summary', 'lastCalculatedAt',
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def get_compliance_percentage(self, obj):
        return obj.get_compliance_percentage()

    def get_score_summary(self, obj):
        return obj.get_score_summary()

    def create(self, validated_data):
        """Create a new checklist score"""
        score = ChecklistScore()
        score.create_score(
            checklist_id=validated_data['checklistId'],
            system_group_id=validated_data.get('systemGroupId'),
            host_name=validated_data['hostName'],
            stig_type=validated_data['stigType']
        )

        score.save()
        return score

    def update(self, instance, validated_data):
        """Update an existing score"""
        for field in ['checklistId', 'systemGroupId', 'hostName', 'stigType']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance


class NessusScanSerializer(serializers.ModelSerializer):
    """Serializer for NessusScan aggregate"""

    # Computed fields
    severity_breakdown = serializers.SerializerMethodField()
    total_severe_vulnerabilities = serializers.SerializerMethodField()
    processing_percentage = serializers.SerializerMethodField()

    class Meta:
        model = NessusScan
        fields = [
            'id', 'systemGroupId', 'filename', 'scan_date', 'scanner_version', 'policy_name',
            'total_hosts', 'total_vulnerabilities', 'scan_duration_seconds',
            'critical_count', 'high_count', 'medium_count', 'low_count', 'info_count',
            'correlated_checklist_ids', 'tags', 'processing_status', 'processing_error',
            'severity_breakdown', 'total_severe_vulnerabilities', 'processing_percentage',
            'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version']

    def get_severity_breakdown(self, obj):
        return obj.severity_breakdown

    def get_total_severe_vulnerabilities(self, obj):
        return obj.total_severe_vulnerabilities

    def get_processing_percentage(self, obj):
        # Simple estimation based on status
        if obj.processing_status == 'completed':
            return 100
        elif obj.processing_status == 'processing':
            return 50  # Could be enhanced with actual progress tracking
        elif obj.processing_status == 'failed':
            return 0
        else:  # uploaded
            return 0

    def create(self, validated_data):
        """Create a new Nessus scan"""
        system_group_id = validated_data['systemGroupId']
        filename = validated_data['filename']
        raw_xml_content = validated_data.get('raw_xml_content', '')

        scan = NessusScan()
        scan.create_scan(system_group_id, filename, raw_xml_content)

        # Set additional fields if provided
        for field in ['tags']:
            if field in validated_data:
                setattr(scan, field, validated_data[field])

        scan.save()
        return scan


class StigTemplateSerializer(serializers.ModelSerializer):
    """Serializer for StigTemplate aggregate"""

    # Computed fields
    full_stig_identifier = serializers.SerializerMethodField()
    is_outdated = serializers.SerializerMethodField()
    usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = StigTemplate
        fields = [
            'id', 'name', 'description', 'stig_type', 'stig_release', 'stig_version',
            'template_type', 'raw_ckl_content', 'benchmark_title', 'benchmark_date', 'usage_count',
            'last_used_at', 'is_active', 'is_official', 'created_from_checklist_id',
            'tags', 'compatible_systems', 'full_stig_identifier', 'is_outdated',
            'usage_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_full_stig_identifier(self, obj):
        return obj.full_stig_identifier

    def get_is_outdated(self, obj):
        return obj.is_outdated

    def get_usage_percentage(self, obj):
        # This would require calculating against total templates
        # For now, return a placeholder
        return 0.0


class ArtifactSerializer(serializers.ModelSerializer):
    """Serializer for Artifact aggregate"""

    # Computed fields
    file_url = serializers.SerializerMethodField()
    human_readable_size = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    relationships_count = serializers.SerializerMethodField()

    class Meta:
        model = Artifact
        fields = [
            'id', 'filename', 'file_size', 'content_type', 'file_hash', 'artifact_type',
            'title', 'description', 'system_group_id', 'checklist_id', 'vulnerability_finding_id',
            'nessus_scan_id', 'control_id', 'cci_ids', 'security_level', 'is_public',
            'access_list', 'is_active', 'retention_period_days', 'expires_at', 'tags',
            'source', 'version', 'file_url', 'human_readable_size', 'is_expired',
            'relationships_count', 'created_at', 'updated_at', 'version'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'version', 'file_hash']

    def get_file_url(self, obj):
        return obj.file_url

    def get_human_readable_size(self, obj):
        return obj.human_readable_size

    def get_is_expired(self, obj):
        return obj.is_expired()

    def get_relationships_count(self, obj):
        count = 0
        if obj.checklist_id:
            count += 1
        if obj.vulnerability_finding_id:
            count += 1
        if obj.nessus_scan_id:
            count += 1
        return count

    def create(self, validated_data):
        """Create a new artifact with file upload"""
        file_content = self.context['request'].FILES.get('file')
        if not file_content:
            raise serializers.ValidationError("File content is required")

        # Create artifact
        artifact = Artifact()
        artifact.create_artifact(
            filename=file_content.name,
            file_content=file_content.read(),
            content_type=file_content.content_type,
            title=validated_data.get('title', file_content.name),
            artifact_type=validated_data.get('artifact_type', 'other'),
            description=validated_data.get('description'),
            system_group_id=validated_data.get('system_group_id'),
            checklist_id=validated_data.get('checklist_id'),
            vulnerability_finding_id=validated_data.get('vulnerability_finding_id'),
            nessus_scan_id=validated_data.get('nessus_scan_id'),
            control_id=validated_data.get('control_id'),
            security_level=validated_data.get('security_level', 'internal'),
            tags=validated_data.get('tags', []),
            source=validated_data.get('source', 'manual_upload'),
            retention_period_days=validated_data.get('retention_period_days')
        )

        return artifact
