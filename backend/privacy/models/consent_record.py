"""
Consent Record Aggregate

Aggregate for managing data subject consent records, including consent types,
purposes, validity periods, and consent withdrawal tracking.
"""

import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.utils import timezone
from core.domain.aggregate import AggregateRoot


class ConsentRecord(AggregateRoot):
    """
    Consent Record aggregate for comprehensive consent management.

    Manages data subject consent for data processing activities, including
    consent types, purposes, validity, withdrawal, and audit trails.
    """

    # Consent identification
    consent_id = models.CharField(
        max_length=100,
        help_text="Unique consent identifier (e.g., CONS-2024-001)"
    )

    # Data subject identification
    data_subject_id = models.CharField(
        max_length=255,
        help_text="Identifier for the data subject (e.g., user ID, email)"
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

    # Consent details
    consent_given = models.BooleanField(
        default=False,
        help_text="Whether consent has been given"
    )

    consent_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when consent was given"
    )

    consent_method = models.CharField(
        max_length=50,
        choices=[
            ('digital_signature', 'Digital Signature'),
            ('checkbox', 'Checkbox/Click'),
            ('written', 'Written Consent'),
            ('verbal', 'Verbal Consent'),
            ('implied', 'Implied Consent'),
            ('opt_in_email', 'Opt-in Email'),
            ('opt_in_form', 'Opt-in Form'),
        ],
        help_text="Method used to obtain consent"
    )

    # Processing purposes and scope
    processing_purposes = models.JSONField(
        default=list,
        blank=True,
        help_text="Specific purposes for which consent is given"
    )

    data_categories = models.JSONField(
        default=list,
        blank=True,
        help_text="Categories of personal data covered by consent"
    )

    recipients = models.JSONField(
        default=list,
        blank=True,
        help_text="Third parties that may receive the data"
    )

    # Consent validity
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date from which consent is valid"
    )

    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date until which consent is valid"
    )

    is_permanent = models.BooleanField(
        default=False,
        help_text="Whether consent is permanent (no expiry)"
    )

    # Consent withdrawal
    withdrawn = models.BooleanField(
        default=False,
        help_text="Whether consent has been withdrawn"
    )

    withdrawal_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when consent was withdrawn"
    )

    withdrawal_method = models.CharField(
        max_length=50,
        choices=[
            ('digital_request', 'Digital Request'),
            ('email', 'Email Request'),
            ('phone', 'Phone Request'),
            ('written', 'Written Request'),
            ('account_deletion', 'Account Deletion'),
            ('unsubscribe', 'Unsubscribe Link'),
        ],
        blank=True,
        null=True,
        help_text="Method used to withdraw consent"
    )

    withdrawal_reason = models.TextField(
        blank=True,
        null=True,
        help_text="Reason provided for withdrawal"
    )

    # Consent status
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('withdrawn', 'Withdrawn'),
        ('revoked', 'Revoked'),
        ('pending_verification', 'Pending Verification'),
        ('invalid', 'Invalid'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending_verification',
        help_text="Current status of the consent"
    )

    # Verification and validation
    verified = models.BooleanField(
        default=False,
        help_text="Whether consent has been verified"
    )

    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date when consent was verified"
    )

    verification_method = models.CharField(
        max_length=50,
        choices=[
            ('automated', 'Automated Verification'),
            ('manual_review', 'Manual Review'),
            ('third_party', 'Third Party Verification'),
            ('legal_review', 'Legal Review'),
        ],
        blank=True,
        null=True,
        help_text="Method used to verify consent"
    )

    # Consent language and documentation
    consent_language = models.CharField(
        max_length=10,
        default='en',
        help_text="Language in which consent was obtained"
    )

    consent_text = models.TextField(
        blank=True,
        null=True,
        help_text="Full text of the consent statement"
    )

    privacy_policy_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Version of privacy policy at time of consent"
    )

    terms_version = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Version of terms at time of consent"
    )

    # Granular consent options
    granular_consents = models.JSONField(
        default=dict,
        blank=True,
        help_text="Granular consent options (e.g., {'marketing': true, 'analytics': false})"
    )

    # Consent source and context
    source_system = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="System or application where consent was obtained"
    )

    source_page = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Page or form where consent was obtained"
    )

    ip_address = models.CharField(
        max_length=45,
        blank=True,
        null=True,
        help_text="IP address from which consent was given"
    )

    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text="User agent string from consent submission"
    )

    # Geographic information
    country_code = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        help_text="Country code where consent was obtained"
    )

    region = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Region/state where consent was obtained"
    )

    # Legal basis information
    legal_basis = models.CharField(
        max_length=50,
        choices=[
            ('consent', 'Consent (Article 6(1)(a))'),
            ('contract', 'Contract (Article 6(1)(b))'),
            ('legal_obligation', 'Legal Obligation (Article 6(1)(c))'),
            ('vital_interests', 'Vital Interests (Article 6(1)(d))'),
            ('public_task', 'Public Task (Article 6(1)(e))'),
            ('legitimate_interests', 'Legitimate Interests (Article 6(1)(f))'),
        ],
        default='consent',
        help_text="Legal basis for processing"
    )

    legitimate_interests = models.TextField(
        blank=True,
        null=True,
        help_text="Description of legitimate interests (if applicable)"
    )

    # Special category data consent (Article 9)
    special_category_consent = models.BooleanField(
        default=False,
        help_text="Whether consent includes special category data processing"
    )

    special_category_legal_bases = models.JSONField(
        default=list,
        blank=True,
        help_text="Legal bases for special category data processing"
    )

    # Consent updates and versioning
    version = models.IntegerField(
        default=1,
        help_text="Consent record version"
    )

    previous_versions = models.JSONField(
        default=list,
        blank=True,
        help_text="Previous versions of this consent record"
    )

    # Audit and compliance
    created_by_system = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="System that created the consent record"
    )

    last_modified_by = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="System/user that last modified the record"
    )

    audit_trail = models.JSONField(
        default=list,
        blank=True,
        help_text="Audit trail of changes to the consent record"
    )

    # Related entities
    related_data_assets = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related data assets"
    )

    related_processing_activities = models.JSONField(
        default=list,
        blank=True,
        help_text="IDs of related processing activities"
    )

    # Metadata
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Consent tags for organization"
    )

    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom fields for additional properties"
    )

    class Meta:
        db_table = "privacy_consent_records"
        indexes = [
            models.Index(fields=['data_subject_id'], name='consent_subject_idx'),
            models.Index(fields=['status'], name='consent_status_idx'),
            models.Index(fields=['consent_date'], name='consent_date_idx'),
            models.Index(fields=['valid_until'], name='consent_expiry_idx'),
            models.Index(fields=['withdrawn'], name='consent_withdrawn_idx'),
            models.Index(fields=['legal_basis'], name='consent_legal_basis_idx'),
            models.Index(fields=['source_system'], name='consent_source_idx'),
            models.Index(fields=['created_at'], name='consent_created_idx'),
        ]
        ordering = ['-consent_date']

    def record_consent(
        self,
        consent_id: str,
        data_subject_id: str,
        data_subject_type: str,
        processing_purposes: List[str],
        consent_method: str,
        consent_language: str = 'en',
        valid_until: Optional[timezone.datetime] = None,
        source_system: Optional[str] = None,
        country_code: Optional[str] = None
    ):
        """Record a new consent"""
        self.consent_id = consent_id
        self.data_subject_id = data_subject_id
        self.data_subject_type = data_subject_type
        self.processing_purposes = processing_purposes
        self.consent_method = consent_method
        self.consent_language = consent_language
        self.valid_until = valid_until
        self.source_system = source_system
        self.country_code = country_code

        self.consent_given = True
        self.consent_date = timezone.now()
        self.valid_from = self.consent_date
        self.status = 'active'

        from .domain_events import ConsentRecordCreated
        self._raise_event(ConsentRecordCreated(
            aggregate_id=self.id,
            consent_id=consent_id,
            data_subject_id=data_subject_id,
            processing_purposes=processing_purposes,
            consent_date=str(self.consent_date)
        ))

    def verify_consent(self, verification_method: str = 'automated'):
        """Verify the consent"""
        self.verified = True
        self.verification_date = timezone.now()
        self.verification_method = verification_method
        self.status = 'active'

        from .domain_events import ConsentRecordUpdated
        self._raise_event(ConsentRecordUpdated(
            aggregate_id=self.id,
            consent_id=self.consent_id,
            status_change='pending_verification → active'
        ))

    def withdraw_consent(
        self,
        withdrawal_method: str,
        withdrawal_reason: Optional[str] = None,
        withdrawn_by: Optional[str] = None
    ):
        """Withdraw consent"""
        if self.status == 'active':
            self.withdrawn = True
            self.withdrawal_date = timezone.now()
            self.withdrawal_method = withdrawal_method
            self.withdrawal_reason = withdrawal_reason
            self.status = 'withdrawn'

            # Add to audit trail
            audit_entry = {
                'action': 'withdrawn',
                'method': withdrawal_method,
                'reason': withdrawal_reason,
                'withdrawn_by': withdrawn_by,
                'withdrawn_at': str(self.withdrawal_date)
            }

            if not self.audit_trail:
                self.audit_trail = []
            self.audit_trail.append(audit_entry)

            from .domain_events import ConsentRecordWithdrawn
            self._raise_event(ConsentRecordWithdrawn(
                aggregate_id=self.id,
                consent_id=self.consent_id,
                withdrawal_date=str(self.withdrawal_date),
                reason=withdrawal_reason
            ))

    def update_granular_consents(self, granular_consents: Dict[str, bool]):
        """Update granular consent options"""
        old_consents = self.granular_consents.copy()
        self.granular_consents.update(granular_consents)

        from .domain_events import ConsentRecordUpdated
        self._raise_event(ConsentRecordUpdated(
            aggregate_id=self.id,
            consent_id=self.consent_id,
            granular_consents_updated=True,
            old_consents=old_consents,
            new_consents=self.granular_consents
        ))

    def extend_validity(self, new_valid_until: timezone.datetime, reason: str):
        """Extend consent validity period"""
        old_valid_until = self.valid_until
        self.valid_until = new_valid_until

        # Add to audit trail
        audit_entry = {
            'action': 'validity_extended',
            'old_valid_until': str(old_valid_until) if old_valid_until else None,
            'new_valid_until': str(new_valid_until),
            'reason': reason,
            'extended_at': str(timezone.now())
        }

        if not self.audit_trail:
            self.audit_trail = []
        self.audit_trail.append(audit_entry)

        from .domain_events import ConsentRecordUpdated
        self._raise_event(ConsentRecordUpdated(
            aggregate_id=self.id,
            consent_id=self.consent_id,
            validity_extended=True,
            new_valid_until=str(new_valid_until)
        ))

    def check_expiry(self):
        """Check if consent has expired"""
        if not self.is_permanent and self.valid_until and self.status == 'active':
            if timezone.now() > self.valid_until:
                self.status = 'expired'

                from .domain_events import ConsentRecordExpired
                self._raise_event(ConsentRecordExpired(
                    aggregate_id=self.id,
                    consent_id=self.consent_id,
                    expiry_date=str(self.valid_until)
                ))

    def invalidate_consent(self, reason: str, invalidated_by: str):
        """Invalidate the consent"""
        if self.status == 'active':
            self.status = 'invalid'

            # Add to audit trail
            audit_entry = {
                'action': 'invalidated',
                'reason': reason,
                'invalidated_by': invalidated_by,
                'invalidated_at': str(timezone.now())
            }

            if not self.audit_trail:
                self.audit_trail = []
            self.audit_trail.append(audit_entry)

            from .domain_events import ConsentRecordUpdated
            self._raise_event(ConsentRecordUpdated(
                aggregate_id=self.id,
                consent_id=self.consent_id,
                status_change='active → invalid',
                reason=reason
            ))

    def update_processing_purposes(self, new_purposes: List[str], updated_by: str):
        """Update processing purposes for the consent"""
        old_purposes = self.processing_purposes.copy()
        self.processing_purposes = new_purposes

        # Add to audit trail
        audit_entry = {
            'action': 'purposes_updated',
            'old_purposes': old_purposes,
            'new_purposes': new_purposes,
            'updated_by': updated_by,
            'updated_at': str(timezone.now())
        }

        if not self.audit_trail:
            self.audit_trail = []
        self.audit_trail.append(audit_entry)

        from .domain_events import ConsentRecordUpdated
        self._raise_event(ConsentRecordUpdated(
            aggregate_id=self.id,
            consent_id=self.consent_id,
            purposes_updated=True,
            new_purposes=new_purposes
        ))

    def create_new_version(self, changes: Dict[str, Any], created_by: str):
        """Create a new version of the consent record"""
        # Store current version in history
        current_version_data = {
            'version': self.version,
            'consent_date': str(self.consent_date),
            'processing_purposes': self.processing_purposes,
            'data_categories': self.data_categories,
            'valid_until': str(self.valid_until) if self.valid_until else None,
            'created_at': str(self.created_at),
            'archived_at': str(timezone.now())
        }

        if not self.previous_versions:
            self.previous_versions = []
        self.previous_versions.append(current_version_data)

        # Update to new version
        self.version += 1

        # Apply changes
        for field, value in changes.items():
            if hasattr(self, field):
                setattr(self, field, value)

        # Add to audit trail
        audit_entry = {
            'action': 'version_created',
            'new_version': self.version,
            'changes': changes,
            'created_by': created_by,
            'created_at': str(timezone.now())
        }

        if not self.audit_trail:
            self.audit_trail = []
        self.audit_trail.append(audit_entry)

        from .domain_events import ConsentRecordUpdated
        self._raise_event(ConsentRecordUpdated(
            aggregate_id=self.id,
            consent_id=self.consent_id,
            new_version=self.version,
            changes=changes
        ))

    @property
    def is_valid(self) -> bool:
        """Check if consent is currently valid"""
        if self.status not in ['active']:
            return False

        if self.withdrawn:
            return False

        if not self.is_permanent and self.valid_until:
            return timezone.now() <= self.valid_until

        return True

    @property
    def is_expired(self) -> bool:
        """Check if consent has expired"""
        if self.is_permanent:
            return False

        if not self.valid_until:
            return False

        return timezone.now() > self.valid_until

    @property
    def days_until_expiry(self) -> Optional[int]:
        """Calculate days until consent expires"""
        if self.is_permanent or not self.valid_until:
            return None

        if self.is_expired:
            return 0

        return (self.valid_until - timezone.now()).days

    @property
    def is_due_for_renewal(self) -> bool:
        """Check if consent is due for renewal (within 30 days of expiry)"""
        days_until = self.days_until_expiry
        return days_until is not None and 0 <= days_until <= 30

    @property
    def consent_duration_days(self) -> Optional[int]:
        """Calculate total duration of consent"""
        if not self.consent_date:
            return None

        end_date = self.withdrawal_date or self.valid_until or timezone.now()
        return (end_date - self.consent_date).days

    @property
    def has_granular_options(self) -> bool:
        """Check if consent has granular options configured"""
        return bool(self.granular_consents)

    @property
    def processing_purposes_count(self) -> int:
        """Count of processing purposes covered by this consent"""
        return len(self.processing_purposes)

    def get_audit_trail_summary(self) -> List[Dict[str, Any]]:
        """Get a summary of the audit trail"""
        return [{
            'action': entry.get('action'),
            'timestamp': entry.get('withdrawn_at') or entry.get('updated_at') or entry.get('created_at'),
            'details': entry
        } for entry in self.audit_trail]

    def __str__(self):
        return f"ConsentRecord({self.consent_id}: {self.data_subject_id} - {self.status})"
