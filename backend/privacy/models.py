from django.db import models
from iam.models import User, FolderMixin
from tprm.models import Entity
from core.models import AppliedControl
from core.models import FilteringLabelMixin
from core.base_models import NameDescriptionMixin
from core.constants import COUNTRY_CHOICES
from django.db.models import Count


class NameDescriptionFolderMixin(NameDescriptionMixin, FolderMixin):
    class Meta:
        abstract = True


LEGAL_BASIS_CHOICES = (
    # Article 6(1) Legal Bases
    ("consent", "Consent"),
    ("contract", "Performance of a Contract"),
    ("legal_obligation", "Compliance with a Legal Obligation"),
    ("vital_interests", "Protection of Vital Interests"),
    ("public_interest", "Performance of a Task in the Public Interest"),
    ("legitimate_interests", "Legitimate Interests"),
    # Special Category Processing - Article 9(2)
    ("explicit_consent", "Explicit Consent for Special Categories"),
    ("employment_social_security", "Employment and Social Security Law"),
    (
        "vital_interests_incapacity",
        "Vital Interests (Subject Physically/Legally Incapable)",
    ),
    ("nonprofit_organization", "Processing by Nonprofit Organization"),
    ("public_data", "Data Manifestly Made Public by the Data Subject"),
    ("legal_claims", "Establishment, Exercise or Defense of Legal Claims"),
    ("substantial_public_interest", "Substantial Public Interest"),
    ("preventive_medicine", "Preventive or Occupational Medicine"),
    ("public_health", "Public Health"),
    ("archiving_research", "Archiving, Research or Statistical Purposes"),
    # Additional GDPR Bases
    ("child_consent", "Child's Consent with Parental Authorization"),
    ("data_transfer_adequacy", "Transfer Based on Adequacy Decision"),
    ("data_transfer_safeguards", "Transfer Subject to Appropriate Safeguards"),
    ("data_transfer_binding_rules", "Transfer Subject to Binding Corporate Rules"),
    (
        "data_transfer_derogation",
        "Transfer Based on Derogation for Specific Situations",
    ),
    # Common Combined Bases
    ("consent_and_contract", "Consent and Contract"),
    ("contract_and_legitimate_interests", "Contract and Legitimate Interests"),
    # Other
    ("not_applicable", "Not Applicable"),
    ("other", "Other Legal Basis (Specify in Description)"),
)


