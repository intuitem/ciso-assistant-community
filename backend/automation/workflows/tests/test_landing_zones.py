"""The structured landing zones: a run that measured something files it where
the product already knows how to read it — a metric sample, a posture result —
instead of leaving a number stranded in a variable. Plus attach_evidence's
versioned mode, which is what makes a recurring collection keep its history.
"""

import uuid

import pytest

from core.models import Asset, Evidence, EvidenceRevision, Framework, RequirementNode
from iam.models import Folder
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from automation.models import PostureAssessment, PostureResult, PostureRun
from automation.workflows.actions import (
    required_permissions,
    validate_post_results_config,
    validate_record_measurement_config,
)
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowVersion,
)
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target):
    return {"id": str(uuid.uuid4()), "source": source["id"], "target": target["id"]}


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def action_flow(folder, config, label="Land it"):
    workflow = Workflow.objects.create(name=f"Flow {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", trigger_config={"type": "manual"})
    act = node("action", label=label, action_config=config)
    end = node("end")
    save_graph(
        version,
        {"nodes": [start, act, end], "edges": [edge(start, act), edge(act, end)]},
    )
    return version


def make_metric(folder, category=MetricDefinition.Category.QUANTITATIVE, choices=None):
    slug = uuid.uuid4().hex[:8]
    definition = MetricDefinition.objects.create(
        name=f"Metric {slug}",
        urn=f"urn:test:risk:library:metrics:metric:{slug}",
        folder=Folder.get_root_folder(),
        category=category,
        choices_definition=choices,
    )
    return MetricInstance.objects.create(
        name=f"Instance {slug}",
        folder=folder,
        metric_definition=definition,
    )


def make_posture(folder, ref_ids=("1.1", "1.2")):
    slug = uuid.uuid4().hex[:8]
    framework = Framework.objects.create(
        name=f"Benchmark {slug}",
        urn=f"urn:test:risk:library:bench-{slug}:framework:bench",
        folder=Folder.get_root_folder(),
    )
    for ref_id in ref_ids:
        RequirementNode.objects.create(
            name=f"Check {ref_id}",
            ref_id=ref_id,
            urn=f"{framework.urn}:req{ref_id}",
            framework=framework,
            assessable=True,
            folder=Folder.get_root_folder(),
        )
    assessment = PostureAssessment.objects.create(
        name=f"Posture {slug}", folder=folder, framework=framework
    )
    asset = Asset.objects.create(name=f"Host {slug}", folder=folder)
    assessment.assets.add(asset)
    return assessment, asset


