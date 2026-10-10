"""Derived metrics: formula validation, evaluation against a folder subtree,
value shaping, the sampler with its lock and error recording, the sweep's
due rule, downsampling, and the preview and refresh endpoints."""

import datetime
import uuid

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from core.models import AppliedControl
from iam.models import Folder, Role, RoleAssignment, User, UserGroup
from metrology.derived import (
    DerivedMetricError,
    compute_sample,
    downsample_derived_samples,
    due_instances,
    evaluate_formula,
    is_due,
    resolve_time_tokens,
    shape_value,
    validate_formula,
)
from metrology.models import CustomMetricSample, MetricDefinition, MetricInstance
from metrology.serializers import MetricDefinitionWriteSerializer
from metrology.views import MetricDefinitionViewSet, MetricInstanceViewSet

CONTROLS = {"model": "applied_control", "aggregates": [{"fn": "count"}]}
ACTIVE = {
    "model": "applied_control",
    "filters": {"conditions": [{"field": "status", "op": "eq", "value": "active"}]},
    "aggregates": [{"fn": "count"}],
}


def make_domain(name, parent=None):
    return Folder.objects.create(
        name=f"{name} {uuid.uuid4().hex[:6]}",
        parent_folder=parent or Folder.get_root_folder(),
        content_type=Folder.ContentType.DOMAIN,
    )


def make_definition(
    expression="active.count * 100.0 / controls.count", datasets=None, **extra
):
    return MetricDefinition.objects.create(
        name=f"Share of active controls {uuid.uuid4().hex[:6]}",
        folder=Folder.get_root_folder(),
        datasets={"controls": CONTROLS, "active": ACTIVE}
        if datasets is None
        else datasets,
        expression=expression,
        **extra,
    )


def make_instance(domain, definition=None, **extra):
    return MetricInstance.objects.create(
        name=f"Instance {uuid.uuid4().hex[:6]}",
        folder=domain,
        metric_definition=definition or make_definition(),
        **{"status": MetricInstance.Status.ACTIVE, **extra},
    )


def make_controls(domain, statuses):
    for index, status in enumerate(statuses):
        AppliedControl.objects.create(name=f"AC {index}", folder=domain, status=status)


class TestValidateFormula:
    def codes(self, datasets, expression):
        return [code for code, _m in validate_formula(datasets, expression)]

    def test_a_manual_definition_has_nothing_to_check(self):
        assert validate_formula(None, "") == []
        assert validate_formula({}, None) == []

    def test_a_clean_formula_passes(self):
        assert (
            validate_formula(
                {"controls": CONTROLS, "active": ACTIVE},
                "active.count / controls.count",
            )
            == []
        )
        assert validate_formula({"c": CONTROLS}, "c.count > previous ? 1 : 0") == []
        assert validate_formula({"c": CONTROLS}, "metrics.other.value + c.count") == []

    def test_datasets_are_required_and_named(self):
        assert self.codes(None, "1 + 1") == ["derived_datasets_missing"]
        assert self.codes({"1st": CONTROLS}, "1") == ["derived_dataset_name_invalid"]
        assert self.codes({"previous": CONTROLS}, "1") == [
            "derived_dataset_name_invalid"
        ]
        assert self.codes({"c": "nope"}, "1") == ["derived_dataset_invalid"]
        assert self.codes({f"d{i}": CONTROLS for i in range(11)}, "1") == [
            "derived_datasets_too_many"
        ]

    def test_datasets_are_read_configs_in_aggregate_mode(self):
        bad = {"model": "applied_control", "aggregates": [{"fn": "avg"}], "limit": 5}
        errors = validate_formula({"c": bad}, "1")
        assert [c for c, _m in errors] == ["derived_dataset_invalid"] * 2
        assert all(m.startswith("dataset 'c': ") for _c, m in errors)
        # The stored mode is ignored: a dataset always aggregates.
        assert validate_formula({"c": {**CONTROLS, "mode": "list"}}, "c.count") == []

    def test_the_expression_is_compiled_and_its_names_checked(self):
        assert self.codes({"c": CONTROLS}, "") == ["derived_expression_missing"]
        assert self.codes({"c": CONTROLS}, "c.count +") == [
            "derived_expression_invalid"
        ]
        assert self.codes({"c": CONTROLS}, "x.count") == [
            "derived_expression_unknown_name"
        ]
        assert self.codes({"c": CONTROLS}, "x" * 3000) == [
            "derived_expression_too_long"
        ]