class Processing(NameDescriptionFolderMixin, FilteringLabelMixin):
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
        ("automatic_deletion", "Automatic Deletion"),
        ("anonymization", "Anonymization"),
        ("manual_review_deletion", "Manual Review Deletion"),
        ("user_requested_deletion", "User Requested Deletion"),
        ("legal_regulatory_hold", "Legal/Regulatory Hold"),
        ("partial_deletion", "Partial Deletion"),
    )
    PERSONAL_DATA_CHOICES = (
        # Basic Identity Information
        ("basic_identity", "Basic Identity Information"),
        ("name", "Name"),
        ("identification_numbers", "Identification Numbers"),
        ("online_identifiers", "Online Identifiers"),
        ("location_data", "Location Data"),
        # Contact Information
        ("contact_details", "Contact Details"),
        ("address", "Address"),
        ("email", "Email Address"),
        ("phone_number", "Phone Number"),
        # Financial Information
        ("financial_data", "Financial Data"),
        ("bank_account", "Bank Account Information"),
        ("payment_card", "Payment Card Information"),
        ("transaction_history", "Transaction History"),
        ("salary_information", "Salary Information"),
        # Special Categories of Personal Data (Sensitive)
        ("health_data", "Health Data"),
        ("genetic_data", "Genetic Data"),
        ("biometric_data", "Biometric Data"),
        ("racial_ethnic_origin", "Racial or Ethnic Origin"),
        ("political_opinions", "Political Opinions"),
        ("religious_beliefs", "Religious or Philosophical Beliefs"),
        ("trade_union_membership", "Trade Union Membership"),
        ("sexual_orientation", "Sexual Orientation"),
        ("sex_life_data", "Sex Life Data"),
        # Digital Behavior and Activities
        ("browsing_history", "Browsing History"),
        ("search_history", "Search History"),
        ("cookies", "Cookies Data"),
        ("device_information", "Device Information"),
        ("ip_address", "IP Address"),
        ("user_behavior", "User Behavior"),
        # Professional Data
        ("employment_details", "Employment Details"),
        ("education_history", "Education History"),
        ("professional_qualifications", "Professional Qualifications"),
        ("work_performance", "Work Performance Data"),
        # Social Relationships
        ("family_details", "Family Details"),
        ("social_network", "Social Network"),
        ("lifestyle_information", "Lifestyle Information"),
        # Communication Data
        ("correspondence", "Correspondence Content"),
        ("messaging_content", "Messaging Content"),
        ("communication_metadata", "Communication Metadata"),
        # Government/Official Data
        ("government_identifiers", "Government Identifiers"),
        ("tax_information", "Tax Information"),
        ("social_security", "Social Security Information"),
        ("drivers_license", "Driver's License Information"),
        ("passport_information", "Passport Information"),
        # Legal Data
        ("legal_records", "Legal Records"),
        ("criminal_records", "Criminal Records"),
        ("judicial_data", "Judicial Data"),
        # Preferences and Opinions
        ("preferences", "Preferences"),
        ("opinions", "Opinions"),
        ("feedback", "Feedback"),
        # Other Types
        ("images_photos", "Images and Photos"),
        ("voice_recordings", "Voice Recordings"),
        ("video_recordings", "Video Recordings"),
        ("other", "Other Personal Data"),
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
        ("customer", "Customer/Client"),
        ("prospect", "Prospective Customer/Client"),
        ("employee", "Employee"),
        ("job_applicant", "Job Applicant"),
        ("contractor", "Contractor/Vendor"),
        ("business_partner", "Business Partner"),
        # Website/Service Users
        ("user", "Website/App User"),
        ("visitor", "Visitor"),
        # Special Categories
        ("minor", "Child/Minor"),
        ("vulnerable", "Vulnerable Person"),
        # Others
        ("public", "General Public"),
        ("other", "Other Data Subject Category"),
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
        ("internal_team", "Internal Team/Department"),
        ("employee", "Employee"),
        ("subsidiary", "Subsidiary Company"),
        ("parent_company", "Parent Company"),
        ("affiliated_entity", "Affiliated Entity"),
        # External Service Providers
        ("service_provider", "Service Provider"),
        ("data_processor", "Data Processor"),
        ("cloud_provider", "Cloud Service Provider"),
        ("it_provider", "IT Service Provider"),
        ("marketing_agency", "Marketing Agency"),
        ("payment_processor", "Payment Processor"),
        ("analytics_provider", "Analytics Provider"),
        # Business Partners
        ("business_partner", "Business Partner"),
        ("distributor", "Distributor"),
        ("reseller", "Reseller"),
        ("supplier", "Supplier"),
        ("contractor", "Contractor"),
        # Professional Services
        ("legal_advisor", "Legal Advisor"),
        ("accountant", "Accountant"),
        ("consultant", "Consultant"),
        ("auditor", "Auditor"),
        # Authorities
        ("regulatory_authority", "Regulatory Authority"),
        ("tax_authority", "Tax Authority"),
        ("law_enforcement", "Law Enforcement"),
        ("government_entity", "Government Entity"),
        ("court", "Court"),
        # Others
        ("joint_controller", "Joint Controller"),
        ("individual_recipient", "Individual Recipient"),
        ("public", "Public Disclosure"),
        ("other", "Other Recipient Category"),
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
        ("data_processor", "Data Processor"),
        ("sub_processor", "Sub-processor"),
        ("joint_controller", "Joint Controller"),
        ("independent_controller", "Independent Controller"),
        ("other", "Other Relationship Type"),
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
