import secrets

from django.db import models
from django.utils import timezone

from auditlog.registry import auditlog
from core.base_models import AbstractBaseModel, NameDescriptionMixin
from core.models import FilteringLabelMixin
from iam.models import FolderMixin


class NameDescriptionFolderMixin(NameDescriptionMixin, FolderMixin):
    class Meta:
        abstract = True


def generate_webhook_secret():
    return secrets.token_urlsafe(32)


class DraftExistsError(Exception):
    """Raised by clone_as_draft when the workflow already has a draft —
    detected under the workflow row lock, after the caller's unlocked
    pre-check has passed (one draft at a time)."""

    def __init__(self, draft):
        self.draft = draft
        super().__init__("draftAlreadyExists")


class Workflow(NameDescriptionFolderMixin, FilteringLabelMixin):
    ref_id = models.CharField(max_length=100, blank=True)
    # Master switch: gates AUTOMATIC execution only — manual runs
    # keep working so a paused workflow stays debuggable. Cascades to versions.
    is_active = models.BooleanField(default=True)
    # Absolute run TTL in seconds: a run older than this is
    # terminated. 0 = no limit. Cascades to versions like is_active; the
    # engine reads the frozen version copy so an edit can't retroactively
    # change in-flight runs.
    timeout_seconds = models.PositiveIntegerField(default=0)
    # Marketplace/catalog provenance: where an imported document
    # came from. Purely informational — the workflow divorces at import and
    # owns its own lifecycle; nothing ever syncs back.
    source_urn = models.CharField(max_length=255, blank=True)
    source_version = models.CharField(max_length=50, blank=True)

    fields_to_check = ["name"]

    # Explicit merge of the base classes' Meta (both abstract-only) so option
    # resolution is deterministic instead of implicit MRO.
    class Meta(NameDescriptionFolderMixin.Meta, FilteringLabelMixin.Meta):
        pass

    def save(self, *args, **kwargs):
        # On folder move, propagate to versions and their children — they only
        # inherit folder at create-time, so IAM scoping would drift.
        folder_changed = False
        active_changed = False
        timeout_changed = False
        if self.pk:
            previous = (
                type(self)
                .objects.filter(pk=self.pk)
                .values("folder_id", "is_active", "timeout_seconds")
                .first()
            )
            if previous:
                if previous["folder_id"] and previous["folder_id"] != self.folder_id:
                    folder_changed = True
                if previous["is_active"] != self.is_active:
                    active_changed = True
                if previous["timeout_seconds"] != self.timeout_seconds:
                    timeout_changed = True
        super().save(*args, **kwargs)
        if active_changed:
            # The version flag is the enforcement layer every execution path
            # checks; not user-toggleable per version in this iteration.
            self.versions.update(is_active=self.is_active)
        if timeout_changed:
            # Same mirroring as is_active: the engine reads the version copy.
            self.versions.update(timeout_seconds=self.timeout_seconds)
        if folder_changed:
            self.versions.update(folder=self.folder)
            self.triggers.update(folder=self.folder)
            self.secrets.update(folder=self.folder)
            WorkflowNode.objects.filter(version__workflow=self).update(
                folder=self.folder
            )
            WorkflowEdge.objects.filter(version__workflow=self).update(
                folder=self.folder
            )
            WorkflowVariable.objects.filter(version__workflow=self).update(
                folder=self.folder
            )
            ConditionBranch.objects.filter(node__version__workflow=self).update(
                folder=self.folder
            )
            ConditionGroup.objects.filter(branch__node__version__workflow=self).update(
                folder=self.folder
            )
            Condition.objects.filter(
                group__branch__node__version__workflow=self
            ).update(folder=self.folder)

    @property
    def published_version(self):
        return self.versions.filter(status=WorkflowVersion.Status.PUBLISHED).first()

    @property
    def draft_version(self):
        return self.versions.filter(status=WorkflowVersion.Status.DRAFT).first()


