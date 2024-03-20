from django.apps import apps
from django.forms.models import model_to_dict
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.html import mark_safe
from django.db.models import Q

from .base_models import *
from .validators import validate_file_size, validate_file_name
from .utils import camel_case
from iam.models import FolderMixin, PublishInRootFolderMixin
from django.core import serializers

import os
import json

from django.urls import reverse
from datetime import date, datetime
from typing import Self
from django.utils.html import format_html

from structlog import get_logger

logger = get_logger(__name__)

User = get_user_model()

########################### Referential objects #########################


class ReferentialObjectMixin(NameDescriptionMixin, FolderMixin):
    """
    Mixin for referential objects.
    """

    urn = models.CharField(
        max_length=100, null=True, blank=True, unique=True, verbose_name=_("URN")
    )
    ref_id = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Reference ID")
    )
    locale = models.CharField(
        max_length=100, null=False, blank=False, default="en", verbose_name=_("Locale")
    )
    default_locale = models.BooleanField(default=True, verbose_name=_("Default locale"))
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider")
    )
    name = models.CharField(
        null=True, max_length=200, verbose_name=_("Name"), unique=False
    )
    description = models.TextField(null=True, blank=True, verbose_name=_("Description"))
    annotation = models.TextField(null=True, blank=True, verbose_name=_("Annotation"))

    class Meta:
        abstract = True

    @property
    def display_short(self) -> str:
        _name = (
            self.ref_id
            if not self.name
            else self.name
            if not self.ref_id
            else f"{self.ref_id} - {self.name}"
        )
        _name = "" if not _name else _name
        return _name

    @property
    def display_long(self) -> str:
        _name = self.display_short
        _display = (
            _name
            if not self.description
            else self.description
            if _name == ""
            else f"{_name}: {self.description}"
        )
        return _display

    def __str__(self) -> str:
        return self.display_short


class Library(ReferentialObjectMixin):
    copyright = models.CharField(
        max_length=4096, null=True, blank=True, verbose_name=_("Copyright")
    )
    version = models.IntegerField(null=False, verbose_name=_("Version"))
    provider = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Provider of the library"),
        verbose_name=_("Provider"),
    )
    packager = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Packager of the library"),
        verbose_name=_("Packager"),
    )
    dependencies = models.ManyToManyField(
        "self", blank=True, verbose_name=_("Dependencies"), symmetrical=False
    )

    @property
    def _objects(self):
        res = {}
        if self.frameworks.count() > 0:
            res["framework"] = model_to_dict(self.frameworks.first())
            res["framework"].update(self.frameworks.first().library_entry)
        if self.threats.count() > 0:
            res["threats"] = [model_to_dict(threat) for threat in self.threats.all()]
        if self.reference_controls.count() > 0:
            res["reference_controls"] = [
                model_to_dict(reference_control)
                for reference_control in self.reference_controls.all()
            ]
        if self.risk_matrices.count() > 0:
            matrix = self.risk_matrices.first()
            res["risk_matrix"] = model_to_dict(matrix)
            res["risk_matrix"]["probability"] = matrix.probability
            res["risk_matrix"]["impact"] = matrix.impact
            res["risk_matrix"]["risk"] = matrix.risk
            res["risk_matrix"]["grid"] = matrix.grid
            res["strength_of_knowledge"] = matrix.strength_of_knowledge
            res["risk_matrix"] = [res["risk_matrix"]]
        return res

    @property
    def reference_count(self) -> int:
        """
        Returns the number of distinct dependent libraries and risk and compliance assessments that reference objects from this library
        """
        return (
            RiskAssessment.objects.filter(
                Q(risk_scenarios__threats__library=self)
                | Q(risk_matrix__library=self)
                | Q(risk_scenarios__applied_controls__reference_control__library=self)
            )
            .distinct()
            .count()
            + ComplianceAssessment.objects.filter(
                Q(framework__library=self)
                | Q(
                    requirement_assessments__applied_controls__reference_control__library=self
                )
            )
            .distinct()
            .count()
            + Library.objects.filter(dependencies=self).distinct().count()
        )

    def delete(self, *args, **kwargs):
        if self.reference_count > 0:
            raise ValueError(
                "This library is still referenced by some risk or compliance assessments"
            )
        dependent_libraries = Library.objects.filter(dependencies=self)
        if dependent_libraries:
            raise ValueError(
                f"This library is a dependency of {dependent_libraries.count()} other libraries"
            )
        super(Library, self).delete(*args, **kwargs)


class Threat(ReferentialObjectMixin, PublishInRootFolderMixin):
    library = models.ForeignKey(
        Library, on_delete=models.CASCADE, null=True, blank=True, related_name="threats"
    )

    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Threat")
        verbose_name_plural = _("Threats")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.requirements.count() > 0:
            return False
        return True

    @property
    def frameworks(self):
        return Framework.objects.filter(requirement__threats=self).distinct()

    def __str__(self):
        return self.name


