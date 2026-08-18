from auditlog.registry import auditlog
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.base_models import AbstractBaseModel, NameDescriptionMixin
from core.models import FilteringLabelMixin
from iam.models import FolderMixin, User


class RemediationIssue(NameDescriptionMixin, FolderMixin, FilteringLabelMixin):
    """A governed remediation case: a Lead and a Respondent side formalize, accept,
    and track one commitment (issues-engagements.md §10).

    Links to business objects are untyped and inert: they grant no access and
    synchronize no lifecycle. The folder is copied from the creation context by
    the caller and stays independent afterwards.
    """

    class Status(models.TextChoices):
        PLANNED = "planned", _("Planned")
        IN_DISCUSSION = "in_discussion", _("In discussion")
        IN_REMEDIATION = "in_remediation", _("In remediation")
        IN_REVIEW = "in_review", _("In review")
        DONE = "done", _("Done")
        CANCELLED = "cancelled", _("Cancelled")

    class Side(models.TextChoices):
        LEAD = "lead", _("Lead")
        RESPONDENT = "respondent", _("Respondent")

    class Resolution(models.TextChoices):
        REMEDIATED = "remediated", _("Remediated")
        ACCEPTED_AS_IS = "accepted_as_is", _("Accepted as-is")
        NOT_APPLICABLE = "not_applicable", _("Not applicable")

    class CancellationReason(models.TextChoices):
        DUPLICATE = "duplicate", _("Duplicate")
        SUPERSEDED = "superseded", _("Superseded")
        WITHDRAWN = "withdrawn", _("Withdrawn")
        CREATED_IN_ERROR = "created_in_error", _("Created in error")
        OTHER = "other", _("Other")

    class AcceptanceState(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        CHANGES_REQUESTED = "changes_requested", _("Changes requested")

    PRIORITY = [
        (1, _("P1")),
        (2, _("P2")),
        (3, _("P3")),
        (4, _("P4")),
    ]

    ref_id = models.CharField(
        max_length=100, blank=True, verbose_name=_("Reference ID")
    )
    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY, null=True, blank=True, verbose_name=_("Priority")
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name=_("Status"),
    )
    resolution = models.CharField(
        max_length=32,
        choices=Resolution.choices,
        blank=True,
        verbose_name=_("Resolution"),
    )
    closure_justification = models.TextField(
        blank=True, verbose_name=_("Closure justification")
    )
    cancellation_reason = models.CharField(
        max_length=32,
        choices=CancellationReason.choices,
        blank=True,
        verbose_name=_("Cancellation reason"),
    )
    closed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Closed at")
    )

    lead_representatives = models.ManyToManyField(
        "core.Actor",
        blank=True,
        related_name="lead_representative_issues",
        verbose_name=_("Lead representatives"),
    )
    respondent_representatives = models.ManyToManyField(
        "core.Actor",
        blank=True,
        related_name="respondent_representative_issues",
        verbose_name=_("Respondent representatives"),
    )
    lead_contributors = models.ManyToManyField(
        "core.Actor",
        blank=True,
        related_name="lead_contributor_issues",
        verbose_name=_("Lead contributors"),
    )
    respondent_contributors = models.ManyToManyField(
        "core.Actor",
        blank=True,
        related_name="respondent_contributor_issues",
        verbose_name=_("Respondent contributors"),
    )

    requirement_assessments = models.ManyToManyField(
        "core.RequirementAssessment",
        blank=True,
        related_name="remediation_issues",
        verbose_name=_("Requirement assessments"),
    )
    findings = models.ManyToManyField(
        "core.Finding",
        blank=True,
        related_name="remediation_issues",
        verbose_name=_("Findings"),
    )
    evidences = models.ManyToManyField(
        "core.Evidence",
        blank=True,
        related_name="remediation_issues",
        verbose_name=_("Evidences"),
    )
    applied_controls = models.ManyToManyField(
        "core.AppliedControl",
        blank=True,
        related_name="remediation_issues",
        verbose_name=_("Applied controls"),
    )

    fields_to_check = ["name"]

    class Meta(FilteringLabelMixin.Meta):
        verbose_name = _("Remediation issue")
        verbose_name_plural = _("Remediation issues")

    @property
    def current_commitment(self):
        return self.commitment_versions.order_by("-version_number").first()

    @property
    def acceptance_state(self) -> str | None:
        """Derived overall state with precedence changes_requested > pending > accepted
        (issues-engagements.md §10.5). None when no commitment exists yet."""
        version = self.current_commitment
        if version is None:
            return None
        states = (version.lead_acceptance, version.respondent_acceptance)
        if self.AcceptanceState.CHANGES_REQUESTED in states:
            return "changes_requested"
        if version.lead_acceptance == self.AcceptanceState.PENDING:
            return "pending_lead"
        if version.respondent_acceptance == self.AcceptanceState.PENDING:
            return "pending_respondent"
        return "accepted"

    def representatives_for(self, side: str):
        if side == self.Side.LEAD:
            return self.lead_representatives
        return self.respondent_representatives

    def sides_acted_by(self, user: User) -> set[str]:
        """Sides for which this user has already performed a commitment action
        (proposed a version or set an acceptance), across all versions of this
        Issue — the scope of the Allow self-validation check (§10.5)."""
        sides: set[str] = set()
        for version in self.commitment_versions.all():
            if version.author_id == user.pk:
                sides.add(version.author_side)
            if version.lead_acceptance_user_id == user.pk:
                sides.add(self.Side.LEAD)
            if version.respondent_acceptance_user_id == user.pk:
                sides.add(self.Side.RESPONDENT)
        return sides

    def user_is_representative(self, user: User, side: str) -> bool:
        """Eligibility resolves through the listed actors: a User directly, a Team
        through its leader/deputies/members, an Entity through its representatives'
        user accounts (issues-engagements.md §10.3)."""
        actors = self.representatives_for(side).select_related(
            "user", "team", "entity"
        )
        for actor in actors:
            if actor.user_id is not None:
                if actor.user_id == user.pk:
                    return True
            elif actor.team_id is not None:
                team = actor.team
                if (
                    team.leader_id == user.pk
                    or team.deputies.filter(pk=user.pk).exists()
                    or team.members.filter(pk=user.pk).exists()
                ):
                    return True
            elif actor.entity_id is not None:
                if actor.entity.representatives.filter(user=user).exists():
                    return True
        return False


