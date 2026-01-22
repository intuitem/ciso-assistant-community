"""
Compliance Projection Handlers

Update read models based on Compliance domain events.
"""

from core.domain.events import EventHandler, DomainEvent
from ..read_models.compliance_posture_by_framework import CompliancePostureByFramework
from ..aggregates.compliance_framework import ComplianceFramework
from ..aggregates.requirement import Requirement
from ..associations.compliance_finding import ComplianceFinding
from ..associations.compliance_exception import ComplianceException
from ..associations.compliance_audit import ComplianceAudit


class ComplianceProjectionHandler(EventHandler):
    """
    Handler that updates CompliancePostureByFramework read model from domain events.
    
    This handler listens to compliance-related domain events and updates
    the denormalized CompliancePostureByFramework read model for efficient querying.
    """
    
    def handle(self, event: DomainEvent):
        """Handle domain events and update read model"""
        event_type = event.event_type
        
        # Determine which framework this event relates to
        framework_id = None
        
        if event_type.startswith("ComplianceFramework"):
            framework_id = event.aggregate_id
        elif event_type.startswith("Requirement"):
            # Get framework_id from requirement
            requirement_id = event.aggregate_id
            try:
                requirement = Requirement.objects.get(id=requirement_id)
                framework_id = requirement.frameworkId
            except Requirement.DoesNotExist:
                pass
        elif event_type.startswith("ComplianceFinding"):
            # Findings may reference requirements, which reference frameworks
            # This is more complex and would need to be handled differently
            pass
        elif event_type.startswith("ComplianceException"):
            # Exceptions reference requirements
            exception_id = event.aggregate_id
            try:
                from ..associations.compliance_exception import ComplianceException
                exception = ComplianceException.objects.get(id=exception_id)
                requirement = Requirement.objects.get(id=exception.requirementId)
                framework_id = requirement.frameworkId
            except (ComplianceException.DoesNotExist, Requirement.DoesNotExist):
                pass
        
        if framework_id:
            self._update_posture(framework_id)
    
    def _update_posture(self, framework_id):
        """
        Update compliance posture for a specific framework.
        
        Args:
            framework_id: UUID of the framework
        """
        try:
            framework = ComplianceFramework.objects.get(id=framework_id)
        except ComplianceFramework.DoesNotExist:
            return
        
        # Get all requirements for this framework
        requirements = Requirement.objects.filter(frameworkId=framework_id)
        total_requirements = requirements.count()
        active_requirements = requirements.filter(
            lifecycle_state=Requirement.LifecycleState.ACTIVE
        ).count()
        requirements_with_controls = sum(
            1 for r in requirements if len(r.mappedControlIds) > 0
        )
        coverage_percentage = (
            (requirements_with_controls / total_requirements * 100)
            if total_requirements > 0 else 0.0
        )
        
        # Get findings for requirements in this framework
        requirement_ids = list(requirements.values_list('id', flat=True))
        findings = ComplianceFinding.objects.filter(requirementIds__overlap=requirement_ids)
        
        open_findings = sum(1 for f in findings if f.lifecycle_state == "open")
        triaged_findings = sum(1 for f in findings if f.lifecycle_state == "triaged")
        remediating_findings = sum(1 for f in findings if f.lifecycle_state == "remediating")
        verified_findings = sum(1 for f in findings if f.lifecycle_state == "verified")
        closed_findings = sum(1 for f in findings if f.lifecycle_state == "closed")
        
        # Get exceptions for requirements in this framework
        exceptions = ComplianceException.objects.filter(requirementId__in=requirement_ids)
        active_exceptions = sum(1 for e in exceptions if e.lifecycle_state == "approved")
        expired_exceptions = sum(1 for e in exceptions if e.lifecycle_state == "expired")
        
        # Get audits for this framework
        audits = ComplianceAudit.objects.filter(scopeFrameworkIds__contains=[framework_id])
        total_audits = audits.count()
        recent_audit = audits.order_by('-start_date').first()
        recent_audit_date = recent_audit.start_date if recent_audit else None
        
        # Update or create the posture record
        CompliancePostureByFramework.objects.update_or_create(
            framework_id=framework_id,
            defaults={
                "framework_name": framework.name,
                "framework_version": framework.version,
                "total_requirements": total_requirements,
                "active_requirements": active_requirements,
                "requirements_with_controls": requirements_with_controls,
                "coverage_percentage": coverage_percentage,
                "open_findings_count": open_findings,
                "triaged_findings_count": triaged_findings,
                "remediating_findings_count": remediating_findings,
                "verified_findings_count": verified_findings,
                "closed_findings_count": closed_findings,
                "active_exceptions_count": active_exceptions,
                "expired_exceptions_count": expired_exceptions,
                "total_audits": total_audits,
                "recent_audit_date": recent_audit_date,
            }
        )

