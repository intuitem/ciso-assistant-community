"""Automation demo builder: workflows from the shipped catalogue plus a few
authored for the story, a short run history, and a Kubernetes CIS posture
assessment with nightly scan results.

Workflows are instantiated the way the library page does it
(``import_workflow`` on a workflow document, into a demo folder), never by
loading the workflow libraries: a load imports every workflow into the root
folder. Only samples without secrets or webhooks are used; the authored ones
follow the same document format and only use internal actions.

Publishing goes through ``WorkflowVersion.publish``, which syncs the trigger
rows; schedule and event triggers arrive disabled, so nothing fires. There is
no user to publish as, so ``published_by`` / ``run_as`` stay empty, as after
the publisher's account is deleted.

Runs are historical records only: ``WorkflowInstance`` and its log rows are
written directly, nothing is executed and no ``WorkflowToken`` is created.
"""

import uuid
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import ClassVar

import yaml
from django.conf import settings

from automation.models import PostureAssessment, PostureResult, PostureRun
from automation.workflows.import_export import import_workflow
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowInstanceLog,
    WorkflowTrigger,
    WorkflowVersion,
)
from automation.workflows.validation import validate_graph
from core.demo import DemoBuilder, register
from core.models import Asset, Framework, RequirementNode

K8S_LIBRARY = "urn:intuitem:risk:library:cis-benchmark-kubernetes"

# Library file stem, lifecycle, publish offset.
# lifecycle: "draft" (never published), "published", "republished" (v1
# archived, v2 published) or "paused" (published, then switched off).
WORKFLOWS = [
    ("workflow-compliance-audit-progress-digest", "published", -60),
    ("workflow-risk-exception-expiry", "paused", -120),
    ("workflow-compliance-audit-closed", "draft", None),
]

DIGEST = "workflow-compliance-audit-progress-digest"
NOTIFY = "grc@example.com"
# Day offsets of past digest runs; the one listed in FAILED_RUNS hit an
# unconfigured mail server.
RUN_OFFSETS = (-28, -21, -14, -7)
FAILED_RUNS = (-21,)
SMTP_ERROR = "send_email: email is not configured (missing EMAIL_HOST)"


def edges(*pairs):
    return [
        {"source": source, "target": target, **({"source_port": port} if port else {})}
        for source, target, port in pairs
    ]


