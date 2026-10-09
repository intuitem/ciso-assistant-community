import uuid

import pytest

from automation.workflows.actions import (
    required_permissions,
    validate_upsert_objects_config,
)
from automation.workflows.engine import start_instance
from automation.workflows.graph import save_graph
from automation.workflows.models import Workflow, WorkflowInstance, WorkflowVersion
from automation.workflows.tests.helpers import publisher_user
from automation.workflows.tests.test_unreachable_tool import edge, make_domain, node
from core.models import Asset

FIELDS = {"name": "{{item.host}}", "ref_id": "{{item.id}}", "type": "SP"}


def upsert_flow(folder, **extra):
    workflow = Workflow.objects.create(name=f"Upsert {uuid.uuid4()}", folder=folder)
    version = WorkflowVersion.objects.create(workflow=workflow, run_as=publisher_user())
    start = node("trigger", "start", trigger_config={"type": "manual"})
    keep = node(
        "action",
        "keep",
        label="Keep",
        action_config={
            "type": "upsert_objects",
            "model": "asset",
            "items": "{{payload.devices}}",
            "fields": FIELDS,
            **extra,
        },
    )
    done = node("end", "done")
    save_graph(
        version,
        {"nodes": [start, keep, done], "edges": [edge(start, keep), edge(keep, done)]},
    )
    return version


def run(version, devices):
    instance = start_instance(version, payload={"devices": devices})
    instance.refresh_from_db()
    return instance


def devices(*names):
    return [{"host": name, "id": f"id-{name}"} for name in names]


@pytest.mark.django_db
class TestUpsertObjects:
    def test_creates_then_updates(self):
        domain = make_domain("Bulk")
        version = upsert_flow(domain)
        first = run(version, devices("a", "b"))
        assert first.status == WorkflowInstance.Status.COMPLETED
        assert first.node_outputs["keep"]["created"] == 2

        second = run(version, [{"host": "a", "id": "id-a2"}, *devices("c")])
        output = second.node_outputs["keep"]
        assert (output["created"], output["updated"]) == (1, 1)
        assets = Asset.objects.filter(folder=domain).order_by("name")
        assert [(a.name, a.ref_id) for a in assets] == [
            ("a", "id-a2"),
            ("b", "id-b"),
            ("c", "id-c"),
        ]

    def test_a_bad_item_is_counted_and_the_rest_land(self):
        domain = make_domain("Partial")
        instance = run(upsert_flow(domain), [{"host": "", "id": "x"}, *devices("ok")])
        output = instance.node_outputs["keep"]
        assert instance.status == WorkflowInstance.Status.COMPLETED
        assert (output["created"], output["failed"]) == (1, 1)
        assert output["errors"][0]["index"] == 0
        assert Asset.objects.filter(folder=domain).count() == 1

    def test_stop_mode_fails_the_run(self):
        domain = make_domain("Stop")
        instance = run(
            upsert_flow(domain, on_item_error="stop"),
            [{"host": "", "id": "x"}, *devices("ok")],
        )
        assert instance.status == WorkflowInstance.Status.FAILED

    def test_cap_marks_truncated(self, settings):
        settings.WORKFLOW_UPSERT_MAX_ITEMS = 2
        domain = make_domain("Cap")
        output = run(upsert_flow(domain), devices("a", "b", "c")).node_outputs["keep"]
        assert (output["received"], output["created"], output["truncated"]) == (
            3,
            2,
            True,
        )

    def test_vendor_values_are_not_rendered_again(self):
        domain = make_domain("Literal")
        run(upsert_flow(domain), [{"host": "{{payload.devices}}", "id": "x"}])
        assert Asset.objects.get(folder=domain).name == "{{payload.devices}}"

    def test_items_must_be_a_list(self):
        domain = make_domain("NotList")
        instance = start_instance(upsert_flow(domain), payload={"devices": "nope"})
        assert instance.status == WorkflowInstance.Status.FAILED