class WorkflowVersion(AbstractBaseModel, FolderMixin):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField(default=1)
    # Mirrors Workflow.is_active — set by the cascade, checked by
    # every automatic execution path.
    is_active = models.BooleanField(default=True)
    # Mirror of Workflow.timeout_seconds, like is_active: seeded on create,
    # kept in sync by the Workflow.save cascade. The engine reads this copy,
    # so a TTL edit applies to in-flight runs too. 0 = no limit.
    timeout_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)
    # Run authorization: published_by is permanent provenance;
    # run_as is the authority the version's runs wield (definer rights,
    # checked live). v1 stamps both with the publisher; v2 makes run_as
    # pickable. Null run_as on a non-draft version = unrunnable (fail closed,
    # republish to fix). Drafts run as the invoker instead.
    published_by = models.ForeignKey(
        "iam.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    run_as = models.ForeignKey(
        "iam.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "version_number"],
                name="unique_workflow_version_number",
            )
        ]

    def save(self, *args, **kwargs):
        self.folder = self.workflow.folder
        # Inherit the TTL from the parent on first save so a new
        # draft/clone carries the workflow's current limit; later edits mirror
        # via Workflow.save(). Only on create — never clobber a frozen copy.
        if self._state.adding:
            self.timeout_seconds = self.workflow.timeout_seconds
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow.name} v{self.version_number}"

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT

    def publish(self, user):
        """Publish this draft and archive the previously published version.

        Graph validity must be checked by the caller (see workflows.validation)
        before calling this. Trigger registrations are synced here so the
        published graph and its operational rows can never drift. The
        publisher becomes the version's run identity: publishing
        is the moment authority attaches.
        """
        from django.db import transaction

        from .triggers import sync_trigger_registrations

        with transaction.atomic():
            # Serialize publish/draft flows per workflow: without the row lock
            # two concurrent publishes could archive each other's version.
            Workflow.objects.select_for_update().get(pk=self.workflow_id)
            WorkflowVersion.objects.filter(
                workflow=self.workflow, status=self.Status.PUBLISHED
            ).update(status=self.Status.ARCHIVED)
            self.status = self.Status.PUBLISHED
            self.published_at = timezone.now()
            self.published_by = user
            self.run_as = user
            self.save()
            sync_trigger_registrations(self)

    def clone_as_draft(self):
        """Clone this version's whole graph into a new draft.

        Raises DraftExistsError if the workflow already has a draft — checked
        under the workflow row lock, so two concurrent clones cannot both pass
        the callers' unlocked pre-check and fork two drafts.
        """
        from django.db import transaction

        with transaction.atomic():
            Workflow.objects.select_for_update().get(pk=self.workflow_id)
            existing_draft = self.workflow.draft_version
            if existing_draft is not None:
                raise DraftExistsError(existing_draft)
            last_number = (
                self.workflow.versions.order_by("-version_number")
                .values_list("version_number", flat=True)
                .first()
            )
            draft = WorkflowVersion.objects.create(
                workflow=self.workflow,
                version_number=(last_number or 0) + 1,
                # A draft cloned from a paused workflow must not come up
                # active — the cascade only fires when the flag changes.
                is_active=self.workflow.is_active,
            )
            variable_map = {
                variable.id: _clone_row(variable, version=draft)
                for variable in self.variables.all()
            }
            node_map = {}
            branch_map = {}
            nodes = self.nodes.prefetch_related(
                models.Prefetch(
                    "branches__condition_groups",
                    queryset=ConditionGroup.objects.filter(parent_group=None),
                ),
            )
            for node in nodes:
                clone = _clone_row(node, version=draft)
                node_map[node.id] = clone
                for branch in node.branches.all():
                    branch_clone = _clone_row(branch, node=clone)
                    branch_map[branch.id] = branch_clone
                    # The prefetch above narrows condition_groups to root
                    # groups; .all() reuses that cache where .filter() would
                    # re-query per branch.
                    for group in branch.condition_groups.all():
                        _clone_condition_group(group, branch_clone, None, variable_map)
            for edge in self.edges.all():
                _clone_row(
                    edge,
                    version=draft,
                    source_node=node_map[edge.source_node_id],
                    target_node=node_map[edge.target_node_id],
                    source_branch=branch_map.get(edge.source_branch_id),
                )
            return draft


