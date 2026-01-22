"""
Risk Assessment Service

Service for performing risk assessments, calculating risk scores,
and managing risk evaluation workflows.
"""

import uuid
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from django.utils import timezone

from ..models.asset_risk import AssetRisk
from ..repositories.asset_risk_repository import AssetRiskRepository
from ..repositories.risk_register_repository import RiskRegisterRepository


class RiskAssessmentService:
    """
    Service for risk assessment operations.

    Provides methods for calculating risk scores, assessing threats,
    evaluating controls, and managing risk evaluation workflows.
    """

    def __init__(self):
        self.asset_risk_repo = AssetRiskRepository()
        self.risk_register_repo = RiskRegisterRepository()

    def calculate_cvss_score(self, base_score: float, temporal_metrics: Optional[Dict[str, float]] = None,
                           environmental_metrics: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Calculate CVSS score with temporal and environmental metrics.

        Args:
            base_score: CVSS base score (0.0-10.0)
            temporal_metrics: Dict with keys: exploitability, remediation_level, report_confidence
            environmental_metrics: Dict with keys: collateral_damage_potential,
                                target_distribution, confidentiality_requirement,
                                integrity_requirement, availability_requirement

        Returns:
            Dict with base_score, temporal_score, and environmental_score
        """
        scores = {'base_score': base_score}

        # Temporal score calculation (simplified)
        if temporal_metrics:
            temporal_score = base_score
            # Apply temporal metric adjustments
            exploitability = temporal_metrics.get('exploitability', 1.0)
            remediation_level = temporal_metrics.get('remediation_level', 1.0)
            report_confidence = temporal_metrics.get('report_confidence', 1.0)

            temporal_score *= exploitability * remediation_level * report_confidence
            scores['temporal_score'] = round(min(temporal_score, 10.0), 1)
        else:
            scores['temporal_score'] = base_score

        # Environmental score calculation (simplified)
        if environmental_metrics:
            environmental_score = scores['temporal_score']
            # Apply environmental metric adjustments
            collateral_damage = environmental_metrics.get('collateral_damage_potential', 1.0)
            target_distribution = environmental_metrics.get('target_distribution', 1.0)
            confidentiality_req = environmental_metrics.get('confidentiality_requirement', 1.0)
            integrity_req = environmental_metrics.get('integrity_requirement', 1.0)
            availability_req = environmental_metrics.get('availability_requirement', 1.0)

            # Simplified environmental calculation
            environmental_factor = (
                collateral_damage * target_distribution *
                max(confidentiality_req, integrity_req, availability_req)
            )

            environmental_score *= environmental_factor
            scores['environmental_score'] = round(min(environmental_score, 10.0), 1)
        else:
            scores['environmental_score'] = scores['temporal_score']

        return scores

    def assess_asset_risk(self, asset_id: uuid.UUID, assessment_data: Dict[str, Any],
                         assessor_user_id: uuid.UUID, assessor_username: str) -> AssetRisk:
        """
        Perform comprehensive risk assessment for an asset.

        Args:
            asset_id: ID of the asset being assessed
            assessment_data: Risk assessment data
            assessor_user_id: ID of the assessor
            assessor_username: Username of the assessor

        Returns:
            Created AssetRisk aggregate
        """
        # Generate unique risk ID
        risk_id = f"RISK-AST-{uuid.uuid4().hex[:8].upper()}"

        # Extract assessment data
        asset_name = assessment_data.get('asset_name', 'Unknown Asset')
        risk_title = assessment_data.get('risk_title', 'Asset Risk Assessment')
        risk_description = assessment_data.get('risk_description', '')
        risk_category = assessment_data.get('risk_category', 'operational')

        # Risk scoring
        inherent_likelihood = assessment_data.get('inherent_likelihood', 3)
        inherent_impact = assessment_data.get('inherent_impact', 3)

        # CVSS assessment (optional)
        cvss_scores = {}
        if 'cvss_base_score' in assessment_data:
            cvss_scores = self.calculate_cvss_score(
                assessment_data['cvss_base_score'],
                assessment_data.get('temporal_metrics'),
                assessment_data.get('environmental_metrics')
            )

        # Create risk aggregate
        risk = AssetRisk()
        risk.create_asset_risk(
            asset_id=asset_id,
            asset_name=asset_name,
            risk_id=risk_id,
            risk_title=risk_title,
            risk_description=risk_description,
            risk_category=risk_category,
            inherent_likelihood=inherent_likelihood,
            inherent_impact=inherent_impact,
            assessed_by_user_id=assessor_user_id,
            assessed_by_username=assessor_username,
            tags=assessment_data.get('tags', [])
        )

        # Set additional CVSS data if provided
        if cvss_scores:
            risk.cvss_base_score = cvss_scores['base_score']
            risk.cvss_temporal_score = cvss_scores['temporal_score']
            risk.cvss_environmental_score = cvss_scores['environmental_score']

        # Set threat details if provided
        threat_data = assessment_data.get('threat_details', {})
        if threat_data:
            risk.threat_source = threat_data.get('source')
            risk.threat_vector = threat_data.get('vector')
            risk.vulnerability_description = threat_data.get('vulnerability_description')

        # Set CVE/CWE data if provided
        if 'cve_ids' in assessment_data:
            risk.cve_ids = assessment_data['cve_ids']
        if 'cwe_ids' in assessment_data:
            risk.cwe_ids = assessment_data['cwe_ids']

        # Set risk threshold and appetite
        risk.risk_threshold = assessment_data.get('risk_threshold', 3)
        risk.risk_appetite = assessment_data.get('risk_appetite', 'moderate')

        # Save the risk
        risk.save()

        return risk

    def update_risk_assessment(self, risk_id: str, update_data: Dict[str, Any],
                             updated_by_user_id: uuid.UUID, updated_by_username: str) -> AssetRisk:
        """
        Update an existing risk assessment.

        Args:
            risk_id: ID of the risk to update
            update_data: Data to update
            updated_by_user_id: ID of the user making the update
            updated_by_username: Username of the user making the update

        Returns:
            Updated AssetRisk aggregate
        """
        risk = self.asset_risk_repo.get(risk_id)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found")

        # Update basic information
        if 'risk_title' in update_data:
            risk.risk_title = update_data['risk_title']
        if 'risk_description' in update_data:
            risk.risk_description = update_data['risk_description']
        if 'risk_category' in update_data:
            risk.risk_category = update_data['risk_category']

        # Update risk scoring
        likelihood_updated = 'inherent_likelihood' in update_data
        impact_updated = 'inherent_impact' in update_data

        if likelihood_updated:
            risk.inherent_likelihood = update_data['inherent_likelihood']
        if impact_updated:
            risk.inherent_impact = update_data['inherent_impact']

        # Recalculate scores if likelihood or impact changed
        if likelihood_updated or impact_updated:
            risk.inherent_risk_score = risk._calculate_risk_score(
                risk.inherent_likelihood, risk.inherent_impact
            )
            risk.inherent_risk_level = risk._get_risk_level(risk.inherent_risk_score)

            # Update residual if no effective treatment
            if risk.treatment_status != 'effective':
                risk.residual_likelihood = risk.inherent_likelihood
                risk.residual_impact = risk.inherent_impact
                risk.residual_risk_score = risk.inherent_risk_score
                risk.residual_risk_level = risk.inherent_risk_level
                risk.requires_treatment = risk.residual_risk_score >= risk.risk_threshold

        # Update CVSS scores if provided
        if 'cvss_base_score' in update_data:
            cvss_scores = self.calculate_cvss_score(
                update_data['cvss_base_score'],
                update_data.get('temporal_metrics'),
                update_data.get('environmental_metrics')
            )
            risk.cvss_base_score = cvss_scores['base_score']
            risk.cvss_temporal_score = cvss_scores['temporal_score']
            risk.cvss_environmental_score = cvss_scores['environmental_score']

        # Update threat details
        threat_data = update_data.get('threat_details', {})
        if threat_data:
            if 'source' in threat_data:
                risk.threat_source = threat_data['source']
            if 'vector' in threat_data:
                risk.threat_vector = threat_data['vector']
            if 'vulnerability_description' in threat_data:
                risk.vulnerability_description = threat_data['vulnerability_description']

        # Update technical details
        if 'cve_ids' in update_data:
            risk.cve_ids = update_data['cve_ids']
        if 'cwe_ids' in update_data:
            risk.cwe_ids = update_data['cwe_ids']

        # Update risk appetite and threshold
        if 'risk_threshold' in update_data:
            risk.risk_threshold = update_data['risk_threshold']
            risk.requires_treatment = risk.residual_risk_score >= risk.risk_threshold
        if 'risk_appetite' in update_data:
            risk.risk_appetite = update_data['risk_appetite']

        # Update tags
        if 'tags' in update_data:
            risk.tags = update_data['tags']

        risk.save()
        return risk

    def evaluate_control_effectiveness(self, risk_id: str, control_assessments: List[Dict[str, Any]],
                                     evaluated_by_user_id: uuid.UUID, evaluated_by_username: str) -> Dict[str, Any]:
        """
        Evaluate effectiveness of controls mitigating a risk.

        Args:
            risk_id: ID of the risk being evaluated
            control_assessments: List of control effectiveness assessments
            evaluated_by_user_id: ID of the evaluator
            evaluated_by_username: Username of the evaluator

        Returns:
            Dict with evaluation results and residual risk calculation
        """
        risk = self.asset_risk_repo.get(risk_id)
        if not risk:
            raise ValueError(f"Risk with ID {risk_id} not found")

        # Calculate residual risk based on control effectiveness
        total_control_effectiveness = 0
        effective_controls = 0

        for assessment in control_assessments:
            effectiveness = assessment.get('effectiveness', 0)  # 0-100 scale
            weight = assessment.get('weight', 1.0)

            if effectiveness >= 70:  # Consider controls with 70%+ effectiveness
                total_control_effectiveness += effectiveness * weight
                effective_controls += 1

        # Calculate average control effectiveness
        if effective_controls > 0:
            average_effectiveness = total_control_effectiveness / effective_controls
        else:
            average_effectiveness = 0

        # Calculate residual likelihood and impact
        # Simplified: reduce by percentage of control effectiveness
        effectiveness_factor = average_effectiveness / 100.0

        residual_likelihood = max(1, int(risk.inherent_likelihood * (1 - effectiveness_factor)))
        residual_impact = max(1, int(risk.inherent_impact * (1 - effectiveness_factor)))

        # Update risk with residual assessment
        risk.update_residual_risk(
            residual_likelihood=residual_likelihood,
            residual_impact=residual_impact,
            effective_date=timezone.now().date()
        )

        # Add evidence of control evaluation
        evidence = {
            'evaluation_date': str(timezone.now().date()),
            'evaluated_by': str(evaluated_by_user_id),
            'control_assessments': control_assessments,
            'average_effectiveness': average_effectiveness,
            'residual_calculation': {
                'inherent_likelihood': risk.inherent_likelihood,
                'inherent_impact': risk.inherent_impact,
                'residual_likelihood': residual_likelihood,
                'residual_impact': residual_impact,
                'effectiveness_factor': effectiveness_factor
            }
        }

        risk.add_evidence('control_evaluation', evidence)
        risk.save()

        return {
            'risk_id': risk_id,
            'inherent_score': risk.inherent_risk_score,
            'residual_score': risk.residual_risk_score,
            'risk_reduction_percentage': risk.risk_reduction_achieved,
            'average_control_effectiveness': average_effectiveness,
            'effective_controls_count': effective_controls,
            'residual_likelihood': residual_likelihood,
            'residual_impact': residual_impact,
            'evaluation_date': str(timezone.now())
        }

    def perform_bulk_risk_assessment(self, asset_ids: List[uuid.UUID], assessment_template: Dict[str, Any],
                                   assessor_user_id: uuid.UUID, assessor_username: str) -> List[AssetRisk]:
        """
        Perform bulk risk assessment for multiple assets using a template.

        Args:
            asset_ids: List of asset IDs to assess
            assessment_template: Template with common risk assessment data
            assessor_user_id: ID of the assessor
            assessor_username: Username of the assessor

        Returns:
            List of created AssetRisk aggregates
        """
        created_risks = []

        for asset_id in asset_ids:
            # Customize template for this asset
            asset_assessment_data = assessment_template.copy()
            asset_assessment_data['asset_id'] = asset_id

            # Add asset-specific data if available
            # (Would typically query asset service for details)

            try:
                risk = self.assess_asset_risk(
                    asset_id=asset_id,
                    assessment_data=asset_assessment_data,
                    assessor_user_id=assessor_user_id,
                    assessor_username=assessor_username
                )
                created_risks.append(risk)
            except Exception as e:
                # Log error but continue with other assets
                print(f"Failed to assess risk for asset {asset_id}: {e}")
                continue

        return created_risks

    def generate_risk_scenarios(self, asset_id: uuid.UUID, threat_modeling_data: Dict[str, Any],
                              assessor_user_id: uuid.UUID, assessor_username: str) -> List[Dict[str, Any]]:
        """
        Generate risk scenarios based on threat modeling data.

        Args:
            asset_id: ID of the asset
            threat_modeling_data: Threat modeling analysis data
            assessor_user_id: ID of the assessor
            assessor_username: Username of the assessor

        Returns:
            List of generated risk scenarios
        """
        scenarios = []

        # Extract threat actors, attack vectors, and assets from threat model
        threat_actors = threat_modeling_data.get('threat_actors', [])
        attack_vectors = threat_modeling_data.get('attack_vectors', [])
        asset_vulnerabilities = threat_modeling_data.get('vulnerabilities', [])

        # Generate scenarios by combining threats, vectors, and vulnerabilities
        for actor in threat_actors:
            for vector in attack_vectors:
                for vulnerability in asset_vulnerabilities:
                    # Calculate scenario likelihood and impact
                    likelihood = self._calculate_scenario_likelihood(actor, vector, vulnerability)
                    impact = self._calculate_scenario_impact(actor, vector, vulnerability)

                    scenario = {
                        'title': f"{actor['name']} exploits {vulnerability['name']} via {vector['name']}",
                        'description': f"{actor['description']} could exploit {vulnerability['description']} using {vector['description']}",
                        'threat_actor': actor,
                        'attack_vector': vector,
                        'vulnerability': vulnerability,
                        'inherent_likelihood': likelihood,
                        'inherent_impact': impact,
                        'inherent_risk_score': likelihood * impact,
                        'risk_category': self._determine_scenario_category(actor, vector, vulnerability),
                        'mitigation_suggestions': self._generate_mitigation_suggestions(vector, vulnerability)
                    }

                    scenarios.append(scenario)

        return scenarios

    def _calculate_scenario_likelihood(self, actor: Dict, vector: Dict, vulnerability: Dict) -> int:
        """Calculate likelihood score for a risk scenario"""
        # Simplified calculation based on actor capability, vector ease, and vulnerability prevalence
        actor_capability = actor.get('capability_score', 3)
        vector_ease = vector.get('ease_score', 3)
        vuln_prevalence = vulnerability.get('prevalence_score', 3)

        likelihood = (actor_capability + vector_ease + vuln_prevalence) // 3
        return max(1, min(5, likelihood))

    def _calculate_scenario_impact(self, actor: Dict, vector: Dict, vulnerability: Dict) -> int:
        """Calculate impact score for a risk scenario"""
        # Simplified calculation based on actor intent, vector damage potential, and vulnerability severity
        actor_intent = actor.get('intent_score', 3)
        vector_damage = vector.get('damage_potential_score', 3)
        vuln_severity = vulnerability.get('severity_score', 3)

        impact = (actor_intent + vector_damage + vuln_severity) // 3
        return max(1, min(5, impact))

    def _determine_scenario_category(self, actor: Dict, vector: Dict, vulnerability: Dict) -> str:
        """Determine risk category for a scenario"""
        # Determine category based on primary threat type
        if 'confidentiality' in vulnerability.get('impact', '').lower():
            return 'confidentiality'
        elif 'integrity' in vulnerability.get('impact', '').lower():
            return 'integrity'
        elif 'availability' in vulnerability.get('impact', '').lower():
            return 'availability'
        elif 'financial' in actor.get('motivation', '').lower():
            return 'financial'
        else:
            return 'operational'

    def _generate_mitigation_suggestions(self, vector: Dict, vulnerability: Dict) -> List[str]:
        """Generate mitigation suggestions for a scenario"""
        suggestions = []

        # Vector-specific mitigations
        vector_type = vector.get('type', '').lower()
        if 'network' in vector_type:
            suggestions.extend([
                "Implement network segmentation",
                "Deploy intrusion detection systems",
                "Use network access controls"
            ])
        elif 'physical' in vector_type:
            suggestions.extend([
                "Implement physical access controls",
                "Use surveillance systems",
                "Deploy environmental monitoring"
            ])
        elif 'social' in vector_type:
            suggestions.extend([
                "Conduct security awareness training",
                "Implement phishing prevention",
                "Use multi-factor authentication"
            ])

        # Vulnerability-specific mitigations
        vuln_type = vulnerability.get('type', '').lower()
        if 'software' in vuln_type:
            suggestions.extend([
                "Keep software updated",
                "Use vulnerability scanning",
                "Implement application whitelisting"
            ])
        elif 'configuration' in vuln_type:
            suggestions.extend([
                "Implement configuration management",
                "Use hardening guidelines",
                "Regular configuration audits"
            ])

        return list(set(suggestions))  # Remove duplicates

    def validate_risk_assessment_data(self, assessment_data: Dict[str, Any]) -> List[str]:
        """
        Validate risk assessment data for completeness and consistency.

        Args:
            assessment_data: Risk assessment data to validate

        Returns:
            List of validation error messages
        """
        errors = []

        # Required fields
        required_fields = ['asset_name', 'risk_title', 'risk_description']
        for field in required_fields:
            if field not in assessment_data or not assessment_data[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Risk scoring validation
        if 'inherent_likelihood' in assessment_data:
            likelihood = assessment_data['inherent_likelihood']
            if not isinstance(likelihood, int) or likelihood < 1 or likelihood > 5:
                errors.append("Inherent likelihood must be an integer between 1 and 5")

        if 'inherent_impact' in assessment_data:
            impact = assessment_data['inherent_impact']
            if not isinstance(impact, int) or impact < 1 or impact > 5:
                errors.append("Inherent impact must be an integer between 1 and 5")

        # CVSS validation
        if 'cvss_base_score' in assessment_data:
            cvss = assessment_data['cvss_base_score']
            if not isinstance(cvss, (int, float)) or cvss < 0.0 or cvss > 10.0:
                errors.append("CVSS base score must be a number between 0.0 and 10.0")

        # Risk category validation
        valid_categories = [
            'confidentiality', 'integrity', 'availability', 'financial',
            'reputational', 'operational', 'compliance', 'strategic'
        ]
        if 'risk_category' in assessment_data:
            category = assessment_data['risk_category']
            if category not in valid_categories:
                errors.append(f"Risk category must be one of: {', '.join(valid_categories)}")

        return errors
