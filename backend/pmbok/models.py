from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.utils.translation import gettext_lazy as _
from iam.models import Folder, FolderMixin
from core.models import (
    AppliedControl,
    FilteringLabelMixin,
    FindingsAssessment,
    Policy,
    ComplianceAssessment,
    RiskAssessment,
    Evidence,
    SecurityException,
    Terminology,
)
from crq.models import QuantitativeRiskStudy
from doc_management.models import DocumentContainer
from ebios_rm.models import EbiosRMStudy
from resilience.models import BusinessImpactAnalysis
from tprm.models import Entity, EntityAssessment
from core.base_models import (
    AbstractBaseModel,
    NameDescriptionMixin,
)
from custom_fields.host import CustomFieldsMixin
from global_settings.models import GlobalSettings

from auditlog.registry import auditlog


class NameDescriptionFolderMixin(NameDescriptionMixin, FolderMixin):
    class Meta:
        abstract = True


class GenericCollection(NameDescriptionFolderMixin, FilteringLabelMixin):
    ITEM_TYPES = {
        "compliance_assessments": ComplianceAssessment.objects.all(),
        "risk_assessments": RiskAssessment.objects.all(),
        "crq_studies": QuantitativeRiskStudy.objects.all(),
        "ebios_studies": EbiosRMStudy.objects.all(),
        "entity_assessments": EntityAssessment.objects.all(),
        "findings_assessments": FindingsAssessment.objects.all(),
        "documents": Evidence.objects.all(),
        "security_exceptions": SecurityException.objects.all(),
        "policies": Policy.objects.all(),
        "applied_controls": AppliedControl.objects.exclude(category="policy"),
        "document_containers": DocumentContainer.objects.all(),
        "business_impact_analyses": BusinessImpactAnalysis.objects.all(),
    }

    ref_id = models.CharField(max_length=100, blank=True)
    dependencies = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
    )

    def get_items(self, field):
        queryset = self.ITEM_TYPES[field].all()
        return queryset.filter(
            pk__in=self.items.filter(
                content_type=ContentType.objects.get_for_model(queryset.model)
            ).values("object_id")
        )

    def set_items(self, field, objects):
        content_type = ContentType.objects.get_for_model(self.ITEM_TYPES[field].model)
        new = {obj.pk for obj in objects}
        current = set(self.get_items(field).values_list("pk", flat=True))
        self.items.filter(
            content_type=content_type, object_id__in=current - new
        ).delete()
        for pk in new - current:
            CollectionItem.objects.get_or_create(
                collection=self, content_type=content_type, object_id=pk
            )

    @classmethod
    def containing(cls, obj):
        return cls.objects.filter(
            items__content_type=ContentType.objects.get_for_model(obj),
            items__object_id=obj.pk,
        )

    @classmethod
    def set_collections_of(cls, obj, collections):
        content_type = ContentType.objects.get_for_model(obj)
        new = {collection.pk for collection in collections}
        current = set(cls.containing(obj).values_list("pk", flat=True))
        CollectionItem.objects.filter(
            content_type=content_type,
            object_id=obj.pk,
            collection_id__in=current - new,
        ).delete()
        for pk in new - current:
            CollectionItem.objects.get_or_create(
                collection_id=pk, content_type=content_type, object_id=obj.pk
            )


class CollectionItem(AbstractBaseModel):
    collection = models.ForeignKey(
        GenericCollection, on_delete=models.CASCADE, related_name="items"
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    item = GenericForeignKey("content_type", "object_id")

    IAM_SCOPE_FIELD = "collection"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "content_type", "object_id"],
                name="unique_collection_item",
            )
        ]
        indexes = [models.Index(fields=["content_type", "object_id"])]


def _delete_collection_items(sender, instance, **kwargs):
    CollectionItem.objects.filter(
        content_type=ContentType.objects.get_for_model(sender),
        object_id=instance.pk,
    ).delete()


for _queryset in GenericCollection.ITEM_TYPES.values():
    post_delete.connect(_delete_collection_items, sender=_queryset.model)