class WorkflowNode(AbstractBaseModel, FolderMixin):
    class Meta(AbstractBaseModel.Meta, FolderMixin.Meta):
        # Rows are saved one at a time in payload order (save_graph), so
        # created_at is the authored order. Without an explicit ordering
        # PostgreSQL returns heap order and exports stop round-tripping.
        ordering = ["created_at"]

    class Type(models.TextChoices):
        TRIGGER = "trigger", "Trigger"
        END = "end", "End"
        TASK = "task", "Task"
        CONDITION = "condition", "Condition"
        ACTION = "action", "Action"
        LOOP = "loop", "Loop"
        SUBPROCESS = "subprocess", "Subprocess"
        EVENT = "event", "Event"

    class TriggerType(models.TextChoices):
        MANUAL = "manual", "Manual"
        WEBHOOK = "webhook", "Webhook"
        SCHEDULE = "schedule", "Schedule"
        INTERNAL_EVENT = "internal_event", "Internal event"

    class RetryBackoff(models.TextChoices):
        FIXED = "fixed", "Fixed"
        EXPONENTIAL = "exponential", "Exponential"

    version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    label = models.CharField(max_length=200, blank=True)
    # Stable slug for {{nodes.<ref>.<path>}} references.
    # Auto-generated from the label on first save, then never regenerated.
    ref = models.CharField(max_length=100, blank=True)
    task_template = models.ForeignKey(
        "core.TaskTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_nodes",
    )
    action_config = models.JSONField(default=dict, blank=True)
    # Loop nodes: {collection, collect?, on_item_error}.
    loop_config = models.JSONField(default=dict, blank=True)
    # Definition half of a trigger node: {"type": manual|webhook|
    # schedule|internal_event, ...subtype keys}. Operational state (enabled,
    # secrets, bookkeeping) lives on WorkflowTrigger rows synced at publish.
    trigger_config = models.JSONField(default=dict, blank=True)
    subprocess_workflow = models.ForeignKey(
        Workflow,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subprocess_nodes",
    )
    input_mapping = models.JSONField(default=dict, blank=True)
    output_mapping = models.JSONField(default=dict, blank=True)
    event_key = models.CharField(max_length=200, blank=True)
    event_filters = models.JSONField(default=dict, blank=True)
    position = models.JSONField(default=dict, blank=True)
    retry_max_attempts = models.PositiveIntegerField(default=0)
    retry_delay_seconds = models.PositiveIntegerField(default=60)
    retry_backoff = models.CharField(
        max_length=20,
        choices=RetryBackoff.choices,
        default=RetryBackoff.FIXED,
    )

    def save(self, *args, **kwargs):
        self.folder = self.version.folder
        if not self.ref:
            self.ref = self._generate_ref()
        super().save(*args, **kwargs)

    @staticmethod
    def slugify_ref(label, node_type):
        """Base ref slug shared by draft ref generation and export ref
        synthesis (import_export._ref_map). Keep the two in step: same
        separator, length cap, and empty-slug fallback."""
        from django.utils.text import slugify

        return slugify(label or node_type).replace("-", "_")[:80] or node_type

    def _generate_ref(self):
        base = self.slugify_ref(self.label, self.type)
        candidate = base
        suffix = 2
        while (
            WorkflowNode.objects.filter(version=self.version, ref=candidate)
            .exclude(pk=self.pk)
            .exists()
        ):
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate

    def __str__(self):
        return self.label or self.type


class WorkflowEdge(AbstractBaseModel, FolderMixin):
    version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name="edges",
    )
    source_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
    )
    target_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="incoming_edges",
    )
    # For edges leaving a condition node: the branch this wire belongs to.
    # Deleting the branch removes its wire. Null for plain edges.
    source_branch = models.ForeignKey(
        "automation.ConditionBranch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="edges",
    )
    label = models.CharField(max_length=200, blank=True)
    # Loop-node output port ("each"|"done"); blank elsewhere.
    source_port = models.CharField(max_length=10, blank=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.version.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.source_node} → {self.target_node}"


class WorkflowVariable(AbstractBaseModel, FolderMixin):
    class Type(models.TextChoices):
        STRING = "string", "String"
        NUMBER = "number", "Number"
        BOOLEAN = "boolean", "Boolean"
        DATE = "date", "Date"
        JSON = "json", "JSON"

    version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name="variables",
    )
    key = models.CharField(max_length=100)
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.STRING,
    )
    default_value = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ["key"]
        constraints = [
            models.UniqueConstraint(
                fields=["version", "key"],
                name="unique_workflow_variable_key",
            )
        ]

    def save(self, *args, **kwargs):
        self.folder = self.version.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return self.key


