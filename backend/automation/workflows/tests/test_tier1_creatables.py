"""Second pass on the create registry: the four objects a run should be able
to open (a published rating, an incident observation, a piece of work, a rights
request) and the three mechanics they needed — a composite natural key, a
folder taken from a parent, and a fence narrower than the column's own choices.
"""

import uuid
from datetime import date, timedelta

import pytest

from core.models import Incident, TaskTemplate, TimelineEntry
from iam.models import Folder
from privacy.models import RightRequest
from tprm.models import Entity, EntityScore
from core.models import Terminology
from automation.workflows.actions import (
    CREATABLE_MODELS,
    _match_fields,
    required_permissions,
    validate_create_config,
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


def action_flow(folder, config, label="Open it"):
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


# `Assessment.save` writes the perimeter's folder only when the folder is unset
# or root, and create_object always passes a real domain folder, so that branch
# never fires for a workflow-created row. Every other match is load-bearing:
# whether the guard fires is a judgment about the values create_object produces,
# which no syntactic check can make, so a new one lands here deliberately or not
# at all.
FOLDER_FROM_EXEMPT = {"entity_assessment"}


def _folder_source(model):
    """The FK name in a `self.folder = self.<fk>.folder` anywhere in the model's
    own save(), or None. Nesting is ignored on purpose — `EntityScore` guards
    the same write with `if self.entity_id`, which is always true for a row
    create_object just built."""
    import ast
    import inspect
    import textwrap

    save = next(
        (klass.__dict__["save"] for klass in model.__mro__ if "save" in klass.__dict__),
        None,
    )
    if save is None:
        return None
    try:
        tree = ast.parse(textwrap.dedent(inspect.getsource(save)))
    except OSError, SyntaxError:  # pragma: no cover - source always ships
        return None
    for statement in ast.walk(tree):
        if not isinstance(statement, ast.Assign):
            continue
        target = statement.targets[0]
        value = statement.value
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "folder"
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
            and isinstance(value, ast.Attribute)
            and value.attr == "folder"
            and isinstance(value.value, ast.Attribute)
            and isinstance(value.value.value, ast.Name)
            and value.value.value.id == "self"
        ):
            return value.value.attr
    return None


def make_provider(name="Ratings Inc"):
    return Terminology.objects.create(
        name=name,
        folder=Folder.get_root_folder(),
        field_path=Terminology.FieldPath.ENTITY_SCORE_PROVIDER,
        is_visible=True,
    )


@pytest.mark.django_db
class TestEntityScore:
    """A rating an external service published: the connector landing zone that
    had no door. One reading per provider per day, so a re-run must patch."""

    def _flow(self, domain, entity, provider, score, as_of, **extra):
        return action_flow(
            domain,
            {
                "type": "create_object",
                "model": "entity_score",
                "fields": {
                    "entity": str(entity.id),
                    "provider": str(provider.id),
                    "score": score,
                    "as_of": as_of,
                    **extra,
                },
                "upsert": True,
            },
        )

    def test_a_published_rating_lands_on_the_entity(self):
        domain = make_domain("Ratings")
        entity = Entity.objects.create(name="Acme", folder=domain)
        provider = make_provider()
        instance = start_instance(
            self._flow(
                domain, entity, provider, 720, "2026-09-16", scale_max=900, grade="B"
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        score = EntityScore.objects.get(entity=entity)
        assert (score.score, score.scale_max, score.grade) == (720, 900, "B")
        assert score.as_of == date(2026, 9, 16)
        assert score.folder == domain

    def test_the_same_day_patches_instead_of_tripping_the_constraint(self):
        domain = make_domain("Same day")
        entity = Entity.objects.create(name="Acme", folder=domain)
        provider = make_provider()
        start_instance(self._flow(domain, entity, provider, 700, "2026-09-16"))
        second = start_instance(self._flow(domain, entity, provider, 705, "2026-09-16"))
        assert second.status == WorkflowInstance.Status.COMPLETED, second.variables
        assert EntityScore.objects.filter(entity=entity).count() == 1
        assert EntityScore.objects.get(entity=entity).score == 705
        assert second.node_outputs["open_it"]["created"] is False

    def test_a_later_date_accumulates_as_history(self):
        domain = make_domain("History")
        entity = Entity.objects.create(name="Acme", folder=domain)
        provider = make_provider()
        start_instance(self._flow(domain, entity, provider, 700, "2026-09-15"))
        start_instance(self._flow(domain, entity, provider, 710, "2026-09-16"))
        assert EntityScore.objects.filter(entity=entity).count() == 2

    def test_it_matches_where_the_row_actually_lands(self):
        """The entity lives below the workflow, so save() files the score in the
        child folder. Matching on the workflow's own folder would miss it and
        the re-run would hit the uniqueness constraint."""
        domain = make_domain("Parent scope")
        child = Folder.objects.create(
            name="Child scope",
            parent_folder=domain,
            content_type=Folder.ContentType.DOMAIN,
        )
        entity = Entity.objects.create(name="Acme", folder=child)
        provider = make_provider()
        start_instance(self._flow(domain, entity, provider, 700, "2026-09-16"))
        second = start_instance(self._flow(domain, entity, provider, 701, "2026-09-16"))
        assert second.status == WorkflowInstance.Status.COMPLETED, second.variables
        assert EntityScore.objects.filter(entity=entity).count() == 1
        assert EntityScore.objects.get(entity=entity).folder == child

    def test_an_entity_outside_the_workflow_scope_is_refused(self):
        domain = make_domain("Here score")
        elsewhere = make_domain("Elsewhere score")
        entity = Entity.objects.create(name="Foreign", folder=elsewhere)
        provider = make_provider()
        version = self._flow(domain, entity, provider, 700, "2026-09-16")
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not EntityScore.objects.filter(entity=entity).exists()

    def test_a_missing_score_is_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "entity_score",
                        "fields": {"entity": "{{e}}", "provider": "{{p}}"},
                    }
                )
            )
        }
        assert codes == {"action_create_missing_field"}

    def test_its_natural_key_is_the_triple(self):
        assert _match_fields(CREATABLE_MODELS["entity_score"]) == (
            "entity",
            "provider",
            "as_of",
        )