@pytest.mark.django_db
class TestUpsertAuthorization:
    def test_updating_a_row_needs_change_where_it_lives(self, monkeypatch):
        from automation.workflows import authz

        home = make_domain("Home")
        elsewhere = make_domain("Elsewhere")
        Asset.objects.create(name="a", ref_id="old", folder=elsewhere)
        monkeypatch.setattr(
            "automation.workflows.actions._creation_folder", lambda instance: elsewhere
        )
        real_can = authz.can
        monkeypatch.setattr(
            authz,
            "can",
            lambda user, codename, folder: (
                False
                if codename == "change_asset" and folder == elsewhere
                else real_can(user, codename, folder)
            ),
        )
        instance = run(upsert_flow(home), devices("a", "b"))
        assert instance.status == WorkflowInstance.Status.FAILED
        assert Asset.objects.get(folder=elsewhere, name="a").ref_id == "old"


@pytest.mark.django_db
class TestBadValues:
    def test_a_value_that_cannot_be_rendered_fails_only_its_item(self):
        domain = make_domain("HugeFloat")
        version = upsert_flow(
            domain, fields={**FIELDS, "description": "score {{item.score}}"}
        )
        output = run(
            version,
            [
                {"host": "bad", "id": "1", "score": 1e300},
                {"host": "good", "id": "2", "score": 1.5},
            ],
        ).node_outputs["keep"]
        assert (output["created"], output["failed"]) == (1, 1)
        assert output["errors"][0] == {"index": 0, "reason": "InvalidOperation"}


def config_node(**config):
    return type(
        "Node",
        (),
        {
            "action_config": {
                "type": "upsert_objects",
                "model": "asset",
                "items": "{{nodes.x.items}}",
                "fields": FIELDS,
                **config,
            }
        },
    )()


class TestPublishAndPermissions:
    def codes(self, **config):
        return {
            code for code, _ in validate_upsert_objects_config(config_node(**config))
        }

    def test_valid_config_passes(self):
        assert self.codes() == set()

    def test_missing_items(self):
        assert "action_upsert_missing_items" in self.codes(items="")

    def test_unknown_model(self):
        assert "action_create_unknown_model" in self.codes(model="nope")

    def test_fenced_value(self):
        assert "action_create_value_not_allowed" in self.codes(
            fields={**FIELDS, "type": "XX"}
        )

    def test_needs_add_and_change(self):
        assert required_permissions(config_node().action_config) == [
            "add_asset",
            "change_asset",
        ]


@pytest.mark.django_db
class TestItemErrors:
    def test_a_value_the_model_rejects_fails_only_its_item(self, monkeypatch):
        from automation.workflows import actions

        real = actions.CreateObjectAction.execute

        def execute(self, config, instance, fields=None):
            if fields and fields.get("name") == "bad":
                raise ValueError("Field 'x' expected a number but got 'n/a'")
            return real(self, config, instance, fields)

        monkeypatch.setattr(actions.CreateObjectAction, "execute", execute)
        domain = make_domain("ValueError")
        output = run(upsert_flow(domain), devices("bad", "good")).node_outputs["keep"]
        assert (output["created"], output["failed"]) == (1, 1)
        assert output["errors"][0] == {"index": 0, "reason": "ValueError"}


@pytest.mark.django_db
class TestLookupsOncePerStep:
    def test_permission_checks_do_not_grow_with_items(self, monkeypatch):
        from automation.workflows import authz

        calls = []
        real_can = authz.can

        def can(user, codename, folder):
            calls.append(codename)
            return real_can(user, codename, folder)

        monkeypatch.setattr(authz, "can", can)
        domain = make_domain("Memo")
        version = upsert_flow(domain)
        run(version, devices(*[f"h{i}" for i in range(5)]))
        five = len(calls)
        calls.clear()
        run(version, devices(*[f"x{i}" for i in range(40)]))
        assert len(calls) == five