# Authored workflows, in the shipped document format: (document,
# lifecycle, publish offset).
PSIRT = "psirt@example.com"
CRA_TRIAGE = {
    "schema_version": 1,
    "ref_id": "cra-vulnerability-triage",
    "name": "CRA vulnerability triage — PSIRT intake",
    "description": (
        "A firmware or app vulnerability recorded at high severity or above opens "
        "the fix as an applied control, links it to the vulnerability and alerts "
        "the PSIRT with the CRA early-warning deadline. Report received, triage, "
        "fix through the staged OTA rollout, then the security advisory."
    ),
    "graph": {
        "variables": [
            {"key": "psirt_emails", "type": "string", "default_value": PSIRT},
            {"key": "warning_due", "type": "string"},
        ],
        "nodes": [
            {
                "ref": "on_report",
                "type": "trigger",
                "label": "High-severity report recorded",
                "trigger_config": {
                    "type": "internal_event",
                    "event_key": "vulnerability.created",
                    "filters": {
                        "operator": "and",
                        "conditions": [{"field": "severity", "op": "gte", "value": 3}],
                    },
                },
            },
            {
                "ref": "open_fix",
                "type": "action",
                "label": "Open the fix",
                "action_config": {
                    "type": "create_object",
                    "model": "applied_control",
                    "fields": {
                        "name": "PSIRT fix: {{payload.object_repr}}",
                        "description": (
                            "Opened automatically on {{today}}. Confirm in PSIRT "
                            "triage, ship the fixed firmware through the staged "
                            "OTA rollout, then publish the security advisory."
                        ),
                    },
                },
            },
            {
                "ref": "link_fix",
                "type": "action",
                "label": "Link it to the vulnerability",
                "action_config": {
                    "type": "update_object",
                    "model": "vulnerability",
                    "id": "{{payload.object_id}}",
                    "m2m": {
                        "applied_controls": {
                            "op": "add",
                            "values": "{{nodes.open_fix.created_object_id}}",
                        }
                    },
                },
            },
            {
                "ref": "early_warning",
                "type": "action",
                "label": "CRA early warning, 24 hours",
                "action_config": {
                    "type": "date_offset",
                    "days": 1,
                    "output": "warning_due",
                },
            },
            {
                "ref": "alert_psirt",
                "type": "action",
                "label": "Alert the PSIRT",
                "action_config": {
                    "type": "send_email",
                    "recipients": "{{psirt_emails}}",
                    "subject": "PSIRT triage: {{payload.object_repr}}",
                    "body": (
                        "{{payload.object_repr}} was recorded on {{today}}. "
                        "{{nodes.open_fix.created_object_name}} is open. If the "
                        "vulnerability is actively exploited, the CRA early warning "
                        "is due by {{warning_due}}."
                    ),
                },
            },
            {"ref": "done", "type": "end"},
        ],
        "edges": edges(
            ("on_report", "open_fix", None),
            ("open_fix", "link_fix", None),
            ("link_fix", "early_warning", None),
            ("early_warning", "alert_psirt", None),
            ("alert_psirt", "done", None),
        ),
    },
}
SUPPLIER_RENEWAL = {
    "schema_version": 1,
    "ref_id": "supplier-reassessment-on-renewal",
    "name": "Contract renewal — supplier reassessment",
    "description": (
        "When a supplier contract gets a new end date, procurement and TPRM are "
        "asked to refresh the supplier's security assessment within 30 days, "
        "before the renewal is signed."
    ),
    "graph": {
        "variables": [
            {
                "key": "procurement_emails",
                "type": "string",
                "default_value": "procurement@example.com",
            },
            {"key": "reassess_by", "type": "string"},
        ],
        "nodes": [
            {
                "ref": "on_renewal",
                "type": "trigger",
                "label": "Contract end date changed",
                "trigger_config": {
                    "type": "internal_event",
                    "event_key": "contract.updated",
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {
                                "field": "end_date",
                                "op": "neq",
                                "value": "",
                                "changed": True,
                            }
                        ],
                    },
                },
            },
            {
                "ref": "deadline",
                "type": "action",
                "label": "Thirty days to reassess",
                "action_config": {
                    "type": "date_offset",
                    "days": 30,
                    "output": "reassess_by",
                },
            },
            {
                "ref": "ask_procurement",
                "type": "action",
                "label": "Ask for the reassessment",
                "action_config": {
                    "type": "send_email",
                    "recipients": "{{procurement_emails}}",
                    "subject": "Renewal: reassess {{payload.object_repr}}",
                    "body": (
                        "{{payload.object_repr}} was renewed on {{today}}. Refresh "
                        "the supplier security questionnaire and its assessment by "
                        "{{reassess_by}}, before signature."
                    ),
                },
            },
            {"ref": "done", "type": "end"},
        ],
        "edges": edges(
            ("on_renewal", "deadline", None),
            ("deadline", "ask_procurement", None),
            ("ask_procurement", "done", None),
        ),
    },
}
AUTHORED = [
    (CRA_TRIAGE, "republished", -150),
    (SUPPLIER_RENEWAL, "published", -70),
]

# Past PSIRT intake runs: day offset, vulnerability reported.
TRIAGE_RUNS = [
    (-62, "Keystone hub: Thread commissioning buffer overflow"),
    (-33, "Lookout camera: RTSP stream reachable without authentication"),
    (-9, "Companion app: session token written to debug logs"),
]

