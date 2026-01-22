"""
Data Subject Right Aggregate

Aggregate for managing GDPR data subject rights requests, including
right of access, rectification, erasure, and other GDPR rights.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class DataSubjectRight(AggregateRoot):
    """
    Data Subject Right aggregate for managing GDPR data subject rights requests.

    Handles the complete lifecycle of data subject rights requests under GDPR,
    including submission, processing, fulfillment, and appeal processes.
    """

    # Request identification
    request_id = models.CharField(
        max_length=100,
        help_text="Unique request identifier (e.g., DSR-2024-001)"
    )

    # Data subject identification
    data_subject_id = models.CharField(
        max_length=255,
        help_text="Identifier for the data subject (email, user ID, etc.)"
    )

    data_subject_type = models.CharField(
        max_length=50,
        choices=[
            ('customer', 'Customer'),
            ('employee', 'Employee'),
            ('website_user', 'Website User'),
            ('prospect', 'Prospect'),
            ('supplier', 'Supplier'),
            ('other', 'Other'),
        ],
        default='customer',
        help_text="Type of data subject"
    )

    # Contact information
    contact_email = models.EmailField(
        blank=True,
        null=True,
        help_text="Email address for communication"
    )

    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Phone number for communication"
    )

    contact_address = models.TextField(
        blank=True,
        null=True,
        help_text="Postal address for communication"
    )

    # Rights requested (GDPR Article 15-22)
    RIGHT_TYPES = [
        ('access', 'Right of Access (Article 15)'),
        ('rectification', 'Right of Rectification (Article 16)'),
        ('erasure', 'Right to Erasure (Article 17)'),
        ('restriction', 'Right to Restriction (Article 18)'),
        ('portability', 'Right to Data Portability (Article 20)'),
        ('objection', 'Right to Object (Article 21)'),
        ('automated_decision_making', 'Rights re Automated Decision Making (Article 22)'),
        ('multiple_rights', 'Multiple Rights'),
    ]

    primary_right = models.CharField(
        max_length=30,
        choices=RIGHT_TYPES,
        help_text="Primary right being requested"
    )

    rights_requested = models.JSONField(
        default=list,
        blank=True,
        help_text="All rights requested in this submission"
    )

    # Request details
    request_description = models.TextField(
        help_text="Description of the request and what the data subject wants"
    )

    request_scope = models.TextField(
        blank=True,
        null=True,
        help_text="Scope of the request (specific data, time periods, etc.)"
    )

    # Request status
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('verification_pending', 'Verification Pending'),
        ('verification_failed', 'Verification Failed'),
        ('processing', 'Processing'),
        ('information_requested', 'Information Requested'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('appeal_pending', 'Appeal Pending'),
        ('appeal_completed', 'Appeal Completed'),
    ]

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='received',
        help_text="Current status of the rights request"
    )

    # Verification
    identity_verified = models.BooleanField(
        default=False,
        help_text="Whether data subject identity has been verified"
    )

    verification_method = models.CharField(
        max_length=50,
        choices=[
            ('email_verification', 'Email Verification'),
            ('document_verification', 'Document Verification'),
            ('knowledge_based', 'Knowledge-Based Authentication'),
            ('third_party', 'Third Party Verification'),
            ('legal_request', 'Legal Authority Request'),
        ],
        blank=True,
        null=True,
        help_text="Method used to verify identity"
    )

    verification_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when identity was verified"
    )

    # Processing timeline
    received_date = models.DateField(
        default=timezone.now,
        help_text="Date when request was received"
    )

    processing_start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when processing began"
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date by which request must be fulfilled (GDPR 30 days)"
    )

    completion_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when request was completed"
    )

    # Processing details
    assigned_to_user_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User ID assigned to process this request"
    )

    assigned_to_username = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Username assigned to process this request"
    )

    processing_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal processing notes"
    )

    # Data discovery and collection
    data_located = models.JSONField(
        default=list,
        blank=True,
        help_text="Systems/locations where data was found"
    )

    data_collected = models.BooleanField(
        default=False,
        help_text="Whether required data has been collected"
    )

    data_reviewed = models.BooleanField(
        default=False,
        help_text="Whether collected data has been reviewed"
    )

    # Response and fulfillment
    response_method = models.CharField(
        max_length=50,
        choices=[
            ('email', 'Email'),
            ('portal', 'Online Portal'),
            ('mail', 'Physical Mail'),
            ('phone', 'Phone'),
            ('in_person', 'In Person'),
        ],
        default='email',
        help_text="Method used to provide response"
    )

    response_sent = models.BooleanField(
        default=False,
        help_text="Whether response has been sent to data subject"
    )

    response_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when response was sent"
    )

    response_summary = models.TextField(
        blank=True,
        null=True,
        help_text="Summary of the response provided"
    )

    # Rejection details
    rejected = models.BooleanField(
        default=False,
        help_text="Whether request was rejected"
    )

    rejection_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for rejection"
    )

    rejection_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of rejection"
    )

    # Appeal process
    appeal_requested = models.BooleanField(
        default=False,
        help_text="Whether data subject appealed the decision"
    )

    appeal_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when appeal was requested"
    )

    appeal_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason for appeal"
    )

    appeal_decision = models.CharField(
        max_length=20,
        choices=[
            ('upheld', 'Decision Upheld'),
            ('overturned', 'Decision Overturned'),
            ('modified', 'Decision Modified'),
        ],
        blank=True,
        null=True,
        help_text="Result of appeal"
    )

    appeal_decision_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of appeal decision"
    )

    # Legal and compliance
    legal_review_required = models.BooleanField(
        default=False,
        help_text="Whether legal review was required"
    )

    legal_review_completed = models.BooleanField(
        default=False,
        help_text="Whether legal review was completed"
    )

    legal_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of legal review"
    )

    legal_findings = models.TextField(
        blank=True,
        null=True,
        help_text="Findings from legal review"
    )

    # Communication log
    communication_log = models.JSONField(
        default=list,
        blank=True,
        help_text="Log of all communications with data subject"
    )

    # Related entities
    related_data_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of data assets involved in this request"
    )

    related_consent_records = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related consent records"
    )

    related_processing_activities = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related processing activities"
    )

    # Audit and compliance
    audit_trail = models.JSONField(
        default=list,
        blank=True,
        help_text="Audit trail of all actions taken"
    )

    compliance_checklist = models.JSONField(
        default=dict,
        blank=True,
        help_text="Compliance checklist items and status"
    )

    # Cost and resource tracking
    processing_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.00,
        help_text="Hours spent processing this request"
    )

    processing_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost incurred processing this request"
    )

    # Metadata
    priority = models.CharField(
        max_length=10,
        choices=[
            ('urgent', 'Urgent'),
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium',
        help_text="Processing priority"
    )

    source = models.CharField(
        max_length=50,
        choices=[
            ('direct_request', 'Direct Request'),
            ('portal', 'Online Portal'),
            ('email', 'Email'),
            ('phone', 'Phone Call'),
            ('legal_request', 'Legal Authority Request'),
            ('third_party', 'Third Party Request'),
        ],
        default='direct_request',
        help_text="How the request was submitted"
    )

    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Request tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    class Meta:
        db_table = "privacy_data_subject_rights"
        indexes = [
            models.Index(fields=['data_subject_id'], name='dsr_subject_idx'),
            models.Index(fields=['status'], name='dsr_status_idx'),
            models.Index(fields=['primary_right'], name='dsr_right_type_idx'),
            models.Index(fields=['assigned_to_user_id'], name='dsr_assigned_idx'),
            models.Index(fields=['due_date'], name='dsr_due_date_idx'),
            models.Index(fields=['received_date'], name='dsr_received_idx'),
            models.Index(fields=['verification_date'], name='dsr_verified_idx'),
            models.Index(fields=['completion_date'], name='dsr_completed_idx'),
            models.Index(fields=['created_at'], name='dsr_created_idx'),
        ]
        ordering = ['-received_date']

    def submit_request(
        self,
        request_id: str,
        data_subject_id: str,
        primary_right: str,
        request_description: str,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        rights_requested: Optional[List[str]] = None,
        request_scope: Optional[str] = None
    ):
        """Submit a new data subject rights request"""
        self.request_id = request_id
        self.data_subject_id = data_subject_id
        self.primary_right = primary_right
        self.request_description = request_description
        self.contact_email = contact_email
        self.contact_phone = contact_phone
        self.rights_requested = rights_requested if rights_requested else [primary_right]
        self.request_scope = request_scope
        self.status = 'received'

        # Set due date (GDPR requires response within 30 days)
        self.due_date = self.received_date + timezone.timedelta(days=30)

        from .domain_events import DataSubjectRightRequested
        self._raise_event(DataSubjectRightRequested(
            aggregate_id=self.id,
            request_id=request_id,
            data_subject_id=data_subject_id,
            primary_right=primary_right,
            due_date=str(self.due_date)
        ))

    def verify_identity(self, verification_method: str):
        """Verify the data subject's identity"""
        if self.status == 'received':
            self.identity_verified = True
            self.verification_method = verification_method
            self.verification_date = timezone.now().date()
            self.status = 'processing'

            from .domain_events import DataSubjectRightProcessed
            self._raise_event(DataSubjectRightProcessed(
                aggregate_id=self.id,
                request_id=self.request_id,
                verification_completed=True,
                verification_method=verification_method
            ))

    def fail_verification(self, reason: str):
        """Mark identity verification as failed"""
        self.status = 'verification_failed'

        # Add to audit trail
        audit_entry = {
            'action': 'verification_failed',
            'reason': reason,
            'failed_at': str(timezone.now())
        }

        if not self.audit_trail:
            self.audit_trail = []
        self.audit_trail.append(audit_entry)

        from .domain_events import DataSubjectRightProcessed
        self._raise_event(DataSubjectRightProcessed(
            aggregate_id=self.id,
            request_id=self.request_id,
            verification_failed=True,
            reason=reason
        ))

    def assign_processor(self, assigned_to_user_id: uuid.UUID, assigned_to_username: str):
        """Assign a processor to handle this request"""
        self.assigned_to_user_id = assigned_to_user_id
        self.assigned_to_username = assigned_to_username
        self.processing_start_date = timezone.now().date()

        from .domain_events import DataSubjectRightProcessed
        self._raise_event(DataSubjectRightProcessed(
            aggregate_id=self.id,
            request_id=self.request_id,
            assigned_to=str(assigned_to_user_id)
        ))

    def locate_data(self, data_locations: List[Dict[str, Any]]):
        """Record data discovery results"""
        self.data_located = data_locations
        self.data_collected = True

        from .domain_events import DataSubjectRightProcessed
        self._raise_event(DataSubjectRightProcessed(
            aggregate_id=self.id,
            request_id=self.request_id,
            data_located=len(data_locations)
        ))

    def request_additional_information(self, information_requested: str):
        """Request additional information from data subject"""
        self.status = 'information_requested'

        # Add to communication log
        communication_entry = {
            'type': 'outbound',
            'method': 'email',
            'subject': 'Additional Information Required',
            'content': information_requested,
            'sent_at': str(timezone.now())
        }

        if not self.communication_log:
            self.communication_log = []
        self.communication_log.append(communication_entry)

        from .domain_events import DataSubjectRightProcessed
        self._raise_event(DataSubjectRightProcessed(
            aggregate_id=self.id,
            request_id=self.request_id,
            information_requested=True
        ))

    def fulfill_request(self, response_summary: str, response_method: str = 'email'):
        """Fulfill the data subject rights request"""
        self.response_summary = response_summary
        self.response_method = response_method
        self.response_sent = True
        self.response_date = timezone.now().date()
        self.status = 'completed'
        self.completion_date = timezone.now().date()

        # Add to communication log
        communication_entry = {
            'type': 'outbound',
            'method': response_method,
            'subject': 'Data Subject Rights Request Response',
            'content': response_summary,
            'sent_at': str(timezone.now())
        }

        if not self.communication_log:
            self.communication_log = []
        self.communication_log.append(communication_entry)

        from .domain_events import DataSubjectRightCompleted
        self._raise_event(DataSubjectRightCompleted(
            aggregate_id=self.id,
            request_id=self.request_id,
            completion_date=str(self.completion_date),
            response_method=response_method
        ))

    def reject_request(self, rejection_reason: str):
        """Reject the data subject rights request"""
        self.rejected = True
        self.rejection_reason = rejection_reason
        self.rejection_date = timezone.now().date()
        self.status = 'rejected'

        # Add to communication log
        communication_entry = {
            'type': 'outbound',
            'method': 'email',
            'subject': 'Data Subject Rights Request - Decision',
            'content': f"Request rejected: {rejection_reason}",
            'sent_at': str(timezone.now())
        }

        if not self.communication_log:
            self.communication_log = []
        self.communication_log.append(communication_entry)

        from .domain_events import DataSubjectRightRejected
        self._raise_event(DataSubjectRightRejected(
            aggregate_id=self.id,
            request_id=self.request_id,
            rejection_reason=rejection_reason
        ))

    def submit_appeal(self, appeal_reason: str):
        """Submit an appeal against the decision"""
        self.appeal_requested = True
        self.appeal_date = timezone.now().date()
        self.appeal_reason = appeal_reason
        self.status = 'appeal_pending'

        from .domain_events import DataSubjectRightProcessed
        self._raise_event(DataSubjectRightProcessed(
            aggregate_id=self.id,
            request_id=self.request_id,
            appeal_submitted=True,
            appeal_reason=appeal_reason
        ))

    def resolve_appeal(self, appeal_decision: str, decision_details: str):
        """Resolve the appeal"""
        self.appeal_decision = appeal_decision
        self.appeal_decision_date = timezone.now().date()
        self.status = 'appeal_completed'

        # Update status based on appeal decision
        if appeal_decision == 'overturned':
            self.status = 'processing'  # Re-process the request
            self.rejected = False
        elif appeal_decision == 'modified':
            # Handle partial success
            pass

        from .domain_events import DataSubjectRightProcessed
        self._raise_event(DataSubjectRightProcessed(
            aggregate_id=self.id,
            request_id=self.request_id,
            appeal_resolved=True,
            appeal_decision=appeal_decision
        ))

    def add_communication(self, communication_type: str, method: str, subject: str, content: str):
        """Add a communication to the log"""
        communication_entry = {
            'type': communication_type,
            'method': method,
            'subject': subject,
            'content': content,
            'sent_at': str(timezone.now())
        }

        if not self.communication_log:
            self.communication_log = []
        self.communication_log.append(communication_entry)

    def update_processing_time(self, hours_spent: float):
        """Update time spent processing this request"""
        self.processing_hours += hours_spent

    def conduct_legal_review(self, legal_findings: str):
        """Conduct legal review of the request"""
        self.legal_review_completed = True
        self.legal_review_date = timezone.now().date()
        self.legal_findings = legal_findings

    @property
    def is_overdue(self) -> bool:
        """Check if the request is overdue"""
        if not self.due_date or self.status in ['completed', 'rejected']:
            return False
        return timezone.now().date() > self.due_date

    @property
    def days_overdue(self) -> int:
        """Calculate days overdue"""
        if not self.is_overdue:
            return 0
        return (timezone.now().date() - self.due_date).days

    @property
    def days_to_due(self) -> Optional[int]:
        """Calculate days until due"""
        if not self.due_date or self.status in ['completed', 'rejected']:
            return None
        return (self.due_date - timezone.now().date()).days

    @property
    def processing_duration_days(self) -> Optional[int]:
        """Calculate processing duration"""
        if not self.processing_start_date or not self.completion_date:
            return None
        return (self.completion_date - self.processing_start_date).days

    @property
    def requires_urgent_attention(self) -> bool:
        """Check if request requires urgent attention"""
        return (
            self.is_overdue or
            self.priority == 'urgent' or
            self.status in ['appeal_pending', 'verification_failed'] or
            (self.days_to_due is not None and self.days_to_due <= 7)
        )

    @property
    def compliance_score(self) -> float:
        """Calculate compliance score for this request handling"""
        # Simplified scoring based on timeliness and completion
        if self.status == 'completed':
            if not self.is_overdue:
                return 100.0
            else:
                # Partial credit for completion, even if late
                return max(50.0, 100.0 - (self.days_overdue * 2))
        elif self.status == 'rejected':
            return 75.0  # Assuming rejection was justified
        else:
            return 0.0

    def get_audit_trail_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of the audit trail"""
        return [{
            'action': entry.get('action', 'unknown'),
            'timestamp': entry.get('timestamp') or entry.get('sent_at') or str(self.created_at),
            'details': entry
        } for entry in self.audit_trail]

    def __str__(self):
        return f"DataSubjectRight({self.request_id}: {self.data_subject_id} - {self.primary_right} - {self.status})"
