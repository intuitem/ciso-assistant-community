from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel
from core.models import NameDescriptionMixin
from iam.models import FolderMixin
from sec_intel.models import TTPCatalog, Tactic, Technique


class ThreatModel(NameDescriptionMixin, FolderMixin):
    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )
    catalog = models.ForeignKey(
        TTPCatalog,
        on_delete=models.PROTECT,
        related_name="threat_models",
        verbose_name=_("TTP catalog"),
    )
    graph_columns = models.JSONField(
        default=dict, blank=True, help_text="Lane sizes in the editor"
    )
    risk_scenarios = models.ManyToManyField(
        "core.RiskScenario",
        blank=True,
        related_name="threat_models",
        verbose_name=_("Risk scenarios"),
    )
    quantitative_risk_scenarios = models.ManyToManyField(
        "crq.QuantitativeRiskScenario",
        blank=True,
        related_name="threat_models",
        verbose_name=_("Quantitative risk scenarios"),
    )

    fields_to_check = ["name"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # nodes and edges mirror the model's folder
        self.nodes.exclude(folder=self.folder).update(folder=self.folder)
        self.edges.exclude(folder=self.folder).update(folder=self.folder)

    class Meta:
        verbose_name = _("Threat model")
        verbose_name_plural = _("Threat models")
        ordering = ["created_at"]


class ThreatModelNode(AbstractBaseModel, FolderMixin):
    class Kind(models.TextChoices):
        TECHNIQUE = "technique", _("Technique")
        # explicit variable: Noisy-OR cannot express conjunction
        OPERATOR = "operator", _("Operator")
        CUSTOM = "custom", _("Custom")

    class Operator(models.TextChoices):
        AND = "AND", "AND"
        OR = "OR", "OR"

    threat_model = models.ForeignKey(
        ThreatModel, on_delete=models.CASCADE, related_name="nodes"
    )
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.TECHNIQUE,
        verbose_name=_("Kind"),
    )
    technique = models.ForeignKey(
        Technique,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="threat_model_nodes",
        verbose_name=_("Technique"),
    )
    # stored, not derived: 145 of 697 techniques sit in >1 tactic
    tactic = models.ForeignKey(
        Tactic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="threat_model_nodes",
        verbose_name=_("Tactic"),
    )
    operator = models.CharField(
        max_length=3,
        choices=Operator.choices,
        null=True,
        blank=True,
        verbose_name=_("Operator"),
    )
    label = models.CharField(max_length=255, blank=True, verbose_name=_("Label"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    assets = models.ManyToManyField(
        "core.Asset",
        blank=True,
        related_name="threat_model_nodes",
        verbose_name=_("Assets"),
    )
    applied_controls = models.ManyToManyField(
        "core.AppliedControl",
        blank=True,
        related_name="threat_model_nodes",
        verbose_name=_("Applied controls"),
    )
    vulnerabilities = models.ManyToManyField(
        "core.Vulnerability",
        blank=True,
        related_name="threat_model_nodes",
        verbose_name=_("Vulnerabilities"),
    )
    is_highlighted = models.BooleanField(default=False, verbose_name=_("Highlighted"))
    properties = models.JSONField(default=dict, blank=True)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)

    class Meta:
        verbose_name = _("Threat model node")
        verbose_name_plural = _("Threat model nodes")
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["threat_model", "technique", "tactic"],
                name="unique_threat_model_node_placement",
            )
        ]

    def __str__(self):
        return self.label or str(self.technique or self.get_kind_display())

    def save(self, *args, **kwargs):
        self.folder = self.threat_model.folder
        super().save(*args, **kwargs)


class ThreatModelEdge(AbstractBaseModel, FolderMixin):
    threat_model = models.ForeignKey(
        ThreatModel, on_delete=models.CASCADE, related_name="edges"
    )
    source = models.ForeignKey(
        ThreatModelNode, on_delete=models.CASCADE, related_name="outgoing"
    )
    target = models.ForeignKey(
        ThreatModelNode, on_delete=models.CASCADE, related_name="incoming"
    )
    label = models.CharField(max_length=255, blank=True, verbose_name=_("Label"))

    class Meta:
        verbose_name = _("Threat model edge")
        verbose_name_plural = _("Threat model edges")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.source} → {self.target}"

    def save(self, *args, **kwargs):
        self.folder = self.threat_model.folder
        super().save(*args, **kwargs)
