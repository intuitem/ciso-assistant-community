"""
Security Incident Aggregate

Aggregate for managing security incidents, including detection, response,
containment, eradication, recovery, and lessons learned.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class SecurityIncident(AggregateRoot):
    """
    Security Incident aggregate for comprehensive incident management.

    Manages the complete incident response lifecycle from detection through
    post-incident analysis, including containment, eradication, recovery,
    and lessons learned.
    """

    # Incident identification
    incident_id = models.CharField(
        max_length=100,
        help_text="Unique incident identifier (e.g., INC-2024-001)"
    )

    title = models.CharField(
        max_length=500,
        help_text="Incident title/summary"
    )

    description = models.TextField(
        help_text="Detailed incident description"
    )

    # Incident classification
    INCIDENT_CATEGORIES = [
        ('malware', 'Malware Infection'),
        ('phishing', 'Phishing/Social Engineering'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('data_breach', 'Data Breach'),
        ('denial_of_service', 'Denial of Service'),
        ('insider_threat', 'Insider Threat'),
        ('physical_security', 'Physical Security'),
        ('policy_violation', 'Policy Violation'),
        ('third_party_compromise', 'Third Party Compromise'),
        ('supply_chain_attack', 'Supply Chain Attack'),
        ('ransomware', 'Ransomware'),
        ('other', 'Other'),
    ]

    category = models.CharField(
        max_length=30,
        choices=INCIDENT_CATEGORIES,
        default='other',
        help_text="Incident category"
    )

    subcategory = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="More specific incident subcategory"
    )

    # Incident severity and impact
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    severity = models.CharField(
        max_length=10,
        choices=SEVERITY_LEVELS,
        default='medium',
        help_text="Incident severity level"
    )

    # Incident priority (calculated)
    PRIORITY_LEVELS = [
        ('p1', 'P1 - Critical'),
        ('p2', 'P2 - High'),
        ('p3', 'P3 - Medium'),
        ('p4', 'P4 - Low'),
    ]

    priority = models.CharField(
        max_length=5,
        choices=PRIORITY_LEVELS,
        default='p3',
        help_text="Incident response priority"
    )

    # Incident status
    STATUS_CHOICES = [
        ('detected', 'Detected'),
        ('investigating', 'Investigating'),
        ('contained', 'Contained'),
        ('eradicating', 'Eradicating'),
        ('recovering', 'Recovering'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('false_positive', 'False Positive'),
    ]

    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='detected',
        help_text="Current incident status"
    )

    # Detection and reporting
    detection_method = models.CharField(
        max_length=50,
        choices=[
            ('automated_monitoring', 'Automated Monitoring'),
            ('manual_report', 'Manual Report'),
            ('security_tool', 'Security Tool Alert'),
            ('external_report', 'External Report'),
            ('audit_finding', 'Audit Finding'),
            ('customer_report', 'Customer Report'),
            ('other', 'Other'),
        ],
        help_text="How the incident was detected"
    )

    detection_date = models.DateTimeField(
        help_text="When the incident was first detected"
    )

    reported_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the incident was officially reported"
    )

    reported_by_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of person who reported the incident"
    )

    reported_by_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of person who reported the incident"
    )

    # Incident timeline
    investigation_start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When investigation began"
    )

    containment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When incident was contained"
    )

    eradication_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When eradication was completed"
    )

    recovery_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When recovery was completed"
    )

    resolution_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When incident was fully resolved"
    )

    closure_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When incident was closed"
    )

    # Incident response team
    assigned_analyst_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID of assigned incident analyst"
    )

    assigned_analyst_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username of assigned incident analyst"
    )

    response_team = models.JSONField(
        default=list,
        blank=True,
        help_text="Incident response team members and roles"
    )

    # Affected systems and data
    affected_systems = models.JSONField(
        default=list,
        blank=True,
        help_text="Systems affected by the incident"
    )

    affected_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="Assets affected by the incident"
    )

    affected_data = models.JSONField(
        default=list,
        blank=True,
        help_text="Data affected by the incident"
    )

    # Business impact assessment
    business_impact = models.CharField(
        max_length=20,
        choices=[
            ('none', 'No Impact'),
            ('minimal', 'Minimal'),
            ('moderate', 'Moderate'),
            ('significant', 'Significant'),
            ('severe', 'Severe'),
            ('critical', 'Critical'),
        ],
        default='minimal',
        help_text="Business impact level"
    )

    impact_description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of business impact"
    )

    financial_impact = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated financial impact"
    )

    operational_impact = models.TextField(
        blank=True,
        null=True,
        help_text="Operational impact description"
    )

    # Root cause analysis
    root_cause = models.TextField(
        blank=True,
        null=True,
        help_text="Root cause analysis"
    )

    contributing_factors = models.JSONField(
        default=list,
        blank=True,
        help_text="Contributing factors to the incident"
    )

    # Containment actions
    containment_actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Actions taken to contain the incident"
    )

    containment_effectiveness = models.CharField(
        max_length=20,
        choices=[
            ('fully_effective', 'Fully Effective'),
            ('partially_effective', 'Partially Effective'),
            ('ineffective', 'Ineffective'),
            ('not_applicable', 'Not Applicable'),
        ],
        default='not_applicable',
        help_text="Effectiveness of containment actions"
    )

    # Eradication actions
    eradication_actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Actions taken to eradicate the threat"
    )

    eradication_effectiveness = models.CharField(
        max_length=20,
        choices=[
            ('fully_effective', 'Fully Effective'),
            ('partially_effective', 'Partially Effective'),
            ('ineffective', 'Ineffective'),
            ('not_applicable', 'Not Applicable'),
        ],
        default='not_applicable',
        help_text="Effectiveness of eradication actions"
    )

    # Recovery actions
    recovery_actions = models.JSONField(
        default=list,
        blank=True,
        help_text="Actions taken to recover from the incident"
    )

    recovery_effectiveness = models.CharField(
        max_length=20,
        choices=[
            ('fully_effective', 'Fully Effective'),
            ('partially_effective', 'Partially Effective'),
            ('ineffective', 'Ineffective'),
            ('not_applicable', 'Not Applicable'),
        ],
        default='not_applicable',
        help_text="Effectiveness of recovery actions"
    )

    # Lessons learned
    lessons_learned = models.TextField(
        blank=True,
        null=True,
        help_text="Lessons learned from the incident"
    )

    preventive_measures = models.JSONField(
        default=list,
        blank=True,
        help_text="Preventive measures recommended"
    )

    process_improvements = models.JSONField(
        default=list,
        blank=True,
        help_text="Process improvements identified"
    )

    # Communication and notification
    stakeholders_notified = models.JSONField(
        default=list,
        blank=True,
        help_text="Stakeholders who were notified"
    )

    external_notifications = models.JSONField(
        default=list,
        blank=True,
        help_text="External parties notified (regulators, customers, etc.)"
    )

    public_disclosure = models.BooleanField(
        default=False,
        help_text="Whether incident was publicly disclosed"
    )

    disclosure_details = models.TextField(
        blank=True,
        null=True,
        help_text="Details of public disclosure"
    )

    # Evidence and documentation
    evidence_collected = models.JSONField(
        default=list,
        blank=True,
        help_text="Evidence collected during investigation"
    )

    investigation_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed investigation notes"
    )

    supporting_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Supporting documents and attachments"
    )

    # Incident metrics
    time_to_detection = models.DurationField(
        null=True,
        blank=True,
        help_text="Time from incident occurrence to detection"
    )

    time_to_containment = models.DurationField(
        null=True,
        blank=True,
        help_text="Time from detection to containment"
    )

    time_to_resolution = models.DurationField(
        null=True,
        blank=True,
        help_text="Time from detection to resolution"
    )

    # Incident classification (NIST categories)
    nist_category = models.CharField(
        max_length=50,
        choices=[
            ('reconnaissance', 'Reconnaissance'),
            ('weaponization', 'Weaponization'),
            ('delivery', 'Delivery'),
            ('exploitation', 'Exploitation'),
            ('installation', 'Installation'),
            ('command_and_control', 'Command and Control'),
            ('actions_on_objectives', 'Actions on Objectives'),
        ],
        blank=True,
        null=True,
        help_text="NIST incident category"
    )

    # Integration with other contexts
    related_risks = models.JSONField(
        default=list,
        blank=True,
        help_text="Related risks from Risk Registers"
    )

    related_findings = models.JSONField(
        default=list,
        blank=True,
        help_text="Related compliance findings"
    )

    related_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="Related assets affected"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Incident tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    # Calculated fields
    response_effectiveness_score = models.IntegerField(
        default=0,
        help_text="Overall response effectiveness score (0-100)"
    )

    class Meta:
        db_table = "security_incidents"
        indexes = [
            models.Index(fields=['status'], name='incident_status_idx'),
            models.Index(fields=['severity'], name='incident_severity_idx'),
            models.Index(fields=['category'], name='incident_category_idx'),
            models.Index(fields=['priority'], name='incident_priority_idx'),
            models.Index(fields=['detection_date'], name='incident_detection_idx'),
            models.Index(fields=['assigned_analyst_user_id'], name='incident_analyst_idx'),
            models.Index(fields=['business_impact'], name='incident_impact_idx'),
            models.Index(fields=['created_at'], name='incident_created_idx'),
        ]
        ordering = ['-detection_date']

    def create_incident(
        self,
        incident_id: str,
        title: str,
        description: str,
        category: str,
        severity: str,
        detection_method: str,
        detection_date: timezone.datetime,
        reported_by_user_id: Optional[uuid.UUID] = None,
        reported_by_username: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        """Create a new security incident"""
        self.incident_id = incident_id
        self.title = title
        self.description = description
        self.category = category
        self.severity = severity
        self.detection_method = detection_method
        self.detection_date = detection_date
        self.reported_by_user_id = reported_by_user_id
        self.reported_by_username = reported_by_username
        self.tags = tags if tags is not None else []

        # Set default priority based on severity
        self._calculate_priority()

        # Set initial status
        self.status = 'detected'

        from .domain_events import SecurityIncidentCreated
        self._raise_event(SecurityIncidentCreated(
            aggregate_id=self.id,
            incident_id=incident_id,
            title=title,
            severity=severity,
            category=category
        ))

    def assign_analyst(
        self,
        analyst_user_id: uuid.UUID,
        analyst_username: str
    ):
        """Assign an analyst to the incident"""
        self.assigned_analyst_user_id = analyst_user_id
        self.assigned_analyst_username = analyst_username
        self.investigation_start_date = timezone.now()

        from .domain_events import SecurityIncidentAssigned
        self._raise_event(SecurityIncidentAssigned(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            analyst_user_id=str(analyst_user_id)
        ))

    def update_status(
        self,
        new_status: str,
        status_notes: Optional[str] = None
    ):
        """Update incident status"""
        old_status = self.status
        self.status = new_status

        # Set timestamps based on status
        if new_status == 'contained' and not self.containment_date:
            self.containment_date = timezone.now()
        elif new_status == 'eradicating':
            # Transition to eradicating
            pass
        elif new_status == 'recovering' and not self.recovery_date:
            self.recovery_date = timezone.now()
        elif new_status == 'resolved' and not self.resolution_date:
            self.resolution_date = timezone.now()
        elif new_status == 'closed' and not self.closure_date:
            self.closure_date = timezone.now()

        from .domain_events import SecurityIncidentStatusUpdated
        self._raise_event(SecurityIncidentStatusUpdated(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            old_status=old_status,
            new_status=new_status
        ))

    def record_containment_actions(self, actions: List[Dict[str, Any]], effectiveness: str):
        """Record containment actions"""
        self.containment_actions = actions
        self.containment_effectiveness = effectiveness
        self.containment_date = timezone.now()

        from .domain_events import SecurityIncidentContained
        self._raise_event(SecurityIncidentContained(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            containment_date=str(self.containment_date)
        ))

    def record_eradication_actions(self, actions: List[Dict[str, Any]], effectiveness: str):
        """Record eradication actions"""
        self.eradication_actions = actions
        self.eradication_effectiveness = effectiveness
        self.eradication_date = timezone.now()

        from .domain_events import SecurityIncidentEradicated
        self._raise_event(SecurityIncidentEradicated(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            eradication_date=str(self.eradication_date)
        ))

    def record_recovery_actions(self, actions: List[Dict[str, Any]], effectiveness: str):
        """Record recovery actions"""
        self.recovery_actions = actions
        self.recovery_effectiveness = effectiveness
        self.recovery_date = timezone.now()

        from .domain_events import SecurityIncidentRecovered
        self._raise_event(SecurityIncidentRecovered(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            recovery_date=str(self.recovery_date)
        ))

    def complete_incident(
        self,
        resolution_date: Optional[timezone.datetime] = None,
        lessons_learned: Optional[str] = None,
        preventive_measures: Optional[List[str]] = None
    ):
        """Mark incident as resolved and record lessons learned"""
        self.status = 'resolved'
        self.resolution_date = resolution_date or timezone.now()

        if lessons_learned:
            self.lessons_learned = lessons_learned
        if preventive_measures:
            self.preventive_measures = preventive_measures

        # Calculate response metrics
        self._calculate_response_metrics()
        self._calculate_response_effectiveness()

        from .domain_events import SecurityIncidentResolved
        self._raise_event(SecurityIncidentResolved(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            resolution_date=str(self.resolution_date)
        ))

    def close_incident(self, closure_date: Optional[timezone.datetime] = None):
        """Close the incident"""
        self.status = 'closed'
        self.closure_date = closure_date or timezone.now()

        from .domain_events import SecurityIncidentClosed
        self._raise_event(SecurityIncidentClosed(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            closure_date=str(self.closure_date)
        ))

    def add_evidence(self, evidence_type: str, evidence_data: Dict[str, Any]):
        """Add evidence to the incident"""
        evidence_entry = {
            'id': str(uuid.uuid4()),
            'type': evidence_type,
            'data': evidence_data,
            'collected_at': str(timezone.now()),
            'collected_by': str(getattr(self, 'updated_by', None))
        }

        if not self.evidence_collected:
            self.evidence_collected = []
        self.evidence_collected.append(evidence_entry)

    def notify_stakeholders(self, stakeholders: List[Dict[str, Any]]):
        """Record stakeholder notifications"""
        if not self.stakeholders_notified:
            self.stakeholders_notified = []

        for stakeholder in stakeholders:
            notification = {
                'stakeholder': stakeholder,
                'notified_at': str(timezone.now()),
                'method': stakeholder.get('notification_method', 'email')
            }
            self.stakeholders_notified.append(notification)

    def assess_impact(self, business_impact: str, financial_impact: Optional[float] = None,
                     operational_impact: Optional[str] = None):
        """Assess and record incident impact"""
        self.business_impact = business_impact
        if financial_impact is not None:
            self.financial_impact = financial_impact
        if operational_impact:
            self.operational_impact = operational_impact

        from .domain_events import SecurityIncidentImpactAssessed
        self._raise_event(SecurityIncidentImpactAssessed(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            business_impact=business_impact,
            financial_impact=financial_impact
        ))

    def perform_root_cause_analysis(self, root_cause: str, contributing_factors: List[str]):
        """Perform and record root cause analysis"""
        self.root_cause = root_cause
        self.contributing_factors = contributing_factors

        from .domain_events import SecurityIncidentRootCauseAnalyzed
        self._raise_event(SecurityIncidentRootCauseAnalyzed(
            aggregate_id=self.id,
            incident_id=self.incident_id,
            root_cause=root_cause
        ))

    def _calculate_priority(self):
        """Calculate incident priority based on severity and other factors"""
        severity_weights = {
            'low': 1,
            'medium': 2,
            'high': 3,
            'critical': 4
        }

        base_priority = severity_weights.get(self.severity, 2)

        # Adjust for category
        if self.category in ['ransomware', 'data_breach', 'supply_chain_attack']:
            base_priority += 1

        # Adjust for business impact
        impact_weights = {
            'none': 0,
            'minimal': 1,
            'moderate': 2,
            'significant': 3,
            'severe': 4,
            'critical': 5
        }

        impact_weight = impact_weights.get(self.business_impact, 1)
        final_priority = min(base_priority + impact_weight, 4)

        priority_map = {1: 'p4', 2: 'p3', 3: 'p2', 4: 'p1'}
        self.priority = priority_map.get(final_priority, 'p3')

    def _calculate_response_metrics(self):
        """Calculate incident response time metrics"""
        if self.containment_date and self.detection_date:
            self.time_to_containment = self.containment_date - self.detection_date

        if self.resolution_date and self.detection_date:
            self.time_to_resolution = self.resolution_date - self.detection_date

    def _calculate_response_effectiveness(self):
        """Calculate overall response effectiveness score"""
        effectiveness_factors = {
            'containment_effectiveness': self._get_effectiveness_score(self.containment_effectiveness),
            'eradication_effectiveness': self._get_effectiveness_score(self.eradication_effectiveness),
            'recovery_effectiveness': self._get_effectiveness_score(self.recovery_effectiveness),
            'evidence_quality': 80 if self.evidence_collected else 40,
            'lessons_learned': 90 if self.lessons_learned else 50,
            'preventive_measures': 85 if self.preventive_measures else 45
        }

        average_effectiveness = sum(effectiveness_factors.values()) / len(effectiveness_factors)
        self.response_effectiveness_score = round(average_effectiveness)

    def _get_effectiveness_score(self, effectiveness: str) -> int:
        """Convert effectiveness string to numeric score"""
        scores = {
            'not_applicable': 50,
            'ineffective': 20,
            'partially_effective': 60,
            'fully_effective': 100
        }
        return scores.get(effectiveness, 50)

    @property
    def is_active(self) -> bool:
        """Check if incident is still active"""
        return self.status not in ['resolved', 'closed', 'false_positive']

    @property
    def response_time_sla_met(self) -> bool:
        """Check if incident response met SLA requirements"""
        # Simplified SLA check - could be enhanced with configurable SLAs
        if not self.time_to_containment:
            return False

        # SLA: P1 within 1 hour, P2 within 4 hours, P3 within 24 hours, P4 within 72 hours
        sla_hours = {
            'p1': 1,
            'p2': 4,
            'p3': 24,
            'p4': 72
        }

        required_hours = sla_hours.get(self.priority, 24)
        actual_hours = self.time_to_containment.total_seconds() / 3600

        return actual_hours <= required_hours

    @property
    def total_response_time_hours(self) -> Optional[float]:
        """Get total response time in hours"""
        if not self.time_to_resolution:
            return None
        return self.time_to_resolution.total_seconds() / 3600

    @property
    def incident_age_days(self) -> int:
        """Get incident age in days"""
        return (timezone.now() - self.detection_date).days

    @property
    def requires_follow_up(self) -> bool:
        """Check if incident requires follow-up actions"""
        return (
            self.status == 'resolved' and
            not self.lessons_learned or
            not self.preventive_measures
        )

    def __str__(self):
        return f"SecurityIncident({self.incident_id}: {self.title} - {self.severity} - {self.status})"