class ConditionBranch(AbstractBaseModel, FolderMixin):
    """A named routing branch of a condition node. Owns its
    condition tree relationally. A branch exists independently
    of its wire, so the builder can define branches before connecting them
    ("define now, wire later"); the wire is the WorkflowEdge whose
    source_branch points here. Exactly one branch per condition node is the
    default (always matches, evaluated last)."""

    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="branches",
    )
    name = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["order", "created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.node.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name or ("otherwise" if self.is_default else "branch")


class ConditionGroup(AbstractBaseModel, FolderMixin):
    class Operator(models.TextChoices):
        AND = "and", "AND"
        OR = "or", "OR"
        NOT = "not", "NOT"

    branch = models.ForeignKey(
        ConditionBranch,
        on_delete=models.CASCADE,
        related_name="condition_groups",
    )
    parent_group = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    operator = models.CharField(
        max_length=10,
        choices=Operator.choices,
        default=Operator.AND,
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.branch.folder
        super().save(*args, **kwargs)


class Condition(AbstractBaseModel, FolderMixin):
    class Operator(models.TextChoices):
        EQ = "eq", "Equals"
        NEQ = "neq", "Not equals"
        GT = "gt", "Greater than"
        LT = "lt", "Less than"
        GTE = "gte", "Greater than or equal"
        LTE = "lte", "Less than or equal"
        IN = "in", "In"
        NOT_IN = "not_in", "Not in"
        CONTAINS = "contains", "Contains"
        IS_NULL = "is_null", "Is null"

    group = models.ForeignKey(
        ConditionGroup,
        on_delete=models.CASCADE,
        related_name="conditions",
    )
    variable = models.ForeignKey(
        WorkflowVariable,
        on_delete=models.PROTECT,
        related_name="conditions",
    )
    op = models.CharField(max_length=20, choices=Operator.choices)
    value = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.group.folder
        super().save(*args, **kwargs)


class WorkflowInstance(AbstractBaseModel, FolderMixin):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        ABANDONED = "abandoned", "Abandoned"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        WEBHOOK = "webhook", "Webhook"
        SUBPROCESS = "subprocess", "Subprocess"
        SCHEDULED = "scheduled", "Scheduled"
        INTERNAL_EVENT = "internal_event", "Internal event"

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="instances",
    )
    version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name="instances",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    trigger = models.CharField(
        max_length=20,
        choices=Trigger.choices,
        default=Trigger.MANUAL,
    )
    variables = models.JSONField(default=dict, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    # Per-node action outputs keyed by node ref (or node id for pre-ref
    # graphs), addressable in templates as {{nodes.<ref>.<path>}} and browsed
    # by the builder's reference-run data panel.
    node_outputs = models.JSONField(default=dict, blank=True)
    initiated_by = models.ForeignKey(
        "iam.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_workflow_instances",
    )
    parent_instance = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    parent_token = models.ForeignKey(
        "automation.WorkflowToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subprocess_instances",
    )
    trigger_registration = models.ForeignKey(
        "automation.WorkflowTrigger",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
    )
    # Event-chain generation counter: user/API-caused events start
    # instances at depth 1; changes those runs make start instances at depth 2,
    # capped by events.MAX_TRIGGER_DEPTH to contain trigger loops.
    trigger_depth = models.PositiveSmallIntegerField(default=0)
    # auditlog correlation id of the user action this run reacted to; the
    # event dispatcher coalesces on it (events.COALESCE_WINDOW). Set there
    # only — a webhook payload must never reach it.
    trigger_cid = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            # The coalescing lookup, on every event dispatch.
            models.Index(fields=["trigger_registration", "trigger_cid"]),
        ]

    def save(self, *args, **kwargs):
        if not self.folder_id:
            self.folder = self.version.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow.name} run {str(self.id)[:8]}"