# Asset name, managed control plane, description, parent primary asset.
CLUSTERS = [
    ("Device cloud Kubernetes cluster", True, None, None),
    (
        "Device cloud staging cluster",
        True,
        (
            "Managed cluster on Kestrava Cloud mirroring the device cloud, where "
            "firmware releases and OTA campaigns are rehearsed."
        ),
        "Customer and device accounts",
    ),
    (
        "Online store Kubernetes cluster",
        True,
        (
            "Managed cluster on Kestrava Cloud running the store front and the order "
            "API; the card flow stays in the segmented checkout environment."
        ),
        "Order fulfilment",
    ),
    (
        "Brno plant edge K3s cluster",
        False,
        (
            "Self-managed K3s nodes in the Brno plant DMZ hosting the MES and the "
            "line dashboards."
        ),
        "Production line control",
    ),
]

# Top-level benchmark section -> (actual, expected) shown on failed checks.
FAIL_DETAILS = {
    "1": ("--anonymous-auth=true", "--anonymous-auth=false"),
    "2": ("--client-cert-auth not set", "--client-cert-auth=true"),
    "3": ("no audit policy file", "--audit-policy-file configured"),
    "4": ("file mode 0644", "file mode 0600 or stricter"),
    "5": ("3 non-compliant workloads", "0 non-compliant workloads"),
}
SCAN_DAYS = 10
SCAN_TOOL = "kube-bench 0.9.2"


def at(ctx, offset, hour=8, minute=0):
    return datetime.combine(ctx.day(offset), time(hour, minute), tzinfo=UTC)


def load_document(stem):
    path = Path(settings.LIBRARIES_PATH) / f"{stem}.yaml"
    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    return document, document["objects"]["workflows"][0]


