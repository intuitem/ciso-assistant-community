"""
Compliance Assessment Service

Service for orchestrating compliance assessments, managing assessment workflows,
coordinating evidence collection, and providing compliance analytics.
"""

import uuid
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone

from ..models.compliance_assessment import ComplianceAssessment
from ..models.requirement_assessment import RequirementAssessment
from ..models.compliance_finding import ComplianceFinding
from ..models.compliance_exception import ComplianceException
from ..repositories.compliance_assessment_repository import ComplianceAssessmentRepository
from ..repositories.requirement_assessment_repository import RequirementAssessmentRepository
from ..repositories.compliance_finding_repository import ComplianceFindingRepository
from ..repositories.compliance_exception_repository import ComplianceExceptionRepository


class ComplianceAssessmentService:
    """
    Service for compliance assessment operations.

    Provides methods for creating, managing, and analyzing compliance assessments
    across different frameworks and organizational scopes.
    """

    def __init__(self):
        self.assessment_repo = ComplianceAssessmentRepository()
        self.requirement_repo = RequirementAssessmentRepository()
        self.finding_repo = ComplianceFindingRepository()
        self.exception_repo = ComplianceExceptionRepository()

    def create_comprehensive_assessment(
        self,
        assessment_data: Dict[str, Any],
        requirements_data: List[Dict[str, Any]],
        assessor_user_id: uuid.UUID,
        assessor_username: str
    ) -> Tuple[ComplianceAssessment, List[RequirementAssessment]]:
        """
        Create a comprehensive compliance assessment with requirements.

        Args:
            assessment_data: Assessment metadata
            requirements_data: List of requirement definitions
            assessor_user_id: ID of the assessor
            assessor_username: Username of the assessor

        Returns:
            Tuple of (assessment, requirement_assessments)
        """
        # Generate unique assessment ID
        assessment_id = f"CMP-{timezone.now().strftime('%Y')}-{uuid.uuid4().hex[:6].upper()}"

        # Create the main assessment
        assessment = ComplianceAssessment()
        assessment.create_assessment(
            assessment_id=assessment_id,
            name=assessment_data['name'],
            target_type=assessment_data['target_type'],
            target_id=assessment_data['target_id'],
            target_name=assessment_data['target_name'],
            primary_framework=assessment_data['primary_framework'],
            scope=assessment_data.get('scope', 'System'),
            assessment_lead_user_id=assessor_user_id,
            assessment_lead_username=assessor_username,
            planned_start_date=assessment_data.get('planned_start_date'),
            planned_completion_date=assessment_data.get('planned_completion_date'),
            description=assessment_data.get('description'),
            tags=assessment_data.get('tags', [])
        )

        # Set additional assessment properties
        if 'additional_frameworks' in assessment_data:
            assessment.additional_frameworks = assessment_data['additional_frameworks']
        if 'assessment_type' in assessment_data:
            assessment.assessment_type = assessment_data['assessment_type']
        if 'priority' in assessment_data:
            assessment.priority = assessment_data['priority']

        assessment.save()

        # Create requirement assessments
        requirement_assessments = []
        for req_data in requirements_data:
            req_assessment = self._create_requirement_assessment(
                compliance_assessment_id=assessment.id,
                requirement_data=req_data,
                assessor_user_id=assessor_user_id,
                assessor_username=assessor_username
            )
            requirement_assessments.append(req_assessment)

            # Link to main assessment
            assessment.requirement_assessment_ids.append(str(req_assessment.id))

        assessment.save()

        return assessment, requirement_assessments

    def _create_requirement_assessment(
        self,
        compliance_assessment_id: uuid.UUID,
        requirement_data: Dict[str, Any],
        assessor_user_id: uuid.UUID,
        assessor_username: str
    ) -> RequirementAssessment:
        """Create a single requirement assessment"""
        req_assessment = RequirementAssessment()
        req_assessment.create_requirement_assessment(
            compliance_assessment_id=compliance_assessment_id,
            requirement_id=requirement_data['requirement_id'],
            requirement_title=requirement_data['title'],
            requirement_description=requirement_data['description'],
            framework=requirement_data['framework'],
            assessor_user_id=assessor_user_id,
            assessor_username=assessor_username,
            tags=requirement_data.get('tags', [])
        )

        # Set additional properties
        if 'framework_section' in requirement_data:
            req_assessment.framework_section = requirement_data['framework_section']
        if 'required_evidence_types' in requirement_data:
            req_assessment.required_evidence_types = requirement_data['required_evidence_types']

        req_assessment.save()
        return req_assessment

    def conduct_evidence_collection(
        self,
        assessment_id: str,
        evidence_data: Dict[str, Any],
        collector_user_id: uuid.UUID,
        collector_username: str
    ) -> Dict[str, Any]:
        """
        Conduct evidence collection for an assessment.

        Args:
            assessment_id: ID of the assessment
            evidence_data: Evidence collection data
            collector_user_id: ID of the collector
            collector_username: Username of the collector

        Returns:
            Evidence collection results
        """
        assessment = self.assessment_repo.get(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        if assessment.status == 'planned':
            assessment.start_assessment()

        # Update assessment status
        assessment.status = 'evidence_collection'
        assessment.save()

        # Process evidence for each requirement
        evidence_results = {
            'total_requirements': len(assessment.requirement_assessment_ids),
            'evidence_collected': 0,
            'evidence_sufficient': 0,
            'requirements_updated': []
        }

        for req_id in assessment.requirement_assessment_ids:
            requirement = self.requirement_repo.get(req_id)
            if not requirement:
                continue

            # Check if evidence provided for this requirement
            req_evidence = evidence_data.get(f"requirement_{req_id}", {})

            if req_evidence:
                # Add evidence to requirement
                evidence_id = req_evidence.get('evidence_id', str(uuid.uuid4()))
                evidence_type = req_evidence.get('evidence_type', 'document')

                requirement.add_evidence(evidence_id, evidence_type)
                requirement.assessment_start_date = timezone.now().date()

                if requirement.evidence_sufficiency in ['adequate', 'comprehensive']:
                    evidence_results['evidence_sufficient'] += 1

                evidence_results['evidence_collected'] += 1
                evidence_results['requirements_updated'].append({
                    'requirement_id': requirement.requirement_id,
                    'evidence_added': True,
                    'sufficiency': requirement.evidence_sufficiency
                })

                requirement.save()

        # Update assessment progress
        assessment.update_progress(
            assessed_requirements=evidence_results['evidence_collected']
        )
        assessment.save()

        return evidence_results

    def perform_requirement_evaluation(
        self,
        assessment_id: str,
        evaluations_data: Dict[str, Any],
        evaluator_user_id: uuid.UUID,
        evaluator_username: str
    ) -> Dict[str, Any]:
        """
        Perform requirement-by-requirement evaluation.

        Args:
            assessment_id: ID of the assessment
            evaluations_data: Evaluation data for requirements
            evaluator_user_id: ID of the evaluator
            evaluator_username: Username of the evaluator

        Returns:
            Evaluation results summary
        """
        assessment = self.assessment_repo.get(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        evaluation_results = {
            'total_requirements': len(assessment.requirement_assessment_ids),
            'evaluated_requirements': 0,
            'compliant_requirements': 0,
            'non_compliant_requirements': 0,
            'not_applicable_requirements': 0,
            'compensating_controls': 0,
            'findings_created': 0,
            'exceptions_created': 0,
            'requirements_needing_remediation': []
        }

        for req_id in assessment.requirement_assessment_ids:
            requirement = self.requirement_repo.get(req_id)
            if not requirement:
                continue

            # Get evaluation data for this requirement
            req_evaluation = evaluations_data.get(f"requirement_{req_id}", {})

            if not req_evaluation:
                continue

            # Update requirement assessment
            assessment_result = req_evaluation.get('assessment_result', 'insufficient_evidence')
            compliance_score = req_evaluation.get('compliance_score', 0.0)
            assessment_notes = req_evaluation.get('assessment_notes', '')
            methodology = req_evaluation.get('assessment_methodology', '')

            requirement.update_assessment_result(
                assessment_result=assessment_result,
                compliance_score=compliance_score,
                assessment_notes=assessment_notes,
                assessment_methodology=methodology
            )

            # Handle control implementations
            if 'implemented_controls' in req_evaluation:
                for control_data in req_evaluation['implemented_controls']:
                    requirement.add_implemented_control(
                        control_id=control_data['control_id'],
                        effectiveness=control_data.get('effectiveness', 'fully_implemented')
                    )

            # Handle compensating controls
            if 'compensating_controls' in req_evaluation:
                for comp_control in req_evaluation['compensating_controls']:
                    requirement.add_compensating_control(
                        control_id=comp_control['control_id'],
                        justification=comp_control['justification']
                    )
                    evaluation_results['compensating_controls'] += 1

            # Create findings for non-compliant requirements
            if assessment_result == 'non_compliant':
                finding = self._create_finding_from_requirement(
                    requirement, assessment, evaluator_user_id, evaluator_username
                )
                assessment.add_finding(str(finding.id))
                evaluation_results['findings_created'] += 1
                evaluation_results['requirements_needing_remediation'].append({
                    'requirement_id': requirement.requirement_id,
                    'finding_id': finding.finding_id,
                    'severity': finding.severity
                })

            # Update counters
            evaluation_results['evaluated_requirements'] += 1

            if assessment_result == 'compliant':
                evaluation_results['compliant_requirements'] += 1
            elif assessment_result == 'non_compliant':
                evaluation_results['non_compliant_requirements'] += 1
            elif assessment_result == 'not_applicable':
                evaluation_results['not_applicable_requirements'] += 1

            requirement.save()

        # Update assessment progress
        assessment.update_progress(
            assessed_requirements=evaluation_results['evaluated_requirements'],
            compliant_requirements=evaluation_results['compliant_requirements'],
            non_compliant_requirements=evaluation_results['non_compliant_requirements'],
            not_applicable_requirements=evaluation_results['not_applicable_requirements'],
            overall_score=self._calculate_overall_compliance_score(assessment)
        )
        assessment.save()

        return evaluation_results

    def _create_finding_from_requirement(
        self,
        requirement: RequirementAssessment,
        assessment: ComplianceAssessment,
        creator_user_id: uuid.UUID,
        creator_username: str
    ) -> ComplianceFinding:
        """Create a compliance finding from a non-compliant requirement"""
        finding_id = f"FIND-{assessment.assessment_id}-{requirement.requirement_id}"

        finding = ComplianceFinding()
        finding.create_finding(
            compliance_assessment_id=assessment.id,
            finding_id=finding_id,
            finding_title=f"Non-compliant: {requirement.requirement_title}",
            finding_description=f"Requirement {requirement.requirement_id} was assessed as non-compliant. {requirement.assessment_notes}",
            finding_type='non_conformity',
            severity=self._determine_finding_severity(requirement),
            framework=requirement.framework,
            identified_by_user_id=creator_user_id,
            identified_by_username=creator_username,
            tags=['auto-generated', 'requirement-assessment']
        )

        # Set additional finding details
        finding.root_cause = requirement.assessment_notes
        finding.related_requirement_ids = [str(requirement.id)]

        finding.save()
        return finding

    def _determine_finding_severity(self, requirement: RequirementAssessment) -> str:
        """Determine finding severity based on requirement criticality"""
        # This could be enhanced with more sophisticated logic
        # For now, use a simple mapping
        if 'critical' in requirement.requirement_title.lower():
            return 'critical'
        elif 'high' in requirement.requirement_title.lower():
            return 'high'
        elif 'confidentiality' in requirement.requirement_title.lower():
            return 'high'
        elif 'integrity' in requirement.requirement_title.lower():
            return 'high'
        else:
            return 'medium'

    def _calculate_overall_compliance_score(self, assessment: ComplianceAssessment) -> float:
        """Calculate overall compliance score for the assessment"""
        if assessment.assessed_requirements == 0:
            return 0.0

        # Weight compliant requirements more heavily
        compliant_weight = 1.0
        non_compliant_weight = 0.0
        not_applicable_weight = 0.5  # Partial credit for N/A items

        total_weighted_score = (
            assessment.compliant_requirements * compliant_weight +
            assessment.non_compliant_requirements * non_compliant_weight +
            assessment.not_applicable_requirements * not_applicable_weight
        )

        return round((total_weighted_score / assessment.assessed_requirements) * 100, 2)

    def generate_assessment_report(
        self,
        assessment_id: str,
        report_type: str = 'comprehensive'
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive assessment report.

        Args:
            assessment_id: ID of the assessment
            report_type: Type of report ('executive', 'technical', 'comprehensive')

        Returns:
            Assessment report data
        """
        assessment = self.assessment_repo.get(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # Get related entities
        requirements = [self.requirement_repo.get(req_id) for req_id in assessment.requirement_assessment_ids]
        requirements = [r for r in requirements if r is not None]

        findings = [self.finding_repo.get(find_id) for find_id in assessment.compliance_finding_ids]
        findings = [f for f in findings if f is not None]

        exceptions = [self.exception_repo.get(exc_id) for exc_id in assessment.compliance_exception_ids]
        exceptions = [e for e in exceptions if e is not None]

        report = {
            'assessment': {
                'id': assessment.assessment_id,
                'name': assessment.name,
                'framework': assessment.primary_framework,
                'status': assessment.status,
                'overall_score': assessment.overall_compliance_score,
                'compliance_level': assessment.compliance_level,
                'progress_percentage': assessment.progress_percentage,
                'completion_date': str(assessment.actual_completion_date) if assessment.actual_completion_date else None
            },
            'summary': {
                'total_requirements': assessment.total_requirements,
                'assessed_requirements': assessment.assessed_requirements,
                'compliant_requirements': assessment.compliant_requirements,
                'non_compliant_requirements': assessment.non_compliant_requirements,
                'not_applicable_requirements': assessment.not_applicable_requirements,
                'total_findings': len(findings),
                'total_exceptions': len(exceptions),
                'compensating_controls_count': assessment.compensating_controls_count
            },
            'generated_at': str(timezone.now())
        }

        if report_type in ['technical', 'comprehensive']:
            report['requirements'] = [{
                'id': req.requirement_id,
                'title': req.requirement_title,
                'assessment_result': req.assessment_result,
                'compliance_score': req.compliance_score,
                'evidence_sufficiency': req.evidence_sufficiency,
                'control_effectiveness': req.control_effectiveness
            } for req in requirements]

            report['findings'] = [{
                'id': finding.finding_id,
                'title': finding.finding_title,
                'type': finding.finding_type,
                'severity': finding.severity,
                'status': finding.status,
                'remediation_status': finding.remediation_status
            } for finding in findings]

        if report_type == 'comprehensive':
            report['exceptions'] = [{
                'id': exc.exception_id,
                'title': exc.exception_title,
                'type': exc.exception_type,
                'status': exc.status,
                'approved': exc.status == 'approved'
            } for exc in exceptions]

            # Add recommendations
            report['recommendations'] = self._generate_assessment_recommendations(assessment, findings, exceptions)

        return report

    def _generate_assessment_recommendations(
        self,
        assessment: ComplianceAssessment,
        findings: List[ComplianceFinding],
        exceptions: List[ComplianceException]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on assessment results"""
        recommendations = []

        # Compliance score recommendations
        if assessment.overall_compliance_score < 70:
            recommendations.append({
                'priority': 'critical',
                'category': 'compliance',
                'recommendation': 'Overall compliance score below acceptable threshold. Immediate remediation required.',
                'action_items': ['Review all non-compliant requirements', 'Prioritize critical findings', 'Develop remediation plan']
            })

        # Finding-based recommendations
        critical_findings = [f for f in findings if f.severity == 'critical' and f.status != 'closed']
        if critical_findings:
            recommendations.append({
                'priority': 'high',
                'category': 'findings',
                'recommendation': f'Address {len(critical_findings)} critical findings immediately.',
                'action_items': [f'Remediate finding {f.finding_id}' for f in critical_findings[:3]]
            })

        # Exception recommendations
        expired_exceptions = [e for e in exceptions if e.status == 'expired']
        if expired_exceptions:
            recommendations.append({
                'priority': 'high',
                'category': 'exceptions',
                'recommendation': f'{len(expired_exceptions)} exceptions have expired and require attention.',
                'action_items': ['Review expired exceptions', 'Determine renewal or remediation needs']
            })

        # Evidence recommendations
        requirements_with_insufficient_evidence = [
            req for req in self.requirement_repo.model.objects.filter(
                compliance_assessment_id=assessment.id,
                evidence_sufficiency='insufficient'
            )
        ]
        if requirements_with_insufficient_evidence:
            recommendations.append({
                'priority': 'medium',
                'category': 'evidence',
                'recommendation': f'{len(requirements_with_insufficient_evidence)} requirements lack sufficient evidence.',
                'action_items': ['Collect additional evidence', 'Re-evaluate requirement assessments']
            })

        return recommendations

    def validate_assessment_data(self, assessment_data: Dict[str, Any]) -> List[str]:
        """
        Validate assessment creation data.

        Args:
            assessment_data: Assessment data to validate

        Returns:
            List of validation error messages
        """
        errors = []

        required_fields = ['name', 'target_type', 'target_id', 'target_name', 'primary_framework']
        for field in required_fields:
            if field not in assessment_data or not assessment_data[field]:
                errors.append(f"Required field '{field}' is missing or empty")

        # Validate dates
        if 'planned_start_date' in assessment_data and 'planned_completion_date' in assessment_data:
            start_date = assessment_data['planned_start_date']
            end_date = assessment_data['planned_completion_date']
            if start_date and end_date and start_date >= end_date:
                errors.append("Planned completion date must be after planned start date")

        # Validate framework
        valid_frameworks = ['NIST SP 800-53', 'ISO 27001', 'COBIT', 'PCI DSS', 'HIPAA', 'GDPR', 'SOX']
        if 'primary_framework' in assessment_data:
            framework = assessment_data['primary_framework']
            if framework not in valid_frameworks:
                errors.append(f"Framework '{framework}' is not in the list of supported frameworks")

        # Validate priority
        if 'priority' in assessment_data:
            priority = assessment_data['priority']
            if priority not in ['critical', 'high', 'medium', 'low']:
                errors.append("Priority must be one of: critical, high, medium, low")

        return errors