class TestTimeTokens:
    def test_today_now_and_offsets(self):
        now = datetime.datetime(2026, 10, 8, 12, 30, tzinfo=datetime.UTC)
        assert resolve_time_tokens("{{today}}", now) == "2026-10-08"
        assert resolve_time_tokens("{{ now }}", now) == "2026-10-08T12:30:00+00:00"
        assert resolve_time_tokens("{{today-30d}}", now) == "2026-09-08"
        assert resolve_time_tokens("{{ today + 7d }}", now) == "2026-10-15"
        assert resolve_time_tokens("plain", now) == "plain"
        assert resolve_time_tokens(["{{today}}"], now) == ["{{today}}"]
        assert resolve_time_tokens(5, now) == 5


@pytest.mark.django_db
class TestEvaluate:
    def test_datasets_feed_the_expression_within_the_subtree(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        sub = make_domain("Sub", mine)
        make_controls(mine, ["active", "to_do"])
        make_controls(sub, ["active"])
        make_controls(parent, ["active", "active"])
        evaluation = evaluate_formula(
            {"controls": CONTROLS, "active": ACTIVE},
            "active.count * 100.0 / controls.count",
            mine,
        )
        assert evaluation.datasets == {"controls": {"count": 3}, "active": {"count": 2}}
        assert evaluation.value == pytest.approx(66.666, abs=1e-2)
        assert evaluation.context["today"] == timezone.now().date().isoformat()

    def test_previous_and_other_metrics_are_in_the_context(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        other = make_instance(domain, ref_id="headcount")
        CustomMetricSample.objects.create(
            metric_instance=other,
            folder=domain,
            timestamp=timezone.now(),
            value={"result": 40.0},
        )
        evaluation = evaluate_formula(
            {"c": CONTROLS},
            "c.count * 1.0 / metrics.headcount.value + (previous == null ? 0 : previous)",
            domain,
            previous=None,
        )
        assert evaluation.value == pytest.approx(0.025)
        assert (
            evaluate_formula({"c": CONTROLS}, "previous + 1", domain, previous=2).value
            == 3
        )

    def test_other_metrics_stay_inside_the_subtree(self):
        parent = make_domain("Parent")
        mine = make_domain("Mine", parent)
        outside = make_instance(parent, ref_id="outside")
        CustomMetricSample.objects.create(
            metric_instance=outside,
            folder=parent,
            timestamp=timezone.now(),
            value={"result": 1.0},
        )
        with pytest.raises(DerivedMetricError, match="no field 'outside'"):
            evaluate_formula({"c": CONTROLS}, "metrics.outside.value", mine)

    def test_time_tokens_reach_the_filters(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(
            name="late",
            folder=domain,
            eta=timezone.now().date() - datetime.timedelta(days=3),
        )
        AppliedControl.objects.create(
            name="soon",
            folder=domain,
            eta=timezone.now().date() + datetime.timedelta(days=3),
        )
        late = {
            "model": "applied_control",
            "filters": {
                "conditions": [{"field": "eta", "op": "lt", "value": "{{today}}"}]
            },
            "aggregates": [{"fn": "count"}],
        }
        assert evaluate_formula({"late": late}, "late.count", domain).value == 1

    def test_failures_name_the_dataset_or_the_expression(self):
        domain = make_domain("Domain")
        with pytest.raises(DerivedMetricError, match="dataset 'c': unknown model"):
            evaluate_formula(
                {"c": {"model": "nope", "aggregates": [{"fn": "count"}]}}, "1", domain
            )
        with pytest.raises(DerivedMetricError, match="expression: division by zero"):
            evaluate_formula({"c": CONTROLS}, "1 / c.count", domain)


@pytest.mark.django_db
class TestShapeValue:
    def test_quantitative_needs_a_finite_number(self):
        definition = MetricDefinition(
            category=MetricDefinition.Category.QUANTITATIVE,
            folder=Folder.get_root_folder(),
        )
        assert shape_value(3, definition) == {"result": 3.0}
        assert shape_value(2.5, definition) == {"result": 2.5}
        for bad in ("3", True, None, [1], {"a": 1}):
            with pytest.raises(DerivedMetricError, match="must return a number"):
                shape_value(bad, definition)

    def test_qualitative_takes_a_name_a_ref_id_or_an_index(self):
        definition = MetricDefinition(
            category=MetricDefinition.Category.QUALITATIVE,
            folder=Folder.get_root_folder(),
            choices_definition=[
                {"ref_id": "green", "name": "Green"},
                {"ref_id": "amber", "name": "Amber"},
                {"ref_id": "red", "name": "Red"},
            ],
        )
        assert shape_value("Amber", definition) == {"choice_index": 2}
        assert shape_value("red", definition) == {"choice_index": 3}
        assert shape_value(1, definition) == {"choice_index": 1}
        assert shape_value(3.0, definition) == {"choice_index": 3}
        for bad in ("Blue", 0, 4, 1.5, None, True):
            with pytest.raises(DerivedMetricError, match="level|not a level"):
                shape_value(bad, definition)


@pytest.mark.django_db
class TestComputeSample:
    def setup_method(self):
        cache.clear()

    def test_writes_a_derived_sample_and_stamps_the_instance(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active", "active", "to_do", "deprecated"])
        instance = make_instance(domain)
        evaluation = compute_sample(instance)
        assert evaluation.value == 50.0
        sample = instance.samples.get()
        assert sample.value == {"result": 50.0}
        assert sample.source == CustomMetricSample.Source.DERIVED
        assert sample.folder == domain
        instance.refresh_from_db()
        assert instance.last_computed_at is not None
        assert instance.last_computation_error == ""
        assert instance.raw_value() == 50.0

    def test_the_previous_sample_feeds_the_next(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        instance = make_instance(
            domain,
            # Both branches of a ternary are evaluated, so the null case is
            # folded into a number before any arithmetic.
            make_definition(
                "(previous == null ? 0 : previous) + c.count", {"c": CONTROLS}
            ),
        )
        assert compute_sample(instance).value == 1
        assert compute_sample(instance).value == 2
        assert instance.samples.count() == 2

    def test_a_failure_is_recorded_and_writes_no_sample(self):
        domain = make_domain("Domain")
        instance = make_instance(
            domain, make_definition("1 / c.count", {"c": CONTROLS})
        )
        with pytest.raises(DerivedMetricError, match="division by zero"):
            compute_sample(instance)
        instance.refresh_from_db()
        assert instance.samples.count() == 0
        assert "division by zero" in instance.last_computation_error
        assert instance.last_computed_at is not None
        # A later success clears it.
        make_controls(domain, ["active"])
        compute_sample(instance)
        instance.refresh_from_db()
        assert instance.last_computation_error == ""

    def test_a_manual_definition_cannot_be_computed(self):
        domain = make_domain("Domain")
        instance = make_instance(domain, make_definition("", {}))
        with pytest.raises(DerivedMetricError, match="no formula"):
            compute_sample(instance)

    def test_write_false_evaluates_without_touching_anything(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        instance = make_instance(domain)
        assert compute_sample(instance, write=False).value == 100.0
        instance.refresh_from_db()
        assert instance.samples.count() == 0 and instance.last_computed_at is None

    def test_the_lock_keeps_two_workers_off_one_instance(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        instance = make_instance(domain)
        cache.add(f"metrology:derived-metric-lock:{instance.id}", "1", 60)
        assert compute_sample(instance) is None
        assert instance.samples.count() == 0
        cache.delete(f"metrology:derived-metric-lock:{instance.id}")
        assert compute_sample(instance) is not None
        # The lock is released after a run, failed or not.
        assert cache.get(f"metrology:derived-metric-lock:{instance.id}") is None


@pytest.mark.django_db
class TestSweep:
    def test_due_follows_the_collection_frequency(self):
        domain = make_domain("Domain")
        now = timezone.now()
        fresh = make_instance(domain, collection_frequency="daily")
        fresh.last_computed_at = now - datetime.timedelta(hours=2)
        fresh.save()
        hourly = make_instance(domain, collection_frequency="hourly")
        hourly.last_computed_at = now - datetime.timedelta(hours=2)
        hourly.save()
        never = make_instance(domain, collection_frequency="yearly")
        manual = make_instance(domain, make_definition("", {}))
        deprecated = make_instance(domain, status=MetricInstance.Status.DEPRECATED)
        stale = make_instance(domain, status=MetricInstance.Status.STALE)
        assert not is_due(fresh, now)
        assert is_due(hourly, now)
        assert is_due(never, now)
        due = {i.id for i in due_instances(now)}
        assert {hourly.id, never.id, stale.id} <= due
        assert fresh.id not in due and manual.id not in due and deprecated.id not in due

    def test_due_within_half_a_sweep_of_the_interval(self):
        """The stamp lands a few seconds after the tick that queued the run,
        so the next aligned tick must still count; a duplicate queued right
        after a run must not."""
        domain = make_domain("Domain")
        now = timezone.now()
        hourly = make_instance(domain, collection_frequency="hourly")
        hourly.last_computed_at = now - datetime.timedelta(minutes=59, seconds=57)
        assert is_due(hourly, now)
        hourly.last_computed_at = now - datetime.timedelta(minutes=50)
        assert not is_due(hourly, now)
        realtime = make_instance(domain, collection_frequency="realtime")
        realtime.last_computed_at = now - datetime.timedelta(minutes=14, seconds=57)
        assert is_due(realtime, now)
        realtime.last_computed_at = now - datetime.timedelta(seconds=2)
        assert not is_due(realtime, now)

    def test_no_frequency_means_daily(self):
        domain = make_domain("Domain")
        instance = make_instance(domain, collection_frequency=None)
        now = timezone.now()
        instance.last_computed_at = now - datetime.timedelta(hours=23)
        assert not is_due(instance, now)
        instance.last_computed_at = now - datetime.timedelta(hours=25)
        assert is_due(instance, now)


@pytest.mark.django_db
class TestDownsampling:
    def test_keeps_one_derived_sample_per_day_beyond_a_week(self):
        domain = make_domain("Domain")
        instance = make_instance(domain)
        now = timezone.now()

        def sample(days_ago, hour, source=CustomMetricSample.Source.DERIVED):
            stamp = (now - datetime.timedelta(days=days_ago)).replace(
                hour=hour, minute=0
            )
            return CustomMetricSample.objects.create(
                metric_instance=instance,
                folder=domain,
                timestamp=stamp,
                value={"result": float(hour)},
                source=source,
            )

        old_morning, old_evening = sample(20, 8), sample(20, 18)
        older = sample(21, 12)
        manual_old = sample(20, 9, source=CustomMetricSample.Source.MANUAL)
        recent_a, recent_b = sample(2, 8), sample(2, 18)
        assert downsample_derived_samples(now) == 1
        remaining = set(instance.samples.values_list("id", flat=True))
        assert old_morning.id not in remaining
        assert {
            old_evening.id,
            older.id,
            manual_old.id,
            recent_a.id,
            recent_b.id,
        } <= remaining

    def test_downsampling_marks_no_reader(self, django_capture_on_commit_callbacks):
        """The sample kept for a day is the one a reader's day-end cutoff
        finds, so nothing a formula reads changes: no mark, no signal."""
        domain = make_domain("Domain")
        instance = make_instance(domain)
        reader = make_instance(
            domain,
            make_definition(
                "x",
                None,
                inputs=[
                    {
                        "key": "x",
                        "definition": str(instance.metric_definition_id),
                        "combine": "one",
                    }
                ],
            ),
        )
        now = timezone.now()
        for hour in (8, 18):
            CustomMetricSample.objects.create(
                metric_instance=instance,
                folder=domain,
                timestamp=(now - datetime.timedelta(days=20)).replace(
                    hour=hour, minute=0
                ),
                value={"result": float(hour)},
                source=CustomMetricSample.Source.DERIVED,
            )
        MetricInstance.objects.filter(id=reader.id).update(recompute_from=None)
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            assert downsample_derived_samples(now) == 1
        assert callbacks == []
        reader.refresh_from_db()
        assert reader.recompute_from is None


@pytest.mark.django_db
class TestSerializer:
    def test_the_formula_is_validated_on_write(self):
        serializer = MetricDefinitionWriteSerializer(
            data={
                "name": "Share",
                "folder": str(Folder.get_root_folder().id),
                "datasets": {"c": CONTROLS},
                "expression": "x.count",
            }
        )
        assert not serializer.is_valid()
        assert "not a dataset" in str(serializer.errors["expression"])

    def test_a_manual_definition_still_saves(self):
        serializer = MetricDefinitionWriteSerializer(
            data={"name": "Manual", "folder": str(Folder.get_root_folder().id)}
        )
        assert serializer.is_valid(), serializer.errors


@pytest.mark.django_db
class TestEndpoints:
    def setup_method(self):
        cache.clear()

    def admin(self):
        return User.objects.create_superuser(
            email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
        )

    def reader(self, folder):
        """A user who may view the folder's metrics but add none."""
        user = User.objects.create_user(
            email=f"reader-{uuid.uuid4().hex[:6]}@tests.local"
        )
        group = UserGroup.objects.create(
            name=f"readers {uuid.uuid4().hex[:4]}", folder=folder
        )
        group.user_set.add(user)
        role = Role.objects.create(
            name=f"viewer {uuid.uuid4().hex[:4]}", folder=Folder.get_root_folder()
        )
        role.permissions.add(
            *Permission.objects.filter(
                codename__in=["view_metricinstance", "view_metricdefinition"]
            )
        )
        assignment = RoleAssignment.objects.create(
            user_group=group, role=role, folder=Folder.get_root_folder()
        )
        assignment.perimeter_folders.add(folder)
        return user

    def post(self, view, path, data, user, **kwargs):
        request = APIRequestFactory().post(path, data, format="json")
        force_authenticate(request, user=user)
        return view(request, **kwargs)

    def test_preview_answers_datasets_and_value(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active", "to_do"])
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        response = self.post(
            view,
            "/metrology/metric-definitions/preview-formula/",
            {
                "folder": str(domain.id),
                "datasets": {"controls": CONTROLS, "active": ACTIVE},
                "expression": "active.count * 100.0 / controls.count",
            },
            self.admin(),
        )
        assert response.status_code == 200, response.data
        assert response.data == {
            "ok": True,
            "value": 50.0,
            "datasets": {"controls": {"count": 2}, "active": {"count": 1}},
        }
        assert CustomMetricSample.objects.count() == 0

    def test_preview_reports_validation_and_evaluation_failures(self):
        domain = make_domain("Domain")
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        response = self.post(
            view,
            "/metrology/metric-definitions/preview-formula/",
            {"folder": str(domain.id), "datasets": {"c": CONTROLS}, "expression": "x"},
            self.admin(),
        )
        assert response.status_code == 200
        assert response.data["ok"] is False
        assert response.data["errors"][0]["code"] == "derived_expression_unknown_name"
        response = self.post(
            view,
            "/metrology/metric-definitions/preview-formula/",
            {
                "folder": str(domain.id),
                "datasets": {"c": CONTROLS},
                "expression": "1 / c.count",
            },
            self.admin(),
        )
        assert response.data["ok"] is False
        assert response.data["errors"][0]["code"] == "derived_evaluation_failed"

    def test_preview_needs_a_folder_and_the_right_to_add_metrics_there(self):
        domain = make_domain("Domain")
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        response = self.post(
            view,
            "/metrology/metric-definitions/preview-formula/",
            {"datasets": {"c": CONTROLS}, "expression": "c.count"},
            self.admin(),
        )
        assert response.status_code == 400
        response = self.post(
            view,
            "/metrology/metric-definitions/preview-formula/",
            {
                "folder": str(domain.id),
                "datasets": {"c": CONTROLS},
                "expression": "c.count",
            },
            self.reader(domain),
        )
        assert response.status_code == 403

    def test_a_derived_sample_cannot_be_deleted_by_hand(self):
        from metrology.views import CustomMetricSampleViewSet

        domain = make_domain("Domain")
        derived = make_instance(domain)
        manual = make_instance(domain, make_definition("", {}))
        view = CustomMetricSampleViewSet.as_view({"delete": "destroy"})
        admin = self.admin()
        for instance, expected in ((derived, 400), (manual, 204)):
            sample = CustomMetricSample.objects.create(
                metric_instance=instance,
                folder=domain,
                timestamp=timezone.now(),
                value={"result": 1.0},
            )
            request = APIRequestFactory().delete(
                f"/metrology/custom-metric-samples/{sample.id}/"
            )
            force_authenticate(request, user=admin)
            response = view(request, pk=str(sample.id))
            assert response.status_code == expected, response.data
            assert CustomMetricSample.objects.filter(id=sample.id).exists() == (
                expected == 400
            )

    def test_refresh_queues_a_recomputation_for_those_who_may_change_it(self):
        domain = make_domain("Domain")
        instance = make_instance(domain)
        view = MetricInstanceViewSet.as_view({"post": "refresh"})
        response = self.post(
            view,
            f"/metrology/metric-instances/{instance.id}/refresh/",
            {},
            self.admin(),
            pk=str(instance.id),
        )
        assert response.status_code == 202
        assert response.data == {"queued": True}
        response = self.post(
            view,
            f"/metrology/metric-instances/{instance.id}/refresh/",
            {},
            self.reader(domain),
            pk=str(instance.id),
        )
        assert response.status_code == 403

    def test_the_registry_is_served_to_the_metric_form(self):
        view = MetricDefinitionViewSet.as_view({"get": "readable_models"})
        request = APIRequestFactory().get(
            "/metrology/metric-definitions/readable-models/"
        )
        force_authenticate(request, user=self.admin())
        response = view(request)
        assert response.status_code == 200
        entries = {entry["key"]: entry for entry in response.data}
        assert entries["applied_control"]["kinds"]["status"] == "text"
        # The editor offers these, and only these, as group-by fields.
        assert entries["applied_control"]["categorical"] == ["status", "priority"]
        assert {fn["name"] for fn in entries["applied_control"]["aggregates"]} >= {
            "count",
            "avg",
        }

    def test_refresh_refuses_a_manual_metric(self):
        domain = make_domain("Domain")
        instance = make_instance(domain, make_definition("", {}))
        view = MetricInstanceViewSet.as_view({"post": "refresh"})
        response = self.post(
            view,
            f"/metrology/metric-instances/{instance.id}/refresh/",
            {},
            self.admin(),
            pk=str(instance.id),
        )
        assert response.status_code == 400


# ---------- regressions from the PR review ----------


def by(field):
    return {
        "model": "applied_control",
        "aggregates": [{"fn": "count", "group_by": field}],
    }


def make_sample(instance, value, minutes_ago=0):
    return CustomMetricSample.objects.create(
        metric_instance=instance,
        folder=instance.folder,
        timestamp=timezone.now() - datetime.timedelta(minutes=minutes_ago),
        value={"result": value},
    )


@pytest.mark.django_db
class TestGroupingNamesCategoriesOnly:
    """A derived value is visible without read rights on the rows: a
    breakdown by name or description would hand out row content."""

    @pytest.mark.parametrize("field", ["name", "description", "ref_id", "id"])
    def test_free_text_cannot_group_a_dataset(self, field):
        errors = validate_formula({"c": by(field)}, "1")
        assert [code for code, _m in errors] == ["derived_dataset_invalid"]
        assert f"'{field}' cannot group a derived metric" in errors[0][1]

    def test_a_category_still_groups(self):
        assert validate_formula({"c": by("status")}, "1") == []

    def test_evaluation_refuses_a_definition_saved_around_the_rule(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="secret plan", folder=domain)
        with pytest.raises(DerivedMetricError, match="cannot group"):
            evaluate_formula({"c": by("name")}, "1", domain)

    def test_the_preview_never_answers_row_content(self):
        domain = make_domain("Domain")
        AppliedControl.objects.create(
            name="secret plan", description="top secret", folder=domain
        )
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        request = APIRequestFactory().post(
            "/metrology/metric-definitions/preview-formula/",
            {
                "folder": str(domain.id),
                "datasets": {"c": by("description")},
                "expression": "1",
            },
            format="json",
        )
        force_authenticate(
            request,
            user=User.objects.create_superuser(
                email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
            ),
        )
        response = view(request)
        assert response.status_code == 200
        assert response.data["ok"] is False
        assert "datasets" not in response.data
        assert "top secret" not in str(response.data)


@pytest.mark.django_db
class TestFilterValueFailures:
    def setup_method(self):
        cache.clear()

    def late(self, token):
        return {
            "late": {
                "model": "applied_control",
                "filters": {
                    "conditions": [{"field": "eta", "op": "lt", "value": token}]
                },
                "aggregates": [{"fn": "count"}],
            }
        }

    def test_a_value_the_column_refuses_is_recorded_not_raised_raw(self):
        """{{now}} on a date column made Django raise ValidationError, which
        escaped compute_sample: nothing was recorded and the sweep requeued
        the instance forever."""
        domain = make_domain("Domain")
        AppliedControl.objects.create(name="a", folder=domain)
        instance = make_instance(
            domain, make_definition("late.count", self.late("{{now}}"))
        )
        with pytest.raises(DerivedMetricError, match="does not fit its field"):
            compute_sample(instance)
        instance.refresh_from_db()
        assert instance.last_computed_at is not None
        assert instance.last_computation_error == (
            "dataset 'late': a filter value does not fit its field"
        )
        # Django's own wording stays in the log.
        assert "YYYY-MM-DD" not in instance.last_computation_error

    def test_the_preview_answers_the_same_failure_without_a_500(self):
        domain = make_domain("Domain")
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        request = APIRequestFactory().post(
            "/metrology/metric-definitions/preview-formula/",
            {
                "folder": str(domain.id),
                "datasets": self.late("not a date"),
                "expression": "late.count",
            },
            format="json",
        )
        force_authenticate(
            request,
            user=User.objects.create_superuser(
                email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
            ),
        )
        response = view(request)
        assert response.status_code == 200
        assert response.data["errors"] == [
            {
                "code": "derived_evaluation_failed",
                "message": "dataset 'late': a filter value does not fit its field",
            }
        ]

    def test_a_stale_matrix_level_is_named(self, monkeypatch):
        import metrology.derived as derived

        def stale(*_args, **_kwargs):
            raise IndexError("list index out of range")

        monkeypatch.setattr(derived, "run_aggregate_read", stale)
        with pytest.raises(DerivedMetricError, match="no longer exists"):
            evaluate_formula({"c": CONTROLS}, "c.count", make_domain("Domain"))


@pytest.mark.django_db
class TestNonStringExpression:
    def test_validation_reports_it(self):
        assert validate_formula({"c": CONTROLS}, 5) == [
            ("derived_expression_invalid", "The expression must be text")
        ]

    def test_the_preview_answers_instead_of_a_500(self):
        domain = make_domain("Domain")
        view = MetricDefinitionViewSet.as_view({"post": "preview_formula"})
        request = APIRequestFactory().post(
            "/metrology/metric-definitions/preview-formula/",
            {"folder": str(domain.id), "datasets": {"c": CONTROLS}, "expression": 5},
            format="json",
        )
        force_authenticate(
            request,
            user=User.objects.create_superuser(
                email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
            ),
        )
        response = view(request)
        assert response.status_code == 200
        assert response.data["errors"][0]["code"] == "derived_expression_invalid"


@pytest.mark.django_db
class TestQueuedTwice:
    def setup_method(self):
        cache.clear()

    def test_a_duplicate_sweep_run_writes_nothing(self):
        """A lagging queue holds the same instance twice; the second run
        finds the first one's stamp and stops."""
        from metrology.tasks import compute_derived_metric_task

        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        instance = make_instance(domain, collection_frequency="daily")
        compute_derived_metric_task.call_local(str(instance.id), only_if_due=True)
        compute_derived_metric_task.call_local(str(instance.id), only_if_due=True)
        assert instance.samples.count() == 1

    def test_the_stamp_is_read_under_the_lock_not_from_the_caller(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        instance = make_instance(domain, collection_frequency="daily")
        stale_copy = MetricInstance.objects.get(id=instance.id)
        assert compute_sample(instance, only_if_due=True) is not None
        # Loaded before the first run finished: its stamp is still None.
        assert stale_copy.last_computed_at is None
        assert compute_sample(stale_copy, only_if_due=True) is None
        assert instance.samples.count() == 1

    def test_a_manual_refresh_always_computes(self):
        domain = make_domain("Domain")
        make_controls(domain, ["active"])
        instance = make_instance(domain, collection_frequency="daily")
        compute_sample(instance)
        compute_sample(instance)
        assert instance.samples.count() == 2


@pytest.mark.django_db
class TestServerOwnedFields:
    def test_a_client_cannot_label_a_sample(self):
        from metrology.serializers import CustomMetricSampleWriteSerializer

        domain = make_domain("Domain")
        instance = make_instance(domain, make_definition("", {}))
        serializer = CustomMetricSampleWriteSerializer(
            data={
                "metric_instance": str(instance.id),
                "timestamp": timezone.now().isoformat(),
                "value": {"result": 1},
                "source": "derived",
            }
        )
        assert serializer.is_valid(), serializer.errors
        assert "source" not in serializer.validated_data

    def test_a_derived_series_refuses_a_typed_in_sample(self):
        from metrology.serializers import CustomMetricSampleWriteSerializer

        domain = make_domain("Domain")
        instance = make_instance(domain)
        serializer = CustomMetricSampleWriteSerializer(
            data={
                "metric_instance": str(instance.id),
                "timestamp": timezone.now().isoformat(),
                "value": {"result": 1},
            }
        )
        assert not serializer.is_valid()
        assert "computed from its formula" in str(serializer.errors["metric_instance"])

    def test_the_sampler_bookkeeping_is_read_only(self):
        from metrology.serializers import MetricInstanceWriteSerializer

        domain = make_domain("Domain")
        instance = make_instance(domain)
        serializer = MetricInstanceWriteSerializer(
            instance,
            data={
                "last_computed_at": "2099-01-01T00:00:00Z",
                "last_computation_error": "forged",
            },
            partial=True,
        )
        assert serializer.is_valid(), serializer.errors
        assert "last_computed_at" not in serializer.validated_data
        assert "last_computation_error" not in serializer.validated_data


@pytest.mark.django_db
class TestOtherMetrics:
    def test_not_queried_when_the_expression_does_not_read_them(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        domain = make_domain("Domain")
        make_instance(domain, ref_id="other")
        with CaptureQueriesContext(connection) as queries:
            evaluate_formula({"c": CONTROLS}, "c.count", domain)
        assert not any("metrology_metricinstance" in query["sql"] for query in queries)

    def test_the_latest_sample_in_two_queries_whatever_the_history(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        from metrology.derived import other_metric_values

        domain = make_domain("Domain")
        first = make_instance(domain, ref_id="first")
        second = make_instance(domain, ref_id="second")
        for minutes_ago, value in ((30, 1.0), (20, 2.0), (10, 3.0)):
            make_sample(first, value, minutes_ago)
        make_sample(second, 7.0)
        make_instance(domain, ref_id="empty")
        with CaptureQueriesContext(connection) as queries:
            values = other_metric_values(domain, referenced={"first"})
        assert values == {
            "first": {"value": 3.0},
            "second": {"value": 7.0},
            "empty": {"value": None},
        }
        # The subtree lookup, the instances with their latest sample id, the
        # samples themselves.
        assert len(queries) <= 3

    def test_a_shared_ref_id_is_never_picked_arbitrarily(self):
        parent = make_domain("Parent")
        left = make_domain("Left", parent)
        right = make_domain("Right", parent)
        make_sample(make_instance(left, ref_id="M1"), 1.0)
        make_sample(make_instance(right, ref_id="M1"), 2.0)
        with pytest.raises(DerivedMetricError, match="2 instances in this domain"):
            evaluate_formula({"c": CONTROLS}, "metrics.M1.value", parent)
        # Not reading it is fine, and it is not offered to read.
        evaluation = evaluate_formula({"c": CONTROLS}, "size(metrics)", parent)
        assert evaluation.value == 0


@pytest.mark.django_db
class TestChoiceEndpointsCache:
    def test_category_is_cached_again(self):
        view = MetricDefinitionViewSet.as_view({"get": "category"})
        request = APIRequestFactory().get("/metrology/metric-definitions/category/")
        force_authenticate(
            request,
            user=User.objects.create_superuser(
                email=f"admin-{uuid.uuid4().hex[:6]}@tests.local"
            ),
        )
        response = view(request)
        response.render()
        assert "max-age" in response.get("Cache-Control", "")