class WorkflowToken(AbstractBaseModel, FolderMixin):
    class Meta(AbstractBaseModel.Meta, FolderMixin.Meta):
        indexes = [
            # The engine filters an instance's tokens by status on every step.
            models.Index(fields=["instance", "status"]),
        ]

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        WAITING = "waiting", "Waiting"
        CONSUMED = "consumed", "Consumed"
        COMPLETED = "completed", "Completed"
        RETRYING = "retrying", "Retrying"
        ERROR = "error", "Error"

    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    current_node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="tokens",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    arrived_via_edge = models.ForeignKey(
        WorkflowEdge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tokens",
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    # Set when a token is parked WAITING for a deferred task and cleared by
    # the delivery that claims it, so a duplicate huey delivery cannot run
    # the side effect twice. The token stays WAITING while in flight.
    dispatch_id = models.UUIDField(null=True, blank=True, editable=False)
    # Iteration context STACK: [{item, index}, ...] — nested loops
    # push/pop; {{item}}/{{index}} resolve to the innermost entry.
    iteration_context = models.JSONField(default=list, blank=True)
    # Controller state for a token parked ON a loop node:
    # {items, index, results, errors}.
    loop_state = models.JSONField(default=dict, blank=True)
    # Body tokens point back at the controller token that emitted them.
    loop_controller = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="loop_body_tokens",
    )

    def save(self, *args, **kwargs):
        self.folder = self.instance.folder
        super().save(*args, **kwargs)


class WorkflowInstanceLog(AbstractBaseModel, FolderMixin):
    class EventType(models.TextChoices):
        INSTANCE_STARTED = "instance_started", "Instance started"
        NODE_ENTERED = "node_entered", "Node entered"
        ACTION_EXECUTED = "action_executed", "Action executed"
        TASK_WAITING = "task_waiting", "Waiting for task"
        EVENT_WAITING = "event_waiting", "Waiting for event"
        EVENT_RECEIVED = "event_received", "Event received"
        SUBPROCESS_STARTED = "subprocess_started", "Subprocess started"
        LOOP_COMPLETED = "loop_completed", "Loop completed"
        AUTHORIZATION_DENIED = "authorization_denied", "Authorization denied"
        RUN_TERMINATED = "run_terminated", "Run terminated"
        INSTANCE_COMPLETED = "instance_completed", "Instance completed"
        ERROR = "error", "Error"

    instance = models.ForeignKey(
        WorkflowInstance,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    edge = models.ForeignKey(
        WorkflowEdge,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    message = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        self.folder = self.instance.folder
        super().save(*args, **kwargs)


class WorkflowSecret(AbstractBaseModel, FolderMixin):
    """Named credential for http_request, referenced as {{secrets.NAME}}.
    Values are write-only at the API level: never returned in responses,
    resolved only by the engine at execution time.

    Workflow-scoped: a secret belongs to one workflow and is only ever
    resolvable by that workflow's instances (no cross-workflow or cross-folder
    reads). Shared/reusable secrets are a future additive tier. Folder is
    propagated from the workflow so RBAC and API scoping keep working."""

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="secrets",
    )
    name = models.CharField(max_length=100)
    value = models.TextField(default="")

    fields_to_check = ["name"]

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "name"],
                name="unique_workflow_secret_name",
            )
        ]

    def save(self, *args, **kwargs):
        self.folder = self.workflow.folder
        super().save(*args, **kwargs)

    def get_scope(self):
        # Uniqueness is per-workflow (matches the DB constraint), not per-folder
        # — two workflows in the same folder may each have a "TOKEN" secret.
        return self.__class__.objects.filter(workflow=self.workflow).order_by(
            "created_at", "id"
        )

    def __str__(self):
        return self.name