@pytest.mark.django_db
class TestTimelineEntry:
    def _flow(self, domain, incident, **fields):
        return action_flow(
            domain,
            {
                "type": "create_object",
                "model": "timeline_entry",
                "fields": {"incident": str(incident.id), **fields},
            },
        )

    def test_an_observation_lands_on_the_incident(self):
        domain = make_domain("Timeline")
        incident = Incident.objects.create(name="Beaconing", folder=domain)
        instance = start_instance(
            self._flow(
                domain,
                incident,
                entry="EDR flagged 3 hosts",
                entry_type="detection",
                observation="from the nightly pull",
            )
        )
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        written = TimelineEntry.objects.get(incident=incident)
        assert written.entry == "EDR flagged 3 hosts"
        assert written.entry_type == "detection"
        assert written.folder == domain

    def test_a_lifecycle_entry_type_is_refused(self):
        """severity_changed/status_changed are the viewset's: a run reports what
        it saw, it does not narrate a state change it did not make."""
        domain = make_domain("No narration")
        incident = Incident.objects.create(name="Beaconing", folder=domain)
        version = self._flow(
            domain, incident, entry="escalated", entry_type="status_changed"
        )
        assert start_instance(version).status == WorkflowInstance.Status.FAILED
        assert not TimelineEntry.objects.filter(incident=incident).exists()

    def test_the_fence_is_reported_at_publish_too(self):
        errors = validate_create_config(
            WorkflowNode(
                action_config={
                    "type": "create_object",
                    "model": "timeline_entry",
                    "fields": {
                        "incident": "{{incident_id}}",
                        "entry": "seen",
                        "entry_type": "severity_changed",
                    },
                }
            )
        )
        assert [c for c, _ in errors] == ["action_create_value_not_allowed"]

    def test_a_blank_entry_is_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "timeline_entry",
                        "fields": {"incident": "{{incident_id}}"},
                    }
                )
            )
        }
        assert codes == {"action_create_missing_field"}

    def test_a_missing_incident_is_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "timeline_entry",
                        "fields": {"entry": "seen"},
                    }
                )
            )
        }
        assert codes == {"action_create_missing_fk"}