@pytest.mark.django_db
class TestAttachEvidenceRevisions:
    """Gap the recurring case hit: the default mode overwrites the newest
    revision, so a nightly collection kept one file and lost every earlier one."""

    def _flow(self, domain, evidence, **extra):
        return action_flow(
            domain,
            {
                "type": "attach_evidence",
                "evidence": str(evidence.id),
                "source": "text",
                "filename": "export.csv",
                "text": "run,ok\n",
                **extra,
            },
        )

    def test_the_default_still_overwrites_the_latest_revision(self):
        domain = make_domain("Overwrite")
        evidence = Evidence.objects.create(name="Weekly export", folder=domain)
        assert start_instance(self._flow(domain, evidence)).status == (
            WorkflowInstance.Status.COMPLETED
        )
        assert start_instance(self._flow(domain, evidence)).status == (
            WorkflowInstance.Status.COMPLETED
        )
        assert evidence.revisions.count() == 1

    def test_new_revision_files_each_run_separately(self):
        domain = make_domain("Versioned")
        evidence = Evidence.objects.create(name="Nightly export", folder=domain)
        first = start_instance(self._flow(domain, evidence, new_revision=True))
        second = start_instance(self._flow(domain, evidence, new_revision=True))
        assert second.status == WorkflowInstance.Status.COMPLETED, second.variables
        versions = sorted(evidence.revisions.values_list("version", flat=True))
        assert versions == [1, 2]
        assert first.node_outputs["land_it"]["version"] == 1
        assert second.node_outputs["land_it"]["version"] == 2
        # Both files survive: the point of the mode.
        assert all(r.attachment for r in evidence.revisions.all())

    def test_a_new_revision_moves_the_evidence_back_to_review(self):
        domain = make_domain("Review again")
        evidence = Evidence.objects.create(
            name="Approved export", folder=domain, status=Evidence.Status.APPROVED
        )
        start_instance(self._flow(domain, evidence, new_revision=True))
        evidence.refresh_from_db()
        assert evidence.status == Evidence.Status.IN_REVIEW

    def test_a_refused_extension_leaves_no_orphan_revision(self):
        domain = make_domain("Bad extension versioned")
        evidence = Evidence.objects.create(name="Payload", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "attach_evidence",
                "evidence": str(evidence.id),
                "source": "text",
                "filename": "payload.exe",
                "text": "whatever",
                "new_revision": True,
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert evidence.revisions.count() == 0
        evidence.refresh_from_db()
        assert evidence.status == Evidence.Status.DRAFT

    def test_filing_a_revision_needs_its_own_permission(self):
        """Both modes: the default one creates a revision when there is none."""
        expected = ["change_evidence", "add_evidencerevision"]
        assert required_permissions({"type": "attach_evidence"}) == expected
        assert (
            required_permissions({"type": "attach_evidence", "new_revision": True})
            == expected
        )


@pytest.mark.django_db
class TestRecordMeasurement:
    def test_a_quantitative_reading_lands_as_a_sample(self):
        domain = make_domain("Quantitative")
        metric = make_metric(domain)
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "42.5",
                "observation": "from the nightly pull",
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        sample = CustomMetricSample.objects.get(metric_instance=metric)
        assert sample.value == {"result": 42.5}
        assert sample.folder == domain
        assert sample.observation == "from the nightly pull"
        assert instance.node_outputs["land_it"]["object_id"] == str(sample.id)

    def test_the_value_may_come_from_an_earlier_step(self):
        domain = make_domain("Templated value")
        metric = make_metric(domain)
        workflow = Workflow.objects.create(name="Pull", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        seed = node(
            "action",
            label="Seed",
            action_config={"type": "set_variables", "variables": {"coverage": 87}},
        )
        act = node(
            "action",
            label="Land it",
            action_config={
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "{{coverage}}",
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, seed, act, end],
                "edges": [edge(start, seed), edge(seed, act), edge(act, end)],
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED
        assert CustomMetricSample.objects.get(metric_instance=metric).value == {
            "result": 87.0
        }

    def test_a_qualitative_metric_takes_a_choice_index(self):
        domain = make_domain("Qualitative")
        metric = make_metric(
            domain,
            category=MetricDefinition.Category.QUALITATIVE,
            choices=[{"ref_id": "low"}, {"ref_id": "high"}],
        )
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "2",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED
        assert CustomMetricSample.objects.get(metric_instance=metric).value == {
            "choice_index": 2
        }

    def test_a_choice_index_past_the_last_option_is_refused(self):
        domain = make_domain("Out of range")
        metric = make_metric(
            domain,
            category=MetricDefinition.Category.QUALITATIVE,
            choices=[{"ref_id": "low"}, {"ref_id": "high"}],
        )
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "3",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not CustomMetricSample.objects.filter(metric_instance=metric).exists()

    def test_a_value_that_is_not_a_number_fails_the_node(self):
        domain = make_domain("Not a number")
        metric = make_metric(domain)
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "n/a",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not CustomMetricSample.objects.filter(metric_instance=metric).exists()

    def test_a_reading_cannot_be_dated_in_the_future(self):
        domain = make_domain("Future")
        metric = make_metric(domain)
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "1",
                "timestamp": "2999-01-01T00:00:00+00:00",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_a_metric_outside_the_workflow_scope_is_refused(self):
        domain = make_domain("Here measure")
        elsewhere = make_domain("Elsewhere measure")
        metric = make_metric(elsewhere)
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "1",
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not CustomMetricSample.objects.filter(metric_instance=metric).exists()

    def test_the_sample_can_cite_the_file_the_number_came_from(self):
        domain = make_domain("Cited")
        metric = make_metric(domain)
        evidence = Evidence.objects.create(name="Export", folder=domain)
        revision = EvidenceRevision.objects.create(evidence=evidence)
        version = action_flow(
            domain,
            {
                "type": "record_measurement",
                "metric_instance": str(metric.id),
                "value": "3",
                "evidence_revision": str(revision.id),
            },
        )
        assert start_instance(version).status == WorkflowInstance.Status.COMPLETED
        assert (
            CustomMetricSample.objects.get(metric_instance=metric).evidence_revision
            == revision
        )

    def test_it_needs_the_sample_permission(self):
        assert required_permissions({"type": "record_measurement"}) == [
            "add_custommetricsample"
        ]


@pytest.mark.django_db
class TestPostResults:
    def _flow(self, domain, assessment, asset, results, **extra):
        return action_flow(
            domain,
            {
                "type": "post_results",
                "posture_assessment": str(assessment.id),
                "asset": str(asset.id),
                "results": results,
                **extra,
            },
        )

    def test_a_scan_lands_as_posture_results(self):
        domain = make_domain("Scan")
        assessment, asset = make_posture(domain)
        version = self._flow(
            domain,
            assessment,
            asset,
            [
                {"ref_id": "1.1", "result": "pass"},
                {"ref_id": "1.2", "result": "fail", "actual": "off", "expected": "on"},
            ],
            tool="fake-scanner",
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        results = {r.requirement.ref_id: r for r in assessment.results}
        assert results["1.1"].result == "pass"
        assert results["1.2"].actual == "off"
        assert results["1.2"].source == PostureResult.Source.API
        assert results["1.2"].run.tool == "fake-scanner"
        output = instance.node_outputs["land_it"]
        assert output["created"] == 2
        assert output["unknown_count"] == 0

    def test_results_may_reference_an_earlier_step(self):
        domain = make_domain("From a step")
        assessment, asset = make_posture(domain)
        workflow = Workflow.objects.create(name="Fetch", folder=domain)
        version = WorkflowVersion.objects.create(
            workflow=workflow, run_as=publisher_user()
        )
        start = node("trigger", trigger_config={"type": "manual"})
        seed = node(
            "action",
            label="Seed",
            action_config={
                "type": "set_variables",
                "variables": {"checks": [{"ref_id": "1.1", "result": "fail"}]},
            },
        )
        act = node(
            "action",
            label="Land it",
            action_config={
                "type": "post_results",
                "posture_assessment": str(assessment.id),
                "asset": str(asset.id),
                "results": "{{checks}}",
            },
        )
        end = node("end")
        save_graph(
            version,
            {
                "nodes": [start, seed, act, end],
                "edges": [edge(start, seed), edge(seed, act), edge(act, end)],
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        assert assessment.results.get().result == "fail"

    def test_the_same_run_id_patches_instead_of_duplicating(self):
        domain = make_domain("Patch")
        assessment, asset = make_posture(domain)
        run_id = str(uuid.uuid4())
        start_instance(
            self._flow(
                domain,
                assessment,
                asset,
                [{"ref_id": "1.1", "result": "fail"}],
                run_id=run_id,
            )
        )
        second = start_instance(
            self._flow(
                domain,
                assessment,
                asset,
                [{"ref_id": "1.1", "result": "pass"}],
                run_id=run_id,
            )
        )
        assert second.status == WorkflowInstance.Status.COMPLETED
        assert assessment.results.count() == 1
        assert assessment.results.get().result == "pass"
        assert second.node_outputs["land_it"]["updated"] == 1

    def test_unknown_checks_are_reported_without_flooding_the_output(self):
        domain = make_domain("Unknown refs")
        assessment, asset = make_posture(domain)
        entries = [{"ref_id": f"9.{i}", "result": "pass"} for i in range(30)]
        instance = start_instance(self._flow(domain, assessment, asset, entries))
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["land_it"]
        assert output["unknown_count"] == 30
        assert len(output["unknown_ref_ids"]) == 20
        assert assessment.results.count() == 0
        # Matched nothing, so the run was dropped and there is no id.
        assert output["run_id"] is None
        assert PostureRun.objects.count() == 0

    def test_an_invalid_verdict_fails_the_node(self):
        domain = make_domain("Bad verdict")
        assessment, asset = make_posture(domain)
        version = self._flow(
            domain, assessment, asset, [{"ref_id": "1.1", "result": "probably"}]
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert assessment.results.count() == 0

    def test_results_that_are_not_a_list_fail_the_node(self):
        domain = make_domain("Not a list")
        assessment, asset = make_posture(domain)
        version = self._flow(domain, assessment, asset, "{{nowhere}}")
        assert start_instance(version).status == WorkflowInstance.Status.FAILED

    def test_an_oversized_batch_is_refused(self, monkeypatch):
        monkeypatch.setattr(
            "automation.workflows.actions.results_max_entries", lambda: 5
        )
        domain = make_domain("Too many")
        assessment, asset = make_posture(domain)
        entries = [{"ref_id": "1.1", "result": "pass"} for _ in range(6)]
        version = self._flow(domain, assessment, asset, entries)
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert assessment.results.count() == 0

    def test_an_assessment_outside_the_workflow_scope_is_refused(self):
        domain = make_domain("Here post")
        elsewhere = make_domain("Elsewhere post")
        assessment, asset = make_posture(elsewhere)
        version = self._flow(
            domain, assessment, asset, [{"ref_id": "1.1", "result": "pass"}]
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert assessment.results.count() == 0

    def test_it_needs_the_assessment_change_permission(self):
        assert required_permissions({"type": "post_results"}) == [
            "change_postureassessment"
        ]


class TestLandingZoneValidation:
    def _node(self, config):
        return WorkflowNode(action_config=config)

    def test_a_measurement_needs_a_metric_and_a_value(self):
        codes = {
            c
            for c, _ in validate_record_measurement_config(
                self._node({"type": "record_measurement"})
            )
        }
        assert codes == {
            "action_measure_missing_metric",
            "action_measure_missing_value",
        }

    def test_a_sound_measurement_passes(self):
        assert (
            validate_record_measurement_config(
                self._node(
                    {
                        "type": "record_measurement",
                        "metric_instance": "{{metric_id}}",
                        "value": "{{nodes.fetch.body.coverage}}",
                    }
                )
            )
            == []
        )

    def test_results_need_an_assessment_an_asset_and_rows(self):
        codes = {
            c
            for c, _ in validate_post_results_config(
                self._node({"type": "post_results"})
            )
        }
        assert codes == {
            "action_results_missing_assessment",
            "action_results_missing_asset",
            "action_results_missing_results",
        }

    def test_a_literal_that_is_not_json_is_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_post_results_config(
                self._node(
                    {
                        "type": "post_results",
                        "posture_assessment": "x",
                        "asset": "y",
                        "results": "the scan output",
                    }
                )
            )
        }
        assert codes == {"action_results_not_a_list"}

    def test_valid_json_that_is_not_a_list_is_refused(self):
        """_resolve_list wants a list; anything else failed on the first run."""
        codes = {
            c
            for c, _ in validate_post_results_config(
                self._node(
                    {
                        "type": "post_results",
                        "posture_assessment": "x",
                        "asset": "y",
                        "results": '{"a": 1}',
                    }
                )
            )
        }
        assert codes == {"action_results_not_a_list"}

    def test_a_step_reference_passes(self):
        assert (
            validate_post_results_config(
                self._node(
                    {
                        "type": "post_results",
                        "posture_assessment": "{{assessment_id}}",
                        "asset": "{{asset_id}}",
                        "results": "{{nodes.fetch.body.checks}}",
                    }
                )
            )
            == []
        )


@pytest.mark.django_db
class TestLockedAssessment:
    def test_a_locked_assessment_refuses_results(self):
        """Sharing the write path has to mean sharing its refusals."""
        domain = make_domain("Locked")
        assessment, asset = make_posture(domain)
        assessment.is_locked = True
        assessment.save()
        instance = start_instance(
            TestPostResults()._flow(
                domain, assessment, asset, [{"ref_id": "1.1", "result": "pass"}]
            )
        )
        assert instance.status == WorkflowInstance.Status.FAILED
        assert assessment.results.count() == 0
