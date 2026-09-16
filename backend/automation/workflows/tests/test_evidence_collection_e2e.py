"""End-to-end rehearsal of the collection pattern, against a real HTTP server.

A weekly task expects an evidence. A workflow finds that evidence, pulls this
week's export from a tool, files it as a new revision and records the number the
export reports. Then it runs again, as next week would.

Nothing here is mocked except the tool itself, which is a real socket serving
real bytes: `requests` runs, the SSRF guard runs, the file is streamed and
written through storage, and the engine walks the graph it would walk in
production. It is the check that the action reference describes what happens.
"""

import json
import threading
import uuid
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from django.test import override_settings

from core.models import Evidence, TaskTemplate
from iam.models import Folder
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user

EXPORT_CSV = b"host,agent\nlaptop-01,ok\nlaptop-02,ok\nserver-03,missing\n"
EXPORT_JSON = {"coverage_percent": 66.7, "hosts": 3, "covered": 2}


class ToolHandler(SimpleHTTPRequestHandler):
    """The 'something' the workflow reaches: a stand-in EDR that publishes a
    coverage summary and a downloadable export."""

    def do_GET(self):
        if self.path == "/coverage.json":
            body, kind = json.dumps(EXPORT_JSON).encode(), "application/json"
        elif self.path == "/export.csv":
            body, kind = EXPORT_CSV, "text/csv"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def tool():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(ToolHandler))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


def chain(version, nodes):
    save_graph(
        version,
        {
            "nodes": nodes,
            "edges": [edge(nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1)],
        },
    )


@pytest.fixture
def scene(db):
    """A domain, the evidence a weekly task expects, and the metric the export
    feeds."""
    domain = Folder.objects.create(
        name=f"Collection {uuid.uuid4().hex[:6]}",
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )
    evidence = Evidence.objects.create(
        name="EDR coverage export", folder=domain, status=Evidence.Status.APPROVED
    )
    task = TaskTemplate.objects.create(
        name="Collect the EDR coverage export",
        folder=domain,
        is_recurrent=True,
        task_date=date(2026, 9, 21),
        schedule={"interval": 1, "frequency": "WEEK"},
    )
    task.evidences.add(evidence)
    definition = MetricDefinition.objects.create(
        name="EDR coverage",
        urn=f"urn:test:risk:library:metrics:metric:edr-{uuid.uuid4().hex[:6]}",
        folder=Folder.get_root_folder(),
        category=MetricDefinition.Category.QUANTITATIVE,
    )
    metric = MetricInstance.objects.create(
        name="EDR coverage — fleet",
        folder=domain,
        metric_definition=definition,
        collection_frequency=MetricInstance.Frequency.WEEKLY,
    )
    return domain, evidence, task, metric


def collection_workflow(domain, metric, base_url, task_node=""):
    """find the evidence → (find the week) → pull the summary → file the export
    → record it."""
    workflow = Workflow.objects.create(name="Weekly EDR collection", folder=domain)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    find_the_week = node(
        "action",
        label="Find the week",
        action_config={
            "type": "read_objects",
            "model": "task_node",
            "mode": "first",
            "filters": {
                "operator": "and",
                "conditions": [{"field": "status", "op": "eq", "value": "pending"}],
            },
            "order_by": "due_date",
        },
    )
    chain(
        version,
        [
            node("trigger", label="Every Monday", trigger_config={"type": "manual"}),
            *([find_the_week] if task_node else []),
            node(
                "action",
                label="Find the evidence",
                action_config={
                    "type": "read_objects",
                    "model": "evidence",
                    "mode": "first",
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {
                                "field": "name",
                                "op": "eq",
                                "value": "EDR coverage export",
                            }
                        ],
                    },
                },
            ),
            node(
                "action",
                label="Pull the summary",
                action_config={
                    "type": "http_request",
                    "method": "GET",
                    "url": f"{base_url}/coverage.json",
                },
            ),
            node(
                "action",
                label="File the export",
                action_config={
                    "type": "attach_evidence",
                    "evidence": "{{nodes.find_the_evidence.object.id}}",
                    "source": "url",
                    "url": f"{base_url}/export.csv",
                    "filename": "edr-export-{{today}}.csv",
                    "new_revision": True,
                    "task_node": task_node,
                },
            ),
            node(
                "action",
                label="Record the coverage",
                action_config={
                    "type": "record_measurement",
                    "metric_instance": str(metric.id),
                    "value": "{{nodes.pull_the_summary.body.coverage_percent}}",
                    "evidence_revision": "{{nodes.file_the_export.revision_id}}",
                    "observation": "Pulled from the EDR export",
                },
            ),
            node("end"),
        ],
    )
    return version


