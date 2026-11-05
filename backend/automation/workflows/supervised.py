"""Supervised actions: workflows a person runs against one object.

The reactive path decides for itself — an event fires, the rules read the answers,
something happens unattended. This is the other half: a reviewer who has read a
request presses a button and a named sequence runs on it. The decision is the
person's; the workflow is their hands.

A manual trigger declares what it applies to:

    trigger_config:
      type: manual
      applies_to:
        model: quick_form_response
        outcome: ciso_approval      # optional — offer it only when this fired

`outcome` is what makes the button a *suggestion* rather than a menu: the answers
select which sequences are worth offering, and the reviewer chooses.
"""

from .models import WorkflowNode, WorkflowVersion


def _requester_emails(obj) -> str:
    """Who to tell about a request, as `send_email` wants them: comma-separated.

    Same notion of "the asking side" as `QuickFormResponse.is_requester` — the
    submitter plus the respondents — so a notification cannot reach someone the
    request does not consider its owner. Team and entity actors have no address of
    their own and are skipped; a workflow that needs them should address a group.
    """
    emails = []
    if obj.submitted_by_id and obj.submitted_by.email:
        emails.append(obj.submitted_by.email)
    for actor in obj.respondents.select_related("user").all():
        email = getattr(actor.user, "email", "") if actor.user_id else ""
        if email:
            emails.append(email)
    seen = set()
    return ",".join(e for e in emails if not (e in seen or seen.add(e)))


#: Object kinds a supervised action may target. Keyed by the string an author
#: writes in `applies_to.model`; the value reads the object's outcome refs so a
#: trigger can be narrowed to the classifications it is meant for.
SUPERVISED_TARGETS = {
    "quick_form_response": {
        "label": "Quick form response",
        "outcomes": lambda obj: [
            ref for ref in (obj.outcome_refs or "").split(",") if ref
        ],
        #: Seeded into the run, but only for variables the workflow declares.
        "variables": lambda obj: {
            "request_id": str(obj.id),
            "request_ref": obj.ref_id or "",
            "outcomes": obj.outcome_refs or "",
            "requester_emails": _requester_emails(obj),
        },
    },
}


def _manual_entry_nodes(version):
    return [
        node
        for node in version.nodes.all()
        if node.type == WorkflowNode.Type.TRIGGER
        and (node.trigger_config or {}).get("type") == WorkflowNode.TriggerType.MANUAL
    ]


def suggested_actions(obj, model_key, folder_ids):
    """Published manual workflows offered for `obj`, newest first.

    Narrowed three ways: the trigger must name this object kind, the workflow must
    live in a folder the object is inside, and an `outcome` on the trigger must be
    one the object actually fired.
    """
    target = SUPERVISED_TARGETS.get(model_key)
    if target is None:
        return []
    fired = set(target["outcomes"](obj))
    versions = (
        WorkflowVersion.objects.filter(
            status=WorkflowVersion.Status.PUBLISHED,
            is_active=True,
            workflow__is_active=True,
            workflow__folder_id__in=folder_ids,
        )
        .select_related("workflow")
        .prefetch_related("nodes")
    )
    offered = []
    for version in versions:
        for node in _manual_entry_nodes(version):
            applies = (node.trigger_config or {}).get("applies_to") or {}
            if applies.get("model") != model_key:
                continue
            wanted = applies.get("outcome")
            if wanted and wanted not in fired:
                continue
            offered.append(
                {
                    "workflow": str(version.workflow_id),
                    "version": str(version.id),
                    "entry_node": str(node.id),
                    "name": version.workflow.name,
                    "description": version.workflow.description,
                    "label": node.label or version.workflow.name,
                    # Present when the button is offered because of an outcome,
                    # so the UI can say why it is being suggested.
                    "because": wanted or None,
                }
            )
    return offered


def run_supervised_action(obj, model_key, version, entry_node, user):
    """Start a manual run against `obj`. Seeds only the variables the workflow
    declares, so a sequence takes what it asked for and nothing else."""
    from .engine import trigger_instance

    target = SUPERVISED_TARGETS[model_key]
    declared = set(version.variables.values_list("key", flat=True))
    seeded = {k: v for k, v in target["variables"](obj).items() if k in declared}
    return trigger_instance(
        version,
        trigger="manual",
        initiated_by=user,
        entry_node=entry_node,
        initial_variables=seeded,
        payload={"model": model_key, "id": str(obj.id)},
    )