class Accreditation(NameDescriptionFolderMixin, FilteringLabelMixin):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("in_progress", "In progress"),
        ("accredited", "Accredited"),
        ("not_accredited", "Not Accredited"),
        ("obsolete", "Obsolete"),
    )
    CATEGORY_CHOICES = (
        ("accreditation_simplified", "accreditationSimplified"),
        ("accreditation_elaborated", "accreditationElaborated"),
        ("accreditation_advanced", "accreditationAdvanced"),
        ("accreditation_sensitive", "accreditationSensitive"),
        ("accreditation_restricted", "accreditationRestricted"),
        ("other", "Other"),
    )

    ref_id = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        related_name="accreditation_category",
        limit_choices_to={
            "field_path": Terminology.FieldPath.ACCREDITATION_CATEGORY,
            "is_visible": True,
        },
    )
    authority = models.ForeignKey(
        Entity,
        on_delete=models.PROTECT,
        related_name="accreditation_authority",
        null=True,
        blank=True,
        help_text="Accreditation authority entity",
    )
    authority_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Free-text authority name, for authorities not registered as entities",
    )
    status = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        related_name="accreditation_status",
        limit_choices_to={
            "field_path": Terminology.FieldPath.ACCREDITATION_STATUS,
            "is_visible": True,
        },
    )

    author = models.ForeignKey(
        "core.Actor",
        on_delete=models.SET_NULL,
        null=True,
        related_name="authored_accreditations",
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
    )
    linked_collection = models.ForeignKey(
        GenericCollection, null=True, on_delete=models.SET_NULL
    )
    checklist = models.ForeignKey(
        ComplianceAssessment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accreditation_checklist",
    )
    commission_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date of the accreditation commission decision",
    )
    duration_months = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Accreditation validity duration in months",
    )
    decision_evidence = models.ManyToManyField(
        Evidence,
        blank=True,
        related_name="accreditation_decisions",
        help_text="Evidence documents for the accreditation decision (e.g. minutes/PV)",
    )
    observation = models.TextField(verbose_name="Observation", blank=True, null=True)


class Project(NameDescriptionFolderMixin, FilteringLabelMixin, CustomFieldsMixin):
    class Kind(models.TextChoices):
        PORTFOLIO = "portfolio", _("Portfolio")
        PROGRAM = "program", _("Program")
        PROJECT = "project", _("Project")

    PRIORITY = [
        (1, _("P1")),
        (2, _("P2")),
        (3, _("P3")),
        (4, _("P4")),
    ]

    TOLERANCES_SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "time": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "plus_days": {"type": "integer", "minimum": 0},
                    "minus_days": {"type": "integer", "minimum": 0},
                },
            },
            "cost": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "plus_pct": {"type": "number", "minimum": 0},
                    "minus_pct": {"type": "number", "minimum": 0},
                },
            },
            "scope": {"type": "string"},
            "quality": {"type": "string"},
            "benefits": {"type": "string"},
            "risk": {"type": "string"},
        },
    }

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.PROJECT,
    )

    ref_id = models.CharField(max_length=100, blank=True)
    ref_link = models.URLField(blank=True, max_length=2048)

    owner = models.ForeignKey(
        "core.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
    )
    sponsor = models.ForeignKey(
        "core.Actor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sponsored_projects",
    )

    status = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="project_status",
        limit_choices_to={
            "field_path": Terminology.FieldPath.PROJECT_STATUS,
            "is_visible": True,
        },
    )
    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY,
        null=True,
        blank=True,
        verbose_name=_("Priority"),
    )
    health = models.ForeignKey(
        Terminology,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="project_health",
        limit_choices_to={
            "field_path": Terminology.FieldPath.PROJECT_HEALTH,
            "is_visible": True,
        },
    )

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    eta = models.DateField(blank=True, null=True)
    closed_at = models.DateField(blank=True, null=True)
    progress = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    purpose = models.TextField(blank=True)
    objectives = models.TextField(blank=True)
    success_criteria = models.TextField(blank=True)
    business_case = models.TextField(blank=True)
    deliverables = models.TextField(blank=True)
    assumptions = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    dependencies_note = models.TextField(blank=True)
    exit_criteria = models.TextField(blank=True)
    organizational_alignment = models.TextField(blank=True)
    approval_requirements = models.TextField(blank=True)

    budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    actual_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(max_length=3, blank=True)

    linked_collection = models.ForeignKey(
        GenericCollection,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    parent_project = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sub_projects",
    )
    tolerances = models.JSONField(default=dict, blank=True)

    observation = models.TextField(blank=True, null=True)

    fields_to_check = ["ref_id", "name"]

    @transaction.atomic
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if is_new:
            if not self.currency and self.parent_project_id:
                self.currency = self.parent_project.currency or ""
            if not self.currency:
                general = GlobalSettings.objects.filter(name="general").first()
                if general:
                    self.currency = general.value.get("currency", "") or ""
            if self.progress is None:
                self.progress = 0
            if self.budget is None:
                self.budget = Decimal("0")
            if self.actual_cost is None:
                self.actual_cost = Decimal("0")
        previous_status_name = None
        if not is_new:
            previous_status_name = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("status__name", flat=True)
                .first()
            )
        new_status_name = self.status.name if self.status_id else None
        if new_status_name == "closed" and previous_status_name != "closed":
            self.closed_at = self.closed_at or date.today()
        elif new_status_name != "closed" and previous_status_name == "closed":
            self.closed_at = None

        super().save(*args, **kwargs)

        if is_new and not self.linked_collection_id and self.folder_id:
            coll = GenericCollection.objects.create(name=self.name, folder=self.folder)
            type(self).objects.filter(pk=self.pk).update(linked_collection=coll)
            self.linked_collection_id = coll.pk

        from metrology.models import BuiltinMetricSample

        BuiltinMetricSample.update_or_create_snapshot(self)
        if self.folder_id:
            BuiltinMetricSample.update_or_create_snapshot(self.folder)


