"""
Privacy Assessment Service

Service for conducting privacy assessments, managing data subject rights,
consent processing, and privacy compliance workflows.
"""

import uuid
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone

from ..models.data_asset import DataAsset
from ..models.consent_record import ConsentRecord
from ..models.data_subject_right import DataSubjectRight
from ..repositories.data_asset_repository import DataAssetRepository
from ..repositories.consent_record_repository import ConsentRecordRepository
from ..repositories.data_subject_right_repository import DataSubjectRightRepository


class PrivacyAssessmentService:
    """
    Service for privacy assessment operations.

    Provides methods for privacy impact assessments, consent management,
    data subject rights processing, and privacy compliance reporting.
    """

    def __init__(self):
        self.data_asset_repo = DataAssetRepository()
        self.consent_repo = ConsentRecordRepository()
        self.dsr_repo = DataSubjectRightRepository()

    def conduct_privacy_impact_assessment(
        self,
        asset_id: str,
        assessment_scope: Dict[str, Any],
        assessor_user_id: uuid.UUID,
        assessor_username: str
    ) -> Dict[str, Any]:
        """
        Conduct a comprehensive Privacy Impact Assessment (PIA).

        Args:
            asset_id: ID of the data asset
            assessment_scope: Assessment scope and methodology
            assessor_user_id: ID of the assessor
            assessor_username: Username of the assessor

        Returns:
            PIA results and recommendations
        """
        asset = self.data_asset_repo.get(asset_id)
        if not asset:
            raise ValueError(f"Data asset {asset_id} not found")

        # Assess risk factors
        risk_factors = self._assess_pia_risk_factors(asset)

        # Evaluate privacy controls
        control_effectiveness = self._evaluate_privacy_controls(asset)

        # Assess data subject impact
        subject_impact = self._assess_data_subject_impact(asset)

        # Generate findings and recommendations
        findings = self._generate_pia_findings(risk_factors, control_effectiveness, subject_impact)
        recommendations = self._generate_pia_recommendations(findings)

        # Determine overall risk level
        overall_risk = self._calculate_overall_pia_risk(risk_factors, control_effectiveness)

        pia_results = {
            'asset_id': asset.asset_id,
            'asset_name': asset.asset_name,
            'assessment_date': str(timezone.now().date()),
            'assessor': assessor_username,
            'risk_factors': risk_factors,
            'control_effectiveness': control_effectiveness,
            'data_subject_impact': subject_impact,
            'findings': findings,
            'recommendations': recommendations,
            'overall_risk_level': overall_risk,
            'pia_conclusion': self._generate_pia_conclusion(overall_risk, recommendations)
        }

        # Update the asset with PIA results
        asset.conduct_privacy_impact_assessment(
            findings=pia_results['pia_conclusion'],
            assessor_user_id=assessor_user_id,
            assessor_username=assessor_username
        )

        asset.save()

        return pia_results

    def _assess_pia_risk_factors(self, asset: DataAsset) -> Dict[str, Any]:
        """Assess PIA risk factors"""
        risk_factors = {
            'data_sensitivity': {
                'level': asset.sensitivity_level,
                'score': self._get_sensitivity_score(asset.sensitivity_level),
                'factors': []
            },
            'data_volume': {
                'estimated_subjects': asset.estimated_data_subjects,
                'score': self._assess_data_volume_risk(asset.estimated_data_subjects),
                'factors': []
            },
            'processing_characteristics': {
                'score': 0,
                'factors': []
            },
            'data_sharing': {
                'score': 0,
                'factors': []
            },
            'international_transfers': {
                'count': len(asset.international_transfers),
                'score': len(asset.international_transfers) * 25,  # 25 points per transfer
                'factors': []
            }
        }

        # Assess processing characteristics
        if asset.processing_purposes:
            high_risk_purposes = ['profiling', 'automated_decision_making', 'marketing']
            risk_purposes = [p for p in asset.processing_purposes if any(hrp in p.lower() for hrp in high_risk_purposes)]
            risk_factors['processing_characteristics']['score'] = len(risk_purposes) * 20

        # Assess data sharing
        recipient_count = len(asset.recipients) + len(asset.third_party_processors)
        risk_factors['data_sharing']['score'] = min(recipient_count * 15, 100)  # Cap at 100

        return risk_factors

    def _evaluate_privacy_controls(self, asset: DataAsset) -> Dict[str, Any]:
        """Evaluate effectiveness of privacy controls"""
        controls = {
            'data_minimization': {
                'implemented': bool(asset.processing_purposes and len(asset.processing_purposes) <= 3),
                'effectiveness': 80 if bool(asset.processing_purposes and len(asset.processing_purposes) <= 3) else 40
            },
            'purpose_limitation': {
                'implemented': bool(asset.processing_purposes),
                'effectiveness': 90 if bool(asset.processing_purposes) else 30
            },
            'storage_limitation': {
                'implemented': bool(asset.retention_schedule),
                'effectiveness': 85 if bool(asset.retention_schedule) else 35
            },
            'security_measures': {
                'implemented': bool(asset.security_measures),
                'effectiveness': 80 if len(asset.security_measures or []) >= 3 else 40
            },
            'consent_mechanism': {
                'implemented': asset.consent_required and bool(asset.consent_mechanisms),
                'effectiveness': 75 if (asset.consent_required and bool(asset.consent_mechanisms)) else 25
            },
            'data_subject_rights': {
                'implemented': bool(asset.subject_rights_supported),
                'effectiveness': asset.data_subject_rights_compliance_score
            }
        }

        overall_effectiveness = sum(control['effectiveness'] for control in controls.values()) / len(controls)

        return {
            'controls': controls,
            'overall_effectiveness': round(overall_effectiveness, 2),
            'implemented_controls': len([c for c in controls.values() if c['implemented']]),
            'total_controls': len(controls)
        }

    def _assess_data_subject_impact(self, asset: DataAsset) -> Dict[str, Any]:
        """Assess impact on data subjects"""
        impact = {
            'vulnerable_subjects': {
                'present': any(vuln in str(asset.data_subject_types).lower()
                             for vuln in ['children', 'elderly', 'patients', 'employees']),
                'score': 30 if any(vuln in str(asset.data_subject_types).lower()
                                 for vuln in ['children', 'elderly', 'patients', 'employees']) else 0
            },
            'data_sensitivity_impact': {
                'score': self._get_sensitivity_score(asset.sensitivity_level) * 0.8
            },
            'processing_scale': {
                'score': self._assess_data_volume_risk(asset.estimated_data_subjects) * 0.6
            },
            'potential_harm': {
                'score': 0,
                'factors': []
            }
        }

        # Calculate potential harm based on data types and processing
        harm_score = 0

        if 'special_category_data' in asset.data_categories:
            harm_score += 40
            impact['potential_harm']['factors'].append('Special category data processing')

        if asset.sensitivity_level == 'highly_restricted':
            harm_score += 30
            impact['potential_harm']['factors'].append('Highly sensitive data')

        if len(asset.international_transfers) > 0:
            harm_score += 20
            impact['potential_harm']['factors'].append('International data transfers')

        if 'profiling' in str(asset.processing_purposes).lower():
            harm_score += 25
            impact['potential_harm']['factors'].append('Automated profiling')

        impact['potential_harm']['score'] = min(harm_score, 100)

        return impact

    def _generate_pia_findings(
        self,
        risk_factors: Dict[str, Any],
        control_effectiveness: Dict[str, Any],
        subject_impact: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate PIA findings"""
        findings = []

        # Risk-based findings
        total_risk_score = sum(factor.get('score', 0) for factor in risk_factors.values()
                              if isinstance(factor, dict) and 'score' in factor)

        if total_risk_score > 60:
            findings.append({
                'type': 'high_risk',
                'severity': 'high',
                'finding': f'High overall risk score ({total_risk_score}) indicates significant privacy risks',
                'impact': 'May require additional safeguards or DPIA review'
            })

        # Control effectiveness findings
        if control_effectiveness['overall_effectiveness'] < 60:
            findings.append({
                'type': 'control_weakness',
                'severity': 'medium',
                'finding': f'Privacy controls effectiveness is low ({control_effectiveness["overall_effectiveness"]}%)',
                'impact': 'Increased risk of privacy breaches or non-compliance'
            })

        # Subject impact findings
        harm_score = subject_impact['potential_harm']['score']
        if harm_score > 50:
            findings.append({
                'type': 'subject_impact',
                'severity': 'high',
                'finding': f'High potential harm to data subjects (score: {harm_score})',
                'impact': 'May require additional consent or impact mitigation measures'
            })

        return findings

    def _generate_pia_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate PIA recommendations based on findings"""
        recommendations = []

        for finding in findings:
            if finding['type'] == 'high_risk':
                recommendations.extend([
                    'Implement additional privacy safeguards',
                    'Consider conducting Data Protection Impact Assessment (DPIA)',
                    'Enhance data minimization practices',
                    'Review and strengthen consent mechanisms'
                ])
            elif finding['type'] == 'control_weakness':
                recommendations.extend([
                    'Strengthen privacy control implementation',
                    'Conduct privacy control gap analysis',
                    'Implement automated privacy monitoring',
                    'Provide additional privacy training'
                ])
            elif finding['type'] == 'subject_impact':
                recommendations.extend([
                    'Implement additional data subject protections',
                    'Enhance consent and withdrawal mechanisms',
                    'Conduct data subject impact assessment',
                    'Implement privacy by design principles'
                ])

        # Remove duplicates and return
        return list(set(recommendations))

    def _calculate_overall_pia_risk(
        self,
        risk_factors: Dict[str, Any],
        control_effectiveness: Dict[str, Any]
    ) -> str:
        """Calculate overall PIA risk level"""
        risk_score = sum(factor.get('score', 0) for factor in risk_factors.values()
                        if isinstance(factor, dict) and 'score' in factor)

        control_score = control_effectiveness['overall_effectiveness']

        # Risk increases with high risk factors and decreases with strong controls
        net_risk = risk_score - (control_score * 0.5)

        if net_risk > 70:
            return 'high'
        elif net_risk > 40:
            return 'medium'
        else:
            return 'low'

    def _generate_pia_conclusion(self, overall_risk: str, recommendations: List[str]) -> str:
        """Generate PIA conclusion text"""
        conclusion = f"This Privacy Impact Assessment concludes that the processing activity "

        if overall_risk == 'high':
            conclusion += "presents HIGH privacy risks that require immediate attention. "
        elif overall_risk == 'medium':
            conclusion += "presents MEDIUM privacy risks that should be monitored. "
        else:
            conclusion += "presents LOW privacy risks but should still be reviewed periodically. "

        if recommendations:
            conclusion += f"Key recommendations include: {', '.join(recommendations[:3])}"

        return conclusion

    def _get_sensitivity_score(self, sensitivity_level: str) -> int:
        """Get sensitivity score for risk calculation"""
        scores = {
            'public': 10,
            'internal': 30,
            'confidential': 60,
            'restricted': 80,
            'highly_restricted': 100
        }
        return scores.get(sensitivity_level, 50)

    def _assess_data_volume_risk(self, estimated_subjects: Optional[int]) -> int:
        """Assess risk based on data volume"""
        if not estimated_subjects:
            return 20  # Unknown volume = moderate risk

        if estimated_subjects > 100000:
            return 100  # Very high volume
        elif estimated_subjects > 10000:
            return 80   # High volume
        elif estimated_subjects > 1000:
            return 60   # Medium volume
        elif estimated_subjects > 100:
            return 40   # Low volume
        else:
            return 20   # Very low volume

    def process_consent_request(
        self,
        data_subject_id: str,
        processing_purposes: List[str],
        consent_method: str,
        consent_data: Dict[str, Any],
        source_system: Optional[str] = None
    ) -> ConsentRecord:
        """
        Process a consent request from a data subject.

        Args:
            data_subject_id: Identifier for the data subject
            processing_purposes: Purposes for which consent is requested
            consent_method: Method used to obtain consent
            consent_data: Additional consent data
            source_system: System where consent was obtained

        Returns:
            Created ConsentRecord
        """
        # Generate consent ID
        consent_id = f"CONS-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"

        # Create consent record
        consent = ConsentRecord()
        consent.record_consent(
            consent_id=consent_id,
            data_subject_id=data_subject_id,
            data_subject_type=consent_data.get('data_subject_type', 'customer'),
            processing_purposes=processing_purposes,
            consent_method=consent_method,
            consent_language=consent_data.get('consent_language', 'en'),
            valid_until=consent_data.get('valid_until'),
            source_system=source_system,
            country_code=consent_data.get('country_code'),
            rights_requested=consent_data.get('rights_requested', processing_purposes)
        )

        # Set additional consent details
        if 'legal_basis' in consent_data:
            consent.legal_basis = consent_data['legal_basis']
        if 'legitimate_interests' in consent_data:
            consent.legitimate_interests = consent_data['legitimate_interests']

        consent.save()
        return consent

    def process_data_subject_right_request(
        self,
        data_subject_id: str,
        primary_right: str,
        request_description: str,
        contact_info: Dict[str, Any],
        request_data: Dict[str, Any]
    ) -> DataSubjectRight:
        """
        Process a data subject rights request.

        Args:
            data_subject_id: Identifier for the data subject
            primary_right: Primary right being requested
            request_description: Description of the request
            contact_info: Contact information for the data subject
            request_data: Additional request data

        Returns:
            Created DataSubjectRight request
        """
        # Generate request ID
        request_id = f"DSR-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"

        # Create data subject right request
        dsr = DataSubjectRight()
        dsr.submit_request(
            request_id=request_id,
            data_subject_id=data_subject_id,
            primary_right=primary_right,
            request_description=request_description,
            contact_email=contact_info.get('email'),
            contact_phone=contact_info.get('phone'),
            rights_requested=request_data.get('rights_requested'),
            request_scope=request_data.get('request_scope')
        )

        # Set additional request details
        dsr.data_subject_type = request_data.get('data_subject_type', 'customer')
        dsr.priority = request_data.get('priority', 'medium')
        dsr.source = request_data.get('source', 'direct_request')

        dsr.save()
        return dsr

    def generate_privacy_compliance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive privacy compliance report.

        Returns:
            Complete privacy compliance report
        """
        # Get data from repositories
        assets = self.data_asset_repo.get_privacy_compliance_overview()
        risk_assessment = self.data_asset_repo.get_data_asset_risk_assessment()
        retention_report = self.data_asset_repo.get_retention_compliance_report()
        rights_readiness = self.data_asset_repo.get_data_subject_rights_readiness()
        maturity_score = self.data_asset_repo.calculate_privacy_maturity_score()

        # Get consent and DSR statistics
        consent_stats = self._get_consent_statistics()
        dsr_stats = self._get_dsr_statistics()

        return {
            'report_title': 'Privacy Compliance Report',
            'generated_at': str(timezone.now()),
            'report_period': 'Current',
            'executive_summary': {
                'maturity_score': maturity_score['maturity_score'],
                'maturity_level': maturity_score['maturity_level'],
                'total_data_assets': assets['total_data_assets'],
                'compliance_rate': assets['compliance_status_distribution'].get('compliant', 0) / assets['total_data_assets'] * 100 if assets['total_data_assets'] > 0 else 0,
                'high_risk_assets': assets['high_risk_assets'],
                'attention_required': assets['attention_required']
            },
            'data_assets': assets,
            'risk_assessment': risk_assessment,
            'retention_compliance': retention_report,
            'data_subject_rights': rights_readiness,
            'consent_management': consent_stats,
            'data_subject_requests': dsr_stats,
            'maturity_assessment': maturity_score,
            'recommendations': self._generate_compliance_recommendations(assets, maturity_score)
        }

    def _get_consent_statistics(self) -> Dict[str, Any]:
        """Get consent record statistics"""
        # This would query the consent repository
        # For now, return placeholder
        return {
            'total_consents': 0,
            'active_consents': 0,
            'withdrawn_consents': 0,
            'expired_consents': 0,
            'consent_withdrawal_rate': 0.0,
            'average_consent_duration_days': 0
        }

    def _get_dsr_statistics(self) -> Dict[str, Any]:
        """Get data subject rights request statistics"""
        # This would query the DSR repository
        # For now, return placeholder
        return {
            'total_requests': 0,
            'completed_requests': 0,
            'pending_requests': 0,
            'overdue_requests': 0,
            'average_processing_days': 0,
            'compliance_rate': 0.0
        }

    def _generate_compliance_recommendations(
        self,
        assets: Dict[str, Any],
        maturity_score: Dict[str, Any]
    ) -> List[str]:
        """Generate compliance improvement recommendations"""
        recommendations = []

        # Maturity-based recommendations
        if maturity_score['maturity_score'] < 50:
            recommendations.append("Establish comprehensive privacy program governance")
            recommendations.append("Conduct privacy awareness training for all staff")
            recommendations.append("Implement privacy by design principles")

        # Asset-based recommendations
        if assets['pia_status']['completion_rate'] < 80:
            recommendations.append("Complete Privacy Impact Assessments for all high-risk processing activities")

        if assets['dpo_review_status']['completion_rate'] < 80:
            recommendations.append("Ensure DPO review for all sensitive data processing")

        if assets['attention_required'] > 0:
            recommendations.append(f"Address compliance issues for {assets['attention_required']} data assets")

        return recommendations