class CommitmentVersion(AbstractBaseModel, FolderMixin):
    """One version of an Issue's commitment (issues-engagements.md §10.4).

    Content is immutable after creation — any change to text or due date is a new
    version. Acceptance fields live on the version row and may change only while
    the version is current; a superseded version is entirely immutable. The audit
    log provides the event history.
    """

    CONTENT_FIELDS = (
        "issue_id",
        "version_number",
        "text",
        "due_date",
        "author_id",
        "author_side",
    )
    ACCEPTANCE_FIELDS = (
        "lead_acceptance",
        "lead_acceptance_user_id",
        "lead_acceptance_at",
        "respondent_acceptance",
        "respondent_acceptance_user_id",
        "respondent_acceptance_at",
    )

    issue = models.ForeignKey(
        RemediationIssue,
        on_delete=models.CASCADE,
        related_name="commitment_versions",
        verbose_name=_("Issue"),
    )
    version_number = models.PositiveIntegerField(default=1)
    text = models.TextField(verbose_name=_("Commitment"))
    due_date = models.DateField(null=True, blank=True, verbose_name=_("Due date"))
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_commitment_versions",
    )
    author_side = models.CharField(
        max_length=16, choices=RemediationIssue.Side.choices
    )

    lead_acceptance = models.CharField(
        max_length=20,
        choices=RemediationIssue.AcceptanceState.choices,
        default=RemediationIssue.AcceptanceState.PENDING,
    )
    lead_acceptance_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    lead_acceptance_at = models.DateTimeField(null=True, blank=True)
    respondent_acceptance = models.CharField(
        max_length=20,
        choices=RemediationIssue.AcceptanceState.choices,
        default=RemediationIssue.AcceptanceState.PENDING,
    )
    respondent_acceptance_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    respondent_acceptance_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-version_number"]
        verbose_name = _("Commitment version")
        verbose_name_plural = _("Commitment versions")
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "version_number"],
                name="unique_commitment_version_per_issue",
            )
        ]

    def __str__(self) -> str:
        return f"{self.issue} v{self.version_number}"

    @property
    def is_current(self) -> bool:
        return not self.issue.commitment_versions.filter(
            version_number__gt=self.version_number
        ).exists()

    @property
    def accepted(self) -> bool:
        return (
            self.lead_acceptance == RemediationIssue.AcceptanceState.ACCEPTED
            and self.respondent_acceptance
            == RemediationIssue.AcceptanceState.ACCEPTED
        )

    def acceptance_field_names(self, side: str) -> tuple[str, str, str]:
        prefix = (
            "lead" if side == RemediationIssue.Side.LEAD else "respondent"
        )
        return (
            f"{prefix}_acceptance",
            f"{prefix}_acceptance_user",
            f"{prefix}_acceptance_at",
        )

    def save(self, *args, **kwargs):
        # Children denormalize folder/is_published from the issue (owned child).
        self.folder = self.issue.folder
        self.is_published = self.issue.is_published
        if not self._state.adding:
            db_row = CommitmentVersion.objects.get(pk=self.pk)
            if any(
                getattr(db_row, field) != getattr(self, field)
                for field in self.CONTENT_FIELDS
            ):
                raise ValidationError({"error": "commitmentContentImmutable"})
            acceptance_changed = any(
                getattr(db_row, field) != getattr(self, field)
                for field in self.ACCEPTANCE_FIELDS
            )
            if acceptance_changed and not db_row.is_current:
                raise ValidationError({"error": "supersededCommitmentImmutable"})
        super().save(*args, **kwargs)


common_exclude = ["created_at", "updated_at"]
auditlog.register(
    RemediationIssue,
    exclude_fields=common_exclude,
    m2m_fields={
        "lead_representatives",
        "respondent_representatives",
        "lead_contributors",
        "respondent_contributors",
        "requirement_assessments",
        "findings",
        "evidences",
        "applied_controls",
    },
)
auditlog.register(
    CommitmentVersion,
    exclude_fields=common_exclude,
)
