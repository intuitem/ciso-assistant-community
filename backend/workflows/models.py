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


class Workflow(NameDescriptionFolderMixin, FilteringLabelMixin):
    ref_id = models.CharField(max_length=100, blank=True)
    webhook_secret = models.CharField(
        max_length=64, default=generate_webhook_secret, unique=True
    )
    # When set, inbound hooks must carry a valid HMAC-SHA256 signature of the
    # raw body (X-Hub-Signature-256 / X-Signature-256, optional sha256= prefix).
    webhook_hmac_secret = models.CharField(max_length=128, blank=True)

    fields_to_check = ["name"]

    def save(self, *args, **kwargs):
        # On folder move, propagate to versions and their children — they only
        # inherit folder at create-time, so IAM scoping would drift.
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
            self.versions.update(folder=self.folder)
            WorkflowNode.objects.filter(version__workflow=self).update(
                folder=self.folder
            )
            WorkflowEdge.objects.filter(version__workflow=self).update(
                folder=self.folder
            )
            WorkflowVariable.objects.filter(version__workflow=self).update(
                folder=self.folder
            )
            ConditionGroup.objects.filter(edge__version__workflow=self).update(
                folder=self.folder
            )
            Condition.objects.filter(group__edge__version__workflow=self).update(
                folder=self.folder
            )
            NodeAssignment.objects.filter(node__version__workflow=self).update(
                folder=self.folder
            )
            NodePresentation.objects.filter(node__version__workflow=self).update(
                folder=self.folder
            )

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
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    published_at = models.DateTimeField(null=True, blank=True)

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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow.name} v{self.version_number}"

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT

    def publish(self):
        """Publish this draft and archive the previously published version.

        Graph validity must be checked by the caller (see workflows.validation)
        before calling this.
        """
        WorkflowVersion.objects.filter(
            workflow=self.workflow, status=self.Status.PUBLISHED
        ).update(status=self.Status.ARCHIVED)
        self.status = self.Status.PUBLISHED
        self.published_at = timezone.now()
        self.save()

    def clone_as_draft(self):
        """Clone this version's whole graph into a new draft (spec D6)."""
        from django.db import transaction

        with transaction.atomic():
            last_number = (
                self.workflow.versions.order_by("-version_number")
                .values_list("version_number", flat=True)
                .first()
            )
            draft = WorkflowVersion.objects.create(
                workflow=self.workflow,
                version_number=(last_number or 0) + 1,
            )
            variable_map = {
                variable.id: _clone_row(variable, version=draft)
                for variable in self.variables.all()
            }
            node_map = {}
            for node in self.nodes.all():
                clone = _clone_row(node, version=draft)
                node_map[node.id] = clone
                for assignment in node.assignments.all():
                    _clone_row(assignment, node=clone)
                if hasattr(node, "presentation"):
                    _clone_row(node.presentation, node=clone)
            for edge in self.edges.all():
                edge_clone = _clone_row(
                    edge,
                    version=draft,
                    source_node=node_map[edge.source_node_id],
                    target_node=node_map[edge.target_node_id],
                )
                for group in edge.condition_groups.filter(parent_group=None):
                    _clone_condition_group(group, edge_clone, None, variable_map)
            return draft