@pytest.mark.django_db(transaction=True)
class TestWeeklyEvidenceCollection:
    def test_the_private_tool_is_refused_without_the_egress_setting(self, scene, tool):
        """The first thing anyone pointing a workflow at an internal tool hits:
        the SSRF guard blocks private addresses, and the escape hatch is an
        instance-wide setting, not a per-step one."""
        domain, _evidence, _task, metric = scene
        version = collection_workflow(domain, metric, tool)
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED

    @override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
    def test_two_weeks_of_collection(self, scene, tool):
        domain, evidence, task, metric = scene
        version = collection_workflow(domain, metric, tool)

        first = start_instance(version)
        assert first.status == WorkflowInstance.Status.COMPLETED, first.variables

        # Week one: the export is on the evidence and the number is on the metric.
        revision = evidence.revisions.order_by("-version").first()
        assert revision.version == 1
        assert revision.attachment.read() == EXPORT_CSV
        assert revision.filename().startswith("edr-export-")
        sample = CustomMetricSample.objects.get(metric_instance=metric)
        assert sample.value == {"result": 66.7}
        assert sample.evidence_revision_id == revision.id

        # The approved evidence went back for review: a new file is not a
        # reviewed file.
        evidence.refresh_from_db()
        assert evidence.status == Evidence.Status.IN_REVIEW

        second = start_instance(version)
        assert second.status == WorkflowInstance.Status.COMPLETED, second.variables

        # Week two: a second revision, the first one still readable.
        versions = sorted(evidence.revisions.values_list("version", flat=True))
        assert versions == [1, 2]
        assert evidence.revisions.get(version=1).attachment.read() == EXPORT_CSV
        assert CustomMetricSample.objects.filter(metric_instance=metric).count() == 2

        # What the task expects is what the workflow filed.
        assert list(task.evidences.all()) == [evidence]

    @override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
    def test_the_revision_is_not_tied_to_the_task_occurrence(self, scene, tool):
        """EvidenceRevision carries a task_node FK, which is how a manually
        uploaded file is pinned to the week it answers for. attach_evidence
        cannot set it, so a collected file is not attributable to an occurrence.
        """
        domain, evidence, _task, metric = scene
        start_instance(collection_workflow(domain, metric, tool))
        assert evidence.revisions.get(version=1).task_node_id is None

    @override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
    def test_the_collected_file_satisfies_the_week_it_was_pulled_for(self, scene, tool):
        """The loop closed: a Read objects step finds this week's occurrence,
        attach_evidence pins the revision to it, and the task board ticks."""
        from core.models import TaskNode
        from core.serializers import TaskNodeReadSerializer

        domain, evidence, task, metric = scene
        occurrence = TaskNode.objects.create(
            task_template=task, folder=domain, due_date=date(2026, 9, 21)
        )
        version = collection_workflow(
            domain, metric, tool, task_node="{{nodes.find_the_week.object.id}}"
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables

        revision = evidence.revisions.get(version=1)
        assert revision.task_node_id == occurrence.id
        assert instance.node_outputs["file_the_export"]["task_node_id"] == str(
            occurrence.id
        )
        reviewed = TaskNodeReadSerializer(occurrence).data["evidence_reviewed"]
        assert reviewed == [evidence.id]

    @override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
    def test_an_occurrence_that_does_not_expect_the_evidence_is_refused(
        self, scene, tool
    ):
        """Pinning to the wrong task writes a link neither reader ever looks at,
        so the step refuses it instead of filing dead data."""
        from core.models import TaskNode, TaskTemplate

        domain, _evidence, _task, metric = scene
        other = TaskTemplate.objects.create(name="Unrelated task", folder=domain)
        stranger = TaskNode.objects.create(
            task_template=other, folder=domain, due_date=date(2026, 9, 21)
        )
        version = collection_workflow(domain, metric, tool, task_node=str(stranger.id))
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    @override_settings(ALLOW_PRIVATE_NETWORK_REQUESTS=True)
    def test_collecting_no_longer_un_satisfies_a_person_s_upload(self, scene, tool):
        """The consequence of the FK being unset, end to end.

        `TaskNodeReadSerializer.get_evidence_reviewed` ticks an expected evidence
        when `evidence.last_revision.task_node` is the occurrence. A collected
        revision becomes the last revision and points at no occurrence, so the
        tick a person earned by uploading this week's file disappears the next
        time the workflow runs. Automating collection on a recurring task's
        evidence used to make the task board worse, not better.

        The tick is now computed from the occurrence's own revisions, the same
        source as `get_evidence_revisions_map`, so a revision filed by anything
        other than this occurrence cannot take it away.
        """
        from core.models import EvidenceRevision, TaskNode
        from core.serializers import TaskNodeReadSerializer

        domain, evidence, task, metric = scene
        occurrence = TaskNode.objects.create(
            task_template=task, folder=domain, due_date=date(2026, 9, 21)
        )
        # What a person does today: upload this week's file on the occurrence.
        EvidenceRevision.objects.create(
            evidence=evidence, version=1, task_node=occurrence
        )
        reviewed = TaskNodeReadSerializer(occurrence).data["evidence_reviewed"]
        assert reviewed == [evidence.id], "the manual upload should satisfy the week"

        # A collection run that does not name the occurrence files v2 with no
        # task_node. The week the person answered for stays answered.
        start_instance(collection_workflow(domain, metric, tool))

        occurrence.refresh_from_db()
        reviewed = TaskNodeReadSerializer(occurrence).data["evidence_reviewed"]
        assert reviewed == [evidence.id], "a later revision must not un-tick the week"

    def test_a_sibling_occurrence_does_not_steal_the_tick(self, scene):
        """The same defect without any workflow involved, which is how it
        reaches every recurring task: February files a revision, January must
        keep its own tick. `expected_evidence` is the template's list, shared by
        every occurrence, so keying the tick off the evidence's latest revision
        let each occurrence un-tick the one before it."""
        from core.models import EvidenceRevision, TaskNode
        from core.serializers import TaskNodeReadSerializer

        domain, evidence, task, _metric = scene
        january = TaskNode.objects.create(
            task_template=task, folder=domain, due_date=date(2026, 1, 12)
        )
        february = TaskNode.objects.create(
            task_template=task, folder=domain, due_date=date(2026, 2, 9)
        )
        EvidenceRevision.objects.create(evidence=evidence, version=1, task_node=january)
        EvidenceRevision.objects.create(
            evidence=evidence, version=2, task_node=february
        )

        assert TaskNodeReadSerializer(january).data["evidence_reviewed"] == [
            evidence.id
        ]
        assert TaskNodeReadSerializer(february).data["evidence_reviewed"] == [
            evidence.id
        ]
