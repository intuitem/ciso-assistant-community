"""update_object action and the shared M2M machinery.

Update targets are subtree-scoped AND gated by the run identity's view scope;
field writes are presence-driven (an empty value clears, an omitted key is
untouched); choice columns reject values outside the model's choices.
"""

import uuid

import pytest
from django.contrib.auth.models import Permission

from core.models import AppliedControl, Evidence, Vulnerability
from iam.models import Folder, Role, RoleAssignment, User
from automation.workflows.actions import (
    required_permissions,
    validate_update_config,
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


def edge(source, target, **kwargs):
    return {
        "id": str(uuid.uuid4()),
        "source": source["id"],
        "target": target["id"],
        **kwargs,
    }


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=name,
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def grant(user, folder, codenames, recursive=True):
    role = Role.objects.create(name=f"role-{uuid.uuid4()}")
    role.permissions.set(
        Permission.objects.filter(codename__in=[*codenames, "view_folder"])
    )
    ra = RoleAssignment.objects.create(
        user=user, role=role, folder=folder, is_recursive=recursive
    )
    ra.perimeter_folders.add(folder)
    return ra


def action_flow(folder, config, run_as=None):
    workflow = Workflow.objects.create(
        name=f"Update flow {uuid.uuid4()}", folder=folder
    )
    version = WorkflowVersion.objects.create(
        workflow=workflow, run_as=run_as or publisher_user()
    )
    start = node("trigger", trigger_config={"type": "manual"})
    action = node("action", label="Mutate", action_config=config)
    end = node("end")
    save_graph(
        version,
        {
            "nodes": [start, action, end],
            "edges": [edge(start, action), edge(action, end)],
            "variables": [],
        },
    )
    return version


def error_messages(instance):
    return [log.message or "" for log in instance.logs.filter(event_type="error")]


@pytest.mark.django_db
class TestUpdateObject:
    def test_updates_named_field_and_leaves_the_rest(self):
        domain = make_domain("Update domain")
        control = AppliedControl.objects.create(
            name="Patch policy", description="v1", ref_id="AC-1", folder=domain
        )
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "fields": {"description": "v2"},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        control.refresh_from_db()
        assert control.description == "v2"
        assert control.name == "Patch policy"
        assert control.ref_id == "AC-1"
        log = instance.logs.get(event_type="action_executed")
        assert log.data["updated_object_id"] == str(control.id)
        assert log.data["updated_fields"] == ["description"]

    def test_present_empty_value_clears_the_field(self):
        domain = make_domain("Clear domain")
        control = AppliedControl.objects.create(
            name="Ctl", description="to be cleared", folder=domain
        )
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "fields": {"description": ""},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        control.refresh_from_db()
        assert control.description is None

    def test_name_cannot_be_cleared(self):
        domain = make_domain("Name domain")
        control = AppliedControl.objects.create(name="Keep me", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "fields": {"name": ""},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("'name' cannot be cleared" in m for m in error_messages(instance))

    def test_object_id_is_templatable(self):
        domain = make_domain("Template domain")
        control = AppliedControl.objects.create(name="Tpl", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": "{{payload.target_id}}",
                "fields": {"description": "via template"},
            },
        )
        instance = start_instance(version, payload={"target_id": str(control.id)})
        assert instance.status == WorkflowInstance.Status.COMPLETED
        control.refresh_from_db()
        assert control.description == "via template"

    def test_choice_validation_rejects_bogus_status(self):
        domain = make_domain("Choice domain")
        vulnerability = Vulnerability.objects.create(name="V", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "vulnerability",
                "object_id": str(vulnerability.id),
                "fields": {"status": "bogus"},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("not a valid status" in m for m in error_messages(instance))
        vulnerability.refresh_from_db()
        assert vulnerability.status != "bogus"

    def test_integer_choice_accepts_rendered_string(self):
        # Templates always render strings; severity columns hold ints.
        domain = make_domain("Severity domain")
        from core.models import Incident

        incident = Incident.objects.create(name="Inc", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "incident",
                "object_id": str(incident.id),
                "fields": {"severity": "2"},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        incident.refresh_from_db()
        assert incident.severity == 2

    def test_clearing_required_choice_field_is_refused(self):
        # A typo'd template renders "" — that must not blank a status column.
        domain = make_domain("Choice clear domain")
        vulnerability = Vulnerability.objects.create(
            name="V", folder=domain, status="potential"
        )
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "vulnerability",
                "object_id": str(vulnerability.id),
                "fields": {"status": ""},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("cannot be cleared" in m for m in error_messages(instance))
        vulnerability.refresh_from_db()
        assert vulnerability.status == "potential"

    def test_target_in_sibling_domain_is_out_of_scope(self):
        ours = make_domain("Ours")
        theirs = make_domain("Theirs")
        control = AppliedControl.objects.create(name="Foreign", folder=theirs)
        version = action_flow(
            ours,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "fields": {"description": "hijack"},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("not found or out of scope" in m for m in error_messages(instance))
        control.refresh_from_db()
        assert control.description != "hijack"

    def test_ancestor_folder_target_is_out_of_scope(self):
        # _accessible_folder_ids would allow ancestors; updates must not.
        domain = make_domain("Child domain")
        control = AppliedControl.objects.create(
            name="Root control", folder=Folder.get_root_folder()
        )
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "fields": {"description": "hijack"},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("not found or out of scope" in m for m in error_messages(instance))

    def test_target_not_viewable_by_run_identity_fails(self):
        parent = make_domain("Visible parent")
        enclave = Folder.objects.create(
            name="Enclave",
            parent_folder=parent,
            content_type=Folder.ContentType.DOMAIN,
        )
        control = AppliedControl.objects.create(name="Hidden", folder=enclave)
        runner = User.objects.create_user(email="updater@authz.test")
        # non-recursive: the identity can act in the parent, not the enclave
        grant(
            runner,
            parent,
            ["view_appliedcontrol", "change_appliedcontrol"],
            recursive=False,
        )
        version = action_flow(
            parent,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "fields": {"description": "hijack"},
            },
            run_as=runner,
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("not found or out of scope" in m for m in error_messages(instance))


@pytest.mark.django_db
class TestM2MWrites:
    def test_add_remove_set_on_update(self):
        domain = make_domain("M2M domain")
        control = AppliedControl.objects.create(name="Ctl", folder=domain)
        first = Evidence.objects.create(name="E1", folder=domain)
        second = Evidence.objects.create(name="E2", folder=domain)

        def run(operation, ids):
            version = action_flow(
                domain,
                {
                    "type": "update_object",
                    "model": "applied_control",
                    "object_id": str(control.id),
                    "m2m": {"evidences": {"operation": operation, "ids": ids}},
                },
            )
            instance = start_instance(version)
            assert instance.status == WorkflowInstance.Status.COMPLETED
            return instance

        instance = run("add", [str(first.id), str(second.id)])
        assert set(control.evidences.all()) == {first, second}
        log = instance.logs.get(event_type="action_executed")
        assert log.data["m2m"] == {"evidences": {"operation": "add", "count": 2}}

        run("remove", str(first.id))  # comma-string form
        assert set(control.evidences.all()) == {second}

        run("set", [str(first.id)])
        assert set(control.evidences.all()) == {first}

        run("set", [])
        assert control.evidences.count() == 0

    def test_set_at_create(self):
        domain = make_domain("M2M create domain")
        evidence = Evidence.objects.create(name="E", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "applied_control",
                "fields": {"name": "With relations"},
                "m2m": {"evidences": {"operation": "set", "ids": [str(evidence.id)]}},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED
        control = AppliedControl.objects.get(name="With relations")
        assert set(control.evidences.all()) == {evidence}

    def test_m2m_target_outside_scope_fails(self):
        ours = make_domain("M2M ours")
        theirs = make_domain("M2M theirs")
        control = AppliedControl.objects.create(name="Ctl", folder=ours)
        foreign = Evidence.objects.create(name="Foreign", folder=theirs)
        version = action_flow(
            ours,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "m2m": {"evidences": {"operation": "add", "ids": [str(foreign.id)]}},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any(
            "outside this workflow's scope" in m for m in error_messages(instance)
        )
        assert control.evidences.count() == 0

    def test_bad_m2m_id_leaves_no_object_behind(self):
        # M2M targets resolve BEFORE the create: a failure here must not
        # persist a half-written object that every retry would duplicate.
        domain = make_domain("M2M no-orphan")
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "applied_control",
                "fields": {"name": "Orphan candidate"},
                "m2m": {"evidences": {"operation": "add", "ids": [str(uuid.uuid4())]}},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert AppliedControl.objects.filter(name="Orphan candidate").count() == 0

    def test_unknown_relation_fails(self):
        domain = make_domain("M2M unknown")
        control = AppliedControl.objects.create(name="Ctl", folder=domain)
        version = action_flow(
            domain,
            {
                "type": "update_object",
                "model": "applied_control",
                "object_id": str(control.id),
                "m2m": {"objectives": {"operation": "add", "ids": []}},
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.FAILED
        assert any("not a writable relation" in m for m in error_messages(instance))


@pytest.mark.django_db
class TestM2MRegistryIntegrity:
    def test_every_m2m_target_is_folder_scoped(self):
        """_resolve_m2m's scope check keys on folder_id; a folder-less target
        model would silently skip it and be attachable across domains."""
        from automation.workflows.actions import CREATABLE_MODELS

        for key, entry in CREATABLE_MODELS.items():
            for name, (target, _endpoint) in (entry.get("m2m_fields") or {}).items():
                columns = {f.name for f in target._meta.concrete_fields}
                assert "folder" in columns, f"{key}.{name} targets folder-less model"


@pytest.mark.django_db
class TestUpdatePermissionsAndValidation:
    def test_required_permissions_codename(self):
        assert required_permissions(
            {"type": "update_object", "model": "applied_control"}
        ) == ["change_appliedcontrol"]
        assert required_permissions({"type": "update_object", "model": "nope"}) == []

    def _codes(self, config):
        domain = make_domain(f"Val domain {uuid.uuid4()}")
        version = action_flow(domain, {"type": "update_object", **config})
        action_node = version.nodes.get(type=WorkflowNode.Type.ACTION)
        return [code for code, _message in validate_update_config(action_node)]

    def test_unknown_model(self):
        assert self._codes({"model": "user"}) == ["action_update_unknown_model"]

    def test_missing_object_id(self):
        codes = self._codes({"model": "applied_control", "fields": {}})
        assert codes == ["action_update_missing_target"]

    def test_non_updatable_field(self):
        codes = self._codes(
            {
                "model": "applied_control",
                "object_id": "{{payload.object_id}}",
                "fields": {"folder": "x"},
            }
        )
        assert codes == ["action_update_invalid_field"]

    def test_literal_empty_on_name_or_required_choice_fails_publish(self):
        codes = self._codes(
            {
                "model": "vulnerability",
                "object_id": "{{payload.object_id}}",
                "fields": {"name": "", "status": ""},
            }
        )
        assert codes == [
            "action_update_invalid_value",
            "action_update_invalid_value",
        ]

    def test_literal_bad_choice_value(self):
        codes = self._codes(
            {
                "model": "vulnerability",
                "object_id": "{{payload.object_id}}",
                "fields": {"status": "bogus"},
            }
        )
        assert codes == ["action_update_invalid_value"]

    def test_templated_choice_value_passes_publish(self):
        codes = self._codes(
            {
                "model": "vulnerability",
                "object_id": "{{payload.object_id}}",
                "fields": {"status": "{{payload.status}}"},
            }
        )
        assert codes == []

    def test_bad_relation_and_operation(self):
        codes = self._codes(
            {
                "model": "applied_control",
                "object_id": "{{payload.object_id}}",
                "m2m": {
                    "objectives": {"operation": "add", "ids": []},
                    "evidences": {"operation": "toggle", "ids": []},
                },
            }
        )
        assert sorted(codes) == [
            "action_update_invalid_relation",
            "action_update_invalid_relation",
        ]
