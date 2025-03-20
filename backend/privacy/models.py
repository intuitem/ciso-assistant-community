from django.db import models
from iam.models import FolderMixin, User
from tprm.models import Entity
from core.base_models import NameDescriptionMixin
from core.models import AppliedControl


class Purpose(NameDescriptionMixin, FolderMixin):
    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="purposes"
    )

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class PersonalData(NameDescriptionMixin, FolderMixin):
    DELETION_POLICY_CHOICES = (
        ("automatic_deletion", "Automatic Deletion"),
        ("anonymization", "Anonymization"),
        ("manual_review_deletion", "Manual Review Deletion"),
        ("user_requested_deletion", "User Requested Deletion"),
        ("legal_regulatory_hold", "Legal/Regulatory Hold"),
        ("partial_deletion", "Partial Deletion"),
    )

    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="personal_data"
    )
    category = models.CharField(max_length=255)
    retention = models.CharField(max_length=255, blank=True)
    deletion_policy = models.CharField(
        max_length=50, choices=DELETION_POLICY_CHOICES, blank=True
    )
    is_sensitive = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)

        # Update the processing's sensitive data flag if needed
        if self.is_sensitive and not self.processing.has_sensitive_personal_data:
            self.processing.has_sensitive_personal_data = True
            self.processing.save(update_fields=["has_sensitive_personal_data"])


class DataSubject(NameDescriptionMixin, FolderMixin):
    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="data_subjects"
    )
    category = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class DataRecipient(NameDescriptionMixin, FolderMixin):
    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="data_recipients"
    )
    category = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class DataContractor(NameDescriptionMixin, FolderMixin):
    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="contractors_involved"
    )
    relationship_type = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    documentation_link = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class DataTransfer(NameDescriptionMixin, FolderMixin):
    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="data_transfers"
    )
    country = models.CharField(max_length=100)
    legal_basis = models.CharField(max_length=255)
    guarantees = models.TextField(blank=True)
    documentation_link = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class Processing(NameDescriptionMixin, FolderMixin):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("deprecated", "Deprecated"),
    )

    ref_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="authored_processings"
    )
    labels = models.JSONField(default=list, blank=True)
    legal_basis = models.CharField(max_length=255)
    information_channel = models.CharField(max_length=255, blank=True)
    usage_channel = models.CharField(max_length=255, blank=True)
    dpia_required = models.BooleanField(default=False)
    dpia_reference = models.CharField(max_length=255, blank=True)
    has_sensitive_personal_data = models.BooleanField(default=False)
    owner = models.ForeignKey(
        Entity, on_delete=models.SET_NULL, null=True, related_name="owned_processings"
    )
    associated_controls = models.ManyToManyField(
        AppliedControl, blank=True, related_name="processings"
    )

    def update_sensitive_data_flag(self):
        """Update the has_sensitive_personal_data flag based on associated personal data"""
        has_sensitive = self.personal_data.filter(is_sensitive=True).exists()

        if has_sensitive != self.has_sensitive_personal_data:
            self.has_sensitive_personal_data = has_sensitive
            self.save(update_fields=["has_sensitive_personal_data"])
