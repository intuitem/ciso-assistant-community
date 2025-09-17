from django.db import models
from iam.models import User, FolderMixin
from tprm.models import Entity
from core.models import AppliedControl
from core.models import FilteringLabelMixin, I18nObjectMixin, ReferentialObjectMixin
from core.base_models import NameDescriptionMixin, AbstractBaseModel
from core.constants import COUNTRY_CHOICES
from django.db.models import Count


class NameDescriptionFolderMixin(NameDescriptionMixin, FolderMixin):
    class Meta:
        abstract = True


LEGAL_BASIS_CHOICES = (
    # Article 6(1) Legal Bases
    ("privacy_consent", "Consent"),
    ("privacy_contract", "Performance of a Contract"),
    ("privacy_legal_obligation", "Compliance with a Legal Obligation"),
    ("privacy_vital_interests", "Protection of Vital Interests"),
    ("privacy_public_interest", "Performance of a Task in the Public Interest"),
    ("privacy_legitimate_interests", "Legitimate Interests"),
    # Special Category Processing - Article 9(2)
    ("privacy_explicit_consent", "Explicit Consent for Special Categories"),
    ("privacy_employment_social_security", "Employment and Social Security Law"),
    (
        "privacy_vital_interests_incapacity",
        "Vital Interests (Subject Physically/Legally Incapable)",
    ),
    ("privacy_nonprofit_organization", "Processing by Nonprofit Organization"),
    ("privacy_public_data", "Data Manifestly Made Public by the Data Subject"),
    ("privacy_legal_claims", "Establishment, Exercise or Defense of Legal Claims"),
    ("privacy_substantial_public_interest", "Substantial Public Interest"),
    ("privacy_preventive_medicine", "Preventive or Occupational Medicine"),
    ("privacy_public_health", "Public Health"),
    ("privacy_archiving_research", "Archiving, Research or Statistical Purposes"),
    # Additional GDPR Bases
    ("privacy_child_consent", "Child's Consent with Parental Authorization"),
    ("privacy_data_transfer_adequacy", "Transfer Based on Adequacy Decision"),
    ("privacy_data_transfer_safeguards", "Transfer Subject to Appropriate Safeguards"),
    (
        "privacy_data_transfer_binding_rules",
        "Transfer Subject to Binding Corporate Rules",
    ),
    (
        "privacy_data_transfer_derogation",
        "Transfer Based on Derogation for Specific Situations",
    ),
    # Common Combined Bases
    ("privacy_consent_and_contract", "Consent and Contract"),
    ("privacy_contract_and_legitimate_interests", "Contract and Legitimate Interests"),
    # Other
    ("privacy_not_applicable", "Not Applicable"),
    ("privacy_other", "Other Legal Basis (Specify in Description)"),
)


class ProcessingNature(ReferentialObjectMixin, I18nObjectMixin):
    DEFAULT_PROCESSING_NATURE = [
        "privacy_collection",
        "privacy_recording",
        "privacy_organization",
        "privacy_structuring",
        "privacy_storage",
        "privacy_adaptationOrAlteration",
        "privacy_retrieval",
        "privacy_consultation",
        "privacy_use",
        "privacy_disclosureByTransmission",
        "privacy_disseminationOrOtherwiseMakingAvailable",
        "privacy_alignmentOrCombination",
        "privacy_restriction",
        "privacy_erasureOrDestruction",
    ]

    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def create_default_values(cls):
        for value in cls.DEFAULT_PROCESSING_NATURE:
            ProcessingNature.objects.update_or_create(
                name=value,
            )

    class Meta:
        ordering = ["name"]
        verbose_name = "Processing Nature"
        verbose_name_plural = "Processing Natures"


class Processing(NameDescriptionFolderMixin, FilteringLabelMixin):
    STATUS_CHOICES = (
        ("privacy_draft", "Draft"),
        ("privacy_in_review", "In Review"),
        ("privacy_approved", "Approved"),
        ("privacy_deprecated", "Deprecated"),
    )

    ref_id = models.CharField(max_length=100, blank=True)
    nature = models.ManyToManyField(ProcessingNature, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="privacy_draft"
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="authored_processings"
    )
    legal_basis = models.CharField(
        max_length=255, choices=LEGAL_BASIS_CHOICES, blank=True
    )
    information_channel = models.CharField(max_length=255, blank=True)
    usage_channel = models.CharField(max_length=255, blank=True)
    dpia_required = models.BooleanField(default=False, blank=True)
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

    def metrics(self):
        return {}


