"""Trigger registration lifecycle.

Trigger nodes carry the definition in the immutable graph; WorkflowTrigger
rows carry the operational state. Publishing a version syncs the rows from
the version's trigger nodes, keyed by node ref: existing rows keep their
enabled flag, webhook secret and bookkeeping ("sticky enable"); new schedule
and internal-event rows arrive disabled so publishing never starts a cron or
an event storm by surprise; webhook rows arrive enabled (they are pull —
someone must call the URL). A ref rename or subtype change is a delete +
create: state resets and webhook URLs rotate.
"""

from django.utils import timezone

from .models import WorkflowNode, WorkflowTrigger, generate_webhook_secret

REGISTERED_TYPES = set(WorkflowTrigger.Type.values)


def sync_trigger_registrations(version):
    """Reconcile the workflow's registration rows with a freshly published
    version. Runs inside the publish transaction."""
    workflow = version.workflow
    desired = {}
    for node in version.nodes.filter(type=WorkflowNode.Type.TRIGGER):
        config = node.trigger_config or {}
        if config.get("type") in REGISTERED_TYPES:
            desired[node.ref] = config

    workflow.triggers.exclude(node_ref__in=desired.keys()).delete()
    existing = {t.node_ref: t for t in workflow.triggers.all()}
    now = timezone.now()

    for ref, config in desired.items():
        trigger_type = config["type"]
        row = existing.get(ref)
        if row is None:
            row = WorkflowTrigger(
                workflow=workflow,
                node_ref=ref,
                type=trigger_type,
                enabled=trigger_type == WorkflowTrigger.Type.WEBHOOK,
            )
        elif row.type != trigger_type:
            # Same ref, different subtype: a different trigger altogether.
            row.type = trigger_type
            row.enabled = trigger_type == WorkflowTrigger.Type.WEBHOOK
            row.secret = generate_webhook_secret()
            row.hmac_secret = ""
            row.next_run_at = None
            row.last_run_at = None
            row.last_triggered_at = None
            row.last_result = ""
            row.trigger_count = 0

        config_changed = row.config != config
        row.config = config
        row.event_key = (
            config.get("event_key", "")
            if trigger_type == WorkflowTrigger.Type.INTERNAL_EVENT
            else ""
        )
        if trigger_type == WorkflowTrigger.Type.SCHEDULE:
            if not row.enabled:
                row.next_run_at = None
            elif config_changed or row.next_run_at is None:
                from .scheduling import next_occurrence

                row.next_run_at = next_occurrence(
                    config.get("cron_expression", ""),
                    config.get("timezone", "UTC"),
                    now,
                )
        else:
            row.next_run_at = None
        row.save()


def validate_trigger_config(node, workflow=None):
    """Publish-time validation of a trigger node's config. Returns a list of
    (code, message) tuples anchored to the node by the caller."""
    from .events import event_key_catalog, validate_filter_tree, _workflow_scope
    from .scheduling import (
        CronValidationError,
        validate_cron_expression,
        validate_timezone,
    )

    errors = []
    config = node.trigger_config or {}
    trigger_type = config.get("type")
    if trigger_type not in set(WorkflowNode.TriggerType.values):
        errors.append(
            ("trigger_type_invalid", "Trigger nodes need a valid trigger type")
        )
        return errors

    if trigger_type == WorkflowNode.TriggerType.SCHEDULE:
        tz_name = config.get("timezone", "UTC")
        try:
            validate_timezone(tz_name)
        except CronValidationError as e:
            errors.append(("trigger_invalid_timezone", str(e)))
            tz_name = "UTC"
        try:
            validate_cron_expression(config.get("cron_expression", ""), tz_name)
        except CronValidationError as e:
            errors.append(("trigger_invalid_cron", str(e)))

    if trigger_type == WorkflowNode.TriggerType.INTERNAL_EVENT:
        event_key = config.get("event_key", "")
        if event_key not in {entry["key"] for entry in event_key_catalog()}:
            errors.append(
                ("trigger_invalid_event_key", "This trigger needs a valid event")
            )
        filters = config.get("filters") or {}
        try:
            validate_filter_tree(filters)
        except ValueError:
            errors.append(("trigger_invalid_filters", "The event filters are invalid"))
        else:
            if workflow is not None and filters:
                scope = _workflow_scope(workflow)
                if _has_out_of_scope_folder(filters, scope):
                    errors.append(
                        (
                            "trigger_filters_out_of_scope",
                            "A folder filter points outside this workflow's scope",
                        )
                    )
    return errors


def _has_out_of_scope_folder(filters, scope):
    from .events import walk_conditions

    for condition in walk_conditions(filters):
        if condition.get("field") == "folder" and condition.get("op", "eq") in (
            "eq",
            "in",
        ):
            values = str(condition.get("value", "")).split(",")
            for folder_value in (v.strip() for v in values):
                if folder_value and folder_value not in scope:
                    return True
    return False