@register
class AutomationBuilder(DemoBuilder):
    """Shipped and authored workflows in several lifecycle states, a short
    run history, and a Kubernetes posture assessment."""

    name = "automation"
    feature_flags = ("workflows", "posture_assessments")
    depends = ("core", "compliance")
    libraries = (K8S_LIBRARY,)
    covers: ClassVar[dict] = {
        Workflow: "folder",
        WorkflowVersion: "folder",
        WorkflowTrigger: "folder",
        WorkflowInstance: "folder",
        PostureAssessment: "folder",
    }

    def stamps(self, ctx):
        # WorkflowInstance is not stamped: build() dates each run on its own
        # day, which is what the run history lists.
        folders = ctx.folders()
        return [
            (Workflow, {"folder__in": folders}, ("name",)),
            (
                WorkflowVersion,
                {"folder__in": folders},
                ("workflow__name", "version_number"),
            ),
            (WorkflowTrigger, {"folder__in": folders}, ("workflow__name", "node_ref")),
            (PostureAssessment, {"folder": ctx.domain}, ("name",)),
        ]

    def build(self, ctx):
        for stem, lifecycle, offset in WORKFLOWS:
            document, entry = load_document(stem)
            workflow = self.build_workflow(
                ctx,
                ctx.domain,
                entry,
                document.get("version"),
                lifecycle,
                offset,
            )
            if workflow is not None and stem == DIGEST:
                self.build_runs(ctx, workflow)
        for entry, lifecycle, offset in AUTHORED:
            workflow = self.build_workflow(
                ctx, ctx.domain, entry, 1, lifecycle, offset, strict=True
            )
            if workflow is not None and entry is CRA_TRIAGE:
                self.build_triage_runs(ctx, workflow)
        self.build_posture(ctx)

    # Workflows

    def build_workflow(
        self, ctx, folder, entry, version, lifecycle, offset, strict=False
    ):
        if Workflow.objects.filter(name=entry["name"], folder=folder).exists():
            return None
        workflow, warnings = import_workflow(entry, folder, source_version=version)
        if strict and warnings:
            ctx.err(f"{entry['name']}: import warnings: {warnings}")
        if lifecycle == "draft":
            return workflow
        draft = workflow.draft_version
        if not self.publish(ctx, draft, offset):
            return workflow
        if lifecycle == "republished":
            draft = draft.clone_as_draft()
            self.publish(ctx, draft, offset + 60)
        if lifecycle == "paused":
            workflow.is_active = False
            workflow.save()
        return workflow

    def publish(self, ctx, version, offset):
        # Same gate as the publish endpoint.
        errors = validate_graph(version)
        if errors:
            ctx.err(f"{version}: not publishable: {errors}")
            return False
        version.publish(None)
        # publish() stamps now(); pin it to the story's date.
        WorkflowVersion.objects.filter(pk=version.pk).update(
            published_at=at(ctx, offset, 10)
        )
        return True

    def record_run(self, ctx, workflow, version, key, offset, failed, fields, log):
        """Write one historical run and its log, dated on the run's day."""
        nodes = {node.ref: node for node in version.nodes.all()}
        instance = WorkflowInstance.objects.create(
            # A run's name embeds its id, so a random one would make every
            # rebuild list different runs. Derived from the domain name,
            # it stays unique across demo domains.
            id=uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"demo:{ctx.domain.name}:{workflow.name}:run:{key}",
            ),
            workflow=workflow,
            version=version,
            # FolderMixin defaults to the root folder, so save() would
            # never fall back to the version's.
            folder=version.folder,
            status=WorkflowInstance.Status.FAILED
            if failed
            else WorkflowInstance.Status.COMPLETED,
            trigger_depth=1,
            **fields,
        )
        entries = [
            WorkflowInstanceLog.objects.create(
                instance=instance,
                node=nodes.get(ref),
                event_type=event_type,
                message=message,
                data=data,
            ).pk
            for event_type, ref, message, data in log
        ]
        started = at(ctx, offset)
        WorkflowInstance.objects.filter(pk=instance.pk).update(
            created_at=started,
            updated_at=started + timedelta(seconds=len(log)),
        )
        for step, pk in enumerate(entries):
            stamp = started + timedelta(seconds=step)
            WorkflowInstanceLog.objects.filter(pk=pk).update(
                created_at=stamp, updated_at=stamp
            )

    def build_runs(self, ctx, workflow):
        version = workflow.published_version
        if version is None:
            return
        audits = [
            audit
            for audit in ctx.refs.get("audits", [])
            if audit.status == "in_progress"
        ]
        rows = [
            {
                "ref_id": audit.ref_id,
                "name": audit.name,
                "status": audit.status,
                "due_date": audit.due_date.isoformat() if audit.due_date else None,
            }
            for audit in audits
        ]
        fetched = {"count": len(rows), "offset": 0, "next_offset": 0, "results": rows}
        looped = {
            "count": len(rows),
            "results": [row["name"] for row in rows],
            "errors": [],
            "pages": 0,
            "stopped": None,
        }
        subject = f"Audits in progress: {len(rows)}"
        for offset in RUN_OFFSETS:
            failed = offset in FAILED_RUNS
            outputs = {"fetch_audits": fetched, "per_audit": looped}
            if rows:
                outputs["note_audit"] = {
                    "message": f"{rows[-1]['name']} · due {rows[-1]['due_date']}"
                }
            log = [
                (
                    "instance_started",
                    "every_monday",
                    "Triggered by manual",
                    {"variables": {"notify_emails": NOTIFY}},
                ),
                ("node_entered", "fetch_audits", "", {}),
                ("action_executed", "fetch_audits", "read_objects", fetched),
                ("node_entered", "per_audit", "", {}),
            ]
            for row in rows:
                message = f"{row['name']} · due {row['due_date']}"
                log += [
                    ("node_entered", "note_audit", "", {}),
                    ("action_executed", "note_audit", "log", {"message": message}),
                ]
            log += [
                (
                    "loop_completed",
                    "per_audit",
                    f"processed {len(rows)} items",
                    looped,
                ),
                ("node_entered", "send_digest", "", {}),
            ]
            if failed:
                log.append(("error", "send_digest", SMTP_ERROR, {}))
            else:
                log += [
                    (
                        "action_executed",
                        "send_digest",
                        "send_email",
                        {"recipients": [NOTIFY], "subject": subject},
                    ),
                    ("node_entered", "done", "", {}),
                    ("instance_completed", None, "", {}),
                ]
            self.record_run(
                ctx,
                workflow,
                version,
                offset,
                offset,
                failed,
                {
                    "trigger": WorkflowInstance.Trigger.MANUAL,
                    "variables": {"notify_emails": NOTIFY},
                    "node_outputs": outputs,
                },
                log,
            )

    def build_triage_runs(self, ctx, workflow):
        version = workflow.published_version
        if version is None:
            return
        for offset, report in TRIAGE_RUNS:
            key = f"triage:{offset}"
            vulnerability_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"demo:{ctx.domain.name}:{key}:vuln")
            )
            control_id = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"demo:{ctx.domain.name}:{key}:fix")
            )
            today = ctx.day(offset).isoformat()
            due = ctx.day(offset + 1).isoformat()
            fix = f"PSIRT fix: {report}"
            payload = {
                "operation": "created",
                "object_id": vulnerability_id,
                "object_repr": report,
            }
            variables = {"psirt_emails": PSIRT, "warning_due": due}
            outputs = {
                "open_fix": {
                    "created_object_id": control_id,
                    "created_object_name": fix,
                    "created_object_model": "applied_control",
                    "created": True,
                },
                "link_fix": {"updated_object_id": vulnerability_id},
                "early_warning": {"result": due, "base": today},
                "alert_psirt": {
                    "recipients": [PSIRT],
                    "subject": f"PSIRT triage: {report}",
                },
            }
            log = [
                (
                    "instance_started",
                    "on_report",
                    "Triggered by internal_event",
                    {"event_key": "vulnerability.created"},
                ),
            ]
            for ref, action in (
                ("open_fix", "create_object"),
                ("link_fix", "update_object"),
                ("early_warning", "date_offset"),
                ("alert_psirt", "send_email"),
            ):
                log += [
                    ("node_entered", ref, "", {}),
                    ("action_executed", ref, action, outputs[ref]),
                ]
            log += [
                ("node_entered", "done", "", {}),
                ("instance_completed", None, "", {}),
            ]
            self.record_run(
                ctx,
                workflow,
                version,
                key,
                offset,
                False,
                {
                    "trigger": WorkflowInstance.Trigger.INTERNAL_EVENT,
                    "variables": variables,
                    "payload": payload,
                    "node_outputs": outputs,
                },
                log,
            )

    # Posture

    def build_posture(self, ctx):
        framework = Framework.objects.filter(library__urn=K8S_LIBRARY).first()
        if framework is None:
            ctx.err("CIS Kubernetes benchmark not loaded, skipping posture")
            return
        assets = self.cluster_assets(ctx)
        perimeter = ctx.refs["perimeters"][0] if ctx.refs.get("perimeters") else None
        fleet, created = PostureAssessment.objects.get_or_create(
            name="Kubernetes CIS benchmark — cluster fleet",
            folder=ctx.domain,
            defaults={
                "ref_id": "PA.K8S.01",
                "framework": framework,
                "selected_implementation_groups": ["A"],
                "history_depth": SCAN_DAYS,
                "status": "in_progress",
                "perimeter": perimeter,
                "due_date": ctx.day(90),
                "description": "Nightly kube-bench scans of the device cloud, "
                "online store and Brno plant clusters, automated checks only. "
                "Clusters managed by Kestrava Cloud report the control plane "
                "sections as not applicable.",
            },
        )
        if created:
            fleet.assets.set([asset for asset, _ in assets])
            self.build_scans(ctx, fleet, assets)
        planned, created = PostureAssessment.objects.get_or_create(
            name="Kubernetes CIS benchmark — manual checks review",
            folder=ctx.domain,
            defaults={
                "ref_id": "PA.K8S.02",
                "framework": framework,
                "selected_implementation_groups": ["M"],
                "status": "planned",
                "perimeter": perimeter,
                "due_date": ctx.day(150),
                "description": "Manual benchmark items reviewed once a year with "
                "the device cloud platform team.",
            },
        )
        if created:
            planned.assets.set([asset for asset, managed in assets if managed])

    def cluster_assets(self, ctx):
        assets = []
        for name, managed, description, parent in CLUSTERS:
            asset = Asset.objects.filter(folder=ctx.domain, name=name).first()
            if asset is None:
                asset = Asset.objects.create(
                    name=name,
                    folder=ctx.domain,
                    description=description or "",
                    type=Asset.Type.SUPPORT,
                )
                primary = Asset.objects.filter(folder=ctx.domain, name=parent).first()
                if primary:
                    asset.parent_assets.set([primary])
            assets.append((asset, managed))
        return assets

    def build_scans(self, ctx, assessment, assets):
        checks = list(
            RequirementNode.objects.filter(
                framework=assessment.framework, assessable=True
            )
            .exclude(ref_id="")
            .order_by("urn")
        )
        checks = [
            check
            for check in checks
            if assessment.requirement_matches_selected_groups(
                check.implementation_groups
            )
        ]
        # A few checks that keep failing on some clusters, so the trend has a
        # residue and the follow-up is meaningful.
        worker_checks = [c for c in checks if c.ref_id.split(".")[0] in ("4", "5")]
        persistent = {
            (check.urn, asset.name)
            for check in ctx.rng.sample(worker_checks, min(4, len(worker_checks)))
            for asset, _ in ctx.rng.sample(assets, 2)
        }
        runs, results = [], []
        for day in range(SCAN_DAYS):
            offset = day - SCAN_DAYS + 1
            pass_rate = 0.62 + 0.3 * day / max(SCAN_DAYS - 1, 1)
            for index, (asset, managed) in enumerate(assets):
                stamp = at(ctx, offset, 2, 10 * index)
                run = PostureRun(
                    posture_assessment=assessment, started_at=stamp, tool=SCAN_TOOL
                )
                runs.append(run)
                for check in checks:
                    section = check.ref_id.split(".")[0]
                    if managed and section in ("1", "2", "3"):
                        result = PostureResult.Result.NOT_APPLICABLE
                    elif (check.urn, asset.name) in persistent:
                        result = PostureResult.Result.FAILED
                    else:
                        roll = ctx.rng.random()
                        if roll < pass_rate:
                            result = PostureResult.Result.PASSED
                        elif roll < pass_rate + 0.02:
                            result = PostureResult.Result.ERROR
                        elif roll < pass_rate + 0.04:
                            result = PostureResult.Result.NOT_CHECKED
                        else:
                            result = PostureResult.Result.FAILED
                    actual, expected = (
                        FAIL_DETAILS.get(section, ("", ""))
                        if result == PostureResult.Result.FAILED
                        else ("", "")
                    )
                    results.append(
                        PostureResult(
                            run=run,
                            requirement=check,
                            asset=asset,
                            result=result,
                            timestamp=stamp,
                            actual=actual,
                            expected=expected,
                            message="check timed out after 30s"
                            if result == PostureResult.Result.ERROR
                            else "",
                            source=PostureResult.Source.IMPORT,
                        )
                    )
        PostureRun.objects.bulk_create(runs, batch_size=1000)
        PostureResult.objects.bulk_create(results, batch_size=2000)
        ctx.out(f"posture seeded with {len(runs)} runs, {len(results)} results")
