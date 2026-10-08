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