class Purpose(NameDescriptionFolderMixin):
    processing = models.ForeignKey(
        Processing, on_delete=models.CASCADE, related_name="purposes"
    )

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class PersonalData(NameDescriptionFolderMixin):
    DELETION_POLICY_CHOICES = (
        ("privacy_automatic_deletion", "Automatic Deletion"),
        ("privacy_anonymization", "Anonymization"),
        ("privacy_manual_review_deletion", "Manual Review Deletion"),
        ("privacy_user_requested_deletion", "User Requested Deletion"),
        ("privacy_legal_regulatory_hold", "Legal/Regulatory Hold"),
        ("privacy_partial_deletion", "Partial Deletion"),
    )
    PERSONAL_DATA_CHOICES = (
        # Basic Identity Information
        ("privacy_basic_identity", "Basic Identity Information"),
        ("privacy_name", "Name"),
        ("privacy_identification_numbers", "Identification Numbers"),
        ("privacy_online_identifiers", "Online Identifiers"),
        ("privacy_location_data", "Location Data"),
        # Contact Information
        ("privacy_contact_details", "Contact Details"),
        ("privacy_address", "Address"),
        ("privacy_email", "Email Address"),
        ("privacy_phone_number", "Phone Number"),
        # Financial Information
        ("privacy_financial_data", "Financial Data"),
        ("privacy_bank_account", "Bank Account Information"),
        ("privacy_payment_card", "Payment Card Information"),
        ("privacy_transaction_history", "Transaction History"),
        ("privacy_salary_information", "Salary Information"),
        # Special Categories of Personal Data (Sensitive)
        ("privacy_health_data", "Health Data"),
        ("privacy_genetic_data", "Genetic Data"),
        ("privacy_biometric_data", "Biometric Data"),
        ("privacy_racial_ethnic_origin", "Racial or Ethnic Origin"),
        ("privacy_political_opinions", "Political Opinions"),
        ("privacy_religious_beliefs", "Religious or Philosophical Beliefs"),
        ("privacy_trade_union_membership", "Trade Union Membership"),
        ("privacy_sexual_orientation", "Sexual Orientation"),
        ("privacy_sex_life_data", "Sex Life Data"),
        # Digital Behavior and Activities
        ("privacy_browsing_history", "Browsing History"),
        ("privacy_search_history", "Search History"),
        ("privacy_cookies", "Cookies Data"),
        ("privacy_device_information", "Device Information"),
        ("privacy_ip_address", "IP Address"),
        ("privacy_user_behavior", "User Behavior"),
        # Professional Data
        ("privacy_employment_details", "Employment Details"),
        ("privacy_education_history", "Education History"),
        ("privacy_professional_qualifications", "Professional Qualifications"),
        ("privacy_work_performance", "Work Performance Data"),
        # Social Relationships
        ("privacy_family_details", "Family Details"),
        ("privacy_social_network", "Social Network"),
        ("privacy_lifestyle_information", "Lifestyle Information"),
        # Communication Data
        ("privacy_correspondence", "Correspondence Content"),
        ("privacy_messaging_content", "Messaging Content"),
        ("privacy_communication_metadata", "Communication Metadata"),
        # Government/Official Data
        ("privacy_government_identifiers", "Government Identifiers"),
        ("privacy_tax_information", "Tax Information"),
        ("privacy_social_security", "Social Security Information"),
        ("privacy_drivers_license", "Driver's License Information"),
        ("privacy_passport_information", "Passport Information"),
        # Legal Data
        ("privacy_legal_records", "Legal Records"),
        ("privacy_criminal_records", "Criminal Records"),
        ("privacy_judicial_data", "Judicial Data"),
        # Preferences and Opinions
        ("privacy_preferences", "Preferences"),
        ("privacy_opinions", "Opinions"),
        ("privacy_feedback", "Feedback"),
        # Other Types
        ("privacy_images_photos", "Images and Photos"),
        ("privacy_voice_recordings", "Voice Recordings"),
        ("privacy_video_recordings", "Video Recordings"),
        ("privacy_other", "Other Personal Data"),
    )

    processing = models.ForeignKey(
        Processing, on_delete=models.CASCADE, related_name="personal_data"
    )
    category = models.CharField(max_length=255, choices=PERSONAL_DATA_CHOICES)
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

    @classmethod
    def get_categories_count(cls):
        categories = (
            cls.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Convert to list of dictionaries with readable category names
        result = []
        for item in categories:
            category_code = item["category"]
            category_name = dict(cls.PERSONAL_DATA_CHOICES).get(
                category_code, category_code
            )
            result.append(
                {"id": category_code, "name": category_name, "value": item["count"]}
            )

        return result


class DataSubject(NameDescriptionFolderMixin):
    CATEGORY_CHOICES = (
        # Core Categories
        ("privacy_customer", "Customer/Client"),
        ("privacy_prospect", "Prospective Customer/Client"),
        ("privacy_employee", "Employee"),
        ("privacy_job_applicant", "Job Applicant"),
        ("privacy_contractor", "Contractor/Vendor"),
        ("privacy_business_partner", "Business Partner"),
        # Website/Service Users
        ("privacy_user", "Website/App User"),
        ("privacy_visitor", "Visitor"),
        # Special Categories
        ("privacy_minor", "Child/Minor"),
        ("privacy_vulnerable", "Vulnerable Person"),
        # Others
        ("privacy_public", "General Public"),
        ("privacy_other", "Other Data Subject Category"),
    )

    processing = models.ForeignKey(
        "Processing", on_delete=models.CASCADE, related_name="data_subjects"
    )
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class DataRecipient(NameDescriptionFolderMixin):
    CATEGORY_CHOICES = (
        # Internal Recipients
        ("privacy_internal_team", "Internal Team/Department"),
        ("privacy_employee", "Employee"),
        ("privacy_subsidiary", "Subsidiary Company"),
        ("privacy_parent_company", "Parent Company"),
        ("privacy_affiliated_entity", "Affiliated Entity"),
        # External Service Providers
        ("privacy_service_provider", "Service Provider"),
        ("privacy_data_processor", "Data Processor"),
        ("privacy_cloud_provider", "Cloud Service Provider"),
        ("privacy_it_provider", "IT Service Provider"),
        ("privacy_marketing_agency", "Marketing Agency"),
        ("privacy_payment_processor", "Payment Processor"),
        ("privacy_analytics_provider", "Analytics Provider"),
        # Business Partners
        ("privacy_business_partner", "Business Partner"),
        ("privacy_distributor", "Distributor"),
        ("privacy_reseller", "Reseller"),
        ("privacy_supplier", "Supplier"),
        ("privacy_contractor", "Contractor"),
        # Professional Services
        ("privacy_legal_advisor", "Legal Advisor"),
        ("privacy_accountant", "Accountant"),
        ("privacy_consultant", "Consultant"),
        ("privacy_auditor", "Auditor"),
        # Authorities
        ("privacy_regulatory_authority", "Regulatory Authority"),
        ("privacy_tax_authority", "Tax Authority"),
        ("privacy_law_enforcement", "Law Enforcement"),
        ("privacy_government_entity", "Government Entity"),
        ("privacy_court", "Court"),
        # Others
        ("privacy_joint_controller", "Joint Controller"),
        ("privacy_individual_recipient", "Individual Recipient"),
        ("privacy_public", "Public Disclosure"),
        ("privacy_other", "Other Recipient Category"),
    )

    processing = models.ForeignKey(
        Processing, on_delete=models.CASCADE, related_name="data_recipients"
    )
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class DataContractor(NameDescriptionFolderMixin):
    RELATIONSHIP_TYPE_CHOICES = (
        ("privacy_data_processor", "Data Processor"),
        ("privacy_sub_processor", "Sub-processor"),
        ("privacy_joint_controller", "Joint Controller"),
        ("privacy_independent_controller", "Independent Controller"),
        ("privacy_other", "Other Relationship Type"),
    )
    processing = models.ForeignKey(
        Processing, on_delete=models.CASCADE, related_name="contractors_involved"
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    relationship_type = models.CharField(
        max_length=255, choices=RELATIONSHIP_TYPE_CHOICES
    )
    country = models.CharField(max_length=3, choices=COUNTRY_CHOICES)
    documentation_link = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)


class DataTransfer(NameDescriptionFolderMixin):
    processing = models.ForeignKey(
        Processing, on_delete=models.CASCADE, related_name="data_transfers"
    )
    entity = models.ForeignKey(
        Entity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    country = models.CharField(max_length=3, choices=COUNTRY_CHOICES)
    legal_basis = models.CharField(
        max_length=255, choices=LEGAL_BASIS_CHOICES, blank=True
    )
    guarantees = models.TextField(blank=True)
    documentation_link = models.URLField(blank=True)

    def save(self, *args, **kwargs):
        self.folder = self.processing.folder
        super().save(*args, **kwargs)