@pytest.mark.django_db
class TestTaskTemplate:
    def test_a_run_can_attach_dated_work(self):
        domain = make_domain("Work")
        due = (date.today() + timedelta(days=30)).isoformat()
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "task_template",
                "fields": {
                    "name": "Re-collect the export",
                    "ref_id": "T-1",
                    "task_date": due,
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        task = TaskTemplate.objects.get(name="Re-collect the export")
        assert task.task_date.isoformat() == due
        assert task.folder == domain
        # Recurrence is an authored decision: objects.create() does not run the
        # schedule column's validator, so the field is not on the whitelist.
        assert "schedule" not in CREATABLE_MODELS["task_template"]["fields"]
        assert task.schedule is None

    def test_it_needs_the_task_permission(self):
        assert required_permissions(
            {"type": "create_object", "model": "task_template"}
        ) == ["add_tasktemplate"]


@pytest.mark.django_db
class TestRightRequest:
    def test_an_intake_opens_a_request(self):
        domain = make_domain("DSAR")
        version = action_flow(
            domain,
            {
                "type": "create_object",
                "model": "right_request",
                "fields": {
                    "name": "Access request — J. Doe",
                    "requested_on": "2026-09-16",
                    "request_type": "access",
                },
            },
        )
        instance = start_instance(version)
        assert instance.status == WorkflowInstance.Status.COMPLETED, instance.variables
        request = RightRequest.objects.get(name="Access request — J. Doe")
        assert request.request_type == "access"
        # A run opens the request; closing it is the DPO's.
        assert request.status == "new"
        assert "status" not in CREATABLE_MODELS["right_request"]["fields"]

    def test_a_missing_request_date_is_caught_at_publish(self):
        codes = {
            c
            for c, _ in validate_create_config(
                WorkflowNode(
                    action_config={
                        "type": "create_object",
                        "model": "right_request",
                        "fields": {"name": "Access request"},
                    }
                )
            )
        }
        assert codes == {"action_create_missing_field"}

    def test_an_unknown_request_type_is_refused_at_publish(self):
        errors = validate_create_config(
            WorkflowNode(
                action_config={
                    "type": "create_object",
                    "model": "right_request",
                    "fields": {
                        "name": "Access request",
                        "requested_on": "2026-09-16",
                        "request_type": "telepathy",
                    },
                }
            )
        )
        assert [c for c, _ in errors] == ["action_create_value_not_allowed"]


class TestRegistryShape:
    """The builder reads the registry over the wire, so an entry that names a
    field the model does not have would render a box that can never save."""

    def test_every_whitelisted_field_exists_on_its_model(self):
        from automation.workflows.actions import get_model_field

        for key, entry in CREATABLE_MODELS.items():
            for field in entry["fields"]:
                assert get_model_field(entry["model"], field) is not None, (
                    f"{key}.{field}"
                )

    def test_every_required_field_and_match_field_is_reachable(self):
        for key, entry in CREATABLE_MODELS.items():
            known = set(entry["fields"]) | set(entry.get("fk_fields") or {})
            for field in entry.get("required_fields") or []:
                assert field in known, f"{key}.{field}"
            for field in _match_fields(entry):
                assert field in known or field == "name", f"{key}.{field}"

    def test_narrowed_values_are_a_subset_of_the_column(self):
        from automation.workflows.actions import _column_choices

        for key, entry in CREATABLE_MODELS.items():
            for field, values in (entry.get("allowed_values") or {}).items():
                column = _column_choices(entry["model"], field)
                assert column is not None, f"{key}.{field}"
                assert set(values) <= column, f"{key}.{field}"

    def test_required_fields_match_what_the_model_cannot_store_empty(self):
        """`required_fields` is declared, not derived — deriving it would let a
        model change silently tighten publish validation. This is the tripwire
        that keeps the declaration honest.

        `name` is excluded: create_object has its own rule for it, with an
        upsert exemption this check would not reproduce.
        """
        from automation.workflows.actions import get_model_field

        for key, entry in CREATABLE_MODELS.items():
            cannot_be_empty = {
                field
                for field in entry["fields"]
                if field != "name"
                and (column := get_model_field(entry["model"], field)) is not None
                and not (column.null or column.blank or column.has_default())
            }
            assert cannot_be_empty == set(entry.get("required_fields") or []), key

    def test_an_entry_declares_folder_from_when_save_derives_the_folder(self):
        """A row whose `save()` takes its folder from a parent does not land in
        the folder the upsert searched, so the match misses and the run either
        duplicates the row or trips a uniqueness constraint.

        Anything the parse finds must either declare `folder_from` or be named
        in FOLDER_FROM_EXEMPT with the reason its write never fires.
        """
        for key, entry in CREATABLE_MODELS.items():
            derived = _folder_source(entry["model"])
            if derived is None or derived not in (entry.get("fk_fields") or {}):
                continue
            if key in FOLDER_FROM_EXEMPT:
                assert entry.get("folder_from") is None, key
                continue
            assert entry.get("folder_from") == derived, key