class WorkflowNode(AbstractBaseModel, FolderMixin):
    class Type(models.TextChoices):
        START = "start", "Start"
        END = "end", "End"
        TASK = "task", "Task"
        CONDITION = "condition", "Condition"
        ACTION = "action", "Action"
        SUBPROCESS = "subprocess", "Subprocess"
        EVENT = "event", "Event"

    class ForkType(models.TextChoices):
        EXCLUSIVE = "exclusive", "Exclusive"
        PARALLEL = "parallel", "Parallel"

    class JoinType(models.TextChoices):
        NONE = "none", "None"
        AND = "and", "AND"
        OR = "or", "OR"

    class RetryBackoff(models.TextChoices):
        FIXED = "fixed", "Fixed"
        EXPONENTIAL = "exponential", "Exponential"

    version = models.ForeignKey(
        WorkflowVersion,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    type = models.CharField(max_length=20, choices=Type.choices)
    fork_type = models.CharField(
        max_length=20,
        choices=ForkType.choices,
        default=ForkType.EXCLUSIVE,
    )
    join_type = models.CharField(
        max_length=20,
        choices=JoinType.choices,
        default=JoinType.NONE,
    )
    label = models.CharField(max_length=200, blank=True)
    task_template = models.ForeignKey(
        "core.TaskTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workflow_nodes",
    )
    action_config = models.JSONField(default=dict, blank=True)
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
        super().save(*args, **kwargs)

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
    label = models.CharField(max_length=200, blank=True)
    priority = models.IntegerField(default=0)

    class Meta:
        ordering = ["priority", "created_at"]

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


class ConditionGroup(AbstractBaseModel, FolderMixin):
    class Operator(models.TextChoices):
        AND = "and", "AND"
        OR = "or", "OR"
        NOT = "not", "NOT"

    edge = models.ForeignKey(
        WorkflowEdge,
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
        self.folder = self.edge.folder
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


class NodeAssignment(AbstractBaseModel, FolderMixin):
    class ResolveType(models.TextChoices):
        ACTOR = "actor", "Actor"
        VARIABLE = "variable", "Variable"

    class Participation(models.TextChoices):
        TASK = "task", "Task"
        NOTIFICATION = "notification", "Notification"

    node = models.ForeignKey(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    role = models.ForeignKey(
        "pmbok.ResponsibilityRole",
        on_delete=models.PROTECT,
        related_name="workflow_assignments",
    )
    resolve_type = models.CharField(
        max_length=20,
        choices=ResolveType.choices,
        default=ResolveType.ACTOR,
    )
    actor = models.ForeignKey(
        "core.Actor",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="workflow_assignments",
    )
    variable_key = models.CharField(max_length=100, blank=True)
    is_blocking = models.BooleanField(default=True)
    participation = models.CharField(
        max_length=20,
        choices=Participation.choices,
        default=Participation.TASK,
    )

    def save(self, *args, **kwargs):
        self.folder = self.node.folder
        super().save(*args, **kwargs)


class NodePresentation(AbstractBaseModel, FolderMixin):
    class Type(models.TextChoices):
        REDIRECT = "redirect", "Redirect"
        EXTERNAL_URL = "external_url", "External URL"

    node = models.OneToOneField(
        WorkflowNode,
        on_delete=models.CASCADE,
        related_name="presentation",
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.REDIRECT,
    )
    redirect_path = models.CharField(max_length=500, blank=True)
    redirect_params = models.JSONField(default=dict, blank=True)
    completion_cta = models.CharField(max_length=200, blank=True)
    instructions = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.folder = self.node.folder
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
        "workflows.WorkflowToken",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subprocess_instances",
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.folder_id:
            self.folder = self.version.folder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.workflow.name} run {str(self.id)[:8]}"


class WorkflowToken(AbstractBaseModel, FolderMixin):
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
        JOIN_ARRIVAL = "join_arrival", "Join arrival"
        JOIN_FIRED = "join_fired", "Join fired"
        SUBPROCESS_STARTED = "subprocess_started", "Subprocess started"
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
    """Encrypted named credential for http_request, referenced as
    {{secrets.NAME}}. Values are write-only: the API never returns them and
    the engine resolves them only at execution time (spec D17)."""

    name = models.CharField(max_length=100)
    encrypted_value = models.BinaryField()

    fields_to_check = ["name"]

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["folder", "name"],
                name="unique_workflow_secret_name",
            )
        ]

    def set_value(self, value: str):
        from .crypto import encrypt_secret

        self.encrypted_value = encrypt_secret(value)

    def get_value(self) -> str:
        from .crypto import decrypt_secret

        return decrypt_secret(bytes(self.encrypted_value))

    def __str__(self):
        return self.name


def _clone_row(instance, **overrides):
    data = {
        field.name: getattr(instance, field.name)
        for field in instance._meta.concrete_fields
        if field.name not in ("id", "created_at", "updated_at")
    }
    data.update(overrides)
    return type(instance).objects.create(**data)


def _clone_condition_group(group, edge_clone, parent_clone, variable_map):
    group_clone = _clone_row(group, edge=edge_clone, parent_group=parent_clone)
    for condition in group.conditions.all():
        _clone_row(
            condition,
            group=group_clone,
            variable=variable_map[condition.variable_id],
        )
    for child in group.children.all():
        _clone_condition_group(child, edge_clone, group_clone, variable_map)


common_exclude = ["created_at", "updated_at"]
auditlog.register(Workflow, exclude_fields=common_exclude)
auditlog.register(WorkflowVersion, exclude_fields=common_exclude)
auditlog.register(WorkflowNode, exclude_fields=common_exclude)
auditlog.register(WorkflowEdge, exclude_fields=common_exclude)
auditlog.register(WorkflowVariable, exclude_fields=common_exclude)
auditlog.register(ConditionGroup, exclude_fields=common_exclude)
auditlog.register(Condition, exclude_fields=common_exclude)
auditlog.register(NodeAssignment, exclude_fields=common_exclude)
auditlog.register(NodePresentation, exclude_fields=common_exclude)
auditlog.register(WorkflowInstance, exclude_fields=common_exclude)