class WorkflowTrigger(AbstractBaseModel, FolderMixin):
    """Operational registration for a published trigger node.

    The definition (subtype, cron, event key, filters, input mapping) lives in
    the immutable graph; rows are synced at publish time
    (workflows.triggers.sync_trigger_registrations) and carry only runtime
    state: enabled, webhook credentials, bookkeeping. Manual trigger nodes get
    no row. The node ref is the identity — a ref rename between publishes is a
    delete + create (state resets, webhook URL changes)."""

    class Type(models.TextChoices):
        WEBHOOK = "webhook", "Webhook"
        SCHEDULE = "schedule", "Schedule"
        INTERNAL_EVENT = "internal_event", "Internal event"

    class Result(models.TextChoices):
        TRIGGERED = "triggered", "Triggered"
        SKIPPED_OVERLAP = "skipped_overlap", "Skipped (previous run still active)"
        SKIPPED_UNPUBLISHED = "skipped_unpublished", "Skipped (unpublished)"
        SKIPPED_DEPTH = "skipped_depth", "Skipped (chain depth)"
        SKIPPED_INACTIVE = "skipped_inactive", "Skipped (workflow inactive)"
        SKIPPED_NO_IDENTITY = "run_identity_missing", "Skipped (no run identity)"
        SKIPPED_INVALID_SCHEDULE = "invalid_schedule", "Skipped (invalid schedule)"
        SKIPPED_COALESCED = (
            "skipped_coalesced",
            "Skipped (same user action already handled)",
        )
        ERROR = "error", "Error"

    workflow = models.ForeignKey(
        Workflow,
        on_delete=models.CASCADE,
        related_name="triggers",
    )
    node_ref = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=Type.choices)
    # Snapshot of the published node's trigger_config, so the scheduler and
    # the event dispatcher never need to read the graph.
    config = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=False)
    # Webhook credential for /hooks/{workflow}/{node_ref}/{secret}/ plus the
    # optional HMAC secret (X-Hub-Signature-256). Write-only at the API;
    # never part of the graph or of YAML exports.
    secret = models.CharField(
        max_length=64, default=generate_webhook_secret, unique=True
    )
    hmac_secret = models.CharField(max_length=128, blank=True)
    # Schedule bookkeeping. next_run_at is computed at publish-sync, on
    # enable-toggle and by the scheduler's CAS claim — never in save().
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    # Event bookkeeping; event_key is denormalized from config for the
    # indexed dispatch gate (one EXISTS query per audited save).
    event_key = models.CharField(max_length=200, blank=True, db_index=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_result = models.CharField(max_length=30, choices=Result.choices, blank=True)
    trigger_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "node_ref"],
                name="unique_workflow_trigger_node_ref",
            )
        ]
        indexes = [
            # The scheduler tick filters due rows on exactly these three.
            models.Index(fields=["type", "enabled", "next_run_at"]),
        ]

    def save(self, *args, **kwargs):
        self.folder = self.workflow.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow.name}: {self.node_ref} ({self.type})"


def _clone_row(instance, **overrides):
    # attname copies raw FK ids, so cloning never lazy-loads the related
    # objects it is about to override anyway.
    data = {
        field.attname: getattr(instance, field.attname)
        for field in instance._meta.concrete_fields
        if field.name not in ("id", "created_at", "updated_at")
    }
    for key in overrides:
        # An override passed by field name ("version") must not clash with
        # the copied raw id ("version_id") — the ORM rejects both at once.
        data.pop(instance._meta.get_field(key).attname, None)
    data.update(overrides)
    return type(instance).objects.create(**data)


def _clone_condition_group(group, branch_clone, parent_clone, variable_map):
    group_clone = _clone_row(group, branch=branch_clone, parent_group=parent_clone)
    for condition in group.conditions.all():
        _clone_row(
            condition,
            group=group_clone,
            variable=variable_map[condition.variable_id],
        )
    for child in group.children.all():
        _clone_condition_group(child, branch_clone, group_clone, variable_map)


common_exclude = ["created_at", "updated_at"]
auditlog.register(Workflow, exclude_fields=common_exclude)
auditlog.register(WorkflowVersion, exclude_fields=common_exclude)
auditlog.register(WorkflowNode, exclude_fields=common_exclude)
auditlog.register(WorkflowEdge, exclude_fields=common_exclude)
auditlog.register(WorkflowVariable, exclude_fields=common_exclude)
auditlog.register(ConditionBranch, exclude_fields=common_exclude)
auditlog.register(ConditionGroup, exclude_fields=common_exclude)
auditlog.register(Condition, exclude_fields=common_exclude)
auditlog.register(WorkflowInstance, exclude_fields=common_exclude)
# secret/hmac_secret excluded so LogEntry diffs never leak credentials.
auditlog.register(
    WorkflowTrigger,
    exclude_fields=common_exclude
    + [
        "secret",
        "hmac_secret",
        "next_run_at",
        "last_run_at",
        "last_triggered_at",
        "last_result",
        "trigger_count",
    ],
)
# value excluded so create/update/delete are audited without leaking the secret.
auditlog.register(WorkflowSecret, exclude_fields=common_exclude + ["value"])