class ReferenceControl(ReferentialObjectMixin):
    CATEGORY = [
        ("policy", _("Policy")),
        ("process", _("Process")),
        ("technical", _("Technical")),
        ("physical", _("Physical")),
    ]

    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reference_controls",
    )

    category = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=CATEGORY,
        verbose_name=_("Category"),
    )

    typical_evidence = models.JSONField(
        verbose_name=_("Typical evidence"), null=True, blank=True
    )

    fields_to_check = ["ref_id", "name"]

    class Meta:
        verbose_name = _("Reference control")
        verbose_name_plural = _("Reference controls")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.requirements.count() or self.appliedcontrol_set.count() > 0:
            return False
        return True

    @property
    def frameworks(self):
        return Framework.objects.filter(requirement__reference_controls=self).distinct()

    def __str__(self):
        return self.name


class RiskMatrix(ReferentialObjectMixin):
    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="risk_matrices",
    )

    json_definition = models.JSONField(
        verbose_name=_("JSON definition"),
        help_text=_(
            "JSON definition of the risk matrix. \
        See the documentation for more information."
        ),
        default=dict,
    )
    is_enabled = models.BooleanField(
        _("enabled"),
        default=True,
        help_text=_(
            "If the risk matrix is set as disabled, it will not be available for selection for new risk assessments."
        ),
    )
    provider = models.CharField(
        max_length=200, blank=True, null=True, verbose_name=_("Provider")
    )

    @property
    def is_used(self) -> bool:
        return RiskAssessment.objects.filter(risk_matrix=self).exists()

    @property
    def risk_assessments(self) -> list:
        return RiskAssessment.objects.filter(risk_matrix=self)

    @property
    def projects(self) -> list:
        return Project.objects.filter(riskassessment__risk_matrix=self).distinct()

    def parse_json(self) -> dict:
        return json.loads(self.json_definition)

    @property
    def grid(self) -> list:
        risk_matrix = self.parse_json()
        grid = []
        for row in risk_matrix["grid"]:
            grid.append([item for item in row])
        return grid

    @property
    def probability(self) -> list:
        risk_matrix = self.parse_json()
        return risk_matrix["probability"]

    @property
    def impact(self) -> list:
        risk_matrix = self.parse_json()
        return risk_matrix["impact"]

    @property
    def risk(self) -> list:
        risk_matrix = self.parse_json()
        return risk_matrix["risk"]

    @property
    def strength_of_knowledge(self):
        risk_matrix = self.parse_json()
        return risk_matrix.get("strength_of_knowledge")

    def render_grid_as_colors(self):
        risk_matrix = self.parse_json()
        grid = risk_matrix["grid"]
        res = [[risk_matrix["risk"][i] for i in row] for row in grid]

        return res

    def __str__(self) -> str:
        return self.name


class Framework(ReferentialObjectMixin):
    library = models.ForeignKey(
        Library,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="frameworks",
    )

    class Meta:
        verbose_name = _("Framework")
        verbose_name_plural = _("Frameworks")

    def is_deletable(self) -> bool:
        """
        Returns True if the framework can be deleted
        """
        if self.compliance_assessment_set.count() > 0:
            return False
        return True

    @property
    def library_entry(self):
        res = {}
        requirement_nodes = self.get_requirement_nodes()
        if requirement_nodes:
            res["requirement_nodes"] = requirement_nodes

        requirement_levels = self.get_requirement_levels()
        if requirement_levels:
            res["requirement_levels"] = requirement_levels

        return res

    def get_requirement_nodes(self):
        # Prefetch related objects if they exist to reduce database queries.
        # Adjust prefetch_related paths according to your model relationships.
        nodes_queryset = self.requirement_nodes.prefetch_related(
            "threats", "reference_controls"
        )
        if nodes_queryset.exists():
            return [self.process_node(node) for node in nodes_queryset]
        return []

    def process_node(self, node):
        # Convert the node to dict and process threats and security functions.
        node_dict = model_to_dict(node)
        if node.threats.exists():
            node_dict["threats"] = [
                model_to_dict(threat) for threat in node.threats.all()
            ]
        if node.reference_controls.exists():
            node_dict["reference_controls"] = [
                model_to_dict(reference_control)
                for reference_control in node.reference_controls.all()
            ]
        return node_dict

    def get_requirement_levels(self):
        levels_queryset = self.requirement_levels.all()
        if levels_queryset.exists():
            return [model_to_dict(level) for level in levels_queryset]
        return []


class RequirementLevel(ReferentialObjectMixin):
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Framework"),
        related_name="requirement_levels",
    )
    level = models.IntegerField(null=False, blank=False, verbose_name=_("Level"))

    class Meta:
        verbose_name = _("Requirements level")
        verbose_name_plural = _("Requirements levels")


class RequirementNode(ReferentialObjectMixin):
    threats = models.ManyToManyField(
        "Threat",
        blank=True,
        verbose_name=_("Threats"),
        related_name="requirements",
    )
    reference_controls = models.ManyToManyField(
        "ReferenceControl",
        blank=True,
        verbose_name=_("Reference controls"),
        related_name="requirements",
    )
    framework = models.ForeignKey(
        Framework,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Framework"),
        related_name="requirement_nodes",
    )
    parent_urn = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Parent URN")
    )
    order_id = models.IntegerField(null=True, verbose_name=_("Order ID"))
    level = models.IntegerField(null=True, verbose_name=_("Level"))
    maturity = models.IntegerField(null=True, verbose_name=_("Maturity"))
    assessable = models.BooleanField(null=False, verbose_name=_("Assessable"))

    class Meta:
        verbose_name = _("RequirementNode")
        verbose_name_plural = _("RequirementNodes")