class ResponsibilityRole(NameDescriptionFolderMixin):
    class Taxonomy(models.TextChoices):
        RACI = "raci", "RACI"
        RASCI = "rasci", "RASCI"
        RAPID = "rapid", "RAPID"
        CUSTOM = "custom", "Custom"

    DEFAULT_ROLES = [
        # RACI
        {
            "taxonomy": "raci",
            "code": "R",
            "name": "responsible",
            "order": 1,
            "color": "#3b82f6",
        },
        {
            "taxonomy": "raci",
            "code": "A",
            "name": "accountable",
            "order": 2,
            "color": "#10b981",
        },
        {
            "taxonomy": "raci",
            "code": "C",
            "name": "consulted",
            "order": 3,
            "color": "#f59e0b",
        },
        {
            "taxonomy": "raci",
            "code": "I",
            "name": "informed",
            "order": 4,
            "color": "#6b7280",
        },
        # RASCI
        {
            "taxonomy": "rasci",
            "code": "R",
            "name": "responsible",
            "order": 1,
            "color": "#3b82f6",
        },
        {
            "taxonomy": "rasci",
            "code": "A",
            "name": "accountable",
            "order": 2,
            "color": "#10b981",
        },
        {
            "taxonomy": "rasci",
            "code": "S",
            "name": "support",
            "order": 3,
            "color": "#8b5cf6",
        },
        {
            "taxonomy": "rasci",
            "code": "C",
            "name": "consulted",
            "order": 4,
            "color": "#f59e0b",
        },
        {
            "taxonomy": "rasci",
            "code": "I",
            "name": "informed",
            "order": 5,
            "color": "#6b7280",
        },
        # RAPID (Bain)
        {
            "taxonomy": "rapid",
            "code": "R",
            "name": "recommend",
            "order": 1,
            "color": "#3b82f6",
        },
        {
            "taxonomy": "rapid",
            "code": "A",
            "name": "agree",
            "order": 2,
            "color": "#10b981",
        },
        {
            "taxonomy": "rapid",
            "code": "P",
            "name": "perform",
            "order": 3,
            "color": "#8b5cf6",
        },
        {
            "taxonomy": "rapid",
            "code": "I",
            "name": "input",
            "order": 4,
            "color": "#f59e0b",
        },
        {
            "taxonomy": "rapid",
            "code": "D",
            "name": "decide",
            "order": 5,
            "color": "#ef4444",
        },
    ]

    code = models.CharField(
        max_length=8,
        help_text="Short letter shown in matrix cells (e.g. 'R', 'A', 'C', 'I')",
    )
    color = models.CharField(max_length=20, blank=True)
    order = models.PositiveIntegerField(default=0)
    taxonomy = models.CharField(
        max_length=20,
        choices=Taxonomy.choices,
        default=Taxonomy.CUSTOM,
        help_text="Which responsibility taxonomy this role belongs to",
    )
    builtin = models.BooleanField(default=False)
    is_visible = models.BooleanField(default=True)
    translations = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        ordering = ["taxonomy", "order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @classmethod
    def create_default_roles(cls):
        # Called from core.startup so the root folder exists on fresh installs.
        root = Folder.objects.filter(content_type=Folder.ContentType.ROOT).first()
        if root is None:
            return
        for role in cls.DEFAULT_ROLES:
            cls.objects.update_or_create(
                taxonomy=role["taxonomy"],
                code=role["code"],
                defaults={
                    "name": role["name"],
                    "order": role["order"],
                    "color": role["color"],
                    "builtin": True,
                    "is_visible": True,
                    "folder": root,
                },
            )


class ResponsibilityMatrix(NameDescriptionFolderMixin, FilteringLabelMixin):
    class Preset(models.TextChoices):
        RACI = "raci", "RACI"
        RASCI = "rasci", "RASCI"
        RAPID = "rapid", "RAPID"
        CUSTOM = "custom", "Custom"

    ref_id = models.CharField(max_length=100, blank=True)
    preset = models.CharField(
        max_length=20,
        choices=Preset.choices,
        default=Preset.RACI,
    )
    roles = models.ManyToManyField(
        ResponsibilityRole,
        related_name="matrices",
        blank=True,
    )
    projects = models.ManyToManyField(
        Project,
        related_name="responsibility_matrices",
        blank=True,
    )

    def save(self, *args, **kwargs):
        # On folder move, propagate to children — they only inherit folder at create-time,
        # so IAM scoping would drift. bulk update() skips save() (no recursion).
        folder_changed = False
        if self.pk:
            old_folder_id = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list("folder_id", flat=True)
                .first()
            )
            if old_folder_id and old_folder_id != self.folder_id:
                folder_changed = True
        super().save(*args, **kwargs)
        if folder_changed:
            self.activities.update(folder=self.folder)
            self.matrix_actors.update(folder=self.folder)
            ResponsibilityAssignment.objects.filter(activity__matrix=self).update(
                folder=self.folder
            )


