"""The {{now}}/{{today}} seeds and the date_offset action they feed."""

import uuid
from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from core.models import AppliedControl
from iam.models import Folder
from automation.workflows.actions import (
    required_permissions,
    validate_date_offset_config,
)
from automation.workflows.context import temporal_seeds
from automation.workflows.engine import create_instance, start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import (
    Workflow,
    WorkflowInstance,
    WorkflowNode,
    WorkflowTrigger,
    WorkflowVersion,
)
from automation.workflows.validation import validate_graph
from automation.workflows.tests.helpers import publisher_user


def node(type_, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "type": type_,
        "position": {"x": 0, "y": 0},
        **kwargs,
    }


def edge(source, target, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        **kwargs,
    }


def make_domain(name):
    return Folder.objects.create(
        name=name,
        parent_folder=Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def flow(folder, action_configs, variables=None, input_mapping=None):
    """Manual trigger -> the given action nodes in sequence -> end."""
    workflow = Workflow.objects.create(name=f"Date flow {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node(
        "trigger", trigger_config={"type": "manual"}, input_mapping=input_mapping or {}
    )
    steps = [
        node("action", label=config.pop("label"), action_config=config)
        for config in action_configs
    ]
    end = node("end")
    chain = [start, *steps, end]
    save_graph(
        version,
        {
            "nodes": chain,
            "edges": [edge(a, b) for a, b in zip(chain, chain[1:])],
            "variables": [
                {"id": str(uuid.uuid4()), **variable} for variable in (variables or [])
            ],
        },
    )
    return version


@pytest.mark.django_db
class TestTemporalSeeds:
    def test_every_run_starts_with_now_and_today(self):
        version = flow(
            make_domain("Seeds"),
            [{"label": "Say", "type": "log", "message": "{{today}} / {{now}}"}],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert instance.variables["today"] == timezone.localdate().isoformat()
        assert instance.variables["now"].startswith(instance.variables["today"])
        # Seeds render like any other variable.
        assert instance.node_outputs["say"]["message"] == (
            f"{instance.variables['today']} / {instance.variables['now']}"
        )

    def test_seeds_are_frozen_at_run_start_not_rendered_fresh(self):
        version = flow(make_domain("Frozen"), [])
        instance = create_instance(version)
        stored = instance.variables["now"]
        instance.refresh_from_db()
        # Persisted with the run, so the log shows what the run compared against.
        assert instance.variables["now"] == stored
        assert "microsecond" not in stored and stored.count(":") >= 2
        # Seconds precision: no microseconds in an email body or a filter value.
        assert "." not in stored.split("+")[0].split("Z")[0]

    def test_schedule_timezone_decides_the_date(self):
        folder = make_domain("Zoned")
        version = flow(folder, [])
        zone = "Pacific/Kiritimati"  # UTC+14: differs from UTC for 10h a day
        registration = WorkflowTrigger.objects.create(
            workflow=version.workflow,
            node_ref="schedule",
            type=WorkflowTrigger.Type.SCHEDULE,
            config={
                "type": "schedule",
                "cron_expression": "0 7 * * *",
                "timezone": zone,
            },
        )
        instance = create_instance(
            version,
            trigger=WorkflowInstance.Trigger.SCHEDULED,
            trigger_registration=registration,
        )
        expected = timezone.now().astimezone(ZoneInfo(zone)).date().isoformat()
        assert instance.variables["today"] == expected

    def test_unresolvable_timezone_falls_back_instead_of_failing(self):
        seeds = temporal_seeds(
            type("Reg", (), {"config": {"timezone": "Mars/Olympus_Mons"}})()
        )
        assert seeds["today"] == timezone.localdate().isoformat()

    def test_event_and_webhook_runs_get_seeds_too(self):
        version = flow(make_domain("Payload"), [])
        instance = create_instance(
            version,
            trigger=WorkflowInstance.Trigger.INTERNAL_EVENT,
            payload={"object_id": "x"},
        )
        assert instance.variables["today"] == timezone.localdate().isoformat()
        assert instance.variables["payload"] == {"object_id": "x"}


@pytest.mark.django_db
class TestReservedVariableKeys:
    @pytest.mark.parametrize("key", ["today", "now", "payload"])
    def test_publish_refuses_a_graph_declaring_a_reserved_key(self, key):
        version = flow(
            make_domain(f"Reserved {key}"),
            [],
            variables=[{"key": key, "type": "string", "default_value": "x"}],
        )
        codes = {error["code"] for error in validate_graph(version)}
        assert "variable_key_reserved" in codes

    def test_ordinary_variable_keys_still_publish(self):
        version = flow(
            make_domain("Ordinary"),
            [],
            variables=[{"key": "horizon", "type": "date", "default_value": ""}],
        )
        assert validate_graph(version) == []


@pytest.mark.django_db
class TestSeedsAreEngineOwned:
    def test_set_variables_may_not_overwrite_a_seed(self):
        version = flow(
            make_domain("Overwrite"),
            [
                {
                    "label": "Cheat",
                    "type": "set_variables",
                    "variables": {"today": "1999-01-01"},
                }
            ],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert instance.variables["today"] == timezone.localdate().isoformat()

    def test_publish_refuses_it_too(self):
        version = flow(
            make_domain("Overwrite publish"),
            [
                {
                    "label": "Cheat",
                    "type": "set_variables",
                    "variables": {"now": "noon"},
                }
            ],
        )
        codes = {error["code"] for error in validate_graph(version)}
        assert "action_set_variables_reserved" in codes


@pytest.mark.django_db
class TestDateOffsetAction:
    def test_defaults_to_the_run_date_and_writes_a_variable(self):
        version = flow(
            make_domain("Offset"),
            [
                {
                    "label": "Horizon",
                    "type": "date_offset",
                    "days": 30,
                    "output": "horizon",
                }
            ],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        expected = (timezone.localdate() + timedelta(days=30)).isoformat()
        assert instance.variables["horizon"] == expected
        assert instance.node_outputs["horizon"] == {
            "result": expected,
            "base": timezone.localdate().isoformat(),
        }

    def test_days_and_weeks_combine_and_go_backwards(self):
        version = flow(
            make_domain("Backwards"),
            [
                {
                    "label": "Cutoff",
                    "type": "date_offset",
                    "base": "2026-03-15",
                    "days": -1,
                    "weeks": -2,
                    "output": "cutoff",
                }
            ],
        )
        instance = start_instance(version)
        assert instance.variables["cutoff"] == "2026-02-28"

    def test_base_accepts_a_datetime_template(self):
        version = flow(
            make_domain("From event"),
            [
                {
                    "label": "Deadline",
                    "type": "date_offset",
                    "base": "{{payload.timestamp}}",
                    "days": 3,
                    "output": "deadline",
                }
            ],
        )
        instance = start_instance(
            version, payload={"timestamp": "2026-08-23T22:41:07.123456+00:00"}
        )
        assert instance.variables["deadline"] == "2026-08-26"

    def test_offset_needs_no_permissions(self):
        assert required_permissions({"type": "date_offset", "days": 1}) == []

    def test_unparsable_base_fails_the_node_without_retrying(self):
        version = flow(
            make_domain("Bad base"),
            [
                {
                    "label": "Broken",
                    "type": "date_offset",
                    "base": "{{payload.when}}",
                    "days": 1,
                    "output": "x",
                }
            ],
        )
        instance = start_instance(version, payload={"when": "next tuesday"})
        assert instance.status == WorkflowInstance.Status.FAILED


class TestDateOffsetValidation:
    def _node(self, config):
        return WorkflowNode(action_config=config)

    def test_literal_config_errors_are_caught_at_publish(self):
        codes = {
            code
            for code, _ in validate_date_offset_config(
                self._node(
                    {
                        "type": "date_offset",
                        "base": "next tuesday",
                        "days": "thirty",
                        "output": "today",
                    }
                )
            )
        }
        assert codes == {
            "action_date_offset_bad_base",
            "action_date_offset_bad_offset",
            "action_date_offset_bad_output",
        }

    def test_templated_values_pass_publish(self):
        assert (
            validate_date_offset_config(
                self._node(
                    {
                        "type": "date_offset",
                        "base": "{{payload.timestamp}}",
                        "days": "{{horizon_days}}",
                        "output": "horizon",
                    }
                )
            )
            == []
        )

    def test_other_action_types_are_ignored(self):
        assert validate_date_offset_config(self._node({"type": "log"})) == []


@pytest.mark.django_db
class TestDateWindowSweep:
    """The payoff: a sweep filtering a date column against a computed
    horizon, inexpressible before the seeds existed."""

    def test_read_filters_on_a_computed_horizon(self):
        domain = make_domain("Sweep")
        today = timezone.localdate()
        AppliedControl.objects.create(
            name="Due soon", folder=domain, eta=today + timedelta(days=5)
        )
        AppliedControl.objects.create(
            name="Due later", folder=domain, eta=today + timedelta(days=90)
        )
        AppliedControl.objects.create(name="No eta", folder=domain)
        version = flow(
            domain,
            [
                {
                    "label": "Horizon",
                    "type": "date_offset",
                    "days": 30,
                    "output": "horizon",
                },
                {
                    "label": "Fetch rows",
                    "type": "read_objects",
                    "model": "applied_control",
                    "mode": "list",
                    "filters": {
                        "operator": "and",
                        "conditions": [
                            {"field": "eta", "op": "gte", "value": "{{today}}"},
                            {"field": "eta", "op": "lte", "value": "{{horizon}}"},
                        ],
                    },
                },
            ],
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        output = instance.node_outputs["fetch_rows"]
        assert output["count"] == 1
        assert output["results"][0]["name"] == "Due soon"