########################### Domain objects #########################


class Project(NameDescriptionMixin, FolderMixin):
    PRJ_LC_STATUS = [
        ("undefined", _("Undefined")),
        ("in_design", _("Design")),
        ("in_dev", _("Development")),
        ("in_prod", _("Production")),
        ("eol", _("EndOfLife")),
        ("dropped", _("Dropped")),
    ]
    internal_reference = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_("Internal reference")
    )
    lc_status = models.CharField(
        max_length=20,
        default="in_design",
        choices=PRJ_LC_STATUS,
        verbose_name=_("Status"),
    )
    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def overall_compliance(self):
        compliance_assessments_list = [
            compliance_assessment
            for compliance_assessment in self.compliance_assessment_set.all()
        ]
        count = (
            RequirementAssessment.objects.filter(status="compliant")
            .filter(compliance_assessment__in=compliance_assessments_list)
            .count()
        )
        total = RequirementAssessment.objects.filter(
            compliance_assessment__in=compliance_assessments_list
        ).count()
        if total == 0:
            return 0
        return round(count * 100 / total)

    def __str__(self):
        return self.name


class Asset(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    class Type(models.TextChoices):
        """
        The type of the asset.

        An asset can either be a primary or a support asset.
        A support asset can be linked to another "parent" asset of type primary or support.
        Cycles are not allowed
        """

        PRIMARY = "PR", _("Primary")
        SUPPORT = "SP", _("Support")

    business_value = models.CharField(
        max_length=200, blank=True, verbose_name=_("business value")
    )
    type = models.CharField(
        max_length=2, choices=Type.choices, default=Type.SUPPORT, verbose_name=_("type")
    )
    parent_assets = models.ManyToManyField(
        "self", blank=True, verbose_name=_("parent assets"), symmetrical=False
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name_plural = _("Assets")
        verbose_name = _("Asset")

    def __str__(self) -> str:
        return str(self.name)

    def is_primary(self) -> bool:
        """
        Returns True if the asset is a primary asset.
        """
        return self.type == Asset.Type.PRIMARY

    def is_support(self) -> bool:
        """
        Returns True if the asset is a support asset.
        """
        return self.type == Asset.Type.SUPPORT

    def ancestors_plus_self(self) -> list[Self]:
        result = {self}
        for x in self.parent_assets.all():
            result.update(x.ancestors_plus_self())
        return list(result)


class Evidence(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    # TODO: Manage file upload to S3/MiniO
    attachment = models.FileField(
        #        upload_to=settings.LOCAL_STORAGE_DIRECTORY,
        blank=True,
        null=True,
        help_text=_("Attachment for evidence (eg. screenshot, log file, etc.)"),
        verbose_name=_("Attachment"),
        validators=[validate_file_size, validate_file_name],
    )
    link = models.URLField(
        blank=True,
        null=True,
        help_text=_("Link to the evidence (eg. Jira ticket, etc.)"),
        verbose_name=_("Link"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Evidence")
        verbose_name_plural = _("Evidences")

    def get_folder(self):
        if self.applied_controls:
            return self.applied_controls.first().folder
        elif self.requirement_assessments:
            return self.requirement_assessments.first().folder
        else:
            return None

    def filename(self):
        return os.path.basename(self.attachment.name)


class AppliedControl(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        ACTIVE = "active", _("Active")
        INACTIVE = "inactive", _("Inactive")

    CATEGORY = ReferenceControl.CATEGORY

    EFFORT = [
        ("S", _("Small")),
        ("M", _("Medium")),
        ("L", _("Large")),
        ("XL", _("Extra Large")),
    ]

    MAP_EFFORT = {None: -1, "S": 1, "M": 2, "L": 4, "XL": 8}
    # todo: think about a smarter model for ranking
    reference_control = models.ForeignKey(
        ReferenceControl,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Reference Control"),
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        verbose_name=_("Evidences"),
        related_name="applied_controls",
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY,
        null=True,
        blank=True,
        verbose_name=_("Category"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        null=True,
        blank=True,
        verbose_name=_("Status"),
    )
    eta = models.DateField(
        blank=True,
        null=True,
        help_text=_("Estimated Time of Arrival"),
        verbose_name=_("ETA"),
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text=_("Date after which the applied control is no longer valid"),
        verbose_name=_("Expiry date"),
    )
    link = models.CharField(
        null=True,
        blank=True,
        max_length=1000,
        help_text=_("External url for action follow-up (eg. Jira ticket)"),
        verbose_name=_("Link"),
    )
    effort = models.CharField(
        null=True,
        blank=True,
        max_length=2,
        choices=EFFORT,
        help_text=_("Relative effort of the measure (using T-Shirt sizing)"),
        verbose_name=_("Effort"),
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Applied control")
        verbose_name_plural = _("Applied controls")

    def save(self, *args, **kwargs):
        if self.reference_control and self.category is None:
            self.category = self.reference_control.category
        super(AppliedControl, self).save(*args, **kwargs)

    @property
    def risk_scenarios(self):
        return self.risk_scenarios.all()

    @property
    def risk_assessments(self):
        return {scenario.risk_assessment for scenario in self.risk_scenarios}

    @property
    def projects(self):
        return {risk_assessment.project for risk_assessment in self.risk_assessments}

    def parent_project(self):
        pass

    def __str__(self):
        return self.name

    @property
    def mid(self):
        return f"M.{self.scoped_id(scope=AppliedControl.objects.filter(folder=self.folder))}"

    @property
    def csv_value(self):
        return f"[{self.status}] {self.name}" if self.status else self.name

    def get_ranking_score(self):
        value = 0
        for risk_scenario in self.risk_scenarios.all():
            current = risk_scenario.current_level
            residual = risk_scenario.residual_level
            if current >= 0 and residual >= 0:
                value += (1 + current - residual) * (current + 1)
        return abs(round(value / self.MAP_EFFORT[self.effort], 4))

    @property
    def get_html_url(self):
        url = reverse("appliedcontrol-detail", args=(self.id,))
        return format_html(
            '<a class="" href="{}"> <b>[MT-eta]</b> {}: {} </a>',
            url,
            self.folder.name,
            self.name,
        )

    def get_linked_requirements_count(self):
        return RequirementNode.objects.filter(
            requirementassessment__applied_controls=self
        ).count()


class PolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(category="policy")

    def create(self, *args, **kwargs):
        kwargs["category"] = "policy"  # Ensure category is always "policy"
        return super().create(*args, **kwargs)


class Policy(AppliedControl):
    class Meta:
        proxy = True
        verbose_name = _("Policy")
        verbose_name_plural = _("Policies")

    objects = PolicyManager()  # Use the custom manager

    def save(self, *args, **kwargs):
        self.category = "policy"
        super(Policy, self).save(*args, **kwargs)


########################### Secondary objects #########################


class Assessment(NameDescriptionMixin):
    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_PROGRESS = "in_progress", _("In progress")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        DEPRECATED = "deprecated", _("Deprecated")

    project = models.ForeignKey(
        "Project", on_delete=models.CASCADE, verbose_name=_("Project")
    )
    version = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Version of the compliance assessment (eg. 1.0, 2.0, etc.)"),
        verbose_name=_("Version"),
        default="1.0",
    )
    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name=_("Status"),
        blank=True,
        null=True,
    )
    authors = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Authors"),
        related_name="%(class)s_authors",
    )
    reviewers = models.ManyToManyField(
        User,
        blank=True,
        verbose_name=_("Reviewers"),
        related_name="%(class)s_reviewers",
    )
    eta = models.DateField(
        null=True,
        blank=True,
        help_text=_("Estimated time of arrival"),
        verbose_name=_("ETA"),
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Due date"),
        verbose_name=_("Due date"),
    )

    fields_to_check = ["name", "version"]

    class Meta:
        abstract = True


class RiskAssessment(Assessment):
    risk_matrix = models.ForeignKey(
        RiskMatrix,
        on_delete=models.PROTECT,
        help_text=_("WARNING! After choosing it, you will not be able to change it"),
        verbose_name=_("Risk matrix"),
    )

    class Meta:
        verbose_name = _("Risk assessment")
        verbose_name_plural = _("Risk assessments")

    def __str__(self) -> str:
        return f"{self.project.folder}/{self.project}/{self.name} - {self.version}"

    @property
    def path_display(self) -> str:
        return f"{self.project.folder}/{self.project}/{self.name} - {self.version}"

    def get_scenario_count(self) -> int:
        count = RiskScenario.objects.filter(risk_assessment=self.id).count()
        scenario_count = count
        return scenario_count

    def quality_check(self) -> dict:
        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the risk risk_assessment:
        _object = serializers.serialize("json", [self])
        _object = json.loads(_object)
        if self.status == Assessment.Status.IN_PROGRESS:
            info_lst.append(
                {
                    "msg": _("{}: Risk assessment is still in progress").format(
                        str(self)
                    ),
                    "obj_type": "risk_assessment",
                    "object": _object,
                }
            )
        if not self.authors.all():
            info_lst.append(
                {
                    "msg": _("{}: No author assigned to this risk assessment").format(
                        str(self)
                    ),
                    "obj_type": "risk_assessment",
                    "object": _object,
                }
            )
        if not self.risk_scenarios.all():
            warnings_lst.append(
                {
                    "msg": _(
                        "{}: RiskAssessment is empty. No risk scenario declared yet"
                    ).format(self),
                    "obj_type": "risk_assessment",
                    "object": _object,
                }
            )
        # ---

        # --- checks on the risk scenarios
        # TODO: Refactor this
        _scenarios = serializers.serialize(
            "json", self.risk_scenarios.all().order_by("created_at")
        )
        scenarios = [x["fields"] for x in json.loads(_scenarios)]
        for ri in scenarios:
            if ri["current_level"] < 0:
                warnings_lst.append(
                    {
                        "msg": _("{} current risk level has not been assessed").format(
                            ri["name"]
                        ),
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_level"] < 0 and ri["current_level"] >= 0:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk level has not been assessed. If no additional measures are applied, it should be at the same level as the current risk"
                        ).format(ri["name"]),
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_level"] > ri["current_level"]:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk level is higher than the current one"
                        ).format(ri["name"]),
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_proba"] > ri["current_proba"]:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk probability is higher than the current one"
                        ).format(ri["name"]),
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )
            if ri["residual_impact"] > ri["current_impact"]:
                errors_lst.append(
                    {
                        "msg": _(
                            "{} residual risk impact is higher than the current one"
                        ).format(ri["name"]),
                        "obj_type": "riskscenario",
                        "object": ri,
                    }
                )

            if (
                ri["residual_level"] < ri["current_level"]
                or ri["residual_proba"] < ri["current_proba"]
                or ri["residual_impact"] < ri["current_impact"]
            ):
                if (
                    len(ri.get("applied_controls", {})) == 0
                    and ri["residual_level"] >= 0
                ):
                    errors_lst.append(
                        {
                            "msg": _(
                                "{}: residual risk level has been lowered without any specific measure"
                            ).format(ri["name"]),
                            "obj_type": "riskscenario",
                            "object": ri,
                        }
                    )

            if ri["treatment"] == "accepted":
                if not ri.get("riskacceptance_set", {}).get("exists", lambda: False)():
                    warnings_lst.append(
                        {
                            "msg": _(
                                "{} risk accepted but no risk acceptance attached"
                            ).format(ri),
                            "obj_type": "riskscenario",
                            "object": ri,
                        }
                    )
        # --- checks on the applied controls
        _measures = serializers.serialize(
            "json",
            AppliedControl.objects.filter(
                risk_scenarios__risk_assessment=self
            ).order_by("created_at"),
        )
        measures = [x["fields"] for x in json.loads(_measures)]
        for i in range(len(measures)):
            measures[i]["id"] = json.loads(_measures)[i]["pk"]

        for mtg in measures:
            if not mtg["eta"]:
                warnings_lst.append(
                    {
                        "msg": _("{} does not have an ETA").format(mtg["name"]),
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )
            else:
                if date.today() > datetime.strptime(mtg["eta"], "%Y-%m-%d").date():
                    errors_lst.append(
                        {
                            "msg": _(
                                "{} ETA is in the past now. Consider updating its status or the date"
                            ).format(mtg["name"]),
                            "obj_type": "appliedcontrol",
                            "object": {"name": mtg["name"], "id": mtg["id"]},
                        }
                    )

            if not mtg["effort"]:
                warnings_lst.append(
                    {
                        "msg": _(
                            "{} does not have an estimated effort. This will help you for prioritization"
                        ).format(mtg["name"]),
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )

            if not mtg["link"]:
                info_lst.append(
                    {
                        "msg": _(
                            "{}: Applied control does not have an external link attached. This will help you for follow-up"
                        ).format(mtg["name"]),
                        "obj_type": "appliedcontrol",
                        "object": {"name": mtg["name"], "id": mtg["id"]},
                    }
                )

        # --- checks on the risk acceptances
        _acceptances = serializers.serialize(
            "json",
            RiskAcceptance.objects.filter(risk_scenarios__risk_assessment=self)
            .distinct()
            .order_by("created_at"),
        )
        acceptances = [x["fields"] for x in json.loads(_acceptances)]
        for ra in acceptances:
            if not ra["expiry_date"]:
                warnings_lst.append(
                    {
                        "msg": _("{}: Acceptance has no expiry date").format(
                            ra["name"]
                        ),
                        "obj_type": "appliedcontrol",
                        "object": ra,
                    }
                )
                continue
            if date.today() > datetime.strptime(ra["expiry_date"], "%Y-%m-%d").date():
                errors_lst.append(
                    {
                        "msg": _(
                            "{}: Acceptance has expired. Consider updating the status or the date"
                        ).format(ra["name"]),
                        "obj_type": "riskacceptance",
                        "object": ra,
                    }
                )

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": sum([len(errors_lst), len(warnings_lst), len(info_lst)]),
        }
        return findings

    # NOTE: if your save() method throws an exception, you might want to override the clean() method to prevent
    # 500 errors when the form submitted. See https://docs.djangoproject.com/en/dev/ref/models/instances/#django.db.models.Model.clean


def risk_scoring(probability, impact, risk_matrix: RiskMatrix) -> int:
    fields = json.loads(risk_matrix.json_definition)
    risk_index = fields["grid"][probability][impact]
    return risk_index


class RiskScenario(NameDescriptionMixin):
    TREATMENT_OPTIONS = [
        ("open", _("Open")),
        ("mitigate", _("Mitigate")),
        ("accept", _("Accept")),
        ("avoid", _("Avoid")),
        ("transfer", _("Transfer")),
    ]

    DEFAULT_SOK_OPTIONS = {
        -1: {
            "name": _("--"),
            "description": _(
                "The strength of the knowledge supporting the assessment is undefined"
            ),
        },
        0: {
            "name": _("Low"),
            "description": _(
                "The strength of the knowledge supporting the assessment is low"
            ),
            "symbol": "◇",
        },
        1: {
            "name": _("Medium"),
            "description": _(
                "The strength of the knowledge supporting the assessment is medium"
            ),
            "symbol": "⬙",
        },
        2: {
            "name": _("High"),
            "description": _(
                "The strength of the knowledge supporting the assessment is high"
            ),
            "symbol": "◆",
        },
    }

    risk_assessment = models.ForeignKey(
        RiskAssessment,
        on_delete=models.CASCADE,
        verbose_name=_("RiskAssessment"),
        related_name="risk_scenarios",
    )
    assets = models.ManyToManyField(
        Asset,
        verbose_name=_("Assets"),
        blank=True,
        help_text=_("Assets impacted by the risk scenario"),
        related_name="risk_scenarios",
    )
    applied_controls = models.ManyToManyField(
        AppliedControl,
        verbose_name=_("Applied controls"),
        blank=True,
        related_name="risk_scenarios",
    )
    threats = models.ManyToManyField(
        Threat,
        verbose_name=_("Threats"),
        blank=True,
        related_name="risk_scenarios",
    )
    existing_controls = models.TextField(
        max_length=2000,
        help_text=_(
            "The existing controls to manage this risk. Edit the risk scenario to add extra applied controls."
        ),
        verbose_name=_("Existing controls"),
        blank=True,
    )

    # current
    current_proba = models.SmallIntegerField(
        default=-1, verbose_name=_("Current probability")
    )
    current_impact = models.SmallIntegerField(
        default=-1, verbose_name=_("Current impact")
    )
    current_level = models.SmallIntegerField(
        default=-1,
        verbose_name=_("Current level"),
        help_text=_(
            "The risk level given the current measures. Automatically updated on Save, based on the chosen risk matrix"
        ),
    )

    # residual
    residual_proba = models.SmallIntegerField(
        default=-1, verbose_name=_("Residual probability")
    )
    residual_impact = models.SmallIntegerField(
        default=-1, verbose_name=_("Residual impact")
    )
    residual_level = models.SmallIntegerField(
        default=-1,
        verbose_name=_("Residual level"),
        help_text=_(
            "The risk level when all the extra measures are done. Automatically updated on Save, based on the chosen risk matrix"
        ),
    )

    treatment = models.CharField(
        max_length=20,
        choices=TREATMENT_OPTIONS,
        default="open",
        verbose_name=_("Treatment status"),
    )

    strength_of_knowledge = models.IntegerField(
        default=-1,
        verbose_name=_("Strength of Knowledge"),
        help_text=_("The strength of the knowledge supporting the assessment"),
    )
    justification = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Justification")
    )

    fields_to_check = ["name"]

    class Meta:
        verbose_name = _("Risk scenario")
        verbose_name_plural = _("Risk scenarios")

    # def get_rating_options(self, field: str) -> list[tuple]:
    #     risk_matrix = self.risk_assessment.risk_matrix.parse_json()
    #     return [(k, v) for k, v in risk_matrix.fields[field].items()]

    def parent_project(self):
        return self.risk_assessment.project

    parent_project.short_description = _("Project")

    def get_matrix(self):
        return self.risk_assessment.risk_matrix.parse_json()

    def get_current_risk(self):
        if self.current_level < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "hexcolor": "#A9A9A9",
            }
        risk_matrix = self.get_matrix()
        return risk_matrix["risk"][self.current_level]

    def get_current_impact(self):
        if self.current_impact < 0:
            return {"abbreviation": "--", "name": "--", "description": "not rated"}
        risk_matrix = self.get_matrix()
        return risk_matrix["impact"][self.current_impact]

    def get_current_proba(self):
        if self.current_proba < 0:
            return {"abbreviation": "--", "name": "--", "description": "not rated"}
        risk_matrix = self.get_matrix()
        return risk_matrix["probability"][self.current_proba]

    def get_residual_risk(self):
        if self.residual_level < 0:
            return {
                "abbreviation": "--",
                "name": "--",
                "description": "not rated",
                "hexcolor": "#A9A9A9",
            }
        risk_matrix = self.get_matrix()
        return risk_matrix["risk"][self.residual_level]

    def get_residual_impact(self):
        if self.residual_impact < 0:
            return {"abbreviation": "--", "name": "--", "description": "not rated"}
        risk_matrix = self.get_matrix()
        return risk_matrix["impact"][self.residual_impact]

    def get_residual_proba(self):
        if self.residual_proba < 0:
            return {"abbreviation": "--", "name": "--", "description": "not rated"}
        risk_matrix = self.get_matrix()
        return risk_matrix["probability"][self.residual_proba]

    def get_strength_of_knowledge(self):
        if self.strength_of_knowledge < 0:
            return self.DEFAULT_SOK_OPTIONS[-1]
        return self.DEFAULT_SOK_OPTIONS[self.strength_of_knowledge]

    def __str__(self):
        return (
            str(self.parent_project().folder)
            + _("/")
            + str(self.parent_project())
            + _(": ")
            + str(self.name)
        )

    @property
    def rid(self):
        """return associated risk assessment id"""
        return f"R.{self.scoped_id(scope=RiskScenario.objects.filter(risk_assessment=self.risk_assessment))}"

    def save(self, *args, **kwargs):
        if self.current_proba >= 0 and self.current_impact >= 0:
            self.current_level = risk_scoring(
                self.current_proba,
                self.current_impact,
                self.risk_assessment.risk_matrix,
            )
        else:
            self.current_level = -1
        if self.residual_proba >= 0 and self.residual_impact >= 0:
            self.residual_level = risk_scoring(
                self.residual_proba,
                self.residual_impact,
                self.risk_assessment.risk_matrix,
            )
        else:
            self.residual_level = -1
        super(RiskScenario, self).save(*args, **kwargs)


class ComplianceAssessment(Assessment):
    class Result(models.TextChoices):
        COMPLIANT = "compliant", _("Compliant")
        NON_COMPLIANT_MINOR = "non_compliant_minor", _("Non compliant (minor)")
        NON_COMPLIANT_MAJOR = "non_compliant_major", _("Non compliant (major)")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    framework = models.ForeignKey(
        Framework, on_delete=models.CASCADE, verbose_name=_("Framework")
    )
    result = models.CharField(
        blank=True,
        null=True,
        max_length=100,
        choices=Result.choices,
        verbose_name=_("Result"),
    )

    class Meta:
        verbose_name = _("Compliance assessment")
        verbose_name_plural = _("Compliance assessments")

    def get_requirements_status_count(self):
        requirements_status_count = []
        for st in RequirementAssessment.Status:
            requirements_status_count.append(
                (
                    RequirementAssessment.objects.filter(status=st)
                    .filter(compliance_assessment=self)
                    .count(),
                    st,
                )
            )
        return requirements_status_count

    def get_measures_status_count(self):
        measures_status_count = []
        measures_list = []
        for requirement_assessment in self.requirement_assessments.all():
            measures_list += requirement_assessment.applied_controls.all().values_list(
                "id", flat=True
            )
        for st in "AppliedControl".Status.choices:
            measures_status_count.append(
                (
                    "AppliedControl".objects.filter(status=st[0])
                    .filter(id__in=measures_list)
                    .count(),
                    st,
                )
            )
        print(
            "AppliedControl".objects.filter(status=st[0])
            .filter(id__in=measures_list)
            .count()
        )
        return measures_status_count

    def donut_render(self) -> dict:
        compliance_assessments_status = {"values": [], "labels": []}
        color_map = {
            "in_progress": "#3b82f6",
            "non_compliant": "#f87171",
            "to_do": "#d1d5db",
            "partially_compliant": "#fde047",
            "not_applicable": "#000000",
            "compliant": "#86efac",
        }
        for st in RequirementAssessment.Status:
            count = (
                RequirementAssessment.objects.filter(status=st)
                .filter(compliance_assessment=self)
                .filter(requirement__assessable=True)
                .count()
            )
            total = RequirementAssessment.objects.filter(
                compliance_assessment=self
            ).count()
            v = {
                "name": st.label,
                "localName": camel_case(st.value),
                "value": count,
                "itemStyle": {"color": color_map[st]},
            }
            compliance_assessments_status["values"].append(v)
            compliance_assessments_status["labels"].append(st.label)
        return compliance_assessments_status

    def quality_check(self) -> dict:
        AppliedControl = apps.get_model("core", "AppliedControl")

        errors_lst = list()
        warnings_lst = list()
        info_lst = list()
        # --- check on the assessment:
        _object = serializers.serialize("json", [self])
        _object = json.loads(_object)
        if self.status == Assessment.Status.IN_PROGRESS:
            info_lst.append(
                {
                    "msg": _("{}: Compliance assessment is still in progress").format(
                        str(self)
                    ),
                    "obj_type": "complianceassessment",
                    "object": _object,
                }
            )

        if not self.authors.all():
            info_lst.append(
                {
                    "msg": _(
                        "{}: No author assigned to this compliance assessment"
                    ).format(str(self)),
                    "obj_type": "complianceassessment",
                    "object": _object,
                }
            )
        # ---

        # --- check on requirement assessments:
        _requirement_assessments = self.requirement_assessments.all().order_by(
            "created_at"
        )
        requirement_assessments = []
        for ra in _requirement_assessments:
            ra_dict = json.loads(serializers.serialize("json", [ra]))[0]["fields"]
            ra_dict["repr"] = str(ra)
            requirement_assessments.append(ra_dict)
        for requirement_assessment in requirement_assessments:
            if (
                requirement_assessment["status"] in ("compliant", "partially_compliant")
                and len(requirement_assessment["applied_controls"]) == 0
            ):
                warnings_lst.append(
                    {
                        "msg": _(
                            "{}: Requirement assessment status is compliant or partially compliant with no applied control applied"
                        ).format(requirement_assessment["repr"]),
                        "obj_type": "requirementassessment",
                        "object": requirement_assessment,
                    }
                )
        # ---

        # --- check on applied controls:
        _applied_controls = serializers.serialize(
            "json",
            AppliedControl.objects.filter(
                requirement_assessments__compliance_assessment=self
            ).order_by("created_at"),
        )
        applied_controls = [x["fields"] for x in json.loads(_applied_controls)]
        for applied_control in applied_controls:
            if not applied_control["reference_control"]:
                info_lst.append(
                    {
                        "msg": _(
                            "{}: Applied control has no reference control selected"
                        ).format(applied_control["name"]),
                        "obj_type": "appliedcontrol",
                        "object": applied_control,
                    }
                )
        # ---

        # --- check on evidence:
        _evidences = serializers.serialize(
            "json",
            Evidence.objects.filter(
                applied_controls__in=AppliedControl.objects.filter(
                    requirement_assessments__compliance_assessment=self
                )
            ).order_by("created_at"),
        )
        evidences = [x["fields"] for x in json.loads(_evidences)]
        for evidence in evidences:
            if not evidence["attachment"]:
                warnings_lst.append(
                    {
                        "msg": _("{}: Evidence has no file uploaded").format(
                            evidence["name"]
                        ),
                        "obj_type": "evidence",
                        "object": evidence,
                    }
                )

        findings = {
            "errors": errors_lst,
            "warnings": warnings_lst,
            "info": info_lst,
            "count": sum([len(errors_lst), len(warnings_lst), len(info_lst)]),
        }
        return findings


class RequirementAssessment(AbstractBaseModel, FolderMixin):
    class Status(models.TextChoices):
        TODO = "to_do", _("To do")
        IN_PROGRESS = "in_progress", _("In progress")
        NON_COMPLIANT = "non_compliant", _("Non compliant")
        PARTIALLY_COMPLIANT = "partially_compliant", _("Partially compliant")
        COMPLIANT = "compliant", _("Compliant")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    status = models.CharField(
        max_length=100,
        choices=Status.choices,
        default=Status.TODO,
        verbose_name=_("Status"),
    )
    evidences = models.ManyToManyField(
        Evidence,
        blank=True,
        verbose_name=_("Evidences"),
        related_name="requirement_assessments",
    )
    observation = models.TextField(null=True, blank=True, verbose_name=_("Observation"))
    compliance_assessment = models.ForeignKey(
        ComplianceAssessment,
        on_delete=models.CASCADE,
        verbose_name=_("Compliance assessment"),
        related_name="requirement_assessments",
    )
    requirement = models.ForeignKey(
        RequirementNode, on_delete=models.CASCADE, verbose_name=_("Requirement")
    )
    applied_controls = models.ManyToManyField(
        "AppliedControl",
        blank=True,
        verbose_name=_("Applied controls"),
        related_name="requirement_assessments",
    )

    def __str__(self) -> str:
        return self.requirement.display_short

    class Meta:
        verbose_name = _("Requirement assessment")
        verbose_name_plural = _("Requirement assessments")


########################### RiskAcesptance is a domain object relying on secondary objects #########################


class RiskAcceptance(NameDescriptionMixin, FolderMixin, PublishInRootFolderMixin):
    ACCEPTANCE_STATE = [
        ("created", _("Created")),
        ("submitted", _("Submitted")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        ("revoked", _("Revoked")),
    ]

    risk_scenarios = models.ManyToManyField(
        RiskScenario,
        verbose_name=_("Risk scenarios"),
        help_text=_(
            "Select the risk scenarios to be accepted, attention they must be part of the chosen domain"
        ),
    )
    approver = models.ForeignKey(
        User,
        max_length=200,
        help_text=_("Risk owner and approver identity"),
        verbose_name=_("Approver"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    state = models.CharField(
        max_length=20,
        choices=ACCEPTANCE_STATE,
        default="created",
        verbose_name=_("State"),
    )
    expiry_date = models.DateField(
        help_text=_("Specify when the risk acceptance will no longer apply"),
        null=True,
        verbose_name=_("Expiry date"),
    )
    accepted_at = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Acceptance date")
    )
    rejected_at = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Rejection date")
    )
    revoked_at = models.DateTimeField(
        blank=True, null=True, verbose_name=_("Revocation date")
    )
    justification = models.CharField(
        max_length=500, blank=True, null=True, verbose_name=_("Justification")
    )

    fields_to_check = ["name"]

    class Meta:
        permissions = [
            ("approve_riskacceptance", "Can validate/rejected risk acceptances")
        ]
        verbose_name = _("Risk acceptance")
        verbose_name_plural = _("Risk acceptances")

    def __str__(self):
        if self.name:
            return self.name
        scenario_names: str = ", ".join(
            [str(scenario) for scenario in self.risk_scenarios.all()]
        )
        return f"{scenario_names}"

    @property
    def get_html_url(self):
        url = reverse("riskacceptance-detail", args=(self.id,))
        return format_html(
            '<a class="" href="{}"> <b>[RA-exp]</b> {}: {} </a>',
            url,
            self.folder.name,
            self.name,
        )

    def set_state(self, state):
        self.state = state
        if state == "accepted":
            self.accepted_at = datetime.now()
        if state == "rejected":
            self.rejected_at = datetime.now()
        elif state == "revoked":
            self.revoked_at = datetime.now()
        self.save()