class ResponsibilityMatrixActivity(AbstractBaseModel, FolderMixin):
    matrix = models.ForeignKey(
        ResponsibilityMatrix,
        on_delete=models.CASCADE,
        related_name="activities",
    )
    name = models.CharField(max_length=500)
    description = models.TextField(
        blank=True,
        help_text="Markdown-formatted long-form description of this activity",
    )
    order = models.PositiveIntegerField(default=0)
    assets = models.ManyToManyField(
        "core.Asset",
        blank=True,
        related_name="responsibility_activities",
    )
    applied_controls = models.ManyToManyField(
        "core.AppliedControl",
        blank=True,
        related_name="responsibility_activities",
    )
    task_templates = models.ManyToManyField(
        "core.TaskTemplate",
        blank=True,
        related_name="responsibility_activities",
    )
    risk_assessments = models.ManyToManyField(
        "core.RiskAssessment",
        blank=True,
        related_name="responsibility_activities",
    )
    compliance_assessments = models.ManyToManyField(
        "core.ComplianceAssessment",
        blank=True,
        related_name="responsibility_activities",
    )
    findings_assessments = models.ManyToManyField(
        "core.FindingsAssessment",
        blank=True,
        related_name="responsibility_activities",
    )
    business_impact_analyses = models.ManyToManyField(
        "resilience.BusinessImpactAnalysis",
        blank=True,
        related_name="responsibility_activities",
    )

    class Meta:
        ordering = ["order", "id"]

    def save(self, *args, **kwargs):
        # Inherit folder from the parent matrix for IAM scoping.
        self.folder = self.matrix.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ResponsibilityMatrixActor(AbstractBaseModel, FolderMixin):
    matrix = models.ForeignKey(
        ResponsibilityMatrix,
        on_delete=models.CASCADE,
        related_name="matrix_actors",
    )
    actor = models.ForeignKey(
        "core.Actor",
        on_delete=models.CASCADE,
        related_name="matrix_memberships",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["matrix", "actor"],
                name="unique_matrix_actor",
            )
        ]

    def save(self, *args, **kwargs):
        self.folder = self.matrix.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actor} in {self.matrix.name}"


class ResponsibilityAssignment(AbstractBaseModel, FolderMixin):
    activity = models.ForeignKey(
        ResponsibilityMatrixActivity,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    actor = models.ForeignKey(
        "core.Actor",
        on_delete=models.CASCADE,
        related_name="responsibility_assignments",
    )
    role = models.ForeignKey(
        ResponsibilityRole,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["activity", "actor"],
                name="unique_responsibility_cell",
            )
        ]

    def save(self, *args, **kwargs):
        self.folder = self.activity.matrix.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.actor} = {self.role.code} for {self.activity.name}"


common_exclude = ["created_at", "updated_at"]
auditlog.register(
    GenericCollection,
    exclude_fields=common_exclude,
)
auditlog.register(
    CollectionItem,
    exclude_fields=common_exclude,
)
auditlog.register(
    Accreditation,
    exclude_fields=common_exclude,
)
auditlog.register(
    Project,
    exclude_fields=common_exclude,
)
auditlog.register(
    ResponsibilityRole,
    exclude_fields=common_exclude,
)
auditlog.register(
    ResponsibilityMatrix,
    exclude_fields=common_exclude,
)
auditlog.register(
    ResponsibilityMatrixActivity,
    exclude_fields=common_exclude,
)
auditlog.register(
    ResponsibilityMatrixActor,
    exclude_fields=common_exclude,
)
auditlog.register(
    ResponsibilityAssignment,
    exclude_fields=common_exclude,
)
