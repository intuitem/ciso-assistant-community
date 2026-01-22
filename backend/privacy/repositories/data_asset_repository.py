"""
Data Asset Repository

Repository for managing DataAsset aggregates with support for
privacy compliance queries, risk assessments, and audit reporting.
"""

import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.utils import timezone

from core.domain.repository import Repository
from ..models.data_asset import DataAsset


class DataAssetRepository(Repository[DataAsset]):
    """
    Repository for DataAsset aggregates.

    Provides methods for querying data assets by privacy criteria,
    compliance status, risk levels, and organizational ownership.
    """

    def __init__(self):
        super().__init__(DataAsset)

    def find_by_data_category(self, category: str) -> List[DataAsset]:
        """Find data assets by primary data category"""
        return list(self.model.objects.filter(primary_data_category=category))

    def find_by_sensitivity_level(self, sensitivity_level: str) -> List[DataAsset]:
        """Find data assets by sensitivity level"""
        return list(self.model.objects.filter(sensitivity_level=sensitivity_level))

    def find_by_compliance_status(self, status: str) -> List[DataAsset]:
        """Find data assets by compliance status"""
        return list(self.model.objects.filter(compliance_status=status))

    def find_by_owner(self, owner_user_id: uuid.UUID) -> List[DataAsset]:
        """Find data assets owned by a specific user"""
        return list(self.model.objects.filter(data_owner_user_id=owner_user_id))

    def find_high_risk_assets(self) -> List[DataAsset]:
        """Find high-risk data assets requiring attention"""
        return list(self.model.objects.filter(
            models.Q(sensitivity_level__in=['restricted', 'highly_restricted']) |
            models.Q(pia_required=True) |
            models.Q(compliance_status__in=['non_compliant', 'remediation_required'])
        ))

    def find_overdue_for_audit(self) -> List[DataAsset]:
        """Find data assets overdue for privacy audit"""
        today = timezone.now().date()
        return list(self.model.objects.filter(
            next_audit_date__isnull=False,
            next_audit_date__lt=today
        ))

    def find_requiring_pia(self) -> List[DataAsset]:
        """Find data assets requiring Privacy Impact Assessment"""
        return list(self.model.objects.filter(
            pia_required=True,
            pia_completed=False
        ))

    def find_by_processing_purpose(self, purpose: str) -> List[DataAsset]:
        """Find data assets by processing purpose"""
        return list(self.model.objects.filter(processing_purposes__contains=[purpose]))

    def get_privacy_compliance_overview(self) -> Dict[str, Any]:
        """Get comprehensive privacy compliance overview"""
        assets = list(self.model.objects.all())

        overview = {
            'total_data_assets': len(assets),
            'data_category_distribution': {},
            'sensitivity_distribution': {},
            'compliance_status_distribution': {},
            'pia_status': {
                'required': len([a for a in assets if a.pia_required]),
                'completed': len([a for a in assets if a.pia_completed]),
                'completion_rate': 0.0
            },
            'dpo_review_status': {
                'required': len([a for a in assets if a.dpo_review_required]),
                'completed': len([a for a in assets if a.dpo_reviewed]),
                'completion_rate': 0.0
            },
            'high_risk_assets': len([a for a in assets if a.is_high_risk]),
            'overdue_audits': len([a for a in assets if a.is_overdue_for_audit]),
            'attention_required': len([a for a in assets if a.requires_audit_attention])
        }

        # Calculate distributions
        for asset in assets:
            overview['data_category_distribution'][asset.primary_data_category] = \
                overview['data_category_distribution'].get(asset.primary_data_category, 0) + 1

            overview['sensitivity_distribution'][asset.sensitivity_level] = \
                overview['sensitivity_distribution'].get(asset.sensitivity_level, 0) + 1

            overview['compliance_status_distribution'][asset.compliance_status] = \
                overview['compliance_status_distribution'].get(asset.compliance_status, 0) + 1

        # Calculate completion rates
        if overview['pia_status']['required'] > 0:
            overview['pia_status']['completion_rate'] = round(
                (overview['pia_status']['completed'] / overview['pia_status']['required']) * 100, 2
            )

        if overview['dpo_review_status']['required'] > 0:
            overview['dpo_review_status']['completion_rate'] = round(
                (overview['dpo_review_status']['completed'] / overview['dpo_review_status']['required']) * 100, 2
            )

        return overview

    def get_data_asset_risk_assessment(self) -> Dict[str, Any]:
        """Generate data asset risk assessment report"""
        assets = list(self.model.objects.all())

        risk_assessment = {
            'total_assets': len(assets),
            'risk_distribution': {
                'high_risk': len([a for a in assets if a.is_high_risk]),
                'sensitive_data': len([a for a in assets if a.sensitivity_level in ['restricted', 'highly_restricted']]),
                'special_categories': len([a for a in assets if 'special_category_data' in a.data_categories]),
                'international_transfers': len([a for a in assets if a.international_transfers])
            },
            'compliance_gaps': {
                'missing_pia': len([a for a in assets if a.pia_required and not a.pia_completed]),
                'missing_dpo_review': len([a for a in assets if a.dpo_review_required and not a.dpo_reviewed]),
                'non_compliant': len([a for a in assets if a.compliance_status == 'non_compliant']),
                'overdue_audits': len([a for a in assets if a.is_overdue_for_audit])
            },
            'data_subject_rights_compliance': {
                'average_score': 0.0,
                'fully_compliant': 0,
                'needs_improvement': 0
            },
            'generated_at': str(timezone.now())
        }

        # Calculate data subject rights compliance
        rights_scores = [a.data_subject_rights_compliance_score for a in assets if a.data_subject_rights_compliance_score > 0]
        if rights_scores:
            risk_assessment['data_subject_rights_compliance']['average_score'] = round(sum(rights_scores) / len(rights_scores), 2)
            risk_assessment['data_subject_rights_compliance']['fully_compliant'] = len([s for s in rights_scores if s >= 90])
            risk_assessment['data_subject_rights_compliance']['needs_improvement'] = len([s for s in rights_scores if s < 70])

        return risk_assessment

    def get_retention_compliance_report(self) -> Dict[str, Any]:
        """Generate data retention compliance report"""
        assets = list(self.model.objects.all())

        retention_report = {
            'total_assets': len(assets),
            'retention_defined': len([a for a in assets if a.retention_period_days]),
            'retention_compliance': {},
            'average_retention_days': 0,
            'excessive_retention': [],
            'insufficient_retention': [],
            'generated_at': str(timezone.now())
        }

        retention_periods = [a.retention_period_days for a in assets if a.retention_period_days]
        if retention_periods:
            retention_report['average_retention_days'] = round(sum(retention_periods) / len(retention_periods), 1)

        # Analyze retention compliance
        for asset in assets:
            if asset.retention_period_days:
                status = asset.retention_compliance_status
                retention_report['retention_compliance'][status] = \
                    retention_report['retention_compliance'].get(status, 0) + 1

                if status == 'potentially_excessive':
                    retention_report['excessive_retention'].append({
                        'asset_id': asset.asset_id,
                        'name': asset.asset_name,
                        'retention_days': asset.retention_period_days
                    })
                elif status == 'potentially_insufficient':
                    retention_report['insufficient_retention'].append({
                        'asset_id': asset.asset_id,
                        'name': asset.asset_name,
                        'retention_days': asset.retention_period_days
                    })

        return retention_report

    def get_data_subject_rights_readiness(self) -> Dict[str, Any]:
        """Assess readiness for handling data subject rights requests"""
        assets = list(self.model.objects.all())

        readiness = {
            'total_assets': len(assets),
            'rights_supported_distribution': {},
            'average_rights_compliance': 0.0,
            'fully_compliant_assets': 0,
            'missing_rights_mechanisms': {
                'access': 0,
                'rectification': 0,
                'erasure': 0
            },
            'recommendations': [],
            'generated_at': str(timezone.now())
        }

        total_rights_score = 0
        fully_compliant = 0

        for asset in assets:
            rights_count = len(asset.subject_rights_supported)
            readiness['rights_supported_distribution'][rights_count] = \
                readiness['rights_supported_distribution'].get(rights_count, 0) + 1

            score = asset.data_subject_rights_compliance_score
            total_rights_score += score

            if score >= 90:
                fully_compliant += 1

            # Check for missing mechanisms
            if not asset.right_of_access_mechanism:
                readiness['missing_rights_mechanisms']['access'] += 1
            if not asset.right_of_rectification_mechanism:
                readiness['missing_rights_mechanisms']['rectification'] += 1
            if not asset.right_of_erasure_mechanism:
                readiness['missing_rights_mechanisms']['erasure'] += 1

        if assets:
            readiness['average_rights_compliance'] = round(total_rights_score / len(assets), 2)
            readiness['fully_compliant_assets'] = fully_compliant

        # Generate recommendations
        if readiness['missing_rights_mechanisms']['access'] > 0:
            readiness['recommendations'].append(
                f"Implement access request mechanisms for {readiness['missing_rights_mechanisms']['access']} assets"
            )
        if readiness['average_rights_compliance'] < 70:
            readiness['recommendations'].append(
                "Improve data subject rights compliance - average score below 70%"
            )

        return readiness

    def bulk_update_compliance_status(self, asset_ids: List[str], new_status: str,
                                    reason: str) -> int:
        """Bulk update compliance status for multiple data assets"""
        assets = self.model.objects.filter(id__in=asset_ids)
        updated_count = 0

        for asset in assets:
            old_status = asset.compliance_status
            asset.compliance_status = new_status
            asset.save()
            updated_count += 1

        return updated_count

    def get_assets_by_data_subject_type(self, subject_type: str) -> List[DataAsset]:
        """Find data assets containing data about specific subject types"""
        return list(self.model.objects.filter(data_subject_types__contains=[subject_type]))

    def get_assets_with_international_transfers(self) -> List[DataAsset]:
        """Find data assets involving international transfers"""
        return list(self.model.objects.exclude(international_transfers__exact=[]))

    def get_assets_requiring_dpo_attention(self) -> List[DataAsset]:
        """Find data assets requiring DPO attention"""
        return list(self.model.objects.filter(
            models.Q(dpo_review_required=True, dpo_reviewed=False) |
            models.Q(compliance_status='non_compliant') |
            models.Q(is_overdue_for_audit=True)
        ))

    def calculate_privacy_maturity_score(self) -> Dict[str, Any]:
        """Calculate overall privacy program maturity score"""
        assets = list(self.model.objects.all())

        if not assets:
            return {
                'maturity_score': 0,
                'maturity_level': 'No Assets',
                'component_scores': {},
                'recommendations': ['Register data assets to begin privacy program assessment']
            }

        # Calculate component scores
        component_scores = {
            'asset_inventory': min(len(assets) * 2, 100),  # Up to 100 points for comprehensive inventory
            'pia_completion': round((len([a for a in assets if a.pia_completed]) / len(assets)) * 100, 2),
            'dpo_review_completion': round((len([a for a in assets if a.dpo_reviewed]) / len(assets)) * 100, 2),
            'compliance_status': round((len([a for a in assets if a.compliance_status == 'compliant']) / len(assets)) * 100, 2),
            'rights_compliance': round(sum(a.data_subject_rights_compliance_score for a in assets) / len(assets), 2),
            'audit_compliance': round((len([a for a in assets if not a.is_overdue_for_audit]) / len(assets)) * 100, 2)
        }

        # Calculate overall maturity score (weighted average)
        weights = {
            'asset_inventory': 0.1,
            'pia_completion': 0.2,
            'dpo_review_completion': 0.15,
            'compliance_status': 0.25,
            'rights_compliance': 0.2,
            'audit_compliance': 0.1
        }

        maturity_score = sum(component_scores[comp] * weights[comp] for comp in component_scores.keys())
        maturity_score = round(maturity_score, 2)

        # Determine maturity level
        if maturity_score >= 90:
            maturity_level = 'Optimized'
        elif maturity_score >= 75:
            maturity_level = 'Managed'
        elif maturity_score >= 50:
            maturity_level = 'Defined'
        elif maturity_score >= 25:
            maturity_level = 'Repeatable'
        else:
            maturity_level = 'Initial'

        # Generate recommendations
        recommendations = []
        if component_scores['pia_completion'] < 80:
            recommendations.append("Complete Privacy Impact Assessments for high-risk data assets")
        if component_scores['dpo_review_completion'] < 80:
            recommendations.append("Ensure DPO review for sensitive data processing")
        if component_scores['rights_compliance'] < 70:
            recommendations.append("Implement comprehensive data subject rights mechanisms")
        if component_scores['audit_compliance'] < 80:
            recommendations.append("Establish regular privacy audit schedule")

        return {
            'maturity_score': maturity_score,
            'maturity_level': maturity_level,
            'component_scores': component_scores,
            'recommendations': recommendations,
            'calculated_at': str(timezone.now())
        }
